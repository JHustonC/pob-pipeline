#!/usr/bin/env python3
"""
End-to-End Test: Mid-Game Character Pipeline
=============================================
Simulates a Level 96 Earthshatter Berserker (Week 1 loadout)
and runs the full analysis pipeline:
1. Character state analysis
2. Upgrade identification with budget
3. Crafting guide matching
4. Farming strategy recommendations
5. Decision matrix application
"""

import json
import sys
sys.path.insert(0, '/Users/joecrawford/.hermes/profiles/bot-of-exile/scripts')

from pob_add_character_loadout import add_character_loadout, PASSIVE_CONVERTER_AVAILABLE
from pob_passive_converter import convert_passive_hashes, get_class_id, get_ascendancy_id


# ============================================================
# SIMULATED CHARACTER STATE (Week 1 - Level 96)
# ============================================================

MID_GAME_CHARACTER = {
    "name": "MidGameBerserker",
    "class": "Marauder",
    "ascendancy": "Berserker",
    "level": 96,
    "league": "Settlers",  # 3.30 league
    "pantheon_major": "Lunaris",
    "pantheon_minor": "Tukohama",
    "bandit_choice": "Eramir",
    "passives": {
        "hashes": [
            9471, 5197, 13922, 487, 1909, 48199, 64587, 7162, 6289, 24716,
            47175, 50340, 57953, 25682, 38777, 14767, 49318, 65107, 42861,
            36200, 24914, 34400
        ],
        "hashes_ex": [22222],
        "mastery_effects": [
            [62015,14206],[54340,7137],[35977,60034],[2841,64875],
            [35118,27095],[59335,28469],[24224,50175],[12169,39010],
            [25011,34242],[9471,56848],[33657,4319]
        ]
    },
    "equipment": [
        # Weapon 1: Carrion Sever (Vaal Axe)
        {
            "inventoryId": "Weapon",
            "name": "Carrion Sever",
            "typeLine": "Vaal Axe",
            "rarity": "Rare",
            "ilvl": 84,
            "properties": [
                {"name": "Physical Damage", "values": [["47-81"]]},
                {"name": "Attack Speed", "values": [["1.56"]]}
            ],
            "explicitMods": [
                "56% increased Physical Damage",
                "Adds 47 to 81 Physical Damage",
                "20% increased Attack Speed",
                "118% increased Physical Damage (crafted)",
                "22% increased Attack Speed while Rare/Unique Enemy Nearby (crafted)"
            ],
            "influences": {}
        },
        # Helmet: Echoes of Creation
        {
            "inventoryId": "Helmet",
            "name": "Echoes of Creation",
            "typeLine": "Royal Burgonet",
            "rarity": "Unique",
            "ilvl": 84,
            "properties": [
                {"name": "Armour", "values": [["1234"]]},
                {"name": "Energy Shield", "values": [["567"]]}
            ],
            "explicitMods": [
                "89% increased Armour",
                "+53 to maximum Life",
                "When you Attack, take 19% of Life as Physical Damage for each Warcry Exerting",
                "Skills deal 15% more Damage for each Warcry Exerting"
            ],
            "influences": {}
        },
        # Body Armour: Plague Hide
        {
            "inventoryId": "BodyArmour",
            "name": "Plague Hide",
            "typeLine": "Royal Plate",
            "rarity": "Rare",
            "ilvl": 86,
            "properties": [
                {"name": "Armour", "values": [["2456"]]}
            ],
            "explicitMods": [
                "10% of Physical Damage from Hits taken as Cold Damage",
                "+1% to all maximum Resistances",
                "140% increased Armour",
                "+41% to Fire Resistance",
                "17% increased Stun and Block Recovery"
            ],
            "influences": {}
        },
        # Gloves: Pain Hand
        {
            "inventoryId": "Gloves",
            "name": "Pain Hand",
            "typeLine": "Leviathan Gauntlets",
            "rarity": "Rare",
            "ilvl": 86,
            "properties": [
                {"name": "Armour", "values": [["1500"]]},
                {"name": "Evasion", "values": [["450"]]}
            ],
            "explicitMods": [
                "Hits have 33% chance to ignore Enemy Physical Damage Reduction",
                "Adds 4 to 8 Fire Damage to Attacks",
                "93% increased Armour",
                "+126 to maximum Life",
                "+43% to Cold Resistance"
            ],
            "influences": {}
        },
        # Boots: Sol Spur
        {
            "inventoryId": "Boots",
            "name": "Sol Spur",
            "typeLine": "Leviathan Greaves",
            "rarity": "Rare",
            "ilvl": 86,
            "properties": [
                {"name": "Armour", "values": [["1500"]]},
                {"name": "Evasion", "values": [["450"]]}
            ],
            "explicitMods": [
                "Gain 4% of Physical Damage as Extra Chaos Damage",
                "5% increased Damage per Endurance Charge",
                "93% increased Armour",
                "+113 to maximum Life",
                "+42% to Fire Resistance"
            ],
            "influences": {}
        },
        # Amulet: Phoenix Gorget
        {
            "inventoryId": "Amulet",
            "name": "Phoenix Gorget",
            "typeLine": "Turquoise Amulet",
            "rarity": "Rare",
            "ilvl": 86,
            "explicitMods": [
                "Adds 3 to 4 Physical Damage to Attacks",
                "+123 to maximum Life",
                "+30% to Fire Resistance",
                "+41% to Cold Resistance",
                "+21% to Lightning Resistance"
            ],
            "influences": {}
        },
        # Belt: Rage Buckle
        {
            "inventoryId": "Belt",
            "name": "Rage Buckle",
            "typeLine": "Stygian Vise",
            "rarity": "Rare",
            "ilvl": 84,
            "explicitMods": [
                "+142 to maximum Life",
                "+32% to Chaos Resistance",
                "+20% to Cold and Lightning Resistances (crafted)"
            ],
            "influences": {}
        },
        # Ring 1: Death Rush
        {
            "inventoryId": "Ring",
            "name": "Death Rush",
            "typeLine": "Amethyst Ring",
            "rarity": "Rare",
            "ilvl": 84,
            "explicitMods": [
                "+23% to Chaos Resistance",
                "Recover 4% of Life on Kill"
            ],
            "influences": {}
        },
        # Ring 2: Vengeance Eye
        {
            "inventoryId": "Ring",
            "name": "Vengeance Eye",
            "typeLine": "Amethyst Ring",
            "rarity": "Rare",
            "ilvl": 84,
            "explicitMods": [
                "+23% to Chaos Resistance",
                "Adds 1 to 2 Cold Damage to Attacks",
                "+66 to maximum Life",
                "+15% to all Elemental Resistances",
                "+38% to Lightning Resistance"
            ],
            "influences": {}
        },
        # Weapon 2 Swap: Onslaught Emblem
        {
            "inventoryId": "Weapon2",
            "name": "Onslaught Emblem",
            "typeLine": "Cedar Tower Shield",
            "rarity": "Rare",
            "ilvl": 84,
            "explicitMods": [
                "+28 to maximum Life",
                "14% increased Armour",
                "+21 to maximum Life",
                "Regenerate 2.4 Life per second",
                "9% increased Stun and Block Recovery"
            ],
            "influences": {}
        },
        # Flasks
        {
            "inventoryId": "Flask",
            "name": "Seething Divine Life Flask of Alleviation",
            "typeLine": "Life Flask",
            "rarity": "Magic",
            "ilvl": 84
        },
        {
            "inventoryId": "Flask",
            "name": "Flagellant's Ruby Flask of Craft",
            "typeLine": "Ruby Flask",
            "rarity": "Magic",
            "ilvl": 84
        },
        {
            "inventoryId": "Flask",
            "name": "Apprentice's Granite Flask of the Kakapo",
            "typeLine": "Granite Flask",
            "rarity": "Magic",
            "ilvl": 84
        },
        {
            "inventoryId": "Flask",
            "name": "Brewer's Sapphire Flask of the Tortoise",
            "typeLine": "Sapphire Flask",
            "rarity": "Magic",
            "ilvl": 84
        },
        {
            "inventoryId": "Flask",
            "name": "Analyst's Topaz Flask of the Lynx",
            "typeLine": "Topaz Flask",
            "rarity": "Magic",
            "ilvl": 84
        }
    ]
}


