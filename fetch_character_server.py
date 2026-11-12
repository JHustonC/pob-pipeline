#!/usr/bin/env python3
"""
Fetch Character Server for PoE Dashboard
=========================================
Runs on the gaming machine (where PoE is installed) and provides:
- OAuth flow with GGG servers
- Character list fetching
- Character data import (level, zone, passives, equipment, gems)
- Real-time sync for dashboard on remote device

Run on gaming machine: python3 fetch_character_server.py
Access dashboard from remote: http://<gaming-machine-ip>:8080
"""

import os
import json
import time
import threading
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any, List
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
import requests

# Import existing OAuth module
import sys
sys.path.insert(0, str(Path(__file__).parent))
from pob_oauth_import import (
    CLIENT_ID, SCOPES, OAUTH_AUTHORIZE_URL, OAUTH_TOKEN_URL, API_BASE_URL,
    CALLBACK_PORTS, CALLBACK_TIMEOUT,
    generate_pkce_pair, generate_state, build_authorize_url,
    exchange_code_for_tokens, refresh_access_token,
    PoEAPIClient, save_tokens, load_tokens,
    OAuthCallbackHandler, start_callback_server
)
from pob_leveling import LevelingTracker, DEFAULT_LOG_PATH, EXILE_UI_DATA_DIR
from pob_target_build_store import TargetBuildStore, create_earthshatter_berserker_template
from gist_sync import GistSync, create_gist

# Server config
SERVER_PORT = 8080
TOKEN_FILE = Path.home() / ".pob_pipeline" / "poe_tokens.json"
CHARACTER_STATE_FILE = Path.home() / ".pob_pipeline" / "character_state.json"

# Gist Sync config (from environment)
GIST_ID = os.environ.get("GH_GIST_ID")
GIST_TOKEN = os.environ.get("GH_TOKEN")
GIST_FILENAME = "character_state.json"
GIST_SYNC_INTERVAL = 30  # seconds

# Global state
oauth_callback_data = {}
oauth_server = None
oauth_server_thread = None
api_client: Optional[PoEAPIClient] = None
leveling_tracker: Optional[LevelingTracker] = None
gist_sync: Optional[GistSync] = None
character_state = {
    "selected_character": None,
    "character_data": None,
    "level": 1,
    "zone": "",
    "passives": [],
    "equipment": [],
    "gems": [],
    "last_sync": None,
    "auto_sync": False,
    "sync_interval": 30  # seconds
}

def load_character_state():
    global character_state, gist_sync
    # Try local file first
    if CHARACTER_STATE_FILE.exists():
        try:
            with open(CHARACTER_STATE_FILE) as f:
                character_state.update(json.load(f))
        except:
            pass
    # Try Gist if configured
    if GIST_ID and GIST_TOKEN:
        gist_sync = GistSync(GIST_ID, GIST_TOKEN, GIST_FILENAME, GIST_SYNC_INTERVAL)
        gist_state = gist_sync.pull()
        if gist_state:
            character_state.update(gist_state)
            print(f"📥 Loaded character state from Gist")

def save_character_state():
    CHARACTER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHARACTER_STATE_FILE, 'w') as f:
        json.dump(character_state, f, indent=2)
    # Also push to Gist if configured
    if gist_sync:
        gist_sync.push(character_state)

def initialize_tracker():
    global leveling_tracker
    if leveling_tracker is None:
        leveling_tracker = LevelingTracker(
            log_path=str(DEFAULT_LOG_PATH),
            target_build_id="earthshatter_berserker_god_tier",
            league="Settlers"
        )

