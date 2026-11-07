#!/usr/bin/env python3
"""
PoE Stash & Currency API Client with OAuth Integration
=======================================================
Complete client for accessing GGG's stash and currency exchange APIs.
Integrates with pob_oauth_import.py for authentication.
"""

import os
import json
import time
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

# Import OAuth client
import sys
sys.path.insert(0, '/Users/joecrawford/.hermes/profiles/bot-of-exile/scripts')
from pob_oauth_import import PoEAPIClient, run_oauth_flow, load_tokens, save_tokens


class CurrencyType(Enum):
    """Standard currency items."""
    CHAOS = "CurrencyChaosOrb"
    DIVINE = "CurrencyDivineOrb"
    EXALTED = "CurrencyExaltedOrb"
    MIRROR_SHARD = "CurrencyMirrorShard"
    MIRROR = "CurrencyMirror"
    ANCIENT_ORB = "CurrencyAncientOrb"
    ORB_OF_ANNULMENT = "CurrencyOrbOfAnnulment"
    VAAL_ORB = "CurrencyVaalOrb"
    ORB_OF_REGRET = "CurrencyOrbOfRegret"
    CARTOGRAPHERS_CHISEL = "CurrencyCartographersChisel"
    GEMCUTTERS_PRIM = "CurrencyGemcuttersPrism"
    ORB_OF_FUSING = "CurrencyOrbOfFusing"
    ORB_OF_ALCHEMY = "CurrencyOrbOfAlchemy"
    ORB_OF_ALTERATION = "CurrencyOrbOfAlteration"
    ORB_OF_AUGMENTATION = "CurrencyOrbOfAugmentation"
    ORB_OF_CHANCE = "CurrencyOrbOfChance"
    ORB_OF_SCOURING = "CurrencyOrbOfScouring"
    ORB_OF_TRANSMUTATION = "CurrencyOrbOfTransmutation"
    BLESSED_ORB = "CurrencyBlessedOrb"
    DIVINE_ORB = "CurrencyDivineOrb"
    EXALTED_ORB = "CurrencyExaltedOrb"
    MIRROR_OF_KALANDRA = "CurrencyMirror"


# Currency ID to display name mapping
CURRENCY_DISPLAY = {
    CurrencyType.CHAOS: "Chaos Orb",
    CurrencyType.DIVINE: "Divine Orb",
    CurrencyType.EXALTED: "Exalted Orb",
    CurrencyType.MIRROR_SHARD: "Mirror Shard",
    CurrencyType.MIRROR: "Mirror of Kalandra",
    CurrencyType.ORB_OF_ANNULMENT: "Orb of Annulment",
    CurrencyType.VAAL_ORB: "Vaal Orb",
    CurrencyType.ORB_OF_REGRET: "Orb of Regret",
    CurrencyType.CARTOGRAPHERS_CHISEL: "Cartographer's Chisel",
    CurrencyType.GEMCUTTERS_PRIM: "Gemcutter's Prism",
    CurrencyType.ORB_OF_FUSING: "Orb of Fusing",
    CurrencyType.ORB_OF_ALCHEMY: "Orb of Alchemy",
    CurrencyType.ORB_OF_ALTERATION: "Orb of Alteration",
    CurrencyType.ORB_OF_AUGMENTATION: "Orb of Augmentation",
    CurrencyType.ORB_OF_CHANCE: "Orb of Chance",
    CurrencyType.ORB_OF_SCOURING: "Orb of Scouring",
    CurrencyType.ORB_OF_TRANSMUTATION: "Orb of Transmutation",
}

# Currency to chaos equivalent rates (approximate, updated from API)
DEFAULT_CURRENCY_RATES = {
    "chaos": 1.0,
    "divine": 200.0,
    "exalted": 80.0,
    "mirror_shard": 1.0,
    "mirror": 20000.0,
    "annulment": 15.0,
    "vaal": 1.5,
    "regret": 0.5,
    "chisel": 1.5,
    "gemcutter": 8.0,
    "fusing": 0.3,
    "alchemy": 0.2,
    "alteration": 0.01,
    "augmentation": 0.01,
    "chance": 0.5,
    "scouring": 0.2,
    "transmutation": 0.01,
}


