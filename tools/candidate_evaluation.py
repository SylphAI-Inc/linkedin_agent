#!/usr/bin/env python3
"""
Candidate Evaluation Tool - Comprehensive quality assessment for extracted profiles
Provides intelligent fallback recommendations based on evaluation results
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from adalflow.core.func_tool import FunctionTool
import time


def evaluate_candidates_quality(
    candidates: Optional[List[Dict[str, Any]]] = None,
    strategy: Optional[Dict[str, Any]] = None,
    min_quality_threshold: float = 6.0,
    target_count: int = 5
) -> Dict[str, Any]:
    """
    Comprehensive evaluation of extracted candidate profiles
    
    Args:
        candidates: List of extracted candidate profiles (if None, gets from collector)
        strategy: AI-generated search strategy for context-aware evaluation
        min_quality_threshold: Minimum acceptable quality score
        target_count: Target number of quality candidates needed
        
    Returns:
        Dict with evaluation results, quality scores, and fallback recommendations
    """
    
    print(f"🎯 Starting comprehensive candidate evaluation...")
    print(f"   Quality threshold: {min_quality_threshold}")
    print(f"   Target count: {target_count}")
    print(f"⏳ Initializing evaluation system...")
    print(f"strategy: {strategy}")
    
    # Get candidates from various sources
    if candidates is None:
        print(f"📥 PHASE 1: Loading candidates from available sources...")
        candidates = _get_candidates_from_sources()
    else:
        print(f"📥 PHASE 1: Using provided candidates for evaluation...")
    
    if not candidates:
        return {
            "success": False,
            "error": "No candidates available for evaluation",
            "quality_sufficient": False,
            "fallback_recommendation": "search_more_candidates",
            "candidates_evaluated": 0,
            "quality_candidates": []
        }
    print(f"candidates: {candidates}")
    
    print(f"📊 PHASE 2: Starting individual candidate assessment...")
    print(f"   Processing {len(candidates)} candidates with strategic criteria")
    
    # Comprehensive evaluation
    evaluated_candidates = []
    quality_stats = {
        "total_evaluated": 0,
        "above_threshold": 0,
        "below_threshold": 0,
        "scores": []
    }
    
    for i, candidate in enumerate(candidates, 1):
        candidate_name = _extract_candidate_name(candidate)
        print(f"   🔍 Evaluating candidate {i}: {candidate_name}")
        
        # Comprehensive quality assessment
        evaluation_result = _evaluate_single_candidate(candidate, strategy, min_quality_threshold)
        evaluated_candidates.append(evaluation_result)
        
        # Track statistics
        quality_stats["total_evaluated"] += 1
        quality_stats["scores"].append(evaluation_result["overall_score"])
        
        if evaluation_result["overall_score"] >= min_quality_threshold:
            quality_stats["above_threshold"] += 1
        else:
            quality_stats["below_threshold"] += 1
    
    # Calculate quality metrics
    avg_score = sum(quality_stats["scores"]) / len(quality_stats["scores"]) if quality_stats["scores"] else 0
    max_score = max(quality_stats["scores"]) if quality_stats["scores"] else 0
    min_score = min(quality_stats["scores"]) if quality_stats["scores"] else 0
    
    # Determine if quality is sufficient
    quality_sufficient = quality_stats["above_threshold"] >= target_count
    
    # HEAP CLEANUP: Remove low-quality candidates from search heap
    print(f"\n🧹 HEAP CLEANUP: Removing low-quality candidates from search heap...")
    try:
        from tools.smart_search import get_current_search_heap
        
        heap = get_current_search_heap()
        if heap and hasattr(heap, 'remove_low_quality_candidates'):
            removed_count = heap.remove_low_quality_candidates(min_quality_threshold)
            remaining_heap_size = len(heap.heap) if hasattr(heap, 'heap') else 0
            print(f"   🗑️ Removed {removed_count} low-quality candidates from heap")
            print(f"   📊 Remaining heap size: {remaining_heap_size} candidates")
            
            # Check if heap is now too small and needs expansion
            if remaining_heap_size < target_count:
                print(f"   ⚠️ Heap size ({remaining_heap_size}) below target ({target_count}) - may trigger search expansion")
        else:
            print(f"   ℹ️ No active search heap found - cleanup skipped")
    except Exception as cleanup_error:
        print(f"   ⚠️ Heap cleanup failed: {cleanup_error}")
        
    print(f"\n🤖 PHASE 3: Analyzing results and generating recommendations...")
    
    # Generate intelligent fallback recommendation
    fallback_rec = _generate_fallback_recommendation(
        quality_stats, avg_score, quality_sufficient, target_count, min_quality_threshold
    )
    
    print(f"\n📈 PHASE 4: FINAL EVALUATION RESULTS")
    print(f"   Average Quality: {avg_score:.2f}")
    print(f"   Quality Range: {min_score:.2f} - {max_score:.2f}")
    print(f"   Above Threshold: {quality_stats['above_threshold']}/{quality_stats['total_evaluated']}")
    print(f"   Quality Sufficient: {'✅ Yes' if quality_sufficient else '❌ No'}")
    print(f"   Recommendation: {fallback_rec['action']}")
    print(f"✅ Candidate evaluation workflow completed!")
    
    return {
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


def _get_candidates_from_sources() -> List[Dict[str, Any]]:
    """Get candidates from available sources (extraction results, collector, etc.)"""
    print(f"   📥 Searching for candidate data sources...")
    candidates = []
    
    try:
        # Try to get from extraction summary first
        from tools.targeted_extraction import get_extraction_summary
        extraction_summary = get_extraction_summary()
        
        if extraction_summary.get("success") and extraction_summary.get("results"):
            print("📥 Using candidates from extraction results")
            for result in extraction_summary["results"]:
                if result.get("profile_data"):
                    candidates.append({
                        **result["candidate_info"],
                        "profile_data": result["profile_data"]
                    })
    except Exception as e:
        print(f"   ⚠️ Could not get extraction results: {e}")
    
    # Fallback to collector if no extraction results
    if not candidates:
        try:
            from tools.smart_search import get_collected_candidates
            collector_result = get_collected_candidates(limit=20, sort_by_score=True)
            
            if collector_result.get("candidates"):
                print("📥 Using candidates from collector")
                candidates = collector_result["candidates"]
        except Exception as e:
            print(f"   ⚠️ Could not get collector candidates: {e}")
    
    return candidates


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


def _evaluate_single_candidate(candidate: Dict[str, Any], strategy: Optional[Dict[str, Any]], min_threshold: float) -> Dict[str, Any]:
    """Comprehensive evaluation of a single candidate using strategy-driven criteria"""
    
    print(f"      🎯 Applying strategic evaluation criteria...")
    
    # Extract profile data
    profile_data = candidate.get("profile_data", {})
    candidate_info = candidate.get("candidate_info", candidate)  # Fallback for different structures
    
    name = profile_data.get("name", candidate_info.get("name", "Unknown"))
    headline = profile_data.get("headline", candidate_info.get("headline", ""))
    experiences = profile_data.get("experiences", [])
    education = profile_data.get("education", [])
    skills = profile_data.get("skills", [])
    about = profile_data.get("about", "")
    
    # Multi-dimensional scoring with strategy-driven criteria
    scores = {
        "experience_quality": _score_experience_quality(experiences, strategy),
        "education_quality": _score_education_quality(education, strategy),
        "skills_relevance": _score_skills_relevance(skills, strategy),
        "profile_completeness": _score_profile_completeness(profile_data),
        "strategic_alignment": _score_strategic_alignment(headline, experiences, strategy),
        "communication_quality": _score_communication_quality(about, headline)
    }
    
    # Calculate strategic bonuses (additive to base scores)
    print(f"      🎆 Calculating strategic bonuses...")
    strategic_bonuses = _calculate_strategic_bonuses({
        "name": name,
        "headline": headline,
        "experiences": experiences,
        "education": education,
        "skills": skills,
        "about": about
    }, strategy)
    
    # Apply bonuses to relevant categories
    scores["experience_quality"] += strategic_bonuses["company_tier_bonus"]
    scores["strategic_alignment"] += strategic_bonuses["seniority_bonus"]
    scores["skills_relevance"] += strategic_bonuses["tech_depth_bonus"]
    scores["education_quality"] += strategic_bonuses["education_prestige_bonus"]
    
    # Cap individual scores at 10.0
    for key in scores:
        scores[key] = min(scores[key], 10.0)
    
    # Dynamic weights based on strategy focus
    weights = _get_dynamic_scoring_weights(strategy)
    
    overall_score = sum(scores[key] * weights[key] for key in scores.keys())
    
    # Apply final strategic multiplier bonus (up to 15% boost)
    print(f"      ✨ Applying final strategic multiplier...")
    final_multiplier = _calculate_final_strategic_multiplier(strategic_bonuses, strategy)
    overall_score *= final_multiplier
    
    # Generate strengths and concerns
    strengths, concerns = _generate_evaluation_insights(scores, min_threshold, strategy)
    
    return {
        "name": name,
        "headline": headline,
        "url": candidate_info.get("url", ""),
        "overall_score": round(overall_score, 2),
        "component_scores": {k: round(v, 2) for k, v in scores.items()},
        "strategic_bonuses": {k: round(v, 2) for k, v in strategic_bonuses.items()},
        "scoring_weights": weights,
        "final_multiplier": round(final_multiplier, 3),
        "meets_threshold": overall_score >= min_threshold,
        "strengths": strengths,
        "concerns": concerns,
        "evaluation_timestamp": datetime.now().isoformat()
    }


def _score_experience_quality(experiences: List[Dict[str, Any]], strategy: Optional[Dict[str, Any]]) -> float:
    """Score based on experience quality and progression using strategy-driven criteria"""
    if not experiences:
        return 5.0  # Increased from 2.0 - neutral score for missing data instead of penalty
    
    score = 5.0  # Base score
    
    # Quantity bonus
    if len(experiences) >= 4:
        score += 1.5
    elif len(experiences) >= 2:
        score += 1.0
    
    # Strategy-driven seniority indicators
    seniority_keywords = _get_strategy_seniority_keywords(strategy)
    for exp in experiences[:3]:  # Check recent experiences
        title = exp.get("title", "").lower()
        
        # Check for strategy-defined seniority levels
        seniority_bonus = _calculate_seniority_bonus(title, seniority_keywords)
        if seniority_bonus > 0:
            score += seniority_bonus
            break
        # Fallback for general engineering roles
        elif any(role in title for role in ["engineer", "developer", "architect"]):
            score += 0.5
    
    # Strategy-driven company quality assessment
    company_bonus = _calculate_company_quality_bonus(experiences[:2], strategy)
    score += company_bonus
    
    return min(score, 10.0)


def _score_education_quality(education: List[Dict[str, Any]], strategy: Optional[Dict[str, Any]]) -> float:
    """Score based on education quality using strategy-driven criteria"""
    if not education:
        return 5.0  # Neutral - experience matters more
    
    score = 6.0  # Base score
    
    # Strategy-driven education evaluation
    target_fields = _get_strategy_education_fields(strategy)
    
    # Look for relevant degrees
    for edu in education:
        degree = edu.get("degree", "").lower()
        school = edu.get("school", "").lower()
        
        # Degree relevance based on strategy
        degree_bonus = _calculate_degree_relevance_bonus(degree, target_fields)
        score += degree_bonus
        
        # School recognition - strategy-aware or general prestige
        school_bonus = _calculate_school_prestige_bonus(school, strategy)
        score += school_bonus
        
        break  # Only check first education entry
    
    return min(score, 10.0)


def _score_skills_relevance(skills: List[str], strategy: Optional[Dict[str, Any]]) -> float:
    """Score based on skills relevance to strategy with dynamic tech stack evaluation"""
    if not skills:
        return 5.0  # Increased from 3.0 - neutral score for missing skills data
    
    score = 5.0  # Base score
    skills_lower = [s.lower() for s in skills]
    
    # Primary strategy-based scoring (highest priority)
    strategy_score = _calculate_strategy_tech_matches(skills_lower, strategy)
    score += strategy_score
    
    # Secondary complementary tech skills (only if strategy doesn't cover everything)
    if strategy_score < 3.0:  # Still room for general tech bonus
        general_score = _calculate_general_tech_bonus(skills_lower, strategy)
        score += general_score
    
    # Skills breadth and depth indicators
    breadth_bonus = _calculate_skills_breadth_bonus(skills_lower, strategy)
    score += breadth_bonus
    
    return min(score, 10.0)


def _score_profile_completeness(profile_data: Dict[str, Any]) -> float:
    """Score based on profile completeness with better baseline for limited data"""
    score = 3.0  # Start with baseline instead of 0 for candidates with some data
    
    # Check presence of key sections
    if profile_data.get("name"):
        score += 0.5
    if profile_data.get("headline"):
        score += 2.0  # Headlines are very important and available
    if profile_data.get("about"):
        score += 1.0
    if profile_data.get("experiences"):
        score += 2.0
    if profile_data.get("education"):
        score += 1.0
    if profile_data.get("skills"):
        score += 1.5
    if profile_data.get("location"):
        score += 0.5
    
    return min(score, 10.0)


def _score_strategic_alignment(headline: str, experiences: List[Dict[str, Any]], strategy: Optional[Dict[str, Any]]) -> float:
    """Score based on strategic alignment with search criteria"""
    if not strategy:
        return 5.0
    
    score = 6.0  # Increased base score - if they passed search, they have some alignment
    headline_lower = headline.lower() if headline else ""
    
    # Title alignment
    target_titles = []
    if "primary_titles" in strategy or "primary_job_titles" in strategy:
        target_titles = [t.lower() for t in (strategy.get("primary_titles", []) or strategy.get("primary_job_titles", []))]
    elif "headline_analysis" in strategy:
        target_titles = [t.lower() for t in strategy["headline_analysis"].get("target_job_titles", [])]
    
    if target_titles and any(title in headline_lower for title in target_titles):
        score += 2.0
    
    # Company alignment
    target_companies = []
    if "target_companies" in strategy:
        target_companies = [c.lower() for c in strategy["target_companies"]]
    elif "headline_analysis" in strategy:
        target_companies = [c.lower() for c in strategy["headline_analysis"].get("company_indicators", [])]
    
    if target_companies:
        for exp in experiences[:2]:  # Check recent companies
            company = exp.get("company", "").lower()
            if any(target in company for target in target_companies):
                score += 1.5
                break
    
    return min(score, 10.0)


def _score_communication_quality(about: str, headline: str) -> float:
    """Score based on communication quality indicators"""
    score = 5.0  # Base score
    
    # About section quality
    if about and len(about) > 100:
        score += 2.0
    elif about and len(about) > 50:
        score += 1.0
    
    # Headline quality
    if headline and len(headline) > 50:
        score += 1.0
    
    return min(score, 10.0)


def _generate_evaluation_insights(scores: Dict[str, float], threshold: float, strategy: Optional[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """Generate human-readable insights from scores using strategy context"""
    strengths = []
    concerns = []
    
    # Strategy-aware insights
    role_context = _get_role_context_from_strategy(strategy)
    
    # Analyze each component with strategy context
    if scores["experience_quality"] >= 7.0:
        strengths.append(f"Strong professional experience for {role_context} roles")
    elif scores["experience_quality"] < 4.0:
        concerns.append("Limited relevant experience information")
    
    if scores["skills_relevance"] >= 7.0:
        strengths.append(f"Highly relevant technical skills for {role_context}")
    elif scores["skills_relevance"] < 4.0:
        concerns.append("Skills may not align well with role requirements")
    
    if scores["strategic_alignment"] >= 7.0:
        strengths.append("Excellent strategic fit for target role and companies")
    elif scores["strategic_alignment"] < 4.0:
        concerns.append("Limited alignment with strategic hiring criteria")
    
    if scores["profile_completeness"] >= 8.0:
        strengths.append("Complete and detailed LinkedIn profile")
    elif scores["profile_completeness"] < 5.0:
        concerns.append("Incomplete profile information")
    
    if scores["education_quality"] >= 7.5:
        strengths.append("Strong educational background")
    
    if scores["communication_quality"] >= 7.5:
        strengths.append("Strong professional communication")
    
    return strengths, concerns


def _generate_fallback_recommendation(stats: Dict[str, Any], avg_score: float, quality_sufficient: bool, 
                                    target_count: int, threshold: float) -> Dict[str, Any]:
    """Generate intelligent fallback recommendations"""
    print(f"   🤔 Analyzing quality distribution and generating recommendations...")
    
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
        from tools.smart_search import get_current_search_heap
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
                from tools.smart_search import get_last_search_info
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
                from tools.smart_search import get_last_search_info
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


def _get_dynamic_scoring_weights(strategy: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """Generate dynamic scoring weights using structured role focus from evaluation criteria"""
    
    # Default weights (balanced approach)
    weights = {
        "experience_quality": 0.35,
        "education_quality": 0.15,
        "skills_relevance": 0.20,
        "profile_completeness": 0.10,
        "strategic_alignment": 0.15,
        "communication_quality": 0.05
    }
    
    if not strategy:
        return weights
    
    # Extract structured role focus from evaluation_criteria
    eval_criteria = strategy.get("evaluation_criteria", {})
    role_focus = eval_criteria.get("role_focus", {})
    
    # Use structured weights if available
    if role_focus:
        # Direct weight assignment from strategy
        weights["experience_quality"] = role_focus.get("experience_weight", 0.35)
        weights["skills_relevance"] = role_focus.get("skills_weight", 0.25)
        weights["strategic_alignment"] = role_focus.get("strategic_weight", 0.20)
        weights["education_quality"] = role_focus.get("education_weight", 0.10)
        
        # Calculate remaining weight for profile completeness and communication
        assigned_weight = sum([weights["experience_quality"], weights["skills_relevance"], 
                              weights["strategic_alignment"], weights["education_quality"]])
        remaining_weight = 1.0 - assigned_weight
        
        # Distribute remaining weight based on role focus
        primary_focus = role_focus.get("primary_focus", "technical").lower()
        
        if primary_focus == "leadership":
            weights["communication_quality"] = remaining_weight * 0.7  # 70% to communication
            weights["profile_completeness"] = remaining_weight * 0.3  # 30% to completeness
        else:
            weights["profile_completeness"] = remaining_weight * 0.7  # 70% to completeness
            weights["communication_quality"] = remaining_weight * 0.3  # 30% to communication
    
    else:
        # Fallback to legacy focus area analysis
        focus_areas = []
        if "profile_evaluation_context" in strategy:
            focus_areas = strategy["profile_evaluation_context"].get("focus_areas", [])
        
        focus_text = " ".join(focus_areas).lower() if focus_areas else ""
        
        # Increase technical skills weight for tech-heavy roles
        if any(tech in focus_text for tech in ["technical", "technology", "programming", "coding"]):
            weights["skills_relevance"] = 0.30
            weights["experience_quality"] = 0.30
            weights["strategic_alignment"] = 0.20
            weights["education_quality"] = 0.10
            weights["profile_completeness"] = 0.08
            weights["communication_quality"] = 0.02
        
        # Increase experience weight for senior roles
        elif any(senior in focus_text for senior in ["leadership", "management", "senior", "lead"]):
            weights["experience_quality"] = 0.45
            weights["strategic_alignment"] = 0.25
            weights["skills_relevance"] = 0.15
            weights["communication_quality"] = 0.08
            weights["education_quality"] = 0.05
            weights["profile_completeness"] = 0.02
    
    # Ensure weights sum to 1.0
    total = sum(weights.values())
    if total != 1.0:
        for key in weights:
            weights[key] = weights[key] / total
    
    return weights


def _get_strategy_seniority_keywords(strategy: Optional[Dict[str, Any]]) -> List[str]:
    """Extract seniority keywords from strategy with fallbacks"""
    if not strategy:
        return ["senior", "lead", "staff", "principal", "director"]
    
    # Try multiple strategy locations
    if "headline_analysis" in strategy and "seniority_keywords" in strategy["headline_analysis"]:
        return [s.lower() for s in strategy["headline_analysis"]["seniority_keywords"]]
    elif "seniority_indicators" in strategy:
        return [s.lower() for s in strategy["seniority_indicators"]]
    
    # Fallback to common seniority terms
    return ["senior", "lead", "staff", "principal", "director", "manager", "head of", "vp", "cto"]


def _calculate_seniority_bonus(title: str, seniority_keywords: List[str]) -> float:
    """Calculate bonus points based on seniority level detected in title"""
    title_lower = title.lower()
    
    for keyword in seniority_keywords:
        if keyword in title_lower:
            # Executive level
            if keyword in ["cto", "ceo", "vp", "head of", "director"]:
                return 2.0
            # Senior IC level  
            elif keyword in ["principal", "staff", "architect"]:
                return 1.5
            # Team lead level
            elif keyword in ["senior", "lead", "sr.", "manager"]:
                return 1.0
            else:
                return 0.5
    
    return 0.0


def _calculate_company_quality_bonus(experiences: List[Dict[str, Any]], strategy: Optional[Dict[str, Any]]) -> float:
    """Calculate bonus based on company quality using strategy and general tiers"""
    if not experiences:
        return 0.0
    
    max_bonus = 0.0
    
    # Strategy-defined target companies (highest priority)
    target_companies = []
    if strategy:
        if "headline_analysis" in strategy and "company_indicators" in strategy["headline_analysis"]:
            target_companies = [c.lower() for c in strategy["headline_analysis"]["company_indicators"]]
        elif "target_companies" in strategy:
            target_companies = [c.lower() for c in strategy["target_companies"]]
    
    # Company tier definitions (fallback/supplement)
    tier_1_companies = ["google", "facebook", "meta", "apple", "microsoft", "amazon", "netflix", "tesla", "uber", "airbnb"]
    tier_2_companies = ["stripe", "dropbox", "slack", "salesforce", "adobe", "nvidia", "twitter", "linkedin", "pinterest", "square"]
    
    for exp in experiences:
        company = exp.get("company", "").lower()
        
        # Strategy companies get highest bonus
        if target_companies and any(target in company for target in target_companies):
            max_bonus = max(max_bonus, 1.5)
        # Tier 1 companies
        elif any(tier1 in company for tier1 in tier_1_companies):
            max_bonus = max(max_bonus, 1.0)
        # Tier 2 companies
        elif any(tier2 in company for tier2 in tier_2_companies):
            max_bonus = max(max_bonus, 0.7)
    
    return max_bonus


def _get_strategy_education_fields(strategy: Optional[Dict[str, Any]]) -> List[str]:
    """Get relevant education fields from strategy context"""
    if not strategy:
        return ["computer", "software", "engineering", "science"]
    
    # Extract from strategy context if available
    focus_areas = []
    if "profile_evaluation_context" in strategy:
        focus_areas = strategy["profile_evaluation_context"].get("focus_areas", [])
    
    focus_text = " ".join(focus_areas).lower() if focus_areas else ""
    
    # Build relevant fields based on focus
    relevant_fields = ["computer", "software", "engineering"]
    
    if "data" in focus_text or "analytics" in focus_text:
        relevant_fields.extend(["data", "statistics", "mathematics", "analytics"])
    
    if "design" in focus_text or "ux" in focus_text:
        relevant_fields.extend(["design", "hci", "interaction", "visual"])
    
    if "business" in focus_text or "product" in focus_text:
        relevant_fields.extend(["business", "mba", "economics"])
    
    return relevant_fields


def _calculate_degree_relevance_bonus(degree: str, target_fields: List[str]) -> float:
    """Calculate bonus based on degree relevance to target fields"""
    degree_lower = degree.lower()
    
    for field in target_fields:
        if field in degree_lower:
            # Perfect match fields
            if field in ["computer", "software", "engineering"]:
                return 1.5
            # Good supplementary fields
            else:
                return 1.0
    
    # No clear match
    return 0.0


def _calculate_school_prestige_bonus(school: str, strategy: Optional[Dict[str, Any]]) -> float:
    """Calculate bonus based on school prestige with strategy awareness"""
    school_lower = school.lower()
    
    # Top tier schools
    top_tier = ["stanford", "mit", "berkeley", "carnegie", "caltech", "harvard", "princeton"]
    if any(top in school_lower for top in top_tier):
        return 1.0
    
    # Good engineering schools
    engineering_schools = ["georgia tech", "michigan", "illinois", "texas", "washington", "purdue"]
    if any(eng in school_lower for eng in engineering_schools):
        return 0.7
    
    # UC system and other state schools
    if "university" in school_lower and any(uc in school_lower for uc in ["california", "ucla", "ucsd"]):
        return 0.5
    
    return 0.0


def _calculate_strategy_tech_matches(skills_lower: List[str], strategy: Optional[Dict[str, Any]]) -> float:
    """Calculate primary bonus from strategy-defined tech stack matches"""
    if not strategy:
        return 0.0
    
    # Extract strategy tech stack
    strategy_skills = []
    if "key_technologies" in strategy:
        strategy_skills = [s.lower() for s in strategy["key_technologies"]]
    elif "headline_analysis" in strategy and "tech_stack_signals" in strategy["headline_analysis"]:
        strategy_skills = [s.lower() for s in strategy["headline_analysis"]["tech_stack_signals"]]
    
    if not strategy_skills:
        return 0.0
    
    # Calculate matches with bonus weighting
    matches = 0
    for skill in strategy_skills:
        if any(skill in candidate_skill for candidate_skill in skills_lower):
            matches += 1
    
    # Progressive bonus: first few matches worth more
    if matches >= 5:
        return 3.0  # Excellent match
    elif matches >= 3:
        return 2.0  # Good match
    elif matches >= 1:
        return 1.0  # Some match
    else:
        return 0.0  # No match


def _calculate_general_tech_bonus(skills_lower: List[str], strategy: Optional[Dict[str, Any]]) -> float:
    """Calculate supplementary bonus from general tech skills (only if strategy match is low)"""
    # Common valuable tech skills (industry standards)
    common_tech = ["python", "java", "javascript", "react", "node", "aws", "docker", "kubernetes", "sql", "git"]
    
    tech_matches = [tech for tech in common_tech if any(tech in skill for skill in skills_lower)]
    
    # Smaller bonus since this is supplementary
    if len(tech_matches) >= 6:
        return 1.0
    elif len(tech_matches) >= 3:
        return 0.7
    elif len(tech_matches) >= 1:
        return 0.4
    else:
        return 0.0


def _calculate_skills_breadth_bonus(skills_lower: List[str], strategy: Optional[Dict[str, Any]]) -> float:
    """Calculate bonus for skills breadth and depth indicators"""
    total_skills = len(skills_lower)
    
    # Skills breadth bonus
    breadth_bonus = 0.0
    if total_skills >= 15:
        breadth_bonus = 0.5  # Good breadth
    elif total_skills >= 8:
        breadth_bonus = 0.3  # Decent breadth
    
    # Look for full-stack indicators
    frontend_skills = ["react", "vue", "angular", "javascript", "typescript", "html", "css"]
    backend_skills = ["python", "java", "node", "go", "rust", "sql", "api"]
    devops_skills = ["docker", "kubernetes", "aws", "gcp", "azure", "ci/cd"]
    
    has_frontend = any(fe in skill for skill in skills_lower for fe in frontend_skills)
    has_backend = any(be in skill for skill in skills_lower for be in backend_skills)
    has_devops = any(do in skill for skill in skills_lower for do in devops_skills)
    
    # Full-stack bonus
    stack_coverage = sum([has_frontend, has_backend, has_devops])
    if stack_coverage >= 3:
        breadth_bonus += 0.5  # True full-stack
    elif stack_coverage >= 2:
        breadth_bonus += 0.3  # Good coverage
    
    return min(breadth_bonus, 1.0)  # Cap at 1.0


def _get_role_context_from_strategy(strategy: Optional[Dict[str, Any]]) -> str:
    """Extract role context from strategy for insights generation"""
    if not strategy:
        return "software engineering"
    
    # Try to get role context from strategy
    if "headline_analysis" in strategy and "target_job_titles" in strategy["headline_analysis"]:
        titles = strategy["headline_analysis"]["target_job_titles"]
        if titles:
            return titles[0].lower()
    
    if "original_query" in strategy:
        return strategy["original_query"].lower()
    
    return "software engineering"


def _calculate_strategic_bonuses(candidate_data: Dict[str, Any], strategy: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate comprehensive strategic bonuses based on strategy alignment"""
    print(f"        📊 Analyzing strategic alignment...")
    
    bonuses = {
        "company_tier_bonus": 0.0,
        "seniority_bonus": 0.0, 
        "tech_depth_bonus": 0.0,
        "education_prestige_bonus": 0.0,
        "role_progression_bonus": 0.0,
        "market_alignment_bonus": 0.0
    }
    
    if not strategy:
        return bonuses
    
    # 1. Company Tier Bonus - Premium companies get significant boost
    bonuses["company_tier_bonus"] = _calculate_company_tier_bonus(
        candidate_data["experiences"], strategy
    )
    
    # 2. Seniority Alignment Bonus - Right seniority level for role
    bonuses["seniority_bonus"] = _calculate_seniority_alignment_bonus(
        candidate_data["headline"], candidate_data["experiences"], strategy
    )
    
    # 3. Technology Depth & Breadth Bonus - Deep expertise in key areas
    bonuses["tech_depth_bonus"] = _calculate_tech_depth_bonus(
        candidate_data["skills"], candidate_data["experiences"], strategy
    )
    
    # 4. Education Prestige & Relevance Bonus
    bonuses["education_prestige_bonus"] = _calculate_education_bonus(
        candidate_data["education"], strategy
    )
    
    # 5. Role Progression Bonus - Career growth trajectory
    bonuses["role_progression_bonus"] = _calculate_role_progression_bonus(
        candidate_data["experiences"], strategy
    )
    
    # 6. Market & Industry Alignment Bonus
    bonuses["market_alignment_bonus"] = _calculate_market_alignment_bonus(
        candidate_data, strategy
    )
    
    return bonuses


