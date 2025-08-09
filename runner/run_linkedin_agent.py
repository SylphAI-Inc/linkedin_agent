import argparse
import os
import sys
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
from utils.role_prompts import RolePromptBuilder  # noqa: E402
from utils.streaming_handler import AgentProgressTracker  # noqa: E402
import requests  # type: ignore  # noqa: E402
import os 

os.environ["ADALFLOW_DISABLE_TRACING"] = "False"
# ensure this is set before any adalflow imports
from adalflow.tracing import enable_mlflow_local, trace

enable_mlflow_local(
    tracking_uri="http://localhost:8000",
    experiment_name="AdalFlow-Tracing-Demo",
    project_name="Agent-Workflows"
)

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
            "role_type": search_params.get("role_type"),
            "enhanced_prompting": search_params.get("enhanced_prompting", False),
            "streaming_enabled": search_params.get("streaming", False),
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
        f.write(f"Role Type: {search_params.get('role_type', 'auto-detected').replace('_', ' ').title()}\n")
        f.write(f"Enhanced Prompting: {'Yes' if search_params.get('enhanced_prompting') else 'No'}\n")
        f.write(f"Streaming Feedback: {'Yes' if search_params.get('streaming') else 'No'}\n")
        f.write(f"Limit: {search_params['limit']}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Results Found: {len(candidates)}\n\n")
        
        for i, candidate in enumerate(candidates, 1):
            search_info = candidate.get("search_info", {})
            profile_info = candidate.get("profile_details", {})
            
            f.write(f"--- Candidate {i} ---\n")
            # Safe access with type checking
            def safe_get(obj, key, default='N/A'):
                if isinstance(obj, dict):
                    return obj.get(key, default)
                return default
            
            f.write(f"Name: {safe_get(profile_info, 'name', safe_get(search_info, 'name', 'N/A'))}\n")
            f.write(f"Title: {safe_get(profile_info, 'headline', safe_get(search_info, 'subtitle', 'N/A'))}\n")
            f.write(f"Location: {safe_get(profile_info, 'location', 'N/A')}\n")
            f.write(f"Company: {safe_get(profile_info, 'current_company', 'N/A')}\n")
            f.write(f"LinkedIn URL: {safe_get(search_info, 'url', 'N/A')}\n")
            
            about = safe_get(profile_info, 'about')
            if about and about != 'N/A' and isinstance(about, str):
                f.write(f"About: {about[:200]}{'...' if len(about) > 200 else ''}\n")
            
            experience = safe_get(profile_info, 'experience')
            if experience and experience != 'N/A':
                if isinstance(experience, list) and len(experience) > 0:
                    f.write(f"Recent Experience:\n")
                    for exp in experience[:2]:  # Show first 2 experiences
                        if isinstance(exp, dict):
                            f.write(f"  • {safe_get(exp, 'title', 'N/A')} at {safe_get(exp, 'company', 'N/A')}\n")
                elif isinstance(experience, str):
                    # Handle raw text experience data
                    f.write(f"Experience: {experience[:100]}...\n")
            
            f.write("\n")
    
    return {
        "json_file": str(json_file),
        "txt_file": str(txt_file),
        "candidates_count": len(candidates)
    }


