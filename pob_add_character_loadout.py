#!/usr/bin/env python3
"""
Add PoE Character as Loadout to Existing PoB Build
====================================================
Takes an existing .build/.json file and adds a character (from OAuth API)
as a new loadout (SkillSet + ItemSet + ConfigSet).
"""

import json
import base64
import zlib
import copy
import uuid
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# Add script directory to path for passive converter
sys.path.insert(0, '/Users/joecrawford/.hermes/profiles/bot-of-exile/scripts')
try:
    from pob_passive_converter import convert_passive_hashes, get_class_id, get_ascendancy_id
    PASSIVE_CONVERTER_AVAILABLE = True
except ImportError:
    PASSIVE_CONVERTER_AVAILABLE = False
    print("Warning: pob_passive_converter not available, passive tree import will be skipped")


# ============================================================
# PoB JSON Structure Helpers
# ============================================================

def get_next_id(items: List[Dict]) -> str:
    """Get next numeric ID for items/skills."""
    if not items:
        return "1"
    max_id = max(int(item.get('_attr', {}).get('id', 0)) for item in items if item.get('_attr', {}).get('id', '').isdigit())
    return str(max_id + 1)


def find_skill_set(build: Dict, loadout_id: str) -> Optional[Dict]:
    """Find SkillSet by ID."""
    for ss in build.get('Skills', {}).get('SkillSet', []):
        if ss.get('_attr', {}).get('id') == loadout_id:
            return ss
    return None


def find_item_set(build: Dict, loadout_id: str) -> Optional[Dict]:
    """Find ItemSet by ID."""
    for iset in build.get('Items', {}).get('ItemSet', []):
        if iset.get('_attr', {}).get('id') == loadout_id:
            return iset
    return None


def find_config_set(build: Dict, loadout_id: str) -> Optional[Dict]:
    """Find ConfigSet by ID."""
    for cs in build.get('Config', {}).get('ConfigSet', []):
        if cs.get('_attr', {}).get('id') == loadout_id:
            return cs
    return None


# ============================================================
# Character Data → PoB Items Conversion
# ============================================================

SLOT_MAPPING = {
    # API inventoryId → PoB slot name
    "Helmet": "Helmet",
    "BodyArmour": "Body Armour",
    "Gloves": "Gloves",
    "Boots": "Boots",
    "Amulet": "Amulet",
    "Ring": "Ring",  # Will need Ring 1 / Ring 2 logic
    "Belt": "Belt",
    "Weapon": "Weapon 1",
    "Weapon2": "Weapon 2",
    "Offhand": "Weapon 2",  # Shield/quiver
    "Flask": "Flask",
    "Jewel": "Jewel",  # Passive tree jewels
    "AbyssalJewel": "Abyssal Jewel",
    "Charm": "Charm",
}

# Standard PoB slots (from ItemSet slots)
POB_SLOTS = [
    "Weapon 1", "Weapon 1 Swap", "Weapon 2", "Weapon 2 Swap",
    "Helmet", "Body Armour", "Gloves", "Boots",
    "Amulet", "Ring 1", "Ring 2", "Belt",
    "Flask 1", "Flask 2", "Flask 3", "Flask 4", "Flask 5",
    "Weapon 1 Abyssal Socket 1", "Weapon 1 Abyssal Socket 2",
    "Weapon 2 Abyssal Socket 1", "Weapon 2 Abyssal Socket 2",
    "Helmet Abyssal Socket 1", "Helmet Abyssal Socket 2",
    "Body Armour Abyssal Socket 1", "Body Armour Abyssal Socket 2",
    "Gloves Abyssal Socket 1", "Gloves Abyssal Socket 2",
    "Boots Abyssal Socket 1", "Boots Abyssal Socket 2",
    "Graft 1", "Graft 2",
]


