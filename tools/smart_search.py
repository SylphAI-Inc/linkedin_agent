"""
Smart Search Tool - Strategy-based candidate discovery
Finds quality candidates based on AI-generated strategy without extracting full profiles
"""

from typing import List, Dict, Any, Set, Optional
from urllib.parse import quote_plus
import time
import re

from adalflow.core.func_tool import FunctionTool
from .web_nav import js as run_js, go as nav_go, wait as nav_wait
from .linkedin_selectors import SEARCH_INPUT, PEOPLE_TAB, SEARCH_RESULTS_CARDS
from .people_search import evaluate_headline_with_strategy
from models.quality_system import (
    QualityThresholds, SearchBudget, CandidateHeap, QualityAnalyzer, CandidateQuality
)


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
        """Get all collected quality candidates (already sorted by heap system)"""
        # Heap system already provides candidates sorted by quality - no need to re-sort
        return self.quality_candidates.copy()


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
    start_page: int = 0,
    min_score_threshold: float = 7.0,
    target_candidate_count: Optional[int] = None,
    quality_mode: str = "adaptive",  # "adaptive", "quality_first", "fast"
    get_heap_backup: bool = False,  # NEW: Access backup candidates from previous search
    backup_offset: int = 0,         # NEW: Start position in heap for backup candidates  
    backup_limit: Optional[int] = None  # NEW: Number of backup candidates to return
) -> Dict[str, Any]:
    """
    Smart search for quality candidates using intelligent quality-driven system
    
    Args:
        query: Search query (role/title)
        location: Geographic location  
        strategy: AI-generated search strategy
        page_limit: Number of pages to search from start_page
        start_page: Page number to start searching from (0-indexed, allows continuation)
        min_score_threshold: Minimum headline score to include candidate
        target_candidate_count: Desired number of candidates (adaptive system may adjust)
        quality_mode: "adaptive" = extend search for quality, "quality_first" = prioritize quality over quantity, "fast" = respect hard limits
        get_heap_backup: If True, return backup candidates from existing heap instead of searching
        backup_offset: Starting position in heap for backup candidates (allows getting candidates beyond top results)
        backup_limit: Maximum number of backup candidates to return
        
    Returns:
        Dict with top quality candidates, quality metrics, and search decisions
    """
    
    # NEW: Handle heap backup mode - return candidates from existing collector
    if get_heap_backup:
        print(f"🔄 Accessing heap backup candidates (offset: {backup_offset}, limit: {backup_limit})")
        
        collector = get_url_collector()
        all_candidates = collector.get_candidates(sort_by_score=True)
        
        if not all_candidates:
            return {
                "success": False,
                "error": "No candidates in heap backup - perform initial search first",
                "backup_mode": True,
                "heap_total": 0,
                "candidates": []
            }
        
        # Apply offset and limit to get backup candidates
        backup_candidates = all_candidates[backup_offset:]
        if backup_limit:
            backup_candidates = backup_candidates[:backup_limit]
        
        print(f"📊 Heap backup: {len(backup_candidates)}/{len(all_candidates)} candidates (offset: {backup_offset})")
        
        return {
            "success": True,
            "backup_mode": True,
            "heap_total": len(all_candidates),
            "candidates_found": len(backup_candidates),
            "candidates": backup_candidates,
            "backup_offset": backup_offset,
            "backup_limit": backup_limit,
            "quality_stats": {
                "count": len(backup_candidates),
                "average": sum(c.get("headline_score", 0) for c in backup_candidates) / len(backup_candidates) if backup_candidates else 0,
                "backup_source": "url_collector_heap"
            },
            "search_decisions": [f"heap_backup_accessed_offset_{backup_offset}"]
        }
    
    # Initialize quality system components
    thresholds = QualityThresholds(
        minimum_acceptable=min_score_threshold,
        target_quality=min_score_threshold + 3.0,
        exceptional_quality=min_score_threshold + 6.0
    )
    
    budget = SearchBudget(
        initial_page_limit=page_limit,
        max_page_limit=min(page_limit * 2, 10) if quality_mode == "adaptive" else page_limit,
        min_acceptable_candidates=target_candidate_count or 3
    )
    
    # Use larger heap to provide candidate flexibility - buffer allows going back to good candidates
    # if top candidates are underwhelming during profile extraction
    heap_buffer_multiplier = 3  # Keep 3x more candidates than requested
    effective_heap_size = max((target_candidate_count or 5) * heap_buffer_multiplier, 20)
    candidate_heap = CandidateHeap(max_size=effective_heap_size, min_score_threshold=min_score_threshold)
    quality_analyzer = QualityAnalyzer(thresholds, budget)
    
    print(f"🔍 Quality-driven search: '{query}' in {location}")
    print(f"📊 Quality mode: {quality_mode}")
    print(f"🎯 Target candidates: {target_candidate_count or 'adaptive'}")
    print(f"🗂️  Heap size: {effective_heap_size} (buffer: {heap_buffer_multiplier}x for flexibility)")
    print(f"📊 Quality thresholds: min={thresholds.minimum_acceptable}, target={thresholds.target_quality}")
    print(f"📄 Page budget: {budget.initial_page_limit} → {budget.max_page_limit} (adaptive)")
    
    # Build search query - keep it simple for reliability
    search_query = f"{query} {location}".strip() if location else query
    print(f"🔍 Search query: '{search_query}'")
    
    pages_searched = 0
    candidates_evaluated = 0
    quality_scores_history = []
    search_decisions = []
    
    try:
        # Autonomous search loop - continues until thresholds met or hard limits reached
        page = start_page  # Start from specified page
        
        if start_page > 0:
            print(f"🔄 Continuing search from page {start_page + 1} (searched {start_page} pages previously)")
            search_decisions.append(f"continued_from_page_{start_page + 1}")
        
        # Internal threshold-based loop - tool decides when to stop
        while page < budget.max_page_limit:
            print(f"📖 Searching page {page + 1} (max: {budget.max_page_limit})")

            # Navigate to search page with proper pagination
            if page == 0:
                search_url = f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(search_query)}"
            else:
                # LinkedIn uses &page= parameter for pagination, not &start=
                search_url = f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(search_query)}&page={page + 1}"
            
            print(f"🌐 Navigating to: {search_url}")
            nav_go(search_url)
            nav_wait(3)  # Wait for page load
            
            # Check if we have search results on the page
            print(f"   🔍 Checking for search results...")
            
            # Extract raw candidate data and do integrated quality assessment
            raw_candidates = _extract_raw_candidate_data_from_page()
            print(f"   📊 Extracted {len(raw_candidates)} raw candidates from page")
            
            if not raw_candidates:
                print(f"❌ No results found on page {page}, stopping search")
                search_decisions.append(f"stopped_no_results_page_{page}")
                break
            
            pages_searched += 1
            page_candidates_added = 0
            page_quality_scores = []
            
            # Single-step processing: extract + assess quality + add to heap
            print(f"   🔍 Processing {len(raw_candidates)} candidates with quality assessment...")
            for i, raw_candidate in enumerate(raw_candidates, 1):
                candidates_evaluated += 1
                
                # Do headline scoring + comprehensive quality assessment in one step
                quality = quality_analyzer.assess_candidate_quality_integrated(raw_candidate, strategy, min_score_threshold)
                
                # Add to heap if quality is sufficient
                added, reason = candidate_heap.add_candidate(raw_candidate, quality)
                
                print(f"      Candidate {i}: {raw_candidate.get('name', 'Unknown')} - Score: {quality.overall_score:.2f} - {'✅' if added else '❌'}")
                
                if added:
                    page_candidates_added += 1
                    page_quality_scores.append(quality.overall_score)
                    quality_scores_history.append(quality.overall_score)
                
                if reason == "replaced_worse_candidate":
                    print(f"         ↗️ Replaced lower quality candidate")
                elif reason == "duplicate":
                    print(f"         🔄 Duplicate candidate")
                elif reason == "quality_too_low":
                    print(f"         📉 Quality too low for heap")
                elif reason == "below_minimum_threshold":
                    print(f"         🚫 Below minimum threshold ({min_score_threshold})")
            
            print(f"   ✅ {page_candidates_added} candidates passed quality threshold")
            print(f"   📊 Extracted {page_candidates_added} candidates from page")
            
            # Get current quality statistics
            current_stats = candidate_heap.get_quality_stats()
            print(f"   📈 Current heap: {current_stats['count']} candidates, avg quality: {current_stats.get('average', 0):.1f}")
            time.sleep(3)
            
            
            # Check if search thresholds are met (autonomous decision making)
            if page >= budget.initial_page_limit:  # Only check after minimum pages
                should_extend_quality, quality_reason = quality_analyzer.should_extend_search(current_stats, pages_searched)
                
                # Check capacity utilization
                capacity_utilization = candidate_heap.get_capacity_utilization()
                needs_more_capacity = candidate_heap.should_continue_search_for_capacity(budget.min_heap_capacity_pct)
                
                # Check minimum candidate count
                has_enough_candidates = len(candidate_heap.heap) >= (target_candidate_count or 3)
                
                # Simple decision: continue if ANY threshold not met
                if not should_extend_quality and not needs_more_capacity and has_enough_candidates:
                    search_decisions.append(f"thresholds_met_quality_{current_stats.get('average', 0):.1f}_capacity_{capacity_utilization:.1f}%_count_{len(candidate_heap.heap)}")
                    print(f"   ✅ All thresholds met: quality={current_stats.get('average', 0):.1f}, capacity={capacity_utilization:.1f}%, count={len(candidate_heap.heap)}")
                    break
                else:
                    # Log why continuing (for debugging)
                    reasons = []
                    if should_extend_quality:
                        reasons.append("quality_low")
                    if needs_more_capacity:
                        reasons.append(f"capacity_{capacity_utilization:.1f}%")
                    if not has_enough_candidates:
                        reasons.append(f"need_{target_candidate_count or 3}_have_{len(candidate_heap.heap)}")
                    
                    print(f"   🔄 Continuing search: {', '.join(reasons)}")
                    search_decisions.append(f"continuing_{'+'.join(reasons)}")
            else:
                print(f"   📖 Searching initial pages ({page + 1}/{budget.initial_page_limit})")
                    
            # Check for quality plateau
            if len(quality_scores_history) >= thresholds.plateau_window:
                if quality_analyzer.detect_quality_plateau(quality_scores_history):
                    search_decisions.append("quality_plateau_detected")
                    print(f"   🏔️ Quality plateau detected - stopping search")
                    break
            
            # Small delay between pages
            time.sleep(3)
            # Move to next page
            page += 1
            pages_searched = page - start_page  # Pages searched in this call
    
    except Exception as e:
        print(f"❌ Search error: {e}")
        return {
            "success": False,
            "error": str(e),
            "pages_searched": pages_searched,
            "candidates_found": 0,
            "candidates_evaluated": candidates_evaluated,
            "total_candidates": 0,
            "search_query": search_query,
            "quality_threshold": min_score_threshold,
            "start_page": start_page,
            "end_page": page if 'page' in locals() else start_page,
            "next_start_page": page if 'page' in locals() else start_page,
            "quality_stats": {"count": 0, "average": 0},
            "quality_candidates": [],
            "search_decisions": search_decisions,
            "quality_mode": quality_mode,
            "adaptive_extensions": 0,
            "quality_insights": {
                "exceptional_candidates": 0,
                "target_candidates": 0, 
                "acceptable_candidates": 0,
                "search_efficiency": 0
            }
        }
    
    # Get final results from quality heap
    final_stats = candidate_heap.get_quality_stats()
    final_candidates = candidate_heap.get_top_candidates(limit=target_candidate_count)
    
    print(f"\n🎯 Search complete:")
    print(f"   📊 Quality: avg={final_stats.get('average', 0):.1f}, count={final_stats['count']}")
    print(f"   📚 Heap capacity: {candidate_heap.get_capacity_utilization():.1f}%")
    print(f"   📄 Pages searched: {pages_searched}/{budget.max_page_limit}")
    print(f"   ✅ Returning {len(final_candidates)} top candidates for extraction")
    
    # Add candidates to collector with full quality assessment data
    collector = get_url_collector()
    for candidate in final_candidates:
        collector.add_candidate({
            'name': candidate.get('name', ''),
            'url': candidate.get('url', ''),
            'headline': candidate.get('headline', ''),
            'headline_score': candidate['quality_assessment'].overall_score,
            'quality_assessment': candidate['quality_assessment']  # Preserve full quality data
        })
    
    print(f"\n🎯 Quality-driven search completed!")
    print(f"   📊 Evaluated {candidates_evaluated} candidates across {pages_searched} pages")
    print(f"   ✅ Found {final_stats['count']} quality candidates")
    print(f"   📈 Quality range: {final_stats.get('min', 0):.1f} → {final_stats.get('max', 0):.1f} (avg: {final_stats.get('average', 0):.1f})")
    print(f"   📤 Returning {len(final_candidates)} candidates (heap holds {final_stats['count']} for flexibility)")
    print(f"   🧠 Search decisions: {', '.join(search_decisions)}")
    
    return {
        "success": True,
        "candidates": final_candidates,  # Main result for agent
        "candidates_found": len(final_candidates),
        "pages_searched": pages_searched,
        
        # CRITICAL: Page continuation info for expand_search_scope fallback
        "next_start_page": page,  # Where to continue searching from
        "search_exhausted": page >= budget.max_page_limit,
        
        # Quality summary (simplified for agent)
        "quality_stats": {
            "count": final_stats['count'], 
            "average": final_stats.get('average', 0),
            "heap_capacity_pct": candidate_heap.get_capacity_utilization()
        },
        
        # Internal data for debugging/monitoring
        "search_decisions": search_decisions,
        "total_heap_candidates": final_stats['count'],  # More in heap than returned
        "search_query": search_query
    }


