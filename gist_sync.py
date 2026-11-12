#!/usr/bin/env python3
"""
GitHub Gist Sync for PoE Character State
=========================================
Pushes character state to a secret GitHub Gist for cross-device dashboard access.
"""

import os
import json
import time
import threading
import requests
from pathlib import Path
from typing import Optional, Dict, Any

class GistSync:
    """Syncs character state to a GitHub Gist."""
    
    def __init__(
        self,
        gist_id: str,
        token: str,
        filename: str = "character_state.json",
        sync_interval: int = 30
    ):
        self.gist_id = gist_id
        self.token = token
        self.filename = filename
        self.sync_interval = sync_interval
        self.api_url = f"https://api.github.com/gists/{gist_id}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        self._stop_event = threading.Event()
        self._sync_thread: Optional[threading.Thread] = None
        self._last_synced_content = ""
    
    def push(self, state: Dict[str, Any]) -> bool:
        """Push state to Gist."""
        try:
            content = json.dumps(state, indent=2)
            
            # Skip if content unchanged
            if content == self._last_synced_content:
                return True
            
            payload = {
                "files": {
                    self.filename: {
                        "content": content
                    }
                }
            }
            
            response = requests.patch(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self._last_synced_content = content
                return True
            else:
                print(f"Gist push failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Gist push error: {e}")
            return False
    
    def pull(self) -> Optional[Dict[str, Any]]:
        """Pull state from Gist."""
        try:
            response = requests.get(self.api_url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                file_data = data.get("files", {}).get(self.filename)
                if file_data and "content" in file_data:
                    return json.loads(file_data["content"])
            elif response.status_code == 404:
                print("Gist not found - check GIST_ID")
            else:
                print(f"Gist pull failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Gist pull error: {e}")
        
        return None
    
    def start_auto_sync(self, state_getter):
        """Start background auto-sync thread."""
        self._stop_event.clear()
        self._sync_thread = threading.Thread(
            target=self._auto_sync_loop,
            args=(state_getter,),
            daemon=True
        )
        self._sync_thread.start()
        print(f"✅ Gist auto-sync started (interval: {self.sync_interval}s)")
    
    def stop_auto_sync(self):
        """Stop background auto-sync."""
        self._stop_event.set()
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
        print("⏹️ Gist auto-sync stopped")
    
    def _auto_sync_loop(self, state_getter):
        """Background loop that pushes state to Gist."""
        while not self._stop_event.is_set():
            time.sleep(self.sync_interval)
            if not self._stop_event.is_set():
                state = state_getter()
                if state:
                    self.push(state)

def create_gist(token: str, filename: str = "character_state.json", description: str = "PoE Character State Sync") -> Optional[str]:
    """Create a new secret Gist and return its ID."""
    try:
        payload = {
            "description": description,
            "public": False,
            "files": {
                filename: {
                    "content": json.dumps({}, indent=2)
                }
            }
        }
        
        response = requests.post(
            "https://api.github.com/gists",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=10
        )
        
        if response.status_code == 201:
            gist_id = response.json()["id"]
            print(f"✅ Created Gist: {gist_id}")
            print(f"   URL: https://gist.github.com/{gist_id}")
            return gist_id
        else:
            print(f"Gist creation failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Gist creation error: {e}")
    
    return None

# For direct execution
if __name__ == "__main__":
    import sys
    
    token = os.environ.get("GH_TOKEN")
    if not token:
        print("Set GH_TOKEN environment variable")
        sys.exit(1)
    
    if len(sys.argv) > 1 and sys.argv[1] == "create":
        gist_id = create_gist(token)
        if gist_id:
            print(f"\nAdd to your environment:")
            print(f"export GH_GIST_ID={gist_id}")
            print(f"export GH_TOKEN={token}")
    else:
        print("Usage: python3 gist_sync.py create")