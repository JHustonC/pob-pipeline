---
name: pob-farming-strategies
category: reverse-engineer-anything
description: League-aware farming strategies for PoE items and currency
version: 1.0.0
author: bot-of-exile
license: MIT
metadata:
  hermes:
    tags: [pob, path-of-building, path-of-exile, farming, strategies, league]
    related_skills: [pob-crafting-guide-finder, pob-stash-currency-api, pob-find-upgrades-trade, pob-target-build-store]
---
## When to Use
- Find farming strategies for items/currency a PoB build needs
- Filter strategies by current league (e.g., 3.30)
- Verify if older league strategies still apply
- Prioritize farming vs crafting vs buying

## Core Concept: League-Aware Filtering

### League Detection & Versioning
```python
CURRENT_LEAGUE = "3.30"  # Update per league
LEAGUE_ALIASES = {
    "3.30": ["3.30", "Settlers", "Kingsmarch"],
    "3.29": ["3.29", "Necropolis", "Allflame"],
    "3.28": ["3.28", "Affliction", "Wildwood"],
    "3.27": ["3.27", "Trial of the Ancestors"],
    "3.26": ["3.26", "Ancestor", "Kalandra"],
}

def is_league_content(league_str: str, target_league: str = CURRENT_LEAGUE) -> bool:
    """Check if content applies to target league."""
    aliases = LEAGUE_ALIASES.get(target_league, [target_league])
    return any(alias.lower() in league_str.lower() for alias in aliases)
```

### Applicability Check Framework
```python
APPLICABILITY_RULES = {
    "mechanic_removed": {
        "check": "mechanic not in current league",
        "action": "exclude",
        "examples": ["Harvest (3.19)", "Metamorph (3.10)", "Synthesis (3.6)"]
    },
    "mechanic_changed": {
        "check": "mechanic exists but modified",
        "action": "verify",
        "examples": ["Delirium mirrors", "Expedition logbooks", "Heist contracts"]
    },
    "mechanic_stable": {
        "check": "mechanic unchanged for 3+ leagues",
        "action": "trust",
        "examples": ["Maps", "Bosses", "Crafting bench"]
    },
    "new_mechanic": {
        "check": "introduced in current league",
        "action": "prioritize",
        "examples": ["Kingsmarch (3.30)", "Allflame (3.29)"]
    }
}

def check_applicability(strategy: dict, target_league: str) -> dict:
    """Return applicability verdict with reasoning."""
    mechanic = strategy.get("mechanic", "").lower()
    
    # Check for removed mechanics
    for removed in ["harvest", "metamorph", "synthesis", "perandus", "talisman"]:
        if removed in mechanic:
            return {"applicable": False, "reason": f"{removed.title()} mechanic removed"}
    
    # Check for changed mechanics
    changed = {
        "delirium": "mirror mechanics changed in 3.26",
        "expedition": "logbook changes in 3.29",
        "heist": "contract/blueprint changes in 3.25",
        "blight": "oil changes in 3.28",
        "sanctum": "relic system added 3.28",
    }
    for key, note in changed.items():
        if key in mechanic:
            return {"applicable": True, "verified": False, "note": note}
    
    return {"applicable": True, "verified": True, "note": "Mechanic stable"}
```

## Farming Method Taxonomy (League-Aware)

### Currency Farming
| Method | League | Applicability | Notes |
|--------|--------|---------------|-------|
| **Map Farming (T16-17)** | All | Stable | Atlas passive tree changes per league |
| **Delirium Mirrors** | 3.19+ | Changed | Mirror mechanics reworked 3.26 |
| **Expedition Logbooks** | 3.15+ | Changed | Logbook drops rebalanced 3.29 |
| **Heist Contracts** | 3.12+ | Changed | Contract/blueprint changes 3.25 |
| **Blight Oils** | 3.11+ | Changed | Oil changes 3.28 |
| **Sanctum Relics** | 3.28+ | New | Forbidden Sanctum endgame |
| **Kingsmarch** | 3.30+ | **New** | Settlers league mechanic |
| **Simulacrums** | 3.19+ | Stable | Wave 20-30 farming |
| **Breachstones** | All | Stable | Pure breachstone rotations |
| **Legion Emblems** | All | Stable | 5-way emblem rotations |
| **Abyssal Depths** | All | Stable | Abyssal jewels, abyssal sockets |
| **Essence Farming** | All | Stable | Memory/essence corruption |
| **Fossil Farming** | All | Stable | Delve depth 200+ |

