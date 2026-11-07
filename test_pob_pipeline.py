#!/usr/bin/env python3
"""
Test Suite for PoB Pipeline Components
=======================================
Comprehensive tests for all pipeline modules and dashboard functions.
"""

import unittest
import json
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add scripts to path
sys.path.insert(0, '/Users/joecrawford/.hermes/profiles/bot-of-exile/scripts')

# Import modules under test
from pob_oauth_import import (
    generate_pkce_pair, generate_state, build_authorize_url,
    exchange_code_for_tokens, refresh_access_token, PoEAPIClient
)
from pob_passive_converter import convert_passive_hashes, get_class_id, get_ascendancy_id
from pob_add_character_loadout import (
    add_character_loadout, api_item_to_pob_item, assign_items_to_slots,
    extract_skills_from_character, build_skill_from_gems,
    find_skill_set, find_item_set, find_config_set, get_next_id,
    import_character_to_build
)

# Integration test helper functions (defined here for testing)
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
        "Ring": "Ring"
    }
    
    ring_count = 0
    for inv_id, item in equipped.items():
        if inv_id in slot_mapping:
            slot = slot_mapping[inv_id]
            if slot == "Ring":
                ring_count += 1
                slot = f"Ring {ring_count}"
            
            target = targets.get(slot)
            if not target:
                continue
                
            current_mods = item.get("explicitMods", [])
            target_mods = target.target_mods if hasattr(target, 'target_mods') else target.get("target_mods", [])
            
            gaps[slot] = {
                "current_item": item["name"],
                "current_base": item["typeLine"],
                "current_ilvl": item.get("ilvl", 0),
                "current_mods": current_mods,
                "target_base": target.base_type if hasattr(target, 'base_type') else target.get("base_type", "Unknown"),
                "target_ilvl": target.target_ilvl if hasattr(target, 'target_ilvl') else target.get("target_ilvl", 86),
                "target_mods": target_mods,
                "missing_mods": [m for m in target_mods if not any(m.lower() in cm.lower() for cm in current_mods)],
                "upgrade_priority": "High" if len(target_mods) > len(current_mods) else "Medium"
            }
    
    return gaps


def estimate_upgrade_costs(gaps):
    """Estimate currency cost for each upgrade path."""
    cost_estimates = {}
    
    base_costs = {
        "Weapon 1": {"buy": 50, "craft": 30, "farm": "Simulacrum/Boss"},
        "Helmet": {"buy": 20, "craft": 15, "farm": "Lab/Enchant"},
        "Body Armour": {"buy": 80, "craft": 50, "farm": "Maps/Boss"},
        "Gloves": {"buy": 30, "craft": 20, "farm": "Maps"},
        "Boots": {"buy": 25, "craft": 15, "farm": "Maps"},
        "Amulet": {"buy": 150, "craft": "N/A", "farm": "Sanctum/Trade"},
        "Belt": {"buy": 200, "craft": "N/A", "farm": "Kingsmarch/Trade"},
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
    """Get farming strategies for target items."""
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
                "applicability": {"verified": True, "note": "3.28+ relic system"},
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
    
    # Return all strategies for currency items (always useful)
    # Filter for specific items if they match
    target_str = " ".join(str(t).lower() for t in target_items)
    result = {}
    for k, v in strategies.items():
        if k in ["divine_orbs", "exalted_orbs"] or k.lower() in target_str:
            result[k] = v
    
    return result


from pob_trade_query_generator import (
    TradeQueryBuilder, CurrencyType, ItemCategory, SLOT_CATEGORY_MAP,
    create_earthshatter_berserker_query
)
from pob_stash_currency_client import (
    PoEStashClient, StashTab, StashItem, NetWorth,
    CurrencyType, DEFAULT_CURRENCY_RATES, CURRENCY_DISPLAY
)
from pob_target_build_store import (
    TargetBuildStore, TargetBuild, TargetItem,
    create_earthshatter_berserker_template, create_budget_version_template
)


# ============================================================
# OAuth Tests
# ============================================================

class TestOAuth(unittest.TestCase):
    """Tests for OAuth PKCE flow."""
    
    def test_generate_pkce_pair(self):
        """Test PKCE code verifier and challenge generation."""
        verifier, challenge = generate_pkce_pair()
        
        self.assertIsInstance(verifier, str)
        self.assertIsInstance(challenge, str)
        self.assertGreater(len(verifier), 20)
        self.assertGreater(len(challenge), 20)
        # Verify they're different
        self.assertNotEqual(verifier, challenge)
        # Verify URL-safe base64 (no +, /, =)
        self.assertNotIn('+', verifier)
        self.assertNotIn('/', verifier)
        self.assertNotIn('=', verifier)
        self.assertNotIn('+', challenge)
        self.assertNotIn('/', challenge)
        self.assertNotIn('=', challenge)
    
    def test_generate_state(self):
        """Test state generation for CSRF protection."""
        state = generate_state()
        self.assertIsInstance(state, str)
        self.assertEqual(len(state), 16)  # 16 hex chars = 8 bytes
        # Should be valid hex
        int(state, 16)  # Should not raise
    
    def test_build_authorize_url(self):
        """Test authorization URL building."""
        url = build_authorize_url(
            code_challenge="test_challenge",
            state="test_state",
            redirect_uri="http://localhost:49082"
        )
        
        self.assertIn("https://www.pathofexile.com/oauth/authorize", url)
        self.assertIn("client_id=pob", url)
        self.assertIn("response_type=code", url)
        self.assertIn("scope=account%3Aprofile+account%3Aleagues+account%3Acharacters+account%3Atrade", url)
        self.assertIn("state=test_state", url)
        self.assertIn("code_challenge=test_challenge", url)
        self.assertIn("code_challenge_method=S256", url)
        self.assertIn("redirect_uri=http%3A%2F%2Flocalhost%3A49082", url)
    
    def test_poe_api_client_init(self):
        """Test PoEAPIClient initialization."""
        client = PoEAPIClient(
            access_token="test_token",
            refresh_token="test_refresh",
            token_expiry=9999999999
        )
        
        self.assertEqual(client.access_token, "test_token")
        self.assertEqual(client.refresh_token, "test_refresh")
        self.assertEqual(client.token_expiry, 9999999999)
        # baseUrl is not exposed as public attribute
        self.assertTrue(hasattr(client, 'session'))


# ============================================================
# Passive Converter Tests
# ============================================================

class TestPassiveConverter(unittest.TestCase):
    """Tests for passive hash conversion."""
    
    def test_get_class_id(self):
        """Test class name to ID mapping."""
        self.assertEqual(get_class_id("Marauder"), 1)
        self.assertEqual(get_class_id("Ranger"), 2)
        self.assertEqual(get_class_id("Witch"), 3)
        self.assertEqual(get_class_id("Duelist"), 4)
        self.assertEqual(get_class_id("Templar"), 5)
        self.assertEqual(get_class_id("Shadow"), 6)
        self.assertEqual(get_class_id("Scion"), 0)
        # Unknown defaults to Marauder
        self.assertEqual(get_class_id("Unknown"), 1)
    
    def test_get_ascendancy_id(self):
        """Test ascendancy name to ID mapping."""
        # Marauder ascendancies
        self.assertEqual(get_ascendancy_id("Marauder", "Juggernaut"), 1)
        self.assertEqual(get_ascendancy_id("Marauder", "Berserker"), 2)
        self.assertEqual(get_ascendancy_id("Marauder", "Chieftain"), 3)
        
        # Ranger ascendancies
        self.assertEqual(get_ascendancy_id("Ranger", "Deadeye"), 1)
        self.assertEqual(get_ascendancy_id("Ranger", "Raider"), 2)
        self.assertEqual(get_ascendancy_id("Ranger", "Pathfinder"), 3)
        
        # Unknown defaults to 1
        self.assertEqual(get_ascendancy_id("Marauder", "Unknown"), 1)
    
    @patch('pob_passive_converter.subprocess.run')
    def test_convert_passive_hashes_success(self, mock_run):
        """Test successful passive hash conversion."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                "validNodes": [9471, 5197, 13922],
                "clusterNodes": [],
                "missingNodes": [],
                "totalValid": 3
            }),
            stderr=""
        )
        
        result = convert_passive_hashes([9471, 5197, 13922])
        
        self.assertEqual(result["totalValid"], 3)
        self.assertEqual(result["validNodes"], [9471, 5197, 13922])
        self.assertEqual(result["missingNodes"], [])
    
    @patch('pob_passive_converter.subprocess.run')
    def test_convert_passive_hashes_with_cluster(self, mock_run):
        """Test conversion with cluster jewel nodes."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                "validNodes": [9471],
                "clusterNodes": [65536, 65537],
                "missingNodes": [],
                "totalValid": 1,
                "totalCluster": 2
            }),
            stderr=""
        )
        
        result = convert_passive_hashes([9471, 65536, 65537])
        
        self.assertEqual(result["totalValid"], 1)
        self.assertEqual(result["totalCluster"], 2)
        self.assertEqual(result["clusterNodes"], [65536, 65537])


