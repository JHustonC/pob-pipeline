---
name: pob-update-manager
category: path-of-building
version: "1.0.0"
author: "bot-of-exile"
license: "MIT"
description: Track PoB commits, detect breaks, run tests, migrate config.
metadata:
  hermes:
    tags: ["pob", "update", "migration", "automation"]
    related_skills: ["pob-oauth-to-loadout", "pob-find-upgrades-trade", "pob-character-import"]
---

# PoB Update Manager

**Use when** PoB repo updates and you need to validate compatibility, run tests, and migrate configs.

## When to Use
- After pulling updates from `PathOfBuildingCommunity/PathOfBuilding` dev branch
- Before running overnight pipeline to ensure compatibility
- When test suite fails unexpectedly after PoB changes
- When new league launches (tree version, ascendancy, item base changes)

## Features
- Tracks PoB commit hash and tree version
- Detects breaking changes via file diffs
- Runs test suite and reports failures
- Provides migration guides for common changes
- Updates stored configs (target builds, OAuth tokens)

## Quick Start
```bash
# Check for updates and run validation
python3 pob_update_manager.py check

# Full update with migration
python3 pob_update_manager.py update

# Show current status
python3 pob_update_manager.py status
```

## Test Integration
- Run from `/Users/joecrawford/.hermes/profiles/bot-of-exile/scripts/` directory
- Executes `test_pob_pipeline.py` (45 tests covering all pipeline modules)
- Exit codes: 0 = up to date, 1 = review needed (breaking changes but tests pass), 2 = action required (test failures)
- Always run `check` after manual migrations to validate

## Files Monitored
| File | Breaking Change Type |
|------|---------------------|
| `src/Tree/PassiveTree.lua` | Tree version, node IDs |
| `src/Classes/TradeQueryGenerator.lua` | Query structure, stat weights |
| `src/Classes/Item.lua` | Item bases, mods, influences |
| `src/Classes/Skill.lua` | Skill gems, tags, stats |
| `src/Classes/Build.lua` | Build JSON structure |
| `src/Classes/CharacterClass.lua` | Class/ascendancy IDs |
| `src/ModParser.lua` | Mod parsing rules |
| `HeadlessWrapper.lua` | Headless API, env vars |
| `Data/*.dat` | Game data (auto-managed) |

## Detection Logic
- Uses directory prefix matching (e.g., `src/Classes/` matches TradeQueryGenerator, Item, Skill, Build, CharacterClass, ModParser)
- Single file can trigger multiple categories — expect over-detection, filter in review
- Run `check` command to see exact files per category before migrating

## Migration Guides
Auto-generated for:
- **Tree version bump** → Update `tree_version` in passive converter, re-validate all hashes
- **New ascendancy/class** → Add IDs to `get_class_id()`/`get_ascendancy_id()`
- **Trade query changes** → Sync `pob_trade_query_generator.py` with Lua
- **Item base changes** → Update `create_*_template()` target items
- **Headless API changes** → Update `POB_CONVERTER_SCRIPT` env var handling

## Config
```json
{
  "pob_repo": "/Users/joecrawford/pob_repo",
  "last_known_commit": "abc123",
  "last_tree_version": "3_29",
  "last_test_run": "2024-01-15T10:30:00Z",
  "last_test_result": "PASS",
  "tracked_configs": [
    "~/.pob_pipeline/target_builds.json",
    "~/.pob_pipeline/poe_tokens.json"
  ]
}
```

## Migration Guide Details
Auto-generated for each detected category with:
- **Title** — Human-readable change type
- **Steps** — Ordered migration actions
- **Files to update** — Python files that need syncing

Run `check` to preview guide before `update`. After manual fixes, re-run `check` to validate.

## Common Pitfalls
- **Over-detection**: `src/Classes/` prefix matches 6 files — single change can flag 5+ categories. Filter by actual file list in `check` output.
- **Tree version parsing**: Relies on regex in `PassiveTree.lua`. If format changes, `get_tree_version()` returns default `3_29`.
- **Test dependencies**: `test_pob_pipeline.py` imports all pipeline modules. Missing imports = test collection errors, not test failures.
- **Config path**: Uses `~/.pob_pipeline/update_manager.json`. Ensure directory exists (auto-created on first `init`).
- **Test integration**: `pob_update_manager.py` runs `test_pob_pipeline.py` from scripts directory. Must `cd` to scripts dir before running tests, or tests fail to import modules.
- **Exit codes**: 0 = up to date, 1 = breaking changes but tests pass (review needed), 2 = test failures (action required). Use these in CI/CD.
- **Migration validation**: After manual migration, always re-run `check` to validate. Don't assume manual edits worked.