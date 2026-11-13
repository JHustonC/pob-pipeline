# Quick Start Guide

## For Another Hermes Instance

### 1. Understand the Project in 30 Seconds

This is a **PoE build pipeline** with:
- **Gaming machine** (Windows) runs `fetch_character_server.py` → OAuth → syncs to GitHub Gist
- **Dashboard** (GitHub Pages) reads from Gist → shows character, lab map, ascendency, crafting checklist
- **Headless PoB** validates passives, runs upgrade queries, creates loadouts

### 2. Key Files to Read First

| File | Purpose |
|------|---------|
| `README.md` | Full documentation |
| `fetch_character_server.py` | Main entry point |
| `pob_oauth_import.py` | OAuth + character import |
| `pob_leveling.py` | Leveling tracker |
| `test_pob_pipeline.py` | 72 tests |

### 3. Run Tests to Verify

```bash
cd /Users/joecrawford/.hermes/profiles/bot-of-exile/scripts/repo/pob-pipeline
python test_pob_pipeline.py
# Should show: 72 passed
```

### 4. Understand the Data Flow

```
GGG OAuth → Character Data → Gist Sync → GitHub Pages Dashboard
                ↓
         Headless PoB (passive validation, upgrades, loadouts)
```

### 5. Key Configuration

- **Gist ID**: In `.env` → `GH_GIST_ID`
- **GitHub Token**: In `.env` → `GH_TOKEN` (fine-grained PAT, gist scope)
- **PoB Repo**: `~/pob_repo` (dev branch, tree 3_29)
- **PoE Log**: `~/Documents/My Games/Path of Exile/logs/client.txt`

### 6. Common Tasks

| Task | Command |
|------|---------|
| Run all tests | `python test_pob_pipeline.py` |
| Check PoB updates | `python pob_update_manager.py check` |
| Start gaming machine server | `start_pob_pipeline.bat` (Windows) |
| View dashboard | https://jhustonc.github.io/pob-pipeline/ |

---

## Project Context for Agents

### What This Project Is NOT
- Not a PoE bot/automation (no gameplay automation)
- Not a trade bot (queries only, no auto-buy)
- Not an LLM-dependent system (pure deterministic code)

### What This Project IS
- Build planning & tracking system
- Cross-device character state sync
- Headless PoB integration for validation
- League-aware farming strategy database
- Leveling assistant with real log parsing

### Skills Available

Load these skills for specific tasks:
```python
skill_view("pob-oauth-to-loadout")      # Full pipeline
skill_view("pob-character-import")      # OAuth methods
skill_view("pob-farming-strategies")    # 3.30 strategies
skill_view("pob-crafting-guide-finder") # Crafting matrix
skill_view("pob-stash-currency-api")    # Net worth
skill_view("pob-find-upgrades-trade")   # Trade queries
skill_view("pob-update-manager")        # PoB updates
skill_view("pob-target-build-store")    # Build templates
skill_view("pob-leveling-page")         # Leveling UI
skill_view("pobb-in-build-extraction")  # pobb.in decoding
```

### Testing Philosophy

- **Every action has a test** - 72 tests cover all modules
- **Run tests before committing** - `python test_pob_pipeline.py`
- **Integration test** - `python e2e_midgame_test.py`

---

## Quick Commands Reference

```bash
# Full test suite
python test_pob_pipeline.py

# Specific module test
python -m pytest test_pob_pipeline.py::TestFarmingStrategies -v

# Update manager
python pob_update_manager.py status
python pob_update_manager.py check
python pob_update_manager.py update

# Leveling tracker
python pob_leveling.py --build earthshatter_berserker_god_tier --league Settlers

# OAuth flow (on gaming machine)
python pob_oauth_import.py

# Passive validation
python pob_passive_converter.py

# Farming strategies
python pob_farming_strategies.py

# Target builds
python pob_target_build_store.py list
python pob_target_build_store.py template earthshatter_berserker god_tier

# Windows setup (on gaming machine)
python setup_windows.py
```

---

## Directory Map

```
/Users/joecrawford/.hermes/profiles/bot-of-exile/scripts/repo/pob-pipeline/
├── README.md                 # ← Start here
├── fetch_character_server.py # Main server
├── gist_sync.py              # Gist sync
├── pob_*.py                  # Core modules
├── test_pob_pipeline.py      # 72 tests
├── setup_windows.py          # Windows setup
├── start_pob_pipeline.bat    # Windows launcher
├── PoBPipeline_Task.xml      # Task Scheduler
├── .env.example              # Config template
├── dashboards/
│   ├── index.html            # GitHub Pages
│   └── pob_leveling_dashboard.html
└── skills/                   # 9 skill directories
```

---

*This guide gets any agent instance productive immediately.*