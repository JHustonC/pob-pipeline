#!/usr/bin/env python3
"""
PoB Passive Hash Converter - Python Wrapper
============================================
Uses headless PoB (luajit HeadlessWrapper.lua) to convert GGG API passive hashes
to validated PoB node IDs.
"""

import os
import json
import subprocess
from typing import List, Dict, Optional


# Path to PoB repo
POB_REPO = "/Users/joecrawford/pob_repo"
HEADLESS_WRAPPER = os.path.join(POB_REPO, "src", "HeadlessWrapper.lua")
CONVERTER_SCRIPT = os.path.join(POB_REPO, "passive_converter_post.lua")

# Lua paths
LUA_PATH = os.path.join(POB_REPO, "src") + "/?.lua;" + \
           os.path.join(POB_REPO, "src") + "/?/init.lua;" + \
           os.path.join(POB_REPO, "runtime/lua") + "/?.lua;" + \
           os.path.join(POB_REPO, "runtime/lua") + "/?/init.lua;;"
LUA_CPATH = os.path.join(POB_REPO, "runtime") + "/?.dll;;"


def convert_passive_hashes(
    hashes: List[int],
    tree_version: str = "3_29",
    class_id: int = 1,
    ascendancy_id: int = 2
) -> Dict:
    """
    Convert GGG API passive hashes to validated PoB node IDs using headless PoB.
    
    Args:
        hashes: List of passive hashes from GGG API (passives.hashes + passives.hashes_ex)
        tree_version: PoB tree version (e.g., "3_29")
        class_id: Class ID (0=Scion, 1=Marauder, 2=Ranger, 3=Witch, 4=Duelist, 5=Templar, 6=Shadow)
        ascendancy_id: Ascendancy ID within the class
    
    Returns:
        Dict with:
        - validNodes: List of hashes that exist in the tree
        - clusterNodes: List of hashes that are cluster jewel nodes (>= 65536)
        - missingNodes: List of hashes not found in tree
        - totalValid, totalCluster, totalMissing counts
    """
    if not hashes:
        return {
            "validNodes": [],
            "clusterNodes": [],
            "missingNodes": [],
            "totalValid": 0,
            "totalCluster": 0,
            "totalMissing": 0,
            "totalInput": 0
        }
    
    # Prepare hash list string
    hash_list_str = ",".join(str(h) for h in hashes)
    
    # Environment variables for the converter
    env = os.environ.copy()
    env["POB_CONVERTER_SCRIPT"] = CONVERTER_SCRIPT
    env["POB_CONVERTER_ARG1"] = tree_version
    env["POB_CONVERTER_ARG2"] = str(class_id)
    env["POB_CONVERTER_ARG3"] = str(ascendancy_id)
    env["POB_CONVERTER_ARG4"] = hash_list_str
    env["LUA_PATH"] = LUA_PATH
    env["LUA_CPATH"] = LUA_CPATH
    
    # Run headless wrapper
    cmd = ["luajit", HEADLESS_WRAPPER]
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            cwd=os.path.join(POB_REPO, "src"),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Parse JSON output (last line should be the JSON)
        output_lines = result.stdout.strip().split('\n')
        json_line = None
        for line in reversed(output_lines):
            line = line.strip()
            if line.startswith('{'):
                json_line = line
                break
        
        if not json_line:
            raise ValueError(f"No JSON output found. Stdout: {result.stdout}\nStderr: {result.stderr}")
        
        data = json.loads(json_line)
        
        if "error" in data:
            raise ValueError(f"Converter error: {data['error']}")
        
        return data
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("Headless PoB conversion timed out")
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse converter output: {e}\nOutput: {result.stdout}")


def get_class_id(class_name: str) -> int:
    """Map class name to PoB class ID."""
    class_map = {
        "Scion": 0,
        "Marauder": 1,
        "Ranger": 2,
        "Witch": 3,
        "Duelist": 4,
        "Templar": 5,
        "Shadow": 6,
    }
    return class_map.get(class_name, 1)


def get_ascendancy_id(class_name: str, ascendancy_name: str) -> int:
    """Map ascendancy name to PoB ascendancy ID within class."""
    # This is simplified - actual mapping depends on class
    # For Marauder: 1=Juggernaut, 2=Berserker, 3=Chieftain
    ascendancy_map = {
        "Marauder": {"Juggernaut": 1, "Berserker": 2, "Chieftain": 3},
        "Ranger": {"Deadeye": 1, "Raider": 2, "Pathfinder": 3},
        "Witch": {"Necromancer": 1, "Occultist": 2, "Elementalist": 3},
        "Duelist": {"Slayer": 1, "Gladiator": 2, "Champion": 3},
        "Templar": {"Inquisitor": 1, "Hierophant": 2, "Guardian": 3},
        "Shadow": {"Assassin": 1, "Saboteur": 2, "Trickster": 3},
        "Scion": {"Ascendant": 1},
    }
    class_asc = ascendancy_map.get(class_name, {})
    return class_asc.get(ascendancy_name, 1)


# ============================================================
# Example Usage
# ============================================================

if __name__ == "__main__":
    # Test with Earthshatter Berserker passive hashes
    test_hashes = [
        9471, 5197, 13922, 487, 1909, 48199, 64587, 7162, 6289, 24716,
        47175, 50340, 57953, 25682, 38777, 14767, 49318, 65107, 42861,
        36200, 24914, 34400
    ]
    
    print(f"Converting {len(test_hashes)} passive hashes...")
    result = convert_passive_hashes(
        test_hashes,
        tree_version="3_29",
        class_id=1,  # Marauder
        ascendancy_id=2  # Berserker
    )
    
    print(f"Valid nodes: {result['totalValid']}")
    print(f"Cluster nodes: {result['totalCluster']}")
    print(f"Missing nodes: {result['totalMissing']}")
    print(f"Valid: {result['validNodes']}")
    print(f"Missing: {result['missingNodes']}")
    print(f"Cluster: {result['clusterNodes']}")