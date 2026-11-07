#!/usr/bin/env python3
"""
PoB Update Manager
==================
Tracks PoB repo updates, detects breaking changes, runs tests, and provides migration guides.
"""

import json
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
import hashlib

# ============================================================
# Configuration
# ============================================================

CONFIG_PATH = Path.home() / ".pob_pipeline" / "update_manager.json"
POB_REPO = Path("/Users/joecrawford/pob_repo")
SCRIPTS_DIR = Path("/Users/joecrawford/.hermes/profiles/bot-of-exile/scripts")
TEST_FILE = SCRIPTS_DIR / "test_pob_pipeline.py"

# Files that indicate breaking changes when modified
BREAKING_FILES = {
    "src/Tree/PassiveTree.lua": "tree_version",
    "src/Classes/TradeQueryGenerator.lua": "trade_query",
    "src/Classes/Item.lua": "item_bases",
    "src/Classes/Skill.lua": "skill_gems",
    "src/Classes/Build.lua": "build_structure",
    "src/Classes/CharacterClass.lua": "class_ascendancy",
    "src/ModParser.lua": "mod_parsing",
    "src/HeadlessWrapper.lua": "headless_api",
}

MIGRATION_GUIDES = {
    "tree_version": {
        "title": "Tree Version Bump",
        "steps": [
            "Check new tree version in PassiveTree.lua (e.g., 3_30)",
            "Update `tree_version` in pob_passive_converter.py",
            "Re-run passive hash validation for all target builds",
            "Update any hardcoded tree versions in test fixtures",
        ],
        "files_to_update": [
            "pob_passive_converter.py",
            "pob_add_character_loadout.py",
            "test_pob_pipeline.py",
        ]
    },
    "class_ascendancy": {
        "title": "New Class/Ascendancy Added",
        "steps": [
            "Check CharacterClass.lua for new class/ascendancy IDs",
            "Add mappings to get_class_id() and get_ascendancy_id() in pob_passive_converter.py",
            "Update target build templates if new ascendancy relevant",
        ],
        "files_to_update": [
            "pob_passive_converter.py",
            "pob_target_build_store.py",
        ]
    },
    "trade_query": {
        "title": "Trade Query Generator Changes",
        "steps": [
            "Diff TradeQueryGenerator.lua against pob_trade_query_generator.py",
            "Sync stat weight mappings, category mappings, price limits",
            "Run test_create_earthshatter_berserker_query to validate",
        ],
        "files_to_update": [
            "pob_trade_query_generator.py",
            "test_pob_pipeline.py",
        ]
    },
    "item_bases": {
        "title": "Item Base/Mod Changes",
        "steps": [
            "Check Item.lua and Mods.dat for new bases, influences, mod pools",
            "Update target build templates with new bases",
            "Verify crafting guides still reference valid bases",
        ],
        "files_to_update": [
            "pob_target_build_store.py",
            "pob_crafting_guide_finder.py (if exists)",
        ]
    },
    "headless_api": {
        "title": "HeadlessWrapper API Changes",
        "steps": [
            "Check HeadlessWrapper.lua for new env vars or output format",
            "Update pob_passive_converter.py env var handling",
            "Test passive converter end-to-end",
        ],
        "files_to_update": [
            "pob_passive_converter.py",
            "HeadlessWrapper.lua (in pob_repo)",
        ]
    },
    "build_structure": {
        "title": "Build JSON Structure Changes",
        "steps": [
            "Check Build.lua for SkillSet/ItemSet/ConfigSet/Tree changes",
            "Update pob_add_character_loadout.py loadout creation",
            "Update pob_collab.py export/import if needed",
            "Run full test suite",
        ],
        "files_to_update": [
            "pob_add_character_loadout.py",
            "pob_collab.py",
            "test_pob_pipeline.py",
        ]
    },
    "mod_parsing": {
        "title": "Mod Parsing Rule Changes",
        "steps": [
            "Check ModParser.lua for new mod types, parsing rules",
            "Verify trade query stat weights still map correctly",
            "Test with known items",
        ],
        "files_to_update": [
            "pob_trade_query_generator.py",
        ]
    },
    "skill_gems": {
        "title": "Skill Gem Changes",
        "steps": [
            "Check Skill.lua for new gems, tags, stats",
            "Update skill extraction in pob_add_character_loadout.py",
            "Verify Earthshatter/Perforate configs still work",
        ],
        "files_to_update": [
            "pob_add_character_loadout.py",
            "pob_target_build_store.py",
        ]
    },
}

# ============================================================
# Data Classes
# ============================================================

@dataclass
class UpdateConfig:
    pob_repo: str = str(POB_REPO)
    last_known_commit: str = ""
    last_tree_version: str = "3_29"
    last_test_run: str = ""
    last_test_result: str = ""
    tracked_configs: List[str] = None
    
    def __post_init__(self):
        if self.tracked_configs is None:
            self.tracked_configs = [
                "~/.pob_pipeline/target_builds.json",
                "~/.pob_pipeline/poe_tokens.json",
            ]

