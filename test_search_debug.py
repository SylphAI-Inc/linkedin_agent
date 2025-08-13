#!/usr/bin/env python3
"""
Debug script to test smart search functionality
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import init_logging, log_info, log_debug, log_error
from tools.smart_search import smart_candidate_search
from tools.strategy_creation import create_search_strategy
from config import load_env

def test_search_debug():
    """Test smart search with debugging"""
    print("🧪 Testing smart search functionality...")
    
    # Initialize logging
    logger = init_logging()
    
    # Load environment
    load_env()
    
    try:
        # First create a strategy
        log_info("Creating test strategy", phase="DEBUG")
        strategy_result = create_search_strategy(
            query="Software Engineer",
            location="San Francisco"
        )
        
        if not strategy_result.get("success"):
            log_error("Strategy creation failed", phase="DEBUG")
            return
            
        log_info("Strategy created successfully", phase="DEBUG")
        
        # Now test search with very small target
        log_info("Testing search with target_candidate_count=1", phase="DEBUG")
        search_result = smart_candidate_search(
            query="Software Engineer",
            location="San Francisco", 
            target_candidate_count=1,
            page_limit=1,  # Just one page
            min_score_threshold=5.0  # Lower threshold
        )
        
        log_info(f"Search result: {search_result}", phase="DEBUG")
        
        if search_result.get("success"):
            log_info(f"✅ Search succeeded: {search_result.get('candidates_found', 0)} candidates found", phase="DEBUG")
        else:
            log_error(f"❌ Search failed: {search_result.get('error', 'Unknown error')}", phase="DEBUG")
            
    except Exception as e:
        log_error(f"Test failed with exception: {e}", phase="DEBUG", exception=e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_search_debug()