def _calculate_company_tier_bonus(experiences: List[Dict[str, Any]], strategy: Dict[str, Any]) -> float:
    """Calculate bonus based on company tier using structured evaluation criteria"""
    max_bonus = 0.0
    
    # Extract structured company tiers from evaluation_criteria
    eval_criteria = strategy.get("evaluation_criteria", {})
    company_tiers = eval_criteria.get("company_tiers", {})
    bonus_weights = eval_criteria.get("bonus_weights", {})
    
    # Get multiplier from strategy or use default
    company_multiplier = bonus_weights.get("company_tier_multiplier", 2.5)
    
    # Strategy-structured company tiers
    target_companies = [c.lower() for c in company_tiers.get("target_companies", [])]
    tier_1_companies = [c.lower() for c in company_tiers.get("tier_1", [])]
    tier_2_companies = [c.lower() for c in company_tiers.get("tier_2", [])]
    
    # Fallback to legacy extraction if no structured data
    if not tier_1_companies and "headline_analysis" in strategy:
        tier_1_companies = [c.lower() for c in strategy["headline_analysis"].get("company_indicators", [])]
    
    for exp in experiences[:3]:  # Check recent experiences
        company = exp.get("company", "").lower()
        
        # Strategy target companies - full multiplier bonus
        if target_companies and any(target in company for target in target_companies):
            max_bonus = max(max_bonus, company_multiplier)
        # Tier 1 companies - 80% of multiplier
        elif tier_1_companies and any(tier1 in company for tier1 in tier_1_companies):
            max_bonus = max(max_bonus, company_multiplier * 0.8)
        # Tier 2 companies - 60% of multiplier  
        elif tier_2_companies and any(tier2 in company for tier2 in tier_2_companies):
            max_bonus = max(max_bonus, company_multiplier * 0.6)
    
    return max_bonus


