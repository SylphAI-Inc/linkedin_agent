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
from utils.logger import init_logging, get_logger, log_info, log_error, log_debug, log_phase_start, log_phase_end

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
        log_info(f"Attaching to existing Chrome on port {cdp.port}", phase="initialization")
    else:
        log_info(f"Starting Chrome with CDP on port {cdp.port}", phase="initialization")
        start_browser()
        # Wait for DevTools endpoint to be ready
        for _ in range(50):
            if _cdp_alive():
                break
            time.sleep(0.2)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="LinkedIn Recruitment Agent - Clean Architecture")
    
    # Core arguments (query can be optional if job description provided)
    parser.add_argument("--query", 
                       help="Job title or role to search for (required unless --job-description provided)")
    parser.add_argument("--location", 
                       default=os.getenv("DEFAULT_LOCATION", "San Francisco Bay Area"),
                       help="Geographic location for search")
    parser.add_argument("--limit", type=int, 
                       default=int(os.getenv("DEFAULT_SEARCH_LIMIT", "10")),
                       help="Maximum number of candidates to extract")
    
    # Job description input
    parser.add_argument("--job-description", 
                       help="Path to text file containing job description for enhanced strategy generation")
    
    # Optional features
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
    # Initialize logging system first
    logger = init_logging()
    
    log_phase_start("MAIN", "LinkedIn Recruitment Agent Starting")
    
    # 1. Parse arguments and setup
    args = parse_arguments()
    
    # Validate arguments - require either query or job description
    if not args.query and not args.job_description:
        log_error("Either --query or --job-description must be provided", phase="initialization")
        log_info("Examples:", phase="initialization")
        log_info("   python runner/run_linkedin_agent_clean.py --query 'Senior Engineer' --location 'SF'", phase="initialization")
        log_info("   python runner/run_linkedin_agent_clean.py --job-description my_job.txt", phase="initialization")
        return
    
    setup_chrome_cdp()
    
    # 1.5. Read job description if provided
    job_description = None
    if args.job_description:
        try:
            job_file = Path(args.job_description)
            if not job_file.exists():
                log_error(f"Job description file not found: {args.job_description}", phase="initialization")
                sys.exit(1)
            
            job_description = job_file.read_text(encoding='utf-8')
            log_info(f"Loaded job description from: {args.job_description} ({len(job_description)} characters)", phase="initialization")
        except Exception as e:
            log_error(f"Error reading job description file", phase="initialization", exception=e)
            sys.exit(1)
    
    # 2. Initialize workflow manager  
    # Provide defaults for job-description-only mode
    effective_query = args.query or "Job Title (from description)"
    effective_location = args.location
    
    workflow = LinkedInWorkflowManager(
        query=effective_query,
        location=effective_location,
        limit=args.limit,
        enhanced_prompting=args.enhanced_prompting,
        streaming=args.streaming,
        job_description=job_description
    )
    
    # 3. Setup progress tracking (strategy is now generated by agent as first step)
    progress_tracker = None
    if args.streaming:
        progress_tracker = AgentProgressTracker(
            query=args.query,
            location=args.location,
            limit=args.limit,
            enable_streaming=True
        )
    
    # 4. Execute agentic recruitment workflow
    log_phase_start("workflow", "AGENTIC RECRUITMENT WORKFLOW")
    log_info("Agent will now execute 5-step workflow:", phase="workflow")
    log_info("   1. STRATEGY → Generate search strategy", phase="workflow")
    log_info("   2. SEARCH → Find candidates on LinkedIn", phase="workflow") 
    log_info("   3. EXTRACT → Get complete profile data", phase="workflow")
    log_info("   4. EVALUATE → Score candidates with strategic bonuses", phase="workflow")
    log_info("   5. OUTREACH → Generate personalized messages", phase="workflow")
    
    # Enable AdalFlow tracing
    os.environ["ADALFLOW_DISABLE_TRACING"] = "False"
    from adalflow.tracing import enable_mlflow_local, trace
    
    try:
        enable_mlflow_local(
            tracking_uri="http://localhost:8000",
            experiment_name="LinkedIn-Recruitment-Workflow",
            project_name="Clean-Agent-Architecture"
        )
    except ImportError:
        log_info("MLflow tracing not available", phase="workflow")
    
    candidates = []
    workflow_start_time = time.time()
    
    with trace(workflow_name="LinkedIn-Recruitment"):
        candidates = workflow.execute_search_workflow(progress_tracker)
    
    # 6. Save and display results
    log_phase_start("results", "RESULTS & SUMMARY")
    
    if candidates:
        # Pass strategy data for enhanced scoring insights
        strategy_data = getattr(workflow, 'strategy_data', None)
        save_info = workflow.save_results(candidates, strategy_data=strategy_data)
        
        # Check if save was successful
        if "Error:" not in str(save_info.get('evaluation_file', '')):
            log_info("RESULTS SAVED:", phase="storage")
            log_info(f"Outreach File: {save_info['outreach_file']}", phase="analysis")
            log_info(f"Evaluation File: {save_info['evaluation_file']}", phase="analysis")
            log_info(f"Candidates File: {save_info['candidates_file']}", phase="storage")
            log_info(f"Summary Report: {save_info['txt_file']}", phase="storage")
        else:
            log_error("Could not save results to files", phase="warning")
        
        log_info(f"👥 Total Candidates: {save_info['candidates_count']}")
        
        # Display summary
        log_info(f"\n🎉 RECRUITMENT SUMMARY:")
        log_debug(f"Query: {args.query}", phase="debug")
        log_debug(f"Location: {args.location}", phase="debug")
        log_debug(f"Found: {len(candidates)}/{args.limit} candidates", phase="debug")
        log_debug(f"Strategy: AI-Generated by Agent", phase="debug")
        
        # Show top candidates with better error handling
        log_info(f"\n📋 TOP CANDIDATES:")
        for i, candidate in enumerate(candidates[:3], 1):
            try:
                profile = candidate.get("profile_details", {})
                name = profile.get("name", "Unknown")
                title = profile.get("headline", "No title")
                
                # Get evaluation score from quality_assessment
                quality_assessment = profile.get("quality_assessment", {})
                evaluation_score = quality_assessment.get("overall_score", 0.0)
                
                log_debug(f"{i}. {name}", phase="debug")
                log_debug(f"   Title: {title}", phase="debug")
                log_debug(f"   Score: {evaluation_score:.1f}/10.0", phase="debug")
            except Exception as display_error:
                log_debug(f"{i}. [Error displaying candidate: {display_error}]", phase="debug")
        
    else:
        log_error(f" No candidates found", phase="error")
        log_info(f"💡 Try adjusting your search criteria or location")
        log_info(f"💡 Check your LinkedIn authentication or network connection")
    
    # Log final summary
    duration = time.time() - workflow_start_time if 'workflow_start_time' in locals() else 0
    logger.workflow_summary(len(candidates), duration, len(candidates) > 0)
    
    log_phase_end("MAIN", len(candidates) > 0, f"Processed {len(candidates)} candidates")
    
    log_info(f"✅ Recruitment workflow completed!")
    if candidates:
        log_info(f"📊 Final result: Successfully processed {len(candidates)} candidates")
    else:
        log_info(f"📊 Final result: No candidates found - consider adjusting search parameters")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_info(f"\n\n⏹️  Workflow interrupted by user")
    except Exception as e:
        log_info(f"\n❌ Workflow failed: {e}")
        import traceback
        traceback.print_exc()