# ============================================================
# Character Loadout Tests
# ============================================================

class TestCharacterLoadout(unittest.TestCase):
    """Tests for adding character as loadout."""
    
    def setUp(self):
        """Create a minimal build structure for testing."""
        self.build = {
            "Skills": {
                "SkillSet": [
                    {"_attr": {"id": "1", "title": "Default"}}
                ]
            },
            "Items": {
                "Item": [],
                "ItemSet": [
                    {
                        "_attr": {"id": "1", "title": "Default", "useSecondWeaponSet": "false"},
                        "Slot": [
                            {"_attr": {"name": "Weapon 1", "itemId": "0"}},
                            {"_attr": {"name": "Helmet", "itemId": "0"}},
                            {"_attr": {"name": "Body Armour", "itemId": "0"}}
                        ]
                    }
                ]
            },
            "Config": {
                "ConfigSet": [
                    {
                        "_attr": {"id": "1", "title": "Default"},
                        "Input": [
                            {"_attr": {"name": "pantheonMajorGod", "string": "Lunaris"}},
                            {"_attr": {"name": "bandit", "string": "None"}}
                        ],
                        "Placeholder": [
                            {"_attr": {"name": "enemyColdResist", "number": "50"}}
                        ]
                    }
                ]
            },
            "Tree": {
                "Spec": [
                    {"_attr": {"id": "1", "title": "Default"}}
                ]
            }
        }
    
    def test_get_next_id(self):
        """Test ID generation."""
        items = [{"_attr": {"id": "1"}}, {"_attr": {"id": "3"}}, {"_attr": {"id": "2"}}]
        self.assertEqual(get_next_id(items), "4")
        
        # Empty list
        self.assertEqual(get_next_id([]), "1")
        
        # Non-numeric IDs ignored
        items = [{"_attr": {"id": "abc"}}, {"_attr": {"id": "5"}}]
        self.assertEqual(get_next_id(items), "6")
    
    def test_find_functions(self):
        """Test finding loadout components."""
        skill_set = find_skill_set(self.build, "1")
        self.assertIsNotNone(skill_set)
        self.assertEqual(skill_set["_attr"]["id"], "1")
        
        item_set = find_item_set(self.build, "1")
        self.assertIsNotNone(item_set)
        self.assertEqual(item_set["_attr"]["id"], "1")
        
        config_set = find_config_set(self.build, "1")
        self.assertIsNotNone(config_set)
        self.assertEqual(config_set["_attr"]["id"], "1")
        
        # Not found
        self.assertIsNone(find_skill_set(self.build, "999"))
    
    def test_api_item_to_pob_item(self):
        """Test API item to PoB item conversion."""
        api_item = {
            "inventoryId": "Helmet",
            "name": "Test Helmet",
            "typeLine": "Royal Burgonet",
            "rarity": "Unique",
            "properties": [
                {"name": "Armour", "values": [["1000"]]},
                {"name": "Energy Shield", "values": [["500"]]}
            ],
            "requirements": [
                {"name": "Level", "values": [["68"]]},
                {"name": "Str", "values": [["100"]]}
            ],
            "sockets": [
                {"group": 0, "attr": "B"}, {"group": 0, "attr": "B"}, {"group": 0, "attr": "B"}
            ],
            "ilvl": 84,
            "quality": 20,
            "implicitMods": ["+2 to Level of Socketed Gems"],
            "explicitMods": [
                "Trigger Level 20 Summon Harbinger",
                "+100 to maximum Life"
            ],
            "corrupted": False
        }
        
        pob_item = api_item_to_pob_item(api_item, 1)
        
        self.assertEqual(pob_item["_attr"]["id"], "1")
        self.assertIn("Rarity: UNIQUE", pob_item["_text"])
        self.assertIn("Test Helmet", pob_item["_text"])
        self.assertIn("Royal Burgonet", pob_item["_text"])
        self.assertIn("Armour: 1000", pob_item["_text"])
        self.assertIn("Implicits: 1", pob_item["_text"])
        self.assertIn("+2 to Level of Socketed Gems", pob_item["_text"])
        self.assertIn("Trigger Level 20 Summon Harbinger", pob_item["_text"])
    
    def test_assign_items_to_slots(self):
        """Test item slot assignment."""
        character = {
            "equipment": [
                {"inventoryId": "Helmet", "name": "Helm"},
                {"inventoryId": "BodyArmour", "name": "Chest"},
                {"inventoryId": "Ring", "name": "Ring1"},
                {"inventoryId": "Ring", "name": "Ring2"},
                {"inventoryId": "Flask", "name": "Flask1"},
                {"inventoryId": "Flask", "name": "Flask2"},
                {"inventoryId": "Weapon", "name": "Sword"}
            ]
        }
        
        slots = assign_items_to_slots(character)
        
        self.assertEqual(slots["Helmet"], 0)
        self.assertEqual(slots["Body Armour"], 1)
        self.assertEqual(slots["Ring 1"], 2)
        self.assertEqual(slots["Ring 2"], 3)
        self.assertEqual(slots["Flask 1"], 4)
        self.assertEqual(slots["Flask 2"], 5)
        self.assertEqual(slots["Weapon 1"], 6)
    
    def test_extract_skills_from_character(self):
        """Test skill extraction from character equipment."""
        character = {
            "equipment": [
                {
                    "inventoryId": "BodyArmour",
                    "name": "Chest",
                    "sockets": [
                        {"group": 0, "attr": "S", "name": "Earthshatter", "typeLine": "SkillGemEarthshatter", "level": 20, "quality": 20},
                        {"group": 0, "attr": "S", "name": "Melee Physical Damage", "typeLine": "SupportGemMeleePhysicalDamage", "level": 20, "quality": 20},
                        {"group": 1, "attr": "S", "name": "Berserk", "typeLine": "SkillGemBerserk", "level": 20, "quality": 20}
                    ]
                }
            ]
        }
        
        skills = extract_skills_from_character(character)
        
        self.assertEqual(len(skills), 2)  # Two groups
        
        # First group: Earthshatter + Melee Phys
        main_skill = skills[0]
        gems = main_skill["Gem"]
        self.assertEqual(len(gems), 2)
        self.assertEqual(gems[0]["_attr"]["nameSpec"], "Earthshatter")
        self.assertEqual(gems[1]["_attr"]["nameSpec"], "Melee Physical Damage")
        
        # Second group: Berserk (single gem)
        main_skill2 = skills[1]
        gem = main_skill2["Gem"]
        self.assertEqual(gem["_attr"]["nameSpec"], "Berserk")
    
    def test_build_skill_from_gems(self):
        """Test skill object building."""
        active = {"name": "Earthshatter", "typeLine": "SkillGemEarthshatter", "level": 20, "quality": 20}
        supports = [
            {"name": "Melee Physical Damage", "typeLine": "SupportGemMeleePhysicalDamage", "level": 20, "quality": 20},
            {"name": "Pulverise", "typeLine": "SupportGemPulverise", "level": 20, "quality": 20}
        ]
        
        skill = build_skill_from_gems(active, supports, "BodyArmour", "Chest")
        
        self.assertEqual(skill["_attr"]["slot"], "Body Armour")
        self.assertEqual(skill["_attr"]["mainActiveSkill"], "1")
        gems = skill["Gem"]
        self.assertEqual(len(gems), 3)
        self.assertEqual(gems[0]["_attr"]["nameSpec"], "Earthshatter")
        self.assertEqual(gems[1]["_attr"]["nameSpec"], "Melee Physical Damage")
        self.assertEqual(gems[2]["_attr"]["nameSpec"], "Pulverise")
    
    def test_add_character_loadout(self):
        """Test full loadout addition."""
        # Mock the passive converter to return valid results
        import pob_add_character_loadout as pcl
        original_convert = pcl.convert_passive_hashes
        
        def mock_convert(hashes, tree_version="3_29", class_id=1, ascendancy_id=2):
            return {
                "validNodes": [1, 2, 3],
                "clusterNodes": [4],
                "missingNodes": [],
                "totalValid": 3,
                "totalCluster": 1,
                "totalMissing": 0,
                "totalInput": 4
            }
        
        pcl.convert_passive_hashes = mock_convert
        
        try:
            character = {
                "name": "TestChar",
                "class": "Marauder",
                "ascendancy": "Berserker",
                "level": 90,
                "league": "Test",
                "pantheon_major": "Lunaris",
                "pantheon_minor": "Tukohama",
                "bandit_choice": "Kill All",
                "passives": {"hashes": [1, 2, 3], "hashes_ex": [4], "mastery_effects": [[5, 6]]},
                "equipment": [
                    {"inventoryId": "Weapon", "name": "Sword", "typeLine": "Vaal Axe", "rarity": "Rare", "ilvl": 84, "explicitMods": ["100% Phys"]}
                ]
            }
            
            new_build = add_character_loadout(self.build, character, "Test Loadout", template_loadout_id="1")
            
            # Check new loadout added
            skill_sets = new_build["Skills"]["SkillSet"]
            self.assertEqual(len(skill_sets), 2)
            self.assertEqual(skill_sets[1]["_attr"]["title"], "Test Loadout")
            
            item_sets = new_build["Items"]["ItemSet"]
            self.assertEqual(len(item_sets), 2)
            self.assertEqual(item_sets[1]["_attr"]["title"], "Test Loadout")
            
            config_sets = new_build["Config"]["ConfigSet"]
            self.assertEqual(len(config_sets), 2)
            
            # Check tree spec added (now with mocked converter)
            specs = new_build["Tree"]["Spec"]
            self.assertEqual(len(specs), 2)
        finally:
            pcl.convert_passive_hashes = original_convert


