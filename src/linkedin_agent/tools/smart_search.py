"""
Smart Search Tool - Simple candidate discovery
"""

from typing import List, Dict, Any
from urllib.parse import quote_plus
import time

from adalflow.core.func_tool import FunctionTool
from ..core.workflow_state import store_search_results
from ..utils.logger import log_info, log_debug, log_error
from .web_nav import js as run_js, go as nav_go, wait as nav_wait
from ..models.quality_system import QualityAnalyzer, QualityThresholds, SearchBudget
from ..config_user import get_search_config


# run the search quer and extract candidates from each page, inital scoring and the filtering
def smart_candidate_search(
    query: str,
    location: str,
    page_limit: int = 3,
    min_score: float = 3.0,
    target_count: int = 10,
) -> Dict[str, Any]:
    """
    Search for candidates on LinkedIn for {page_limit} pages, extract basic info, and perform LLM-based quality assessment.
    Collect up to {target_count} candidates meeting the minimum score threshold.

    Args:
        query: Search query (role/title)
        location: Geographic location
        page_limit: Number of pages to search (default 3)
        min_score: Minimum score to include candidate (default 3.0)
    Returns:
        Dict with search results
    """

    log_info(f"🔍 Searching: '{query}' in {location}")

    search_config = get_search_config()
    network_filter = search_config.network_filter

    # Build search query
    search_query = f"{query} {location}".strip() if location else query

    # Initialize quality analyzer for LLM-based assessment
    thresholds = QualityThresholds(
        minimum_acceptable=min_score, target_quality=7.0, exceptional_quality=9.0
    )
    budget = SearchBudget(initial_page_limit=page_limit, max_page_limit=page_limit)
    quality_analyzer = QualityAnalyzer(thresholds, budget)

    all_candidates = []
    seen_urls = set()

    try:
        for page in range(page_limit):
            log_info(f"📖 Searching page {page + 1}/{page_limit}")

            # Build URL with pagination and network filter
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(search_query)}"

            # Add network filter (must come before pagination for LinkedIn)
            if network_filter:
                # Use proper URL encoding for network filter array
                # F = 1st degree, S = 2nd degree, O = 3rd+ degree
                search_url += f"&network=[%22{network_filter}%22]"
                log_debug(
                    f"Using network filter: {network_filter} (1st degree)"
                    if network_filter == "F"
                    else f"Using network filter: {network_filter}"
                )

            # Add pagination
            if page > 0:
                search_url += f"&page={page + 1}"

            log_debug(f"🌐 Navigating to: {search_url}")
            nav_go(search_url)

            # Wait for search results to load
            try:
                nav_wait(".search-results-container li, .search-no-results", 10)
            except:
                log_debug("Timeout waiting for search results")

            # Light scroll to trigger lazy loading
            try:
                run_js("window.scrollBy(0, 800);")
                nav_wait("2")
            except:
                pass

            # Extract candidates from page
            candidates = _extract_candidates_from_page()

            if not candidates:
                log_info(f"No more results on page {page + 1}")
                # Debug: Check what's actually on the page
                _debug_page_if_no_results()
                break

            log_info(f"Found {len(candidates)} candidates on page {page + 1}")
            log_info(f"Candidates info: {candidates}")

            # Process and deduplicate candidates
            for candidate in candidates:
                url = candidate.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)

                    # Use LLM-based quality assessment
                    try:
                        # Create candidate data for assessment
                        candidate_data = {
                            "name": candidate.get("name", ""),
                            "headline": candidate.get("headline", ""),
                            "url": url,
                        }

                        # Get LLM quality assessment
                        quality_assessment = quality_analyzer.assess_candidate_quality(
                            candidate_data=candidate_data,
                            role_query=query,
                            job_requirements=f"Looking for {query} in {location}"
                            if location
                            else f"Looking for {query}",
                        )

                        score = quality_assessment.overall_score
                        candidate["score"] = score
                        candidate["quality_assessment"] = quality_assessment
                        if score >= min_score:
                            all_candidates.append(candidate)
                            strength = (
                                quality_assessment.strengths[0]
                                if quality_assessment.strengths
                                else "Good match"
                            )
                            log_info(
                                f"   ✅ {candidate['name']} (Score: {score:.1f}) - {strength}"
                            )
                        else:
                            concern = (
                                quality_assessment.concerns[0]
                                if quality_assessment.concerns
                                else "Below threshold"
                            )
                            log_debug(
                                f"   ❌ {candidate['name']} (Score: {score:.1f}) - {concern}"
                            )

                    except Exception as e:
                        log_debug(
                            f"LLM assessment failed for {candidate.get('name', 'Unknown')}: {e}"
                        )
                        # Fallback: basic keyword matching
                        headline = candidate.get("headline", "").lower()
                        query_lower = query.lower()
                        score = 5.0 if query_lower in headline else 3.0
                        candidate["score"] = score

                        if score >= min_score:
                            all_candidates.append(candidate)
                            log_info(
                                f"   ✅ {candidate['name']} (Fallback Score: {score:.1f})"
                            )
                        else:
                            log_debug(
                                f"   ❌ {candidate['name']} (Fallback Score: {score:.1f})"
                            )

            # Stop if we have enough candidates
            if len(all_candidates) >= target_count:
                log_info(f"✅ Found {target_count} candidates, stopping search")
                break

            time.sleep(2)  # Rate limiting

    except Exception as e:
        log_error(f"Search error: {e}")
        return {
            "success": False,
            "error": str(e),
            "candidates_found": len(all_candidates),
        }

    # Sort by score and limit to target count
    all_candidates.sort(key=lambda x: x["score"], reverse=True)
    final_candidates = all_candidates[:target_count]

    log_info(f"🎯 Search complete: {len(final_candidates)} candidates found")

    # Store in global state
    store_search_results(final_candidates)

    output = {
        "success": True,
        "candidates_found": len(final_candidates),
        "candidates": final_candidates,
        "message": f"Found {len(final_candidates)} candidates",
    }
    log_info(f"Search output: {output}")
    return output


