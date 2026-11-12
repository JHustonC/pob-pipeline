#!/usr/bin/env python3
"""
PoB Leveling Tracker
====================
Reads PoE client.txt logs to track zone changes, level ups, quest completions.
Provides real-time gem recommendations, passive tree guidance, Lab trial tracking,
and milestone comparisons against target builds.
"""

import json
import re
import os
import time
import threading
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from collections import deque

# ============================================================
# Configuration
# ============================================================

DEFAULT_LOG_PATH = Path.home() / "Documents" / "My Games" / "Path of Exile" / "logs" / "client.txt"
EXILE_UI_DATA_DIR = Path("/Users/joecrawford/.hermes/profiles/bot-of-exile/scripts/exile_ui_data")

# ============================================================
# Data Classes
# ============================================================

@dataclass
class ZoneInfo:
    """Zone information from Exile-UI areas.json"""
    id: str
    name: str
    level: Optional[int] = None
    map_name: Optional[str] = None
    crafting_recipe: Optional[str] = None
    has_lab_trial: bool = False  # Only on first character in league
    act: int = 0
    connections: List[str] = field(default_factory=list)

@dataclass
class GemInfo:
    """Gem information from Exile-UI gems.json"""
    name: str
    attribute: int  # 0=str, 1=dex, 2=int
    level: int
    quests: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)

@dataclass
class PassiveNode:
    """Passive tree node from Exile-UI tree data"""
    id: str
    name: str
    group: str
    orbit: int
    orbit_index: int
    is_notable: bool = False
    is_keystone: bool = False
    is_mastery: bool = False
    ascendancy_name: Optional[str] = None
    stats: List[str] = field(default_factory=list)
    connections: List[str] = field(default_factory=list)

@dataclass
class LevelingState:
    """Current leveling state"""
    character_name: str = ""
    level: int = 1
    current_zone_id: str = ""
    current_zone_name: str = ""
    current_act: int = 1
    completed_quests: List[str] = field(default_factory=list)
    allocated_passives: List[str] = field(default_factory=list)
    active_gems: List[str] = field(default_factory=list)
    last_update: str = ""
    
    # Guidance
    next_gem: Optional[GemInfo] = None
    next_gems: List[GemInfo] = field(default_factory=list)
    next_passive_node: Optional[PassiveNode] = None
    lab_trial_zone: Optional[str] = None
    milestone_reached: bool = False
    milestone_details: Dict = field(default_factory=dict)

@dataclass
class LogEvent:
    """Parsed log event"""
    timestamp: datetime
    event_type: str  # zone_change, level_up, quest_complete, item_pickup, etc.
    data: Dict[str, Any]
    raw_line: str

# ============================================================
# Log Parser
# ============================================================

