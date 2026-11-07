#!/usr/bin/env bash
# pob-pipeline-package.sh
# Creates a portable package of the entire PoB pipeline

set -euo pipefail

PACKAGE_NAME="pob-pipeline-$(date +%Y%m%d-%H%M%S)"
SOURCE_PROFILE="$HOME/.hermes/profiles/bot-of-exile"
POB_REPO="/Users/joecrawford/pob_repo"
OUTPUT_DIR="$HOME/pob-pipeline-packages"

echo "📦 Creating PoB Pipeline Package: $PACKAGE_NAME"
echo "=============================================="

mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

# Create package directory
PACKAGE_DIR="$OUTPUT_DIR/$PACKAGE_NAME"
mkdir -p "$PACKAGE_DIR"

# 1. Copy Hermes profile (skills, scripts, memories)
echo "📁 Copying Hermes profile..."
rsync -av --exclude='cache' --exclude='*.log' \
    "$SOURCE_PROFILE/" "$PACKAGE_DIR/hermes-profile/"

# 2. Copy PoB repo (just src and runtime, not .git)
echo "📁 Copying PoB repo (src + runtime)..."
mkdir -p "$PACKAGE_DIR/pob_repo"
rsync -av --exclude='.git' --exclude='*.log' --exclude='build' \
    "$POB_REPO/src/" "$PACKAGE_DIR/pob_repo/src/"
rsync -av --exclude='.git' \
    "$POB_REPO/runtime/" "$PACKAGE_DIR/pob_repo/runtime/" 2>/dev/null || true

# 3. Copy Exile-UI data (download if needed)
echo "📁 Setting up Exile-UI data..."
mkdir -p "$PACKAGE_DIR/exile_ui_data/english"
mkdir -p "$PACKAGE_DIR/exile_ui_data/global"

# Download latest Exile-UI data files
BASE_URL="https://raw.githubusercontent.com/Lailloken/Exile-UI/main/data"
for file in \
    "english/[leveltracker] areas.json" \
    "english/[leveltracker] gems.json" \
    "english/[leveltracker] default guide.json" \
    "english/[leveltracker] default guide 2.json" \
    "english/client.txt" \
    "global/[leveltracker] tree 3_29.json" \
    "global/[leveltracker] tree 3_28.json"; do
    
    url_encoded=$(echo "$file" | sed 's/ /%20/g; s/\[/%5B/g; s/\]/%5D/g')
    dest="$PACKAGE_DIR/exile_ui_data/$file"
    mkdir -p "$(dirname "$dest")"
    
    echo "  Downloading: $file"
    curl -sL "$BASE_URL/$url_encoded" -o "$dest" || echo "  ⚠️  Failed: $file"
done

# 4. Create installer script
cat > "$PACKAGE_DIR/install.sh" << 'INSTALL_EOF'
#!/usr/bin/env bash
# pob-pipeline-install.sh
# Installs the PoB pipeline package on a new machine

set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_PROFILE="$HOME/.hermes/profiles/bot-of-exile"
POB_REPO_TARGET="/Users/joecrawford/pob_repo"

echo "🔧 Installing PoB Pipeline Package"
echo "=================================="

# 1. Install Hermes profile
echo "📁 Installing Hermes profile..."
mkdir -p "$TARGET_PROFILE"
rsync -av "$PACKAGE_DIR/hermes-profile/" "$TARGET_PROFILE/"

# 2. Install PoB repo
echo "📁 Installing PoB repo..."
mkdir -p "$POB_REPO_TARGET"
rsync -av "$PACKAGE_DIR/pob_repo/src/" "$POB_REPO_TARGET/src/"
rsync -av "$PACKAGE_DIR/pob_repo/runtime/" "$POB_REPO_TARGET/runtime/" 2>/dev/null || true

# 3. Install Exile-UI data
echo "📁 Installing Exile-UI data..."
EXILE_UI_DATA="$HOME/.hermes/profiles/bot-of-exile/scripts/exile_ui_data"
mkdir -p "$EXILE_UI_DATA"
rsync -av "$PACKAGE_DIR/exile_ui_data/" "$EXILE_UI_DATA/"

# 4. Verify LuaJIT
echo "🔍 Checking LuaJIT..."
if ! command -v luajit &> /dev/null; then
    echo "⚠️  LuaJIT not found. Install with: brew install luajit"
else
    echo "  ✅ LuaJIT: $(luajit -v 2>&1 | head -1)"
fi

# 5. Verify Python deps
echo "🔍 Checking Python dependencies..."
python3 -c "import requests, json, pathlib, dataclasses, subprocess, threading" 2>/dev/null && echo "  ✅ Core modules OK" || echo "  ⚠️  Some modules missing"