def sync_character_data():
    """Sync character data from PoE API to local state."""
    global api_client, character_state
    
    if not api_client or not character_state["selected_character"]:
        return False
    
    try:
        char_name = character_state["selected_character"]
        character = api_client.get_character(char_name)
        
        if not character:
            return False
        
        # Extract key data
        character_state["character_data"] = character
        character_state["level"] = character.get("level", 1)
        character_state["zone"] = character.get("area", {}).get("name", "Unknown")
        character_state["last_sync"] = time.time()
        
        # Passives
        passives = character.get("passives", {})
        character_state["passives"] = passives.get("hashes", [])
        
        # Equipment
        equipment = character.get("equipment", [])
        character_state["equipment"] = [
            {
                "slot": item.get("inventoryId", ""),
                "name": item.get("name", "Unknown"),
                "type": item.get("typeLine", ""),
                "ilvl": item.get("ilvl", 0),
                "rarity": item.get("rarity", ""),
                "mods": item.get("explicitMods", []),
                "requirements": item.get("requirements", [])
            }
            for item in equipment
        ]
        
        # Gems
        gems = []
        for item in equipment:
            if "socketedItems" in item:
                for gem in item["socketedItems"]:
                    gems.append({
                        "name": gem.get("name", ""),
                        "level": gem.get("level", 1),
                        "quality": gem.get("quality", 0),
                        "slot": item.get("inventoryId", ""),
                        "support": gem.get("support", False)
                    })
        character_state["gems"] = gems
        
        # Update leveling tracker state
        if leveling_tracker:
            leveling_tracker.state.level = character_state["level"]
            leveling_tracker.state.current_zone_name = character_state["zone"]
            leveling_tracker.state.active_gems = [g["name"] for g in gems if not g["support"]]
            # Update passive recommendations
            leveling_tracker._update_passive_recommendations()
            leveling_tracker._notify_callbacks()
        
        save_character_state()
        return True
        
    except Exception as e:
        print(f"Sync error: {e}")
        return False

def auto_sync_loop():
    """Background thread to auto-sync character data."""
    # Use GistSync's auto-sync if available
    if gist_sync:
        gist_sync.start_auto_sync(lambda: character_state)
        # Keep thread alive
        while character_state.get("auto_sync", False):
            time.sleep(1)
        gist_sync.stop_auto_sync()
    else:
        # Fallback to local-only auto-sync
        while character_state.get("auto_sync", False):
            time.sleep(character_state.get("sync_interval", 30))
            if character_state.get("auto_sync", False):
                print(f"🔄 Auto-sync: {character_state['selected_character']}")
                sync_character_data()

# ============================================================
# HTTP Request Handler
# ============================================================

class FetchCharacterHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/":
            self.serve_dashboard()
        elif path == "/api/status":
            self.api_status()
        elif path == "/api/oauth/start":
            self.api_oauth_start()
        elif path == "/api/oauth/callback":
            self.api_oauth_callback(parsed)
        elif path == "/api/characters":
            self.api_characters()
        elif path == "/api/character/select":
            self.api_character_select(parsed)
        elif path == "/api/character/sync":
            self.api_character_sync()
        elif path == "/api/character/state":
            self.api_character_state()
        elif path == "/api/character/auto_sync":
            self.api_auto_sync(parsed)
        elif path == "/api/leveling/state":
            self.api_leveling_state()
        elif path == "/api/leveling/recommendations":
            self.api_leveling_recommendations()
        else:
            self.send_error(404)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/api/oauth/start":
            self.api_oauth_start()
        elif path == "/api/character/select":
            self.api_character_select_post()
        elif path == "/api/character/auto_sync":
            self.api_auto_sync_post()
        else:
            self.send_error(404)
    
    def serve_dashboard(self):
        """Serve the crafting checklist dashboard with fetch character integration."""
        dashboard_path = Path(__file__).parent / "crafting_checklist.html"
        if dashboard_path.exists():
            with open(dashboard_path) as f:
                content = f.read()
            
            # Inject fetch character script
            fetch_script = """
            <script>
            // Fetch Character Integration
            const FETCH_API_BASE = '/api';
            
            async function fetchCharacterStart() {
                const btn = document.getElementById('fetch-char-btn');
                btn.disabled = true;
                btn.textContent = '🔐 Starting OAuth...';
                try {
                    const res = await fetch(FETCH_API_BASE + '/oauth/start', {method: 'POST'});
                    const data = await res.json();
                    if (data.auth_url) {
                        window.open(data.auth_url, '_blank', 'width=600,height=700');
                        btn.textContent = '⏳ Waiting for auth...';
                        pollOAuthStatus();
                    } else {
                        alert('Error: ' + (data.error || 'Unknown'));
                        btn.disabled = false;
                        btn.textContent = '🔐 Fetch Character';
                    }
                } catch (e) {
                    alert('Error: ' + e);
                    btn.disabled = false;
                    btn.textContent = '🔐 Fetch Character';
                }
            }
            
            async function pollOAuthStatus() {
                try {
                    const res = await fetch(FETCH_API_BASE + '/oauth/status');
                    const data = await res.json();
                    if (data.authenticated) {
                        document.getElementById('fetch-char-btn').textContent = '✅ Authenticated';
                        document.getElementById('fetch-char-btn').disabled = true;
                        loadCharacters();
                    } else {
                        setTimeout(pollOAuthStatus, 2000);
                    }
                } catch (e) {
                    setTimeout(pollOAuthStatus, 2000);
                }
            }
            
            async function loadCharacters() {
                try {
                    const res = await fetch(FETCH_API_BASE + '/characters');
                    const data = await res.json();
                    const select = document.getElementById('character-select');
                    select.innerHTML = '<option value="">Select character...</option>';
                    data.characters.forEach(c => {
                        const opt = document.createElement('option');
                        opt.value = c.name;
                        opt.textContent = `${c.name} (Lvl ${c.level} ${c.class}) - ${c.league}`;
                        select.appendChild(opt);
                    });
                    document.getElementById('character-select-container').style.display = 'block';
                } catch (e) {
                    console.error(e);
                }
            }
            
            async function selectCharacter() {
                const select = document.getElementById('character-select');
                const name = select.value;
                if (!name) return;
                
                const btn = document.getElementById('select-char-btn');
                btn.disabled = true;
                btn.textContent = '📥 Fetching...';
                
                try {
                    const res = await fetch(FETCH_API_BASE + '/character/select', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({name})
                    });
                    const data = await res.json();
                    if (data.success) {
                        btn.textContent = '✅ Character Loaded';
                        loadCharacterState();
                        startAutoSync();
                    } else {
                        alert('Error: ' + data.error);
                        btn.disabled = false;
                        btn.textContent = '📥 Load Character';
                    }
                } catch (e) {
                    alert('Error: ' + e);
                    btn.disabled = false;
                    btn.textContent = '📥 Load Character';
                }
            }
            
            async function loadCharacterState() {
                try {
                    const res = await fetch(FETCH_API_BASE + '/character/state');
                    const data = await res.json();
                    const div = document.getElementById('character-state');
                    div.innerHTML = `
                        <h4>📊 ${data.character_data?.name || data.selected_character}</h4>
                        <p><strong>Level:</strong> ${data.level}</p>
                        <p><strong>Zone:</strong> ${data.zone}</p>
                        <p><strong>Passives:</strong> ${data.passives?.length || 0}</p>
                        <p><strong>Equipment:</strong> ${data.equipment?.length || 0} slots</p>
                        <p><strong>Gems:</strong> ${data.gems?.length || 0}</p>
                        <p><strong>Last Sync:</strong> ${data.last_sync ? new Date(data.last_sync * 1000).toLocaleTimeString() : 'Never'}</p>
                    `;
                    document.getElementById('character-state-container').style.display = 'block';
                } catch (e) {
                    console.error(e);
                }
            }
            
            async function syncCharacter() {
                try {
                    const res = await fetch(FETCH_API_BASE + '/character/sync', {method: 'POST'});
                    const data = await res.json();
                    if (data.success) {
                        loadCharacterState();
                    } else {
                        alert('Sync failed: ' + data.error);
                    }
                } catch (e) {
                    alert('Sync error: ' + e);
                }
            }
            
            async function toggleAutoSync() {
                const checkbox = document.getElementById('auto-sync');
                try {
                    await fetch(FETCH_API_BASE + '/character/auto_sync', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({enabled: checkbox.checked})
                    });
                } catch (e) {
                    checkbox.checked = !checkbox.checked;
                    alert('Error: ' + e);
                }
            }
            
            async function loadLevelingRecommendations() {
                try {
                    const res = await fetch(FETCH_API_BASE + '/leveling/recommendations');
                    const data = await res.json();
                    const div = document.getElementById('leveling-recs');
                    div.innerHTML = `
                        <h4>💎 Next Gems</h4>
                        <ul>${(data.next_gems || []).map(g => `<li>${g.name} (Lvl ${g.level})</li>`).join('')}</ul>
                        <h4>🌳 Next Passives</h4>
                        <ul>${(data.next_passives || []).map(p => `<li>${p.name}</li>`).join('')}</ul>
                    `;
                    document.getElementById('leveling-recs-container').style.display = 'block';
                } catch (e) {
                    console.error(e);
                }
            }
            
            // Check auth status on load
            async function checkAuth() {
                try {
                    const res = await fetch(FETCH_API_BASE + '/status');
                    const data = await res.json();
                    if (data.authenticated) {
                        document.getElementById('fetch-char-btn').textContent = '✅ Authenticated';
                        document.getElementById('fetch-char-btn').disabled = true;
                        loadCharacters();
                    }
                } catch (e) {}
            }
            
            document.addEventListener('DOMContentLoaded', checkAuth);
            </script>
            """
            
            # Inject before </body>
            content = content.replace('</body>', fetch_script + '</body>')
            
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(content.encode())
        else:
            self.send_error(404)
    
    def api_status(self):
        self.send_json({
            "authenticated": api_client is not None and api_client.access_token is not None,
            "server_time": time.time()
        })
    
    def api_oauth_start(self):
        global api_client, oauth_callback_data, oauth_server, oauth_server_thread
        
        # Generate PKCE
        code_verifier, code_challenge = generate_pkce_pair()
        state = generate_state()
        
        # Start callback server
        oauth_callback_data = {"code_verifier": code_verifier, "state": state}
        oauth_server = None
        port = None
        
        for p in CALLBACK_PORTS:
            try:
                oauth_server = start_callback_server(p, oauth_callback_data)
                port = p
                break
            except OSError:
                continue
        
        if not oauth_server:
            self.send_json({"error": "Could not start callback server"}, 500)
            return
        
        redirect_uri = f"http://localhost:{port}"
        auth_url = build_authorize_url(code_challenge, state, redirect_uri)
        
        # Run server in background
        oauth_server_thread = threading.Thread(target=oauth_server.serve_forever)
        oauth_server_thread.daemon = True
        oauth_server_thread.start()
        
        self.send_json({
            "auth_url": auth_url,
            "redirect_uri": redirect_uri,
            "state": state
        })
    
    def api_oauth_callback(self, parsed):
        global api_client, oauth_callback_data, oauth_server
        
        query = parse_qs(parsed.query)
        
        if "code" in query:
            oauth_callback_data["code"] = query["code"][0]
            oauth_callback_data["state"] = query.get("state", [None])[0]
            
            # Verify state
            if oauth_callback_data.get("state") != oauth_callback_data.get("state"):
                self.send_html("OAuth state mismatch", 400)
                return
            
            # Exchange code for tokens
            try:
                tokens = exchange_code_for_tokens(
                    oauth_callback_data["code"],
                    oauth_callback_data["code_verifier"],
                    f"http://localhost:{CALLBACK_PORTS[0]}"  # Use first port as fallback
                )
                
                api_client = PoEAPIClient(
                    access_token=tokens["access_token"],
                    refresh_token=tokens["refresh_token"],
                    token_expiry=int(time.time()) + tokens["expires_in"]
                )
                
                save_tokens(api_client, str(TOKEN_FILE))
                
                self.send_html("""
                <!DOCTYPE html><html><head><title>Success</title>
                <style>body{font-family:Arial;background:#121212;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
                .card{background:#1E1E1E;padding:20px;border-radius:10px;text-align:center}
                h1{color:#4CAF50}</style></head>
                <body><div class="card"><h1>✅ Authentication Successful</h1>
                <p>You can now return to the dashboard and fetch characters.</p>
                <script>setTimeout(() => window.close(), 3000);</script>
                </div></body></html>
                """)
                
            except Exception as e:
                self.send_html(f"Token exchange failed: {e}", 500)
        else:
            error = query.get("error", ["unknown"])[0]
            desc = query.get("error_description", [""])[0]
            self.send_html(f"OAuth failed: {error} - {desc}", 400)
        
        if oauth_server:
            oauth_server.shutdown()
    
    def api_characters(self):
        if not api_client:
            self.send_json({"error": "Not authenticated"}, 401)
            return
        
        try:
            char_list = api_client.get_character_list()
            characters = char_list.get("characters", [])
            self.send_json({"characters": characters})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def api_character_select(self, parsed):
        query = parse_qs(parsed.query)
        name = query.get("name", [None])[0]
        
        if not name:
            self.send_json({"error": "Character name required"}, 400)
            return
        
        if not api_client:
            self.send_json({"error": "Not authenticated"}, 401)
            return
        
        try:
            character = api_client.get_character(name)
            if not character:
                self.send_json({"error": "Character not found"}, 404)
                return
            
            character_state["selected_character"] = name
            character_state["character_data"] = character
            character_state["level"] = character.get("level", 1)
            character_state["zone"] = character.get("area", {}).get("name", "Unknown")
            character_state["last_sync"] = time.time()
            
            # Extract passives
            passives = character.get("passives", {})
            character_state["passives"] = passives.get("hashes", [])
            
            # Equipment
            equipment = character.get("equipment", [])
            character_state["equipment"] = [
                {
                    "slot": item.get("inventoryId", ""),
                    "name": item.get("name", "Unknown"),
                    "type": item.get("typeLine", ""),
                    "ilvl": item.get("ilvl", 0),
                    "rarity": item.get("rarity", ""),
                    "mods": item.get("explicitMods", []),
                }
                for item in equipment
            ]
            
            # Gems
            gems = []
            for item in equipment:
                if "socketedItems" in item:
                    for gem in item["socketedItems"]:
                        gems.append({
                            "name": gem.get("name", ""),
                            "level": gem.get("level", 1),
                            "quality": gem.get("quality", 0),
                            "slot": item.get("inventoryId", ""),
                            "support": gem.get("support", False)
                        })
            character_state["gems"] = gems
            
            save_character_state()
            
            self.send_json({"success": True, "character": character})
            
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def api_character_select_post(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        data = json.loads(body)
        name = data.get("name")
        
        if not name:
            self.send_json({"error": "Character name required"}, 400)
            return
        
        # Reuse the GET logic
        parsed = urlparse(f"/?name={name}")
        self.api_character_select(parsed)
    
    def api_character_sync(self):
        if not character_state["selected_character"]:
            self.send_json({"error": "No character selected"}, 400)
            return
        
        success = sync_character_data()
        if success:
            self.send_json({"success": True, "last_sync": character_state["last_sync"]})
        else:
            self.send_json({"error": "Sync failed"}, 500)
    
    def api_character_state(self):
        self.send_json(character_state)
    
    def api_auto_sync(self, parsed):
        query = parse_qs(parsed.query)
        enabled = query.get("enabled", ["false"])[0].lower() == "true"
        character_state["auto_sync"] = enabled
        save_character_state()
        
        if enabled:
            if gist_sync:
                gist_sync.start_auto_sync(lambda: character_state)
            else:
                thread = threading.Thread(target=auto_sync_loop, daemon=True)
                thread.start()
        
        self.send_json({"auto_sync": enabled})
    
    def api_auto_sync_post(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        data = json.loads(body)
        enabled = data.get("enabled", False)
        
        character_state["auto_sync"] = enabled
        save_character_state()
        
        if enabled:
            if gist_sync:
                gist_sync.start_auto_sync(lambda: character_state)
            else:
                thread = threading.Thread(target=auto_sync_loop, daemon=True)
                thread.start()
        
        self.send_json({"auto_sync": enabled})
    
    def api_leveling_state(self):
        if leveling_tracker:
            state = leveling_tracker.state
            self.send_json({
                "level": state.level,
                "zone": state.current_zone_name,
                "act": state.current_act,
                "quests": state.completed_quests,
                "next_gem": state.next_gem.name if state.next_gem else None,
                "next_gems": [{"name": g.name, "level": g.level} for g in state.next_gems],
                "next_passive": state.next_passive_node.name if state.next_passive_node else None,
                "lab_trial": state.lab_trial_zone,
                "milestone": state.milestone_reached
            })
        else:
            initialize_tracker()
            self.api_leveling_state()
    
    def api_leveling_recommendations(self):
        if leveling_tracker:
            state = leveling_tracker.state
            self.send_json({
                "next_gems": [{"name": g.name, "level": g.level, "attribute": g.attribute} for g in state.next_gems],
                "next_passives": [{"name": p.name, "stats": p.stats} for p in [state.next_passive_node] if p]
            })
        else:
            self.send_json({"next_gems": [], "next_passives": []})
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def send_html(self, content, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(content.encode())
    
    def log_message(self, format, *args):
        pass

def run_server():
    global api_client, gist_sync
    
    # Try to load existing tokens
    api_client = load_tokens(str(TOKEN_FILE))
    if api_client:
        try:
            profile = api_client.get_profile()
            print(f"✅ Loaded saved tokens for: {profile.get('name')}")
        except:
            api_client = None
            print("⚠️ Saved tokens invalid")
    
    load_character_state()
    initialize_tracker()
    
    # Initialize GistSync if configured
    if GIST_ID and GIST_TOKEN:
        global gist_sync
        gist_sync = GistSync(GIST_ID, GIST_TOKEN, GIST_FILENAME, GIST_SYNC_INTERVAL)
        print(f"📡 GistSync enabled (interval: {GIST_SYNC_INTERVAL}s)")
        # Push initial state
        gist_sync.push(character_state)
    else:
        print("📡 GistSync not configured (set GH_GIST_ID and GH_TOKEN to enable)")
    
    # Start auto-sync if enabled
    if character_state.get("auto_sync"):
        threading.Thread(target=auto_sync_loop, daemon=True).start()
    
    server = HTTPServer(("0.0.0.0", SERVER_PORT), FetchCharacterHandler)
    print(f"""
╔════════════════════════════════════════════════════════════════╗
║     🎮 Fetch Character Server - PoE 3.30 Covens of Umbra      ║
╠════════════════════════════════════════════════════════════════╣
║  Dashboard: http://localhost:{SERVER_PORT}                              ║
║  Remote:    http://<your-ip>:{SERVER_PORT}                              ║
║                                                                ║
║  This server runs on your GAMING MACHINE (where PoE is)       ║
║  View the dashboard from ANY DEVICE on your network           ║
║                                                                ║
║  Features:                                                     ║
║  🔐 OAuth flow with GGG servers                               ║
║  👥 Fetch character list & select character                   ║
║  📥 Import: level, zone, passives, equipment, gems            ║
║  🔄 Auto-sync every 30s (toggleable)                          ║
║  🌳 Leveling tracker integration (passive/gem recommendations)║
║  📡 GistSync: {'ENABLED' if GIST_ID and GIST_TOKEN else 'NOT CONFIGURED'}                                    ║
║                                                                ║
║  Press Ctrl+C to stop                                          ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        server.shutdown()

if __name__ == "__main__":
    run_server()