# ============================================================
# TARGET END-GAME (God Tier) FOR COMPARISON
# ============================================================

GOD_TIER_TARGETS = {
    "Weapon 1": {
        "base": "Vaal Axe",
        "target_mods": [
            "180%+ increased Physical Damage",
            "25%+ increased Attack Speed",
            "+2 to Level of Socketed Melee Gems",
            "Critical Strike Multiplier +",
            "Critical Strike Chance +"
        ],
        "ilvl": 86,
        "influences": {}
    },
    "Helmet": {
        "base": "Royal Burgonet",
        "target_mods": [
            "Echoes of Creation (already have)",
            "Enchant: Warcry Buff Effect / Cooldown Recovery"
        ],
        "ilvl": 84,
        "influences": {}
    },
    "Body Armour": {
        "base": "Royal Plate",
        "target_mods": [
            "200%+ increased Armour",
            "+150+ Life",
            "Maximum Resistances +",
            "Physical Damage taken as Elemental"
        ],
        "ilvl": 86,
        "influences": {}
    },
    "Gloves": {
        "base": "Leviathan Gauntlets",
        "target_mods": [
            "Hits ignore Enemy Phys Reduction",
            "100+ Life",
            "Attack Speed / Crit mods"
        ],
        "ilvl": 86,
        "influences": {}
    },
    "Boots": {
        "base": "Leviathan Greaves",
        "target_mods": [
            "30%+ Movement Speed",
            "Chaos Damage / Endurance Charge scaling",
            "100+ Life"
        ],
        "ilvl": 86,
        "influences": {}
    },
    "Belt": {
        "base": "Mageblood (Heavy Belt)",
        "target_mods": [
            "4 Flask Effects",
            "Life/Resistances during Flask Effect"
        ],
        "ilvl": 86,
        "influences": {}
    },
    "Amulet": {
        "base": "Ashes of the Stars (Onyx Amulet)",
        "target_mods": [
            "+1 Level to All Skill Gems",
            "Attribute scaling"
        ],
        "ilvl": 86,
        "influences": {}
    },
    "Ring 1": {
        "base": "Circle of Guilt / Rare Ring",
        "target_mods": [
            "Crit Multi / Crit Chance",
            "Life / Resistances"
        ],
        "ilvl": 86,
        "influences": {}
    },
    "Ring 2": {
        "base": "Rare Ring / Circle of Guilt",
        "target_mods": [
            "Crit Multi / Crit Chance",
            "Life / Resistances"
        ],
        "ilvl": 86,
        "influences": {}
    }
}


