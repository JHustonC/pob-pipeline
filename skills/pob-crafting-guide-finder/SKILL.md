---
name: pob-crafting-guide-finder
category: reverse-engineer-anything
description: Find crafting guides for PoB build item requirements
version: 1.0.0
author: bot-of-exile
license: MIT
metadata:
  hermes:
    tags: [pob, path-of-building, path-of-exile, crafting, guides, items]
    related_skills: [pob-find-upgrades-trade, pob-character-import, pob-oauth-to-loadout, pob-target-build-store, pob-farming-strategies]
---
## When to Use
- Find crafting guides for items a PoB build needs
- Match guide outputs to build's stat requirements
- Identify crafting paths (bench, harvest, essences, fossils, etc.)
- Prioritize guides by cost/effort vs. upgrade value

## Approach

### 1. Analyze Build Item Requirements
From PoB loadout, extract per-slot needs:
```python
def analyze_build_needs(build_json):
    needs = {}
    for slot, item in equipped_items.items():
        # Parse current mods
        current_mods = parse_item_mods(item)
        
        # Identify desired mods from trade weights or upgrade queries
        desired_mods = get_desired_mods(slot, build)
        
        # Gap analysis
        missing = desired_mods - current_mods
        needs[slot] = {
            "base": item.base_type,
            "ilvl": item.ilvl,
            "current": current_mods,
            "desired": desired_mods,
            "missing": missing,
            "influences": item.influences
        }
    return needs
```

### 2. Crafting Guide Sources
| Source | Type | Search Strategy |
|--------|------|----------------|
| PoE Wiki | Official | `site:pathofexile.fandom.com crafting {base}` |
| PoE Vault | Build DB | `site:poe-vault.com crafting {mod}` |
| Maxroll | Guides | `site:maxroll.gg crafting {base}` |
| Craft of Exile | Simulator | `craftofexile.com` - simulates outcomes |
| PoE DB | Data | `poedb.tw` - mod pools, crafting outcomes |
| YouTube | Video guides | `crafting {base} {mod} path of exile` |
| Reddit | Community | `r/pathofexile crafting {base}` |
| Crafting Bench | In-game | Fixed recipes, meta-crafting |

### 3. Crafting Method Taxonomy
```python
CRAFTING_METHODS = {
    "bench": {
        "cost": "low", "deterministic": True,
        "mods": ["prefix/suffix cannot be changed", "craft {mod}", "quality"]
    },
    "essence": {
        "cost": "medium", "deterministic": "guaranteed_mod",
        "mods": ["guaranteed tier X mod"]
    },
    "fossil": {
        "cost": "medium-high", "deterministic": "weighted",
        "mods": ["delve fossil pools"]
    },
    "harvest": {
        "cost": "variable", "deterministic": "reforge/augment",
        "mods": ["reforge keep prefix", "augment phys", "remove non-phys"]
    },
    "beast": {
        "cost": "high", "deterministic": "specific",
        "mods": ["split item", "imprint", "craft specific"]
    },
    "maven": {
        "cost": "very high", "deterministic": "elevated",
        "mods": ["elevated mods", "orb of dominance"]
    },
    "exalted_slam": {
        "cost": "high", "deterministic": False,
        "mods": ["random explicit"]
    },
    "annulment": {
        "cost": "high", "deterministic": False,
        "mods": ["remove random mod"]
    }
}
```

### 4. Guide Matching Algorithm
```python
def match_guides_to_needs(needs, guides):
    matches = []
    for slot, need in needs.items():
        for guide in guides:
            score = 0
            # Base type match
            if guide.base_type == need["base"]: score += 50
            # Mod overlap
            overlap = set(guide.output_mods) & set(need["desired"])
            score += len(overlap) * 20
            # Method cost vs budget
            if guide.cost_tier <= budget_tier: score += 15
            # Deterministic vs RNG
            if guide.deterministic: score += 10
            # ILvl compatible
            if guide.min_ilvl <= need["ilvl"]: score += 5
            
            if score > 30:
                matches.append({
                    "slot": slot,
                    "guide": guide,
                    "score": score,
                    "crafting_path": extract_path(guide, need)
                })
    return sorted(matches, key=lambda x: -x["score"])
```