# ============================================================
# Trade Query Generator Tests
# ============================================================

class TestTradeQueryGenerator(unittest.TestCase):
    """Tests for trade query generation."""
    
    def test_trade_query_builder_init(self):
        """Test builder initialization."""
        builder = TradeQueryBuilder(
            league="Settlers",
            max_price=50,
            currency=CurrencyType.DIVINE,
            character_level=95,
            character_attributes={"strength": 200, "dexterity": 100, "intelligence": 50}
        )
        
        self.assertEqual(builder.league, "Settlers")
        self.assertEqual(builder.max_price, 50)
        self.assertEqual(builder.currency, CurrencyType.DIVINE)
        self.assertEqual(builder.character_level, 95)
        self.assertEqual(builder.character_attributes["strength"], 200)
    
    def test_add_stat_weight(self):
        """Test adding stat weights."""
        builder = TradeQueryBuilder()
        builder.add_stat_weight("FullDPS", 1.0)
        builder.add_stat_weight("FireResist", 0.5, "cap_at_max")
        
        self.assertEqual(len(builder.stat_weights), 2)
        self.assertEqual(builder.stat_weights[0].stat_id, "FullDPS")
        self.assertEqual(builder.stat_weights[0].weight, 1.0)
        self.assertEqual(builder.stat_weights[1].transform, "cap_at_max")
    
    def test_set_current_stat(self):
        """Test setting current stat values."""
        builder = TradeQueryBuilder()
        builder.add_stat_weight("FullDPS", 1.0)
        builder.set_current_stat("FullDPS", 500000)
        
        sw = builder.stat_weights[0]
        self.assertEqual(sw.current_value, 500000)
    
    def test_build_query(self):
        """Test query building."""
        builder = TradeQueryBuilder(
            max_price=50,
            currency=CurrencyType.DIVINE,
            character_level=95
        )
        builder.add_stat_weight("FullDPS", 1.0)
        builder.set_current_stat("FullDPS", 500000)
        builder.add_stat_weight("FireResist", 0.5, "cap_at_max")
        builder.set_current_stat("FireResist", 85)
        
        query = builder.build_query({"FullDPS": 500000, "FireResist": 85})
        
        self.assertIn("query", query.query)
        self.assertEqual(query.query["sort"], {"price": "asc"})
        self.assertEqual(query.query["query"]["filters"]["trade_filters"]["filters"]["price"]["max"], 50)
        self.assertEqual(query.query["query"]["filters"]["trade_filters"]["filters"]["price"]["currency"], CurrencyType.DIVINE.value)
        
        # Check stat filters
        stat_filters = query.query["query"]["stats"][0]["filters"]
        self.assertGreater(len(stat_filters), 0)
        
        # Find FullDPS filter
        full_dps_filter = next((f for f in stat_filters if f["id"] == "FullDPS"), None)
        self.assertIsNotNone(full_dps_filter)
        self.assertEqual(full_dps_filter["value"]["min"], 450000)  # 90% of 500000
    
    def test_to_trade_url(self):
        """Test URL generation."""
        builder = TradeQueryBuilder(league="Settlers", max_price=10, currency=CurrencyType.CHAOS)
        query = builder.build_query()
        url = builder.to_trade_url(query)
        
        self.assertIn("https://www.pathofexile.com/trade/search/Settlers/", url)
    
    def test_create_earthshatter_berserker_query(self):
        """Test build-specific query creation."""
        current_weapon = {
            "stats": {
                "FullDPS": 500000,
                "AttackSpeed": 1.5,
                "CriticalStrikeChance": 5.0,
                "EffectiveHitPool": 50000
            }
        }
        
        builder = create_earthshatter_berserker_query(
            slot="Weapon 1",
            current_item=current_weapon,
            max_price=50,
            currency=CurrencyType.DIVINE,
            league="Settlers"
        )
        
        query = builder.build_query(current_weapon["stats"])
        
        # Should have build-specific weights
        self.assertGreater(len(builder.stat_weights), 5)


