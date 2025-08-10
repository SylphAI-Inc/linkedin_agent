"""
Targeted Extraction Tool - Extract profiles from quality candidate URLs
Since URLs are pre-filtered for quality, focus on reliable extraction and basic validation
"""

from typing import List, Dict, Any
import time

from adalflow.core.func_tool import FunctionTool
from .web_nav import go as nav_go, wait as nav_wait
from .profile_extractor import extract_profile  # Use existing extraction function
from .smart_search import get_url_collector


def extract_candidate_profiles(
    candidate_limit: int = None,
    delay_between_extractions: float = 1.0,
    validate_extraction: bool = True
) -> Dict[str, Any]:
    """
    Extract profiles from collected quality candidate URLs
    
    Args:
        candidate_limit: Max number of candidates to extract (None = all)
        delay_between_extractions: Delay between extractions (seconds)
        validate_extraction: Whether to validate extracted data
        
    Returns:
        Dict with extracted profiles and extraction statistics
    """
    
    collector = get_url_collector()
    candidates = collector.get_candidates(sort_by_score=True)  # Get candidates sorted by score
    
    if not candidates:
        return {
            "success": False,
            "error": "No candidates available for extraction",
            "extracted_count": 0,
            "failed_count": 0,
            "results": []
        }
    
    # Limit candidates if specified - now getting the TOP candidates by score
    if candidate_limit:
        candidates = candidates[:candidate_limit]
        print(f"🎯 Selected top {len(candidates)} candidates by headline score")
        if candidates:
            print(f"📊 Score range: {candidates[0].get('headline_score', 0):.1f} (highest) to {candidates[-1].get('headline_score', 0):.1f} (lowest)")
    
    print(f"🎯 Starting targeted extraction for {len(candidates)} candidates")
    print(f"⏱️  Delay between extractions: {delay_between_extractions}s")
    
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
            print(f"❌ {i}/{len(candidates)}: No URL for {name}")
            failed_extractions.append({
                "candidate": candidate,
                "error": "Missing URL"
            })
            extraction_stats["failed"] += 1
            continue
        
        extraction_stats["attempted"] += 1
        
        try:
            print(f"📥 {i}/{len(candidates)}: Extracting {name}")
            print(f"   URL: {url}")
            
            # Navigate to profile
            nav_go(url)
            nav_wait(2)  # Wait for page load
            
            # Extract profile data
            profile_data = extract_profile()
            
            if validate_extraction:
                validation_result = _validate_extracted_profile(profile_data, candidate)
                if validation_result["valid"]:
                    extraction_stats["validation_passed"] += 1
                    print(f"   ✅ Extracted and validated: {profile_data.get('name', name)}")
                else:
                    extraction_stats["validation_failed"] += 1
                    print(f"   ⚠️  Extracted but validation issues: {validation_result['issues']}")
            else:
                extraction_stats["validation_passed"] += 1
                print(f"   ✅ Extracted: {profile_data.get('name', name)}")
            
            # Combine candidate info with extracted profile
            result = {
                "candidate_info": candidate,
                "profile_data": profile_data,
                "extraction_success": True,
                "extraction_timestamp": time.time()
            }
            
            if validate_extraction:
                result["validation"] = validation_result
            
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
    
    print(f"\n📊 EXTRACTION SUMMARY:")
    print(f"   Total candidates: {len(candidates)}")
    print(f"   Attempted: {extraction_stats['attempted']}")
    print(f"   Successful: {extraction_stats['successful']}")
    print(f"   Failed: {extraction_stats['failed']}")
    print(f"   Success rate: {success_rate:.1f}%")
    
    if validate_extraction:
        print(f"   Validation passed: {extraction_stats['validation_passed']}")
        print(f"   Validation issues: {extraction_stats['validation_failed']}")
    
    return {
        "success": True,
        "extracted_count": extraction_stats["successful"],
        "failed_count": extraction_stats["failed"],
        "success_rate": success_rate,
        "statistics": extraction_stats,
        "results": extracted_profiles,
        "failed_extractions": failed_extractions
    }


def _validate_extracted_profile(profile_data: Dict[str, Any], candidate_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate extracted profile data against original candidate info
    
    Args:
        profile_data: Extracted profile data
        candidate_info: Original candidate info from search
        
    Returns:
        Validation result with issues list
    """
    
    issues = []
    valid = True
    
    # Check if profile_data is valid dict
    if not isinstance(profile_data, dict):
        issues.append("Profile data is not a valid dictionary")
        valid = False
        return {"valid": False, "issues": issues}
    
    # Handle both direct profile data and wrapped profile data structures
    # Some extraction methods return wrapped data with 'profile_data' key
    actual_profile_data = profile_data
    if 'profile_data' in profile_data and isinstance(profile_data['profile_data'], dict):
        actual_profile_data = profile_data['profile_data']
    
    # Basic data presence checks
    extracted_name = actual_profile_data.get('name', '').strip()
    expected_name = candidate_info.get('name', '').strip()
    
    if not extracted_name:
        issues.append("Missing name in extracted profile")
        valid = False
    elif expected_name and extracted_name.lower() != expected_name.lower():
        # Allow slight variations but flag major mismatches
        if not any(word in extracted_name.lower() for word in expected_name.lower().split()):
            issues.append(f"Name mismatch: expected '{expected_name}', got '{extracted_name}'")
            # Don't mark as invalid for name mismatch - could be LinkedIn display variations
    
    # Check headline presence
    extracted_headline = actual_profile_data.get('headline', '').strip()
    expected_headline = candidate_info.get('headline', '').strip()
    
    if not extracted_headline:
        issues.append("Missing headline in extracted profile")
        # Don't mark as invalid - some profiles may not have headlines visible
    
    # Check for basic profile completeness
    required_fields = ['name', 'url']
    for field in required_fields:
        if not actual_profile_data.get(field):
            issues.append(f"Missing required field: {field}")
            valid = False
    
    # Check URL consistency
    extracted_url = actual_profile_data.get('url', '')
    expected_url = candidate_info.get('url', '') or candidate_info.get('normalized_url', '')
    
    if extracted_url and expected_url:
        # Normalize URLs for comparison
        extracted_normalized = extracted_url.split('?')[0].rstrip('/').lower()
        expected_normalized = expected_url.split('?')[0].rstrip('/').lower()
        
        if extracted_normalized != expected_normalized:
            issues.append(f"URL mismatch: navigation vs extracted")
            # Don't mark as invalid - could be URL variations
    
    # Check if profile seems to be a feed or error page
    if extracted_name.lower() in ['feed updates', 'linkedin', 'error']:
        issues.append("Profile appears to be a feed/error page")
        valid = False
    
    return {
        "valid": valid,
        "issues": issues,
        "extracted_name": extracted_name,
        "expected_name": expected_name
    }


def get_extraction_summary() -> Dict[str, Any]:
    """Get summary of current extraction status"""
    collector = get_url_collector()
    total_candidates = collector.get_candidate_count()
    candidates = collector.get_candidates()
    
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
    collector = get_url_collector()
    candidates = collector.get_candidates()
    
    for candidate in candidates:
        candidate_url = candidate.get('url') or candidate.get('normalized_url')
        if candidate_url and candidate_url == url:
            candidate['extracted'] = True
            return True
    
    return False


# Create AdalFlow Function Tools
ExtractCandidateProfilesTool = FunctionTool(fn=extract_candidate_profiles)
GetExtractionSummaryTool = FunctionTool(fn=get_extraction_summary)