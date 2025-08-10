"""
Smart Search Tool - Strategy-based candidate discovery
Finds quality candidates based on AI-generated strategy without extracting full profiles
"""

from typing import List, Dict, Any, Set
from urllib.parse import quote_plus
import time
import re

from adalflow.core.func_tool import FunctionTool
from .web_nav import js as run_js, go as nav_go, wait as nav_wait
from .linkedin_selectors import SEARCH_INPUT, PEOPLE_TAB, SEARCH_RESULTS_CARDS
from .people_search import evaluate_headline_with_strategy


class CandidateURLCollector:
    """Collects and manages candidate URLs with deduplication"""
    
    def __init__(self):
        self.processed_urls: Set[str] = set()
        self.quality_candidates: List[Dict[str, Any]] = []
    
    def normalize_url(self, url: str) -> str:
        """Normalize LinkedIn URL for consistent comparison"""
        if not url:
            return ""
        
        # Remove tracking parameters and normalize
        url = url.split('?')[0]  # Remove query parameters
        url = url.rstrip('/')    # Remove trailing slash
        url = url.lower()        # Lowercase for comparison
        
        # Extract profile ID for consistent deduplication
        match = re.search(r'/in/([^/]+)', url)
        if match:
            profile_id = match.group(1)
            return f"https://www.linkedin.com/in/{profile_id}"
        
        return url
    
    def is_duplicate(self, url: str) -> bool:
        """Check if URL has already been processed"""
        normalized = self.normalize_url(url)
        return normalized in self.processed_urls
    
    def add_candidate(self, candidate_data: Dict[str, Any]) -> bool:
        """Add candidate if not duplicate and meets quality threshold"""
        url = candidate_data.get('url', '')
        normalized_url = self.normalize_url(url)
        
        if normalized_url in self.processed_urls:
            return False
        
        self.processed_urls.add(normalized_url)
        candidate_data['normalized_url'] = normalized_url
        self.quality_candidates.append(candidate_data)
        return True
    
    def get_candidate_count(self) -> int:
        """Get total number of quality candidates collected"""
        return len(self.quality_candidates)
    
    def get_candidates(self, sort_by_score: bool = True) -> List[Dict[str, Any]]:
        """Get all collected quality candidates, optionally sorted by score"""
        candidates = self.quality_candidates.copy()
        
        if sort_by_score:
            # Sort by headline_score descending (highest scores first)
            candidates.sort(key=lambda x: x.get('headline_score', 0), reverse=True)
            print(f"📊 Sorted {len(candidates)} candidates by headline score (highest first)")
        
        return candidates


# Global collector instance for the session
_url_collector = CandidateURLCollector()


def get_url_collector() -> CandidateURLCollector:
    """Get the global URL collector instance"""
    return _url_collector


def smart_candidate_search(
    query: str, 
    location: str, 
    strategy: Dict[str, Any],
    page_limit: int = 3,
    min_score_threshold: float = 2.0
) -> Dict[str, Any]:
    """
    Smart search for quality candidates using strategy-based filtering
    
    Args:
        query: Search query (role/title)
        location: Geographic location  
        strategy: AI-generated search strategy
        page_limit: Max pages to search (default 3)
        min_score_threshold: Minimum headline score to include candidate
        
    Returns:
        Dict with candidate URLs, counts, and quality metrics
    """
    
    collector = get_url_collector()
    initial_count = collector.get_candidate_count()
    
    print(f"🔍 Smart search: '{query}' in {location}")
    print(f"📊 Quality threshold: {min_score_threshold}")
    print(f"📄 Max pages: {page_limit}")
    
    # Build search query using simple approach like the working original
    # Keep it simple - complex OR queries don't work well on LinkedIn
    search_query = query
    if location:
        search_query = f"{query} {location}".strip()
    
    print(f"🔍 Search query: '{search_query}'")
    
    pages_searched = 0
    candidates_found = 0
    
    try:
        for page in range(page_limit):
            print(f"📖 Searching page {page + 1}/{page_limit}")

            # Navigate to search page with proper pagination
            if page == 0:
                search_url = f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(search_query)}"
            else:
                # LinkedIn uses &page= parameter for pagination, not &start=
                search_url = f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(search_query)}&page={page + 1}"
            
            print(f"🌐 Navigating to: {search_url}")
            nav_go(search_url)
            nav_wait(3)  # Wait for page load            # Check if we have search results on the page
            print(f"   🔍 Checking for search results...")
            
            # Extract candidate data from current page
            page_results = _extract_candidate_data_from_page(strategy, min_score_threshold)
            print(f"   📊 Extracted {len(page_results)} candidates from page")
            
            if not page_results:
                print(f"❌ No results found on page {page + 1}, stopping search")
                break
            
            pages_searched += 1
            page_candidates = 0
            
            # Process each candidate
            for candidate in page_results:
                if collector.add_candidate(candidate):
                    candidates_found += 1
                    page_candidates += 1
                    print(f"  ✅ Added: {candidate['name']} (score: {candidate.get('headline_score', 0):.1f})")
                else:
                    print(f"  🔄 Duplicate: {candidate['name']}")
            
            print(f"📊 Page {page + 1}: {page_candidates} new candidates added")
            
            # Small delay between pages
            time.sleep(2)
    
    except Exception as e:
        print(f"❌ Search error: {e}")
        return {
            "success": False,
            "error": str(e),
            "pages_searched": pages_searched,
            "candidates_found": 0,
            "total_candidates": collector.get_candidate_count()
        }
    
    total_found = collector.get_candidate_count()
    new_candidates = total_found - initial_count
    
    return {
        "success": True,
        "pages_searched": pages_searched,
        "candidates_found": new_candidates,
        "total_candidates": total_found,
        "search_query": search_query,
        "quality_threshold": min_score_threshold
    }


