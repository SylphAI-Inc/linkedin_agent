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
        
        # Let's debug step by step what the actual search function will see
        step_by_step = w.js("""
        (() => {
          console.log('=== DEBUGGING SEARCH FUNCTION STEP BY STEP ===');
          
          // Step 1: Count containers
          const containers = document.querySelectorAll('.search-results-container li');
          console.log('Step 1 - Container count:', containers.length);
          
          if (containers.length === 0) return { error: 'No containers found' };
          
          // Step 2: Process first container
          const firstContainer = containers[0];
          const lines = firstContainer.textContent.split('\\n').map(l => l.trim()).filter(l => l && l !== 'Status is offline');
          console.log('Step 2 - Lines from first container:', lines);
          
          // Step 3: Look for profile link
          const profileLink = firstContainer.querySelector('a[href*="/in/"]');
          console.log('Step 3 - Profile link found:', !!profileLink, profileLink?.href);
          
          // Step 4: Name extraction debug
          let name = null;
          let debugInfo = [];
          for (const line of lines) {
            const hasProfile = line.includes("'s profile");
            const noBullet = !line.includes('•');
            const noDegree = !line.includes('degree');
            const viewIndex = line.indexOf('View ');
            
            debugInfo.push({
              line,
              hasProfile,
              noBullet, 
              noDegree,
              viewIndex,
              meetsCriteria: hasProfile && noBullet && noDegree && viewIndex > 0
            });
            
            if (hasProfile && noBullet && noDegree && viewIndex > 0) {
              const beforeView = line.substring(0, viewIndex).trim();
              console.log('Potential name found:', beforeView);
              if (beforeView.length > 2 && beforeView.length < 50) {
                name = beforeView;
                break;
              }
            }
          }
          
          // Step 5: Subtitle extraction debug
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
            containerCount: containers.length,
            extractedName: name,
            extractedSubtitle: subtitle,
            extractedUrl: profileLink?.href,
            debugLines: debugInfo,
            finalResult: {
              name: name || null,
              subtitle: subtitle || null,
              url: profileLink?.href || null
            }
          };
        })()
        """)
        
        print("=== STEP-BY-STEP DEBUG ===")
        print(f"Container count: {step_by_step.get('containerCount', 'N/A')}")
        print(f"Extracted name: {step_by_step.get('extractedName', 'N/A')}")
        print(f"Extracted subtitle: {step_by_step.get('extractedSubtitle', 'N/A')}")
        print(f"Extracted URL: {step_by_step.get('extractedUrl', 'N/A')}")
        print(f"Final result: {step_by_step.get('finalResult', 'N/A')}")
        
        print("\\n=== LINE-BY-LINE DEBUG ===")
        for i, debug in enumerate(step_by_step.get('debugLines', [])[:5]):
            print(f"Line {i}: {debug['line']}")
            print(f"  Has profile: {debug['hasProfile']}")
            print(f"  No bullet: {debug['noBullet']}")
            print(f"  No degree: {debug['noDegree']}")
            print(f"  View index: {debug['viewIndex']}")
            print(f"  Meets criteria: {debug['meetsCriteria']}")
            print()
        
    finally:
        w.close()

if __name__ == "__main__":
    main()