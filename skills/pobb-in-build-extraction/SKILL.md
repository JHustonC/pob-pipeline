---
name: pobb-in-build-extraction
category: reverse-engineer-anything
description: Extract PoB build from pobb.in via base64url+zlib decode
version: 1.0.0
author: bot-of-exile
license: MIT
metadata:
  hermes:
    tags: [pob, path-of-building, pobb.in, build-extraction, reverse-engineering]
    related_skills: []
---
## When to Use
- You have a pobb.in share link (e.g., `https://pobb.in/XXXXXX`) and need the raw `.build` XML
- You want to import a community build into Path of Building for analysis/modification
- You need to convert a pobb.in build to JSON for agent collaboration via `pob_collab.py`

## The Problem
pobb.in share links serve HTML with the buildcode embedded in a readonly input: `aria-label="Path of Building buildcode"`.

## Extraction Method

### 1. Fetch HTML
```python
import requests
html = requests.get("https://pobb.in/YFaTC_ulBFvf").text
```

### 2. Extract buildcode (regex for `eNrt...` pattern)
```python
import re
match = re.search(r'eNrt[A-Za-z0-9+/=_-]{100,}', html)
buildcode = match.group()  # base64url encoded
```

### 3. Decode: base64url → base64 → zlib
```python
import base64, zlib

buildcode_std = buildcode.replace('-', '+').replace('_', '/')
padding = 4 - (len(buildcode_std) % 4)
if padding != 4:
    buildcode_std += '=' * padding

decoded = base64.b64decode(buildcode_std)
xml = zlib.decompress(decoded)  # PoB .build XML
```

### 4. Save & export to JSON
```python
with open('build.build', 'wb') as f:
    f.write(xml)

from pob_collab import export_build
export_build('build.build', 'build.json')
```

## Validated Working Function
```python
def extract_pobb_build(pobb_url, out_build, out_json):
    """Extract PoB build from pobb.in link to .build + JSON."""
    import requests, re, base64, zlib
    html = requests.get(pobb_url).text
    match = re.search(r'eNrt[A-Za-z0-9+/=_-]{100,}', html)
    if not match:
        raise ValueError("Buildcode not found in pobb.in page")
    buildcode = match.group()
    buildcode_std = buildcode.replace('-', '+').replace('_', '/')
    padding = 4 - (len(buildcode_std) % 4)
    if padding != 4:
        buildcode_std += '=' * padding
    xml = zlib.decompress(base64.b64decode(buildcode_std))
    with open(out_build, 'wb') as f:
        f.write(xml)
    from pob_collab import export_build
    export_build(out_build, out_json)
    return xml

# Usage
extract_pobb_build(
    "https://pobb.in/YFaTC_ulBFvf",
    "/tmp/earthshatter_berserker.build",
    "/tmp/earthshatter_berserker.json"
)
```

### Validated Key Points
- **Prefix `eNrt`** = zlib compressed (standard PoB)
- **base64url** uses `-` `_` instead of `+` `/`
- **Padding** required before `base64.b64decode()`
- **zlib.decompress()** works directly (no `-zlib.MAX_WBITS` needed)
- Output is valid PoB `.build` XML
- Roundtrip: `.build` → JSON (via `pob_collab.export_build`) → `.build` (via `pob_collab.import_build`) works perfectly

### Validated Working Commands
```bash
# Extract from pobb.in
python3 -c "
import requests, re, base64, zlib
html = requests.get('https://pobb.in/YFaTC_ulBFvf').text
match = re.search(r'eNrt[A-Za-z0-9+/=_-]{100,}', html)
buildcode = match.group().replace('-', '+').replace('_', '/')
buildcode += '=' * (4 - len(buildcode) % 4)
xml = zlib.decompress(base64.b64decode(buildcode))
open('/tmp/build.build', 'wb').write(xml)
"

# Export to JSON
cd /Users/joecrawford/pob_repo && python3 -c "from pob_collab import export_build; export_build('/tmp/build.build', '/tmp/build.json')"
```