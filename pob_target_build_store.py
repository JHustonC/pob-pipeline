#!/usr/bin/env python3
"""
Target Build Store
===================
Flexible storage for target/end-game builds. Supports multiple builds,
easy editing, versioning, and integration with the pipeline.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path


# Default storage location
DEFAULT_STORE_PATH = Path.home() / ".pob_pipeline" / "target_builds.json"


@dataclass
class TargetItem:
    """Target item for a specific slot."""
    slot: str
    base_type: str
    target_ilvl: int = 86
    target_rarity: str = "Rare"  # Rare, Unique
    target_mods: List[str] = field(default_factory=list)
    target_influences: Dict[str, bool] = field(default_factory=dict)
    target_unique_name: Optional[str] = None  # If unique
    crafting_priority: str = "Medium"  # High, Medium, Low
    notes: str = ""


@dataclass
class TargetBuild:
    """Complete target/end-game build configuration."""
    id: str
    name: str
    description: str
    character_class: str
    ascendancy: str
    target_level: int = 100
    target_league: str = "Settlers"
    main_skill: str = ""
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    items: List[TargetItem] = field(default_factory=list)
    passive_tree_goals: List[str] = field(default_factory=list)  # e.g., "Add 20% more life"
    config_overrides: Dict[str, Any] = field(default_factory=dict)  # Pantheon, bandit, etc.
    tags: List[str] = field(default_factory=list)  # "budget", "minmax", "hc", "bossing"


class TargetBuildStore:
    """Manages target builds with JSON persistence."""
    
    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = store_path or DEFAULT_STORE_PATH
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, TargetBuild] = {}
        self._load()
    
    def _load(self):
        """Load builds from JSON file."""
        if self.store_path.exists():
            try:
                with open(self.store_path, 'r') as f:
                    data = json.load(f)
                for build_id, build_data in data.items():
                    # Convert items back to TargetItem objects
                    items = [TargetItem(**item) for item in build_data.get("items", [])]
                    build_data["items"] = items
                    self._data[build_id] = TargetBuild(**build_data)
            except Exception as e:
                print(f"Warning: Failed to load target builds: {e}")
                self._data = {}
    
    def _save(self):
        """Save builds to JSON file."""
        # Convert to serializable dict
        serializable = {}
        for build_id, build in self._data.items():
            d = asdict(build)
            # TargetItem objects are already dicts via asdict
            serializable[build_id] = d
        
        with open(self.store_path, 'w') as f:
            json.dump(serializable, f, indent=2)
    
    # CRUD Operations
    def create(self, build: TargetBuild) -> str:
        """Create a new target build."""
        if build.id in self._data:
            raise ValueError(f"Build with id '{build.id}' already exists")
        self._data[build.id] = build
        self._save()
        return build.id
    
    def get(self, build_id: str) -> Optional[TargetBuild]:
        """Get a target build by ID."""
        return self._data.get(build_id)
    
    def update(self, build: TargetBuild) -> bool:
        """Update an existing target build."""
        if build.id not in self._data:
            return False
        build.updated_at = datetime.now().isoformat()
        build.version += 1
        self._data[build.id] = build
        self._save()
        return True
    
    def delete(self, build_id: str) -> bool:
        """Delete a target build."""
        if build_id not in self._data:
            return False
        del self._data[build_id]
        self._save()
        return True
    
    def list_all(self) -> List[TargetBuild]:
        """List all target builds, sorted by updated_at desc."""
        return sorted(self._data.values(), key=lambda b: b.updated_at, reverse=True)
    
    def list_by_tag(self, tag: str) -> List[TargetBuild]:
        """List builds with a specific tag."""
        return [b for b in self._data.values() if tag in b.tags]
    
    def duplicate(self, build_id: str, new_id: str, new_name: str) -> Optional[TargetBuild]:
        """Duplicate a build with new ID and name."""
        original = self.get(build_id)
        if not original:
            return None
        
        new_build = TargetBuild(
            id=new_id,
            name=new_name,
            description=f"Copy of {original.name}",
            character_class=original.character_class,
            ascendancy=original.ascendancy,
            target_level=original.target_level,
            target_league=original.target_league,
            main_skill=original.main_skill,
            items=[TargetItem(**asdict(item)) for item in original.items],
            passive_tree_goals=original.passive_tree_goals.copy(),
            config_overrides=original.config_overrides.copy(),
            tags=original.tags.copy()
        )
        self.create(new_build)
        return new_build
    
    # Item management
    def add_item(self, build_id: str, item: TargetItem) -> bool:
        """Add a target item to a build."""
        build = self.get(build_id)
        if not build:
            return False
        # Check if slot already exists
        for i, existing in enumerate(build.items):
            if existing.slot == item.slot:
                build.items[i] = item
                build.updated_at = datetime.now().isoformat()
                self._save()
                return True
        build.items.append(item)
        build.updated_at = datetime.now().isoformat()
        self._save()
        return True
    
    def remove_item(self, build_id: str, slot: str) -> bool:
        """Remove a target item from a build."""
        build = self.get(build_id)
        if not build:
            return False
        build.items = [i for i in build.items if i.slot != slot]
        build.updated_at = datetime.now().isoformat()
        self._save()
        return True
    
    def get_item(self, build_id: str, slot: str) -> Optional[TargetItem]:
        """Get a specific target item."""
        build = self.get(build_id)
        if not build:
            return None
        for item in build.items:
            if item.slot == slot:
                return item
        return None
    
    # Import/Export
    def export(self, build_id: str, export_path: Path) -> bool:
        """Export a build to a JSON file."""
        build = self.get(build_id)
        if not build:
            return False
        
        export_data = {build_id: asdict(build)}
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        return True
    
    def import_build(self, import_path: Path) -> bool:
        """Import a build from a JSON file."""
        try:
            with open(import_path, 'r') as f:
                data = json.load(f)
            
            for build_id, build_data in data.items():
                items = [TargetItem(**item) for item in build_data.get("items", [])]
                build_data["items"] = items
                build = TargetBuild(**build_data)
                self._data[build.id] = build
            
            self._save()
            return True
        except Exception as e:
            print(f"Failed to import build: {e}")
            return False


# Pre-built templates for common end-game builds
def create_earthshatter_berserker_template() -> TargetBuild:
    """Create the Earthshatter Berserker end-game template."""
    items = [
        TargetItem(
            slot="Weapon 1",
            base_type="Vaal Axe",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "180%+ increased Physical Damage",
                "25%+ increased Attack Speed",
                "+2 to Level of Socketed Melee Gems",
                "Critical Strike Multiplier +",
                "Critical Strike Chance +",
                "Gain 1 Rage on Hit"
            ],
            target_influences={"warlord": True},
            crafting_priority="High",
            notes="God tier: 180%+ phys, 25%+ AS, +2 melee, crit multi/chance, warlord influence for +1 rage. Crafting: Recombinator (Flat+Hybrid Phys → %Phys+AS → combine). ~25-35 div. Tempering 8% Phys. Warlord slam for Culling/Phys if Killed."
        ),
        TargetItem(
            slot="Weapon 2 (Swap)",
            base_type="Vaal Axe",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "Perforate of Duality (Transfigured)",
                "Physical Damage +",
                "Attack Speed +",
                "Impale Chance +"
            ],
            crafting_priority="Medium",
            notes="Swap for Perforate of Duality on immunity phases. Can use lower budget axe."
        ),
        TargetItem(
            slot="Helmet",
            base_type="Royal Burgonet",
            target_ilvl=84,
            target_rarity="Unique",
            target_unique_name="Echoes of Creation",
            target_mods=[
                "Enchant: Warcry Buff Effect +",
                "Enchant: Warcry Cooldown Recovery +"
            ],
            crafting_priority="High",
            notes="Lab enchant for warcry build. Buy or run Lab for enchant. 30-50 div at league start."
        ),
        TargetItem(
            slot="Body Armour",
            base_type="Royal Plate",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "200%+ increased Armour",
                "+150+ to maximum Life",
                "+1% to all maximum Elemental Resistances",
                "Physical Damage taken as Cold/Lightning/Fire",
                "8% Physical Damage Reduction (Harvest forced)",
                "Crusader Influence: +1% max Res during Flask Effect"
            ],
            target_influences={"crusader": True},
            crafting_priority="High",
            notes="Max armour stacking with max res and phys taken as elemental. Crafting: Essence of Dread (Armour) on Royal Plate ilvl86+ → Harvest force 8% PDR → Tempering 8% Armour. Exarch/Eater influence for additional max res."
        ),
        TargetItem(
            slot="Gloves",
            base_type="Leviathan Gauntlets",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "Hits have 33% chance to ignore Enemy Physical Damage Reduction",
                "+100+ to maximum Life",
                "Attack Speed / Critical Strike mods",
                "Hunter Influence: Curse on Hit"
            ],
            target_influences={"hunter": True},
            crafting_priority="High",
            notes="Hits ignore phys reduction is key for damage. Crafting: Essence of Loathing (Attack Speed) or Contempt (Flat Phys) → Hunter influence for Curse on Hit."
        ),
        TargetItem(
            slot="Boots",
            base_type="Leviathan Greaves",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "30%+ Movement Speed",
                "5% increased Damage per Endurance Charge",
                "+100+ to maximum Life",
                "Redeemer Influence: Regen per Endurance Charge"
            ],
            target_influences={"redeemer": True},
            crafting_priority="High",
            notes="Movement speed + endurance charge scaling. Crafting: Essence of Zeal (Move Speed + Onslaught on Kill) → Redeemer influence for Regen per End Charge."
        ),
        TargetItem(
            slot="Amulet",
            base_type="Onyx Amulet",
            target_ilvl=86,
            target_rarity="Unique",
            target_unique_name="Ashes of the Stars",
            target_mods=[
                "+1 Level to All Skill Gems",
                "+2% to Quality of All Skill Gems",
                "Attribute Scaling"
            ],
            crafting_priority="High",
            notes="+1 gem level is massive for Earthshatter. Trade only (~150 div). Budget: Rare Onyx with +1 Skill, Attributes, Life."
        ),
        TargetItem(
            slot="Belt",
            base_type="Heavy Belt",
            target_ilvl=86,
            target_rarity="Unique",
            target_unique_name="Mageblood",
            target_mods=[
                "4 Flask Effects",
                "Life/Resistances during Flask Effect",
                "Magic Utility Flasks have 50% increased Effect"
            ],
            crafting_priority="High",
            notes="Best belt for flask builds - trade only (~200 div). Budget: Rare Stygian Vise with Flask Effect Duration, Life, Res."
        ),
        TargetItem(
            slot="Ring 1",
            base_type="Diamond Ring",
            target_ilvl=86,
            target_rarity="Unique",
            target_unique_name="Circle of Guilt",
            target_mods=[
                "Critical Strike Multiplier +",
                "Critical Strike Chance +",
                "Life / Resistances"
            ],
            crafting_priority="High",
            notes="Circle of Guilt for crit scaling (~60 div). Budget: Rare Diamond with Crit Multi/Chance, Life, Res."
        ),
        TargetItem(
            slot="Ring 2",
            base_type="Diamond Ring",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "Critical Strike Multiplier +",
                "Critical Strike Chance +",
                "Life / Resistances",
                "Elemental Damage with Attacks"
            ],
            target_influences={"shaper": True},
            crafting_priority="Medium",
            notes="Shaper ring for ele damage with attacks. Crafting: Essence of Loathing → Shaper influence."
        ),
        TargetItem(
            slot="Flask 1",
            base_type="Divine Life Flask",
            target_rarity="Magic",
            target_mods=["Staunching (Bleed Immune)", "Enduring"],
            crafting_priority="High",
            notes="Bleed immune + Enduring for sustain"
        ),
        TargetItem(
            slot="Flask 2",
            base_type="Mana Flask",
            target_rarity="Magic",
            target_mods=["Enduring", "Surgeon's"],
            crafting_priority="High",
            notes="Enduring for mana sustain at full"
        ),
        TargetItem(
            slot="Flask 3",
            base_type="Quicksilver Flask",
            target_rarity="Magic",
            target_mods=["Adrenaline", "Warding"],
            crafting_priority="High",
            notes="Adrenaline for speed, Warding for curse immune"
        ),
        TargetItem(
            slot="Flask 4",
            base_type="Silver Flask",
            target_rarity="Magic",
            target_mods=["Heat", "Warding"],
            crafting_priority="High",
            notes="T17 ele res + curse immune"
        ),
        TargetItem(
            slot="Flask 5",
            base_type="Ruby/Topaz/Sapphire Flask",
            target_rarity="Magic",
            target_mods=["Heat", "Warding"],
            crafting_priority="Medium",
            notes="T17 max ele res"
        ),
        TargetItem(
            slot="Cluster Jewel 1 (Medium)",
            base_type="Medium Cluster Jewel",
            target_rarity="Rare",
            target_mods=[
                "Mob Mentality (Endurance + Frenzy on Warcry)",
                "Warning Call (100% Inc Armour)",
                "2 passive skills"
            ],
            crafting_priority="High",
            notes="Delirium 4-passive or Harvest Reforge. Mob Mentality + Warning Call core."
        ),
        TargetItem(
            slot="Cluster Jewel 2 (Medium)",
            base_type="Medium Cluster Jewel",
            target_rarity="Rare",
            target_mods=[
                "Mob Mentality (Endurance + Frenzy on Warcry)",
                "Lead By Example (Onslaught on Crit)",
                "2 passive skills"
            ],
            crafting_priority="High",
            notes="Delirium 4-passive. Lead By Example for perma Onslaught."
        ),
        TargetItem(
            slot="Cluster Jewel 3 (Small)",
            base_type="Small Cluster Jewel",
            target_rarity="Rare",
            target_mods=[
                "Lead By Example (Onslaught on Crit)"
            ],
            crafting_priority="Medium",
            notes="Delirium 2-passive for Onslaught uptime"
        ),
        TargetItem(
            slot="Jewel 1",
            base_type="Viridian Jewel",
            target_rarity="Unique",
            target_unique_name="Impossible Escape",
            crafting_priority="High",
            notes="Allows notable allocation without pathing"
        ),
        TargetItem(
            slot="Jewel 2",
            base_type="Viridian Jewel",
            target_rarity="Unique",
            target_unique_name="Stormshroud",
            crafting_priority="Medium",
            notes="Physical as Cold for defence"
        ),
    ]

    return TargetBuild(
        id="earthshatter_berserker_god_tier",
        name="Earthshatter Berserker - God Tier (3.30 Covens of Umbra)",
        description="Min-maxed Earthshatter Berserker for Uber boss farming. Uses Perforate of Duality swap for immunity phases. 3.30: Covens of Umbra - Fate bossing, Threads juicing, Wickerman Viscera.",
        character_class="Marauder",
        ascendancy="Berserker",
        target_level=100,
        target_league="Settlers",
        main_skill="Earthshatter / Perforate of Duality (swap)",
        items=items,
        passive_tree_goals=[
            "Allocate all life/armour nodes",
            "Maximize warcry effect nodes (Mob Mentality clusters)",
            "Get Rage mastery + Warcry mastery (10 min power, rage gen)",
            "Divine Shield for ES from armour",
            "Armour Mastery for +1% max res",
            "Fortify Mastery (replace Fortify Support)",
            "Fist of War Support from Act 4",
            "Overexertion + Autoexertion for 6 exerts on Intimidating Cry",
            "Disciple of the Unyielding + Endurance charge nodes early",
            "Bastion Breaker + Overwhelm mastery for bossing"
        ],
        config_overrides={
            "pantheonMajorGod": "Lunaris",
            "pantheonMinorGod": "Tukohama",
            "bandit": "Kill All",
            "warcry_quality": {
                "Intimidating Cry": 20,
                "Infernal Cry": 13,
                "Seismic Cry": 20,
                "Rallying Cry": 13,
                "Enduring Cry": 20,
                "General's Cry": 20
            }
        },
        tags=["minmax", "uber-bossing", "earthshatter", "berserker", "3.30", "covens-of-umbra"]
    )


def create_earthshatter_berserker_mid_tier() -> TargetBuild:
    """Mid-tier Earthshatter Berserker (~150-200 div). Solid upgrades from budget, not quite god-tier."""
    mid_build = create_earthshatter_berserker_template()
    mid_build.id = "earthshatter_berserker_mid_tier"
    mid_build.name = "Earthshatter Berserker - Mid Tier (3.30 Covens of Umbra)"
    mid_build.description = "Mid-tier version with key upgrades. ~150-200 div total. Strong bossing, good tankiness."
    mid_build.tags = ["mid-tier", "earthshatter", "berserker", "3.30", "covens-of-umbra"]
    
    # Keep some uniques, upgrade others
    for item in mid_build.items:
        # Weapon: Still rare but better crafted (~1200 pDPS)
        if item.slot == "Weapon 1":
            item.target_mods = [
                "150%+ increased Physical Damage",
                "22%+ increased Attack Speed",
                "+2 to Level of Socketed Melee Gems",
                "Critical Strike Multiplier +",
                "Critical Strike Chance +",
                "Gain 1 Rage on Hit"
            ]
            item.notes = "Mid tier: 1200+ pDPS. Recombinator craft. ~20-30 div."
        elif item.slot == "Helmet":
            item.target_rarity = "Unique"
            item.target_unique_name = "Echoes of Creation"
            item.target_mods = [
                "Enchant: Warcry Buff Effect +",
                "Enchant: Warcry Cooldown Recovery +"
            ]
            item.notes = "Echoes of Creation (30-50 div). Lab enchant for warcry."
        elif item.slot == "Body Armour":
            item.target_mods = [
                "180%+ increased Armour",
                "+130+ to maximum Life",
                "+1% to all maximum Elemental Resistances",
                "Physical Damage taken as Cold/Lightning/Fire",
                "8% Physical Damage Reduction (Harvest forced)",
                "Crusader Influence: +1% max Res during Flask Effect"
            ]
            item.target_influences = {"crusader": True}
            item.notes = "Mid tier: 2500+ Armour, 8% PDR. Crusader influence for max res."
        elif item.slot == "Gloves":
            item.target_mods = [
                "Hits have 33% chance to ignore Enemy Physical Damage Reduction",
                "+90+ to maximum Life",
                "Attack Speed / Critical Strike mods",
                "Hunter Influence: Curse on Hit"
            ]
            item.target_influences = {"hunter": True}
            item.notes = "Hunter influence for Curse on Hit. Ignore phys reduct key for damage."
        elif item.slot == "Boots":
            item.target_mods = [
                "30%+ Movement Speed",
                "5% increased Damage per Endurance Charge",
                "+90+ to maximum Life",
                "Redeemer Influence: Regen per Endurance Charge"
            ]
            item.target_influences = {"redeemer": True}
            item.notes = "Redeemer for Endurance Charge regen. Move speed + endurance scaling."
        elif item.slot == "Amulet":
            item.target_rarity = "Unique"
            item.target_unique_name = "Ashes of the Stars"
            item.target_mods = [
                "+1 Level to All Skill Gems",
                "+2% to Quality of All Skill Gems",
                "Attribute Scaling"
            ]
            item.notes = "+1 gem level massive for Earthshatter. Trade only (~150 div)."
        elif item.slot == "Belt":
            item.target_rarity = "Unique"
            item.target_unique_name = "Mageblood"
            item.target_mods = [
                "4 Flask Effects",
                "Life/Resistances during Flask Effect",
                "Magic Utility Flasks have 50% increased Effect"
            ]
            item.notes = "Best flask belt. Trade only (~200 div)."
        elif item.slot == "Ring 1":
            item.target_rarity = "Unique"
            item.target_unique_name = "Circle of Guilt"
            item.target_mods = [
                "Critical Strike Multiplier +",
                "Critical Strike Chance +",
                "Life / Resistances"
            ]
            item.notes = "Circle of Guilt for crit scaling (~60 div)."
        elif item.slot == "Ring 2":
            item.target_rarity = "Rare"
            item.target_mods = [
                "Critical Strike Multiplier +",
                "Critical Strike Chance +",
                "Life / Resistances",
                "Elemental Damage with Attacks"
            ]
            item.target_influences = {"shaper": True}
            item.notes = "Shaper ring for ele damage with attacks."
    
    return mid_build


def create_facebreaker_luminary_budget() -> TargetBuild:
    """Budget Facebreaker Luminary (~30-50 div). League starter friendly."""
    items = [
        TargetItem(
            slot="Weapon 1",
            base_type="Facebreakers",
            target_ilvl=1,
            target_rarity="Unique",
            target_unique_name="Facebreakers",
            target_mods=[
                "Unarmed attacks count as using Main Hand Weapon",
                "Unarmed attacks count as using Off Hand Weapon",
                "Physical Damage +"
            ],
            crafting_priority="High",
            notes="Core unique. ~5-10 div. Get best roll possible on physical damage."
        ),
        TargetItem(
            slot="Weapon 2",
            base_type="Shield",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "Life +",
                "Resistances +",
                "Block Chance +",
                "Spell Block Chance +"
            ],
            crafting_priority="High",
            notes="Shield for block. Craft Life + Res + Block. ~5-10 div."
        ),
        TargetItem(
            slot="Helmet",
            base_type="Royal Burgonet",
            target_ilvl=84,
            target_rarity="Unique",
            target_unique_name="Fowlorn",
            target_mods=[
                "War Cry Cooldown Recovery Speed +",
                "Life +",
                "Resistances +"
            ],
            crafting_priority="High",
            notes="Fowlorn for War Cry CDR. ~10-15 div. Alt: Rare with Essence of Horror (Crit Reduction) + Lab enchant."
        ),
        TargetItem(
            slot="Body Armour",
            base_type="Royal Plate",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "Life +",
                "Armour +",
                "Resistances +",
                "Physical Damage Reduction +"
            ],
            crafting_priority="High",
            notes="Essence of Dread (Armour) on Royal Plate ilvl86+. Harvest force PDR. ~10-20 div."
        ),
        TargetItem(
            slot="Gloves",
            base_type="Leviathan Gauntlets",
            target_ilvl=86,
            target_rarity="Unique",
            target_unique_name="Deep Breaths Anoint",
            target_mods=[
                "Anoint: Deep Breaths",
                "Life +",
                "Resistances +"
            ],
            crafting_priority="High",
            notes="Deep Breaths anoint for CDR + AoE. ~15-25 div. Alt: Rare with Essence of Loathing (Attack Speed)."
        ),
        TargetItem(
            slot="Boots",
            base_type="Leviathan Greaves",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "Life +",
                "Resistances +",
                "Movement Speed +",
                "Onslaught on Kill"
            ],
            crafting_priority="High",
            notes="Essence of Zeal (Move Speed + Onslaught). ~5-10 div."
        ),
        TargetItem(
            slot="Amulet",
            base_type="Onyx Amulet",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "Flat Physical Damage to Attacks +",
                "Life +",
                "Resistances +",
                "Attribute Requirements -"
            ],
            crafting_priority="Critical",
            notes="CRITICAL: Flat Phys on amulet is the difference between 0 damage and killing white mobs when Rallying Cry drops. Harvest/Beast craft. ~10-20 div."
        ),
        TargetItem(
            slot="Belt",
            base_type="Stygian Vise",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "Flask Effect Duration +",
                "Life +",
                "Resistances +",
                "Flask Charges gained +"
            ],
            crafting_priority="High",
            notes="Stygian Vise for Abyssal Jewel. Flask Duration + Life/Res. ~5-10 div."
        ),
        TargetItem(
            slot="Ring 1",
            base_type="Diamond Ring",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "Life +",
                "Resistances +",
                "Elemental Damage with Attacks +"
            ],
            crafting_priority="Medium",
            notes="Rare Diamond with Life/Res/Ele Damage. ~5 div."
        ),
        TargetItem(
            slot="Ring 2",
            base_type="Diamond Ring",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "Life +",
                "Resistances +",
                "Elemental Damage with Attacks +"
            ],
            crafting_priority="Medium",
            notes="Rare Diamond with Life/Res/Ele Damage. ~5 div."
        ),
        TargetItem(
            slot="Belt",
            base_type="Cord Belt",
            target_ilvl=86,
            target_rarity="Unique",
            target_unique_name="Cord Belt",
            target_mods=[],
            crafting_priority="Medium",
            notes="Cord Belt back in 3.30. Better than Stygian for this build. ~5 div."
        ),
        TargetItem(
            slot="Cluster Jewel 1 (Medium)",
            base_type="Medium Cluster Jewel",
            target_rarity="Rare",
            target_mods=[
                "Mob Mentality (Endurance + Frenzy on Warcry)",
                "Warning Call (100% Inc Armour)",
                "2 passive skills"
            ],
            crafting_priority="High",
            notes="Delirium 4-passive. Mob Mentality + Warning Call core."
        ),
        TargetItem(
            slot="Cluster Jewel 2 (Medium)",
            base_type="Medium Cluster Jewel",
            target_rarity="Rare",
            target_mods=[
                "Mob Mentality (Endurance + Frenzy on Warcry)",
                "Lead By Example (Onslaught on Crit)",
                "2 passive skills"
            ],
            crafting_priority="High",
            notes="Delirium 4-passive. Lead By Example for perma Onslaught."
        ),
        TargetItem(
            slot="Cluster Jewel 3 (Small)",
            base_type="Small Cluster Jewel",
            target_rarity="Rare",
            target_mods=[
                "Lead By Example (Onslaught on Crit)"
            ],
            crafting_priority="Medium",
            notes="Delirium 2-passive for Onslaught uptime."
        ),
        TargetItem(
            slot="Jewel 1",
            base_type="Viridian Jewel",
            target_rarity="Unique",
            target_unique_name="Impossible Escape",
            crafting_priority="High",
            notes="Allows notable allocation without pathing. ~10 div."
        ),
        TargetItem(
            slot="Jewel 2",
            base_type="Viridian Jewel",
            target_rarity="Rare",
            target_mods=[
                "Life +",
                "Damage with Attacks +",
                "Resistances +"
            ],
            crafting_priority="Medium",
            notes="Budget: Rare Viridian with Life + Damage. ~2 div."
        ),
    ]

    return TargetBuild(
        id="facebreaker_luminary_budget",
        name="Facebreaker Luminary - Budget (3.30 Covens of Umbra)",
        description="Budget Facebreaker Luminary league starter. ~30-50 div total. Uses Mercenary Rallying Cry for warcries. Seamless swap from 2H axe Earthshatter.",
        character_class="Scion",
        ascendancy="Luminary",
        target_level=100,
        target_league="Settlers",
        main_skill="Earthshatter (Facebreaker + Merc Rallying Cry)",
        items=items,
        passive_tree_goals=[
            "Start Scion → Ascendant → Slayer → Saboteur → Luminary",
            "Resolute Technique (keystone) - ignore accuracy/evade",
            "Block nodes (Glancing Blows + Shield Mastery)",
            "Armour + Life nodes",
            "Warcry Effect nodes (Mob Mentality clusters)",
            "Endurance Charge generation (Mob Mentality + Disciple of the Unyielding)",
            "Block Mastery (Glancing Blows + Shield Mastery)",
            "Armour Mastery for +1% max res",
            "Fortify Mastery",
            "Bastion Breaker for Overwhelm"
        ],
        config_overrides={
            "pantheonMajorGod": "Lunaris",
            "pantheonMinorGod": "Tukohama",
            "bandit": "Kill All",
            "warcry_quality": {
                "Rallying Cry": 20,
                "Intimidating Cry": 20,
                "Seismic Cry": 20,
                "Enduring Cry": 20,
                "Infernal Cry": 13,
                "General's Cry": 20
            }
        },
        tags=["budget", "luminary", "facebreaker", "earthshatter", "3.30", "covens-of-umbra", "league-starter"]
    )


def create_facebreaker_luminary_mid_tier() -> TargetBuild:
    """Mid-tier Facebreaker Luminary (~150-200 div). Upgrades from budget with better uniques."""
    items = [
        TargetItem(
            slot="Weapon 1",
            base_type="Facebreakers",
            target_ilvl=1,
            target_rarity="Unique",
            target_unique_name="Facebreakers",
            target_mods=["+2 to Level of Socketed Melee Gems", "Physical Damage +"],
            crafting_priority="High",
            notes="Best roll Facebreakers (+2 gems, high phys). ~30-50 div."
        ),
        TargetItem(
            slot="Weapon 2",
            base_type="The Anvil",
            target_ilvl=86,
            target_rarity="Unique",
            target_unique_name="The Anvil",
            target_mods=["Life +", "Armour +", "Block Chance +", "Spell Block Chance +"],
            crafting_priority="High",
            notes="The Anvil for massive armour + block. ~20-30 div."
        ),
        TargetItem(
            slot="Helmet",
            base_type="Royal Burgonet",
            target_ilvl=84,
            target_rarity="Unique",
            target_unique_name="Fowlorn",
            target_mods=["War Cry Cooldown Recovery Speed +", "Life +", "Resistances +"],
            crafting_priority="High",
            notes="Fowlorn with good War Cry CDR roll. ~20 div."
        ),
        TargetItem(
            slot="Body Armour",
            base_type="Royal Plate",
            target_ilvl=86,
            target_rarity="Unique",
            target_unique_name="The Fourth Vow",
            target_mods=["Life +", "Armour +", "Resistances +", "Physical Damage Reduction +"],
            crafting_priority="High",
            notes="The Fourth Vow for Phys as Cold + Armour. ~30 div."
        ),
        TargetItem(
            slot="Gloves",
            base_type="Leviathan Gauntlets",
            target_ilvl=86,
            target_rarity="Unique",
            target_unique_name="Deep Breaths Anoint",
            target_mods=["Anoint: Deep Breaths", "Life +", "Resistances +"],
            crafting_priority="High",
            notes="Deep Breaths anoint (CDR + AoE). ~25 div."
        ),
        TargetItem(
            slot="Boots",
            base_type="Leviathan Greaves",
            target_ilvl=86,
            target_rarity="Unique",
            target_unique_name="Ralakesh's Impatience",
            target_mods=["Life +", "Resistances +", "Movement Speed +", "Cannot be Stunned if you've been Hit Recently"],
            crafting_priority="High",
            notes="Ralakesh's for perma onslaught + stun immune. ~30 div."
        ),
        TargetItem(
            slot="Amulet",
            base_type="Onyx Amulet",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "Flat Physical Damage to Attacks + (T1)",
                "Life + (T1)",
                "Resistances + (T1)",
                "Attribute Requirements -"
            ],
            crafting_priority="Critical",
            notes="T1 Flat Phys + T1 Life. Harvest/Beast craft. ~50 div."
        ),
        TargetItem(
            slot="Belt",
            base_type="Cord Belt",
            target_ilvl=86,
            target_rarity="Unique",
            target_unique_name="Cord Belt",
            target_mods=[],
            crafting_priority="Medium",
            notes="Cord Belt for flask effect. ~10 div."
        ),
        TargetItem(
            slot="Ring 1",
            base_type="Diamond Ring",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "Life + (T1)",
                "Resistances + (T1)",
                "Elemental Damage with Attacks + (T1)",
                "Physical Damage +"
            ],
            crafting_priority="Medium",
            notes="T1 Life/Res/Ele Dmg. ~15 div."
        ),
        TargetItem(
            slot="Ring 2",
            base_type="Diamond Ring",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "Life + (T1)",
                "Resistances + (T1)",
                "Elemental Damage with Attacks + (T1)",
                "Physical Damage +"
            ],
            crafting_priority="Medium",
            notes="T1 Life/Res/Ele Dmg. ~15 div."
        ),
        TargetItem(
            slot="Cluster Jewel 1 (Medium)",
            base_type="Medium Cluster Jewel",
            target_rarity="Rare",
            target_mods=[
                "Mob Mentality (Endurance + Frenzy on Warcry)",
                "Warning Call (100% Inc Armour)",
                "2 passive skills"
            ],
            crafting_priority="High",
            notes="Delirium 4-passive. Mob Mentality + Warning Call core."
        ),
        TargetItem(
            slot="Cluster Jewel 2 (Medium)",
            base_type="Medium Cluster Jewel",
            target_rarity="Rare",
            target_mods=[
                "Mob Mentality (Endurance + Frenzy on Warcry)",
                "Lead By Example (Onslaught on Crit)",
                "2 passive skills"
            ],
            crafting_priority="High",
            notes="Delirium 4-passive. Lead By Example for perma Onslaught."
        ),
        TargetItem(
            slot="Cluster Jewel 3 (Small)",
            base_type="Small Cluster Jewel",
            target_rarity="Rare",
            target_mods=[
                "Lead By Example (Onslaught on Crit)"
            ],
            crafting_priority="Medium",
            notes="Delirium 2-passive for Onslaught uptime."
        ),
        TargetItem(
            slot="Jewel 1",
            base_type="Viridian Jewel",
            target_rarity="Unique",
            target_unique_name="Impossible Escape",
            crafting_priority="High",
            notes="Impossible Escape. ~15 div."
        ),
        TargetItem(
            slot="Jewel 2",
            base_type="Viridian Jewel",
            target_rarity="Rare",
            target_mods=["Life + (T1)", "Damage with Attacks + (T1)", "Resistances +"],
            crafting_priority="Medium",
            notes="T1 Life + Damage. ~10 div."
        ),
    ]

    return TargetBuild(
        id="facebreaker_luminary_mid_tier",
        name="Facebreaker Luminary - Mid Tier (3.30 Covens of Umbra)",
        description="Mid-tier Facebreaker Luminary with key unique upgrades. ~150-200 div total. Strong tankiness, good damage.",
        character_class="Scion",
        ascendancy="Luminary",
        target_level=100,
        target_league="Settlers",
        main_skill="Earthshatter (Facebreaker + Merc Rallying Cry)",
        items=items,
        passive_tree_goals=[
            "Start Scion → Ascendant → Slayer → Saboteur → Luminary",
            "Resolute Technique (keystone) - ignore accuracy/evade",
            "Block nodes (Glancing Blows + Shield Mastery)",
            "Armour + Life nodes",
            "Warcry Effect nodes (Mob Mentality clusters)",
            "Endurance Charge generation (Mob Mentality + Disciple of the Unyielding)",
            "Block Mastery (Glancing Blows + Shield Mastery)",
            "Armour Mastery for +1% max res",
            "Fortify Mastery",
            "Bastion Breaker for Overwhelm"
        ],
        config_overrides={
            "pantheonMajorGod": "Lunaris",
            "pantheonMinorGod": "Tukohama",
            "bandit": "Kill All",
            "warcry_quality": {
                "Rallying Cry": 20,
                "Intimidating Cry": 20,
                "Seismic Cry": 20,
                "Enduring Cry": 20,
                "Infernal Cry": 13,
                "General's Cry": 20
            }
        },
        tags=["mid-tier", "luminary", "facebreaker", "earthshatter", "3.30", "covens-of-umbra"]
    )


def create_facebreaker_luminary_god_tier() -> TargetBuild:
    """God-tier Facebreaker Luminary (~500+ div). Mirror-tier version."""
    items = [
        TargetItem(
            slot="Weapon 1",
            base_type="Facebreakers",
            target_ilvl=1,
            target_rarity="Unique",
            target_unique_name="Facebreakers",
            target_mods=["+2 to Level of Socketed Melee Gems", "Physical Damage + (T1)"],
            crafting_priority="High",
            notes="Mirror-tier Facebreakers (+2 gems, T1 phys). ~200+ div."
        ),
        TargetItem(
            slot="Weapon 2",
            base_type="Aegis Aurora",
            target_ilvl=86,
            target_rarity="Unique",
            target_unique_name="Aegis Aurora",
            target_mods=["Energy Shield +", "Armour +", "Block Chance +", "Spell Block Chance +"],
            crafting_priority="High",
            notes="Aegis Aurora for ES on block. ~50 div."
        ),
        TargetItem(
            slot="Helmet",
            base_type="Royal Burgonet",
            target_ilvl=84,
            target_rarity="Unique",
            target_unique_name="Fowlorn",
            target_mods=["War Cry Cooldown Recovery Speed + (T1)", "Life +", "Resistances +"],
            crafting_priority="High",
            notes="Perfect roll Fowlorn. ~50 div."
        ),
        TargetItem(
            slot="Body Armour",
            base_type="Royal Plate",
            target_ilvl=86,
            target_rarity="Unique",
            target_unique_name="The Fourth Vow",
            target_mods=["Life +", "Armour +", "Resistances +", "Physical Damage taken as Cold +"],
            crafting_priority="High",
            notes="The Fourth Vow for Phys as Cold + massive Armour. ~80 div."
        ),
        TargetItem(
            slot="Gloves",
            base_type="Leviathan Gauntlets",
            target_ilvl=86,
            target_rarity="Unique",
            target_unique_name="Deep Breaths Anoint",
            target_mods=["Anoint: Deep Breaths", "Life +", "Resistances +"],
            crafting_priority="High",
            notes="Perfect Deep Breaths anoint. ~40 div."
        ),
        TargetItem(
            slot="Boots",
            base_type="Leviathan Greaves",
            target_ilvl=86,
            target_rarity="Unique",
            target_unique_name="Ralakesh's Impatience",
            target_mods=["Life +", "Resistances +", "Movement Speed +", "Cannot be Stunned"],
            crafting_priority="High",
            notes="Ralakesh's Impatience. ~50 div."
        ),
        TargetItem(
            slot="Amulet",
            base_type="Onyx Amulet",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "Flat Physical Damage to Attacks + (T1)",
                "Life + (T1)",
                "Resistances + (T1)",
                "Attribute Requirements -"
            ],
            crafting_priority="Critical",
            notes="Mirror-tier T1 Flat Phys + T1 Life + T1 Res. ~200 div."
        ),
        TargetItem(
            slot="Belt",
            base_type="Cord Belt",
            target_ilvl=86,
            target_rarity="Unique",
            target_unique_name="Cord Belt",
            target_mods=[],
            crafting_priority="Medium",
            notes="Cord Belt. ~20 div."
        ),
        TargetItem(
            slot="Ring 1",
            base_type="Diamond Ring",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "Life + (T1)",
                "Resistances + (T1)",
                "Elemental Damage with Attacks + (T1)",
                "Physical Damage + (T1)"
            ],
            crafting_priority="Medium",
            notes="Quad T1. ~50 div."
        ),
        TargetItem(
            slot="Ring 2",
            base_type="Diamond Ring",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=[
                "Life + (T1)",
                "Resistances + (T1)",
                "Elemental Damage with Attacks + (T1)",
                "Physical Damage + (T1)"
            ],
            crafting_priority="Medium",
            notes="Quad T1. ~50 div."
        ),
        TargetItem(
            slot="Cluster Jewel 1 (Medium)",
            base_type="Medium Cluster Jewel",
            target_rarity="Rare",
            target_mods=[
                "Mob Mentality (Endurance + Frenzy on Warcry)",
                "Warning Call (100% Inc Armour)",
                "2 passive skills"
            ],
            crafting_priority="High",
            notes="Perfect 4-passive. ~30 div."
        ),
        TargetItem(
            slot="Cluster Jewel 2 (Medium)",
            base_type="Medium Cluster Jewel",
            target_rarity="Rare",
            target_mods=[
                "Mob Mentality (Endurance + Frenzy on Warcry)",
                "Lead By Example (Onslaught on Crit)",
                "2 passive skills"
            ],
            crafting_priority="High",
            notes="Perfect 4-passive. ~30 div."
        ),
        TargetItem(
            slot="Cluster Jewel 3 (Small)",
            base_type="Small Cluster Jewel",
            target_rarity="Rare",
            target_mods=[
                "Lead By Example (Onslaught on Crit)"
            ],
            crafting_priority="Medium",
            notes="Perfect 2-passive. ~15 div."
        ),
        TargetItem(
            slot="Jewel 1",
            base_type="Viridian Jewel",
            target_rarity="Unique",
            target_unique_name="Impossible Escape",
            crafting_priority="High",
            notes="Impossible Escape. ~20 div."
        ),
        TargetItem(
            slot="Jewel 2",
            base_type="Viridian Jewel",
            target_rarity="Unique",
            target_unique_name="Watchers Eye",
            target_mods=["Warcry Buff Effect +", "Damage +", "Warcry Cooldown Recovery +"],
            crafting_priority="High",
            notes="Watcher's Eye with Warcry mods. ~100 div."
        ),
    ]

    return TargetBuild(
        id="facebreaker_luminary_god_tier",
        name="Facebreaker Luminary - God Tier (3.30 Covens of Umbra)",
        description="Mirror-tier Facebreaker Luminary. ~800+ div total. Maximum tankiness and damage.",
        character_class="Scion",
        ascendancy="Luminary",
        target_level=100,
        target_league="Settlers",
        main_skill="Earthshatter (Facebreaker + Merc Rallying Cry)",
        items=items,
        passive_tree_goals=[
            "Start Scion → Ascendant → Slayer → Saboteur → Luminary",
            "Resolute Technique (keystone) - ignore accuracy/evade",
            "Block nodes (Glancing Blows + Shield Mastery)",
            "Armour + Life nodes (max life)",
            "Warcry Effect nodes (Mob Mentality clusters)",
            "Endurance Charge generation (Mob Mentality + Disciple of the Unyielding)",
            "Block Mastery (Glancing Blows + Shield Mastery)",
            "Armour Mastery for +1% max res",
            "Fortify Mastery",
            "Bastion Breaker for Overwhelm"
        ],
        config_overrides={
            "pantheonMajorGod": "Lunaris",
            "pantheonMinorGod": "Tukohama",
            "bandit": "Kill All",
            "warcry_quality": {
                "Rallying Cry": 20,
                "Intimidating Cry": 20,
                "Seismic Cry": 20,
                "Enduring Cry": 20,
                "Infernal Cry": 13,
                "General's Cry": 20
            }
        },
        tags=["minmax", "luminary", "facebreaker", "earthshatter", "3.30", "covens-of-umbra"]
    )


def create_budget_version_template() -> TargetBuild:
    """Budget-friendly version (~50 div total)."""
    budget_build = create_earthshatter_berserker_template()
    budget_build.id = "earthshatter_berserker_budget"
    budget_build.name = "Earthshatter Berserker - Budget (3.30 Covens of Umbra)"
    budget_build.description = "Budget version using craftable rares instead of chase uniques. ~50 div total. 3.30: Covens of Umbra."
    budget_build.tags = ["budget", "earthshatter", "berserker", "3.30", "covens-of-umbra"]
    
    # Modify items for budget - convert ALL uniques to rares
    for item in budget_build.items:
        if item.target_unique_name:
            item.target_unique_name = None
            item.target_rarity = "Rare"
            item.target_mods = [m for m in item.target_mods if "Unique" not in m]
            item.crafting_priority = "Medium"
            item.notes = f"Budget rare version (craftable) - {item.notes}"
    
    # Specific budget overrides
    for item in budget_build.items:
        if item.slot == "Amulet":
            item.target_mods = [
                "+1 Level to All Skill Gems",
                "Attribute Scaling",
                "Life / Resistances"
            ]
            item.notes = "Budget: Craft +1 Skill on Onyx Amulet (Harvest/Beast) + Attributes + Life"
        elif item.slot == "Belt":
            item.target_mods = [
                "Flask Effect Duration +",
                "Life / Resistances during Flask Effect",
                "Flask Charges gained +"
            ]
            item.notes = "Budget: Stygian Vise with Flask Duration, Life, Res, Abyssal Jewel"
        elif item.slot == "Ring 1":
            item.target_mods = [
                "Critical Strike Multiplier +",
                "Critical Strike Chance +",
                "Life / Resistances"
            ]
            item.notes = "Budget: Rare Diamond with Crit Multi/Chance, Life, Res"
        elif item.slot == "Helmet":
            item.target_rarity = "Rare"
            item.target_mods = [
                "Lab Enchant: Warcry Buff Effect / Cooldown Recovery",
                "Armour + Life + Res",
                "Essence of Horror: 10% Reduced Extra Dmg from Crits per Endurance Charge"
            ]
            item.notes = "Budget: Rare Royal Burgonet with Lab enchant + Essence of Horror"
        elif item.slot == "Jewel 1":
            item.target_rarity = "Rare"
            item.target_mods = [
                "Life + Damage with Attacks / Spell",
                "Mana / Resistances"
            ]
            item.target_unique_name = None
            item.notes = "Budget: Rare Viridian with Life + Damage"
        elif item.slot == "Jewel 2":
            item.target_rarity = "Rare"
            item.target_mods = [
                "Life + Damage",
                "Mana / Resistances"
            ]
            item.target_unique_name = None
            item.notes = "Budget: Rare Viridian with Life + Damage"
    
    return budget_build


# ============================================================
# CLI Interface
# ============================================================

def main():
    import sys
    
    store = TargetBuildStore()
    
    if len(sys.argv) < 2:
        print("Usage: python target_build_store.py <command> [args]")
        print("\nCommands:")
        print("  list                    - List all target builds")
        print("  get <id>                - Get build details")
        print("  create <id> <name>      - Create new empty build")
        print("  template <type> <id>    - Create from template (god_tier, budget)")
        print("  update <id> <field> <value> - Update build field")
        print("  item-add <build_id> <slot> <base> <mods...> - Add target item")
        print("  item-remove <build_id> <slot> - Remove target item")
        print("  duplicate <src_id> <new_id> <new_name> - Duplicate build")
        print("  delete <id>             - Delete build")
        print("  export <id> <file>      - Export build to JSON file")
        print("  import <file>           - Import build from JSON file")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        builds = store.list_all()
        if not builds:
            print("No target builds found.")
            return
        print(f"{'ID':<40} {'Name':<40} {'Class':<15} {'League':<12} {'Updated':<20} {'Tags'}")
        print("-" * 150)
        for b in builds:
            tags = ",".join(b.tags)
            print(f"{b.id:<40} {b.name:<40} {b.character_class}/{b.ascendancy:<15} {b.target_league:<12} {b.updated_at[:19]:<20} {tags}")
    
    elif cmd == "get":
        if len(sys.argv) < 3:
            print("Usage: get <id>")
            return
        build = store.get(sys.argv[2])
        if not build:
            print(f"Build not found: {sys.argv[2]}")
            return
        print(json.dumps(asdict(build), indent=2))
    
    elif cmd == "create":
        if len(sys.argv) < 4:
            print("Usage: create <id> <name> [class] [ascendancy]")
            return
        build_id, name = sys.argv[2], sys.argv[3]
        cls = sys.argv[4] if len(sys.argv) > 4 else "Marauder"
        asc = sys.argv[5] if len(sys.argv) > 5 else "Berserker"
        
        build = TargetBuild(
            id=build_id,
            name=name,
            description="",
            character_class=cls,
            ascendancy=asc
        )
        store.create(build)
        print(f"Created build: {build_id}")
    
    elif cmd == "template":
        if len(sys.argv) < 4:
            print("Usage: template <god_tier|budget> <id>")
            return
        tpl_type, build_id = sys.argv[2], sys.argv[3]
        
        if tpl_type == "god_tier":
            build = create_earthshatter_berserker_template()
        elif tpl_type == "budget":
            build = create_budget_version_template()
        else:
            print(f"Unknown template: {tpl_type}")
            return
        
        build.id = build_id
        store.create(build)
        print(f"Created {tpl_type} template: {build_id}")
    
    elif cmd == "update":
        if len(sys.argv) < 5:
            print("Usage: update <id> <field> <value>")
            return
        build_id, field, value = sys.argv[2], sys.argv[3], sys.argv[4]
        build = store.get(build_id)
        if not build:
            print(f"Build not found: {build_id}")
            return
        
        # Handle special fields
        if field == "tags":
            value = value.split(",")
        elif field in ["target_level", "version"]:
            value = int(value)
        elif field in ["config_overrides"]:
            value = json.loads(value)
        
        setattr(build, field, value)
        build.updated_at = datetime.now().isoformat()
        build.version += 1
        store.update(build)
        print(f"Updated {field} for {build_id}")
    
    elif cmd == "item-add":
        if len(sys.argv) < 6:
            print("Usage: item-add <build_id> <slot> <base> <rarity> <mods...>")
            return
        build_id, slot, base, rarity = sys.argv[2:6]
        mods = sys.argv[6:] if len(sys.argv) > 6 else []
        
        item = TargetItem(
            slot=slot,
            base_type=base,
            target_rarity=rarity,
            target_mods=mods
        )
        store.add_item(build_id, item)
        print(f"Added item to {slot} for {build_id}")
    
    elif cmd == "item-remove":
        if len(sys.argv) < 4:
            print("Usage: item-remove <build_id> <slot>")
            return
        store.remove_item(sys.argv[2], sys.argv[3])
        print(f"Removed item from slot {sys.argv[3]}")
    
    elif cmd == "duplicate":
        if len(sys.argv) < 5:
            print("Usage: duplicate <src_id> <new_id> <new_name>")
            return
        src_id, new_id, new_name = sys.argv[2], sys.argv[3], sys.argv[4]
        new_build = store.duplicate(src_id, new_id, new_name)
        if new_build:
            print(f"Duplicated {src_id} -> {new_id} ({new_name})")
        else:
            print(f"Source build not found: {src_id}")
    
    elif cmd == "delete":
        if len(sys.argv) < 3:
            print("Usage: delete <id>")
            return
        if store.delete(sys.argv[2]):
            print(f"Deleted build: {sys.argv[2]}")
        else:
            print(f"Build not found: {sys.argv[2]}")
    
    elif cmd == "export":
        if len(sys.argv) < 4:
            print("Usage: export <id> <file>")
            return
        build = store.get(sys.argv[2])
        if not build:
            print(f"Build not found: {sys.argv[2]}")
            return
        with open(sys.argv[3], 'w') as f:
            json.dump(asdict(build), f, indent=2)
        print(f"Exported to {sys.argv[3]}")
    
    elif cmd == "import":
        if len(sys.argv) < 3:
            print("Usage: import <file>")
            return
        with open(sys.argv[2], 'r') as f:
            data = json.load(f)
        build = TargetBuild(**data)
        store.create(build)
        print(f"Imported build: {build.id}")
    
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()