def _calculate_seniority_alignment_bonus(headline: str, experiences: List[Dict[str, Any]], strategy: Dict[str, Any]) -> float:
    """Calculate bonus based on seniority alignment using structured evaluation criteria"""
    
    # Extract structured seniority mapping from evaluation_criteria
    eval_criteria = strategy.get("evaluation_criteria", {})
    seniority_mapping = eval_criteria.get("seniority_mapping", {})
    bonus_weights = eval_criteria.get("bonus_weights", {})
    
    # Get multiplier and target seniority from strategy
    seniority_multiplier = bonus_weights.get("seniority_alignment_multiplier", 2.0)
    target_seniority_level = seniority_mapping.get("target_seniority", "senior")
    
    # Get structured seniority keywords
    exec_keywords = [k.lower() for k in seniority_mapping.get("executive", [])]
    principal_keywords = [k.lower() for k in seniority_mapping.get("principal", [])]
    senior_keywords = [k.lower() for k in seniority_mapping.get("senior", [])]
    
    # Fallback to legacy extraction if no structured data
    if not exec_keywords and "headline_analysis" in strategy:
        all_keywords = strategy["headline_analysis"].get("seniority_keywords", [])
        exec_keywords = ["cto", "vp", "director", "head of", "chief"]
        principal_keywords = ["principal", "staff", "architect"]
        senior_keywords = ["senior", "lead", "sr."]
    
    analysis_text = f"{headline} {' '.join([exp.get('title', '') for exp in experiences[:2]])}".lower()
    
    # Detect candidate seniority level
    candidate_level = "mid"
    if any(exec in analysis_text for exec in exec_keywords):
        candidate_level = "executive"
    elif any(prin in analysis_text for prin in principal_keywords):
        candidate_level = "principal"
    elif any(senior in analysis_text for senior in senior_keywords):
        candidate_level = "senior"
    
    # Calculate alignment bonus based on target vs candidate level
    level_hierarchy = {"mid": 1, "senior": 2, "principal": 3, "executive": 4}
    target_level_num = level_hierarchy.get(target_seniority_level, 2)
    candidate_level_num = level_hierarchy.get(candidate_level, 1)
    
    # Perfect match gets full multiplier
    if candidate_level == target_seniority_level:
        return seniority_multiplier
    # One level up gets 80% (valuable over-qualification)
    elif candidate_level_num == target_level_num + 1:
        return seniority_multiplier * 0.8
    # One level down gets 60% (still valuable)
    elif candidate_level_num == target_level_num - 1:
        return seniority_multiplier * 0.6
    # Two levels different gets 30% (some value)
    elif abs(candidate_level_num - target_level_num) == 2:
        return seniority_multiplier * 0.3
    
    return 0.0