def main():
    import time
    load_env()
    parser = argparse.ArgumentParser(description="LinkedIn Recruitment Agent with Role-Specific Targeting")
    parser.add_argument("--query", required=True, help="Job title or role to search for")
    parser.add_argument("--location", default=os.getenv("DEFAULT_LOCATION", "San Francisco Bay Area"), 
                       help="Geographic location for search")
    parser.add_argument("--limit", type=int, default=int(os.getenv("DEFAULT_SEARCH_LIMIT", "10")),
                       help="Maximum number of candidates to extract")
    parser.add_argument("--role-type", choices=list(RolePromptBuilder.ROLE_CONTEXTS.keys()), 
                       help="Specific role type for enhanced targeting (auto-detected if not specified)")
    parser.add_argument("--enhanced-prompting", action="store_true", default=True,
                       help="Use role-specific enhanced prompting (default: True)")
    parser.add_argument("--basic-prompting", dest="enhanced_prompting", action="store_false",
                       help="Use basic prompting instead of enhanced")
    parser.add_argument("--streaming", action="store_true", default=True,
                       help="Enable real-time streaming feedback (default: True)")
    parser.add_argument("--no-streaming", dest="streaming", action="store_false",
                       help="Disable streaming feedback")
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
    
    # Build enhanced or basic prompt based on user preference
    if args.enhanced_prompting:
        print(f"Using enhanced role-specific prompting for: {args.query}")
        prompt = RolePromptBuilder.build_enhanced_prompt(
            base_query=args.query,
            location=args.location,
            limit=args.limit,
            role_type=args.role_type
        )
        
        # Show detected role type
        detected_role = args.role_type or RolePromptBuilder.detect_role_type(args.query)
        print(f"Target role type: {detected_role.replace('_', ' ').title()}")
        
        # Show role-specific focus
        role_instructions = RolePromptBuilder.get_role_specific_instructions(detected_role)
        print(f"Role-specific focus:\n{role_instructions}")
    else:
        print("Using basic prompting")
        prompt = (
            f"Open LinkedIn, search for people with '{args.query}' in {args.location}. "
            f"Collect up to {args.limit} candidates. For each, open the profile and call extract_complete_profile. "
            f"Keep actions small and verify URL/location changes."
        )

    search_params = {
        "query": args.query,
        "location": args.location,
        "limit": args.limit,
        "role_type": args.role_type or RolePromptBuilder.detect_role_type(args.query),
        "enhanced_prompting": args.enhanced_prompting,
        "streaming": args.streaming
    }
    
    # Initialize progress tracking
    if args.streaming:
        progress_tracker = AgentProgressTracker(
            query=args.query,
            location=args.location, 
            limit=args.limit,
            enable_streaming=True
        )
        progress_tracker.start_workflow()
    else:
        progress_tracker = None
    
    candidates = []
    
    with trace(workflow_name="AdalFlow-Agent"):
        try:
            res = agent.call(query=prompt)
            
            if progress_tracker:
                progress_tracker.log_completion(candidates)
            
            # Define steps before conditional block to avoid variable scoping issues
            steps = getattr(res, "step_history", getattr(res, "steps", []))
            
            if not progress_tracker:  # Only show detailed steps if not streaming
                print("Run complete. Steps:")
                
                if not steps:
                    print("No steps recorded - agent may have encountered parsing issues")
                print(f"Result: {res}")
                
                # Check if there's profile data in the final answer
                final_answer = getattr(res, '_answer', getattr(res, 'answer', None))
                if final_answer and 'linkedin.com/in/' in str(final_answer):
                    print("🔍 Found LinkedIn URLs in final answer, attempting to extract...")
                    import re
                    urls = re.findall(r'https://www\.linkedin\.com/in/[^\s\n)]+', str(final_answer))
                    print(f"Found {len(urls)} LinkedIn URLs: {urls}")
                    
                    # For now, we'll use fallback mode to get actual profile data
                
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
                    
                    # Handle Function objects from AdalFlow - check step structure
                    # Steps have: step, action (Function), function (Function), observation
                    action = getattr(s, 'action', None)
                    function = getattr(s, 'function', None)
                    observation = getattr(s, 'observation', None)
                    
                    # Extract tool info from action or function
                    func_obj = action or function
                    if func_obj:
                        tool_name = getattr(func_obj, 'name', None)
                        tool_kwargs = getattr(func_obj, 'kwargs', {})
                        tool_args = getattr(func_obj, 'args', [])
                    else:
                        tool_name = getattr(s, 'name', getattr(s, 'tool_name', None))
                        tool_args = getattr(s, 'args', getattr(s, 'tool_args', []))
                        tool_kwargs = getattr(s, 'kwargs', getattr(s, 'tool_kwargs', {}))
                    
                    tool_result = observation
                    
                    if tool_name:
                        print("  ->", tool_name, tool_kwargs or tool_args, "=>", (str(tool_result)[:120] if tool_result is not None else None))
                        
                        # Collect profile extraction results (both extract_profile and extract_complete_profile)
                        if tool_name in ['extract_profile', 'extract_complete_profile'] and tool_result is not None:
                            profile_data = tool_result
                            
                            # Get the URL from the tool arguments (for extract_complete_profile)
                            linkedin_url = "N/A"
                            if tool_kwargs and tool_kwargs.get('profile_url'):
                                linkedin_url = tool_kwargs['profile_url']
                                # Clean up the URL (remove miniProfileUrn params)
                                if '?miniProfileUrn' in linkedin_url:
                                    linkedin_url = linkedin_url.split('?miniProfileUrn')[0]
                            else:
                                # Fallback: try to get URL from previous navigation steps
                                for prev_step in steps[:i]:
                                    prev_name = getattr(prev_step, 'name', getattr(prev_step, 'tool_name', None))
                                    prev_kwargs = getattr(prev_step, 'kwargs', getattr(prev_step, 'tool_kwargs', {}))
                                    if prev_name == 'go' and 'linkedin.com/in/' in str(prev_kwargs):
                                        linkedin_url = prev_kwargs.get('url', 'N/A')
                            
                            print(f"    🔍 Found profile extraction for: {linkedin_url}")
                            candidates.append({
                                "search_info": {"url": linkedin_url},
                                "profile_details": profile_data
                            })
                    
                    time.sleep(0.1)
                
                print(f"\n📊 Total candidates extracted from agent: {len(candidates)}")
                
                # If no candidates found from tool results, try extracting from final answer
                if len(candidates) == 0:
                    print("🔍 No tool results found, checking final answer...")
                    
                    # Debug: print the full result structure
                    print(f"Result type: {type(res)}")
                    print(f"Result attributes: {[attr for attr in dir(res) if not attr.startswith('_')]}")
                    
                    # Try multiple ways to get the final answer
                    final_answer = None
                    if hasattr(res, 'data') and res.data:
                        if hasattr(res.data, '_answer'):
                            final_answer = res.data._answer
                        elif hasattr(res.data, 'answer'):
                            final_answer = res.data.answer
                    elif hasattr(res, '_answer'):
                        final_answer = res._answer
                    elif hasattr(res, 'answer'):
                        final_answer = res.answer
                    
                    print(f"Final answer found: {final_answer is not None}")
                    if final_answer:
                        print(f"Final answer preview: {str(final_answer)[:200]}...")
                    
                    if final_answer and 'linkedin.com/in/' in str(final_answer):
                        print("🔍 Extracting URLs from final answer...")
                        import re
                        # More precise regex to avoid trailing punctuation
                        urls = re.findall(r'https://www\.linkedin\.com/in/[a-zA-Z0-9\-_]+/?', str(final_answer))
                        # Clean up URLs - remove trailing punctuation
                        cleaned_urls = []
                        for url in urls:
                            cleaned_url = url.rstrip('.,!?":\'')  # Remove trailing punctuation
                            if not cleaned_url.endswith('/'):
                                cleaned_url += '/'
                            cleaned_urls.append(cleaned_url)
                        
                        print(f"Found {len(cleaned_urls)} LinkedIn URLs: {cleaned_urls}")
                        
                        if cleaned_urls:
                            print("📥 Re-extracting profiles using direct functions...")
                            from tools.extract_profile import extract_profile
                            from tools.web_nav import go
                            
                            for i, url in enumerate(cleaned_urls, 1):
                                try:
                                    print(f"  Extracting profile {i}: {url}")
                                    
                                    # Add delay to avoid rate limiting
                                    if i > 1:
                                        time.sleep(2)
                                    
                                    go(url)
                                    time.sleep(1)  # Wait for page load
                                    
                                    # Verify we're on the right page before extracting
                                    from tools.web_nav import get_current_url
                                    current_url = get_current_url()
                                    print(f"    Current URL: {current_url}")
                                    
                                    if '/feed/' in current_url or 'linkedin.com/in/' not in current_url:
                                        print(f"    ⚠️  Redirected away from profile - skipping")
                                        continue
                                    
                                    profile_data = extract_profile()
                                    
                                    # Validate extracted data
                                    if isinstance(profile_data, dict) and profile_data.get('name') != 'feed updates':
                                        candidates.append({
                                            "search_info": {"url": url},
                                            "profile_details": profile_data
                                        })
                                        print(f"    ✅ Successfully extracted: {profile_data.get('name', 'Unknown')}")
                                    else:
                                        print(f"    ⚠️  Invalid profile data - skipping")
                                        
                                except Exception as e:
                                    print(f"    ❌ Failed to extract profile {i}: {e}")
                            
                            print(f"📊 Successfully re-extracted {len(candidates)} candidates from URLs")
                    else:
                        print("❌ No LinkedIn URLs found in final answer")
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
