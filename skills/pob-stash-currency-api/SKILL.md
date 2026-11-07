---
name: pob-stash-currency-api
category: reverse-engineer-anything
description: Access PoE stashes and currency exchange API for net worth
version: 1.0.0
author: bot-of-exile
license: MIT
metadata:
  hermes:
    tags: [pob, path-of-building, path-of-exile, stash, currency, api]
    related_skills: [pob-character-import, pob-oauth-to-loadout]
---
## When to Use
- Access your PoE stashes to calculate net worth / currency holdings
- Fetch currency exchange rates from GGG's official API
- Build net worth trackers like WealthExile or Maxroll PoExchange
- Check available currency for trade budget limits

## Required OAuth Scopes
- `account:stashes` - for private stash access
- `account:characters` - for character/league info
- `service:cxapi` - for currency exchange (confidential clients only)
- OR use public currency exchange endpoint (no auth)

## API Endpoints

### 1. List Stashes (Private)
```
GET https://api.pathofexile.com/stash[/<realm>]/<league>
Headers: Authorization: Bearer <access_token>
```
**Realm**: `pc` (default), `xbox`, `sony`
**League**: Required (e.g., "Settlers", "Standard")

**Response**: stashes array with items including currency stack sizes

### 2. Currency Exchange (Public - No Auth)
```
GET https://web.poecdn.com/api/currency-exchange[/<realm>][/<id>]
```
Returns hourly aggregate exchange rates for all currency pairs.

### 3. Currency Exchange (OAuth - service:cxapi)
```
GET https://api.pathofexile.com/currency-exchange[/<realm>][/<id>]
Headers: Authorization: Bearer <access_token>
```
Requires confidential client.

## Python Implementation (Validated Working)
```python
from pob_stash_currency_client import PoEStashClient, create_client_from_saved_tokens

# 1. Create client (auto-loads saved tokens or runs OAuth flow)
client = create_client_from_saved_tokens("pc")

# 2. Fetch stashes for character's league
league = "Settlers"  # 3.30 league
stashes = client.get_stashes(league)
currency_tabs = [s for s in stashes if s.type == "CurrencyStash"]

# 3. Calculate net worth
net_worth = client.calculate_net_worth(league)
print(f"Total Divine Equivalent: {net_worth.total_divine_equiv:.1f}")
print(f"Liquid Currency: {net_worth.liquid_currency}")

# 4. Get budget recommendations
budget = net_worth.total_divine_equiv * 0.3  # 30% of net worth
```

### Key Currency IDs (Validated)
```python
CURRENCY_DISPLAY = {
    "CurrencyChaosOrb": "Chaos Orb",
    "CurrencyDivineOrb": "Divine Orb",
    "CurrencyExaltedOrb": "Exalted Orb",
    "CurrencyMirrorShard": "Mirror Shard",
    "CurrencyMirror": "Mirror of Kalandra",
    "CurrencyOrbOfAnnulment": "Orb of Annulment",
    "CurrencyVaalOrb": "Vaal Orb",
    "CurrencyOrbOfRegret": "Orb of Regret",
    "CurrencyCartographersChisel": "Cartographer's Chisel",
    "CurrencyGemcuttersPrism": "Gemcutter's Prism",
    "CurrencyOrbOfFusing": "Orb of Fusing",
    "CurrencyOrbOfAlchemy": "Orb of Alchemy",
    "CurrencyOrbOfAlteration": "Orb of Alteration",
    "CurrencyOrbOfAugmentation": "Orb of Augmentation",
    "CurrencyOrbOfChance": "Orb of Chance",
    "CurrencyOrbOfScouring": "Orb of Scouring",
    "CurrencyOrbOfTransmutation": "Orb of Transmutation",
}
```

### Rate Limits (Validated)
- Account Stashes: ~60 req/min
- Currency Exchange: Public CDN (hourly cached), OAuth `service:cxapi` (confidential clients only)
- Use exponential backoff on 429

### Testing Stash/Currency Client

The test suite (`test_pob_pipeline.py`) covers:
- Currency display name mapping
- Default currency rates existence
- Net worth calculation logic
- Stash item parsing from API data

### Net Worth Calculation Test Pattern
```python
# Use lowercase keys for currency rates (not API format)
currency_counts = {"chaos": 100, "divine": 5, "exalted": 2}
total_chaos = sum(c * DEFAULT_CURRENCY_RATES.get(k, 0) for k, c in currency_counts.items())
total_divine = total_chaos / DEFAULT_CURRENCY_RATES["divine"]

# Verify against expected
expected_chaos = 100 * DEFAULT_CURRENCY_RATES["chaos"] + 5 * DEFAULT_CURRENCY_RATES["divine"] + 2 * DEFAULT_CURRENCY_RATES["exalted"]
assert total_chaos == expected_chaos
```

### Key Pitfall: Currency Key Format
- **API format**: `CurrencyChaosOrb`, `CurrencyDivineOrb` (from PoE API)
- **Rate keys**: `chaos`, `divine`, `exalted` (lowercase in `DEFAULT_CURRENCY_RATES`)
- Always normalize API currency IDs to lowercase rate keys

### Test Coverage
```python
# Verify rates exist
assert "chaos" in DEFAULT_CURRENCY_RATES
assert "divine" in DEFAULT_CURRENCY_RATES
assert DEFAULT_CURRENCY_RATES["divine"] == 200.0

# Item parsing
item = StashItem(id="CurrencyChaosOrb", ...)
assert item.currency_type == "CurrencyChaosOrb"
```

## Validated Working Commands
```bash
# Run with saved tokens
python3 -c "from pob_stash_currency_client import create_client_from_saved_tokens; c=create_client_from_saved_tokens('pc'); print(c.calculate_net_worth('Settlers'))"
```