# ============================================================
# ANALYSIS FUNCTIONS
# ============================================================

def analyze_gear_gaps(character, targets):
    """Compare current gear to target end-game gear."""
    gaps = {}
    equipped = {item["inventoryId"]: item for item in character["equipment"]}
    
    slot_mapping = {
        "Weapon": "Weapon 1",
        "Helmet": "Helmet", 
        "BodyArmour": "Body Armour",
        "Gloves": "Gloves",
        "Boots": "Boots",
        "Amulet": "Amulet",
        "Belt": "Belt",
        "Ring": "Ring"  # Will need to handle both rings
    }
    
    ring_count = 0
    for inv_id, item in equipped.items():
        if inv_id in slot_mapping:
            slot = slot_mapping[inv_id]
            if slot == "Ring":
                ring_count += 1
                slot = f"Ring {ring_count}"
            
            target = targets.get(slot, {})
            current_mods = item.get("explicitMods", [])
            target_mods = target.get("target_mods", [])
            
            gaps[slot] = {
                "current_item": item["name"],
                "current_base": item["typeLine"],
                "current_ilvl": item.get("ilvl", 0),
                "current_mods": current_mods,
                "target_base": target.get("base", "Unknown"),
                "target_ilvl": target.get("ilvl", 86),
                "target_mods": target_mods,
                "missing_mods": [m for m in target_mods if not any(m.lower() in cm.lower() for cm in current_mods)],
                "upgrade_priority": "High" if len(target_mods) > len(current_mods) else "Medium"
            }
    
    return gaps