def _calculate_tech_depth_bonus(skills: List[str], experiences: List[Dict[str, Any]], strategy: Dict[str, Any]) -> float:
    """Calculate bonus for technical depth using structured technology priorities"""
    
    # Extract structured technology priorities from evaluation_criteria
    eval_criteria = strategy.get("evaluation_criteria", {})
    tech_priorities = eval_criteria.get("technology_priorities", {})
    bonus_weights = eval_criteria.get("bonus_weights", {})
    
    # Get tech multiplier from strategy
    tech_multiplier = bonus_weights.get("tech_depth_multiplier", 3.0)
    
    # Get structured tech categories
    must_have_techs = [t.lower() for t in tech_priorities.get("must_have", [])]
    preferred_techs = [t.lower() for t in tech_priorities.get("preferred", [])]
    complementary_techs = [t.lower() for t in tech_priorities.get("complementary", [])]
    
    # Fallback to legacy extraction if no structured data
    if not must_have_techs and "headline_analysis" in strategy:
        all_techs = strategy["headline_analysis"].get("tech_stack_signals", [])
        must_have_techs = [t.lower() for t in all_techs[:3]]  # Top 3 as must-have
        preferred_techs = [t.lower() for t in all_techs[3:6]]  # Next 3 as preferred
        complementary_techs = [t.lower() for t in all_techs[6:]]  # Rest as complementary
    
    skills_lower = [s.lower() for s in skills]
    
    # Calculate matches in each category
    must_have_matches = sum(1 for tech in must_have_techs 
                          if any(tech in skill for skill in skills_lower))
    preferred_matches = sum(1 for tech in preferred_techs 
                          if any(tech in skill for skill in skills_lower))
    complementary_matches = sum(1 for tech in complementary_techs 
                              if any(tech in skill for skill in skills_lower))
    
    # Experience validation for must-have technologies
    exp_validation_count = 0
    for exp in experiences[:3]:
        exp_text = " ".join(exp.get("bullets", [])).lower()
        for tech in must_have_techs:
            if tech in exp_text:
                exp_validation_count += 1
                break  # One per experience max
    
    # Calculate weighted tech depth bonus
    depth_bonus = 0.0
    
    # Must-have technologies (70% weight)
    if must_have_matches >= len(must_have_techs):
        depth_bonus += tech_multiplier * 0.7  # Perfect coverage
    elif must_have_matches >= len(must_have_techs) * 0.75:
        depth_bonus += tech_multiplier * 0.6  # Excellent coverage
    elif must_have_matches >= len(must_have_techs) * 0.5:
        depth_bonus += tech_multiplier * 0.4  # Good coverage
    elif must_have_matches >= 1:
        depth_bonus += tech_multiplier * 0.2  # Some coverage
    
    # Preferred technologies (20% weight)
    if preferred_matches >= len(preferred_techs) * 0.5:
        depth_bonus += tech_multiplier * 0.2
    elif preferred_matches >= 1:
        depth_bonus += tech_multiplier * 0.1
    
    # Complementary technologies (10% weight)
    if complementary_matches >= 2:
        depth_bonus += tech_multiplier * 0.1
    elif complementary_matches >= 1:
        depth_bonus += tech_multiplier * 0.05
    
    # Experience validation bonus
    if exp_validation_count >= 2:
        depth_bonus += 0.8  # Strong validation
    elif exp_validation_count >= 1:
        depth_bonus += 0.5  # Some validation
    
    # Specialization indicators
    specialization_indicators = ["expert", "specialist", "architect", "advanced", "lead"]
    if any(spec in skill for skill in skills_lower for spec in specialization_indicators):
        depth_bonus += 0.5
    
    return depth_bonus