def api_item_to_pob_item(api_item: Dict, next_id: int) -> Dict:
    """
    Convert PoE API item format to PoB item format.
    This is a simplified version - full conversion requires itemLib parsing.
    """
    # Build item text representation (PoB's native format)
    lines = []
    
    # Rarity
    rarity_map = {"Normal": "NORMAL", "Magic": "MAGIC", "Rare": "RARE", "Unique": "UNIQUE"}
    rarity = rarity_map.get(api_item.get("rarity", "Normal"), "NORMAL")
    lines.append(f"Rarity: {rarity}")
    
    # Name
    if api_item.get("name"):
        lines.append(api_item["name"])
    
    # Base type
    if api_item.get("typeLine"):
        lines.append(api_item["typeLine"])
    
    # Properties (armour, evasion, ES, damage, etc.)
    for prop in api_item.get("properties", []):
        if prop.get("values"):
            val = prop["values"][0][0] if prop["values"][0] else ""
            lines.append(f"{prop['name']}: {val}")
    
    # Requirements
    requirements = []
    for req in api_item.get("requirements", []):
        requirements.append(f"{req['name']}: {req['values'][0][0] if req['values'] else ''}")
    if requirements:
        lines.append("Requirements:")
        lines.extend(f"  {r}" for r in requirements)
    
    # Sockets
    sockets = api_item.get("sockets", [])
    if sockets:
        socket_groups = {}
        for s in sockets:
            group = s.get("group", 0)
            if group not in socket_groups:
                socket_groups[group] = []
            socket_groups[group].append(s["attr"])  # attr: D=Dex, S=Str, I=Int
        socket_str = " ".join("-".join(attrs) for attrs in socket_groups.values())
        lines.append(f"Sockets: {socket_str}")
    
    # Item Level
    if api_item.get("ilvl"):
        lines.append(f"Item Level: {api_item['ilvl']}")
    
    # Quality
    if api_item.get("quality", 0) > 0:
        lines.append(f"Quality: {api_item['quality']}")
    
    # Implicits
    implicits = api_item.get("implicitMods", [])
    if implicits:
        lines.append("Implicits: " + str(len(implicits)))
        for mod in implicits:
            lines.append(mod)
    
    # Explicits
    explicits = api_item.get("explicitMods", [])
    if explicits:
        for mod in explicits:
            lines.append(mod)
    
    # Crafted mods
    crafted = api_item.get("craftedMods", [])
    if crafted:
        lines.append("Crafted:")
        for mod in crafted:
            lines.append(mod)
    
    # Fractured mods
    fractured = api_item.get("fracturedMods", [])
    if fractured:
        lines.append("Fractured:")
        for mod in fractured:
            lines.append(mod)
    
    # Enchantments
    enchants = api_item.get("enchantMods", [])
    if enchants:
        lines.append("Enchantments:")
        for mod in enchants:
            lines.append(mod)
    
    # Corrupted
    if api_item.get("corrupted"):
        lines.append("Corrupted")
    
    # Influences
    influences = []
    for inf in ["shaper", "elder", "crusader", "redeemer", "hunter", "warlord"]:
        if api_item.get(inf):
            influences.append(inf.capitalize())
    if influences:
        lines.append("Has " + " ".join(influences) + " Influence")
    
    item_text = "\n".join(lines)
    
    return {
        "_attr": {"id": str(next_id)},
        "_elem": "Item",
        "_text": item_text
    }


def assign_items_to_slots(character: Dict) -> Dict[str, int]:
    """
    Assign API items to PoB slot names.
    Returns dict of slot_name -> item_index (in character equipment list)
    """
    equipment = character.get("equipment", [])
    slot_assignments = {}
    ring_count = 0
    flask_count = 0
    
    for i, item in enumerate(equipment):
        inv_id = item.get("inventoryId", "")
        
        if inv_id == "Ring":
            ring_count += 1
            slot_name = f"Ring {ring_count}"
        elif inv_id == "Flask":
            flask_count += 1
            slot_name = f"Flask {flask_count}"
        elif inv_id == "Jewel":
            # Jewels go to passive tree sockets - handled separately
            continue
        elif inv_id == "AbyssalJewel":
            # Abyssal jewels go to abyssal sockets on gear
            continue
        else:
            slot_name = SLOT_MAPPING.get(inv_id, inv_id)
        
        if slot_name in POB_SLOTS:
            slot_assignments[slot_name] = i
    
    return slot_assignments