def _extract_candidate_data_from_page(strategy: Dict[str, Any], min_score: float) -> List[Dict[str, Any]]:
    """Extract candidate data from current search results page using exact working code from people_search.py"""
    
    # Use robust selectors for LinkedIn search results - try multiple patterns
    extraction_code = f"""
    (() => {{
      // Try multiple selector patterns to find profile containers
      let containers = [];
      const selectors = [
        '.search-results-container ul > li',  // Nested structure
        '.search-results-container li',       // Direct structure  
        '.entity-result',                     // Alternative LinkedIn class
        '.search-result',                     // Generic search result
        '[data-entity-urn*="person"]'         // Data attribute pattern
      ];
      
      for (const selector of selectors) {{
        containers = Array.from(document.querySelectorAll(selector));
        if (containers.length > 0) {{
          console.log(`Found ${{containers.length}} containers with selector: ${{selector}}`);
          break;
        }}
      }}
      
      // If no containers found, try broader search for profile links
      if (containers.length === 0) {{
        const allLinks = Array.from(document.querySelectorAll('a[href*="/in/"]'));
        console.log(`Fallback: found ${{allLinks.length}} profile links`);
        containers = allLinks.map(link => link.closest('li')).filter(li => li);
      }}
      
      containers = containers.slice(0, 20);
      
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
    
    try:
        print(f"   🛠️  Running JavaScript extraction...")
        results = run_js(extraction_code)
        
        print(f"   📊 JS returned: {type(results)} with {len(results) if isinstance(results, list) else 'non-list'} items")
        
        if results is None:
            print(f"   ⚠️  JavaScript returned None")
            return []
            
        if not isinstance(results, list):
            print(f"   ⚠️  JavaScript returned non-list: {results}")
            results = []
        
        quality_candidates = []
        
        print(f"   🔍 Processing {len(results)} raw candidates...")
        
        for i, candidate in enumerate(results):
            try:
                # Evaluate headline using strategy - use subtitle field from extraction
                headline = candidate.get('subtitle', '')
                evaluation = evaluate_headline_with_strategy(headline, strategy)
                
                score = evaluation.get('score', 0.0)
                worth_extracting = score >= min_score
                
                print(f"      Candidate {i+1}: {candidate.get('name', 'Unknown')} - Score: {score:.1f} - {'✅' if worth_extracting else '❌'}")
                
                if worth_extracting:
                    # Convert subtitle to headline to match expected format
                    candidate['headline'] = candidate.get('subtitle', '')
                    candidate.update({
                        'headline_score': score,
                        'quality_signals': evaluation.get('signals', []),
                        'worth_extracting': True,
                        'extraction_timestamp': time.time()
                    })
                    quality_candidates.append(candidate)
                    
            except Exception as candidate_error:
                print(f"      ❌ Error processing candidate {i+1}: {candidate_error}")
                continue
        
        print(f"   ✅ {len(quality_candidates)} candidates passed quality threshold")
        return quality_candidates
        
    except Exception as e:
        print(f"   ❌ Page extraction error: {e}")
        print(f"   🔍 Error type: {type(e).__name__}")
        import traceback
        print(f"   📋 Traceback: {traceback.format_exc()[:200]}...")
        return []


def get_collected_candidates(limit: int = None, sort_by_score: bool = True) -> Dict[str, Any]:
    """Get all collected quality candidates, sorted by score"""
    collector = get_url_collector()
    candidates = collector.get_candidates(sort_by_score=sort_by_score)
    
    if limit:
        candidates = candidates[:limit]
        if sort_by_score and candidates:
            print(f"🎯 Selected top {len(candidates)} candidates (scores: {candidates[0].get('headline_score', 0):.1f} to {candidates[-1].get('headline_score', 0):.1f})")
    
    return {
        "total_count": collector.get_candidate_count(),
        "returned_count": len(candidates),
        "candidates": candidates
    }


def clear_candidate_collection() -> Dict[str, Any]:
    """Clear all collected candidates (useful for new searches)"""
    global _url_collector
    old_count = _url_collector.get_candidate_count()
    _url_collector = CandidateURLCollector()
    
    return {
        "success": True,
        "cleared_count": old_count,
        "message": f"Cleared {old_count} candidates from collection"
    }


# Create AdalFlow Function Tools
SmartCandidateSearchTool = FunctionTool(fn=smart_candidate_search)
GetCollectedCandidatesTool = FunctionTool(fn=get_collected_candidates)
ClearCandidateCollectionTool = FunctionTool(fn=clear_candidate_collection)