@dataclass
class StashTab:
    """Represents a stash tab."""
    id: str
    name: str
    type: str  # "CurrencyStash", "NormalStash", "QuadStash", etc.
    league: str
    items: List[Dict] = field(default_factory=list)
    item_count: int = 0


@dataclass
class StashItem:
    """Item in a stash tab."""
    id: str  # Full item ID (e.g., "Metadata/Items/Currency/CurrencyChaosOrb")
    name: str
    type_line: str
    stack_size: int
    max_stack_size: int
    x: int
    y: int
    properties: List[Dict] = field(default_factory=list)
    requirements: List[Dict] = field(default_factory=list)
    explicit_mods: List[str] = field(default_factory=list)
    implicit_mods: List[str] = field(default_factory=list)
    crafted_mods: List[str] = field(default_factory=list)
    corrupted: bool = False
    identified: bool = True
    ilvl: int = 0
    rarity: str = "Normal"
    influences: Dict[str, bool] = field(default_factory=dict)
    sockets: List[Dict] = field(default_factory=list)
    # For currency
    currency_type: Optional[str] = None


@dataclass
class NetWorth:
    """Calculated net worth."""
    currency_counts: Dict[str, int] = field(default_factory=dict)
    currency_rates: Dict[str, float] = field(default_factory=dict)
    total_chaos_equiv: float = 0.0
    total_divine_equiv: float = 0.0
    liquid_currency: Dict[str, int] = field(default_factory=dict)
    calculated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class PoEStashClient:
    """Client for PoE Stash and Currency APIs."""
    
    def __init__(
        self,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        realm: str = "pc",
        currency_rates: Optional[Dict[str, float]] = None
    ):
        self.realm = realm
        self.currency_rates = currency_rates or DEFAULT_CURRENCY_RATES.copy()
        self.api_client = PoEAPIClient(
            access_token=access_token,
            refresh_token=refresh_token
        ) if access_token else None
        self.session = requests.Session()
        
        if access_token:
            self.session.headers["Authorization"] = f"Bearer {access_token}"
    
    @classmethod
    def from_oauth_flow(cls, realm: str = "pc") -> "PoEStashClient":
        """Create client by running OAuth flow."""
        client = run_oauth_flow()
        save_tokens(client)
        return cls(
            access_token=client.access_token,
            refresh_token=client.refresh_token,
            realm=realm
        )
    
    @classmethod
    def from_saved_tokens(cls, realm: str = "pc", token_file: str = "poe_tokens.json") -> Optional["PoEStashClient"]:
        """Create client from saved tokens."""
        client = load_tokens(token_file)
        if not client:
            return None
        return cls(
            access_token=client.access_token,
            refresh_token=client.refresh_token,
            realm=realm
        )
    
    def _ensure_auth(self) -> bool:
        """Ensure we have valid authentication."""
        if not self.api_client:
            return False
        # The PoEAPIClient handles auto-refresh internally
        return True
    
    def get_stashes(self, league: str) -> List[StashTab]:
        """Get all stash tabs in a league."""
        if not self._ensure_auth():
            raise ValueError("Not authenticated. Run OAuth flow first.")
        
        realm_path = "" if self.realm == "pc" else f"/{self.realm}"
        url = f"https://api.pathofexile.com/stash{realm_path}/{league}"
        
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        stashes = []
        
        for tab_data in data.get("stashes", []):
            tab = StashTab(
                id=tab_data.get("id", ""),
                name=tab_data.get("name", ""),
                type=tab_data.get("type", "NormalStash"),
                league=league,
                item_count=len(tab_data.get("items", []))
            )
            tab.items = tab_data.get("items", [])
            stashes.append(tab)
        
        return stashes
    
    def get_stash_items(self, league: str, stash_id: str) -> List[Dict]:
        """Get items in a specific stash tab."""
        if not self._ensure_auth():
            raise ValueError("Not authenticated.")
        
        realm_path = "" if self.realm == "pc" else f"/{self.realm}"
        url = f"https://api.pathofexile.com/stash{realm_path}/{league}/{stash_id}"
        
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        
        return response.json().get("items", [])
    
    def parse_stash_item(self, item_data: Dict) -> StashItem:
        """Parse raw API item data into StashItem."""
        item_id = item_data.get("id", "")
        
        # Determine currency type
        currency_type = None
        if item_id.startswith("Metadata/Items/Currency/"):
            currency_type = item_id.split("/")[-1]
        
        return StashItem(
            id=item_id,
            name=item_data.get("name", ""),
            type_line=item_data.get("typeLine", ""),
            stack_size=item_data.get("stackSize", 1),
            max_stack_size=item_data.get("maxStackSize", 1),
            x=item_data.get("x", 0),
            y=item_data.get("y", 0),
            properties=item_data.get("properties", []),
            requirements=item_data.get("requirements", []),
            explicit_mods=item_data.get("explicitMods", []),
            implicit_mods=item_data.get("implicitMods", []),
            crafted_mods=item_data.get("craftedMods", []),
            corrupted=item_data.get("corrupted", False),
            identified=item_data.get("identified", True),
            ilvl=item_data.get("ilvl", 0),
            rarity=item_data.get("rarity", "Normal"),
            influences={
                "shaper": item_data.get("shaper", False),
                "elder": item_data.get("elder", False),
                "crusader": item_data.get("crusader", False),
                "redeemer": item_data.get("redeemer", False),
                "hunter": item_data.get("hunter", False),
                "warlord": item_data.get("warlord", False)
            },
            sockets=item_data.get("sockets", []),
            currency_type=currency_type
        )
    
    def get_all_stash_items(self, league: str) -> List[StashItem]:
        """Get all items from all stash tabs in a league."""
        stashes = self.get_stashes(league)
        all_items = []
        
        for tab in stashes:
            # For currency stashes, items are already in tab.items
            if tab.type == "CurrencyStash":
                for item_data in tab.items:
                    all_items.append(self.parse_stash_item(item_data))
            else:
                # For other tabs, we might need to fetch individually
                items = self.get_stash_items(league, tab.id)
                for item_data in items:
                    all_items.append(self.parse_stash_item(item_data))
        
        return all_items
    
    def get_currency_exchange_rates(self, realm: Optional[str] = None) -> Dict[str, float]:
        """Get current currency exchange rates from public CDN."""
        r = realm or self.realm
        url = f"https://web.poecdn.com/api/currency-exchange/{r}"
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        rates = {}
        
        # Parse the hourly digest
        for market in data.get("markets", []):
            pair = market.get("market_pair", [])
            if len(pair) == 2:
                from_curr, to_curr = pair
                # Store both directions
                buy_price = market.get("buy_price", 0)
                sell_price = market.get("sell_price", 0)
                
                if buy_price > 0:
                    rates[f"{from_curr}_to_{to_curr}"] = buy_price
                if sell_price > 0:
                    rates[f"{to_curr}_to_{from_curr}"] = 1.0 / sell_price if sell_price > 0 else 0
        
        return rates
    
    def calculate_net_worth(
        self,
        league: str,
        currency_rates: Optional[Dict[str, float]] = None,
        liquid_only: bool = False
    ) -> NetWorth:
        """Calculate total net worth from stashes."""
        
        rates = currency_rates or self.currency_rates
        items = self.get_all_stash_items(league)
        
        currency_counts = {}
        total_chaos = 0.0
        
        # Currency items that are liquid (easily tradable)
        liquid_currencies = {
            "CurrencyChaosOrb", "CurrencyDivineOrb", "CurrencyExaltedOrb",
            "CurrencyMirrorShard", "CurrencyMirror", "CurrencyOrbOfAnnulment",
            "CurrencyVaalOrb", "CurrencyOrbOfRegret", "CurrencyCartographersChisel",
            "CurrencyGemcuttersPrism", "CurrencyOrbOfFusing", "CurrencyOrbOfAlchemy"
        }
        
        for item in items:
            if item.currency_type:
                currency_name = item.currency_type
                count = item.stack_size
                
                currency_counts[currency_name] = currency_counts.get(currency_name, 0) + count
                
                # Calculate chaos equivalent
                if currency_name in DEFAULT_CURRENCY_RATES:
                    chaos_value = count * DEFAULT_CURRENCY_RATES[currency_name]
                    total_chaos += chaos_value
        
        # Calculate liquid currency
        liquid = {}
        for curr, count in currency_counts.items():
            if curr in liquid_currencies:
                liquid[curr] = count
        
        divine_rate = rates.get("divine", DEFAULT_CURRENCY_RATES.get("divine", 200))
        
        return NetWorth(
            currency_counts=currency_counts,
            currency_rates=rates,
            total_chaos_equiv=sum(c * DEFAULT_CURRENCY_RATES.get(k, 0) for k, c in currency_counts.items()),
            total_divine_equiv=sum(c * DEFAULT_CURRENCY_RATES.get(k, 0) for k, c in currency_counts.items()) / max(divine_rate, 1),
            liquid_currency=liquid,
            calculated_at=datetime.now().isoformat()
        )
    
    def get_character_stash_summary(self, character_name: str, league: str) -> Dict:
        """Get stash summary for a specific character's league."""
        net_worth = self.calculate_net_worth(league)
        
        return {
            "character": character_name,
            "league": league,
            "net_worth": {
                "total_chaos_equiv": net_worth.total_chaos_equiv,
                "total_divine_equiv": net_worth.total_divine_equiv,
                "currency_counts": net_worth.currency_counts,
                "liquid_currency": net_worth.liquid_currency,
                "calculated_at": net_worth.calculated_at
            },
            "upgrade_budget_recommendations": {
                "conservative": net_worth.total_divine_equiv * 0.2,  # 20%
                "moderate": net_worth.total_divine_equiv * 0.3,      # 30%
                "aggressive": net_worth.total_divine_equiv * 0.5     # 50%
            }
        }


