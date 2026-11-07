#!/usr/bin/env python3
"""
Path of Building OAuth Character Import
========================================
Implements the OAuth2 flow used by PoB to authenticate with Path of Exile
and fetch character data via the official API.

Based on: src/Classes/PoEAPI.lua and src/LaunchServer.lua from PoB repo
"""

import base64
import hashlib
import json
import os
import secrets
import time
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Optional, Dict, Any
import requests


# PoB's OAuth client ID (public)
CLIENT_ID = "pob"

# Required scopes for character import
SCOPES = [
    "account:profile",
    "account:leagues",
    "account:characters",
    "account:trade"
]

# API endpoints
OAUTH_AUTHORIZE_URL = "https://www.pathofexile.com/oauth/authorize"
OAUTH_TOKEN_URL = "https://www.pathofexile.com/oauth/token"
API_BASE_URL = "https://api.pathofexile.com"

# Local callback server port range (same as PoB)
CALLBACK_PORTS = [49082, 49083, 49084]
CALLBACK_TIMEOUT = 60  # seconds


def generate_pkce_pair() -> tuple[str, str]:
    """
    Generate PKCE code_verifier and code_challenge (S256 method).
    PoB uses base64url encoding without padding.
    """
    # Generate random secret (32-bit in PoB, we use 256-bit for better security)
    secret = secrets.token_bytes(32)
    code_verifier = base64.urlsafe_b64encode(secret).decode().rstrip('=')
    
    # code_challenge = base64url(sha256(code_verifier))
    challenge_bytes = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode().rstrip('=')
    
    return code_verifier, code_challenge


def generate_state() -> str:
    """Generate 16-char hex state string for CSRF protection."""
    return secrets.token_hex(8)


