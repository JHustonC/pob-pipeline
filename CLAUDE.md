# CLAUDE.md - Agent Guidance for PoB Pipeline

## Project Overview

This is a **Path of Building build collaboration pipeline** - a complete automation system for PoE build management with cross-device sync. It runs as pure deterministic code (Python, LuaJIT, HTML/JS) with **zero LLM runtime dependency**.

## Critical Context for Any Agent

### 1. Architecture is Split Across Two Machines

| Machine | Role | Key Process |
|---------|------|-------------|
| **Gaming (Windows)** | Data source | `fetch_character_server.py` - OAuth, GGG API, Gist sync |
| **Viewing (Any)** | Dashboard | GitHub Pages reads from Gist |

**The "Fetch Character" button ONLY works on `localhost:8080` (gaming machine).** GitHub Pages is read-only.

### 2. OAuth Flow is Localhost-Only

```python
# In pob_oauth_import.py
CALLBACK_PORTS = [49082, 49083, 49084]
REDIRECT_URI = "http://localhost:49082"
```

- PKCE S256, no client secret
- Local callback server MUST run on gaming machine
- Tokens persisted to `~/.pob_pipeline/poe_tokens.json`

### 3. Headless PoB Uses Env Vars (Not CLI Args)

```bash
# In pob_passive_converter.py
POB_CONVERTER_SCRIPT=passive_converter_post.lua
POB_CONVERTER_ARG1=class_id
POB_CONVERTER_ARG2=ascendancy_id
POB_CONVERTER_ARG3=hashes_json
```

Modified `HeadlessWrapper.lua` detects `POB_CONVERTER_SCRIPT` and runs converter after `build` object init.

### 4. Current League is 3.30 Covens of Umbra

Farming strategies prioritize:
- Covens Fate Selection (~2 div/hr) - VERIFIED
- Kingsmarch Daily (~2 div/hr) - VERIFIED
- Thread Farming 10 types (~1.5 div/hr) - VERIFIED
- T16-17 Maps (~3 div/hr) - VERIFIED

Old strategies (Delirium Simulacrum, Scarabs) marked OBSOLETE.

### 5. Cross-Device Sync = GitHub Gist (Secret)

```python
# In gist_sync.py
sync = GistSync(gist_id=GH_GIST_ID, token=GH_TOKEN)
sync.push({"character_state.json": state})
```

- Gaming machine pushes every 30s
- Dashboard reads via GitHub API
- No tunnel/VPN needed

---

## Agent Workflows

### When User Says "Run the Pipeline"

```bash
# On gaming machine (Windows)
cd C:\Users\Shadow\pob-pipeline
start_pob_pipeline.bat
# → Opens browser for OAuth → Pick character → Auto-syncs to Gist

# On any device
open https://jhustonc.github.io/pob-pipeline/
```

### When User Says "Test Everything"

```bash
cd /Users/joecrawford/.hermes/profiles/bot-of-exile/scripts/repo/pob-pipeline
python test_pob_pipeline.py
# Must see: 72 passed
```

### When User Says "PoB Updated"

```bash
python pob_update_manager.py check
# Shows: commits behind, breaking changes, migration guide

python pob_update_manager.py update
# Pulls, runs tests, migrates configs
```

### When User Says "Compare Builds"

```bash
python compare_builds.py
# Shows tier-by-tier comparison table
```

### When User Says "Add Farming Strategy"

1. Edit `pob_farming_strategies.py`
2. Add to `STRATEGY_REGISTRY` with `FarmingMethod`, `Applicability`, `div_per_hour`, `confidence`
3. Add test in `TestFarmingStrategies`
4. Run tests

---

## Common Pitfalls to Avoid

| Pitfall | Correct Approach |
|---------|------------------|
| Trying OAuth from GitHub Pages | Must run on gaming machine localhost |
| Using CLI args for headless PoB | Use env vars `POB_CONVERTER_SCRIPT` + `POB_CONVERTER_ARG{N}` |
| Assuming GitHub Pages can write | It's static - only reads from Gist |
| Forgetting league version | Always check `League.SETTLERS_KINGSMARCH` for 3.30 |
| Not running tests before commit | `python test_pob_pipeline.py` must pass (72 tests) |

---

## Key File Locations

