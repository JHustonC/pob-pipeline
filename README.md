# PoB Pipeline — Path of Building Automation

A complete automation pipeline for Path of Building with OAuth character import, passive tree validation, trade queries, stash/currency analysis, farming strategies, crafting guides, and a leveling assistant.

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Features](#features)
- [File Structure](#file-structure)
- [Skills](#skills)
- [Requirements](#requirements)
- [Configuration](#configuration)
- [Testing](#testing)
- [Updating](#updating)

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/JHustonC/pob-pipeline.git
cd pob-pipeline

# 2. Install PoB repo (for headless validation)
git clone https://github.com/PathOfBuildingCommunity/PathOfBuilding.git ~/pob_repo

# 3. Install LuaJIT
brew install luajit

# 4. Run tests
python3 test_pob_pipeline.py

# 5. Start leveling tracker
python3 pob_leveling.py --build earthshatter_berserker_god_tier --league Settlers

# 6. Open dashboard
open pob_leveling_dashboard.html
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Python Scripts (business logic)                    │
│  ├── pob_leveling.py        ← parses client.txt     │
│  ├── pob_update_manager.py  ← git diff + tests      │
│  ├── pob_target_build_store.py ← JSON persistence  │
│  ├── pob_oauth_import.py    ← OAuth + char import   │
│  ├── pob_passive_converter.py ← headless PoB        │
│  ├── pob_add_character_loadout.py ← loadout builder │
│  ├── pob_trade_query_generator.py ← trade queries   │
│  ├── pob_stash_currency_client.py ← stash + NW      │
│  └── test_pob_pipeline.py   ← 52 unit tests         │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│  HTML/JS Dashboards (UI)                            │
│  ├── pob_pipeline_dashboard.html  ← endgame UI      │
│  └── pob_leveling_dashboard.html  ← leveling UI     │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│  PoB Headless (LuaJIT)                              │
│  └── HeadlessWrapper.lua + converter scripts        │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│  Data Files (Exile-UI + PoB repo)                   │
│  ├── areas.json, gems.json, guide.json, tree.json  │
│  └── client.txt (PoE log)                           │
└─────────────────────────────────────────────────────┘
```

---

## Features

### 1. Leveling Assistant (`pob_leveling.py`)

Reads PoE chat logs (`client.txt`) to track:
- **Zone changes** — "You have entered X"
- **Level ups** — "CharacterName (Class) is now level X"
- **Quest completions** — "Quest completed: X"
- **Lab trials** — Which zones have trials (first character only)
- **Gem recommendations** — Based on Exile-UI gems.json + target build
- **Passive tree guide** — Next node to take per Exile-UI tree.json
- **Milestone comparison** — At key zones/levels, triggers pipeline comparison

### 2. OAuth Character Import (`pob_oauth_import.py`)

- PKCE (S256) authorization flow
- Local callback server (ports 49082-49084)
- Token persistence with auto-refresh
- PoEAPIClient with league/character/stash endpoints

### 3. Passive Tree Validation (`pob_passive_converter.py`)

- Headless PoB via `POB_CONVERTER_SCRIPT` + `POB_CONVERTER_ARG{N}` env vars
- Validates passive hashes against tree version (3_29, 3_28, etc.)
- Detects missing/cluster nodes

### 4. Loadout Builder (`pob_add_character_loadout.py`)

- Extracts slot templates (74 slots)
- Config templates (23 inputs, 28 placeholders)
- Creates SkillSet/ItemSet/ConfigSet/Tree.Spec from character data

### 5. Trade Query Generator (`pob_trade_query_generator.py`)

- Weighted stat queries with currency type mapping
- Character level caps and item level filters
- `create_earthshatter_berserker_query()` factory

### 6. Stash & Currency (`pob_stash_currency_client.py`)

- PoEStashClient — stash tabs, items, currency
- CurrencyExchangeClient — public CDN rates
- NetWorth calculator (chaos/divine/exalted/mirror)
- Liquid budget computation

### 7. Farming Strategies (`pob_farming_strategies.py`)

- League detection (3.30 Settlers/Kingsmarch, 3.29 Necropolis, etc.)
- Strategy registry with `FarmingMethod` enum
- `Applicability` enum (verified/needs_review/obsolete)
- Priority sorting by div/hr × confidence

### 8. Target Build Store (`pob_target_build_store.py`)

- Persistent JSON store at `~/.pob_pipeline/target_builds.json`
- Templates: god_tier, budget, HC
- CRUD, duplicate, import/export, tags

### 9. Update Manager (`pob_update_manager.py`)

- Tracks PoB commit hash
- Detects breaking changes across 8 file categories
- Runs test suite
- Provides migration guides

---

## File Structure

```
pob-pipeline/
├── README.md
├── pob_leveling.py
├── pob_leveling_dashboard.html
├── pob_pipeline_dashboard.html
├── pob_oauth_import.py
├── pob_passive_converter.py
├── pob_add_character_loadout.py
├── pob_trade_query_generator.py
├── pob_stash_currency_client.py
├── pob_target_build_store.py
├── pob_farming_strategies.py
├── pob_update_manager.py
├── test_pob_pipeline.py
├── e2e_midgame_test.py
├── pob-pipeline-package.sh
└── skills/
    ├── pob-character-import/
    ├── pob-crafting-guide-finder/
    ├── pob-farming-strategies/
    ├── pob-find-upgrades-trade/
    ├── pob-oauth-to-loadout/
    ├── pob-stash-currency-api/
    ├── pob-target-build-store/
    ├── pob-update-manager/
    └── pobb-in-build-extraction/
```

---

## Skills

| Skill | Description |
|-------|-------------|
| `pob-character-import` | OAuth + public API character import |
| `pob-oauth-to-loadout` | Full pipeline: OAuth → character → loadout → upgrades |
| `pobb-in-build-extraction` | Extract PoB build from pobb.in links |
| `pob-stash-currency-api` | Stash API + currency exchange + net worth |
| `pob-find-upgrades-trade` | Weighted trade query builder |
| `pob-crafting-guide-finder` | Crafting taxonomy + decision matrix |
| `pob-farming-strategies` | League-aware farming with verification |
| `pob-update-manager` | PoB update tracking + migration |
| `pob-target-build-store` | Target build persistence |

---

## Requirements

- **macOS** (paths assume macOS; adjust for Linux/Windows)
- **LuaJIT**: `brew install luajit`
- **Python 3.9+**: requests, stdlib only
- **PoE log**: `~/Documents/My Games/Path of Exile/logs/client.txt`
- **PoB repo**: `~/pob_repo` (dev branch)

---

## Configuration

Edit `pob_leveling.py`:
```python
DEFAULT_LOG_PATH = Path.home() / "Documents/My Games/Path of Exile/logs/client.txt"
```

Edit `pob_update_manager.py`:
```python
POB_REPO = Path("/Users/joecrawford/pob_repo")
```

---

## Testing

```bash
# Run all 52 tests
python3 test_pob_pipeline.py

# Run specific test class
python3 -m pytest test_pob_pipeline.py::TestLevelingTracker -v
```

---

## Updating

```bash
# Check for PoB updates
python3 pob_update_manager.py check

# Full update (pull + migrate + test)
python3 pob_update_manager.py update

# Status
python3 pob_update_manager.py status
```

---

## License

MIT

---

## Credits

- [Path of Building](https://github.com/PathOfBuildingCommunity/PathOfBuilding) — PoB repo
- [Exile-UI](https://github.com/Lailloken/Exile-UI) — Leveling data (areas, gems, guide, tree)
- [PoB Community](https://github.com/PathOfBuildingCommunity) — PoB development