# ============================================================
# Character Data → PoB Skills Conversion
# ============================================================

def extract_skills_from_character(character: Dict) -> List[Dict]:
    """
    Extract active skills from character equipment.
    Returns list of skill dicts for PoB format.
    """
    skills = []
    equipment = character.get("equipment", [])
    
    for item in equipment:
        sockets = item.get("sockets", [])
        if not sockets:
            continue
        
        # Group sockets by link group
        groups = {}
        for s in sockets:
            group = s.get("group", 0)
            if group not in groups:
                groups[group] = []
            groups[group].append(s)
        
        # For each linked group, create a skill setup
        for group_id, group_sockets in groups.items():
            # Find the active skill gem (first gem in group that's not a support)
            # In real implementation, check gem type from gem data
            # For now, assume first is active if it has no "Support" in name
            active_gem = None
            support_gems = []
            
            for s in group_sockets:
                gem_name = s.get("name", "") or s.get("typeLine", "")
                is_support = "Support" in gem_name or "Support" in s.get("typeLine", "")
                if active_gem is None and not is_support:
                    active_gem = s
                else:
                    support_gems.append(s)
            
            # If no clear active gem, use first
            if active_gem is None and group_sockets:
                active_gem = group_sockets[0]
                support_gems = group_sockets[1:]
            
            if active_gem:
                skill = build_skill_from_gems(
                    active_gem, 
                    support_gems, 
                    item.get("inventoryId", ""),
                    item.get("name", "")
                )
                skills.append(skill)
    
    return skills


def build_skill_from_gems(active_gem: Dict, support_gems: List[Dict], slot: str, item_name: str) -> Dict:
    """Build PoB Skill object from gem data."""
    gems = []
    
    # Active gem - extract name from various possible fields
    active_name = active_gem.get("name") or active_gem.get("typeLine") or "Unknown"
    active_type = active_gem.get("typeLine", "Metadata/Items/Gems/SkillGemDefault")
    
    gems.append({
        "_attr": {
            "count": "1",
            "enableGlobal1": "true",
            "enableGlobal2": "true",
            "enabled": "true",
            "gemId": active_type,
            "level": str(active_gem.get("level", 1)),
            "nameSpec": active_name,
            "quality": str(active_gem.get("quality", 0)),
            "skillId": active_name.replace(" ", "").replace("'", ""),
            "variantId": active_name.replace(" ", "").replace("'", ""),
        },
        "_elem": "Gem"
    })
    
    # Support gems
    for sg in support_gems:
        sg_name = sg.get("name") or sg.get("typeLine") or "Unknown"
        sg_type = sg.get("typeLine", "Metadata/Items/Gems/SupportGemDefault")
        gems.append({
            "_attr": {
                "count": "1",
                "enableGlobal1": "true",
                "enableGlobal2": "true",
                "enabled": "true",
                "gemId": sg_type,
                "level": str(sg.get("level", 1)),
                "nameSpec": sg_name,
                "quality": str(sg.get("quality", 0)),
                "skillId": "Support" + sg_name.replace(" ", "").replace("'", ""),
                "variantId": "Support" + sg_name.replace(" ", "").replace("'", ""),
            },
            "_elem": "Gem"
        })
    
    # Determine slot
    pob_slot = SLOT_MAPPING.get(slot, "Weapon 1")
    
    return {
        "Gem": gems if len(gems) > 1 else gems[0],
        "_attr": {
            "enabled": "true",
            "includeInFullDPS": "true",
            "label": "",
            "mainActiveSkill": "1",
            "mainActiveSkillCalcs": "1",
            "slot": pob_slot
        },
        "_elem": "Skill"
    }