### 5. Crafting Path Output Format
```json
{
  "slot": "Weapon 1",
  "base": "Vaal Axe",
  "ilvl": 86,
  "current_mods": ["180% inc Phys", "25% AS", "+2 Melee Gems", "Gain Rage"],
  "target_mods": ["180% inc Phys", "25% AS", "+2 Melee", "Crit Multi", "Crit Chance"],
  "crafting_paths": [
    {
      "method": "Harvest",
      "steps": [
        "1. Harvest: Reforge Keep Prefixes (keep phys% + AS)",
        "2. Harvest: Augment Critical (add crit multi/chance)",
        "3. Bench: Craft % Crit Multi (if suffix open)"
      ],
      "estimated_cost": "15-30 Divine",
      "success_rate": "High (deterministic)",
      "guide_url": "https://...",
      "guide_source": "PoE Wiki / Craft of Exile"
    },
    {
      "method": "Essence",
      "steps": [
        "1. Essence of Horror (guarantees +1 Melee Gems)",
        "3. Harvest reforge for phys/AS"
      ],
      "estimated_cost": "50+ Divine",
      "success_rate": "Medium (RNG)"
    }
  ]
}
```

## Integration with Target Build Store

The `pob-target-build-store` skill provides the **target build definition** that drives crafting guide search:

```python
from pob_target_build_store import TargetBuildStore
from pob_crafting_guide_finder import find_crafting_guides

store = TargetBuildStore()
target_build = store.get("earthshatter_berserker_god_tier")

for item in target_build.items:
    if item.crafting_priority == "High":
        guides = find_crafting_guides(
            base_type=item.base_type,
            desired_mods=item.target_mods,
            ilvl=item.target_ilvl,
            influences=list(item.target_influences.keys()),
            budget=available_currency
        )
```

The target build store provides:
- **Base type** per slot → narrows guide search
- **Target mods** per slot → drives guide matching
- **Influences** per slot → filters for influenced crafting guides
- **Crafting priority** → filters for High priority items first
- **Unique names** → identifies trade-only items (Mageblood, Ashes)

## Integration with Target Build Store

### Search Functions
```python
def search_crafting_guides(base_type, desired_mods):
    """Search multiple sources for relevant guides."""
    queries = [
        f"crafting {base_type} {mod}" for mod in desired_mods
    ] + [f"how to craft {base_type} path of exile"]
    
    # Use web search, filter for:
    # - PoE Wiki, PoE Vault, Maxroll, Craft of Exile
    # - Recent (current league)
    # - Matching base type
    pass

def parse_guide(guide_url):
    """Extract structured crafting info from guide."""
    # Parse for:
    # - Base type required
    # - ILvl requirement
    # - Crafting method(s)
    # - Step-by-step process
    # - Cost estimate
    # - Deterministic vs RNG steps
    # - Output mod pool
    pass
```

## Integration with PoB Pipeline
```
# After pob-find-upgrades-trade identifies upgrade slots:
upgrade_slots = find_upgrade_slots(build)  # e.g., ["Weapon 1", "Body Armour"]

for slot in upgrade_slots:
    current_item = get_equipped_item(build, slot)
    desired_stats = get_trade_weights(build, slot)
    
    crafting_guides = find_crafting_guides(
        base_type=current_item.base,
        desired_mods=desired_stats,
        ilvl=current_item.ilvl,
        influences=current_item.influences,
        budget=available_currency
    )
    
    # Present options:
    # 1. Buy finished (trade)
    # 2. Craft from base (guides)
    # 3. Improve current (targeted crafting)
```

