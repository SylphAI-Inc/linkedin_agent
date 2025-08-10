#!/usr/bin/env python3
"""Analyze LinkedIn's new search result HTML structure."""

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
        # Navigate to search
        w.go("https://www.linkedin.com/search/results/people/?keywords=software%20engineer")
        w.wait("body", 5)
        
        # Click People tab
        w.js("""
        const peopleTab = document.querySelector('button[aria-label*="People"], a[href*="/search/results/people/"]');
        if (peopleTab) peopleTab.click();
        """)
        w.wait("body", 3)
        
        # Analyze the structure
        analysis = w.js("""
        (() => {
          const containers = Array.from(document.querySelectorAll('.search-results-container li'));
          console.log('Total containers found:', containers.length);
          
          return containers.slice(0, 3).map((li, index) => {
            // Get all links
            const allLinks = Array.from(li.querySelectorAll('a')).map(a => ({
              href: a.href,
              text: a.textContent?.trim(),
              hasProfile: a.href.includes('/in/')
            }));
            
            // Get all spans with text
            const allSpans = Array.from(li.querySelectorAll('span')).map(s => ({
              text: s.textContent?.trim(),
              classes: Array.from(s.classList).join(' '),
              hasText: s.textContent?.trim()?.length > 2
            })).filter(s => s.hasText);
            
            // Get structure info
            return {
              index,
              profileLink: allLinks.find(l => l.hasProfile)?.href,
              possibleNames: allSpans.slice(0, 5).map(s => s.text),
              allClasses: Array.from(li.querySelectorAll('*')).map(el => Array.from(el.classList).join(' ')).filter(c => c),
              html: li.outerHTML.substring(0, 400) + '...'
            };
          });
        })()
        """)
        
        print("=== LinkedIn Search Structure Analysis ===")
        for i, item in enumerate(analysis):
            print(f"\n--- Item {i+1} ---")
            print(f"Profile Link: {item['profileLink']}")
            print(f"Possible Names: {item['possibleNames'][:3]}")
            print(f"Unique Classes: {set(c for c in item['allClasses'] if c)}")
            print(f"HTML Preview: {item['html'][:200]}...")
            
        # Try improved extraction
        improved_extraction = w.js("""
        (() => {
          const containers = Array.from(document.querySelectorAll('.search-results-container li'));
          
          return containers.slice(0, 3).map(li => {
            // Find profile link
            const profileLink = li.querySelector('a[href*="/in/"]');
            
            // Find name - try multiple strategies
            let name = null;
            
            // Strategy 1: Look for span within profile link
            if (profileLink) {
              const nameInLink = profileLink.querySelector('span');
              if (nameInLink) name = nameInLink.textContent?.trim();
            }
            
            // Strategy 2: Look for first substantial span text
            if (!name) {
              const spans = Array.from(li.querySelectorAll('span'));
              const nameSpan = spans.find(s => {
                const text = s.textContent?.trim();
                return text && text.length > 2 && text.length < 50 && !text.includes('•') && !text.includes('View') && !text.includes('degree');
              });
              if (nameSpan) name = nameSpan.textContent?.trim();
            }
            
            // Find subtitle/job title - usually after name
            let subtitle = null;
            const allText = li.textContent?.split('\\n').map(t => t.trim()).filter(t => t && t.length > 2);
            const nameIndex = allText?.findIndex(t => t === name);
            if (nameIndex >= 0 && nameIndex < allText.length - 1) {
              subtitle = allText[nameIndex + 1];
              // Clean subtitle - remove connection indicators
              if (subtitle.includes('•')) subtitle = subtitle.split('•')[1]?.trim();
            }
            
            return {
              name,
              subtitle,
              url: profileLink?.href,
              allText: allText?.slice(0, 5) // For debugging
            };
          });
        })()
        """)
        
        print(f"\n=== Improved Extraction Results ===")
        for item in improved_extraction:
            print(f"Name: {item['name']}")
            print(f"Subtitle: {item['subtitle']}")
            print(f"URL: {item['url']}")
            print(f"Debug - All text: {item['allText']}")
            print("---")
        
    finally:
        w.close()

if __name__ == "__main__":
    main()