def build_authorize_url(code_challenge: str, state: str, redirect_uri: str) -> str:
    """Build the OAuth authorization URL."""
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "redirect_uri": redirect_uri,
    }
    return f"{OAUTH_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""
    
    def __init__(self, *args, callback_data: dict, **kwargs):
        self.callback_data = callback_data
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        
        if "code" in query:
            self.callback_data["code"] = query["code"][0]
            self.callback_data["state"] = query.get("state", [None])[0]
            self._send_success()
        else:
            self.callback_data["error"] = query.get("error", ["unknown"])[0]
            self.callback_data["error_description"] = query.get("error_description", [""])[0]
            self._send_failure()
    
    def _send_success(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        html = """
        <!DOCTYPE html><html><head><title>PoB - Authentication Complete</title>
        <style>body{font-family:Arial;background:#121212;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
        .card{background:#1E1E1E;padding:20px;border-radius:10px;text-align:center;max-width:400px}
        h1{color:#4CAF50}</style></head>
        <body><div class="card"><h1>Authentication Successful</h1>
        <p>✅ You can now return to the app.</p></div></body></html>
        """
        self.wfile.write(html.encode())
    
    def _send_failure(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        error = self.callback_data.get("error", "unknown")
        desc = self.callback_data.get("error_description", "")
        html = f"""
        <!DOCTYPE html><html><head><title>PoB - Authentication Failed</title>
        <style>body{{font-family:Arial;background:#121212;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}}
        .card{{background:#1E1E1E;padding:20px;border-radius:10px;text-align:center;max-width:400px}}
        h1{{color:#f44336}} code{{background:#f8d7da;color:#721c24;padding:3px 6px;border-radius:4px}}</style></head>
        <body><div class="card"><h1>Authentication Failed</h1>
        <p>❌ Please try again.</p><code>{error}: {desc}</code></div></body></html>
        """
        self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        pass  # Suppress default logging


def start_callback_server(port: int, callback_data: dict) -> HTTPServer:
    """Start local HTTP server to receive OAuth callback."""
    def handler(*args, **kwargs):
        return OAuthCallbackHandler(*args, callback_data=callback_data, **kwargs)
    
    server = HTTPServer(("localhost", port), handler)
    return server


def exchange_code_for_tokens(code: str, code_verifier: str, redirect_uri: str) -> Dict[str, Any]:
    """Exchange authorization code for access/refresh tokens."""
    data = {
        "client_id": CLIENT_ID,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "scope": " ".join(SCOPES),
        "code_verifier": code_verifier,
    }
    
    response = requests.post(OAUTH_TOKEN_URL, data=data, timeout=30)
    response.raise_for_status()
    return response.json()


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """Refresh expired access token."""
    data = {
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    
    response = requests.post(OAUTH_TOKEN_URL, data=data, timeout=30)
    response.raise_for_status()
    return response.json()


class PoEAPIClient:
    """Client for Path of Exile OAuth API."""
    
    def __init__(self, access_token: str = None, refresh_token: str = None, token_expiry: int = 0):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = token_expiry
        self.session = requests.Session()
    
    def _ensure_valid_token(self) -> bool:
        """Ensure we have a valid access token, refresh if needed."""
        if not self.access_token or not self.refresh_token:
            return False
        
        if self.token_expiry > time.time() + 60:  # 60s buffer
            return True
        
        # Refresh token
        try:
            tokens = refresh_access_token(self.refresh_token)
            self.access_token = tokens["access_token"]
            self.refresh_token = tokens["refresh_token"]
            self.token_expiry = int(time.time()) + tokens["expires_in"]
            return True
        except Exception as e:
            print(f"Token refresh failed: {e}")
            self.access_token = None
            self.refresh_token = None
            self.token_expiry = 0
            return False
    
    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make authenticated API request with auto-refresh."""
        if not self._ensure_valid_token():
            raise Exception("Not authenticated")
        
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        
        url = f"{API_BASE_URL}{endpoint}"
        response = self.session.request(method, url, headers=headers, **kwargs)
        
        # Handle 401 with one retry after refresh
        if response.status_code == 401 and self.refresh_token:
            if self._ensure_valid_token():
                headers["Authorization"] = f"Bearer {self.access_token}"
                response = self.session.request(method, url, headers=headers, **kwargs)
        
        return response
    
    def get_character_list(self, realm: str = "pc") -> Dict[str, Any]:
        """Get list of characters for the authenticated account."""
        realm_path = "" if realm == "pc" else f"/{realm}"
        response = self._request("GET", f"/character{realm_path}")
        response.raise_for_status()
        return response.json()
    
    def get_character(self, name: str, realm: str = "pc") -> Optional[Dict[str, Any]]:
        """Get full character data (passives, equipment, inventory, etc.)."""
        realm_path = "" if realm == "pc" else f"/{realm}"
        response = self._request("GET", f"/character{realm_path}/{urllib.parse.quote(name)}")
        
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json().get("character")
    
    def get_profile(self) -> Dict[str, Any]:
        """Get account profile."""
        response = self._request("GET", "/profile")
        response.raise_for_status()
        return response.json()


def run_oauth_flow() -> PoEAPIClient:
    """
    Run the complete OAuth flow:
    1. Generate PKCE pair
    2. Start local callback server
    3. Open browser to authorization URL
    4. Wait for callback with authorization code
    5. Exchange code for tokens
    6. Return authenticated API client
    """
    print("🔐 Starting PoE OAuth flow...")
    
    # Generate PKCE
    code_verifier, code_challenge = generate_pkce_pair()
    state = generate_state()
    
    # Start callback server
    callback_data = {}
    server = None
    port = None
    
    for p in CALLBACK_PORTS:
        try:
            server = start_callback_server(p, callback_data)
            port = p
            break
        except OSError:
            continue
    
    if not server:
        raise Exception("Could not start callback server on any port")
    
    redirect_uri = f"http://localhost:{port}"
    auth_url = build_authorize_url(code_challenge, state, redirect_uri)
    
    print(f"📋 Authorization URL copied to clipboard (also opening in browser)")
    print(f"🌐 URL: {auth_url}")
    
    # Try to open in browser
    try:
        import webbrowser
        webbrowser.open(auth_url)
    except:
        pass
    
    # Run server in background thread
    server_thread = Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for callback
    print("⏳ Waiting for authorization (60s timeout)...")
    start_time = time.time()
    while time.time() - start_time < CALLBACK_TIMEOUT:
        if "code" in callback_data or "error" in callback_data:
            break
        time.sleep(0.5)
    
    server.shutdown()
    server.server_close()
    
    if "error" in callback_data:
        raise Exception(f"OAuth failed: {callback_data['error']} - {callback_data.get('error_description', '')}")
    
    if "code" not in callback_data:
        raise Exception("Timeout: No callback received")
    
    if callback_data.get("state") != state:
        raise Exception("OAuth state mismatch - possible CSRF attack")
    
    print("✅ Authorization code received, exchanging for tokens...")
    
    # Exchange code for tokens
    tokens = exchange_code_for_tokens(
        callback_data["code"],
        code_verifier,
        redirect_uri
    )
    
    client = PoEAPIClient(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_expiry=int(time.time()) + tokens["expires_in"]
    )
    
    print("🎉 OAuth complete! You're now authenticated.")
    return client


def save_tokens(client: PoEAPIClient, filepath: str = "poe_tokens.json"):
    """Save tokens to file for reuse."""
    data = {
        "access_token": client.access_token,
        "refresh_token": client.refresh_token,
        "token_expiry": client.token_expiry,
    }
    with open(filepath, "w") as f:
        json.dump(data, f)
    print(f"💾 Tokens saved to {filepath}")


def load_tokens(filepath: str = "poe_tokens.json") -> Optional[PoEAPIClient]:
    """Load tokens from file."""
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, "r") as f:
        data = json.load(f)
    
    # Check if token is still valid (or can be refreshed)
    if data.get("token_expiry", 0) < time.time() and not data.get("refresh_token"):
        return None
    
    return PoEAPIClient(
        access_token=data.get("access_token"),
        refresh_token=data.get("refresh_token"),
        token_expiry=data.get("token_expiry", 0)
    )


# ============================================================
# Example usage
# ============================================================

if __name__ == "__main__":
    import sys
    
    # Try to load existing tokens first
    client = load_tokens()
    
    if not client:
        print("No valid saved tokens found. Starting OAuth flow...")
        client = run_oauth_flow()
        save_tokens(client)
    else:
        print("✅ Using saved tokens")
        # Validate by fetching profile
        try:
            profile = client.get_profile()
            print(f"👤 Authenticated as: {profile.get('name')}")
        except Exception as e:
            print(f"⚠️ Saved tokens invalid: {e}")
            client = run_oauth_flow()
            save_tokens(client)
    
    # Fetch character list
    print("\n📋 Fetching character list...")
    char_list = client.get_character_list()
    characters = char_list.get("characters", [])
    
    if not characters:
        print("No characters found.")
        sys.exit(0)
    
    print(f"\nFound {len(characters)} character(s):")
    for i, char in enumerate(characters):
        print(f"  {i+1}. {char['name']} (Level {char['level']} {char['class']}) - {char.get('league', 'Unknown')}")
    
    # Let user select character
    try:
        choice = int(input("\nSelect character number (or 0 to exit): ")) - 1
        if choice < 0 or choice >= len(characters):
            sys.exit(0)
    except (ValueError, KeyboardInterrupt):
        sys.exit(0)
    
    selected = characters[choice]
    print(f"\n📥 Fetching full data for {selected['name']}...")
    
    character = client.get_character(selected["name"])
    if not character:
        print("Character not found.")
        sys.exit(1)
    
    # Display key info
    print(f"\n📊 Character: {character['name']}")
    print(f"   Class: {character['class']} (Level {character['level']})")
    print(f"   League: {character.get('league', 'Unknown')}")
    print(f"   Ascendancy: {character.get('ascendancy', 'None')}")
    
    # Passive tree info
    passives = character.get("passives", {})
    if passives:
        hashes = passives.get("hashes", [])
        print(f"   Passive nodes allocated: {len(hashes)}")
    
    # Equipment
    equipment = character.get("equipment", [])
    if equipment:
        print(f"   Equipment slots filled: {len(equipment)}")
        for item in equipment[:5]:  # Show first 5
            print(f"     - {item.get('inventoryId', 'Unknown')}: {item.get('name', 'Unidentified')}")
    
    # Save full character data
    output_file = f"{selected['name']}_character.json"
    with open(output_file, "w") as f:
        json.dump(character, f, indent=2)
    print(f"\n💾 Full character data saved to {output_file}")
    print("   You can now convert this to a PoB build using pob_collab.py")