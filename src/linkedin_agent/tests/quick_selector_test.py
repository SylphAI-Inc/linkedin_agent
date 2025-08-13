#!/usr/bin/env python3
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import load_env, CDPConfig
from vendor.claude_web.tools.web_tool import WebTool

def main():
    load_env()
    cdp = CDPConfig() 
    os.environ["CHROME_CDP_PORT"] = str(cdp.port)
    os.environ["HEADLESS_MODE"] = "true"
    
    w = WebTool(port=cdp.port)
    w.connect()
    
    try:
        w.go("https://www.linkedin.com/search/results/people/?keywords=software%20engineer")
        w.wait("body", 8)
        
        # Check what containers we actually have
        check_containers = w.js("""
        (() => {
          const selectors = [
            '.search-results-container li',
            '.search-results-container', 
            '.search-results',
            'li',
            '[class*="search"]',
            '[class*="result"]'
          ];
          
          const results = {};
          selectors.forEach(sel => {
            const elements = document.querySelectorAll(sel);
            results[sel] = elements.length;
          });
          
          // Also check page state
          results['bodyText'] = document.body.innerText.substring(0, 200);
          results['title'] = document.title;
          results['url'] = window.location.href;
          
          return results;
        })()
        """)
        
        print("Container check:", check_containers)
        
        # If we found the right containers, extract from the first few
        if check_containers.get('.search-results-container li', 0) > 0:
            print("Found search containers, extracting...")
            
            extraction = w.js("""
            (() => {
              const containers = Array.from(document.querySelectorAll('.search-results-container li')).slice(0, 2);
              
              return containers.map(li => {
                // Get the raw text content split by lines
                const lines = li.textContent.split('\\n').map(l => l.trim()).filter(l => l);
                
                // Look for profile link
                const profileLink = li.querySelector('a[href*="/in/"]');
                
                return {
                  profileUrl: profileLink?.href || null,
                  rawLines: lines.slice(0, 8), // First 8 lines of text
                  linkText: profileLink?.textContent?.trim() || null
                };
              });
            })()
            """)
            
            print("Raw extraction:", extraction)
        
    finally:
        w.close()

if __name__ == "__main__":
    main()