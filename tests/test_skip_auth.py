#!/usr/bin/env python3
"""Test LinkedIn agent with direct search (skip auth check loop)."""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import load_env, CDPConfig
from vendor.claude_web.browser import start as start_browser
from tools.people_search import search_people
from tools.extract_profile import extract_profile
from tools.web_nav import go

def main():
    load_env()
    cdp = CDPConfig()
    os.environ["CHROME_CDP_PORT"] = str(cdp.port)
    os.environ["HEADLESS_MODE"] = "true"
    
    print("🚀 Testing LinkedIn workflow without auth loop...")
    
    # Step 1: Search for candidates
    print("\n1️⃣ Searching for Software Engineers...")
    search_results = search_people("Software Engineer", "San Francisco Bay Area", 2)
    print(f"Search Results: {search_results}")
    
    if search_results.get("count", 0) == 0:
        print("❌ No search results found. Check authentication or search terms.")
        return
    
    candidates = []
    
    # Step 2: Extract profiles for each candidate
    for i, candidate in enumerate(search_results.get("results", [])[:2]):
        print(f"\n2️⃣ Extracting profile {i+1}: {candidate['name']}")
        
        # Navigate to profile
        profile_url = candidate["url"]
        go(profile_url)
        
        # Extract detailed profile information
        profile_data = extract_profile()
        
        # Combine search + profile data
        full_candidate = {
            "search_info": candidate,
            "profile_details": profile_data,
            "extraction_success": bool(profile_data)
        }
        
        candidates.append(full_candidate)
        print(f"✅ Extracted: {profile_data.get('name', 'N/A')} - {profile_data.get('headline', 'N/A')}")
    
    # Step 3: Final results
    print(f"\n🎯 FINAL RESULTS - Found {len(candidates)} candidates:")
    for i, candidate in enumerate(candidates, 1):
        search_info = candidate["search_info"]
        profile_info = candidate["profile_details"]
        
        print(f"\n--- Candidate {i} ---")
        print(f"Name: {profile_info.get('name', search_info.get('name', 'N/A'))}")
        print(f"Title: {profile_info.get('headline', search_info.get('subtitle', 'N/A'))}")
        print(f"Location: {profile_info.get('location', 'N/A')}")
        print(f"About: {(profile_info.get('about', '') or 'N/A')[:100]}...")
        print(f"Experience: {(profile_info.get('experience', '') or 'N/A')[:100]}...")
        print(f"LinkedIn URL: {search_info.get('url', 'N/A')}")
    
    print(f"\n✅ LinkedIn recruitment workflow completed successfully!")
    return candidates

if __name__ == "__main__":
    results = main()