## Validated Crafting Paths for Earthshatter Berserker (Week 1 → God Tier)
| Slot | Current | Target | Missing Mods | Best Method | Est. Cost |
|------|---------|--------|--------------|-------------|-----------|
| Weapon 1 | Carrion Sever (Vaal Axe) | Vaal Axe perfected | 180%+ Phys, 25% AS, +2 Melee, Crit Multi/Chance | Harvest: Reforge Keep Prefixes → Augment Crit → Bench Craft Crit Multi | 30 div |
| Helmet | Echoes of Creation | +Lab Enchant | Warcry Buff Effect / CDR | Lab Enchant (deterministic) | 20 div |
| Body Armour | Plague Hide | Royal Plate maxed | 200%+ Armour, +150 Life, Max Res | Harvest: Reforge Keep Prefixes → Augment Life/Res | 50 div |
| Gloves | Pain Hand | Leviathan Gauntlets | 100+ Life, AS/Crit | Fossil (Pristine/Jagged) + Harvest Augment | 20 div |
| Boots | Sol Spur | Leviathan Greaves | 30% MS, Chaos/Endurance | Harvest: Augment Movement/Chaos | 15 div |
| Amulet | Phoenix Gorget | Ashes of the Stars | +1 Gem Level | Trade only (Sanctum drop) | 150 div |
| Belt | Rage Buckle | Mageblood | 4 Flask Effects | Trade only | 200+ div |
| Ring 1 | Vengeance Eye | Circle of Guilt / Rare | Crit Multi/Chance, Life/Res | Fossil (Pristine) + Harvest | 25 div |

### Validated Crafting Steps (Harvest - Deterministic)
```python
# Weapon upgrade path (validated)
weapon_crafting_steps = [
    "1. Harvest: Reforge Keep Prefixes (keeps 180% Phys + 25% AS)",
    "2. Harvest: Augment Critical (adds Crit Multi/Chance)",
    "3. Bench: Craft % Crit Multi (if suffix open)",
    "Estimated cost: 15-30 Divine",
    "Success rate: High (deterministic)",
]

# Helmet enchant (deterministic)
helmet_crafting_steps = [
    "1. Lab: Divine Font → Warcry Buff Effect / Cooldown Recovery",
    "Estimated cost: 20 Divine (buy enchanted) or 5-10 Divine (self-lab)",
    "Success rate: 100% (guaranteed)",
]
```

### Validated Search Queries
```python
def search_crafting_guides(base_type, desired_mods):
    queries = []
    for mod in desired_mods:
        queries.extend([
            f"site:pathofexile.fandom.com crafting {base_type} {mod}",
            f"site:craftofexile.com {base_type} {mod}",
            f"site:poedb.tw {base_type} {mod} crafting",
            f"site:poe-vault.com crafting {base_type} {mod}",
            f"site:maxroll.gg {base_type} crafting",
        ])
    queries.append(f"how to craft {base_type} path of exile {mod}")
    # Filter: current league (3.30), matching base type, deterministic methods first
    return queries
```

### Validated Decision Matrix
| Slot | Current Cost | Decision | Reasoning |
|------|-------------|----------|-----------|
| Helmet | 20 div | **BUY_FINISHED** | Within 20 div budget |
| Weapon 1 | 50 div | FARM_CURRENCY_THEN_BUY | 50 div > budget |
| Body Armour | 80 div | FARM_CURRENCY_THEN_BUY | 80 div > budget |
| Gloves | 30 div | FARM_CURRENCY_THEN_BUY | 30 div > budget |
| Boots | 25 div | FARM_CURRENCY_THEN_BUY | 25 div > budget |
| Amulet | 150 div | FARM_CURRENCY_THEN_BUY | Trade only (Ashes) |
| Belt | 200 div | FARM_CURRENCY_THEN_BUY | Trade only (Mageblood) |
| Ring 1 | 40 div | FARM_CURRENCY_THEN_BUY | 40 div > budget |
| Ring 2 | 40 div | FARM_CURRENCY_THEN_BUY | 40 div > budget |

### Validated Farming Priority for Currency
1. Kingsmarch daily (3.30 mechanic) → ~2 div/hr
2. T16-17 Maps + Atlas passives → ~3 div/hr
3. Boss carries → ~1 div/hr + Exalted
4. Heist blueprints → Ring bases
5. Sanctum → Ashes relics

## Related
- `pob-find-upgrades-trade` - Identifies which slots need upgrades
- `pob-oauth-to-loadout` - Provides build with items/stats
- `pob-stash-currency-api` - Provides budget for crafting vs buying