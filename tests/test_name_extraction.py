#!/usr/bin/env python3
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
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
        
        # Test name extraction with the exact patterns we observed
        name_test = w.js("""
        (() => {
          // Test with the exact strings we saw
          const testStrings = [
            'Shazmina AhmedView Shazmina Ahmed's profile',
            'Charlie ZhongView Charlie Zhong's profile'
          ];
          
          const results = testStrings.map(line => {
            let name = null;
            
            // Method 1: Split on "View "
            if (line.includes('View ') && line.includes("'s profile")) {
              const namePart = line.split('View ')[0].trim();
              if (namePart && namePart.length > 2 && !namePart.includes('•')) {
                name = namePart;
              }
            }
            
            // Method 2: Regex pattern
            if (!name && line.includes("View ") && line.includes("'s profile") && !line.includes('•')) {
              const match = line.match(/^([A-Za-z\\s]+)View\\s+.*'s profile/);
              if (match && match[1]) {
                name = match[1].trim();
              }
            }
            
            return { line, extractedName: name };
          });
          
          return results;
        })()
        """)
        
        print("=== Name Extraction Test ===")
        for result in name_test or []:
            if isinstance(result, dict):
                print(f"Line: {result.get('line', 'N/A')}")
                print(f"Extracted: {result.get('extractedName', 'N/A')}")
                print("---")
        
        # Now test on live data
        live_test = w.js("""
        (() => {
          const containers = Array.from(document.querySelectorAll('.search-results-container li')).slice(0, 2);
          
          return containers.map((li, index) => {
            const profileLink = li.querySelector('a[href*="/in/"]');
            const lines = li.textContent.split('\\n').map(l => l.trim()).filter(l => l && l !== 'Status is offline');
            
            let name = null;
            let nameFromLine = null;
            
            for (const line of lines) {
              // Look for pattern with "View" and "'s profile" 
              if (line.includes('View ') && line.includes("'s profile")) {
                nameFromLine = line;
                // Extract name before "View" 
                const namePart = line.split('View ')[0].trim();
                if (namePart && namePart.length > 2 && !namePart.includes('•')) {
                  name = namePart;
                  break;
                }
              }
              // Alternative pattern: "NameView Name's profile" (no space before View)
              else if (line.includes("View ") && line.includes("'s profile") && !line.includes('•')) {
                nameFromLine = line;
                const match = line.match(/^([A-Za-z\\s]+)View\\s+.*'s profile/);
                if (match && match[1]) {
                  name = match[1].trim();
                  break;
                }
              }
            }
            
            return {
              index,
              name,
              nameFromLine,
              url: profileLink?.href || null,
              allLines: lines
            };
          });
        })()
        """)
        
        print("\\n=== Live Extraction Test ===")
        for item in live_test:
            print(f"Item {item['index']}")
            print(f"  Name: {item['name']}")
            print(f"  Name line: {item['nameFromLine']}")
            print(f"  URL: {item['url']}")
            print(f"  All lines: {item['allLines'][:3]}...")
            print("---")
        
    finally:
        w.close()

if __name__ == "__main__":
    main()