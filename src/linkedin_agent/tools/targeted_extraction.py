"""
Targeted Extraction Tool - Extract profiles from quality candidate URLs
Since URLs are pre-filtered for quality, focus on reliable extraction and basic validation
"""

from typing import Dict, Any, Optional
import time

from adalflow.core.func_tool import FunctionTool
from .web_nav import go as nav_go, wait as nav_wait
from .profile_extractor import extract_profile  # Use existing extraction function
# URL collector removed - using workflow state directly
from ..core.workflow_state import get_candidates_for_extraction, store_extraction_results
from ..utils.logger import log_info, log_debug, log_error, log_progress


def extract_candidate_profiles(
    candidate_limit: int | None = None,
    delay_between_extractions: Optional[float] = None,
    validate_extraction: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Extract profiles using global state architecture
    
    Args:
        candidate_limit: Max number of candidates to extract (None = all)
        delay_between_extractions: Delay between extractions (uses config default if None)
        validate_extraction: Whether to validate extracted data (uses config default if None)
        
    Returns:
        Lightweight status dict: {success: True, extracted_count: 10}
        Actual extracted profiles stored in global state
    """
    
    # Load user configuration for defaults
    from ..config_user import get_extraction_config
    extraction_config = get_extraction_config()
    
    # Use config defaults if not provided
    if delay_between_extractions is None:
        delay_between_extractions = extraction_config.delay_between_extractions
    if validate_extraction is None:
        validate_extraction = extraction_config.validate_extraction_quality
    
    # Get candidates from global state (automatically populated by search)
    candidates = get_candidates_for_extraction()
    
    if not candidates:
        return {
            "success": False,
            "error": "No candidates found in global state. Run smart_candidate_search first.",
            "extracted_count": 0,
            "failed_count": 0
        }
    
    log_info(f"🔄 Retrieved {len(candidates)} candidates from global state for extraction", phase="EXTRACTION")
    
    # Limit candidates if specified - now getting the TOP candidates by score
    if candidate_limit:
        candidates = candidates[:candidate_limit]
        log_info(f"🎯 Selected top {len(candidates)} candidates by headline score", phase="EXTRACTION")
        if candidates:
            log_debug(f"📊 Score range: {candidates[0].get('headline_score', 0):.1f} (highest) to {candidates[-1].get('headline_score', 0):.1f} (lowest)", phase="EXTRACTION")
    
    log_info(f"🎯 Starting targeted extraction for {len(candidates)} candidates", phase="EXTRACTION")
    log_debug(f"⏱️  Delay between extractions: {delay_between_extractions}s", phase="EXTRACTION")
    
    extracted_profiles = []
    failed_extractions = []
    extraction_stats = {
        "attempted": 0,
        "successful": 0,
        "failed": 0,
        "validation_passed": 0,
        "validation_failed": 0
    }
    
    for i, candidate in enumerate(candidates, 1):
        url = candidate.get('url') or candidate.get('normalized_url')
        name = candidate.get('name', 'Unknown')
        
        if not url:
            log_error(f"❌ {i}/{len(candidates)}: No URL for {name}", phase="EXTRACTION")
            failed_extractions.append({
                "candidate": candidate,
                "error": "Missing URL"
            })
            extraction_stats["failed"] += 1
            continue
        
        extraction_stats["attempted"] += 1
        
        try:
            log_progress(f"Extracting {name} ({i}/{len(candidates)})", "EXTRACTION")
            log_debug(f"   URL: {url}", phase="EXTRACTION")
            
            # Navigate to profile
            nav_go(url)
            nav_wait('2')  # Wait for page load
            
            # Extract profile data
            profile_data = extract_profile()
            
            # Combine candidate info with extracted profile
            result = {
                "candidate_info": candidate,
                "profile_data": profile_data,
                "extraction_success": True,
                "extraction_timestamp": time.time()
            }
            
            extracted_profiles.append(result)
            extraction_stats["successful"] += 1
            
        except Exception as e:
            print(f"   ❌ Extraction failed: {e}")
            failed_extractions.append({
                "candidate": candidate,
                "error": str(e)
            })
            extraction_stats["failed"] += 1
        
        # Delay between extractions to avoid rate limiting
        if i < len(candidates):
            time.sleep(delay_between_extractions)
    
    success_rate = (extraction_stats["successful"] / extraction_stats["attempted"] * 100) if extraction_stats["attempted"] > 0 else 0
    
    print("\n📊 EXTRACTION SUMMARY:")
    print(f"   Total candidates: {len(candidates)}")
    print(f"   Attempted: {extraction_stats['attempted']}")
    print(f"   Successful: {extraction_stats['successful']}")
    print(f"   Failed: {extraction_stats['failed']}")
    print(f"   Success rate: {success_rate:.1f}%")
    
    
    # Store extraction results in global state
    extraction_data = {
        "results": extracted_profiles,
        "statistics": extraction_stats,
        "failed_extractions": failed_extractions
    }
    global_state_result = store_extraction_results(extraction_data)
    print(f"💾 {global_state_result.get('message', 'Extraction results stored in global state')}")
    
    # Return lightweight status for agent
    output = {
        "success": True,
        "extracted_count": extraction_stats["successful"],
        "failed_count": extraction_stats["failed"],
        "success_rate": success_rate,
        "message": f"Extracted {extraction_stats['successful']} profiles, stored in global state"
    }
    log_info(message=f"Extraction completed: {output}", phase="EXTRACTION")
    return output


# def _validate_extracted_profile(profile_data: Dict[str, Any], candidate_info: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Validate extracted profile data against original candidate info
    
#     Args:
#         profile_data: Extracted profile data
#         candidate_info: Original candidate info from search
        
#     Returns:
#         Validation result with issues list
#     """
    
#     issues = []
#     valid = True
    
#     # Check if profile_data is valid dict
#     if not isinstance(profile_data, dict):
#         issues.append("Profile data is not a valid dictionary")
#         valid = False
#         return {"valid": False, "issues": issues}
    
#     # Handle both direct profile data and wrapped profile data structures
#     # Some extraction methods return wrapped data with 'profile_data' key
#     actual_profile_data = profile_data
#     if 'profile_data' in profile_data and isinstance(profile_data['profile_data'], dict):
#         actual_profile_data = profile_data['profile_data']
    
#     # Basic data presence checks
#     extracted_name = actual_profile_data.get('name', '').strip()
#     expected_name = candidate_info.get('name', '').strip()
    
#     if not extracted_name:
#         issues.append("Missing name in extracted profile")
#         valid = False
#     elif expected_name and extracted_name.lower() != expected_name.lower():
#         # Allow slight variations but flag major mismatches
#         if not any(word in extracted_name.lower() for word in expected_name.lower().split()):
#             issues.append(f"Name mismatch: expected '{expected_name}', got '{extracted_name}'")
#             # Don't mark as invalid for name mismatch - could be LinkedIn display variations
    
#     # Check headline presence
#     extracted_headline = actual_profile_data.get('headline', '').strip()
#     expected_headline = candidate_info.get('headline', '').strip()
    
#     if not extracted_headline:
#         issues.append("Missing headline in extracted profile")
#         # Don't mark as invalid - some profiles may not have headlines visible
    
#     # Check for basic profile completeness
#     required_fields = ['name', 'url']
#     for field in required_fields:
#         if not actual_profile_data.get(field):
#             issues.append(f"Missing required field: {field}")
#             valid = False
    
#     # Check URL consistency
#     extracted_url = actual_profile_data.get('url', '')
#     expected_url = candidate_info.get('url', '') or candidate_info.get('normalized_url', '')
    
#     if extracted_url and expected_url:
#         # Normalize URLs for comparison
#         extracted_normalized = extracted_url.split('?')[0].rstrip('/').lower()
#         expected_normalized = expected_url.split('?')[0].rstrip('/').lower()
        
#         if extracted_normalized != expected_normalized:
#             issues.append(f"URL mismatch: navigation vs extracted")
#             # Don't mark as invalid - could be URL variations
    
#     # Check if profile seems to be a feed or error page
#     if extracted_name.lower() in ['feed updates', 'linkedin', 'error']:
#         issues.append("Profile appears to be a feed/error page")
#         valid = False
    
#     return {
#         "valid": valid,
#         "issues": issues,
#         "extracted_name": extracted_name,
#         "expected_name": expected_name
#     }


def get_extraction_summary() -> Dict[str, Any]:
    """Get summary of current extraction status"""
    # Get candidates from workflow state
    candidates = get_candidates_for_extraction()
    total_candidates = len(candidates)
    
    # Count how many have been extracted
    extracted_count = sum(1 for c in candidates if c.get('extracted', False))
    pending_count = total_candidates - extracted_count
    
    return {
        "total_candidates": total_candidates,
        "extracted_count": extracted_count,
        "pending_count": pending_count,
        "candidates": candidates
    }


def mark_candidate_extracted(url: str) -> bool:
    """Mark a candidate as extracted (internal tracking)"""
    # Get candidates from workflow state
    candidates = get_candidates_for_extraction()
    
    for candidate in candidates:
        candidate_url = candidate.get('url') or candidate.get('normalized_url')
        if candidate_url and candidate_url == url:
            candidate['extracted'] = True
            return True
    
    return False


# Create AdalFlow Function Tools
ExtractCandidateProfilesTool = FunctionTool(fn=extract_candidate_profiles)
GetExtractionSummaryTool = FunctionTool(fn=get_extraction_summary)