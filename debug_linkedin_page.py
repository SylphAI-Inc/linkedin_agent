#!/usr/bin/env python3
"""
Debug script to check what's on the LinkedIn search page
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tools.web_nav import go as nav_go, wait as nav_wait, js as run_js
from utils.logger import init_logging, log_info
from urllib.parse import quote_plus

def debug_linkedin_page():
    """Check what's actually on the LinkedIn search page"""
    print("🔍 Debugging LinkedIn search page...")
    
    logger = init_logging()
    
    try:
        # Navigate to a simple LinkedIn search
        search_query = "Software Engineer San Francisco"
        search_url = f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(search_query)}"
        
        log_info(f"Navigating to: {search_url}", phase="DEBUG")
        nav_go(search_url)
        nav_wait(5)  # Wait longer for page load
        
        # Check basic page info
        page_info_js = """
        (() => {
            return {
                title: document.title,
                url: window.location.href,
                has_results_container: !!document.querySelector('.search-results-container'),
                profile_links_count: document.querySelectorAll('a[href*="/in/"]').length,
                page_text_snippet: document.body.textContent.substring(0, 500),
                all_list_items: document.querySelectorAll('li').length,
                search_divs: document.querySelectorAll('div[class*="search"]').length
            };
        })()
        """
        
        log_info("Getting page information...", phase="DEBUG")
        page_info = run_js(page_info_js)
        
        log_info(f"Page title: {page_info.get('title', 'Unknown')}", phase="DEBUG")
        log_info(f"URL: {page_info.get('url', 'Unknown')}", phase="DEBUG") 
        log_info(f"Has results container: {page_info.get('has_results_container', False)}", phase="DEBUG")
        log_info(f"Profile links found: {page_info.get('profile_links_count', 0)}", phase="DEBUG")
        log_info(f"Total list items: {page_info.get('all_list_items', 0)}", phase="DEBUG")
        log_info(f"Search divs: {page_info.get('search_divs', 0)}", phase="DEBUG")
        
        if page_info.get('page_text_snippet'):
            log_info(f"Page text snippet: {page_info['page_text_snippet'][:200]}...", phase="DEBUG")
        
        # Try the actual extraction to see what happens
        log_info("Testing candidate extraction...", phase="DEBUG")
        extraction_js = """
        (() => {
            const selectors = [
                '.search-results-container li',
                '.search-results-container ul > li', 
                '.entity-result',
                '.search-result',
                '[data-entity-urn*="person"]'
            ];
            
            let containers = [];
            let selectorUsed = null;
            
            for (const selector of selectors) {
                containers = Array.from(document.querySelectorAll(selector));
                if (containers.length > 0) {
                    selectorUsed = selector;
                    break;
                }
            }
            
            return {
                selector_used: selectorUsed,
                containers_found: containers.length,
                profile_links_in_containers: containers.filter(li => li.querySelector('a[href*="/in/"]')).length
            };
        })()
        """
        
        extraction_result = run_js(extraction_js)
        log_info(f"Extraction result: {extraction_result}", phase="DEBUG")
        
    except Exception as e:
        log_info(f"❌ Debug failed: {e}", phase="DEBUG")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_linkedin_page()