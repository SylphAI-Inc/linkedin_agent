from typing import List, Dict
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


def search_people(query: str, location: str = "", limit: int = 10) -> List[Dict]:
    """Navigate LinkedIn people search and return lightweight result cards (name, subtitle, url)."""
    q = (query + (f" {location}" if location else "")).strip()
    url = f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(q)}"
    nav_go(url)
    # Wait for modern search containers
    nav_wait("li.reusable-search__result-container, div.reusable-search__result-container, .search-results-container", 10)
    # Prefer People tab when present
    _js_click_first(PEOPLE_TAB)
    nav_wait("li.reusable-search__result-container, div.reusable-search__result-container", 10)

    code_collect = f"""
    (() => {{
      const containers = Array.from(document.querySelectorAll('li.reusable-search__result-container, div.reusable-search__result-container'));
      const cards = containers.slice(0, {limit});
      return cards.map(c => {{
        const link = c.querySelector('a.app-aware-link[href*="/in/"]') || c.querySelector('a[href*="/in/"]');
        const nameEl = c.querySelector('span[aria-hidden="true"], span[dir]');
        const subtitleEl = c.querySelector('.entity-result__primary-subtitle, .entity-result__secondary-subtitle, .t-14.t-normal');
        const name = (nameEl?.textContent||'').trim();
        const subtitle = (subtitleEl?.textContent||'').trim();
        const url = link ? link.href : null;
        return {{ name, subtitle, url }};
      }}).filter(x => x.url);
    }})()
    """
    return run_js(code_collect) or []


SearchPeopleTool = FunctionTool(fn=search_people)
