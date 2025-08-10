"""
Result saving functionality - separated for better modularity
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


def save_recruitment_results(candidates: List[Dict[str, Any]], 
                           search_params: Dict[str, Any], 
                           output_dir: str = "results") -> Dict[str, str]:
    """Save recruitment results to files with clean separation"""
    
    # Get repo root and create results directory
    current_file = Path(__file__).resolve()
    repo_root = current_file.parents[1]  # Go up from runner/ to repo root
    results_dir = repo_root / output_dir
    results_dir.mkdir(exist_ok=True)
    
    # Generate timestamp and clean filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    query_clean = search_params["query"].replace(" ", "_").replace("/", "_")[:30]
    
    # Save detailed JSON results
    json_file = results_dir / f"linkedin_search_{query_clean}_{timestamp}.json"
    
    detailed_results = {
        "search_metadata": {
            "timestamp": datetime.now().isoformat(),
            **search_params,
            "total_found": len(candidates)
        },
        "candidates": candidates
    }
    
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(detailed_results, f, indent=2, ensure_ascii=False)
    
    # Save human-readable summary
    txt_file = results_dir / f"linkedin_summary_{query_clean}_{timestamp}.txt"
    
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(f"LinkedIn Recruitment Results\n")
        f.write(f"=" * 50 + "\n\n")
        f.write(f"Search Query: {search_params['query']}\n")
        f.write(f"Location: {search_params['location']}\n")
        f.write(f"Enhanced Prompting: {'Yes' if search_params.get('enhanced_prompting') else 'No'}\n")
        f.write(f"Strategy Used: {'Yes' if search_params.get('strategy_used') else 'No'}\n")
        f.write(f"Limit: {search_params['limit']}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Results Found: {len(candidates)}\n\n")
        
        for i, candidate in enumerate(candidates, 1):
            search_info = candidate.get("search_info", {})
            profile_info = candidate.get("profile_details", {})
            
            f.write(f"--- Candidate {i} ---\n")
            f.write(f"Name: {_safe_get(profile_info, 'name', _safe_get(search_info, 'name', 'N/A'))}\n")
            f.write(f"Title: {_safe_get(profile_info, 'headline', _safe_get(search_info, 'subtitle', 'N/A'))}\n")
            f.write(f"Location: {_safe_get(profile_info, 'location', 'N/A')}\n")
            f.write(f"LinkedIn URL: {_safe_get(search_info, 'url', 'N/A')}\n")
            
            # Add about section if available
            about = _safe_get(profile_info, 'about')
            if about and about != 'N/A' and isinstance(about, str):
                f.write(f"About: {about[:200]}{'...' if len(about) > 200 else ''}\n")
            
            # Add experience summary
            experiences = _safe_get(profile_info, 'experiences')
            if experiences and experiences != 'N/A' and isinstance(experiences, list) and len(experiences) > 0:
                f.write(f"Recent Experience:\n")
                for exp in experiences[:2]:  # Show first 2 experiences
                    if isinstance(exp, dict):
                        f.write(f"  • {_safe_get(exp, 'title', 'N/A')} at {_safe_get(exp, 'company', 'N/A')}\n")
            
            # Add data quality if available
            quality = _safe_get(profile_info, 'data_quality', {})
            if isinstance(quality, dict) and quality.get('completeness_percentage'):
                f.write(f"Profile Completeness: {quality['completeness_percentage']}%\n")
            
            f.write("\n")
    
    return {
        "json_file": str(json_file),
        "txt_file": str(txt_file),
        "candidates_count": len(candidates)
    }


def _safe_get(obj: Any, key: str, default: str = 'N/A') -> str:
    """Safely get value from dict-like object"""
    if isinstance(obj, dict):
        return str(obj.get(key, default))
    return default