class PoELogParser:
    """Parses PoE client.txt log file for leveling events."""
    
    # Log patterns (from Exile-UI client.txt)
    # Zone: "2024/01/15 10:00:00 You have entered Twilight Strand."
    # Level: "2024/01/15 10:05:00 CharacterName (Class) is now level 2"
    # Quest: Various formats from NPC dialogue
    PATTERNS = {
        "zone_change": re.compile(
            r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*?"
            r"You have entered (.+?)\."
        ),
        "level_up": re.compile(
            r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*?"
            r"is now level (\d+)"
        ),
        "quest_complete": re.compile(
            r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*?"
            r"Quest completed: ([^.]+)"
        ),
        "quest_reward": re.compile(
            r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*?"
            r"Received quest reward: ([^.]+)"
        ),
        "area_transition": re.compile(
            r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*?"
            r"Area transition: (.+?) -> (.+?)"
        ),
    }
    
    def __init__(self, log_path: Path):
        self.log_path = Path(log_path).expanduser()
        self._position = 0
        self._callbacks: Dict[str, List[Callable]] = {
            "zone_change": [],
            "level_up": [],
            "quest_complete": [],
            "quest_reward": [],
            "area_transition": [],
            "any": []
        }
    
    def on(self, event_type: str, callback: Callable[[LogEvent], None]):
        """Register callback for event type."""
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)
        self._callbacks["any"].append(callback)
    
    def _parse_line(self, line: str) -> Optional[LogEvent]:
        """Parse a single log line."""
        for event_type, pattern in self.PATTERNS.items():
            match = pattern.search(line)
            if match:
                groups = match.groups()
                timestamp = datetime.strptime(groups[0], "%Y/%m/%d %H:%M:%S")
                
                data = {}
                if event_type == "zone_change":
                    data["zone_name"] = groups[1].strip()
                elif event_type == "level_up":
                    data["new_level"] = int(groups[1])
                elif event_type == "quest_complete":
                    data["quest_name"] = groups[1].strip()
                elif event_type == "quest_reward":
                    data["reward"] = groups[1].strip()
                elif event_type == "area_transition":
                    data["from_zone"] = groups[1].strip()
                    data["to_zone"] = groups[2].strip()
                
                return LogEvent(timestamp, event_type, data, line)
        return None
    
    def read_new_lines(self) -> List[LogEvent]:
        """Read new lines since last position."""
        if not self.log_path.exists():
            return []
        
        events = []
        with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(self._position)
            for line in f:
                event = self._parse_line(line)
                if event:
                    events.append(event)
                    # Trigger callbacks
                    for cb in self._callbacks.get(event.event_type, []):
                        cb(event)
                    for cb in self._callbacks["any"]:
                        cb(event)
            self._position = f.tell()
        
        return events
    
    def tail_follow(self, interval: float = 1.0, stop_event: Optional[threading.Event] = None):
        """Continuously tail the log file."""
        while not (stop_event and stop_event.is_set()):
            self.read_new_lines()
            time.sleep(interval)

# ============================================================
# Data Loaders
# ============================================================