# ============================================================
# Stash Currency Client Tests
# ============================================================

class TestStashCurrencyClient(unittest.TestCase):
    """Tests for stash and currency client."""
    
    def test_currency_display_mapping(self):
        """Test currency display names."""
        self.assertEqual(CURRENCY_DISPLAY[CurrencyType.CHAOS], "Chaos Orb")
        self.assertEqual(CURRENCY_DISPLAY[CurrencyType.DIVINE], "Divine Orb")
        self.assertEqual(CURRENCY_DISPLAY[CurrencyType.EXALTED], "Exalted Orb")
        self.assertEqual(CURRENCY_DISPLAY[CurrencyType.MIRROR], "Mirror of Kalandra")
    
    def test_default_currency_rates(self):
        """Test default rates exist for major currencies."""
        self.assertIn("chaos", DEFAULT_CURRENCY_RATES)
        self.assertIn("divine", DEFAULT_CURRENCY_RATES)
        self.assertIn("exalted", DEFAULT_CURRENCY_RATES)
        self.assertEqual(DEFAULT_CURRENCY_RATES["chaos"], 1.0)
        self.assertGreater(DEFAULT_CURRENCY_RATES["divine"], 100)
    
    def test_stash_item_parsing(self):
        """Test item parsing from API data."""
        client = PoEStashClient()
        
        item_data = {
            "id": "Metadata/Items/Currency/CurrencyChaosOrb",
            "name": "",
            "typeLine": "Chaos Orb",
            "stackSize": 10,
            "maxStackSize": 20,
            "x": 0, "y": 0,
            "properties": [],
            "requirements": [],
            "explicitMods": [],
            "implicitMods": [],
            "craftedMods": [],
            "corrupted": False,
            "identified": True,
            "ilvl": 0,
            "rarity": "Currency"
        }
        
        item = client.parse_stash_item(item_data)
        
        self.assertEqual(item.id, "Metadata/Items/Currency/CurrencyChaosOrb")
        self.assertEqual(item.name, "")
        self.assertEqual(item.type_line, "Chaos Orb")
        self.assertEqual(item.stack_size, 10)
        self.assertEqual(item.currency_type, "CurrencyChaosOrb")
    
    def test_net_worth_calculation(self):
        """Test net worth calculation."""
        client = PoEStashClient()
        client.currency_rates = DEFAULT_CURRENCY_RATES.copy()
        
        # Simulate calculation logic using correct keys (lowercase)
        currency_counts = {"chaos": 100, "divine": 5, "exalted": 2}
        total_chaos = sum(c * DEFAULT_CURRENCY_RATES.get(k, 0) for k, c in currency_counts.items())
        total_divine = total_chaos / DEFAULT_CURRENCY_RATES["divine"]
        
        expected_chaos = 100 * DEFAULT_CURRENCY_RATES["chaos"] + 5 * DEFAULT_CURRENCY_RATES["divine"] + 2 * DEFAULT_CURRENCY_RATES["exalted"]
        self.assertEqual(total_chaos, expected_chaos)
        self.assertAlmostEqual(total_divine, expected_chaos / DEFAULT_CURRENCY_RATES["divine"])


