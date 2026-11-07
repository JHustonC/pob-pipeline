---
name: pob-oauth-to-loadout
category: reverse-engineer-anything
description: Full pipeline OAuth auth to PoB loadout with passive tree
version: 1.0.0
author: bot-of-exile
license: MIT
metadata:
  hermes:
    tags: [pob, path-of-building, path-of-exile, oauth, character-import, loadout]
    related_skills: [pob-character-import, pobb-in-build-extraction, pob-add-character-loadout, pob-target-build-store]
---
## When to Use
- Import a live PoE character into an existing PoB build as a new loadout
- Full automated pipeline: OAuth -> API fetch -> item/skill/passive conversion -> .build file
- Preserve existing build's loadout structure (slots, config, tree specs)

## Pipeline Overview

```
PoE Account (OAuth) -> /character/{name} API -> Headless PoB (passive validation) -> PoB JSON -> .build file
```

## Components

### 1. OAuth Authentication (`pob_oauth_import.py`)
- PKCE (S256) flow matching PoB exactly
- Local callback server on ports 49082-49084 (60s timeout)
- Token persistence with auto-refresh
- Scopes: `account:characters`, `account:profile`, `account:leagues`, `account:trade`

### 2. Character Fetch
- `GET https://api.pathofexile.com/character/{name}` (OAuth)
- Returns: passives (hashes, hashes_ex, mastery_effects), equipment, inventory, jewels, guardian, bandit, pantheon

### 3. Passive Tree Conversion (`pob_passive_converter.py`)
- Uses `luajit HeadlessWrapper.lua` with PoB's tree data
- Validates API hashes against tree nodes for correct class/ascendancy
- Separates regular nodes, cluster jewel nodes (>=65536), missing nodes
- Outputs PoB-compatible nodes string

### 4. Loadout Creation (`pob_add_character_loadout.py`)
- **Items**: Converts API item format -> PoB text format (rarity, mods, sockets, quality, influences)
- **Skills**: Extracts linked socket groups -> active + support gems per setup
- **Config**: Copies template loadout's 23 inputs + 28 placeholders, updates pantheon/bandit
- **Tree Spec**: Adds new Spec entry with validated nodes, mastery effects, cluster sockets
- **Slot Template**: Uses existing loadout's 74-slot structure (Weapon 1, Helmet, Ring 1-3, Flask 1-5, Abyssal sockets, Grafts)

## Usage

```python
# Full pipeline
from pob_add_character_loadout import import_character_to_build

import_character_to_build(
    build_path="my_build.build",
    character_name="MyCharacter",
    output_path="my_build_with_char.build",
    access_token="...",  # from pob_oauth_import.py
    refresh_token="..."
)
```

Or step by step:
```python
from pob_oauth_import import run_oauth_flow, PoEAPIClient, load_tokens, save_tokens
from pob_add_character_loadout import add_character_loadout
from pob_collab import import_build
import json

# 1. OAuth - try saved tokens first, then run flow
client = load_tokens()
if not client:
    client = run_oauth_flow()  # Opens browser, local server on 49082-49084
    save_tokens(client)

# 2. Fetch character (full data: passives, equipment, inventory, jewels, guardian, bandit, pantheon)
character = client.get_character("MyCharacter")
if not character:
    raise ValueError("Character not found or private profile")

# 3. Load build & add loadout
with open("my_build.json") as f:
    build = json.load(f)

new_build = add_character_loadout(build, character, "MyCharacter (Lv95)")

# 4. Save
with open("my_build_with_char.json", "w") as f:
    json.dump(new_build, f, indent=2)
import_build("my_build_with_char.json", "my_build_with_char.build")
```

### Validated Working Commands
```bash
# OAuth flow (first time)
python3 pob_oauth_import.py

# Full pipeline test
python3 e2e_midgame_test.py

# Headless passive hash validation
luajit HeadlessWrapper.lua passive_converter_post.lua \
  --build=my_build.json --slot="Weapon 1" --budget=50
```

## Key Features
- Preserves all existing loadouts
- Matches template loadout's slot/config structure exactly
- Validates passive hashes against actual tree data
- Handles cluster jewel nodes (hashes_ex)
- Converts mastery effects
- Full .build <-> JSON roundtrip via `pob_collab.py`

## Testing

### Mocking Passive Converter
The `convert_passive_hashes()` function calls headless PoB (`luajit HeadlessWrapper.lua`) which requires the PoB repo and LuaJIT. For unit tests, mock it:

```python
import pob_add_character_loadout as pcl
original = pcl.convert_passive_hashes

def mock_convert(hashes, tree_version="3_29", class_id=1, ascendancy_id=2):
    return {
        "validNodes": [1, 2, 3],
        "clusterNodes": [4],
        "missingNodes": [],
        "totalValid": 3,
        "totalCluster": 1,
        "totalMissing": 0,
        "totalInput": 4
    }

pcl.convert_passive_hashes = mock_convert
try:
    # Run test that calls add_character_loadout()
    new_build = add_character_loadout(build, character, "Test")
    # Tree spec will be added with mocked data
finally:
    pcl.convert_passive_hashes = original
```

### Test Build Fixture
Use a minimal build structure for testing loadout addition:
```python
build = {
    "Skills": {"SkillSet": [{"_attr": {"id": "1", "title": "Default"}}]},
    "Items": {
        "Item": [],
        "ItemSet": [{
            "_attr": {"id": "1", "title": "Default"},
            "Slot": [
                {"_attr": {"name": "Weapon 1", "itemId": "0"}},
                {"_attr": {"name": "Helmet", "itemId": "0"}},
                {"_attr": {"name": "Body Armour", "itemId": "0"}}
            ]
        }]
    },
    "Config": {
        "ConfigSet": [{
            "_attr": {"id": "1", "title": "Default"},
            "Input": [
                {"_attr": {"name": "pantheonMajorGod", "string": "Lunaris"}},
                {"_attr": {"name": "bandit", "string": "None"}}
            ],
            "Placeholder": [{"_attr": {"name": "enemyColdResist", "number": "50"}}]
        }]
    },
    "Tree": {"Spec": [{"_attr": {"id": "1", "title": "Default"}}]}
}
```

### Test Coverage
The test suite (`test_pob_pipeline.py`) validates:
- OAuth PKCE generation, authorization URL, state
- Passive hash conversion (valid, cluster, missing)
- Class/ascendancy ID mapping
- Character loadout: full addition, item conversion, slot assignment, skill extraction
- Trade query: stat weights, query building, Earthshatter query, URL generation
- Stash/Currency: currency mapping, rates, net worth, item parsing
- Target Build Store: CRUD, duplication, import/export, item management
- Templates: God Tier and Budget Earthshatter
- Dashboard JS functions
- Full pipeline data flow

Run tests:
```bash
cd /Users/joecrawford/.hermes/profiles/bot-of-exile/scripts
python3 test_pob_pipeline.py -v
```