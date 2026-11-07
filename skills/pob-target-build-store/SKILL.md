---
name: pob-target-build-store
category: reverse-engineer-anything
description: Store and manage target builds for PoB pipeline.
version: 1.0.0
author: bot-of-exile
license: MIT
metadata:
  hermes:
    tags: [pob, path-of-building, path-of-exile, target-build, build-planning, localStorage]
    related_skills: [pob-crafting-guide-finder, pob-farming-strategies, pob-find-upgrades-trade, pob-oauth-to-loadout]
---
## When to Use
- Store and manage multiple target/end-game builds for PoB comparison
- Switch between build variants (God Tier, Budget, HC, mapping, bossing)
- Persist target builds across dashboard sessions via localStorage
- Use target builds as the "goal" for gap analysis in pob-find-upgrades-trade
- Track crafting priorities and farming targets per build variant

## Core Concept
A **Target Build** represents the end-state you want to reach. It defines:
- Every slot's target base type, ilvl, rarity, mods, influences, unique name
- Crafting priority per item (High/Medium/Low)
- Build metadata: class, ascendancy, level, league, main skill, tags
- Config overrides: pantheon, bandit, custom modifiers

The pipeline compares **current gear** (from pob-oauth-to-loadout) against the **target build** to produce gap analysis, crafting recommendations, and farming priorities.

## CLI Usage
```bash
# List all target builds
python3 pob_target_build_store.py list

# Get full build details
python3 pob_target_build_store.py get earthshatter_berserker_god_tier

# Create from template (god_tier, budget)
python3 pob_target_build_store.py template god_tier my_berserker
python3 pob_target_build_store.py template budget my_budget_berserker

# Create empty build
python3 pob_target_build_store.py create my_build "My Build" Ranger Deadeye

# Add items to a build
python3 pob_target_build_store.py item-add my_build "Weapon 1" "Harbinger Bow" Rare "200% Phys" "25% AS" "+2 Bow Gems"

# Update build fields
python3 pob_target_build_store.py update my_build description "Updated for 3.30"
python3 pob_target_build_store.py update my_build tags "budget,mapping,3.30"

# Duplicate and modify (e.g., God Tier -> HC variant)
python3 pob_target_build_store.py duplicate earthshatter_berserker_god_tier my_variant "My Variant"
python3 pob_target_build_store.py update my_variant tags "hc,minmax,earthshatter,berserker,3.30"

# Export/Import for sharing/backup
python3 pob_target_build_store.py export earthshatter_berserker_god_tier /tmp/build.json
python3 pob_target_build_store.py import /tmp/build.json

# Delete
python3 pob_target_build_store.py delete old_build
```

## Python API: Export/Import
```python
from pob_target_build_store import TargetBuildStore

store = TargetBuildStore()

# Export single build to JSON file
store.export("earthshatter_berserker_god_tier", Path("/tmp/export.json"))

# Import build(s) from JSON file
store.import_build(Path("/tmp/export.json"))
```

## Testing Target Build Store
The test suite (`test_pob_pipeline.py`) covers:
- CRUD operations: create, get, update, delete
- Duplication with new ID/name
- Import/export roundtrip
- Item management: add, remove, get
- Listing and tag filtering

Key test patterns:
```python
# Test import/export
build = TargetBuild(id="test", name="Test", description="...", ...)
store.create(build)
store.export("test", export_path)
new_store = TargetBuildStore(new_path)
new_store.import_build(export_path)
imported = new_store.get("test")
assert imported.name == "Test"
```

## Storage
- File: `~/.pob_pipeline/target_builds.json`
- Format: JSON with build objects keyed by ID
- Auto-creates directory on first use
- Versioned: each update increments `version` and updates `updated_at`

## Data Model
```python
@dataclass
class TargetItem:
    slot: str
    base_type: str
    target_ilvl: int = 86
    target_rarity: str = "Rare"
    target_mods: List[str]
    target_influences: Dict[str, bool]
    target_unique_name: Optional[str]
    crafting_priority: str = "Medium"
    notes: str = ""

@dataclass
class TargetBuild:
    id: str
    name: str
    description: str
    character_class: str
    ascendancy: str
    target_level: int = 100
    target_league: str = "Settlers"
    main_skill: str = ""
    version: int = 1
    created_at: str
    updated_at: str
    items: List[TargetItem]
    passive_tree_goals: List[str]
    config_overrides: Dict[str, Any]
    tags: List[str]
```

