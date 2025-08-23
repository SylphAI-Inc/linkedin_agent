#!/usr/bin/env python3
"""
Candidate Evaluation Tool - LLM-powered quality assessment for extracted profiles
Provides intelligent fallback recommendations based on evaluation results
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from adalflow.core.func_tool import FunctionTool
from ..core.workflow_state import get_profiles_for_evaluation, store_evaluation_results, get_workflow_summary, _workflow_state
from ..utils.logger import log_info, log_debug, log_error, log_progress
from ..models.quality_system import QualityGenerator, CandidateAssessment


def evaluate_candidates_quality(
    min_quality_threshold: Optional[float] = None,
    target_count: Optional[int] = None
) -> Dict[str, Any]:
    """
    Comprehensive evaluation using global state architecture
    
    Args:
        min_quality_threshold: Minimum acceptable quality score (uses config default if None)
        target_count: Target number of quality candidates needed (uses config default if None)
        
    Returns:
        Lightweight status dict: {success: True, candidates_evaluated: 10, quality_sufficient: True}
        Actual evaluation results stored in global state
    """
    
    # Load user configuration for defaults
    from ..config_user import get_search_config
    search_config = get_search_config()
    
    # Use config defaults if not provided
    if min_quality_threshold is None:
        min_quality_threshold = search_config.min_evaluation_threshold
    if target_count is None:
        target_count = search_config.target_quality_candidates
    
    log_info(f"🎯 Starting comprehensive candidate evaluation...", phase="EVALUATION")
    log_info(f"   Quality threshold: {min_quality_threshold}, Target count: {target_count}", phase="EVALUATION")
    log_progress("Initializing evaluation system", "EVALUATION")
    
    # Get candidates from global state
    candidates = get_profiles_for_evaluation()
    
    # Initialize LLM quality generator
    quality_generator = QualityGenerator()
    
    # Get role query from workflow state or use default
    workflow_summary = get_workflow_summary()
    role_query = workflow_summary.get('search_query', 'Software Engineer')
    job_requirements = workflow_summary.get('job_requirements', '')
    
    log_debug(f"Retrieved candidates type: {type(candidates)}", phase="EVALUATION")
    log_debug(f"Retrieved candidates length: {len(candidates) if isinstance(candidates, list) else 'N/A'}", phase="EVALUATION")
    if candidates and isinstance(candidates, list):
        log_debug(f"First candidate keys: {list(candidates[0].keys()) if candidates[0] else 'Empty'}", phase="EVALUATION")
    
    # Enhanced debug logging for empty candidates case
    if not candidates:
        log_error(f"No candidates found in global state for evaluation", phase="EVALUATION")
        log_debug(f"Checking global workflow state...", phase="EVALUATION")
        
        workflow_status = get_workflow_summary()
        log_debug(f"Current workflow phase: {workflow_status.get('current_phase')}", phase="EVALUATION")
        log_debug(f"Candidates extracted: {workflow_status.get('candidates_extracted')}", phase="EVALUATION")
        log_debug(f"Raw extraction results count: {len(_workflow_state._extraction_results)}", phase="EVALUATION")
        
        # Check if extraction results exist but are in wrong format
        extraction_results = _workflow_state._extraction_results
        if extraction_results:
            log_debug(f"Extraction results exist but appear malformed:", phase="EVALUATION")
            log_debug(f"First extraction result type: {type(extraction_results[0])}", phase="EVALUATION")
            log_debug(f"First extraction result keys: {list(extraction_results[0].keys()) if isinstance(extraction_results[0], dict) else 'Not dict'}", phase="EVALUATION")
        
        return {
            "success": False,
            "error": "No candidates found in global state. Run extract_candidate_profiles first.",
            "quality_sufficient": False,
            "candidates_evaluated": 0,
            "debug_info": {
                "workflow_phase": workflow_status.get('current_phase'),
                "candidates_extracted_count": workflow_status.get('candidates_extracted'),
                "raw_extraction_count": len(_workflow_state._extraction_results)
            }
        }
    
    log_info(f"📊 PHASE 2: Starting LLM-powered candidate assessment...")
    log_info(f"   Processing {len(candidates)} candidates with AI evaluation")
    
    # LLM-powered evaluation
    evaluated_candidates = []
    quality_stats = {
        "total_evaluated": 0,
        "above_threshold": 0,
        "below_threshold": 0,
        "scores": []
    }
    
    for i, candidate in enumerate(candidates, 1):
        candidate_name = _extract_candidate_name(candidate)
        log_info(f"   🔍 Evaluating candidate {i}: {candidate_name}")
        
        # Prepare candidate data for LLM assessment
        candidate_data = _prepare_candidate_for_llm(candidate)
        
        # Get LLM quality assessment
        llm_assessment = quality_generator.assess_candidate_quality_llm(
            candidate_data=candidate_data,
            role_query=role_query,
            job_requirements=job_requirements
        )
        
        # Convert LLM assessment to evaluation result format
        evaluation_result = _convert_llm_assessment_to_result(llm_assessment, candidate)
        evaluation_result["meets_threshold"] = llm_assessment.overall_score >= min_quality_threshold
        evaluated_candidates.append(evaluation_result)
        
        # Track statistics
        quality_stats["total_evaluated"] += 1
        quality_stats["scores"].append(llm_assessment.overall_score)
        
        if llm_assessment.overall_score >= min_quality_threshold:
            quality_stats["above_threshold"] += 1
        else:
            quality_stats["below_threshold"] += 1
    
    # Calculate quality metrics
    avg_score = sum(quality_stats["scores"]) / len(quality_stats["scores"]) if quality_stats["scores"] else 0
    max_score = max(quality_stats["scores"]) if quality_stats["scores"] else 0
    min_score = min(quality_stats["scores"]) if quality_stats["scores"] else 0
    
    # Determine if quality is sufficient
    # If we have fewer total candidates than target, check if we have enough relative to what we evaluated
    candidates_available = len(candidates)
    effective_target = min(target_count, candidates_available)
    quality_sufficient = quality_stats["above_threshold"] >= effective_target
    
    # HEAP CLEANUP: Remove low-quality candidates from search heap
    log_info(f"\n🧹 HEAP CLEANUP: Removing low-quality candidates from search heap...")
    try:
        from .smart_search import get_current_search_heap
        
        heap = get_current_search_heap()
        if heap and hasattr(heap, 'remove_low_quality_candidates'):
            removed_count = heap.remove_low_quality_candidates(min_quality_threshold)
            remaining_heap_size = len(heap.heap) if hasattr(heap, 'heap') else 0
            log_info(f"   🗑️ Removed {removed_count} low-quality candidates from heap")
            log_info(f"   📊 Remaining heap size: {remaining_heap_size} candidates")
            
            # Check if heap is now too small and needs expansion
            if remaining_heap_size < target_count:
                log_info(f"   ⚠️ Heap size ({remaining_heap_size}) below target ({target_count}) - may trigger search expansion")
        else:
            log_info(f"   ℹ️ No active search heap found - cleanup skipped")
    except Exception as cleanup_error:
        log_info(f"   ⚠️ Heap cleanup failed: {cleanup_error}")
        
    log_info(f"\n🤖 PHASE 3: Analyzing results and generating recommendations...")
    
    # Generate intelligent fallback recommendation
    fallback_rec = _generate_fallback_recommendation(
        quality_stats, quality_sufficient, target_count, min_quality_threshold
    )
    
    log_info(f"\n📈 PHASE 4: FINAL EVALUATION RESULTS")
    log_info(f"   Average Quality: {avg_score:.2f}")
    log_info(f"   Quality Range: {min_score:.2f} - {max_score:.2f}")
    log_info(f"   Above Threshold: {quality_stats['above_threshold']}/{quality_stats['total_evaluated']}")
    log_info(f"   Quality Sufficient: {'✅ Yes' if quality_sufficient else '❌ No'}")
    log_info(f"   Recommendation: {fallback_rec['action']}")
    log_info(f"✅ Candidate evaluation workflow completed!")
    
    # Create result data for global state storage
    evaluation_result_data = {
        "success": True,
        "quality_sufficient": quality_sufficient,
        "candidates_evaluated": quality_stats["total_evaluated"],
        "quality_candidates": [c for c in evaluated_candidates if c["overall_score"] >= min_quality_threshold],
        "all_evaluated_candidates": evaluated_candidates,
        
        # Quality metrics
        "quality_stats": {
            "average_score": round(avg_score, 2),
            "max_score": round(max_score, 2),
            "min_score": round(min_score, 2),
            "above_threshold": quality_stats["above_threshold"],
            "below_threshold": quality_stats["below_threshold"],
            "threshold_used": min_quality_threshold
        },
        
        # Intelligent fallback recommendation
        "fallback_recommendation": fallback_rec["action"],
        "fallback_reasoning": fallback_rec["reasoning"],
        "fallback_params": fallback_rec["params"],
        
        "evaluation_timestamp": datetime.now().isoformat()
    }
    
    # Store results in global state
    store_evaluation_results(evaluation_result_data)
    
    # Return lightweight response for agent workflow
    return {
        "success": True,
        "quality_sufficient": quality_sufficient,
        "candidates_evaluated": quality_stats["total_evaluated"],
        "quality_candidates_count": len([c for c in evaluated_candidates if c["overall_score"] >= min_quality_threshold]),
        "average_score": round(avg_score, 2),
        "fallback_recommendation": fallback_rec["action"],
        "message": f"Evaluated {quality_stats['total_evaluated']} candidates, {quality_stats['above_threshold']} above threshold {min_quality_threshold}"
    }




def _extract_candidate_name(candidate: Dict[str, Any]) -> str:
    """Extract candidate name from different data structures"""
    if 'candidate_info' in candidate and 'profile_data' in candidate:
        # Nested structure: {candidate_info: {...}, profile_data: {...}}
        candidate_info = candidate['candidate_info']
        profile_data = candidate['profile_data']
        return profile_data.get('name', candidate_info.get('name', 'Unknown'))
    elif 'profile_data' in candidate:
        # Only profile_data
        return candidate['profile_data'].get('name', 'Unknown')
    else:
        # Flat structure
        return candidate.get('name', 'Unknown')


def _prepare_candidate_for_llm(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare candidate data for LLM assessment"""
    # Handle different candidate data structures
    if 'candidate_info' in candidate and 'profile_data' in candidate:
        # Nested structure
        candidate_info = candidate['candidate_info']
        profile_data = candidate['profile_data']
        return {
            'name': profile_data.get('name', candidate_info.get('name', 'Unknown')),
            'headline': profile_data.get('headline', candidate_info.get('headline', '')),
            'url': candidate_info.get('url', ''),
            'profile_data': profile_data
        }
    elif 'profile_data' in candidate:
        # Only profile_data
        return {
            'name': candidate['profile_data'].get('name', 'Unknown'),
            'headline': candidate['profile_data'].get('headline', ''),
            'url': candidate.get('url', ''),
            'profile_data': candidate['profile_data']
        }
    else:
        # Flat structure - already in the right format
        return candidate