| Component | Path |
|-----------|------|
| Main server | `scripts/fetch_character_server.py` |
| OAuth | `scripts/pob_oauth_import.py` |
| Passive converter | `scripts/pob_passive_converter.py` |
| Loadout builder | `scripts/pob_add_character_loadout.py` |
| Trade queries | `scripts/pob_trade_query_generator.py` |
| Stash/currency | `scripts/pob_stash_currency_client.py` |
| Farming | `scripts/pob_farming_strategies.py` |
| Target builds | `scripts/pob_target_build_store.py` |
| Update manager | `scripts/pob_update_manager.py` |
| Leveling | `scripts/pob_leveling.py` |
| Gist sync | `scripts/gist_sync.py` |
| Tests | `scripts/test_pob_pipeline.py` |
| Windows setup | `scripts/setup_windows.py` |
| Dashboard (Pages) | `dashboards/index.html` |
| Full dashboard | `dashboards/pob_leveling_dashboard.html` |
| PoB repo | `/Users/joecrawford/pob_repo` (dev branch) |
| Data dir | `~/.pob_pipeline/` |

---

## Skills to Load for Specific Tasks

```python
# Full OAuth → Loadout pipeline
skill_view("pob-oauth-to-loadout")

# Character import methods
skill_view("pob-character-import")

# 3.30 farming strategies
skill_view("pob-farming-strategies")

# Crafting decision matrix
skill_view("pob-crafting-guide-finder")

# Net worth calculation
skill_view("pob-stash-currency-api")

# Trade query building
skill_view("pob-find-upgrades-trade")

# PoB update tracking
skill_view("pob-update-manager")

# Target build templates
skill_view("pob-target-build-store")

# Leveling page with lab map
skill_view("pob-leveling-page")

# pobb.in build extraction
skill_view("pobb-in-build-extraction")
```

---

## Environment Variables Reference

```bash
# Required for cross-device sync
GH_GIST_ID=abc123def456
GH_TOKEN=ghp_xxxxxxxxxxxx

# PoE OAuth (public client)
POE_CLIENT_ID=pob
POE_REDIRECT_URI=http://localhost:49082
POE_SCOPES=account:profile,account:characters,account:stashes,account:trade

# PoB repo (headless)
POB_REPO_PATH=/Users/joecrawford/pob_repo
POB_TREE_VERSION=3_29

# Paths
PIPELINE_DATA_DIR=~/.pob_pipeline
LOG_LEVEL=INFO
```

---

## Test Coverage Map

| Module | Test Class | Tests | Key Assertions |
|--------|------------|-------|----------------|
| OAuth | TestOAuthImport | 6 | PKCE, authorize URL, token exchange, refresh |
| Passive | TestPassiveConverter | 5 | Hash validation, tree version, class/ascendancy |
| Loadout | TestAddCharacterLoadout | 5 | Slot templates, config extraction, loadout creation |
| Trade | TestTradeQueryGenerator | 7 | Weights, currency, level caps, factory |
| Stash | TestStashCurrencyClient | 8 | Stash tabs, items, rates, net worth, liquid budget |
| Builds | TestTargetBuildStore | 10 | CRUD, templates, duplicate, import/export, tags |
| Farming | TestFarmingStrategies | 20 | League detection, applicability, verification, 3.30 |
| Leveling | TestLevelingTracker | 8 | Zone parsing, level tracking, quests, lab trials |
| Updates | TestUpdateManager | 7 | Config, commit detection, breaking changes, migration |
| Dashboard | TestDashboard | 3 | localStorage, pipeline overlay, dev panel |
| Integration | TestIntegration | 3 | Full pipeline, Gist sync, OAuth flow |

---

## Deployment Checklist

- [ ] Tests pass: `python test_pob_pipeline.py` (72/72)
- [ ] Push to main: `git push origin main`
- [ ] GitHub Pages rebuilds (1-2 min)
- [ ] Dashboard loads: https://jhustonc.github.io/pob-pipeline/
- [ ] Gaming machine: `start_pob_pipeline.bat` runs
- [ ] OAuth completes, character selected
- [ ] Gist updates with character_state.json
- [ ] Dashboard shows character data

---

## For New Agent Instances

1. **Read README.md** - Complete documentation
2. **Read QUICKSTART.md** - 30-second orientation
3. **Run tests** - `python test_pob_pipeline.py`
4. **Load relevant skill** - Based on task
5. **Understand two-machine architecture** - Gaming + Viewing

---

*This file ensures any agent instance has immediate productive context.*