class ExileUIDataLoader:
    """Loads and caches Exile-UI leveling data."""
    
    def __init__(self, data_dir: Path = EXILE_UI_DATA_DIR):
        self.data_dir = data_dir
        self._zones: Dict[str, ZoneInfo] = {}
        self._gems: Dict[str, GemInfo] = {}
        self._guide: List = []
        self._tree_nodes: Dict[str, PassiveNode] = {}
        self._tree_constants: Dict = {}
        self._quest_map: Dict = {}
    
    def load_all(self):
        """Load all data files."""
        self._load_areas()
        self._load_gems()
        self._load_guide()
        self._load_tree()
    
    def _load_areas(self):
        """Load zones from areas.json (Act 1-10 structure)."""
        areas_file = self.data_dir / "english" / "[leveltracker] areas.json"
        if not areas_file.exists():
            # Try to download from GitHub
            self._download_areas()
            return
        
        with open(areas_file) as f:
            acts_data = json.load(f)
        
        for act_idx, act_zones in enumerate(acts_data):
            act_num = act_idx + 1
            for zone_data in act_zones:
                zone = ZoneInfo(
                    id=zone_data.get("id", ""),
                    name=zone_data.get("name", ""),
                    level=zone_data.get("lvl"),
                    map_name=zone_data.get("map_name"),
                    crafting_recipe=zone_data.get("crafting_recipe"),
                    act=act_num
                )
                # Determine if zone has Lab trial (specific zones)
                zone.has_lab_trial = self._has_lab_trial(zone.id, zone.name)
                self._zones[zone.id] = zone
                self._zones[zone.name.lower()] = zone
    
    def _has_lab_trial(self, zone_id: str, zone_name: str) -> bool:
        """Check if zone has a Lab trial (first character only)."""
        # Based on Exile-UI guide and PoE wiki
        lab_trial_zones = {
            "1_1_7_1",  # Lower Prison
            "1_2_6_1",  # Chamber of Sins 1
            "1_3_10_1", # The Sewers
            "1_4_3_1",  # The Mines 1
            "2_6_7_1",  # Lower Prison (Act 6)
            "2_7_5_1",  # Chamber of Sins 1 (Act 7)
            "2_8_12_1", # Solaris Temple 1
            "2_9_10_1", # Belly of the Beast
            "2_10_9",   # The Ossuary
        }
        return zone_id in lab_trial_zones
    
    def _load_gems(self):
        """Load gems from gems.json."""
        gems_file = self.data_dir / "english" / "[leveltracker] gems.json"
        if not gems_file.exists():
            return
        
        with open(gems_file) as f:
            data = json.load(f)
        
        self._quest_map = data.get("_quests", {})
        
        for gem_name, gem_data in data.items():
            if gem_name.startswith("_"):
                continue
            gem = GemInfo(
                name=gem_name,
                attribute=gem_data.get("attribute", 0),
                level=gem_data.get("level", 1),
                quests=gem_data.get("quests", {})
            )
            self._gems[gem_name.lower()] = gem
    
    def _load_guide(self):
        """Load default guide from guide.json."""
        guide_file = self.data_dir / "english" / "[leveltracker] default guide.json"
        if not guide_file.exists():
            return
        
        with open(guide_file) as f:
            self._guide = json.load(f)
    
    def _load_tree(self):
        """Load passive tree from tree JSON."""
        tree_file = self.data_dir / "global" / "[leveltracker] tree 3_29.json"
        if not tree_file.exists():
            return
        
        with open(tree_file) as f:
            data = json.load(f)
        
        self._tree_constants = data.get("constants", {})
        
        # Parse nodes from groups
        for group in data.get("groups", []):
            for node_id in group.get("nodes", []):
                # Full node data is in the root object
                pass
        
        # Parse root nodes
        root = data.get("root", {})
        for node_id, node_data in root.items():
            if node_id in ("groups", "constants", "tree"):
                continue
            if not isinstance(node_data, dict):
                continue
            
            node = PassiveNode(
                id=node_id,
                name=node_data.get("dn", f"Node {node_id}"),
                group=str(node_data.get("group", "")),
                orbit=node_data.get("orbit", 0),
                orbit_index=node_data.get("orbitindex", 0),
                is_notable=node_data.get("isnotable") == "1",
                is_keystone=node_data.get("iskystone") == "1",
                is_mastery=node_data.get("ismastery") == "1",
                ascendancy_name=node_data.get("ascendancyname"),
                stats=node_data.get("sd", []),
                connections=node_data.get("out", [])
            )
            self._tree_nodes[node_id] = node
    
    def _download_areas(self):
        """Download areas data from GitHub."""
        # Placeholder - in real use, would fetch from raw.githubusercontent.com
        pass
    
    # --- Query methods ---
    
    def get_zone(self, zone_id: str) -> Optional[ZoneInfo]:
        """Get zone by ID or name."""
        return self._zones.get(zone_id) or self._zones.get(zone_id.lower())
    
    def get_zone_by_level(self, level: int) -> List[ZoneInfo]:
        """Get zones appropriate for a level."""
        return [z for z in self._zones.values() if z.level and abs(z.level - level) <= 3]
    
    def get_next_zones(self, current_zone_id: str) -> List[ZoneInfo]:
        """Get connected zones from current zone."""
        zone = self.get_zone(current_zone_id)
        if not zone:
            return []
        return [self._zones[c] for c in zone.connections if c in self._zones]
    
    def get_gem(self, gem_name: str) -> Optional[GemInfo]:
        """Get gem by name."""
        return self._gems.get(gem_name.lower())
    
    def get_available_gems(self, level: int, completed_quests: List[str], 
                          character_class: str = "") -> List[GemInfo]:
        """Get gems available at current level with quest progress."""
        available = []
        for gem in self._gems.values():
            if gem.level <= level:
                # Check if unlocked via quest
                unlocked = False
                for quest_name, quest_data in gem.quests.items():
                    vendor_classes = quest_data.get("vendor", [])
                    quest_classes = quest_data.get("quest", [])
                    
                    # Available from vendor for this class
                    if not character_class or character_class.lower() in [c.lower() for c in vendor_classes]:
                        unlocked = True
                        break
                    
                    # Unlocked via quest completion
                    if quest_name in completed_quests:
                        if not character_class or character_class.lower() in [c.lower() for c in quest_classes]:
                            unlocked = True
                            break
                
                if unlocked or not gem.quests:
                    available.append(gem)
        
        return sorted(available, key=lambda g: (g.level, g.name))
    
    def get_next_gem_recommendations(self, current_gems: List[str], level: int,
                                    completed_quests: List[str], character_class: str,
                                    target_build_gems: List[str]) -> List[GemInfo]:
        """Get recommended next gems based on target build."""
        available = self.get_available_gems(level, completed_quests, character_class)
        
        # Prioritize gems in target build
        target_gem_names = [g.lower() for g in target_build_gems]
        recommended = []
        
        for gem in available:
            if gem.name.lower() in target_gem_names and gem.name not in current_gems:
                recommended.append(gem)
        
        # Add other useful gems
        for gem in available:
            if gem not in recommended and gem.name not in current_gems:
                recommended.append(gem)
        
        return recommended[:5]  # Top 5
    
    def get_passive_node(self, node_id: str) -> Optional[PassiveNode]:
        """Get passive node by ID."""
        return self._tree_nodes.get(str(node_id))
    
    def get_next_passive_nodes(self, allocated: List[str], target_build_nodes: List[str],
                              class_id: int, ascendancy_id: int) -> List[PassiveNode]:
        """Get next recommended passive nodes based on target build."""
        # Find nodes in target build that aren't allocated yet
        remaining = [n for n in target_build_nodes if n not in allocated]
        
        recommended = []
        for node_id in remaining[:10]:  # Limit
            node = self.get_passive_node(node_id)
            if node:
                # Check if prerequisites met (simplified - check connections)
                prereqs_met = all(p in allocated for p in node.connections if p in self._tree_nodes)
                if prereqs_met or not node.connections:
                    recommended.append(node)
        
        return recommended[:3]  # Top 3
    
    def get_guide_step(self, zone_id: str, level: int, conditions: Dict = None) -> List:
        """Get current guide step for zone/level."""
        # Simplified - find matching act in guide
        act_idx = 0
        for i, act_data in enumerate(self._guide):
            if act_data and isinstance(act_data[0], list):
                first_step = act_data[0]
                if isinstance(first_step, list) and len(first_step) > 1:
                    if "areaid" in str(first_step[1]):
                        # This is a zone step, check if matches
                        pass
        return []