def _extract_candidates_from_page() -> List[Dict[str, Any]]:
    """Extract candidate data from current search results page"""

    # First check if there are any results
    count_code = """
    (() => {
      const nodes = document.querySelectorAll('.search-results-container li');
      return nodes ? nodes.length : 0;
    })()
    """

    try:
        count = int(run_js(count_code) or 0)
        if count == 0:
            log_debug("No search result containers found on page")
            return []
    except:
        return []

    # Extract candidates using the proven logic from people_search.py
    extraction_code = """
    (() => {
      const containers = Array.from(document.querySelectorAll('.search-results-container li')).slice(0, 30);
      
      return containers.map(li => {
        const profileLink = li.querySelector('a[href*="/in/"]');
        const lines = li.textContent.split('\\n').map(l => l.trim()).filter(l => l && l !== 'Status is offline');
        
        // Find name using LinkedIn's pattern
        let name = null;
        for (const line of lines) {
          if ((line.includes("'s profile") || line.includes("'s profile") || line.includes("s profile")) && 
              line.includes("View ") && !line.includes('•') && !line.includes('degree')) {
            const viewIndex = line.indexOf('View ');
            if (viewIndex > 0) {
              const beforeView = line.substring(0, viewIndex).trim();
              if (beforeView.length > 2 && beforeView.length < 50) {
                name = beforeView;
                break;
              }
            }
          }
        }
        
        // Find headline - usually appears after connection info
        let headline = null;
        let foundConnectionLine = false;
        for (const line of lines) {
          if (line.includes('degree connection')) {
            foundConnectionLine = true;
            continue;
          }
          if (foundConnectionLine && line && !line.includes('degree') && !line.includes('View ') && 
              !line.includes('Status is') && !line.includes('Message') && line.length > 5) {
            headline = line;
            break;
          }
        }
        
        // If no headline found after connection, try to find any descriptive text
        if (!headline) {
          for (const line of lines) {
            // Skip common non-headline patterns
            if (line && 
                !line.includes('View ') &&
                !line.includes('degree') &&
                !line.includes('Status') &&
                !line.includes('Message') &&
                !line.includes('mutual') &&
                !line.includes('follower') &&
                line.length > 10 &&
                line.length < 200) {
              headline = line;
              break;
            }
          }
        }
        
        return {
          name: name || null,
          headline: headline || null,
          url: profileLink?.href || null
        };
      }).filter(x => x.url && x.name);
    })()
    """

    try:
        results = run_js(extraction_code)
        if results:
            log_debug(f"Extracted {len(results)} candidates from page")
        else:
            log_debug("No candidates extracted from page")
        return results if isinstance(results, list) else []
    except Exception as e:
        log_error(f"Extraction error: {e}")
        return []


def _debug_page_if_no_results():
    """Debug helper to understand why no results were extracted"""
    debug_code = """
    (() => {
      const info = {
        url: window.location.href,
        hasResults: false,
        containerCounts: {}
      };
      
      // Check various selectors
      const selectors = [
        'div.reusable-search__result-container',
        'li.reusable-search__result-container',
        '.entity-result',
        '.search-results__list > li',
        'ul.reusable-search__entity-result-list > li'
      ];
      
      selectors.forEach(sel => {
        const count = document.querySelectorAll(sel).length;
        if (count > 0) {
          info.containerCounts[sel] = count;
          info.hasResults = true;
        }
      });
      
      // Check for "no results" message
      const bodyText = document.body.textContent || '';
      info.hasNoResultsMessage = bodyText.includes('No results found') || 
                                  bodyText.includes('0 results');
      
      // Count profile links
      info.profileLinkCount = document.querySelectorAll('a[href*="/in/"]').length;
      
      return info;
    })()
    """

    try:
        debug_info = run_js(debug_code)
        log_debug(f"Page debug info: {debug_info}")
        if debug_info.get("hasNoResultsMessage"):
            log_debug("LinkedIn returned 'No results found' message")
        if debug_info.get("profileLinkCount", 0) > 0:
            log_debug(
                f"Found {debug_info['profileLinkCount']} profile links but extraction failed"
            )
    except Exception as e:
        log_debug(f"Debug failed: {e}")


# Note: We now use LLM-based quality assessment from quality_system instead of simple scoring
# This provides much more accurate and context-aware candidate evaluation

# Create AdalFlow Function Tool
SmartCandidateSearchTool = FunctionTool(fn=smart_candidate_search)