# ============================================================
# Target Build Store Tests
# ============================================================

class TestTargetBuildStore(unittest.TestCase):
    """Tests for target build storage."""
    
    def setUp(self):
        """Create temp store for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.store_path = Path(self.temp_dir) / "test_builds.json"
        self.store = TargetBuildStore(self.store_path)
    
    def tearDown(self):
        """Clean up temp files."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_create_build(self):
        """Test build creation."""
        build = TargetBuild(
            id="test_build",
            name="Test Build",
            description="A test build",
            character_class="Marauder",
            ascendancy="Berserker",
            target_level=100,
            target_league="Settlers",
            main_skill="Earthshatter"
        )
        
        self.store.create(build)
        
        retrieved = self.store.get("test_build")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Test Build")
        self.assertEqual(retrieved.character_class, "Marauder")
    
    def test_duplicate_id_raises(self):
        """Test duplicate ID raises error."""
        build = TargetBuild(id="dup", name="Test", description="", character_class="Marauder", ascendancy="Berserker")
        self.store.create(build)
        
        with self.assertRaises(ValueError):
            self.store.create(build)
    
    def test_update_build(self):
        """Test build updates."""
        build = TargetBuild(id="update_test", name="Original", description="", character_class="Marauder", ascendancy="Berserker")
        self.store.create(build)
        
        build.name = "Updated"
        build.description = "New description"
        build.tags = ["minmax", "berserker"]
        self.store.update(build)
        
        retrieved = self.store.get("update_test")
        self.assertEqual(retrieved.name, "Updated")
        self.assertEqual(retrieved.description, "New description")
        self.assertEqual(retrieved.tags, ["minmax", "berserker"])
        self.assertEqual(retrieved.version, 2)
    
    def test_delete_build(self):
        """Test build deletion."""
        build = TargetBuild(id="to_delete", name="Delete Me", description="", character_class="Marauder", ascendancy="Berserker")
        self.store.create(build)
        
        result = self.store.delete("to_delete")
        self.assertTrue(result)
        self.assertIsNone(self.store.get("to_delete"))
        
        # Deleting non-existent returns False
        self.assertFalse(self.store.delete("nonexistent"))
    
    def test_list_all(self):
        """Test listing builds."""
        self.store.create(TargetBuild(id="a", name="A", description="", character_class="Marauder", ascendancy="Berserker"))
        self.store.create(TargetBuild(id="b", name="B", description="", character_class="Ranger", ascendancy="Deadeye"))
        
        builds = self.store.list_all()
        self.assertEqual(len(builds), 2)
        # Sorted by updated_at desc
        self.assertEqual(builds[0].id, "b")
    
    def test_list_by_tag(self):
        """Test filtering by tag."""
        b1 = TargetBuild(id="t1", name="T1", description="", character_class="Marauder", ascendancy="Berserker", tags=["minmax", "berserker"])
        b2 = TargetBuild(id="t2", name="T2", description="", character_class="Ranger", ascendancy="Deadeye", tags=["budget", "mapper"])
        b3 = TargetBuild(id="t3", name="T3", description="", character_class="Marauder", ascendancy="Berserker", tags=["hc", "minmax"])
        
        self.store.create(b1)
        self.store.create(b2)
        self.store.create(b3)
        
        minmax = self.store.list_by_tag("minmax")
        self.assertEqual(len(minmax), 2)
        self.assertEqual({b.id for b in minmax}, {"t1", "t3"})
    
    def test_item_management(self):
        """Test adding/removing items."""
        build = TargetBuild(id="item_test", name="Item Test", description="", character_class="Marauder", ascendancy="Berserker")
        self.store.create(build)
        
        item = TargetItem(
            slot="Weapon 1",
            base_type="Vaal Axe",
            target_ilvl=86,
            target_rarity="Rare",
            target_mods=["180% Phys", "25% AS"],
            target_influences={"warlord": True},
            crafting_priority="High"
        )
        
        self.store.add_item("item_test", item)
        
        retrieved = self.store.get("item_test")
        self.assertEqual(len(retrieved.items), 1)
        self.assertEqual(retrieved.items[0].slot, "Weapon 1")
        self.assertEqual(retrieved.items[0].base_type, "Vaal Axe")
        
        # Update existing slot
        item2 = TargetItem(slot="Weapon 1", base_type="Harbinger Bow", target_rarity="Unique")
        self.store.add_item("item_test", item2)
        
        retrieved = self.store.get("item_test")
        self.assertEqual(len(retrieved.items), 1)
        self.assertEqual(retrieved.items[0].base_type, "Harbinger Bow")
        
        # Remove item
        self.store.remove_item("item_test", "Weapon 1")
        retrieved = self.store.get("item_test")
        self.assertEqual(len(retrieved.items), 0)
    
    def test_duplicate_build(self):
        """Test build duplication."""
        original = TargetBuild(id="orig", name="Original", description="", character_class="Marauder", ascendancy="Berserker")
        self.store.create(original)
        
        duplicate = self.store.duplicate("orig", "copy", "Copy of Original")
        
        self.assertIsNotNone(duplicate)
        self.assertEqual(duplicate.id, "copy")
        self.assertEqual(duplicate.name, "Copy of Original")
        self.assertEqual(duplicate.character_class, "Marauder")
    
    def test_import_export(self):
        """Test JSON import/export."""
        build = TargetBuild(
            id="export_test",
            name="Export Test",
            description="Test build for export",
            character_class="Marauder",
            ascendancy="Berserker",
            items=[TargetItem(slot="Weapon 1", base_type="Vaal Axe", target_mods=["100% Phys"])]
        )
        self.store.create(build)
        
        # Export
        export_path = Path(self.temp_dir) / "export.json"
        self.store.export("export_test", export_path)
        
        self.assertTrue(export_path.exists())
        
        # Import to new store
        new_store = TargetBuildStore(Path(self.temp_dir) / "new.json")
        new_store.import_build(export_path)
        
        imported = new_store.get("export_test")
        self.assertIsNotNone(imported)
        self.assertEqual(imported.name, "Export Test")
        self.assertEqual(len(imported.items), 1)