def _calculate_education_bonus(education: List[Dict[str, Any]], strategy: Dict[str, Any]) -> float:
    """Calculate education bonus using structured education criteria"""
    if not education:
        return 0.0
    
    # Extract structured education criteria from evaluation_criteria
    eval_criteria = strategy.get("evaluation_criteria", {})
    education_criteria = eval_criteria.get("education_criteria", {})
    bonus_weights = eval_criteria.get("bonus_weights", {})
    
    # Get education multiplier from strategy
    education_multiplier = bonus_weights.get("education_multiplier", 2.0)
    
    # Get structured education preferences
    top_schools = [s.lower() for s in education_criteria.get("top_schools", [])]
    relevant_degrees = [d.lower() for d in education_criteria.get("relevant_degrees", [])]
    preferred_fields = [f.lower() for f in education_criteria.get("preferred_fields", [])]
    
    # Fallback to hardcoded values if no structured data
    if not top_schools:
        top_schools = ["stanford", "mit", "berkeley", "carnegie mellon", "caltech"]
        relevant_degrees = ["computer science", "software engineering", "computer engineering"]
        preferred_fields = ["computer science", "engineering", "mathematics"]
    
    max_bonus = 0.0
    
    for edu in education[:2]:  # Check top 2 education entries
        bonus = 0.0
        
        school = edu.get("school", "").lower()
        degree = edu.get("degree", "").lower()
        
        # School prestige scoring
        if any(top_school in school for top_school in top_schools):
            bonus += education_multiplier * 0.6  # 60% of multiplier for top schools
        elif any(ivy in school for ivy in ["harvard", "princeton", "yale", "columbia"]):
            bonus += education_multiplier * 0.5  # 50% for Ivy League
        elif any(good in school for good in ["georgia tech", "michigan", "illinois", "washington"]):
            bonus += education_multiplier * 0.4  # 40% for good engineering schools
        elif "university" in school:
            bonus += education_multiplier * 0.1  # 10% for any university
        
        # Degree relevance scoring
        if any(relevant in degree for relevant in relevant_degrees):
            bonus += education_multiplier * 0.4  # 40% for perfect relevance
        elif any(field in degree for field in preferred_fields):
            bonus += education_multiplier * 0.3  # 30% for good technical background
        elif "master" in degree or "phd" in degree:
            bonus += education_multiplier * 0.2  # 20% for advanced degree
        elif "bachelor" in degree:
            bonus += education_multiplier * 0.1  # 10% for any bachelor's
        
        max_bonus = max(max_bonus, bonus)
    
    return max_bonus


