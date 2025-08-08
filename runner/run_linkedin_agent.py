import argparse
import os
import sys
import time
from pathlib import Path

# Ensure repo root is on sys.path when running as a script
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.linkedin_agent import LinkedInAgent  # noqa: E402
from config import load_env, CDPConfig  # noqa: E402
from vendor.claude_web.browser import start as start_browser  # noqa: E402
import requests  # type: ignore  # noqa: E402


def main():
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--location", default=os.getenv("DEFAULT_LOCATION", "San Francisco Bay Area"))
    parser.add_argument("--limit", type=int, default=int(os.getenv("DEFAULT_SEARCH_LIMIT", "10")))
    parser.add_argument("--approve-outreach", dest="approve_outreach", action="store_true")
    args = parser.parse_args()

    # Ensure Chrome is running with CDP on the configured port; propagate to env for all components
    cdp = CDPConfig()
    os.environ["CHROME_CDP_PORT"] = str(cdp.port)
    # Attach if DevTools is already up; otherwise launch a new Chrome instance
    def _cdp_alive() -> bool:
        try:
            r = requests.get(f"http://localhost:{cdp.port}/json", timeout=0.5)
            return bool(r.ok)
        except Exception:
            return False

    if _cdp_alive():
        print(f"Attaching to existing Chrome on port {cdp.port}")
    else:
        print("Starting Chrome with CDP on port", cdp.port)
        start_browser()
        # Wait for DevTools endpoint to be ready
        for _ in range(50):
            if _cdp_alive():
                break
            time.sleep(0.2)

    agent = LinkedInAgent()
    prompt = (
        f"Open LinkedIn, search for people with '{args.query}' in {args.location}. "
        f"Collect up to {args.limit} candidates. For each, open the profile and call extract_profile. "
        f"Keep actions small and verify URL/location changes."
    )

    try:
        res = agent.call(query=prompt)
        print("Run complete. Steps:")
        steps = getattr(res, "step_history", getattr(res, "steps", []))
        
        if not steps:
            print("No steps recorded - agent may have encountered parsing issues")
            print(f"Result: {res}")
            # Try to run the core functionality directly as fallback
            print("\n Falling back to direct search functionality...")
            from tools.people_search import search_people
            from tools.extract_profile import extract_profile
            from tools.web_nav import go
            
            # Direct search
            search_results = search_people(args.query, args.location, args.limit)
            print(f" Direct search found: {search_results}")
            
            if search_results.get("count", 0) > 0:
                candidates = []
                for i, candidate in enumerate(search_results.get("results", [])[:args.limit]):
                    print(f" Extracting profile {i+1}: {candidate['name']}")
                    go(candidate["url"])
                    profile_data = extract_profile()
                    candidates.append({"search_info": candidate, "profile_details": profile_data})
                
                print(f"\n FALLBACK RESULTS - Found {len(candidates)} candidates:")
                for i, candidate in enumerate(candidates, 1):
                    search_info = candidate["search_info"]
                    profile_info = candidate["profile_details"]
                    print(f"\n--- Candidate {i} ---")
                    print(f"Name: {profile_info.get('name', search_info.get('name', 'N/A'))}")
                    print(f"Title: {profile_info.get('headline', search_info.get('subtitle', 'N/A'))}")
                    print(f"LinkedIn URL: {search_info.get('url', 'N/A')}")
        else:
            for i, s in enumerate(steps, 1):
                print(i, getattr(s, 'thought', getattr(s, 'action', 'step')))
                if getattr(s, 'tool_name', None):
                    print("  ->", s.tool_name, getattr(s, 'tool_args', {}), "=>", (str(getattr(s, 'tool_result', None))[:120] if getattr(s, 'tool_result', None) is not None else None))
                time.sleep(0.1)
    except Exception as e:
        print(f" Agent execution failed: {e}")
        print("\n Falling back to direct functionality...")
        
        # Fallback to direct execution
        from tools.people_search import search_people
        from tools.extract_profile import extract_profile
        from tools.web_nav import go
        
        try:
            search_results = search_people(args.query, args.location, args.limit)
            print(f" Direct search found: {search_results}")
            
            if search_results.get("count", 0) > 0:
                candidates = []
                for i, candidate in enumerate(search_results.get("results", [])[:args.limit]):
                    print(f" Extracting profile {i+1}: {candidate['name']}")
                    go(candidate["url"])
                    profile_data = extract_profile()
                    candidates.append({"search_info": candidate, "profile_details": profile_data})
                
                print(f"\n FALLBACK RESULTS - Found {len(candidates)} candidates:")
                for i, candidate in enumerate(candidates, 1):
                    search_info = candidate["search_info"]
                    profile_info = candidate["profile_details"]
                    print(f"\n--- Candidate {i} ---")
                    print(f"Name: {profile_info.get('name', search_info.get('name', 'N/A'))}")
                    print(f"Title: {profile_info.get('headline', search_info.get('subtitle', 'N/A'))}")
                    print(f"LinkedIn URL: {search_info.get('url', 'N/A')}")
            else:
                print(" No candidates found")
        except Exception as fallback_error:
            print(f" Fallback also failed: {fallback_error}")


if __name__ == "__main__":
    main()
