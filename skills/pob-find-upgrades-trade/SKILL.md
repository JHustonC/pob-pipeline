---
name: pob-find-upgrades-trade
category: reverse-engineer-anything
description: PoB Find Upgrades with trade integration and budget limits
version: 1.0.0
author: bot-of-exile
license: MIT
metadata:
  hermes:
    tags: [pob, path-of-building, path-of-exile, trade, upgrades]
    related_skills: [pob-character-import, pob-oauth-to-loadout, pob-stash-currency-api]
---
## When to Use
- Generate trade site search links for item upgrades using PoB's weighted query system
- Auto-configure search with character's level, stats, and requirements
- Limit searches by available currency budget from stash API
- Integrate PoB's TradeQueryGenerator for stat weights and query building

## PoB Trade System Overview

### Core Components
1. **TradeQueryGenerator** - Builds weighted queries from stat weights
2. **TradeQueryRequests** - Handles API requests to trade site
3. **TradeQuery** - Main coordination class
4. **TradeHelpers** - Stat matching, mod parsing

### How "Find Upgrades" Works
1. **Stat Weights**: PoB calculates each mod's value by measuring DPS/EHP change
2. **Query Generation**: Converts weights → trade site filters with min/max
3. **Weighted Search**: Trade site returns results sorted by weighted sum
4. **Result Evaluation**: Each listing re-evaluated in PoB for exact upgrade %

## Python Trade Query Builder (Validated Working)
```python
from pob_trade_query_generator import TradeQueryBuilder, CurrencyType, ItemCategory

# Create builder for Earthshatter Berserker
builder = TradeQueryBuilder(
    league="Settlers",
    max_price=50,
    currency=CurrencyType.DIVINE,
    character_level=96,
    character_attributes={"strength": 212, "dexterity": 100, "intelligence": 50}
)
builder.set_category(ItemCategory.ONE_HAND_AXE)

# Add build-specific stat weights
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
    "ImpaleChance": 0.5,
    "ImpaleEffect": 0.4,
}
for stat_id, weight in build_weights.items():
    builder.add_stat_weight(stat_id, weight)

# Set current item stats for min calculation
current_weapon_stats = {
    "FullDPS": 500000,
    "AttackSpeed": 1.56,
    "CriticalStrikeChance": 5.0,
    "CriticalStrikeMultiplier": 150,
    "EffectiveHitPool": 50000,
    "MaxLife": 4000,
    "AllResist": 77,
}
for stat_id, value in current_weapon_stats.items():
    builder.set_current_stat(stat_id, value)

# Build query
query = builder.build_query(current_weapon_stats)
trade_url = builder.to_trade_url(query)
print(f"Trade URL: {trade_url}")
```

### Validated Stat Weights for Earthshatter Berserker
```python
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
    "ImpaleChance": 0.5,
    "ImpaleEffect": 0.4,
}
```

### Testing Trade Query Generator

The test suite (`test_pob_pipeline.py`) covers:
- TradeQueryBuilder initialization
- Adding stat weights
- Setting current stats
- Building queries
- Creating Earthshatter Berserker specific query
- Converting to trade URL

### Test Patterns
```python
# Initialize builder
builder = TradeQueryBuilder(
    league="Settlers",
    max_price=50,
    currency=CurrencyType.DIVINE
)

# Add weights
builder.add_stat_weight("FullDPS", 1.0)
builder.add_stat_weight("AttackSpeed", 0.6)

# Set current stats
builder.set_current_stat("FullDPS", 500000)

# Build and verify
query = builder.build_query()
assert "query" in query
assert "filters" in query["query"]

# URL generation
trade_url = builder.to_trade_url(query)
assert "pathofexile.com/trade" in trade_url
```

### Earthshatter Query Factory Test
```python
query = create_earthshatter_berserker_query(
    league="Settlers",
    max_price=50,
    currency=CurrencyType.DIVINE
)
assert query is not None
```

## Validated Working Commands
```bash
# Headless PoB upgrade finder
luajit HeadlessWrapper.lua find_upgrades.lua \
  --build=my_build.json --slot="Weapon 1" \
  --budget=50 --currency=divine --league=Settlers

# Python trade query generator
python3 -c "from pob_trade_query_generator import TradeQueryBuilder, CurrencyType; b=TradeQueryBuilder(league='Settlers', max_price=50, currency=CurrencyType.DIVINE); print(b.to_trade_url(b.build_query()))"
```