def create_client_from_saved_tokens(realm: str = "pc") -> Optional[PoEStashClient]:
    """Helper to create client from saved tokens or run OAuth flow."""
    client = PoEStashClient.from_saved_tokens(realm)
    if client:
        print("✅ Loaded saved tokens")
        return client
    
    print("🔐 No saved tokens, starting OAuth flow...")
    return PoEStashClient.from_oauth_flow(realm)


# ============================================================
# Example Usage
# ============================================================

if __name__ == "__main__":
    import sys
    
    # Try to load saved tokens first
    client = create_client_from_saved_tokens("pc")
    
    if not client:
        print("❌ Failed to create client")
        sys.exit(1)
    
    # Test with a league
    league = "Settlers"  # 3.30 league
    
    print(f"\n🔍 Fetching stashes for {league}...")
    try:
        stashes = client.get_stashes(league)
        print(f"Found {len(stashes)} stash tabs")
        
        currency_tabs = [s for s in stashes if s.type == "CurrencyStash"]
        print(f"Currency tabs: {len(currency_tabs)}")
        
        print(f"\n💰 Calculating net worth...")
        net_worth = client.calculate_net_worth(league)
        
        print(f"\n📊 NET WORTH SUMMARY")
        print(f"  Total Chaos Equivalent: {net_worth.total_chaos_equiv:,.0f}")
        print(f"  Total Divine Equivalent: {net_worth.total_divine_equiv:,.2f}")
        
        print(f"\n💎 Currency Holdings:")
        for curr, count in sorted(net_worth.currency_counts.items(), key=lambda x: -x[1]):
            if count > 0:
                display = CURRENCY_DISPLAY.get(curr, curr)
                chaos_val = count * DEFAULT_CURRENCY_RATES.get(curr, 0)
                print(f"  {display}: {count:,} ({chaos_val:,.0f} chaos)")
        
        print(f"\n💧 Liquid Currency (easily tradable):")
        for curr, count in net_worth.liquid_currency.items():
            display = CURRENCY_DISPLAY.get(curr, curr)
            print(f"  {display}: {count:,}")
        
        print(f"\n📈 Upgrade Budget Recommendations:")
        div = net_worth.total_divine_equiv
        print(f"  Conservative (20%): {div * 0.2:.1f} divine")
        print(f"  Moderate (30%): {div * 0.3:.1f} divine")
        print(f"  Aggressive (50%): {div * 0.5:.1f} divine")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()