## Templates
Two built-in templates for Earthshatter Berserker:
- `god_tier`: 9 items, chase uniques (Mageblood, Ashes, Circle of Guilt, Echoes), ~500 div
- `budget`: Same slots, craftable rares, ~50 div

## Dashboard Integration
The dashboard (`pob_pipeline_dashboard.html`) provides a UI for:
- **Toolbar dropdown**: Select active target build for pipeline comparison
- **"Manage Targets" button**: Opens modal with card grid of all builds
- **Create/Edit modal**: Full form with dynamic item rows
- **localStorage persistence**: Builds survive page reloads
- **Auto-select**: Selected target feeds into pipeline gap analysis

### Modal Features
- Dynamic item rows: Add/remove slots on demand
- Slot selector: All 15 equipment slots + flasks
- Multi-select influences: shaper, elder, crusader, redeemer, hunter, warlord
- Mods textarea: One mod per line
- Crafting priority dropdown: High/Medium/Low
- Form validation: Required fields (ID, name, slot, base)
- Duplicate protection: ID must be unique

### Pipeline Integration
When a target build is selected in the dashboard:
1. `renderTargetBuildList()` loads from localStorage
2. Selected build's items become the **target** for gap analysis
3. `pob-find-upgrades-trade` uses target mods for trade weights
4. `pob-crafting-guide-finder` uses missing mods for crafting paths
5. `pob-farming-strategies` uses unique items for farm targets

## Python API Usage
```python
from pob_target_build_store import TargetBuildStore, TargetBuild, TargetItem

store = TargetBuildStore()
build = store.get("earthshatter_berserker_god_tier")

from pob_find_upgrades_trade import find_upgrade_slots
from pob_crafting_guide_finder import find_crafting_guides
from pob_farming_strategies import get_farming_strategies

upgrade_slots = find_upgrade_slots(current_build, build)
for slot in upgrade_slots:
    crafting_guides = find_crafting_guides(build.items[slot])
    farming = get_farming_strategies([item.target_unique_name for item in build.items])
```

## Pre-built Earthshatter Berserker Templates
| Template | ID | Items | Uniques | Est. Cost |
|----------|-----|-------|---------|-----------|
| God Tier | `earthshatter_berserker_god_tier` | 9 | Mageblood, Ashes, Circle of Guilt, Echoes | ~500 div |
| Budget | `earthshatter_berserker_budget` | 9 | Echoes only | ~50 div |
| HC Variant | `earthshatter_berserker_hc` | 9 | Mageblood, Ashes, Circle of Guilt | ~500 div |

## Tags for Filtering
- `minmax`: Fully optimized, no compromises
- `budget`: Cost-conscious, craftable rares
- `hc`: Hardcore viable (more life/defense)
- `uber-bossing`: Optimized for Uber Sirus/Uber Maven
- `mapping`: Fast clear, QoL focused
- `3.30` / `3.29` / `3.28`: League version

## Integration with Pipeline Skills
| Skill | Role |
|-------|------|
| `pob-oauth-to-loadout` | Provides **current** gear from character import |
| `pob-find-upgrades-trade` | Uses target mods for **trade weights** |
| `pob-crafting-guide-finder` | Uses **missing mods** for crafting paths |
| `pob-farming-strategies` | Uses **unique items** for farm targets |
| `pob-stash-currency-api` | Provides **budget** for decision matrix |
| `pob-target-build-store` | **This skill** - stores the **target** definition |

## File Locations
- CLI: `/Users/joecrawford/.hermes/profiles/bot-of-exile/scripts/pob_target_build_store.py`
- Dashboard UI: `/Users/joecrawford/.hermes/profiles/bot-of-exile/scripts/pob_pipeline_dashboard.html`
- Storage: `~/.pob_pipeline/target_builds.json`

## Dashboard Modal JavaScript Functions
```javascript
openTargetBuildModal(mode, build)
addTargetItemRow(item)
saveTargetBuild(event)
renderTargetBuildList()
selectTargetBuild(id)
```