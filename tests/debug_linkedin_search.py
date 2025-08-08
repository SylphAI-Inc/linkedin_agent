#!/usr/bin/env python3
"""Deep debug of LinkedIn search selectors and behavior."""

import os
import time
from pathlib import Path

# Setup path - go up one level from tests/ to repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import load_env, CDPConfig
from vendor.claude_web.tools.web_tool import WebTool

def main():
    load_env()
    cdp = CDPConfig() 
    
    # Auto-start Chrome CDP
    if not cdp.ensure_chrome_running():
        print("Failed to start Chrome CDP")
        return
    
    os.environ["CHROME_CDP_PORT"] = str(cdp.port)
    os.environ["HEADLESS_MODE"] = "true"
    
    w = WebTool(port=cdp.port)
    w.connect()
    
    try:
        # Navigate and check authentication
        print("=== Step 1: Authentication Check ===")
        w.go("https://www.linkedin.com")
        w.wait("body", 5)
        
        auth_status = w.js("""
        (() => {
          const hasMe = !!document.querySelector('button[aria-label*="me"], a[href*="/in/"], .global-nav__me, button[data-test-id="me-menu-trigger"]');
          const hasSearch = !!document.querySelector('input[placeholder*="search" i], .search-global-typeahead__input, input[aria-label*="search" i]');
          const bodyText = document.body.innerText.toLowerCase();
          const needsAuth = bodyText.includes('sign in') || bodyText.includes('log in') || bodyText.includes('join now');
          return { 
            hasMe, 
            hasSearch, 
            needsAuth, 
            url: window.location.href,
            title: document.title,
            searchSelector: document.querySelector('input[placeholder*="search" i], .search-global-typeahead__input, input[aria-label*="search" i]')?.tagName + '.' + Array.from(document.querySelector('input[placeholder*="search" i], .search-global-typeahead__input, input[aria-label*="search" i]')?.classList || []).join('.')
          };
        })()
        """)
        print(f"Auth Status: {auth_status}")
        
        if not auth_status.get("hasSearch"):
            print("❌ No search box found - user may not be authenticated")
            return
            
        print("✅ User appears authenticated with search access")
        
        # Try direct search navigation
        print("\n=== Step 2: Direct Search Navigation ===")
        search_url = "https://www.linkedin.com/search/results/people/?keywords=software%20engineer"
        w.go(search_url)
        w.wait("body", 5)
        
        page_analysis = w.js("""
        (() => {
          // Check for various possible containers
          const containerSelectors = [
            'li.reusable-search__result-container',
            'div.reusable-search__result-container', 
            '.search-results-container li',
            '.search-result',
            '[data-test-entity-urn]',
            '.entity-result',
            '.search-entity-result',
            '.reusable-search__result'
          ];
          
          const results = {};
          containerSelectors.forEach(sel => {
            const elements = document.querySelectorAll(sel);
            results[sel] = elements.length;
            if (elements.length > 0) {
              results[sel + '_sample'] = elements[0]?.outerHTML?.substring(0, 200) + '...';
            }
          });
          
          // Check for error states
          const errorStates = {
            'noResults': document.querySelector('.search-no-results, .artdeco-empty-state'),
            'authWall': document.body.innerText.toLowerCase().includes('sign in to see more results'),
            'premiumRequired': document.body.innerText.toLowerCase().includes('upgrade to see more'),
            'hasSearchFilters': !!document.querySelector('.search-filters, .search-s-filters'),
            'hasPeopleTab': !!document.querySelector('button[aria-label*="People"], a[href*="/search/results/people/"]')
          };
          
          return {
            url: window.location.href,
            title: document.title,
            containers: results,
            errorStates,
            bodyPreview: document.body.innerText.substring(0, 500)
          };
        })()
        """)
        
        print(f"Page analysis: {page_analysis}")
        
        # Try clicking People tab if available
        if page_analysis.get("errorStates", {}).get("hasPeopleTab"):
            print("\n=== Step 3: Clicking People Tab ===")
            people_clicked = w.js("""
            (() => {
              const peopleTab = document.querySelector('button[aria-label*="People"], a[href*="/search/results/people/"]');
              if (peopleTab) {
                peopleTab.click();
                return true;
              }
              return false;
            })()
            """)
            
            if people_clicked:
                print("✅ Clicked People tab")
                w.wait("body", 3)
                
                # Re-analyze after clicking
                updated_analysis = w.js("""
                (() => {
                  const containers = document.querySelectorAll('li.reusable-search__result-container, div.reusable-search__result-container, .entity-result');
                  return {
                    containerCount: containers.length,
                    sampleHTML: containers[0]?.outerHTML?.substring(0, 300) + '...' || 'none',
                    url: window.location.href
                  };
                })()
                """)
                print(f"After People tab click: {updated_analysis}")
        
        # Try scrolling to trigger lazy loading
        print("\n=== Step 4: Scrolling to Trigger Lazy Load ===")
        for i in range(3):
            w.js("window.scrollBy(0, 800);")
            time.sleep(1)
            count = w.js("document.querySelectorAll('li.reusable-search__result-container, div.reusable-search__result-container, .entity-result').length")
            print(f"After scroll {i+1}: {count} containers found")
            
        # Final extraction attempt
        print("\n=== Step 5: Final Extraction Attempt ===")
        extraction_result = w.js("""
        (() => {
          const containers = Array.from(document.querySelectorAll('li.reusable-search__result-container, div.reusable-search__result-container, .entity-result'));
          console.log('Found containers:', containers.length);
          
          return containers.slice(0, 3).map((c, i) => {
            // Try multiple selector strategies
            const strategies = [
              // Strategy 1: Original selectors
              {
                link: c.querySelector('a.app-aware-link[href*="/in/"]') || c.querySelector('a[href*="/in/"]'),
                name: c.querySelector('span[aria-hidden="true"], span[dir]'),
                subtitle: c.querySelector('.entity-result__primary-subtitle, .entity-result__secondary-subtitle, .t-14.t-normal')
              },
              // Strategy 2: More generic selectors
              {
                link: c.querySelector('a[href*="/in/"]'),
                name: c.querySelector('span:first-of-type, .entity-result__title-text span'),
                subtitle: c.querySelector('.entity-result__subtitle, .t-14, .text-body-small')
              },
              // Strategy 3: Text-based extraction
              {
                link: c.querySelector('a[href*="/in/"]'),
                name: Array.from(c.querySelectorAll('span')).find(s => s.textContent && s.textContent.trim().length > 2 && !s.textContent.includes('Connect'))?.textContent?.trim(),
                subtitle: 'text-based-extraction'
              }
            ];
            
            let result = null;
            for (let j = 0; j < strategies.length; j++) {
              const strat = strategies[j];
              if (strat.link && (strat.name?.textContent || typeof strat.name === 'string')) {
                result = {
                  strategy: j + 1,
                  name: typeof strat.name === 'string' ? strat.name : strat.name?.textContent?.trim(),
                  subtitle: typeof strat.subtitle === 'string' ? strat.subtitle : strat.subtitle?.textContent?.trim(),
                  url: strat.link?.href
                };
                break;
              }
            }
            
            return result || { 
              strategy: 'failed',
              containerHTML: c.outerHTML.substring(0, 200) + '...',
              index: i
            };
          });
        })()
        """)
        
        print(f"Extraction results: {extraction_result}")
        
    finally:
        w.close()

if __name__ == "__main__":
    main()