# 6. Run tests
echo "🧪 Running tests..."
cd "$TARGET_PROFILE/scripts"
python3 test_pob_pipeline.py 2>&1 | tail -10

echo ""
echo "✅ Installation complete!"
echo ""
echo "📋 Next steps:"
echo "  1. cd $TARGET_PROFILE/scripts"
echo "  2. python3 pob_update_manager.py init"
echo "  3. python3 pob_leveling.py --build earthshatter_berserker_god_tier"
echo "  4. Open pob_leveling_dashboard.html in browser"
echo ""
echo "📁 PoE log path (adjust if needed):"
echo "   ~/Documents/My Games/Path of Exile/logs/client.txt"

INSTALL_EOF

chmod +x "$PACKAGE_DIR/install.sh"

# 5. Create quick-start README
cat > "$PACKAGE_DIR/README.md" << 'README_EOF'
# PoB Pipeline Package

Portable Path of Building automation pipeline with leveling assistant.

## Quick Start

```bash
# 1. Run installer
./install.sh

# 2. Initialize update manager
cd ~/.hermes/profiles/bot-of-exile/scripts
python3 pob_update_manager.py init

# 3. Start leveling tracker
python3 pob_leveling.py --build earthshatter_berserker_god_tier --league Settlers

# 4. Open dashboard
open pob_leveling_dashboard.html
```

## What's Included

| Component | Description |
|-----------|-------------|
| `hermes-profile/` | Skills, scripts, memories, cron |
| `pob_repo/src/` | PoB Lua source (for headless) |
| `pob_repo/runtime/` | LuaJIT runtime libs |
| `exile_ui_data/` | Leveling data (areas, gems, guide, tree) |
| `install.sh` | One-command installer |

## Key Scripts

| Script | Purpose |
|--------|---------|
| `pob_leveling.py` | Chat log parser → zone, level, gems, passive tree |
| `pob_update_manager.py` | PoB repo updates + breaking change detection |
| `pob_target_build_store.py` | Target build CRUD (god_tier, budget, etc.) |
| `pob_oauth_import.py` | OAuth → character import → loadout |
| `pob_pipeline_dashboard.html` | Endgame upgrade dashboard |
| `pob_leveling_dashboard.html` | Leveling assistant UI |
| `test_pob_pipeline.py` | 52 unit tests |

## Requirements

- **macOS** (paths assume macOS; adjust for Linux/Windows)
- **LuaJIT**: `brew install luajit`
- **Python 3.9+**: requests, stdlib only
- **PoE log**: `~/Documents/My Games/Path of Exile/logs/client.txt`

## Directory Structure After Install

```
~/.hermes/profiles/bot-of-exile/
├── skills/              # pob-update-manager, pob-leveling-page, etc.
├── scripts/
│   ├── pob_*.py         # All pipeline scripts
│   ├── *_dashboard.html # Web UIs
│   ├── test_pob_pipeline.py
│   └── exile_ui_data/   # Downloaded Exile-UI data
└── memories/            # Persistent memory

/Users/joecrawford/pob_repo/
├── src/                 # PoB Lua source
└── runtime/             # LuaJIT libs
```

## Configuration

Edit `~/.hermes/profiles/bot-of-exile/scripts/pob_leveling.py`:
```python
DEFAULT_LOG_PATH = Path.home() / "Documents/My Games/Path of Exile/logs/client.txt"
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `luajit: not found` | `brew install luajit` |
| `ModuleNotFoundError` | `pip3 install requests` |
| Log not found | Check `~/Documents/My Games/Path of Exile/logs/client.txt` exists |
| Tests fail | Run `python3 pob_update_manager.py check` |

## Updating

```bash
# Check for PoB updates
python3 pob_update_manager.py check

# Full update (pull + migrate + test)
python3 pob_update_manager.py update
```

README_EOF

# 6. Create archive
echo "📦 Creating archive..."
cd "$OUTPUT_DIR"
tar -czf "$PACKAGE_NAME.tar.gz" "$PACKAGE_NAME"
zip -rq "$PACKAGE_NAME.zip" "$PACKAGE_NAME"

# 7. Show summary
echo ""
echo "✅ Package created: $OUTPUT_DIR/$PACKAGE_NAME"
echo ""
echo "📊 Contents:"
du -sh "$PACKAGE_DIR"/*
echo ""
echo "📦 Archives:"
ls -lh "$OUTPUT_DIR/$PACKAGE_NAME.tar.gz" "$OUTPUT_DIR/$PACKAGE_NAME.zip"
echo ""
echo "🚀 To deploy on another machine:"
echo "   1. Copy $PACKAGE_NAME.tar.gz (or .zip)"
echo "   2. tar -xzf $PACKAGE_NAME.tar.gz"
echo "   3. cd $PACKAGE_NAME && ./install.sh"

README_EOF