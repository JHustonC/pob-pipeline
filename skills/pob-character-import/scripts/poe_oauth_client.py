#!/usr/bin/env python3
"""
Path of Exile OAuth2 client for Path of Building.
Implements the exact OAuth flow used by PoB (PKCE S256, local callback server).
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
from typing import Dict, Any, Optional
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
TOKEN_FILE = "poe_tokens.json"


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256 method)."""
    secret = secrets.token_bytes(32)
    code_verifier = base64.urlsafe_b64encode(secret).decode().rstrip('=')
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
        html = """<!DOCTYPE html><html><head><title>PoB - Authentication Complete</title>
        <style>body{font-family:Arial;background:#121212;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
        .card{background:#1E1E1E;padding:20px;border-radius:10px;text-align:center;max-width:400px}
        h1{color:#4CAF50}</style></head>
        <body><div class="card"><h1>Authentication Successful</h1>
        <p>You can now return to the app.</p></div></body></html>"""
        self.wfile.write(html.encode())
    
    def _send_failure(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        error = self.callback_data.get("error", "unknown")
        desc = self.callback_data.get("error_description", "")
        html = f"""<!DOCTYPE html><html><head><title>PoB - Authentication Failed</title>
        <style>body{{font-family:Arial;background:#121212;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}}
        .card{{background:#1E1E1E;padding:20px;border-radius:10px;text-align:center;max-width:400px}}
        h1{{color:#f44336}} code{{background:#f8d7da;color:#721c24;padding:3px 6px;border-radius:4px}}</style></head>
        <body><div class="card"><h1>Authentication Failed</h1>
        <p>Please try again.</p><code>{error}: {desc}</code></div></body></html>"""
        self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        pass


def start_callback_server(port: int, callback_data: dict) -> HTTPServer:
    """Start local HTTP server to receive OAuth callback."""
    def handler(*args, **kwargs):
        return OAuthCallbackHandler(*args, callback_data=callback_data, **kwargs)
    return HTTPServer(("localhost", port), handler)


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


def save_tokens(tokens: Dict[str, Any], filepath: str = TOKEN_FILE):
    """Save tokens to file for reuse."""
    data = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_expiry": int(time.time()) + tokens["expires_in"],
    }
    with open(filepath, "w") as f:
        json.dump(data, f)


def load_tokens(filepath: str = TOKEN_FILE) -> Optional[Dict[str, Any]]:
    """Load tokens from file."""
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r") as f:
        return json.load(f)


class PoEAPIClient:
    """Client for Path of Exile OAuth API."""
    
    def __init__(self, tokens: Dict[str, Any]):
        self.access_token = tokens.get("access_token")
        self.refresh_token = tokens.get("refresh_token")
        self.token_expiry = tokens.get("token_expiry", 0)
        self.session = requests.Session()
    
    def _ensure_valid_token(self) -> bool:
        """Ensure we have a valid access token, refresh if needed."""
        if not self.access_token or not self.refresh_token:
            return False
        if self.token_expiry > time.time() + 60:
            return True
        try:
            tokens = refresh_access_token(self.refresh_token)
            self.access_token = tokens["access_token"]
            self.refresh_token = tokens["refresh_token"]
            self.token_expiry = int(time.time()) + tokens["expires_in"]
            save_tokens({
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "token_expiry": self.token_expiry
            })
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
    """Run the complete OAuth flow and return authenticated client."""
    print("Starting PoE OAuth flow...")
    code_verifier, code_challenge = generate_pkce_pair()
    state = generate_state()
    
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
    
    print(f"Authorization URL: {auth_url}")
    try:
        import webbrowser
        webbrowser.open(auth_url)
    except:
        pass
    
    server_thread = Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    print("Waiting for authorization (60s timeout)...")
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
    
    print("Exchanging code for tokens...")
    tokens = exchange_code_for_tokens(callback_data["code"], code_verifier, redirect_uri)
    save_tokens(tokens)
    
    return PoEAPIClient(tokens)


def get_client() -> PoEAPIClient:
    """Get authenticated client, running OAuth flow if needed."""
    tokens = load_tokens()
    if not tokens:
        return run_oauth_flow()
    client = PoEAPIClient(tokens)
    try:
        client.get_profile()
        return client
    except Exception:
        return run_oauth_flow()


if __name__ == "__main__":
    client = get_client()
    profile = client.get_profile()
    print(f"Authenticated as: {profile.get('name')}")
    
    chars = client.get_character_list()
    for i, c in enumerate(chars.get("characters", [])):
        print(f"  {i+1}. {c['name']} (Lv{c['level']} {c['class']}) - {c.get('league', 'Unknown')}")