def estimate_upgrade_costs(gaps):
    """Estimate currency cost for each upgrade path."""
    cost_estimates = {}
    
    # Base costs (divine orbs) - rough estimates for 3.30
    base_costs = {
        "Weapon 1": {"buy": 50, "craft": 30, "farm": "Simulacrum/Boss"},
        "Helmet": {"buy": 20, "craft": 15, "farm": "Lab/Enchant"},
        "Body Armour": {"buy": 80, "craft": 50, "farm": "Maps/Boss"},
        "Gloves": {"buy": 30, "craft": 20, "farm": "Maps"},
        "Boots": {"buy": 25, "craft": 15, "farm": "Maps"},
        "Belt": {"buy": 200, "craft": "N/A", "farm": "Kingsmarch/Trade"},  # Mageblood
        "Amulet": {"buy": 150, "craft": "N/A", "farm": "Sanctum/Trade"},  # Ashes
        "Ring 1": {"buy": 40, "craft": 25, "farm": "Heist/Delve"},
        "Ring 2": {"buy": 40, "craft": 25, "farm": "Heist/Delve"},
    }
    
    for slot, gap in gaps.items():
        if slot in base_costs:
            cost = base_costs[slot]
            gap["cost_estimate"] = cost
            gap["acquisition_options"] = {
                "buy_finished": cost["buy"],
                "craft_from_base": cost["craft"] if cost["craft"] != "N/A" else None,
                "farm_currency_then_buy": cost["farm"],
                "farm_item_directly": "Specific content" if slot in ["Belt", "Amulet"] else "General mapping"
            }
    
    return gaps


def apply_decision_matrix(gaps, liquid_budget_divine=20):
    """Apply decision matrix to each upgrade slot."""
    decisions = {}
    
    for slot, gap in gaps.items():
        options = gap.get("acquisition_options", {})
        cost = gap.get("cost_estimate", {})
        
        buy_cost = options.get("buy_finished", 999)
        craft_cost = options.get("craft_from_base") or 999
        farm_direct = options.get("farm_item_directly", "")
        
        # Decision logic
        if buy_cost <= liquid_budget_divine * 0.3:
            decision = "BUY_FINISHED"
            reasoning = f"Affordable ({buy_cost} div) within budget ({liquid_budget_divine} div)"
        elif craft_cost <= liquid_budget_divine * 0.5 and craft_cost != "N/A":
            decision = "CRAFT_FROM_BASE"
            reasoning = f"Crafting cheaper ({craft_cost} div) than buying ({buy_cost} div)"
        elif "Mageblood" in farm_direct or "Ashes" in farm_direct:
            decision = "FARM_CURRENCY_THEN_BUY"
            reasoning = f"Item ({gap['target_base']}) only obtainable via trade, farm currency first"
        elif "Lab" in farm_direct or "Sanctum" in farm_direct:
            decision = "FARM_IT_YOURSELF"
            reasoning = f"League-specific content ({farm_direct}) drops this item"
        elif buy_cost <= liquid_budget_divine:
            decision = "BUY_FINISHED"
            reasoning = f"Within total budget ({buy_cost}/{liquid_budget_divine} div)"
        else:
            decision = "FARM_CURRENCY_THEN_BUY"
            reasoning = f"Too expensive to buy now ({buy_cost} div), farm currency first"
        
        decisions[slot] = {
            "decision": decision,
            "reasoning": reasoning,
            "buy_cost": buy_cost,
            "craft_cost": craft_cost,
            "liquid_budget": liquid_budget_divine
        }
    
    return decisions