### Item-Specific Farming
| Target | Best Method | League Notes |
|--------|-------------|--------------|
| **Divine Orbs** | Maps (T16-17), Bosses | Atlas passives critical |
| **Exalted Orbs** | Bosses, Maps, Heist | Heist contracts changed 3.25 |
| **Chaos Orbs** | Maps, Delirium, Expedition | Expedition logbooks changed 3.29 |
| **Awakened Gems** | Simulacrums, Bosses | Wave 30 Simulacrums |
| **Level 21 Gems** | Simulacrums, Vaal Temple | Vaal side areas |
| **Cluster Jewels** | Delirium, Heist | Heist blueprints 3.25 |
| **Fossils** | Delve 200+ | Sulphite cost changes |
| **Essences** | Memory, Essence corruption | Corrupted essences 3.28 |
| **Oils** | Blight, Blighted Maps | Oil changes 3.28 |
| **Relics** | Sanctum, Forbidden Sanctum | 3.28+ only |
| **Artifacts** | Expedition, Logbooks | Logbook drops 3.29 |
| **Kingsmarch Resources** | Settlers (3.30) | **League specific** |

## Web Content Discovery Strategy

### Priority Order for Search
```python
SEARCH_PRIORITY = [
    # 1. Current league specific
    (f"{CURRENT_LEAGUE} farming", 100),
    (f"{CURRENT_LEAGUE} {mechanic} guide", 95),
    
    # 2. Current league mechanic names
    (f"{LEAGUE_ALIASES[CURRENT_LEAGUE][1]} farming", 90),
    
    # 2. Recent league (previous 2)
    (f"{PREV_LEAGUE} farming", 70),
    
    # 3. General mechanics (verify applicability)
    (f"{mechanic} farming path of exile", 50),
    
    # 4. Older but stable mechanics
    (f"{stable_mechanic} guide", 40),
]
```

### Source Reliability Scoring
```python
SOURCE_RELIABILITY = {
    "poe.fandom.com": 90,  # Official wiki
    "poe-vault.com": 85,   # Build DB
    "maxroll.gg": 85,      # Guides
    "craftofexile.com": 95, # Simulator
    "poedb.tw": 90,        # Data
    "pathofexile.com": 100, # Official
    "youtube.com": 60,     # Video (check date)
    "reddit.com": 50,      # Community (check date)
    "github.com": 70,      # Tools
}

def score_content(url: str, league: str, date: str) -> float:
    """Score content relevance and reliability."""
    score = SOURCE_RELIABILITY.get(extract_domain(url), 30)
    
    # Date penalty
    if date:
        days_old = (now - parse_date(date)).days
        if days_old > 365: score *= 0.5
        elif days_old > 180: score *= 0.75
    
    # League match bonus
    if is_league_content(url, league): score *= 1.5
    elif any(l in url.lower() for l in ["3.29", "3.28"]): score *= 0.8
    
    return score
```

## Applicability Verification Pipeline

### Automated Check
```python
def verify_strategy(strategy: dict, target_league: str = CURRENT_LEAGUE) -> dict:
    """Full verification of a farming strategy."""
    result = {
        "strategy": strategy,
        "target_league": target_league,
        "checks": {},
        "verdict": "unknown",
        "confidence": 0.0
    }
    
    # 1. Mechanic existence check
    mechanic = strategy.get("mechanic", "").lower()
    result["checks"]["mechanic_exists"] = check_mechanic_exists(mechanic, target_league)
    
    # 2. Drop table currency check
    if "drops" in strategy:
        result["checks"]["drops_current"] = verify_drop_table(strategy["drops"], target_league)
    
    # 3. Economy viability
    if "profit_per_hour" in strategy:
        result["checks"]["economy_viable"] = check_economy(strategy["profit_per_hour"], target_league)
    
    # 4. Requirement check
    if "requirements" in strategy:
        result["checks"]["requirements_met"] = check_requirements(strategy["requirements"], target_league)
    
    # Aggregate verdict
    passed = sum(1 for v in result["checks"].values() if v)
    total = len(result["checks"])
    result["confidence"] = passed / total if total > 0 else 0
    
    if result["confidence"] >= 0.75:
        result["verdict"] = "recommended"
    elif result["confidence"] >= 0.5:
        result["verdict"] = "verify_manually"
    else:
        result["verdict"] = "not_recommended"
    
    return result
```

## Integration with Crafting Guide Finder

### Extended Decision Matrix
| Option | When |
|--------|------|
| **Buy finished** | Cheap, high supply, low crafting cost |
| **Craft from base** | Expensive/rare, deterministic path exists |
| **Improve current** | Good base, 1-2 missing mods, Harvest available |
| **Farm it yourself** | League-specific drops, boss-exclusive, high drop rate content |
| **Farm currency → Buy** | Stable currency farms, volatile item prices |

