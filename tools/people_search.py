from typing import List, Dict, Any
from urllib.parse import quote_plus

from adalflow.core.func_tool import FunctionTool
from .web_nav import js as run_js, go as nav_go, wait as nav_wait
from .linkedin_selectors import SEARCH_INPUT, PEOPLE_TAB, SEARCH_RESULTS_CARDS


def _js_click_first(sel: str) -> bool:
    code = f"""
    (() => {{
      const el = document.querySelector('{sel}'.replace(/'/g, "\\'"));
      if (!el) return false;
      el.click();
      return true;
    }})()
    """
    return bool(run_js(code))


def search_people(query: str, location: str = "", limit: int = 10) -> Dict[str, Any]:
    """Navigate LinkedIn people search and return lightweight result cards (name, subtitle, url).

    Returns a structured payload to help the agent reason:
      { "count": int, "results": [{ name, subtitle, url }] }
    """
    q = (query + (f" {location}" if location else "")).strip()
    url = f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(q)}"
    nav_go(url)
    # Wait for search results 
    nav_wait(".search-results-container li, .search-no-results", 12)
    
    # Prefer People tab when present (best-effort)
    _js_click_first(PEOPLE_TAB)
    nav_wait(".search-results-container li", 5)

    # Check for results using the correct selector
    code_count = """
    (() => {
      const nodes = document.querySelectorAll('.search-results-container li');
      return nodes ? nodes.length : 0;
    })()
    """
    count = int(run_js(code_count) or 0)
    
    # Light scrolling to ensure all results are loaded
    if count > 0:
        run_js("window.scrollBy(0, 800);")
        nav_wait(".search-results-container li", 2)
        count = int(run_js(code_count) or 0)

    if count == 0:
        return {"count": 0, "results": [], "error": "No search results found"}

    code_collect = f"""
    (() => {{
      const containers = Array.from(document.querySelectorAll('.search-results-container li')).slice(0, {limit});
      
      return containers.map(li => {{
        const profileLink = li.querySelector('a[href*="/in/"]');
        const lines = li.textContent.split('\\n').map(l => l.trim()).filter(l => l && l !== 'Status is offline');
        
        // Find name using LinkedIn's pattern
        let name = null;
        for (const line of lines) {{
          if ((line.includes("'s profile") || line.includes("'s profile") || line.includes("s profile")) && 
              line.includes("View ") && !line.includes('•') && !line.includes('degree')) {{
            const viewIndex = line.indexOf('View ');
            if (viewIndex > 0) {{
              const beforeView = line.substring(0, viewIndex).trim();
              if (beforeView.length > 2 && beforeView.length < 50) {{
                name = beforeView;
                break;
              }}
            }}
          }}
        }}
        
        // Find subtitle - usually appears after connection info
        let subtitle = null;
        let foundConnectionLine = false;
        for (const line of lines) {{
          if (line.includes('degree connection')) {{
            foundConnectionLine = true;
            continue;
          }}
          if (foundConnectionLine && line && !line.includes('degree') && !line.includes('View ') && !line.includes('Status is') && line.length > 5) {{
            subtitle = line;
            break;
          }}
        }}
        
        return {{
          name: name || null,
          subtitle: subtitle || null, 
          url: profileLink?.href || null
        }};
      }}).filter(x => x.url && x.name);
    }})()
    """
    results = run_js(code_collect) or []
    # Normalize and structure output to help the planner
    if not isinstance(results, list):
        results = []
    payload = {"count": len(results), "results": results}
    return payload


SearchPeopleTool = FunctionTool(fn=search_people)