# ============================================================
# Leveling Tracker (Main Class)
# ============================================================

class LevelingTracker:
    """Main leveling tracker that coordinates log parsing, data, and guidance."""
    
    def __init__(self, 
                 log_path: str = str(DEFAULT_LOG_PATH),
                 target_build_id: str = "earthshatter_berserker_god_tier",
                 league: str = "Settlers",
                 character_class: str = "Marauder",
                 ascendancy: str = "Berserker",
                 data_dir: Optional[Path] = None):
        
        self.log_path = Path(log_path).expanduser()
        self.target_build_id = target_build_id
        self.league = league
        self.character_class = character_class
        self.ascendancy = ascendancy
        
        # Initialize components
        self.parser = PoELogParser(self.log_path)
        self.data = ExileUIDataLoader(data_dir or EXILE_UI_DATA_DIR)
        self.data.load_all()
        
        # State
        self.state = LevelingState()
        self.state.character_name = ""
        self._stop_event = threading.Event()
        self._tail_thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[LevelingState], None]] = []
        
        # Load target build
        self._load_target_build()
        
        # Register log callbacks
        self.parser.on("zone_change", self._on_zone_change)
        self.parser.on("level_up", self._on_level_up)
        self.parser.on("quest_complete", self._on_quest_complete)
        self.parser.on("quest_reward", self._on_quest_reward)
    
    def _load_target_build(self):
        """Load target build from store."""
        from pob_target_build_store import TargetBuildStore, create_earthshatter_berserker_template
        
        store = TargetBuildStore()
        build = store.get(self.target_build_id)
        if not build:
            # Use template
            if "earthshatter" in self.target_build_id and "berserker" in self.target_build_id:
                build = create_earthshatter_berserker_template()
            else:
                build = create_earthshatter_berserker_template()
        
        self.target_build = build
        self.target_gems = [item.target_unique_name or item.base_type for item in build.items if item.target_unique_name]
        self.target_passives = []  # Would be loaded from build's passive_tree_goals
    
    def import_pob_build(self, pob_xml_path: Path):
        """Import a PoB build XML for leveling guidance (passive tree, gems, items)."""
        import xml.etree.ElementTree as ET
        
        tree = ET.parse(pob_xml_path)
        root = tree.getroot()
        
        # Extract passive tree nodes from the active spec
        tree_elem = root.find('.//Tree')
        if tree_elem is not None:
            active_spec_id = tree_elem.get('activeSpec', '1')
            for spec in root.findall('.//Spec'):
                if spec.get('title', '').startswith(str(active_spec_id)) or active_spec_id in spec.get('title', ''):
                    nodes_str = spec.get('nodes', '')
                    if nodes_str:
                        self.target_passives = nodes_str.split(',')
                        break
        
        # Extract skill gems from all Skill elements
        gems = []
        for skill in root.findall('.//Skill'):
            for gem in skill.findall('Gem'):
                gem_name = gem.get('name')
                if gem_name and gem.get('enableGlobal1') == 'true':
                    gems.append(gem_name)
        
        # Add to target gems for recommendations
        self.target_gems.extend([g for g in gems if g not in self.target_gems])
        
        # Extract items for reference
        items = []
        for item in root.findall('.//Item'):
            text_content = item.text.strip() if item.text else ""
            if text_content:
                lines = text_content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith(('Rarity:', 'Unique ID:', 'Item Level:', 'Quality:', 'LevelReq:', 'Armour:', 'ArmourBasePercentile:', 'Sockets:', 'Implicits:', '+', '-', 'Reflects', 'Gain', 'Grants', 'Regenerates', 'Adds')):
                        if ':' not in line or line.count(':') > 1:
                            items.append(line)
                            break
        
        print(f"Imported PoB build: {len(self.target_passives)} passive nodes, {len(gems)} gems, {len(items)} items")
        return {
            "passive_nodes": self.target_passives,
            "gems": gems,
            "items": items
        }
    
    def on_state_change(self, callback: Callable[[LevelingState], None]):
        """Register callback for state changes."""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self):
        """Notify all callbacks of state change."""
        self.state.last_update = datetime.now().isoformat()
        for cb in self._callbacks:
            try:
                cb(self.state)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def _on_zone_change(self, event: LogEvent):
        """Handle zone change event."""
        zone_name = event.data.get("zone_name", "").strip()
        zone = self.data.get_zone(zone_name)
        
        if zone:
            self.state.current_zone_id = zone.id
            self.state.current_zone_name = zone.name
            self.state.current_act = zone.act
            
            # Check for Lab trial
            if zone.has_lab_trial:
                self.state.lab_trial_zone = zone.name
            else:
                self.state.lab_trial_zone = None
            
            # Update gem recommendations
            self._update_gem_recommendations()
            
            # Update passive recommendations
            self._update_passive_recommendations()
            
            # Check milestone
            self._check_milestone(zone)
        
        self._notify_callbacks()
    
    def _on_level_up(self, event: LogEvent):
        """Handle level up event."""
        new_level = event.data.get("new_level", 0)
        self.state.level = new_level
        
        # Update recommendations
        self._update_gem_recommendations()
        self._update_passive_recommendations()
        
        # Check milestone
        self._check_milestone_level(new_level)
        
        self._notify_callbacks()
    
    def _on_quest_complete(self, event: LogEvent):
        """Handle quest completion."""
        quest_name = event.data.get("quest_name", "").strip().lower()
        if quest_name and quest_name not in self.state.completed_quests:
            self.state.completed_quests.append(quest_name)
            self._update_gem_recommendations()
            self._notify_callbacks()
    
    def _on_quest_reward(self, event: LogEvent):
        """Handle quest reward (gem reward)."""
        reward = event.data.get("reward", "").strip()
        if reward and reward not in self.state.active_gems:
            self.state.active_gems.append(reward)
            self._notify_callbacks()
    
    def _update_gem_recommendations(self):
        """Update gem recommendations based on current state."""
        if not self.target_build:
            return
        
        recommendations = self.data.get_next_gem_recommendations(
            current_gems=self.state.active_gems,
            level=self.state.level,
            completed_quests=self.state.completed_quests,
            character_class=self.character_class,
            target_build_gems=self.target_gems
        )
        
        self.state.next_gems = recommendations
        self.state.next_gem = recommendations[0] if recommendations else None
    
    def _update_passive_recommendations(self):
        """Update passive node recommendations."""
        if not self.target_build:
            return
        
        # Get class/ascendancy IDs
        from pob_passive_converter import get_class_id, get_ascendancy_id
        class_id = get_class_id(self.character_class)
        ascendancy_id = get_ascendancy_id(self.character_class, self.ascendancy)
        
        recommendations = self.data.get_next_passive_nodes(
            allocated=self.state.allocated_passives,
            target_build_nodes=self.target_passives,
            class_id=class_id,
            ascendancy_id=ascendancy_id
        )
        
        self.state.next_passive_node = recommendations[0] if recommendations else None
    
    def _check_milestone(self, zone: ZoneInfo):
        """Check if current zone is a milestone."""
        # Milestones: Act transitions, Lab trials, key bosses
        milestone_zones = {
            "1_1_11_2": "Merveil (Act 1 boss)",
            "1_2_14_2": "Vaal Ruins / Weaver",
            "1_3_18_2": "Dominus (Act 3 boss)",
            "1_4_6_3": "Malachai (Act 4 boss)",
            "1_5_8": "Kitava (Act 5 boss)",
            "2_6_15": "Brine King (Act 6 boss)",
            "2_7_12_2": "Temple of Decay",
            "2_8_13": "Harbour Bridge (Act 8 boss)",
            "2_9_10_2": "Rotting Core (Act 9 boss)",
            "2_10_6": "Kitava (Act 10 boss)",
        }
        
        if zone.id in milestone_zones:
            self.state.milestone_reached = True
            self.state.milestone_details = {
                "zone": zone.name,
                "milestone": milestone_zones[zone.id],
                "level": self.state.level,
                "timestamp": datetime.now().isoformat()
            }
    
    def _check_milestone_level(self, level: int):
        """Check if level is a milestone."""
        milestone_levels = [10, 20, 30, 40, 50, 60, 70, 80, 90]
        if level in milestone_levels:
            self.state.milestone_reached = True
            self.state.milestone_details = {
                "type": "level",
                "level": level,
                "timestamp": datetime.now().isoformat()
            }
    
    def start(self):
        """Start tracking (tail log file)."""
        self._stop_event.clear()
        self._tail_thread = threading.Thread(
            target=self.parser.tail_follow,
            args=(1.0, self._stop_event),
            daemon=True
        )
        self._tail_thread.start()
        
        # Initial parse of existing log
        self.parser.read_new_lines()
        self._notify_callbacks()
    
    def stop(self):
        """Stop tracking."""
        self._stop_event.set()
        if self._tail_thread:
            self._tail_thread.join(timeout=2.0)
    
    def get_state(self) -> LevelingState:
        """Get current leveling state."""
        return self.state
    
    def run_milestone_comparison(self) -> Dict:
        """Run pipeline comparison at milestone."""
        # This would integrate with pob_update_manager.py check
        # For now, return structure
        return {
            "milestone": self.state.milestone_details,
            "character_level": self.state.level,
            "target_build": self.target_build_id,
            "comparison_pending": True,
            "message": "Run pipeline to compare character vs target build"
        }
    
    def get_dashboard_data(self) -> Dict:
        """Get data formatted for dashboard display."""
        return {
            "character": {
                "name": self.state.character_name,
                "level": self.state.level,
                "class": self.character_class,
                "ascendancy": self.ascendancy,
                "league": self.league
            },
            "zone": {
                "id": self.state.current_zone_id,
                "name": self.state.current_zone_name,
                "act": self.state.current_act,
                "level": self.data.get_zone(self.state.current_zone_id).level if self.data.get_zone(self.state.current_zone_id) else None,
                "has_lab_trial": bool(self.state.lab_trial_zone),
                "lab_trial_zone": self.state.lab_trial_zone
            },
            "gems": {
                "active": self.state.active_gems,
                "next_recommended": [asdict(g) for g in self.state.next_gems[:3]] if self.state.next_gems else [],
                "current_focus": asdict(self.state.next_gem) if self.state.next_gem else None
            },
            "passive_tree": {
                "allocated_count": len(self.state.allocated_passives),
                "next_node": asdict(self.state.next_passive_node) if self.state.next_passive_node else None,
                "target_build": self.target_build.name if self.target_build else None
            },
            "milestone": {
                "reached": self.state.milestone_reached,
                "details": self.state.milestone_details
            },
            "quests": {
                "completed": self.state.completed_quests,
                "count": len(self.state.completed_quests)
            },
            "last_update": self.state.last_update
        }


