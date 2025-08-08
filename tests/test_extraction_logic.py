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
        
        # Test the exact extraction logic from the updated search function
        test_extraction = w.js("""
        (() => {
          const containers = Array.from(document.querySelectorAll('.search-results-container li')).slice(0, 3);
          
          return containers.map((li, index) => {
            // Get profile link
            const profileLink = li.querySelector('a[href*="/in/"]');
            
            // Extract text lines and clean them
            const lines = li.textContent.split('\\n').map(l => l.trim()).filter(l => l && l !== 'Status is offline');
            
            // Find name - usually the first substantial text that contains a person's name
            let name = null;
            for (const line of lines) {
              // Look for pattern "FirstName LastName" followed by "View [Name]'s profile"
              if (line.includes('View ') && line.includes("'s profile")) {
                // Extract name before "View"
                const namePart = line.split('View ')[0].trim();
                if (namePart && namePart.length > 2 && !namePart.includes('•')) {
                  name = namePart;
                  break;
                }
              }
            }
            
            // Find subtitle - usually appears after connection info
            let subtitle = null;
            let foundConnectionLine = false;
            for (const line of lines) {
              if (line.includes('degree connection')) {
                foundConnectionLine = true;
                continue;
              }
              if (foundConnectionLine && line && !line.includes('degree') && !line.includes('View ') && !line.includes('Status is') && line.length > 5) {
                subtitle = line;
                break;
              }
            }
            
            return {
              index,
              name: name || null,
              subtitle: subtitle || null,
              url: profileLink?.href || null,
              debug_lines: lines.slice(0, 8),  // More debug lines
              debug_profileLink: profileLink ? 'found' : 'not found'
            };
          });
        })()
        """)
        
        print("=== Extraction Test Results ===")
        for item in test_extraction:
            print(f"\n--- Item {item['index']} ---")
            print(f"Name: {item['name']}")  
            print(f"Subtitle: {item['subtitle']}")
            print(f"URL: {item['url']}")
            print(f"Profile Link: {item['debug_profileLink']}")
            print(f"Debug lines: {item['debug_lines']}")
        
        # Test a simpler extraction approach
        simple_extraction = w.js("""
        (() => {
          const containers = Array.from(document.querySelectorAll('.search-results-container li')).slice(0, 2);
          
          return containers.map((li, index) => {
            const profileLink = li.querySelector('a[href*="/in/"]');
            const allText = li.textContent;
            
            // Simple regex to find name patterns
            const nameMatch = allText.match(/([A-Z][a-z]+ [A-Z][a-z]+)View \\1's profile/);
            
            return {
              index,
              url: profileLink?.href || null,
              nameFromRegex: nameMatch ? nameMatch[1] : null,
              rawText: allText.substring(0, 200) + '...'
            };
          });
        })()
        """)
        
        print(f"\n=== Simple Extraction ===")
        for item in simple_extraction:
            print(f"Item {item['index']}: {item['nameFromRegex']} -> {item['url']}")
            print(f"Raw: {item['rawText'][:100]}...")
        
    finally:
        w.close()

if __name__ == "__main__":
    main()