def _calculate_role_progression_bonus(experiences: List[Dict[str, Any]], strategy: Dict[str, Any]) -> float:
    """Calculate bonus for career progression and growth trajectory"""
    if len(experiences) < 2:
        return 0.0
    
    progression_bonus = 0.0
    
    # Analyze title progression in recent roles
    recent_titles = [exp.get("title", "").lower() for exp in experiences[:4]]
    
    # Look for seniority progression
    has_junior = any("junior" in title or "intern" in title for title in recent_titles)
    has_mid = any("engineer" in title or "developer" in title for title in recent_titles) 
    has_senior = any("senior" in title or "sr." in title for title in recent_titles)
    has_lead = any("lead" in title or "principal" in title or "staff" in title for title in recent_titles)
    
    # Calculate progression score
    progression_levels = sum([has_junior, has_mid, has_senior, has_lead])
    if progression_levels >= 3:
        progression_bonus += 1.5  # Clear progression
    elif progression_levels >= 2:
        progression_bonus += 1.0  # Some progression
    
    # Look for leadership/scope expansion
    leadership_indicators = ["lead", "manager", "head", "director", "team lead"]
    if any(leader in title for title in recent_titles for leader in leadership_indicators):
        progression_bonus += 1.0
    
    # Company progression (moving to better companies)
    companies = [exp.get("company", "").lower() for exp in experiences[:3]]
    tier_1 = ["google", "facebook", "apple", "microsoft", "amazon"]
    tier_2 = ["uber", "airbnb", "stripe", "netflix"]
    
    company_tiers = []
    for company in companies:
        if any(t1 in company for t1 in tier_1):
            company_tiers.append(1)
        elif any(t2 in company for t2 in tier_2):
            company_tiers.append(2)
        else:
            company_tiers.append(3)
    
    # Check for upward company movement
    if len(company_tiers) >= 2 and company_tiers[0] < company_tiers[-1]:
        progression_bonus += 0.8  # Moved to better company
    
    return min(progression_bonus, 2.5)  # Cap at 2.5


