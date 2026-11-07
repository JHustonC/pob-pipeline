#!/usr/bin/env python3
"""
PoB Trade Query Generator - Python Wrapper
===========================================
Python interface to PoB's TradeQueryGenerator for building weighted trade queries.
Can be used standalone or as a bridge to headless PoB.
"""

import json
import base64
import urllib.parse
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class CurrencyType(Enum):
    CHAOS = "chaos"
    DIVINE = "divine"
    EXALTED = "exalted"
    MIRROR = "mirror"
    ANCIENT_ORB = "ancient-orb"
    ANCIENT_ORB_OF_ANNULMENT = "orb-of-annulment"


class ItemCategory(Enum):
    # Weapons
    CLAW = "claw"
    DAGGER = "dagger"
    ONE_HAND_AXE = "one-hand-axe"
    ONE_HAND_MACE = "one-hand-mace"
    ONE_HAND_SWORD = "one-hand-sword"
    RUNE_DAGGER = "rune-dagger"
    SCEPTRE = "sceptre"
    STAFF = "staff"
    WARSTAFF = "warstaff"
    TWO_HAND_AXE = "two-hand-axe"
    TWO_HAND_MACE = "two-hand-mace"
    TWO_HAND_SWORD = "two-hand-sword"
    BOW = "bow"
    WAND = "wand"
    FISHING_ROD = "fishing-rod"
    # Armour
    HELMET = "helmet"
    BODY_ARMOUR = "body-armour"
    GLOVES = "gloves"
    BOOTS = "boots"
    SHIELD = "shield"
    QUIVER = "quiver"
    # Accessories
    AMULET = "amulet"
    RING = "ring"
    BELT = "belt"
    # Flasks
    LIFE_FLASK = "life-flask"
    MANA_FLASK = "mana-flask"
    UTILITY_FLASK = "utility-flask"
    # Jewels
    JEWEL = "jewel"
    ABYSS_JEWEL = "abyss-jewel"
    # Other
    MAP = "map"


# Slot to category mapping
SLOT_CATEGORY_MAP = {
    "Weapon 1": ItemCategory.ONE_HAND_AXE,  # Will be overridden by base type
    "Weapon 2": ItemCategory.SHIELD,
    "Helmet": ItemCategory.HELMET,
    "Body Armour": ItemCategory.BODY_ARMOUR,
    "Gloves": ItemCategory.GLOVES,
    "Boots": ItemCategory.BOOTS,
    "Amulet": ItemCategory.AMULET,
    "Ring 1": ItemCategory.RING,
    "Ring 2": ItemCategory.RING,
    "Belt": ItemCategory.BELT,
    "Flask 1": ItemCategory.LIFE_FLASK,
    "Flask 2": ItemCategory.MANA_FLASK,
    "Flask 3": ItemCategory.UTILITY_FLASK,
    "Flask 4": ItemCategory.UTILITY_FLASK,
    "Flask 5": ItemCategory.UTILITY_FLASK,
}


# Stat weight definitions (matching PoB's TradeQueryGenerator)
STAT_WEIGHTS = {
    # Offensive
    "FullDPS": {"weight": 1.0, "transform": None},
    "TotalDPS": {"weight": 1.0, "transform": None},
    "TotalDotDPS": {"weight": 0.5, "transform": None},
    "CombinedDPS": {"weight": 1.0, "transform": None},
    "PhysicalDPS": {"weight": 0.8, "transform": None},
    "ElementalDPS": {"weight": 0.8, "transform": None},
    "ChaosDPS": {"weight": 0.5, "transform": None},
    "AttackSpeed": {"weight": 0.6, "transform": None},
    "CriticalStrikeChance": {"weight": 0.7, "transform": None},
    "CriticalStrikeMultiplier": {"weight": 0.7, "transform": None},
    "ImpaleChance": {"weight": 0.5, "transform": None},
    "ImpaleEffect": {"weight": 0.4, "transform": None},
    
    # Defensive
    "EffectiveHitPool": {"weight": 0.8, "transform": None},  # EHP
    "MaxLife": {"weight": 0.6, "transform": None},
    "MaxEnergyShield": {"weight": 0.5, "transform": None},
    "MaxMana": {"weight": 0.2, "transform": None},
    "Armour": {"weight": 0.4, "transform": None},
    "Evasion": {"weight": 0.4, "transform": None},
    "EnergyShield": {"weight": 0.4, "transform": None},
    "PhysicalDamageReduction": {"weight": 0.5, "transform": None},
    "BlockChance": {"weight": 0.3, "transform": None},
    "SpellBlockChance": {"weight": 0.3, "transform": None},
    "SpellSuppressionChance": {"weight": 0.4, "transform": None},
    "SpellDodgeChance": {"weight": 0.2, "transform": None},
    "AttackDodgeChance": {"weight": 0.2, "transform": None},
    
    # Resistances (lower is better - transform negates)
    "FireResist": {"weight": 0.4, "transform": "cap_at_max"},
    "ColdResist": {"weight": 0.4, "transform": "cap_at_max"},
    "LightningResist": {"weight": 0.4, "transform": "cap_at_max"},
    "ChaosResist": {"weight": 0.5, "transform": "cap_at_max"},
    "AllResist": {"weight": 0.6, "transform": "cap_at_max"},
    "MaxFireResist": {"weight": 0.5, "transform": None},
    "MaxColdResist": {"weight": 0.5, "transform": None},
    "MaxLightningResist": {"weight": 0.5, "transform": None},
    "MaxChaosResist": {"weight": 0.5, "transform": None},
    
    # Attributes
    "Strength": {"weight": 0.1, "transform": None},
    "Dexterity": {"weight": 0.1, "transform": None},
    "Intelligence": {"weight": 0.1, "transform": None},
    "AllAttributes": {"weight": 0.2, "transform": None},
    
    # Utility
    "MovementSpeed": {"weight": 0.3, "transform": None},
    "LifeRegeneration": {"weight": 0.3, "transform": None},
    "ManaRegeneration": {"weight": 0.2, "transform": None},
    "LifeRecoveryRate": {"weight": 0.3, "transform": None},
    "LifeGainOnKill": {"weight": 0.2, "transform": None},
    "LifeLeechRate": {"weight": 0.3, "transform": None},
    "ManaLeechRate": {"weight": 0.2, "transform": None},
}


