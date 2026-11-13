# PoB Pipeline — Path of Building Build Collaboration System

A complete end-to-end pipeline for Path of Exile build management, featuring OAuth character import, headless PoB passive tree validation & upgrade queries, stash/currency analysis, trade query generation, league-aware farming strategies, crafting guide finder, leveling assistant, target build store, cross-device sync via GitHub Gist, and update manager.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Core Modules](#core-modules)
- [File Structure](#file-structure)
- [Configuration](#configuration)
- [Running the Pipeline](#running-the-pipeline)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [League Awareness](#league-awareness)
- [Decision Matrix (Crafting)](#decision-matrix-crafting)
- [Cross-Device Setup](#cross-device-setup)
- [Version History](#version-history)

---

## Quick Start

### On Gaming Machine (Windows)

```cmd
# 1. Clone repo
cd C:\Users\Shadow
git clone https://github.com/JHustonC/pob-pipeline.git
cd pob-pipeline

# 2. One-time setup
python setup_windows.py
# Creates: .env, start_pob_pipeline.bat, PoBPipeline_Task.xml

# 3. Edit .env with your credentials
notepad .env
# Required:
# GH_GIST_ID=your-gist-id          # Secret Gist for cross-device sync
# GH_TOKEN=ghp_xxx...              # Fine-grained PAT with gist scope
# POE_CLIENT_ID=pob                # Public client ID
# POE_REDIRECT_URI=http://localhost:49082

# 4. Run the server
start_pob_pipeline.bat

# 5. In browser: http://localhost:8080
#    Click "🔐 Fetch Character" → Authorize → Pick character
```

### On Any Device (View Dashboard)

Visit: **https://jhustonc.github.io/pob-pipeline/**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GAMING MACHINE (Windows)                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ fetch_character_server.py                                            │   │
│  │   ├── OAuth PKCE (S256) → GGG API                                   │   │
│  │   ├── Callback server: localhost:49082-49084                        │   │
│  │   ├── Fetches: level, zone, passives, equipment, gems, stash        │   │
│  │   ├── Auto-sync to GitHub Gist every 30s                            │   │
│  │   └── Serves dashboard: http://localhost:8080                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                              Pushes to GitHub Gist
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ANY DEVICE (Dashboard)                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ https://jhustonc.github.io/pob-pipeline/ (GitHub Pages)             │   │
│  │   ├── Reads character_state.json from Gist                          │   │
│  │   ├── Shows: level, zone, gems, passives, gear                      │   │
│  │   ├── Lab map (fetches daily from poelab.com)                       │   │
│  │   ├── Ascendency choice panel (8 points + next node stats)          │   │
│  │   ├── Crafting checklist (6 stages Campaign→God Tier)               │   │
│  │   └── Next gem/passive recommendations                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                              Headless PoB (luajit)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PoB REPO (/Users/joecrawford/pob_repo)                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ HeadlessWrapper.lua + find_upgrades.lua + passive_converter_post.lua │   │
│  │   ├── Validates passive hashes against tree 3_29                    │   │
│  │   ├── Runs upgrade queries with budget limits                       │   │
│  │   └── Creates loadouts from character data                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Modules

### 1. OAuth & Character Import (`pob_oauth_import.py`)

```python
from pob_oauth_import import run_oauth_flow, PoEAPIClient

# Run OAuth flow (starts callback server on localhost:49082)
client = run_oauth_flow()

# Fetch character
character = client.get_character("CharacterName")
# Returns: level, class, ascendancy, passives, items, gems, stash tabs
```

**Features:**
- PKCE S256 (no client secret needed)
- Local callback server (ports 49082-49084)
- Token persistence at `~/.pob_pipeline/poe_tokens.json`
- Auto-refresh on expiry
- Scopes: `account:profile`, `account:characters`, `account:stashes`, `account:trade`

---

### 2. Passive Converter (`pob_passive_converter.py`)

```python
from pob_passive_converter import convert_passive_hashes

# Validate passive hashes against PoB tree
result = convert_passive_hashes(
    character_class=1,      # Marauder
    ascendancy=2,           # Berserker
    passive_hashes=["hash1", "hash2", ...],
    tree_version="3_29"
)
# Returns: {valid_nodes: [...], missing: [...], cluster_jewels: [...]}
```

**Headless PoB Integration:**
- Uses `POB_CONVERTER_SCRIPT` + `POB_CONVERTER_ARG{N}` env vars
- Modified `HeadlessWrapper.lua` detects env var and runs converter
- Runs: `luajit HeadlessWrapper.lua passive_converter_post.lua`

---

### 3. Loadout Creator (`pob_add_character_loadout.py`)

```python
from pob_add_character_loadout import create_loadout_from_character

loadout = create_loadout_from_character(character_data, target_build)
# Creates: SkillSet, ItemSet, ConfigSet, Tree.Spec
# Extracts: 74 slot templates, 23 config inputs, 28 placeholders
```

---

### 4. Trade Query Generator (`pob_trade_query_generator.py`)

```python
from pob_trade_query_generator import TradeQueryBuilder, create_earthshatter_berserker_query

# Build query with stat weights
builder = TradeQueryBuilder()
query = builder.build_query(
    slot="Weapon 1",
    base_type="Infernal Sword",
    stats={"phys_dps": 1.0, "crit_chance": 0.8, "attack_speed": 0.5},
    budget=50,  # divines
    currency="divine"
)

# Or use factory for Earthshatter Berserker
query = create_earthshatter_berserker_query(budget=100)
```

**Features:**
- CurrencyType enum (chaos, divine, exalted, mirror)
- Slot→category mapping
- Stat weight helpers
- Character level caps
- Price limits (min/max)

---

### 5. Stash & Currency (`pob_stash_currency_client.py`)

```python
from pob_stash_currency_client import PoEStashClient, CurrencyExchangeClient, NetWorthCalculator

# Stash tabs
stash = PoEStashClient(oauth_client)
tabs = stash.get_stash_tabs("Settlers of Kalguur")
items = stash.get_stash_items("Settlers of Kalguur", tab_index=0)

# Currency rates (public CDN - no auth needed)
currency = CurrencyExchangeClient()
rates = currency.get_rates()  # chaos, divine, exalted, mirror

# Net worth
net_worth = NetWorthCalculator(rates)
total_chaos = net_worth.calculate(items)
liquid_budget = net_worth.get_liquid_budget(total_chaos, spend_pct=0.4)
```

---

### 6. Farming Strategies (`pob_farming_strategies.py`)

```python
from pob_farming_strategies import get_farming_strategies, League

# Get strategies for current league (3.30 Covens of Umbra)
strategies = get_farming_strategies(League.SETTLERS_KINGSMARCH)

# Each strategy has:
# - method: FarmingMethod (MAPS, HEIST, SANCTUM, COVENS_FATE, etc.)
# - applicability: Applicability (VERIFIED, NEEDS_REVIEW, OBSOLETE)
# - div_per_hour: estimated div/hr
# - confidence: 0.0-1.0
# - requirements: list of requirements
# - priority_score = div_per_hour * confidence
```

**3.30 Covens of Umbra Strategies:**
| Method | Div/hr | Confidence | Applicability |
|--------|--------|------------|---------------|
| Covens Fate Selection | 2.0 | 0.85 | VERIFIED |
| Thread Farming (10 types) | 1.5 | 0.8 | VERIFIED |
| Kingsmarch Daily | 2.0 | 0.9 | VERIFIED |
| T16-17 Maps | 3.0 | 0.75 | VERIFIED |
| Boss Carries | 5.0 | 0.6 | NEEDS_REVIEW |
| Heist | 2.5 | 0.7 | VERIFIED |
| Sanctum | 3.0 | 0.65 | NEEDS_REVIEW |
| Mirage Core | 2.0 | 0.6 | NEEDS_REVIEW |

---

### 7. Target Build Store (`pob_target_build_store.py`)

```python
from pob_target_build_store import TargetBuildStore, TargetBuild, TargetItem

store = TargetBuildStore()

# Create from template
build = store.create_from_template("earthshatter_berserker", "god_tier")
# Or create custom
build = TargetBuild(
    name="my_build",
    class_name="Berserker",
    ascendancy="Berserker",
    target_level=100,
    main_skill="Earthshatter",
    budget_div=200,
    tags=["endgame", "bossing"]
)

# Add items
build.add_item(TargetItem(
    slot="Weapon 1",
    base_type="Infernal Sword",
    rarity="unique",
    name="Ashes of the Stars",
    priority=10,
    notes="God tier: Ashes. Budget: rare with phys% + crit multi"
))

store.save(build)
```

**Templates Included:**
- `earthshatter_berserker_god_tier` (~500+ div)
- `earthshatter_berserker_mid_tier` (~150-200 div)
- `earthshatter_berserker_budget` (~30-50 div)
- `earthshatter_berserker_hc` (SSFHC viable)
- `facebreaker_luminary_god_tier`
- `facebreaker_luminary_mid_tier`
- `facebreaker_luminary_budget`
- `kinetic_blast_wander`

---

### 8. Update Manager (`pob_update_manager.py`)

```python
from pob_update_manager import PoBUpdateManager

manager = PoBUpdateManager()

# Initialize with current PoB state
manager.init(pob_repo_path="/Users/joecrawford/pob_repo")

# Check for updates
status = manager.check()
# Returns: {has_updates, commits_behind, breaking_changes, migration_guide}

# Detect breaking changes across 8 categories
changes = manager.detect_breaking_changes()
# Categories: passive_tree, items, skills, config, ui, data, build_format, headless

# Apply update
manager.update()
# Runs tests, migrates configs, updates stored data
```

**Monitors 8 file categories for breaking changes:**
1. `src/Classes/Passive*` - Passive tree
2. `src/Classes/Item*` - Items
3. `src/Classes/Skill*` - Skills
4. `src/Classes/Config*` - Configuration
5. `src/Classes/Controls*` - UI controls
6. `src/Data/` - Data files
7. `src/Classes/Build.lua` - Build format
8. `HeadlessWrapper.lua` - Headless wrapper

---

### 9. Leveling Tracker (`pob_leveling.py`)

```python
from pob_leveling import LevelingTracker

tracker = LevelingTracker(
    log_path="~/Documents/My Games/Path of Exile/logs/client.txt",
    exile_ui_data_path="./exile_ui_data"
)

# Parse client.txt for:
# - Zone transitions ("You have entered ZoneName.")
# - Level ups ("CharacterName (Class) is now level 45.")
# - Quest completions ("Quest completed: quest_name")
# - Lab trials ("You have completed the Trial of ...")

tracker.parse_log()

# Get recommendations
next_gem = tracker.get_next_gem_recommendation()
next_passive = tracker.get_next_passive_recommendation()
lab_trial = tracker.get_current_lab_trial()
```

**Exile-UI Data Sources (auto-downloaded):**
- `areas.json` - Zone info + lab trial locations
- `gems.json` - Gem unlock requirements by quest
- `default_guide.json` - Leveling milestones
- `tree_3_29.json` - Passive tree node ordering

---

### 10. Gist Sync (`gist_sync.py`)

```python
from gist_sync import GistSync

sync = GistSync(
    gist_id="your-gist-id",
    token="ghp_xxx...",
    files={
        "character_state.json": character_state,
        "target_builds.json": target_builds,
        "poe_tokens.json": tokens
    }
)

# Push to Gist
sync.push()

# Pull from Gist
data = sync.pull()
```

**Cross-device flow:**
1. Gaming machine pushes `character_state.json` every 30s
2. Dashboard reads from Gist via GitHub API
3. No tunnel/VPN needed - works across networks

---

## File Structure

```
pob-pipeline/
├── .github/
│   └── workflows/           # CI/CD for GitHub Pages
├── docs/                    # Documentation
├── scripts/                 # Python pipeline scripts
│   ├── fetch_character_server.py    # Main server (OAuth, Gist sync, dashboard)
│   ├── gist_sync.py                 # GitHub Gist sync module
│   ├── pob_oauth_import.py          # OAuth PKCE + PoEAPIClient
│   ├── pob_passive_converter.py     # Headless PoB passive validation
│   ├── pob_add_character_loadout.py # Loadout creation from char data
│   ├── pob_trade_query_generator.py # Weighted trade query builder
│   ├── pob_stash_currency_client.py # Stash API + currency + net worth
│   ├── pob_farming_strategies.py    # League-aware farming (3.30 updated)
│   ├── pob_target_build_store.py    # Persistent target build store
│   ├── pob_update_manager.py        # PoB update tracking & migration
│   ├── pob_leveling.py              # Leveling tracker + log parser
│   ├── setup_windows.py             # Windows one-click setup
│   ├── compare_builds.py            # Build tier comparison
│   ├── e2e_midgame_test.py          # Full pipeline integration test
│   └── test_pob_pipeline.py         # 72 tests across 11 test classes
├── dashboards/
│   ├── index.html                    # Main dashboard (GitHub Pages)
│   ├── pob_leveling_dashboard.html   # Full leveling dashboard
│   └── crafting_checklist.html       # Crafting checklist (legacy)
├── config/
│   ├── .env.example                  # Environment template
│   └── pob_pipeline_config.json      # Pipeline configuration
├── data/
│   ├── target_builds.json            # Target build store (auto-generated)
│   ├── poe_tokens.json               # OAuth tokens (auto-generated)
│   └── character_state.json          # Current character (auto-generated)
├── tests/
│   └── test_*.py                     # Unit & integration tests
├── start_pob_pipeline.bat            # Windows launcher
├── PoBPipeline_Task.xml              # Task Scheduler for auto-start
├── requirements.txt                  # Python dependencies
└── README.md                         # This file
```

---

## Configuration

### Environment Variables (`.env`)

```bash
# GitHub Gist (required for cross-device sync)
GH_GIST_ID=abc123def456
GH_TOKEN=ghp_xxxxxxxxxxxx

# PoE OAuth
POE_CLIENT_ID=pob
POE_REDIRECT_URI=http://localhost:49082
POE_SCOPES=account:profile,account:characters,account:stashes,account:trade

# PoB Repo
POB_REPO_PATH=/Users/joecrawford/pob_repo
POB_TREE_VERSION=3_29

# Paths
PIPELINE_DATA_DIR=~/.pob_pipeline
LOG_LEVEL=INFO

# Optional: Trade API
TRADE_API_URL=https://www.pathofexile.com/api/trade2
```

### Windows Setup (`setup_windows.py`)

Creates:
- `.env` from template
- `start_pob_pipeline.bat` - Launcher script
- `PoBPipeline_Task.xml` - Task Scheduler for auto-start on boot
- Validates Python, Git, dependencies

---

## Running the Pipeline

### Full Pipeline (Manual)

```bash
# 1. OAuth & character import
python -m pob_oauth_import

# 2. Validate passives
python -m pob_passive_converter

# 3. Create loadout
python -m pob_add_character_loadout

# 4. Analyze stash & currency
python -m pob_stash_currency_client

# 5. Generate trade queries
python -m pob_trade_query_generator

# 6. Get farming strategies
python -m pob_farming_strategies

# 7. Update target build store
python -m pob_target_build_store

# 8. Check PoB updates
python -m pob_update_manager check
```

### Automated (Windows Task Scheduler)

```cmd
# Install as scheduled task (runs on boot, every 30 min)
schtasks /create /xml "PoBPipeline_Task.xml" /tn "PoBPipeline_FetchCharacterServer"
```

---

## Testing

```bash
# Run all tests (72 tests, 11 classes)
python test_pob_pipeline.py

# Run specific test class
python -m pytest test_pob_pipeline.py::TestOAuthImport -v
python -m pytest test_pob_pipeline.py::TestFarmingStrategies -v

# Test coverage
python -m pytest test_pob_pipeline.py --cov=pob_pipeline --cov-report=html
```

**Test Classes:**
| Class | Tests | Coverage |
|-------|-------|----------|
| TestOAuthImport | 6 | PKCE, authorize URL, token exchange, refresh |
| TestPassiveConverter | 5 | Hash validation, tree version, class/ascendancy |
| TestAddCharacterLoadout | 5 | Slot templates, config extraction, loadout creation |
| TestTradeQueryGenerator | 7 | Weights, currency, level caps, factory |
| TestStashCurrencyClient | 8 | Stash tabs, items, rates, net worth, liquid budget |
| TestTargetBuildStore | 10 | CRUD, templates, duplicate, import/export, tags |
| TestFarmingStrategies | 20 | League detection, applicability, verification, 3.30 |
| TestLevelingTracker | 8 | Zone parsing, level tracking, quests, lab trials |
| TestUpdateManager | 7 | Config, commit detection, breaking changes, migration |
| TestDashboard | 3 | localStorage, pipeline overlay, dev panel |
| TestIntegration | 3 | Full pipeline, Gist sync, OAuth flow |

---

## Deployment

### GitHub Pages (Dashboard)

```bash
# Push to main branch
git push origin main

# GitHub Actions builds and deploys to:
# https://jhustonc.github.io/pob-pipeline/
```

**Workflow:** `.github/workflows/pages.yml`
- Triggers on push to main
- Copies `index.html` + assets to `gh-pages` branch
- Deploys to GitHub Pages

### Gaming Machine (Windows)

```cmd
# One-time setup
python setup_windows.py

# Manual run
start_pob_pipeline.bat

# Auto-run on boot (Task Scheduler)
schtasks /create /xml "PoBPipeline_Task.xml" /tn "PoBPipeline_FetchCharacterServer"
```

---

## Troubleshooting

### OAuth Issues

| Issue | Fix |
|-------|-----|
| "localhost refused to connect" | Server not running. Run `start_pob_pipeline.bat` first |
| "Invalid redirect URI" | Check `.env` POE_REDIRECT_URI matches `http://localhost:49082` |
| "Token expired" | Auto-refresh should handle. Delete `~/.pob_pipeline/poe_tokens.json` to re-auth |
| Port 49082 busy | Script tries 49082, 49083, 49084. Kill process or change ports |

### Dashboard Issues

| Issue | Fix |
|-------|-----|
| Only shows crafting checklist | Hard refresh (`Ctrl+Shift+R`) or open in Incognito |
| "Fetch Character" does nothing | Button only works on `localhost:8080` (Python server), not GitHub Pages |
| Lab map not loading | Click "Refresh" button; poelab.com may be slow |
| No character data | Run OAuth flow on gaming machine first |

### Gist Sync Issues

| Issue | Fix |
|-------|-----|
| 404 on Gist | Check `GH_GIST_ID` in `.env` matches your secret Gist |
| 403 Forbidden | `GH_TOKEN` needs `gist` scope (fine-grained PAT) |
| Not updating | Server pushes every 30s. Check server logs for errors |

### Headless PoB Issues

| Issue | Fix |
|-------|-----|
| "luajit not found" | Install LuaJIT: `brew install luajit` (macOS) / download Windows binary |
| "LUA_PATH not set" | Set: `export LUA_PATH="/path/to/pob_repo/src/?.lua;;"` |
| "Passive validation failed" | Check tree version matches (3_29 for 3.30) |

---

## League Awareness

Current league: **3.30 Covens of Umbra** (Settlers of Kalguir / Kingsmarch)

**Farming priorities for 3.30:**
1. Covens Fate Selection (~2 div/hr) - VERIFIED
2. Kingsmarch Daily (~2 div/hr) - VERIFIED
3. Thread Farming 10 types (~1.5 div/hr) - VERIFIED
4. T16-17 Maps (~3 div/hr) - VERIFIED
5. Heist (~2.5 div/hr) - VERIFIED
6. Sanctum (~3 div/hr) - NEEDS_REVIEW
7. Mirage Core (~2 div/hr) - NEEDS_REVIEW
8. Boss Carries (~5 div/hr) - NEEDS_REVIEW

**Obsolete for 3.30:** Delirium Simulacrum (reworked), Old Scarabs (→ Threads)

---

## Decision Matrix (Crafting)

For each item slot, the pipeline recommends:

| Option | When to Use |
|--------|-------------|
| **Buy** | Available on trade, within budget, good rolls |
| **Craft** | Base is cheap, crafting method reliable, high ceiling |
| **Improve** | Have decent base, can add quality/enchants/fractured |
| **Farm** | League-specific drop (Delirium orbs, Expedition logbooks, Blight oils, Heist blueprints, Sanctum relics, **Covens Fates/Viscera/Threads**) |

---

## Cross-Device Setup Summary

```
Gaming Machine (Windows)                    Viewing Device (Any)
─────────────────────                       ────────────────────
1. python setup_windows.py                  1. Visit dashboard URL
2. Edit .env (Gist ID, GH_TOKEN)            
3. start_pob_pipeline.bat                   2. See character data
4. Browser: localhost:8080                  
5. Click "Fetch Character"                  
6. OAuth → Pick character                   
7. Auto-syncs to Gist every 30s             
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-11-12 | Initial release: Full pipeline with OAuth, headless PoB, farming, crafting, leveling, dashboard, Gist sync, update manager, 72 tests |

---

## Links

- **GitHub Repo:** https://github.com/JHustonC/pob-pipeline
- **Dashboard:** https://jhustonc.github.io/pob-pipeline/
- **PoB Repo:** https://github.com/PathOfBuildingCommunity/PathOfBuilding
- **Exile-UI Data:** https://github.com/Exile-UI/Exile-UI
- **poelab.com:** https://www.poelab.com/
- **Maxroll Build Guides:** https://maxroll.gg/poe/build-guides

---

## License

MIT License - See LICENSE file

---

## Credits

- [Path of Building](https://github.com/PathOfBuildingCommunity/PathOfBuilding) — PoB repo
- [Exile-UI](https://github.com/Lailloken/Exile-UI) — Leveling data (areas, gems, guide, tree)
- [PoB Community](https://github.com/PathOfBuildingCommunity) — PoB development

---

*This document provides complete project understanding for any agent instance.*