# ============================================================
# Character Data → PoB Passive Tree
# ============================================================

def passive_hashes_to_pob_spec(hashes: List[int], hashes_ex: List[int] = None, 
                                mastery_effects: List[List[int]] = None) -> str:
    """
    Convert passive hashes to PoB tree spec format.
    This is complex - PoB uses a binary format. 
    For now, return a placeholder that PoB can parse.
    """
    # The real implementation would use PoB's passiveTree:PassivesFromHashes()
    # which requires the passive tree data files.
    # For headless use, we'd need to load the tree data.
    return ""


# ============================================================
# Main: Add Character as Loadout
# ============================================================

def add_character_loadout(
    build_json: Dict,
    character: Dict,
    loadout_title: str = "Imported Character",
    loadout_id: str = None,
    template_loadout_id: str = "1"  # Use first loadout as template
) -> Dict:
    """
    Add a character as a new loadout to an existing build.
    
    Args:
        build_json: Existing build JSON (from export_build)
        character: Character data from OAuth API /character/{name}
        loadout_title: Title for the new loadout
        loadout_id: Optional specific ID (auto-generated if not provided)
        template_loadout_id: Loadout ID to use as template for slots/config
    
    Returns:
        Modified build JSON with new loadout added
    """
    build = copy.deepcopy(build_json)
    
    # Get template structures from existing loadout
    template_skillset = find_skill_set(build, template_loadout_id)
    template_itemset = find_item_set(build, template_loadout_id)
    template_configset = find_config_set(build, template_loadout_id)
    
    if not template_itemset:
        raise ValueError(f"Template loadout {template_loadout_id} not found")
    
    # Extract slot template (names only, itemId will be replaced)
    slot_template = []
    for slot in template_itemset.get('Slot', []):
        slot_template.append({
            "_attr": {"name": slot['_attr']['name']},
            "_elem": "Slot"
        })
    
    # Extract config template (inputs and placeholders structure)
    config_input_template = []
    for inp in template_configset.get('Input', []):
        config_input_template.append(copy.deepcopy(inp))
    
    config_placeholder_template = []
    for ph in template_configset.get('Placeholder', []):
        config_placeholder_template.append(copy.deepcopy(ph))
    
    # Determine next loadout ID
    existing_ids = set()
    for ss in build.get('Skills', {}).get('SkillSet', []):
        existing_ids.add(ss.get('_attr', {}).get('id'))
    for iset in build.get('Items', {}).get('ItemSet', []):
        existing_ids.add(iset.get('_attr', {}).get('id'))
    for cs in build.get('Config', {}).get('ConfigSet', []):
        existing_ids.add(cs.get('_attr', {}).get('id'))
    
    if loadout_id is None:
        loadout_id = str(max([int(i) for i in existing_ids if i.isdigit()] + [0]) + 1)
    elif loadout_id in existing_ids:
        raise ValueError(f"Loadout ID {loadout_id} already exists")
    
    # ===== 1. ADD ITEMS =====
    items_list = build.setdefault('Items', {}).setdefault('Item', [])
    next_item_id = int(get_next_id(items_list))
    
    # Convert character items to PoB items
    slot_assignments = assign_items_to_slots(character)
    equipment = character.get("equipment", [])
    
    item_id_map = {}  # slot_name -> item_id
    
    for slot_name, equip_idx in slot_assignments.items():
        api_item = equipment[equip_idx]
        pob_item = api_item_to_pob_item(api_item, next_item_id)
        items_list.append(pob_item)
        item_id_map[slot_name] = str(next_item_id)
        next_item_id += 1
    
    # Also add inventory items (optional - could be stash)
    inventory = character.get("inventory", [])
    for item in inventory:
        pob_item = api_item_to_pob_item(item, next_item_id)
        items_list.append(pob_item)
        next_item_id += 1
    
    # ===== 2. CREATE ITEM SET (using template) =====
    item_set = {
        "_attr": {
            "id": loadout_id,
            "title": loadout_title,
            "useSecondWeaponSet": template_itemset.get('_attr', {}).get('useSecondWeaponSet', 'false')
        },
        "_elem": "ItemSet",
        "Slot": []
    }
    
    # Create all slots from template
    for slot_tmpl in slot_template:
        slot_name = slot_tmpl['_attr']['name']
        slot_attr = {"name": slot_name}
        if slot_name in item_id_map:
            slot_attr["itemId"] = item_id_map[slot_name]
            slot_attr["active"] = "true"
        else:
            slot_attr["itemId"] = "0"
        item_set["Slot"].append({"_attr": slot_attr, "_elem": "Slot"})
    
    build.setdefault('Items', {}).setdefault('ItemSet', []).append(item_set)
    
    # ===== 3. CREATE SKILL SET =====
    skills_list = build.setdefault('Skills', {}).setdefault('SkillSet', [])
    
    # Extract skills from character
    char_skills = extract_skills_from_character(character)
    
    skill_set = {
        "_attr": {
            "id": loadout_id,
            "title": loadout_title
        },
        "_elem": "SkillSet",
        "Skill": char_skills
    }
    
    skills_list.append(skill_set)
    
    # ===== 4. CREATE CONFIG SET (using template) =====
    config_sets = build.setdefault('Config', {}).setdefault('ConfigSet', [])
    
    # Base config from character
    passives = character.get("passives", {})
    
    config_set = {
        "_attr": {
            "id": loadout_id,
            "title": loadout_title
        },
        "_elem": "ConfigSet",
        "CustomModifierBlock": {
            "_attr": {"enabled": "true", "title": "Default"},
            "_elem": "CustomModifierBlock"
        },
        "Input": config_input_template,  # Use template inputs
        "Placeholder": config_placeholder_template  # Use template placeholders
    }
    
    # Update character-specific inputs
    for inp in config_set["Input"]:
        attrs = inp.get('_attr', {})
        name = attrs.get('name')
        if name == 'pantheonMajorGod':
            attrs['string'] = character.get("pantheon_major", "Lunaris")
        elif name == 'pantheonMinorGod':
            attrs['string'] = character.get("pantheon_minor", "Tukohama")
        elif name == 'bandit':
            attrs['string'] = character.get("bandit_choice", "None")
    
    config_sets.append(config_set)
    
    # ===== 5. UPDATE PASSIVE TREE (Tree.Spec) =====
    if PASSIVE_CONVERTER_AVAILABLE:
        passives = character.get("passives", {})
        if passives:
            # Combine regular hashes and extended (cluster jewel) hashes
            all_hashes = list(passives.get("hashes", []))
            all_hashes.extend(passives.get("hashes_ex", []))
            
            if all_hashes:
                # Get class/ascendancy IDs
                class_name = character.get("class", "Marauder")
                ascendancy_name = character.get("ascendancy", "")
                class_id = get_class_id(class_name)
                ascendancy_id = get_ascendancy_id(class_name, ascendancy_name)
                
                # Convert hashes using headless PoB
                print(f"Converting {len(all_hashes)} passive hashes for {class_name}/{ascendancy_name}...")
                result = convert_passive_hashes(
                    all_hashes,
                    tree_version="3_29",  # Should match build's tree version
                    class_id=class_id,
                    ascendancy_id=ascendancy_id
                )
                
                if result.get("totalValid", 0) > 0:
                    # Build nodes string for PoB format
                    valid_hashes = result["validNodes"]
                    cluster_hashes = result["clusterNodes"]
                    
                    # Main nodes (regular)
                    nodes_str = ",".join(str(h) for h in valid_hashes)
                    
                    # Mastery effects
                    mastery_effects = passives.get("mastery_effects", [])
                    mastery_str = ",".join(f"{{{m},{e}}}" for m, e in mastery_effects)
                    
                    # Create new Spec entry for Tree
                    tree_section = build.setdefault('Tree', {})
                    spec_list = tree_section.setdefault('Spec', [])
                    
                    new_spec = {
                        "_attr": {
                            "ascendClassId": str(ascendancy_id),
                            "classId": str(class_id),
                            "clusterHashFormatVersion": "2",
                            "masteryEffects": mastery_str,
                            "nodes": nodes_str
                        },
                        "_elem": "Spec",
                        "Overrides": {
                            "_attr": [],
                            "_elem": "Overrides"
                        },
                        "Sockets": {
                            "_attr": [],
                            "_elem": "Sockets"
                        },
                        "URL": {
                            "_attr": [],
                            "_elem": "URL",
                            "_text": ""
                        }
                    }
                    
                    # Add cluster jewel sockets if any
                    if cluster_hashes:
                        for cluster_hash in cluster_hashes:
                            socket = {
                                "_attr": {
                                    "itemId": "0",
                                    "nodeId": str(cluster_hash)
                                },
                                "_elem": "Socket"
                            }
                            new_spec.setdefault("Sockets", {"_attr": [], "_elem": "Sockets"}).setdefault("_attr", []).append(socket)
                    
                    spec_list.append(new_spec)
                    print(f"Added passive tree spec for loadout {loadout_id} ({len(valid_hashes)} nodes)")
    
    return build