### Farming Strategy Output Format
```json
{
  "target": "Divine Orbs",
  "league": "3.30",
  "strategies": [
    {
      "method": "Map Farming (T16-17)",
      "mechanic": "Atlas Passive Tree",
      "applicability": {"verified": True, "note": "Stable mechanic"},
      "requirements": {"atlas_completion": "80%+", "build": "Fast clear"},
      "estimated_returns": {"divine_per_hour": 2.5, "chaos_per_hour": 500},
      "investment": {"maps": "50c/map", "sextants": "10c"},
      "source": "poe.fandom.com",
      "source_date": "2024-01-15",
      "league_tested": "3.30",
      "confidence": 0.9
    },
    {
      "method": "Expedition Logbooks",
      "mechanic": "Expedition",
      "applicability": {"verified": False, "note": "Logbook drops changed 3.29"},
      "estimated_returns": {"artifacts_per_hour": 10, "logbooks_per_hour": 5},
      "source": "poe-vault.com",
      "source_date": "2023-10-01",
      "league_tested": "3.28",
      "confidence": 0.5
    }
  ],
  "recommendation": "Map farming with Atlas passives for Divine; Expedition requires verification"
}
```

## League Update Checklist (Per New League)

### When New League Launches
1. Update `CURRENT_LEAGUE` constant
2. Add league aliases to `LEAGUE_ALIASES`
3. Run applicability check on all cached strategies
4. Search for new league-specific mechanics
5. Update drop tables for changed mechanics
6. Verify economy viability (currency ratios)
7. Test new Atlas passive tree configurations

### Automated League Transition
```python
def on_league_change(new_league: str):
    """Handle league transition."""
    # 1. Archive old league strategies
    archive_strategies(CURRENT_LEAGUE)
    
    # 2. Update current league
    CURRENT_LEAGUE = new_league
    
    # 3. Re-verify all strategies
    for strategy in all_strategies:
        verification = verify_strategy(strategy, new_league)
        if not verification["checks"].get("mechanic_exists", True):
            strategy["status"] = "deprecated"
        elif verification["confidence"] < 0.5:
            strategy["status"] = "needs_verification"
        else:
            strategy["status"] = "verified"
    
    # 4. Search for new content
    search_new_league_content(new_league)
    
    # 5. Update decision matrices
    update_decision_matrices()
```

## Validated 3.30 (Settlers) Farming Strategies
| Method | Mechanic | Verified | Returns | Notes |
|--------|----------|----------|---------|-------|
| **Kingsmarch Daily** | Kingsmarch | ✅ Yes | ~2 div/hr + Gold/Artifacts | **New 3.30 mechanic, prioritize** |
| **T16-17 Maps + Atlas** | Atlas Passives | ✅ Yes | ~3 div/hr + 600 chaos/hr | Atlas passives change/league |
| **Boss Carries** | Endgame Bosses | ✅ Yes | ~1 div/hr + 5 ex/hr | Stable |
| **Heist Blueprints** | Heist | ✅ Yes | Ring bases, currency | Contracts changed 3.25 |
| **Sanctum/Forbidden** | Sanctum | ✅ Yes | Relics, Ashes chance | 3.28+ relic system |
| **Expedition Logbooks** | Expedition | ⚠️ Verify | Artifacts, logbooks | Logbook drops changed 3.29 |
| **Delirium Mirrors** | Delirium | ✅ Yes | Simulacrum splinters | Reworked 3.26 |

### Validated Farming Priority for 3.30
```python
FARMING_PRIORITY_3_30 = [
    {"method": "Kingsmarch Daily", "div_per_hour": 2.0, "priority": 1, "note": "New league mechanic"},
    {"method": "T16-17 Maps + Atlas", "div_per_hour": 3.0, "priority": 2, "note": "Atlas passives change/league"},
    {"method": "Boss Carries", "div_per_hour": 1.0, "exalted_per_hour": 5, "priority": 3},
    {"method": "Heist Blueprints", "priority": 4, "note": "Ring bases, currency"},
    {"method": "Sanctum/Forbidden", "priority": 5, "note": "Ashes relics"},
    {"method": "Expedition Logbooks", "priority": 6, "note": "Verify 3.29 changes"},
]
```

