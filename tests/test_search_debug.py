#!/usr/bin/env python3
"""Debug script to test search functionality step by step."""

import os
import time
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).resolve().parent
import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import load_env, CDPConfig
from vendor.claude_web.tools.web_tool import WebTool
from tools.people_search import search_people

def main():
    load_env()
    cdp = CDPConfig()
    os.environ["CHROME_CDP_PORT"] = str(cdp.port)
    os.environ["HEADLESS_MODE"] = "true"
    
    print(f"Using CDP port: {cdp.port}")
    
    # Initialize WebTool
    w = WebTool(port=cdp.port)
    try:
        w.connect()
        print("✓ WebTool connected successfully")
    except Exception as e:
        print(f"✗ WebTool connection failed: {e}")
        return
    
    # Test basic navigation
    try:
        w.go("https://www.linkedin.com")
        title = w.js("document.title")
        print(f"✓ LinkedIn loaded: {title}")
        
        # Check if we need to login
        body_text = w.js("document.body.innerText")[:200]
        print(f"Page content preview: {body_text}...")
        
        if "sign in" in body_text.lower() or "log in" in body_text.lower():
            print("⚠ LinkedIn requires authentication")
            print("This is likely why the agent gets stuck - it can't search without login")
            
        # Test search with improved error handling
        print("\n🔍 Testing improved search functionality...")
        result = search_people("Software Engineer", "San Francisco Bay Area", 2)
        print(f"Search result: {result}")
        
        if result.get("auth_required"):
            print("✓ Correctly detected authentication requirement")
        elif result.get("error"):
            print(f"✓ Provided helpful error message: {result['error']}")
        else:
            print(f"✓ Found {result['count']} results")
        
    except Exception as e:
        print(f"✗ Navigation/search failed: {e}")
    finally:
        w.close()

if __name__ == "__main__":
    main()