@dataclass
class StatWeight:
    """Single stat weight entry."""
    stat_id: str
    weight: float
    transform: Optional[str] = None  # "cap_at_max" for resistances
    min_value: Optional[float] = None
    current_value: Optional[float] = None


@dataclass
class ItemStat:
    """Item stat for trade query."""
    id: str
    value: Optional[Dict[str, float]] = None  # {"min": x, "max": y}
    disabled: bool = False


@dataclass
class TradeFilter:
    """Trade filter for query."""
    filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TradeQuery:
    """Complete trade query structure."""
    query: Dict[str, Any] = field(default_factory=dict)
    sort: Dict[str, str] = field(default_factory=lambda: {"price": "asc"})


class TradeQueryBuilder:
    """Builds weighted trade queries for PoE trade site."""
    
    def __init__(
        self,
        league: str = "Settlers",
        max_price: float = 50,
        currency: CurrencyType = CurrencyType.DIVINE,
        character_level: int = 95,
        character_attributes: Optional[Dict[str, int]] = None
    ):
        self.league = league
        self.max_price = max_price
        self.currency = currency
        self.character_level = character_level
        self.character_attributes = character_attributes or {}
        self.stat_weights: List[StatWeight] = []
        self.custom_filters: List[Dict] = []
        
    def add_stat_weight(self, stat_id: str, weight: float, transform: Optional[str] = None):
        """Add a stat weight for query generation."""
        self.stat_weights.append(StatWeight(
            stat_id=stat_id,
            weight=weight,
            transform=transform
        ))
        return self
    
    def set_current_stat(self, stat_id: str, value: float):
        """Set current item stat value for min calculation."""
        for sw in self.stat_weights:
            if sw.stat_id == stat_id:
                sw.current_value = value
                break
        return self
    
    def add_custom_filter(self, filter_dict: Dict):
        """Add a custom trade filter."""
        self.custom_filters.append(filter_dict)
        return self
    
    def set_category(self, category: ItemCategory):
        """Set item category filter."""
        self.category = category
        return self
    
    def build_query(self, current_item_stats: Optional[Dict[str, float]] = None) -> TradeQuery:
        """Build the complete trade query."""
        
        # Build stat filters from weights
        stat_filters = []
        
        for sw in self.stat_weights:
            if sw.weight < 0.1:
                continue  # Skip negligible weights
            
            # Determine min value
            min_val = sw.min_value
            if min_val is None and sw.current_value is not None:
                # Default: at least 90% of current value
                min_val = sw.current_value * 0.9
            elif min_val is None and current_item_stats and sw.stat_id in current_item_stats:
                min_val = current_item_stats[sw.stat_id] * 0.9
            
            if min_val is not None:
                filter_entry = {
                    "id": sw.stat_id,
                    "value": {"min": min_val}
                }
                if sw.transform == "cap_at_max":
                    filter_entry["value"]["max"] = 90  # Cap resistances at 90% (overcapped doesn't help)
                stat_filters.append(filter_entry)
        
        # Build query structure
        query = {
            "query": {
                "status": {"option": "online"},
                "stats": [{
                    "type": "and",
                    "filters": stat_filters
                }],
                "filters": {
                    "type_filters": {
                        "filters": {
                            "category": {"option": self.category.value if hasattr(self, 'category') else "any"}
                        }
                    },
                    "trade_filters": {
                        "filters": {
                            "price": {"max": self.max_price, "currency": self.currency.value},
                            "level": {"max": self.character_level}
                        }
                    }
                }
            },
            "sort": {"price": "asc"}
        }
        
        # Add attribute requirement filters
        if self.character_attributes:
            attr_filters = query["query"]["filters"]["trade_filters"]["filters"]
            if "strength" in self.character_attributes:
                attr_filters["strength"] = {"max": self.character_attributes["strength"]}
            if "dexterity" in self.character_attributes:
                attr_filters["dexterity"] = {"max": self.character_attributes["dexterity"]}
            if "intelligence" in self.character_attributes:
                attr_filters["intelligence"] = {"max": self.character_attributes["intelligence"]}
        
        # Add custom filters
        for cf in self.custom_filters:
            # Merge custom filters appropriately
            pass
        
        return TradeQuery(query=query)
    
    def to_trade_url(self, trade_query: TradeQuery) -> str:
        """Convert query to PoE trade site URL."""
        encoded = base64.urlsafe_b64encode(
            json.dumps(trade_query.query, separators=(',', ':')).encode()
        ).decode().rstrip('=')
        return f"https://www.pathofexile.com/trade/search/{self.league}/{encoded}"
    
    def to_json(self, trade_query: TradeQuery) -> str:
        """Serialize query to JSON."""
        return json.dumps(trade_query.query, indent=2)