# ============================================================
# Core Functions
# ============================================================

def load_config() -> UpdateConfig:
    """Load update manager config."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        return UpdateConfig(**data)
    return UpdateConfig()

def save_config(config: UpdateConfig):
    """Save update manager config."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(asdict(config), f, indent=2)

def get_current_commit() -> str:
    """Get current PoB repo commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=POB_REPO,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""

def get_tree_version() -> str:
    """Extract tree version from PassiveTree.lua."""
    try:
        tree_file = POB_REPO / "src" / "Tree" / "PassiveTree.lua"
        if tree_file.exists():
            content = tree_file.read_text()
            # Look for tree version pattern
            import re
            match = re.search(r'tree_version\s*=\s*["\'](\d+_\d+)["\']', content)
            if match:
                return match.group(1)
            match = re.search(r'["\'](\d+_\d+)["\']\s*--\s*tree version', content)
            if match:
                return match.group(1)
    except Exception:
        pass
    return "3_29"

def get_changed_files(since_commit: str) -> List[str]:
    """Get files changed since last known commit."""
    if not since_commit:
        return []
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", since_commit, "HEAD"],
            cwd=POB_REPO,
            capture_output=True,
            text=True,
            check=True
        )
        return [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
    except subprocess.CalledProcessError:
        return []

def detect_breaking_changes(changed_files: List[str]) -> Dict[str, List[str]]:
    """Detect which breaking change categories are affected."""
    detected = {}
    for file in changed_files:
        for pattern, category in BREAKING_FILES.items():
            if file.startswith(pattern.rsplit('/', 1)[0]) or file == pattern:
                if category not in detected:
                    detected[category] = []
                detected[category].append(file)
    return detected

def run_tests() -> tuple[bool, str]:
    """Run the test suite."""
    try:
        result = subprocess.run(
            [sys.executable, str(TEST_FILE)],
            cwd=SCRIPTS_DIR,
            capture_output=True,
            text=True,
            timeout=120
        )
        output = result.stdout + result.stderr
        passed = result.returncode == 0
        return passed, output
    except subprocess.TimeoutExpired:
        return False, "Tests timed out after 120s"
    except Exception as e:
        return False, f"Test execution failed: {e}"

def generate_migration_guide(detected: Dict[str, List[str]]) -> str:
    """Generate migration guide for detected changes."""
    if not detected:
        return "No breaking changes detected. Safe to update."
    
    lines = ["# Migration Guide\n"]
    lines.append(f"Detected {len(detected)} breaking change category(ies):\n")
    
    for category, files in detected.items():
        if category in MIGRATION_GUIDES:
            guide = MIGRATION_GUIDES[category]
            lines.append(f"## {guide['title']}")
            lines.append(f"Affected files: {', '.join(files)}\n")
            for i, step in enumerate(guide['steps'], 1):
                lines.append(f"{i}. {step}")
            lines.append(f"\n**Files to update:** {', '.join(guide['files_to_update'])}\n")
        else:
            lines.append(f"## {category.replace('_', ' ').title()}")
            lines.append(f"Affected files: {', '.join(files)}")
            lines.append("No automated guide available. Manual review required.\n")
    
    return "\n".join(lines)

def check_command() -> int:
    """Check for updates and validate."""
    print("🔍 PoB Update Manager - Check Mode")
    print("=" * 50)
    
    config = load_config()
    current_commit = get_current_commit()
    current_tree = get_tree_version()
    
    print(f"PoB Repo: {POB_REPO}")
    print(f"Current Commit: {current_commit[:8]}")
    print(f"Last Known Commit: {config.last_known_commit[:8] if config.last_known_commit else 'None'}")
    print(f"Current Tree Version: {current_tree}")
    print(f"Last Tree Version: {config.last_tree_version}")
    print()
    
    # Check for changes
    if config.last_known_commit and config.last_known_commit != current_commit:
        print("📝 Changes detected since last run")
        changed = get_changed_files(config.last_known_commit)
        print(f"  {len(changed)} file(s) changed")
        
        breaking = detect_breaking_changes(changed)
        if breaking:
            print(f"  ⚠️  {len(breaking)} breaking change category(ies) detected:")
            for cat, files in breaking.items():
                print(f"    - {cat}: {', '.join(files)}")
        else:
            print("  ✅ No breaking changes detected")
    else:
        print("✅ No new commits since last check")
        breaking = {}
    
    # Run tests
    print("\n🧪 Running test suite...")
    passed, output = run_tests()
    if passed:
        print("  ✅ All tests passed")
    else:
        print("  ❌ Tests failed")
        # Show last 20 lines
        for line in output.strip().split('\n')[-20:]:
            print(f"    {line}")
    
    # Show migration guide if needed
    if breaking:
        print("\n" + "=" * 50)
        print(generate_migration_guide(breaking))
    
    # Summary
    print("\n" + "=" * 50)
    if config.last_known_commit != current_commit:
        if breaking and not passed:
            print("⚠️  ACTION REQUIRED: Breaking changes + test failures")
            return 2
        elif breaking:
            print("⚠️  REVIEW NEEDED: Breaking changes detected (tests pass)")
            return 1
        elif not passed:
            print("❌ TESTS FAIL: No breaking changes but tests fail")
            return 2
        else:
            print("✅ SAFE TO UPDATE: No breaking changes, tests pass")
            return 0
    else:
        if not passed:
            print("❌ TESTS FAIL: Existing code has issues")
            return 2
        print("✅ UP TO DATE: No changes, tests pass")
        return 0

def update_command() -> int:
    """Full update with migration."""
    print("🔄 PoB Update Manager - Update Mode")
    print("=" * 50)
    
    config = load_config()
    
    # Pull latest
    print("📥 Pulling latest PoB changes...")
    try:
        subprocess.run(["git", "pull", "origin", "dev"], cwd=POB_REPO, check=True)
        print("  ✅ Pull complete")
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Pull failed: {e}")
        return 1
    
    # Get new state
    new_commit = get_current_commit()
    new_tree = get_tree_version()
    
    print(f"\nNew Commit: {new_commit[:8]}")
    print(f"New Tree Version: {new_tree}")
    
    # Detect changes
    if config.last_known_commit:
        changed = get_changed_files(config.last_known_commit)
        breaking = detect_breaking_changes(changed)
        
        if breaking:
            print(f"\n⚠️  {len(breaking)} breaking change category(ies) detected:")
            for cat, files in breaking.items():
                print(f"  - {cat}: {', '.join(files)}")
            
            print("\n" + "=" * 50)
            print(generate_migration_guide(breaking))
            
            print("⏸️  Manual migration required before tests can pass.")
            print("Run 'pob_update_manager.py check' after fixing to validate.")
            return 1
    
    # Run tests
    print("\n🧪 Running test suite...")
    passed, output = run_tests()
    if passed:
        print("  ✅ All tests passed")
    else:
        print("  ❌ Tests failed")
        for line in output.strip().split('\n')[-20:]:
            print(f"    {line}")
        return 1
    
    # Update config
    config.last_known_commit = new_commit
    config.last_tree_version = new_tree
    config.last_test_run = datetime.now().isoformat()
    config.last_test_result = "PASS" if passed else "FAIL"
    save_config(config)
    
    print("\n✅ Update complete! Config saved.")
    return 0

def status_command() -> int:
    """Show current status."""
    config = load_config()
    current_commit = get_current_commit()
    current_tree = get_tree_version()
    
    print("📊 PoB Update Manager Status")
    print("=" * 50)
    print(f"PoB Repo: {POB_REPO}")
    print(f"Current Commit: {current_commit[:8]} ({current_commit})")
    print(f"Last Known Commit: {config.last_known_commit[:8] if config.last_known_commit else 'Never'}")
    print(f"Current Tree Version: {current_tree}")
    print(f"Last Tree Version: {config.last_tree_version}")
    print(f"Last Test Run: {config.last_test_run or 'Never'}")
    print(f"Last Test Result: {config.last_test_result or 'N/A'}")
    print(f"\nTracked Configs:")
    for c in config.tracked_configs:
        path = Path(c).expanduser()
        status = "✅" if path.exists() else "❌"
        print(f"  {status} {c}")
    
    # Check if update available
    if config.last_known_commit and config.last_known_commit != current_commit:
        print("\n🔔 Updates available! Run 'check' for details.")
    elif config.last_known_commit == current_commit and config.last_known_commit:
        print("\n✅ Up to date.")
    else:
        print("\n⚠️  First run - no baseline commit recorded.")
    
    return 0

def init_command() -> int:
    """Initialize with current state."""
    config = UpdateConfig()
    config.last_known_commit = get_current_commit()
    config.last_tree_version = get_tree_version()
    config.last_test_run = datetime.now().isoformat()
    save_config(config)
    print("✅ Initialized update manager with current state")
    print(f"  Commit: {config.last_known_commit[:8]}")
    print(f"  Tree: {config.last_tree_version}")
    return 0

# ============================================================
# CLI
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("PoB Update Manager")
        print("Usage: python3 pob_update_manager.py <command>")
        print("\nCommands:")
        print("  init     - Initialize with current PoB state")
        print("  status   - Show current status")
        print("  check    - Check for updates, detect breaks, run tests")
        print("  update   - Pull updates, run migrations, validate")
        return 1
    
    cmd = sys.argv[1]
    
    if cmd == "init":
        return init_command()
    elif cmd == "status":
        return status_command()
    elif cmd == "check":
        return check_command()
    elif cmd == "update":
        return update_command()
    else:
        print(f"Unknown command: {cmd}")
        return 1

if __name__ == "__main__":
    sys.exit(main())