def get_farming_strategies(target_items, league="3.30"):
    """Get farming strategies for target items/currency."""
    
    # 3.30 (Settlers/Kingsmarch) specific strategies
    strategies = {
        "divine_orbs": [
            {
                "method": "T16-17 Map Farming with Atlas Passives",
                "mechanic": "Atlas Passive Tree",
                "applicability": {"verified": True, "note": "Stable mechanic, Atlas passives change per league"},
                "requirements": {"atlas_completion": "80%+", "build": "Fast clear (5m/map)"},
                "estimated_returns": {"divine_per_hour": 3.0, "chaos_per_hour": 600},
                "investment": {"maps": "30-50c", "sextants": "5-10c", "scarabs": "10-20c"},
                "source": "poe.fandom.com", "league_tested": "3.30", "confidence": 0.9
            },
            {
                "method": "Kingsmarch (Settlers League Mechanic)",
                "mechanic": "Kingsmarch",
                "applicability": {"verified": True, "note": "New 3.30 mechanic, prioritize"},
                "requirements": {"settlers_reputation": "High", "workers": "Trained"},
                "estimated_returns": {"divine_per_hour": 2.0, "resources": "Gold/Artifacts"},
                "investment": {"time": "Daily management"},
                "source": "pathofexile.com", "league_tested": "3.30", "confidence": 0.95
            }
        ],
        "exalted_orbs": [
            {
                "method": "Boss Carries / Boss Farming",
                "mechanic": "Endgame Bosses",
                "applicability": {"verified": True, "note": "Stable"},
                "estimated_returns": {"exalted_per_hour": 5, "divine_per_hour": 1},
                "source": "poe-vault.com", "league_tested": "3.30", "confidence": 0.85
            }
        ],
        "chaos_orbs": [
            {
                "method": "Expedition Logbooks (verify 3.29 changes)",
                "mechanic": "Expedition",
                "applicability": {"verified": False, "note": "Logbook drops rebalanced 3.29"},
                "estimated_returns": {"chaos_per_hour": 800},
                "source": "poe-vault.com", "league_tested": "3.28", "confidence": 0.5
            }
        ],
        "Mageblood": [
            {
                "method": "Trade (only source)",
                "mechanic": "Trade",
                "applicability": {"verified": True, "note": "Unique belt, cannot be farmed"},
                "estimated_cost": "200+ Divine",
                "source": "Official Trade Site", "confidence": 1.0
            }
        ],
        "Ashes of the Stars": [
            {
                "method": "Sanctum / Forbidden Sanctum",
                "mechanic": "Sanctum",
                "applicability": {"verified": True, "note": "3.28+ only, relic system"},
                "estimated_returns": {"relics_per_hour": 5, "ashes_chance": "Low"},
                "source": "poe-vault.com", "league_tested": "3.30", "confidence": 0.7
            },
            {
                "method": "Trade",
                "mechanic": "Trade",
                "applicability": {"verified": True, "note": "Most reliable"},
                "estimated_cost": "150 Divine",
                "source": "Official Trade Site", "confidence": 1.0
            }
        ],
        "Crit Rings": [
            {
                "method": "Heist Blueprint Farming",
                "mechanic": "Heist",
                "applicability": {"verified": True, "note": "Contracts/blueprints changed 3.25"},
                "estimated_returns": {"rings_per_hour": 3, "value": "Variable"},
                "source": "poe-vault.com", "league_tested": "3.30", "confidence": 0.8
            },
            {
                "method": "Delve Fossil Crafting (Pristine/Jagged)",
                "mechanic": "Delve",
                "applicability": {"verified": True, "note": "Stable"},
                "estimated_cost": "20-30 Divine per attempt",
                "source": "craftofexile.com", "confidence": 0.85
            }
        ]
    }
    
    return {k: v for k, v in strategies.items() if any(k in str(t).lower() for t in target_items)}


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_pipeline():
    print("=" * 70)
    print("END-TO-END PIPELINE: Mid-Game Earthshatter Berserker (Level 96)")
    print("=" * 70)
    
    # 1. Load build
    with open('/tmp/earthshatter_berserker.json', 'r') as f:
        build = json.load(f)
    
    print("\n[1/6] CHARACTER STATE LOADED")
    print(f"    Character: {MID_GAME_CHARACTER['name']}")
    print(f"    Class: {MID_GAME_CHARACTER['class']} / {MID_GAME_CHARACTER['ascendancy']}")
    print(f"    Level: {MID_GAME_CHARACTER['level']}")
    print(f"    League: {MID_GAME_CHARACTER['league']} (3.30)")
    
    # 2. Analyze gear gaps
    print("\n[2/6] GEAR GAP ANALYSIS")
    gaps = analyze_gear_gaps(MID_GAME_CHARACTER, GOD_TIER_TARGETS)
    for slot, gap in gaps.items():
        print(f"\n  {slot}:")
        print(f"    Current: {gap['current_item']} ({gap['current_base']}) ilvl{gap['current_ilvl']}")
        print(f"    Target:  {gap['target_base']} ilvl{gap['target_ilvl']}")
        print(f"    Missing: {', '.join(gap['missing_mods']) if gap['missing_mods'] else 'None'}")
        print(f"    Priority: {gap['upgrade_priority']}")
    
    # 3. Estimate costs
    print("\n[3/6] UPGRADE COST ESTIMATION")
    gaps = estimate_upgrade_costs(gaps)
    for slot, gap in gaps.items():
        cost = gap.get("cost_estimate", {})
        opts = gap.get("acquisition_options", {})
        print(f"\n  {slot}:")
        print(f"    Buy: {cost.get('buy', 'N/A')} div | Craft: {cost.get('craft', 'N/A')} div")
        print(f"    Farm: {cost.get('farm', 'N/A')}")
    
    # 4. Apply decision matrix
    print("\n[4/6] DECISION MATRIX (Budget: 20 Divine liquid)")
    LIQUID_BUDGET = 20  # Divine orbs available
    decisions = apply_decision_matrix(gaps, LIQUID_BUDGET)
    for slot, dec in decisions.items():
        print(f"\n  {slot}: {dec['decision']}")
        print(f"    Reason: {dec['reasoning']}")
    
    # 5. Farming strategies
    print("\n[5/6] FARMING STRATEGIES (League 3.30)")
    target_items = [g["target_base"] for g in gaps.values()] + ["Divine Orbs", "Exalted Orbs"]
    farm_strats = get_farming_strategies(target_items, "3.30")
    
    for category, strats in farm_strats.items():
        print(f"\n  {category.upper()}:")
        for s in strats:
            app = s.get("applicability", {})
            status = "✓" if app.get("verified") else "⚠" if not app.get("verified") else "?"
            print(f"    {status} {s['method']}")
            print(f"       {app.get('note', '')}")
            if "estimated_returns" in s:
                ret = s["estimated_returns"]
                print(f"       Returns: {', '.join(f'{k}: {v}' for k,v in ret.items())}")
            if "estimated_cost" in s:
                print(f"       Cost: {s['estimated_cost']}")
            print(f"       Confidence: {s.get('confidence', 0):.0%}")
    
    # 6. Summary report
    print("\n[6/6] SUMMARY & ACTION PLAN")
    print("\n  IMMEDIATE ACTIONS (within 20 div budget):")
    for slot, dec in decisions.items():
        if dec["decision"] in ["BUY_FINISHED", "CRAFT_FROM_BASE"]:
            cost = dec["buy_cost"] if dec["decision"] == "BUY_FINISHED" else dec["craft_cost"]
            print(f"    → {slot}: {dec['decision']} ({cost} div)")
    
    print("\n  MEDIUM TERM (farm currency):")
    for slot, dec in decisions.items():
        if dec["decision"] in ["FARM_CURRENCY_THEN_BUY"]:
            print(f"    → {slot}: Farm {dec['buy_cost']} div via {decisions[slot]['reasoning']}")
    
    print("\n  LONG TERM (league mechanics):")
    for slot, dec in decisions.items():
        if dec["decision"] in ["FARM_IT_YOURSELF"]:
            print(f"    → {slot}: {dec['reasoning']}")
    
    print("\n  RECOMMENDED FARMING PRIORITY (3.30):")
    print("    1. Kingsmarch daily management (new league mechanic)")
    print("    2. T16-17 Maps with Atlas passives (Divine/hr)")
    print("    3. Boss carries for Exalted")
    print("    4. Heist blueprints for Rings")
    print("    5. Sanctum for Ashes of the Stars (if build needs)")
    
    return {
        "character": MID_GAME_CHARACTER,
        "gaps": gaps,
        "decisions": decisions,
        "farming": farm_strats
    }


if __name__ == "__main__":
    result = run_pipeline()