# ============================================================
# Full Pipeline: OAuth → Character → Loadout
# ============================================================

def import_character_to_build(
    build_path: str,
    character_name: str,
    output_path: str,
    realm: str = "pc",
    loadout_title: str = None,
    access_token: str = None,
    refresh_token: str = None
):
    """
    Full pipeline: Load build, fetch character via OAuth, add as loadout, save.
    """
    # Load existing build
    if build_path.endswith('.build'):
        # Need to export to JSON first
        from pob_collab import export_build
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            export_build(build_path, tmp.name)
            with open(tmp.name, 'r') as f:
                build = json.load(f)
    else:
        with open(build_path, 'r') as f:
            build = json.load(f)
    
    # Fetch character (simplified - would use PoEAPIClient in real use)
    if access_token:
        from pob_oauth_import import PoEAPIClient
        client = PoEAPIClient(access_token=access_token, refresh_token=refresh_token)
        character = client.get_character(character_name, realm)
        if not character:
            raise ValueError(f"Character {character_name} not found")
    else:
        # Assume character data passed directly
        character = character_name  # Would be dict in real use
    
    if loadout_title is None:
        loadout_title = f"{character['name']} ({character['class']} Lv{character['level']})"
    
    # Add loadout
    build = add_character_loadout(build, character, loadout_title)
    
    # Save as JSON
    with open(output_path.replace('.build', '.json'), 'w') as f:
        json.dump(build, f, indent=2)
    
    # Convert back to .build
    from pob_collab import import_build
    import_build(output_path.replace('.build', '.json'), output_path)
    
    print(f"✅ Added loadout '{loadout_title}' (ID: {loadout_id}) to {output_path}")


# ============================================================
# Example Usage
# ============================================================

if __name__ == "__main__":
    # Demo: Load build, show structure
    with open('/tmp/earthshatter_berserker.json', 'r') as f:
        build = json.load(f)
    
    print("Current loadouts:")
    for ss in build.get('Skills', {}).get('SkillSet', []):
        print(f"  {ss['_attr']['id']}: {ss['_attr']['title']}")
    
    # Simulate adding a character (would need real character data)
    print("\nTo add a character loadout:")
    print("  1. Fetch character via OAuth (pob_oauth_import.py)")
    print("  2. Call add_character_loadout(build, character, 'My Char')")
    print("  3. Save JSON and import_build() back to .build")