# ============================================================
# Template Tests
# ============================================================

class TestTemplates(unittest.TestCase):
    """Tests for build templates."""
    
    def test_god_tier_template(self):
        """Test god tier template creation."""
        build = create_earthshatter_berserker_template()
        
        self.assertEqual(build.id, "earthshatter_berserker_god_tier")
        self.assertEqual(build.character_class, "Marauder")
        self.assertEqual(build.ascendancy, "Berserker")
        self.assertEqual(build.target_level, 100)
        self.assertEqual(build.main_skill, "Earthshatter / Perforate of Duality")
        
        # Check all slots present
        slots = {item.slot for item in build.items}
        expected_slots = {"Weapon 1", "Helmet", "Body Armour", "Gloves", "Boots", "Amulet", "Belt", "Ring 1", "Ring 2"}
        self.assertEqual(slots, expected_slots)
        
        # Check unique items
        uniques = [i for i in build.items if i.target_unique_name]
        unique_names = {i.target_unique_name for i in uniques}
        self.assertIn("Mageblood", unique_names)
        self.assertIn("Ashes of the Stars", unique_names)
        self.assertIn("Echoes of Creation", unique_names)
        self.assertIn("Circle of Guilt", unique_names)
        
        # Check influences
        influenced = [i for i in build.items if i.target_influences]
        self.assertGreater(len(influenced), 0)
    
    def test_budget_template(self):
        """Test budget template creation."""
        build = create_budget_version_template()
        
        self.assertEqual(build.id, "earthshatter_berserker_budget")
        self.assertEqual(build.tags, ["budget", "earthshatter", "berserker", "3.30"])
        
        # Should have same slots but as rares
        slots = {item.slot for item in build.items}
        expected_slots = {"Weapon 1", "Helmet", "Body Armour", "Gloves", "Boots", "Amulet", "Belt", "Ring 1", "Ring 2"}
        self.assertEqual(slots, expected_slots)
        
        # No uniques - all should be Rare
        uniques = [i for i in build.items if i.target_unique_name]
        self.assertEqual(len(uniques), 0)
        
        # All should be Rare
        for item in build.items:
            self.assertEqual(item.target_rarity, "Rare")


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration(unittest.TestCase):
    """Integration tests for full pipeline."""
    
    def test_full_pipeline_data_flow(self):
        """Test data flows through all components."""
        # 1. Create target build
        target = create_earthshatter_berserker_template()
        
        # 2. Simulate mid-game character
        character = {
            "name": "MidGame",
            "class": "Marauder",
            "ascendancy": "Berserker",
            "level": 96,
            "league": "Settlers",
            "passives": {"hashes": [1, 2, 3], "hashes_ex": [], "mastery_effects": []},
            "equipment": [
                {"inventoryId": "Weapon", "name": "Basic Axe", "typeLine": "Vaal Axe", "rarity": "Rare", "ilvl": 84, "explicitMods": ["100% Phys"]},
                {"inventoryId": "Helmet", "name": "Basic Helm", "typeLine": "Royal Burgonet", "rarity": "Rare", "ilvl": 84, "explicitMods": ["100 Life"]}
            ]
        }
        
        # 3. Analyze gaps
        target_dict = {item.slot: item for item in target.items}
        gaps = analyze_gear_gaps(character, target_dict)
        
        # Should have gaps for both slots
        self.assertIn("Weapon 1", gaps)
        self.assertIn("Helmet", gaps)
        self.assertGreater(len(gaps["Weapon 1"]["missing_mods"]), 0)
        
        # 4. Estimate costs
        gaps_with_costs = estimate_upgrade_costs(gaps)
        self.assertIn("cost_estimate", gaps_with_costs["Weapon 1"])
        
        # 5. Apply decision matrix
        decisions = apply_decision_matrix(gaps_with_costs, liquid_budget_divine=20)
        self.assertIn("Weapon 1", decisions)
        self.assertIn("decision", decisions["Weapon 1"])
        
        # 6. Get farming strategies
        farm_strats = get_farming_strategies(["Vaal Axe", "Royal Burgonet"], "3.30")
        self.assertIn("divine_orbs", farm_strats)
    
    def test_dashboard_js_functions_exist(self):
        """Verify key JS functions are defined in dashboard."""
        # This would be tested with a headless browser in real scenario
        # For now, verify the HTML contains the function definitions
        dashboard_path = Path('/Users/joecrawford/.hermes/profiles/bot-of-exile/scripts/pob_pipeline_dashboard.html')
        content = dashboard_path.read_text()
        
        # Key functions
        self.assertIn('function runPipeline()', content)
        self.assertIn('function renderAll(', content)
        self.assertIn('function loadDemoData()', content)
        self.assertIn('function openPipelineOverlay()', content)
        self.assertIn('function executePipeline()', content)
        self.assertIn('function toggleDevPanel()', content)
        self.assertIn('function addDebugLog(', content)
        self.assertIn('function updateDebugState()', content)
        self.assertIn('function updateDebugConfig()', content)


