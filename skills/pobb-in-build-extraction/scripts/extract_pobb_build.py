#!/usr/bin/env python3
"""
Extract PoB build from pobb.in share link.
"""
import re
import base64
import zlib
import requests

def extract_pobb_build(pobb_url: str, out_build: str, out_json: str = None) -> bytes:
    """
    Extract PoB build from pobb.in link.
    
    Args:
        pobb_url: e.g., 'https://pobb.in/YFaTC_ulBFvf'
        out_build: Output .build file path
        out_json: Optional output .json file path (uses pob_collab.export_build)
    
    Returns:
        Raw XML bytes of the .build file
    """
    html = requests.get(pobb_url, timeout=30).text
    
    # Find the eNrt... base64url-encoded zlib stream
    match = re.search(r'eNrt[A-Za-z0-9+/=_-]{100,}', html)
    if not match:
        raise ValueError("Buildcode not found in pobb.in page. Check if the link is valid.")
    
    buildcode = match.group()
    
    # Convert base64url -> standard base64
    buildcode_std = buildcode.replace('-', '+').replace('_', '/')
    padding = 4 - (len(buildcode_std) % 4)
    if padding != 4:
        buildcode_std += '=' * padding
    
    # Decode and decompress
    decoded = base64.b64decode(buildcode_std)
    xml = zlib.decompress(decoded)  # PoB .build XML
    
    # Save .build
    with open(out_build, 'wb') as f:
        f.write(xml)
    
    # Optional: export to JSON for agent collaboration
    if out_json:
        try:
            from pob_collab import export_build
            export_build(out_build, out_json)
        except ImportError:
            # pob_collab not available - run from PoB repo directory
            pass
    
    return xml

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: extract_pobb_build.py <pobb.in_url> <output.build> [output.json]")
        sys.exit(1)
    
    url = sys.argv[1]
    out_build = sys.argv[2]
    out_json = sys.argv[3] if len(sys.argv) > 3 else None
    
    xml = extract_pobb_build(url, out_build, out_json)
    print(f"Extracted {len(xml)} bytes to {out_build}")
    if out_json:
        print(f"Exported JSON to {out_json}")