def _convert_llm_assessment_to_result(llm_assessment: CandidateAssessment, candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Convert LLM assessment to evaluation result format"""
    # Extract basic candidate info
    candidate_info = candidate.get('candidate_info', candidate)
    profile_data = candidate.get('profile_data', {})
    
    name = profile_data.get('name', candidate_info.get('name', 'Unknown'))
    headline = profile_data.get('headline', candidate_info.get('headline', ''))
    url = candidate_info.get('url', '')
    
    return {
        "name": name,
        "headline": headline,
        "url": url,
        "overall_score": round(llm_assessment.overall_score, 2),
        "component_scores": {
            "technical_score": round(llm_assessment.technical_score, 2),
            "experience_score": round(llm_assessment.experience_score, 2),
            "cultural_fit_score": round(llm_assessment.cultural_fit_score, 2),
            "extraction_quality": round(llm_assessment.extraction_quality, 2),
            "profile_completeness": round(llm_assessment.profile_completeness, 2)
        },
        "key_signals": {
            "role_match": llm_assessment.key_signals.role_match,
            "seniority_appropriate": llm_assessment.key_signals.seniority_appropriate,
            "tech_stack_match": llm_assessment.key_signals.tech_stack_match,
            "company_tier": llm_assessment.key_signals.company_tier
        },
        "meets_threshold": llm_assessment.overall_score >= 7.0,  # Will be updated with actual threshold
        "strengths": llm_assessment.strengths,
        "concerns": llm_assessment.concerns,
        "reasoning": llm_assessment.reasoning,
        "evaluation_timestamp": datetime.now().isoformat()
    }




def _generate_fallback_recommendation(stats: Dict[str, Any], quality_sufficient: bool, 
                                    target_count: int, threshold: float) -> Dict[str, Any]:
    """Generate intelligent fallback recommendations"""
    log_info(f"   🤔 Analyzing quality distribution and generating recommendations...")
    
    if quality_sufficient:
        return {
            "action": "proceed_with_outreach",
            "reasoning": f"Found {stats['above_threshold']} quality candidates above threshold {threshold}",
            "params": {}
        }
    
    # Analyze what type of fallback is needed
    total_evaluated = stats["total_evaluated"]
    above_threshold = stats["above_threshold"]
    
    # Check current heap state after cleanup
    try:
        from .smart_search import get_current_search_heap
        heap = get_current_search_heap()
        remaining_heap_size = len(heap.heap) if heap and hasattr(heap, 'heap') else 0
    except:
        remaining_heap_size = 0
    
    if above_threshold == 0:
        # No good candidates - check if heap has enough potential or needs expansion
        candidates_needed = target_count
        if remaining_heap_size >= candidates_needed:  # Heap has enough to potentially meet target
            # Calculate proper offset based on how many candidates were already processed
            processed_count = total_evaluated
            return {
                "action": "try_heap_backups",
                "reasoning": f"No quality candidates found. {remaining_heap_size} candidates remain in cleaned heap (enough to meet target).",
                "params": {"backup_offset": processed_count, "backup_limit": min(remaining_heap_size, 6)}
            }
        else:  # Heap too small, expand search to add more candidates
            # Get the last search page info to continue from where we left off
            try:
                from .smart_search import get_last_search_info
                search_info = get_last_search_info()
                next_page = search_info.get("next_start_page", 3) if search_info else 3
            except:
                next_page = 3  # Fallback to page 3
            
            return {
                "action": "expand_search_scope", 
                "reasoning": f"Heap has only {remaining_heap_size} candidates, need {candidates_needed}. Expanding search from page {next_page + 1}.",
                "params": {"start_page": next_page, "page_limit": 3}
            }
    
    elif above_threshold < target_count // 2:
        # Some good candidates but not enough - check if heap can provide the rest
        candidates_still_needed = target_count - above_threshold
        if remaining_heap_size >= candidates_still_needed:  # Heap likely has enough
            # Calculate proper offset based on how many candidates were already processed
            processed_count = total_evaluated
            return {
                "action": "try_heap_backups",
                "reasoning": f"Found {above_threshold}/{target_count} quality candidates. {remaining_heap_size} remain in heap (enough for target).",
                "params": {"backup_offset": processed_count, "backup_limit": min(remaining_heap_size, candidates_still_needed + 2)}
            }
        else:  # Heap insufficient, expand search to add more candidates
            # Get the last search page info to continue from where we left off
            try:
                from .smart_search import get_last_search_info
                search_info = get_last_search_info()
                next_page = search_info.get("next_start_page", 3) if search_info else 3
            except:
                next_page = 3  # Fallback to page 3
                
            return {
                "action": "expand_search_scope",
                "reasoning": f"Found {above_threshold}/{target_count} candidates. Heap has only {remaining_heap_size}, need {candidates_still_needed} more. Expanding search from page {next_page + 1}.",
                "params": {"start_page": next_page, "page_limit": 3}
            }
    
    else:
        # Close to target - try a few more from heap
        processed_count = total_evaluated
        return {
            "action": "try_heap_backups",
            "reasoning": f"Close to target with {above_threshold}/{target_count}. Try a few more from heap.",
            "params": {"backup_offset": processed_count, "backup_limit": 3}
        }


# Export the tool
CandidateEvaluationTool = FunctionTool(fn=evaluate_candidates_quality)