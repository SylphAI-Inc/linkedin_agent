import argparse
import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path

# Ensure repo root is on sys.path when running as a script
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.linkedin_agent import LinkedInAgent  # noqa: E402
from config import load_env, CDPConfig  # noqa: E402
from vendor.claude_web.browser import start as start_browser  # noqa: E402
import requests  # type: ignore  # noqa: E402


def save_results(candidates, search_params, output_dir="results"):
    """Save search results to files"""
    # Create results directory
    results_dir = REPO_ROOT / output_dir
    results_dir.mkdir(exist_ok=True)
    
    # Generate timestamp for unique filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    query_clean = search_params["query"].replace(" ", "_").replace("/", "_")[:30]
    
    # Save detailed JSON results
    json_file = results_dir / f"linkedin_search_{query_clean}_{timestamp}.json"
    
    detailed_results = {
        "search_metadata": {
            "timestamp": datetime.now().isoformat(),
            "query": search_params["query"],
            "location": search_params["location"], 
            "limit": search_params["limit"],
            "total_found": len(candidates)
        },
        "candidates": candidates
    }
    
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(detailed_results, f, indent=2, ensure_ascii=False)
    
    # Save human-readable summary
    txt_file = results_dir / f"linkedin_summary_{query_clean}_{timestamp}.txt"
    
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(f"LinkedIn Search Results\n")
        f.write(f"=" * 50 + "\n\n")
        f.write(f"Search Query: {search_params['query']}\n")
        f.write(f"Location: {search_params['location']}\n")
        f.write(f"Limit: {search_params['limit']}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Results Found: {len(candidates)}\n\n")
        
        for i, candidate in enumerate(candidates, 1):
            search_info = candidate.get("search_info", {})
            profile_info = candidate.get("profile_details", {})
            
            f.write(f"--- Candidate {i} ---\n")
            f.write(f"Name: {profile_info.get('name', search_info.get('name', 'N/A'))}\n")
            f.write(f"Title: {profile_info.get('headline', search_info.get('subtitle', 'N/A'))}\n")
            f.write(f"Location: {profile_info.get('location', 'N/A')}\n")
            f.write(f"Company: {profile_info.get('current_company', 'N/A')}\n")
            f.write(f"LinkedIn URL: {search_info.get('url', 'N/A')}\n")
            
            if profile_info.get('about'):
                f.write(f"About: {profile_info['about'][:200]}{'...' if len(profile_info.get('about', '')) > 200 else ''}\n")
            
            if profile_info.get('experience') and len(profile_info['experience']) > 0:
                f.write(f"Recent Experience:\n")
                for exp in profile_info['experience'][:2]:  # Show first 2 experiences
                    f.write(f"  • {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')}\n")
            
            f.write("\n")
    
    return {
        "json_file": str(json_file),
        "txt_file": str(txt_file),
        "candidates_count": len(candidates)
    }


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

    search_params = {
        "query": args.query,
        "location": args.location,
        "limit": args.limit
    }
    
    candidates = []
    
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
            # Extract candidates from agent steps
            for i, s in enumerate(steps, 1):
                print(i, getattr(s, 'thought', getattr(s, 'action', 'step')))
                if getattr(s, 'tool_name', None):
                    print("  ->", s.tool_name, getattr(s, 'tool_args', {}), "=>", (str(getattr(s, 'tool_result', None))[:120] if getattr(s, 'tool_result', None) is not None else None))
                    
                    # Collect profile extraction results
                    if s.tool_name == 'extract_profile' and getattr(s, 'tool_result', None):
                        profile_data = s.tool_result
                        # Try to get the URL from previous navigation steps
                        linkedin_url = "N/A"
                        for prev_step in steps[:i]:
                            if getattr(prev_step, 'tool_name', None) == 'go' and 'linkedin.com/in/' in str(getattr(prev_step, 'tool_args', {})):
                                linkedin_url = getattr(prev_step, 'tool_args', {}).get('url', 'N/A')
                        
                        candidates.append({
                            "search_info": {"url": linkedin_url},
                            "profile_details": profile_data
                        })
                
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
    
    # Save results if we found any candidates
    if candidates:
        try:
            save_info = save_results(candidates, search_params)
            print(f"\n RESULTS SAVED:")
            print(f"📄 Detailed JSON: {save_info['json_file']}")
            print(f"📝 Summary: {save_info['txt_file']}")
            print(f"👥 Total candidates: {save_info['candidates_count']}")
        except Exception as save_error:
            print(f"\n⚠️  Failed to save results: {save_error}")
    else:
        print(f"\n❌ No candidates found to save")


if __name__ == "__main__":
    main()