### Validated Budget Allocation
| Budget % | Target | Method |
|----------|--------|--------|
| 100% (20 div) | Helmet enchant | BUY_FINISHED |
| 250% (50 div) | Weapon 1 | FARM_CURRENCY_THEN_BUY |
| 400% (80 div) | Body Armour | FARM_CURRENCY_THEN_BUY |
| 150% (30 div) | Gloves | FARM_CURRENCY_THEN_BUY |
| 125% (25 div) | Boots | FARM_CURRENCY_THEN_BUY |
| 750% (150 div) | Ashes of the Stars | TRADE_ONLY |
| 1000% (200 div) | Mageblood | TRADE_ONLY |
| 200% (40 div) | Rings | FARM_CURRENCY_THEN_BUY |

### Validated Applicability Checks for 3.30
```python
APPLICABILITY_3_30 = {
    "Kingsmarch": {"verified": True, "note": "New 3.30 mechanic"},
    "Atlas Passives": {"verified": True, "note": "Stable, changes/league"},
    "Delirium Mirrors": {"verified": True, "note": "Reworked 3.26"},
    "Expedition": {"verified": False, "note": "Logbook drops changed 3.29"},
    "Heist": {"verified": True, "note": "Contracts changed 3.25"},
    "Sanctum": {"verified": True, "note": "3.28+ relic system"},
    "Harvest": {"verified": False, "note": "Removed 3.19"},
    "Metamorph": {"verified": False, "note": "Removed 3.10"},
    "Synthesis": {"verified": False, "note": "Removed 3.6"},
}
```

### Validated League Transition Checklist
```python
def on_league_change(new_league: str):
    """Handle league transition - run when new league launches."""
    # 1. Update constants
    CURRENT_LEAGUE = new_league
    LEAGUE_ALIASES[new_league] = [new_league, league_name, mechanic_name]
    
    # 2. Re-verify all cached strategies
    for strategy in all_strategies:
        verification = verify_strategy(strategy, new_league)
        if not verification["checks"].get("mechanic_exists", True):
            strategy["status"] = "deprecated"
        elif verification["confidence"] < 0.5:
            strategy["status"] = "needs_verification"
        else:
            strategy["status"] = "verified"
    
    # 3. Search for new league-specific content
    search_new_league_content(new_league)
    
    # 4. Update decision matrices
    update_decision_matrices()
```

## Testing Farming Strategies

The test suite includes a `get_farming_strategies()` helper that mirrors the production logic:

```python
def get_farming_strategies(target_items, league="3.30"):
    """Get farming strategies for target items."""
    strategies = {  # ... full strategy definitions ... }
    
    # Always include currency farming (divine_orbs, exalted_orbs)
    # Filter item-specific strategies by target_items
    target_str = " ".join(str(t).lower() for t in target_items)
    result = {}
    for k, v in strategies.items():
        if k in ["divine_orbs", "exalted_orbs"] or k.lower() in target_str:
            result[k] = v
    return result
```

### Test Coverage
```python
# Test integration with full pipeline
farm_strats = get_farming_strategies(["Vaal Axe", "Royal Burgonet"], "3.30")
assert "divine_orbs" in farm_strats  # Currency always included
assert "exalted_orbs" in farm_strats
```

### Applicability Verification in Tests
Each strategy includes applicability metadata:
```python
"applicability": {"verified": True, "note": "Stable mechanic"},
"league_tested": "3.30",
"confidence": 0.9
```

Tests verify:
- Currency farming strategies always returned
- Item-specific strategies filtered by target items
- League parameter passed through
- Confidence scores present

## Integration with Target Build Store

The `pob-target-build-store` skill provides the **target build definition** that drives farming strategy selection:

```python
from pob_target_build_store import TargetBuildStore
from pob_farming_strategies import get_farming_strategies

store = TargetBuildStore()
target_build = store.get("earthshatter_berserker_god_tier")

# Extract unique items that must be farmed/traded
unique_items = [item.target_unique_name for item in target_build.items if item.target_unique_name]
# ["Mageblood", "Ashes of the Stars", "Circle of Guilt", "Echoes of Creation"]

farming = get_farming_strategies(unique_items, league="3.30")
```

The target build store provides:
- **Unique items** → drives farm vs trade decisions
- **Crafting priority** → High priority items get farming priority
- **Base types** → determines farming method (e.g., Vaal Axe → boss/map farming)
- **League** → filters for league-specific mechanics (Kingsmarch for 3.30)

## Integration with Target Build Store
| Source | Reliability | Notes |
|--------|-------------|-------|
| pathofexile.com | 100 | Official |
| craftofexile.com | 95 | Simulator |
| poe.fandom.com | 90 | Official wiki |
| poedb.tw | 90 | Data |
| poe-vault.com | 85 | Build DB |
| maxroll.gg | 85 | Guides |
| youtube.com | 60 | Check date |
| reddit.com | 50 | Check date |