def _extract_raw_candidate_data_from_page() -> List[Dict[str, Any]]:
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
          headline: subtitle || null,  // Use headline instead of subtitle for clarity
          url: profileLink?.href || null
        }};
      }}).filter(x => x.url && x.name);
    }})()
    """
    
    try:
        print(f"   🛠️  Running JavaScript extraction...")
        results = run_js(extraction_code)
        
        if results is None or not isinstance(results, list):
            print(f"   ⚠️  JavaScript returned invalid data: {results}")
            return []
        
        # Return raw candidate data - no scoring here
        return [
            {
                'name': candidate.get('name', ''),
                'headline': candidate.get('headline', ''),
                'url': candidate.get('url', '')
            }
            for candidate in results
            if candidate.get('name') and candidate.get('url')
        ]
        
    except Exception as e:
        print(f"   ❌ Extraction error: {e}")
        return []


def get_heap_candidates(heap: 'CandidateHeap', limit: int = None, offset: int = 0) -> Dict[str, Any]:
    """Get candidates from the quality heap with optional offset for accessing backup candidates"""
    all_candidates = heap.get_top_candidates()  # Get all candidates from heap
    
    # Apply offset and limit
    candidates = all_candidates[offset:]
    if limit:
        candidates = candidates[:limit]
        
    return {
        "total_in_heap": len(all_candidates),
        "returned_count": len(candidates),
        "candidates": candidates,
        "heap_stats": heap.get_quality_stats()
    }

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