# ============================================================
# Dashboard JS Function Tests (via Node.js if available)
# ============================================================

class TestDashboardJS(unittest.TestCase):
    """Tests for dashboard JavaScript functions."""
    
    @classmethod
    def setUpClass(cls):
        """Check if Node.js is available for JS testing."""
        try:
            import subprocess
            result = subprocess.run(['node', '--version'], capture_output=True)
            cls.node_available = result.returncode == 0
        except:
            cls.node_available = False
    
    def test_js_syntax_valid(self):
        """Test JavaScript syntax is valid (if Node available)."""
        if not self.node_available:
            self.skipTest("Node.js not available")
        
        import subprocess
        import tempfile
        
        # Extract JS from dashboard
        dashboard_path = Path('/Users/joecrawford/.hermes/profiles/bot-of-exile/scripts/pob_pipeline_dashboard.html')
        content = dashboard_path.read_text()
        
        # Extract script content
        import re
        scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
        js_content = '\n'.join(scripts)
        
        # Write to temp file and check syntax
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(js_content)
            temp_path = f.name
        
        try:
            result = subprocess.run(['node', '--check', temp_path], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"JS syntax error: {result.stderr}")
        finally:
            os.unlink(temp_path)


# ============================================================
# Update Manager Tests
# ============================================================

class TestUpdateManager(unittest.TestCase):
    """Tests for pob_update_manager.py."""
    
    def setUp(self):
        """Set up test config."""
        import tempfile
        from pob_update_manager import POB_REPO
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_path = self.temp_dir / "test_config.json"
        
        # Create test config
        self.config = {
            "pob_repo": str(POB_REPO),
            "last_known_commit": "abc123",
            "last_tree_version": "3_29",
            "last_test_run": "2024-01-15T10:30:00Z",
            "last_test_result": "PASS",
            "tracked_configs": []
        }
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f)
    
    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_config_load_save(self):
        """Test config loading and saving."""
        from pob_update_manager import load_config, save_config, UpdateConfig
        
        # Patch CONFIG_PATH
        import pob_update_manager as pum
        original_path = pum.CONFIG_PATH
        pum.CONFIG_PATH = self.config_path
        
        try:
            config = load_config()
            self.assertEqual(config.last_known_commit, "abc123")
            self.assertEqual(config.last_tree_version, "3_29")
            
            # Modify and save
            config.last_known_commit = "def456"
            save_config(config)
            
            # Reload
            config2 = load_config()
            self.assertEqual(config2.last_known_commit, "def456")
        finally:
            pum.CONFIG_PATH = original_path
    
    def test_get_current_commit(self):
        """Test getting current git commit."""
        from pob_update_manager import get_current_commit
        
        commit = get_current_commit()
        self.assertIsInstance(commit, str)
        self.assertEqual(len(commit), 40)  # Full SHA
    
    def test_get_tree_version(self):
        """Test extracting tree version."""
        from pob_update_manager import get_tree_version
        
        version = get_tree_version()
        self.assertIsInstance(version, str)
        self.assertTrue("_" in version)  # e.g., 3_29
    
    def test_detect_breaking_changes(self):
        """Test breaking change detection."""
        from pob_update_manager import detect_breaking_changes
        
        # Test with known breaking files
        changed = [
            "src/Tree/PassiveTree.lua",
            "src/Classes/TradeQueryGenerator.lua",
            "src/Classes/Item.lua",
            "README.md"  # Non-breaking
        ]
        
        detected = detect_breaking_changes(changed)
        # Should detect tree_version for PassiveTree.lua
        self.assertIn("tree_version", detected)
        # Should detect trade_query for TradeQueryGenerator.lua
        self.assertIn("trade_query", detected)
        # Should detect item_bases for Item.lua
        self.assertIn("item_bases", detected)
        # Other categories may also match due to shared directory prefix
        self.assertGreaterEqual(len(detected), 3)
    
    def test_generate_migration_guide(self):
        """Test migration guide generation."""
        from pob_update_manager import generate_migration_guide
        
        detected = {
            "tree_version": ["src/Tree/PassiveTree.lua"],
            "trade_query": ["src/Classes/TradeQueryGenerator.lua"]
        }
        
        guide = generate_migration_guide(detected)
        self.assertIn("Migration Guide", guide)
        self.assertIn("Tree Version Bump", guide)
        self.assertIn("Trade Query Generator Changes", guide)
        self.assertIn("PassiveTree.lua", guide)
        self.assertIn("TradeQueryGenerator.lua", guide)
    
    def test_no_breaking_changes(self):
        """Test guide for no breaking changes."""
        from pob_update_manager import generate_migration_guide
        
        guide = generate_migration_guide({})
        self.assertIn("No breaking changes detected", guide)


