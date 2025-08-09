#!/usr/bin/env python3
"""
Clean LinkedIn Recruitment Runner
Simplified, modular approach with clear separation of concerns
"""
import argparse
import os
import sys
import time
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import load_env, CDPConfig
from vendor.claude_web.browser import start as start_browser
from utils.streaming_handler import AgentProgressTracker
from runner.workflow_manager import LinkedInWorkflowManager
import requests


def setup_chrome_cdp():
    """Setup Chrome DevTools Protocol connection"""
    load_env()
    cdp = CDPConfig()
    os.environ["CHROME_CDP_PORT"] = str(cdp.port)
    
    def _cdp_alive() -> bool:
        try:
            r = requests.get(f"http://localhost:{cdp.port}/json", timeout=0.5)
            return bool(r.ok)
        except Exception:
            return False

    if _cdp_alive():
        print(f"✅ Attaching to existing Chrome on port {cdp.port}")
    else:
        print(f"🚀 Starting Chrome with CDP on port {cdp.port}")
        start_browser()
        # Wait for DevTools endpoint to be ready
        for _ in range(50):
            if _cdp_alive():
                break
            time.sleep(0.2)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="LinkedIn Recruitment Agent - Clean Architecture")
    
    # Required arguments
    parser.add_argument("--query", required=True, 
                       help="Job title or role to search for")
    parser.add_argument("--location", 
                       default=os.getenv("DEFAULT_LOCATION", "San Francisco Bay Area"),
                       help="Geographic location for search")
    parser.add_argument("--limit", type=int, 
                       default=int(os.getenv("DEFAULT_SEARCH_LIMIT", "10")),
                       help="Maximum number of candidates to extract")
    
    # Optional features
    parser.add_argument("--role-type", 
                       choices=['software_engineer', 'product_manager', 'sales_executive', 
                               'marketing_manager', 'data_scientist', 'designer'],
                       help="Specific role type for enhanced targeting")
    parser.add_argument("--enhanced-prompting", action="store_true", default=True,
                       help="Use role-specific enhanced prompting (default: True)")
    parser.add_argument("--basic-prompting", dest="enhanced_prompting", action="store_false",
                       help="Use basic prompting instead of enhanced")
    parser.add_argument("--streaming", action="store_true", default=True,
                       help="Enable real-time streaming feedback (default: True)")
    parser.add_argument("--no-streaming", dest="streaming", action="store_false",
                       help="Disable streaming feedback")
    
    return parser.parse_args()


def main():
    """Main execution function - clean and focused"""
    print("🎯 LinkedIn Recruitment Agent - Starting...")
    
    # 1. Parse arguments and setup
    args = parse_arguments()
    setup_chrome_cdp()
    
    # 2. Initialize workflow manager
    workflow = LinkedInWorkflowManager(
        query=args.query,
        location=args.location,
        limit=args.limit,
        role_type=args.role_type,
        enhanced_prompting=args.enhanced_prompting,
        streaming=args.streaming
    )
    
    # 3. Create recruitment strategy
    print("\n" + "="*60)
    print("STEP 1: STRATEGY CREATION")
    print("="*60)
    
    strategy = workflow.create_recruitment_strategy()
    if strategy.get('fallback_strategy'):
        print("⚠️  Using fallback strategy (LLM unavailable)")
    else:
        print("✅ AI-powered strategy created")
        print(f"🎯 Focus areas: {', '.join(strategy.get('profile_evaluation_context', {}).get('focus_areas', []))}")
    
    # 4. Setup progress tracking
    progress_tracker = None
    if args.streaming:
        progress_tracker = AgentProgressTracker(
            query=args.query,
            location=args.location,
            limit=args.limit,
            enable_streaming=True
        )
    
    # 5. Execute recruitment workflow
    print("\n" + "="*60)
    print("STEP 2: RECRUITMENT EXECUTION")
    print("="*60)
    
    # Enable AdalFlow tracing
    os.environ["ADALFLOW_DISABLE_TRACING"] = "False"
    from adalflow.tracing import enable_mlflow_local, trace
    
    try:
        enable_mlflow_local(
            tracking_uri="http://localhost:8000",
            experiment_name="LinkedIn-Recruitment-Workflow",
            project_name="Clean-Agent-Architecture"
        )
    except:
        print("ℹ️  MLflow tracing not available")
    
    candidates = []
    
    with trace(workflow_name="LinkedIn-Recruitment"):
        candidates = workflow.execute_search_workflow(progress_tracker)
    
    # 6. Save and display results
    print("\n" + "="*60)
    print("STEP 3: RESULTS & SUMMARY")
    print("="*60)
    
    if candidates:
        try:
            save_info = workflow.save_results(candidates)
            print(f"💾 RESULTS SAVED:")
            print(f"📄 Detailed JSON: {save_info['json_file']}")
            print(f"📝 Summary Report: {save_info['txt_file']}")
            print(f"👥 Total Candidates: {save_info['candidates_count']}")
            
            # Display summary
            print(f"\n🎉 RECRUITMENT SUMMARY:")
            print(f"   Query: {args.query}")
            print(f"   Location: {args.location}")
            print(f"   Found: {len(candidates)}/{args.limit} candidates")
            print(f"   Strategy: {'AI-Enhanced' if not strategy.get('fallback_strategy') else 'Fallback'}")
            
            # Show top candidates
            print(f"\n📋 TOP CANDIDATES:")
            for i, candidate in enumerate(candidates[:3], 1):
                profile = candidate.get("profile_details", {})
                name = profile.get("name", "Unknown")
                title = profile.get("headline", "No title")
                quality = profile.get("data_quality", {})
                completeness = quality.get("completeness_percentage", "N/A")
                
                print(f"   {i}. {name}")
                print(f"      Title: {title}")
                print(f"      Completeness: {completeness}%")
            
        except Exception as save_error:
            print(f"⚠️  Failed to save results: {save_error}")
            print(f"📊 Found {len(candidates)} candidates (unsaved)")
    else:
        print("❌ No candidates found")
        print("💡 Try adjusting your search criteria or location")
    
    print(f"\n✅ Recruitment workflow completed!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Workflow interrupted by user")
    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        import traceback
        traceback.print_exc()