def _calculate_market_alignment_bonus(candidate_data: Dict[str, Any], strategy: Dict[str, Any]) -> float:
    """Calculate bonus for overall market and industry alignment"""
    
    alignment_bonus = 0.0
    
    # Extract strategy context
    target_titles = []
    if "headline_analysis" in strategy and "target_job_titles" in strategy["headline_analysis"]:
        target_titles = [t.lower() for t in strategy["headline_analysis"]["target_job_titles"]]
    
    headline = candidate_data.get("headline", "").lower()
    
    # Perfect title alignment
    if target_titles and any(target in headline for target in target_titles):
        alignment_bonus += 1.5
    
    # Industry/domain alignment indicators
    experiences = candidate_data.get("experiences", [])
    if experiences:
        recent_companies = [exp.get("company", "").lower() for exp in experiences[:2]]
        
        # Tech industry alignment
        tech_indicators = ["tech", "software", "startup", "saas", "platform"]
        if any(tech in company for company in recent_companies for tech in tech_indicators):
            alignment_bonus += 0.8
    
    # Skills market relevance (trending/in-demand technologies)
    skills_lower = [s.lower() for s in candidate_data.get("skills", [])]
    hot_tech = ["kubernetes", "docker", "react", "typescript", "aws", "gcp", "microservices", "graphql"]
    hot_matches = [tech for tech in hot_tech if any(tech in skill for skill in skills_lower)]
    
    if len(hot_matches) >= 3:
        alignment_bonus += 1.0
    elif len(hot_matches) >= 1:
        alignment_bonus += 0.5
    
    return min(alignment_bonus, 2.0)  # Cap at 2.0


def _calculate_final_strategic_multiplier(strategic_bonuses: Dict[str, float], strategy: Optional[Dict[str, Any]]) -> float:
    """Calculate final multiplier based on overall strategic alignment strength"""
    
    total_bonus_points = sum(strategic_bonuses.values())
    
    # Progressive multiplier based on total strategic alignment
    if total_bonus_points >= 12.0:
        return 1.15  # 15% boost for exceptional strategic fit
    elif total_bonus_points >= 8.0:
        return 1.12  # 12% boost for strong strategic fit
    elif total_bonus_points >= 5.0:
        return 1.08  # 8% boost for good strategic fit
    elif total_bonus_points >= 2.0:
        return 1.05  # 5% boost for some strategic fit
    else:
        return 1.00  # No multiplier boost


# Export the tool
CandidateEvaluationTool = FunctionTool(fn=evaluate_candidates_quality)