def create_earthshatter_berserker_query(
    slot: str,
    current_item: Dict,
    max_price: float = 50,
    currency: CurrencyType = CurrencyType.DIVINE,
    league: str = "Settlers"
) -> TradeQueryBuilder:
    """Create a query builder pre-configured for Earthshatter Berserker."""
    
    builder = TradeQueryBuilder(
        league=league,
        max_price=max_price,
        currency=currency,
        character_level=96,
        character_attributes={"strength": 212, "dexterity": 100, "intelligence": 50}
    )
    
    # Map slot to category
    if slot in SLOT_CATEGORY_MAP:
        builder.set_category(SLOT_CATEGORY_MAP[slot])
    
    # Add build-specific stat weights
    # Earthshatter Berserker priorities:
    build_weights = {
        "FullDPS": 1.0,
        "TotalDPS": 0.8,
        "AttackSpeed": 0.6,
        "CriticalStrikeChance": 0.7,
        "CriticalStrikeMultiplier": 0.7,
        "EffectiveHitPool": 0.8,
        "MaxLife": 0.6,
        "Armour": 0.4,
        "PhysicalDamageReduction": 0.5,
        "AllResist": 0.6,
        "FireResist": 0.4,
        "ColdResist": 0.4,
        "LightningResist": 0.4,
        "ChaosResist": 0.5,
        "MaxFireResist": 0.5,
        "MaxColdResist": 0.5,
        "MaxLightningResist": 0.5,
        "ImpaleChance": 0.5,
        "ImpaleEffect": 0.4,
    }
    
    for stat_id, weight in build_weights.items():
        builder.add_stat_weight(stat_id, weight)
    
    # Set current item stats for min calculation
    if current_item and "stats" in current_item:
        for stat_id, value in current_item["stats"].items():
            builder.set_current_stat(stat_id, value)
    
    return builder


# ============================================================
# Trade API Client
# ============================================================

class TradeAPIClient:
    """Client for PoE Trade API."""
    
    BASE_URL = "https://www.pathofexile.com/api/trade"
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id
        self.headers = {
            "User-Agent": "PoB-TradeQueryGenerator/1.0",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if session_id:
            self.headers["Cookie"] = f"POESESSID={session_id}"
    
    def search(self, league: str, query: Dict) -> Dict:
        """Execute a trade search."""
        import requests
        url = f"{self.BASE_URL}/search/{league}"
        response = requests.post(url, json=query, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def fetch_results(self, league: str, result_ids: List[str], query_id: str) -> Dict:
        """Fetch detailed results for search results."""
        import requests
        ids = ",".join(result_ids)
        url = f"{self.BASE_URL}/fetch/{ids}?query={query_id}"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def get_search_query(self, league: str, query_id: str) -> Dict:
        """Get the saved query."""
        import requests
        url = f"{self.BASE_URL}/search/{league}/{query_id}"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()


# ============================================================
# Example Usage
# ============================================================

if __name__ == "__main__":
    # Example: Create query for Earthshatter Berserker Weapon upgrade
    current_weapon = {
        "name": "Carrion Sever",
        "base": "Vaal Axe",
        "ilvl": 84,
        "stats": {
            "FullDPS": 500000,
            "TotalDPS": 500000,
            "AttackSpeed": 1.56,
            "CriticalStrikeChance": 5.0,
            "CriticalStrikeMultiplier": 150,
            "EffectiveHitPool": 50000,
            "MaxLife": 4000,
            "Armour": 0,
            "AllResist": 77,
            "FireResist": 90,
            "ColdResist": 90,
            "LightningResist": 90,
            "ChaosResist": 77,
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
    url = builder.to_trade_url(query)
    
    print("=== Trade Query Generated ===")
    print(f"URL: {url}")
    print(f"\nJSON Query:")
    print(builder.to_json(query))
    
    # Example: Search with API (requires session_id for larger queries)
    # client = TradeAPIClient(session_id="YOUR_POESESSID")
    # result = client.search("Settlers", query.query)
    # print(f"Found {result.get('total', 0)} results")