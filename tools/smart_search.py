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
    min_score_threshold: float = 5.0,
    target_candidate_count: Optional[int] = None,
    quality_mode: str = "adaptive",  # "adaptive", "quality_first", "fast"
    extraction_quality_gate: float = 5.0  # Minimum heap average to proceed with extraction
) -> Dict[str, Any]:
    """
    Smart search for quality candidates using intelligent quality-driven system
    
    Args:
        query: Search query (role/title)
        location: Geographic location  
        strategy: AI-generated search strategy
        page_limit: Initial max pages to search (may be extended based on quality)
        min_score_threshold: Minimum headline score to include candidate
        target_candidate_count: Desired number of candidates (adaptive system may adjust)
        quality_mode: "adaptive" = extend search for quality, "quality_first" = prioritize quality over quantity, "fast" = respect hard limits
        extraction_quality_gate: Minimum heap average quality to proceed with extraction (0.0 = no gate)
        
    Returns:
        Dict with top quality candidates, quality metrics, and search decisions
    """
    
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
        # Main search loop with adaptive extension
        current_page_limit = budget.initial_page_limit
        page = 0
        
        while page < current_page_limit:
            print(f"📖 Searching page {page + 1}/{current_page_limit}")

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
            
            
            # Make adaptive decisions - include extraction quality gate check
            if quality_mode == "adaptive" and page >= budget.initial_page_limit:
                should_extend, reason = quality_analyzer.should_extend_search(current_stats, pages_searched)
                
                # Also check extraction quality gate
                extraction_ready = True
                if extraction_quality_gate > 0.0:
                    extraction_ready, gate_reason = candidate_heap.is_ready_for_extraction(
                        min_avg_threshold=extraction_quality_gate,
                        min_candidates=target_candidate_count or 3
                    )
                    if not extraction_ready:
                        should_extend = True
                        reason = f"extraction_gate_{gate_reason}"
                        print(f"   📊 Extraction gate requires more quality: {gate_reason}")
                
                if should_extend and current_page_limit < budget.max_page_limit:
                    old_limit = current_page_limit
                    current_page_limit = min(current_page_limit + 2, budget.max_page_limit)
                    search_decisions.append(f"extended_search_{reason}_from_{old_limit}_to_{current_page_limit}")
                    print(f"   🔄 Extending search: {reason} (pages: {old_limit} → {current_page_limit})")
                elif not should_extend and extraction_ready:
                    search_decisions.append(f"quality_sufficient_{reason}")
                    print(f"   ✅ Quality sufficient: {reason}")
                    break
                elif not extraction_ready and current_page_limit >= budget.max_page_limit:
                    search_decisions.append(f"max_pages_reached_quality_insufficient")
                    print(f"   ⚠️  Reached max pages but extraction gate not met")
                    break
                    
            # Check for quality plateau
            if len(quality_scores_history) >= thresholds.plateau_window:
                if quality_analyzer.detect_quality_plateau(quality_scores_history):
                    search_decisions.append("quality_plateau_detected")
                    print(f"   🏔️ Quality plateau detected - stopping search")
                    break
            
            # Small delay between pages
            time.sleep(2)
            # Move to next page
            page += 1
            pages_searched = page
    
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
    
    # Check extraction quality gate
    final_stats = candidate_heap.get_quality_stats()
    
    # Final extraction quality gate check (after all searching is done)
    if extraction_quality_gate > 0.0:
        ready_for_extraction, gate_reason = candidate_heap.is_ready_for_extraction(
            min_avg_threshold=extraction_quality_gate,
            min_candidates=target_candidate_count or 3
        )
        
        if not ready_for_extraction:
            print(f"\n🚫 Final extraction quality gate failed: {gate_reason}")
            print(f"   Current heap average: {final_stats.get('average', 0):.2f}")
            print(f"   Required average: {extraction_quality_gate}")
            print(f"   Searched {pages_searched} pages but quality insufficient for extraction")
            
            return {
                "success": False,
                "error": f"extraction_quality_gate_failed_{gate_reason}",
                "pages_searched": pages_searched,
                "candidates_found": final_stats['count'],
                "candidates_evaluated": candidates_evaluated,
                "search_query": search_query,
                "quality_stats": final_stats,
                "extraction_quality_gate": extraction_quality_gate,
                "gate_status": "failed",
                "gate_reason": gate_reason,
                "quality_candidates": [],  # Don't return candidates if gate failed
                "search_decisions": search_decisions,
                "recommendation": f"Lower extraction_quality_gate below {extraction_quality_gate} or search more sources"
            }
        else:
            print(f"\n✅ Extraction quality gate passed: {gate_reason}")
    
    # Get final results from quality heap - limit to target count but keep buffer for flexibility
    final_candidates = candidate_heap.get_top_candidates(limit=target_candidate_count)
    
    # Add old collector for backward compatibility
    collector = get_url_collector()
    for candidate in final_candidates:
        collector.add_candidate({
            'name': candidate.get('name', ''),
            'url': candidate.get('url', ''),
            'headline': candidate.get('headline', ''),
            'headline_score': candidate['quality_assessment'].overall_score
        })
    
    print(f"\n🎯 Quality-driven search completed!")
    print(f"   📊 Evaluated {candidates_evaluated} candidates across {pages_searched} pages")
    print(f"   ✅ Found {final_stats['count']} quality candidates")
    print(f"   📈 Quality range: {final_stats.get('min', 0):.1f} → {final_stats.get('max', 0):.1f} (avg: {final_stats.get('average', 0):.1f})")
    print(f"   📤 Returning {len(final_candidates)} candidates (heap holds {final_stats['count']} for flexibility)")
    print(f"   🧠 Search decisions: {', '.join(search_decisions)}")
    
    return {
        "success": True,
        "pages_searched": pages_searched,
        "candidates_found": final_stats['count'],
        "candidates_evaluated": candidates_evaluated,
        "total_candidates": final_stats['count'],  # From quality heap
        "search_query": search_query,
        "quality_threshold": min_score_threshold,
        
        # Quality system results
        "quality_stats": final_stats,
        "quality_candidates": final_candidates,
        "search_decisions": search_decisions,
        "quality_mode": quality_mode,
        "adaptive_extensions": len([d for d in search_decisions if "extended" in d]),
        
        # Heap buffer information
        "heap_size": effective_heap_size,
        "heap_buffer_multiplier": heap_buffer_multiplier,
        "total_heap_candidates": final_stats['count'],
        "returned_candidates": len(final_candidates),
        
        # Quality insights
        "quality_insights": {
            "exceptional_candidates": len([c for c in final_candidates if c['quality_assessment'].overall_score >= thresholds.exceptional_quality]),
            "target_candidates": len([c for c in final_candidates if c['quality_assessment'].overall_score >= thresholds.target_quality]),
            "acceptable_candidates": len([c for c in final_candidates if c['quality_assessment'].overall_score >= thresholds.minimum_acceptable]),
            "search_efficiency": final_stats['count'] / candidates_evaluated if candidates_evaluated > 0 else 0
        }
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