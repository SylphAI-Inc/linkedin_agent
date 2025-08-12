"""
Result saving functionality - separated for better modularity
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


def save_recruitment_results(candidates: List[Dict[str, Any]], 
                           search_params: Dict[str, Any], 
                           output_dir: str = "results",
                           strategy_data: Dict[str, Any] = None,
                           outreach_data: Dict[str, Any] = None) -> Dict[str, str]:
    """Save recruitment results to multiple files: scoring summary + detailed candidate info"""
    
    # Get repo root and create results directory
    current_file = Path(__file__).resolve()
    repo_root = current_file.parents[1]  # Go up from runner/ to repo root
    results_dir = repo_root / output_dir
    results_dir.mkdir(exist_ok=True)
    
    # Generate timestamp and clean filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    query_clean = search_params["query"].replace(" ", "_").replace("/", "_")[:30]
    
    # File paths for different types of data
    evaluation_file = results_dir / f"linkedin_evaluation_{query_clean}_{timestamp}.json"
    candidates_file = results_dir / f"linkedin_candidates_{query_clean}_{timestamp}.json"
    
    # Prepare evaluation results data
    evaluation_summary = {
        "search_metadata": {
            "timestamp": datetime.now().isoformat(),
            **search_params,
            "total_found": len(candidates)
        },
        "candidate_evaluations": _extract_candidate_evaluations(candidates, strategy_data)
    }
    
    # Prepare detailed candidate data
    candidate_details = {
        "search_metadata": {
            "timestamp": datetime.now().isoformat(),
            **search_params,
            "total_found": len(candidates)
        },
        "candidates": _extract_candidate_details(candidates)
    }
    
    # Save evaluation results
    with open(evaluation_file, "w", encoding="utf-8") as f:
        json.dump(evaluation_summary, f, indent=2, ensure_ascii=False)
    
    # Save detailed candidate information
    with open(candidates_file, "w", encoding="utf-8") as f:
        json.dump(candidate_details, f, indent=2, ensure_ascii=False)
    
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
    
    # Save outreach results separately if provided (for compatibility with existing workflow)
    outreach_file = None
    if outreach_data:
        try:
            from tools.candidate_outreach import save_outreach_results
            outreach_file = save_outreach_results(outreach_data)
            print("📧 Outreach results saved alongside other recruitment data")
        except Exception as e:
            print(f"⚠️  Could not save outreach results: {e}")
            outreach_file = None
    
    result = {
        "evaluation_file": str(evaluation_file),
        "candidates_file": str(candidates_file), 
        "txt_file": str(txt_file),
        "candidates_count": len(candidates)
    }
    
    # Add outreach file to results if it was saved
    if outreach_file:
        result["outreach_file"] = outreach_file
    
    return result


def _extract_candidate_evaluations(candidates: List[Dict[str, Any]], strategy_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Extract complete evaluation results from candidates exactly as generated by evaluation tool"""
    evaluations = []
    
    for candidate in candidates:
        # Basic candidate info
        evaluation_data = {
            "name": _safe_get(candidate.get("profile_details", {}), "name"),
            "headline": _safe_get(candidate.get("profile_details", {}), "headline"),
            "url": _safe_get(candidate.get("search_info", {}), "url"),
            "headline_score": candidate.get("search_info", {}).get("headline_score", 0.0)
        }
        
        # Add complete evaluation results if available
        quality = candidate.get("profile_details", {}).get("quality_assessment")
        if quality and isinstance(quality, dict):
            # Store all evaluation results as-is from the evaluation tool
            evaluation_data.update({
                "overall_score": quality.get("overall_score", 0.0),
                "component_scores": quality.get("component_scores", {}),
                "strategic_bonuses": quality.get("strategic_bonuses", {}),
                "scoring_weights": quality.get("scoring_weights", {}),
                "final_multiplier": quality.get("final_multiplier", 1.0),
                "meets_threshold": quality.get("meets_threshold", False),
                "strengths": quality.get("strengths", []),
                "concerns": quality.get("concerns", []),
                "evaluation_timestamp": quality.get("evaluation_timestamp", ""),
                "baseline_scores": quality.get("baseline_scores", {})
            })
        else:
            # Fallback for candidates without evaluation
            evaluation_data.update({
                "overall_score": 0.0,
                "component_scores": {},
                "strategic_bonuses": {},
                "meets_threshold": False,
                "strengths": [],
                "concerns": ["No detailed evaluation available"]
            })
        
        # Add outreach data if available
        outreach_info = candidate.get("profile_details", {}).get("outreach_info", {})
        if outreach_info:
            evaluation_data["outreach_data"] = {
                "recommend_outreach": outreach_info.get("recommend_outreach", False),
                "outreach_score": outreach_info.get("outreach_score", 0.0),
                "outreach_reasoning": outreach_info.get("outreach_reasoning", ""),
                "personalized_message_available": bool(outreach_info.get("message", ""))
            }
        
        evaluations.append(evaluation_data)
    
    return evaluations


def _extract_candidate_details(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract detailed candidate information (experiences, education, etc.)"""
    details = []
    
    for candidate in candidates:
        profile_details = candidate.get("profile_details", {})
        
        detail_data = {
            "name": _safe_get(profile_details, "name"),
            "headline": _safe_get(profile_details, "headline"),
            "url": _safe_get(profile_details, "url"),
            "location": _safe_get(profile_details, "location"),
            "about": _safe_get(profile_details, "about"),
            "experiences": profile_details.get("experiences", []),
            "education": profile_details.get("education", []),
            "skills": profile_details.get("skills", []),
            "data_quality": profile_details.get("data_quality", {}),
            "extraction_metadata": {
                "extraction_quality": profile_details.get("quality_assessment", {}).get("extraction_quality", 0.0),
                "profile_completeness": profile_details.get("quality_assessment", {}).get("profile_completeness", 0.0),
                "timestamp": profile_details.get("quality_assessment", {}).get("timestamp")
            }
        }
        
        details.append(detail_data)
    
    return details



def _safe_get(obj: Any, key: str, default: str = 'N/A') -> str:
    """Safely get value from dict-like object"""
    if isinstance(obj, dict):
        return str(obj.get(key, default))
    return default