---
name: pob-character-import
category: reverse-engineer-anything
description: Import PoE characters into PoB via OAuth or public API
version: 1.0.0
author: bot-of-exile
license: MIT
metadata:
  hermes:
    tags: [pob, path-of-building, path-of-exile, character-import, api]
    related_skills: [pobb-in-build-extraction]
---
## When to Use
- Import a live PoE character into Path of Building
- Understand the two import methods: OAuth (authenticated) vs Public API (account name)
- Build tooling that fetches character data programmatically

## Two Import Methods

### Method 1: OAuth API (Authenticated, Full Access)
**Requires**: User authorizes PoB via OAuth2 (PoE website)
**Scopes**: `account:characters`, `account:profile`, `account:leagues`, `account:trade`
**Endpoints**:
```
GET https://api.pathofexile.com/character          # List characters
GET https://api.pathofexile.com/character/{name}   # Full character (passives + items + equipment)
```
**Realms**: PC (default), `xbox`, `sony`, `poe2`
**Returns**: Complete character object with passives, equipment, inventory, jewels, guardian, etc.

### Method 2: Public Character Window API (No Auth, Public Profiles Only)
**Requires**: Account name with discriminator (e.g., `MyAccount#1234`)
**Profile must be public** (private profiles return 401/403)
**Endpoints**:
```
GET https://www.pathofexile.com/character-window/get-characters?accountName={name}&realm={realm}
GET https://www.pathofexile.com/character-window/get-passive-skills?accountName={name}&character={char}&realm={realm}
GET https://www.pathofexile.com/character-window/get-items?accountName={name}&character={char}&realm={realm}
```
**Realms**: `pc`, `xbox`, `sony`
**Note**: Separate calls for character list, passive tree, and items/skills
**Account name case sensitivity**: `/get-characters` is case-insensitive, but `/get-passive-skills` and `/get-items` ARE case-sensitive. PoB works around this by fetching the profile page to get the canonical account name.

## API Response Structures

### OAuth `/character/{name}` Response
```json
{
  "character": {
    "name": "CharacterName",
    "class": "Marauder",
    "level": 100,
    "league": "Settlers",
    "passives": {
      "hashes": [12345, 67890],
      "hashes_ex": [11111],
      "skill_overrides": {},
      "mastery_effects": [[nodeHash, effectHash]]
    },
    "equipment": [{"id": "Metadata/Items/...", "properties": [...], "sockets": [...]}],
    "inventory": [...],
    "jewels": [...],
    "guardian": [...],
    "bandit_choice": "Kill All",
    "pantheon_major": "Lunaris",
    "pantheon_minor": "Tukohama"
  }
}
```

### Public `get-passive-skills` Response
```json
{
  "hashes": [12345, 67890],
  "hashes_ex": [11111],
  "skill_overrides": {},
  "mastery_effects": [[nodeHash, effectHash]],
  "bandit_choice": "Kill All",
  "pantheon_major": "Lunaris",
  "pantheon_minor": "Tukohama",
  "items": [{"id": "Metadata/Items/Jewels/...", "properties": [...]}]
}
```

### Public `get-items` Response
```json
{
  "items": [
    {"inventoryId": "Helmet", "id": "Metadata/Items/Helmets/...", "properties": [...], "sockets": [...]}
  ],
  "guardian": [{"id": "Metadata/Items/...", "properties": [...]}]
}
```

## Validated Working Implementation (pob_oauth_import.py)
```python
from pob_oauth_import import run_oauth_flow, PoEAPIClient, load_tokens, save_tokens

# 1. Try saved tokens first, then run OAuth flow
client = load_tokens()
if not client:
    client = run_oauth_flow()  # Opens browser, local server on ports 49082-49084 (60s timeout)
    save_tokens(client)

# 2. Fetch character (full data: passives, equipment, inventory, jewels, guardian, bandit, pantheon)
character = client.get_character("MyCharacter")
if not character:
    raise ValueError("Character not found or private profile")

# 3. Key character data structure
character_data = {
    "name": character["name"],
    "class": character["class"],
    "ascendancy": character.get("ascendancy", ""),
    "level": character["level"],
    "league": character.get("league", ""),
    "passives": {
        "hashes": character["passives"].get("hashes", []),
        "hashes_ex": character["passives"].get("hashes_ex", []),
        "mastery_effects": character["passives"].get("mastery_effects", []),
    },
    "equipment": character.get("equipment", []),
    "inventory": character.get("inventory", []),
    "jewels": character.get("jewels", []),
    "guardian": character.get("guardian", []),
    "bandit_choice": character.get("bandit_choice", "None"),
    "pantheon_major": character.get("pantheon_major", ""),
    "pantheon_minor": character.get("pantheon_minor", ""),
}
```

### Validated Working Commands
```bash
# First run - OAuth flow
python3 pob_oauth_import.py

# Subsequent runs - uses saved tokens (auto-refreshes)
python3 pob_oauth_import.py
```

### Validated OAuth Flow (Matches PoB Exactly)
| Step | Description | PoB Source |
|------|-------------|------------|
| 1. PKCE Generation | `code_verifier` (base64url) + `code_challenge` (S256) | `PoEAPI.lua:95-97` |
| 2. State | 16-char hex CSRF token | `PoEAPI.lua:100-102` |
| 3. Auth URL | `client_id=pob`, scopes: `account:characters account:profile account:leagues account:trade` | `PoEAPI.lua:104-109` |
| 4. Local Server | Ports 49082-49084, 60s timeout | `LaunchServer.lua` |
| 5. Code Exchange | POST `/oauth/token` with `code_verifier` | `PoEAPI.lua:131-150` |
| 6. Token Storage | `access_token`, `refresh_token`, `expiry` | `PoEAPI.lua:142-146` |
| 7. Auto-refresh | On 401, use refresh token once | `PoEAPI.lua:158-172` |

### Validated API Endpoints
```python
# OAuth (authenticated)
GET https://api.pathofexile.com/character          # List characters
GET https://api.pathofexile.com/character/{name}   # Full character data

# Public (no auth, public profiles only)
GET https://www.pathofexile.com/character-window/get-characters?accountName={name}&realm={realm}
GET https://www.pathofexile.com/character-window/get-passive-skills?accountName={name}&character={char}&realm={realm}
GET https://www.pathofexile.com/character-window/get-items?accountName={name}&character={char}&realm={realm}
```

### Rate Limits (Validated)
- OAuth API: ~120 req/min (character list), ~60 req/min (character detail)
- Public API: Stricter, not officially documented
- Use exponential backoff on 429

### Validated Working Example
```bash
# Full OAuth + character fetch
python3 -c "
from pob_oauth_import import run_oauth_flow
client = run_oauth_flow()
char = client.get_character('MyCharacter')
print(f'Character: {char[\"name\"]} Lv{char[\"level\"]} {char[\"class\"]}')
"
```