# ============================================================
# CLI / Testing
# ============================================================

def main():
    """Test the leveling tracker."""
    import argparse
    
    parser = argparse.ArgumentParser(description="PoB Leveling Tracker")
    parser.add_argument("--log", default=str(DEFAULT_LOG_PATH), help="Path to client.txt")
    parser.add_argument("--build", default="earthshatter_berserker_god_tier", help="Target build ID")
    parser.add_argument("--league", default="Settlers", help="League name")
    parser.add_argument("--class", dest="char_class", default="Marauder", help="Character class")
    parser.add_argument("--ascendancy", default="Berserker", help="Ascendancy")
    parser.add_argument("--once", action="store_true", help="Parse once and exit")
    args = parser.parse_args()
    
    tracker = LevelingTracker(
        log_path=args.log,
        target_build_id=args.build,
        league=args.league,
        character_class=args.char_class,
        ascendancy=args.ascendancy
    )
    
    def print_state(state: LevelingState):
        print(f"\n=== Leveling State ===")
        print(f"Level: {state.level} | Zone: {state.current_zone_name} (Act {state.current_act})")
        print(f"Next Gem: {state.next_gem.name if state.next_gem else 'None'}")
        print(f"Next Node: {state.next_passive_node.name if state.next_passive_node else 'None'}")
        print(f"Lab Trial: {state.lab_trial_zone or 'None'}")
        print(f"Milestone: {state.milestone_reached}")
        print(f"Quests: {len(state.completed_quests)} completed")
    
    tracker.on_state_change(print_state)
    
    if args.once:
        tracker.parser.read_new_lines()
    else:
        print("Starting leveling tracker... (Ctrl+C to stop)")
        tracker.start()
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            tracker.stop()
            print("\nStopped.")


if __name__ == "__main__":
    main()