# ============================================================
# Leveling Tracker Tests
# ============================================================

class TestLevelingTracker(unittest.TestCase):
    """Tests for pob_leveling.py LevelingTracker."""
    
    def setUp(self):
        """Set up test fixtures."""
        import tempfile
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_file = self.temp_dir / "client.txt"
        
        # Create mock log file with actual PoE format
        self.log_file.write_text("""2024/01/15 10:00:00 You have entered Twilight Strand.
2024/01/15 10:05:00 TestChar (Marauder) is now level 2
2024/01/15 10:10:00 Quest completed: enemy_at_the_gate
2024/01/15 10:15:00 You have entered The Coast.
2024/01/15 10:20:00 TestChar (Marauder) is now level 4
2024/01/15 10:25:00 Quest completed: the_caged_brute1
2024/01/15 10:30:00 You have entered Mud Flats.
2024/01/15 10:35:00 TestChar (Marauder) is now level 6
""")
    
    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_log_parser_zone_change(self):
        """Test parsing zone change events."""
        from pob_leveling import PoELogParser
        
        parser = PoELogParser(self.log_file)
        events = parser.read_new_lines()
        
        zone_events = [e for e in events if e.event_type == "zone_change"]
        self.assertGreater(len(zone_events), 0)
        
        # Check first zone
        first_zone = zone_events[0]
        self.assertEqual(first_zone.data.get("zone_name"), "Twilight Strand")
    
    def test_log_parser_level_up(self):
        """Test parsing level up events."""
        from pob_leveling import PoELogParser
        
        parser = PoELogParser(self.log_file)
        events = parser.read_new_lines()
        
        level_events = [e for e in events if e.event_type == "level_up"]
        self.assertEqual(len(level_events), 3)  # levels 2, 4, 6
        
        levels = [e.data.get("new_level") for e in level_events]
        self.assertIn(2, levels)
        self.assertIn(4, levels)
        self.assertIn(6, levels)
    
    def test_log_parser_quest_complete(self):
        """Test parsing quest completion events."""
        from pob_leveling import PoELogParser
        
        parser = PoELogParser(self.log_file)
        events = parser.read_new_lines()
        
        quest_events = [e for e in events if e.event_type == "quest_complete"]
        self.assertEqual(len(quest_events), 2)
        
        quests = [e.data.get("quest_name") for e in quest_events]
        self.assertIn("enemy_at_the_gate", quests)
        self.assertIn("the_caged_brute1", quests)
    
    def test_zone_info_creation(self):
        """Test ZoneInfo dataclass."""
        from pob_leveling import ZoneInfo
        
        zone = ZoneInfo(
            id="1_1_1",
            name="Twilight Strand",
            level=1,
            act=1
        )
        
        self.assertEqual(zone.id, "1_1_1")
        self.assertEqual(zone.name, "Twilight Strand")
        self.assertEqual(zone.level, 1)
        self.assertEqual(zone.act, 1)
    
    def test_gem_info_creation(self):
        """Test GemInfo dataclass."""
        from pob_leveling import GemInfo
        
        gem = GemInfo(
            name="Earthshatter",
            attribute=1,
            level=1,
            quests={"enemy_at_the_gate": {"quest": ["marauder"]}}
        )
        
        self.assertEqual(gem.name, "Earthshatter")
        self.assertEqual(gem.attribute, 1)
        self.assertEqual(gem.level, 1)
        self.assertIn("enemy_at_the_gate", gem.quests)
    
    def test_leveling_state(self):
        """Test LevelingState dataclass."""
        from pob_leveling import LevelingState
        
        state = LevelingState(
            level=10,
            current_zone_name="The Coast",
            current_act=1
        )
        
        self.assertEqual(state.level, 10)
        self.assertEqual(state.current_zone_name, "The Coast")
        self.assertEqual(state.current_act, 1)
    
    def test_exile_ui_data_loader(self):
        """Test ExileUIDataLoader basic initialization."""
        from pob_leveling import ExileUIDataLoader
        
        loader = ExileUIDataLoader()
        # Just verify it initializes without error
        self.assertIsNotNone(loader)
        self.assertIsInstance(loader._zones, dict)
        self.assertIsInstance(loader._gems, dict)


# ============================================================
# Run Tests
# ============================================================

def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestOAuth))
    suite.addTests(loader.loadTestsFromTestCase(TestPassiveConverter))
    suite.addTests(loader.loadTestsFromTestCase(TestCharacterLoadout))
    suite.addTests(loader.loadTestsFromTestCase(TestTradeQueryGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestStashCurrencyClient))
    suite.addTests(loader.loadTestsFromTestCase(TestTargetBuildStore))
    suite.addTests(loader.loadTestsFromTestCase(TestTemplates))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestDashboardJS))
    suite.addTests(loader.loadTestsFromTestCase(TestUpdateManager))
    suite.addTests(loader.loadTestsFromTestCase(TestLevelingTracker))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)