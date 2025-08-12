"""Role-specific prompts for enhanced LinkedIn agent targeting"""

from typing import Dict, List, Optional, Any


class RolePromptBuilder:
    """Builds enhanced prompts for LinkedIn recruitment using AI-generated strategy data"""
    
    @classmethod
    def build_enhanced_prompt(
        cls, 
        base_query: str, 
        location: str, 
        limit: int,
        strategy: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build an enhanced agentic workflow prompt"""
        
        # Use strategy if provided, otherwise fall back to basic prompt
        if strategy and not strategy.get("fallback_strategy", False):
            # Extract strategy-based information directly from the SearchStrategy format
            headline_analysis = strategy.get("headline_analysis", {})
            profile_context = strategy.get("profile_evaluation_context", {})
            search_filtering = strategy.get("search_filtering", {})
            
            target_titles = headline_analysis.get("target_job_titles", [base_query])
            alternative_titles = headline_analysis.get("alternative_titles", [])
            tech_stack = headline_analysis.get("tech_stack_signals", [])
            focus_areas = profile_context.get("focus_areas", ["experience", "skills"])
            ideal_candidate = profile_context.get("ideal_candidate_description", f"Experienced {base_query}")
            seniority_keywords = headline_analysis.get("seniority_keywords", ["senior", "lead", "principal"])
            company_indicators = headline_analysis.get("company_indicators", [])
            positive_patterns = search_filtering.get("positive_headline_patterns", [])
            negative_patterns = search_filtering.get("negative_headline_patterns", [])
            
            # Determine role description from strategy data
            role_description = target_titles[0] if target_titles else base_query
        else:
            # Minimal fallback when no strategy available
            target_titles = [base_query]
            alternative_titles = []
            tech_stack = []
            focus_areas = ["experience", "skills"]
            ideal_candidate = f"Experienced {base_query}"
            seniority_keywords = ["senior", "lead", "principal"]
            company_indicators = []
            positive_patterns = []
            negative_patterns = []
            role_description = base_query
        
        # Build the enhanced prompt using strategy data
        prompt_parts = [
            f"You are an expert LinkedIn recruiter specialized in finding top {role_description} candidates.",
            "",
            f"SEARCH OBJECTIVE:",
            f"- Find {limit} high-quality candidates (optimal query and location will be determined by strategy)",
            f"- Focus on candidates with relevant experience and strong profiles",
            f"- Prioritize active professionals with complete LinkedIn profiles",
            "",
            f"STRATEGIC TARGETING (AI-Generated):",
            f"- Primary job titles: {', '.join(target_titles[:5])}",
            f"- Alternative titles: {', '.join(alternative_titles[:5])}" if alternative_titles else "",
            f"- Key technologies: {', '.join(tech_stack[:8])}" if tech_stack else "",
            f"- Seniority indicators: {', '.join(seniority_keywords)}" if seniority_keywords else "",
            f"- Target companies: {', '.join(company_indicators[:5])}" if company_indicators else "",
            "",
            f"PROFILE EVALUATION FOCUS:",
            f"- Priority areas: {', '.join(focus_areas)}" if focus_areas else "",
            f"- Ideal candidate: {ideal_candidate}",
        ]
        
        # Add positive/negative patterns if available from strategy
        if positive_patterns:
            prompt_parts.extend([
                "",
                f"POSITIVE HEADLINE SIGNALS:",
                f"- Look for: {', '.join(positive_patterns[:3])}"
            ])
        
        if negative_patterns:
            prompt_parts.extend([
                "",
                f"NEGATIVE PATTERNS TO AVOID:",
                f"- Skip profiles with: {', '.join(negative_patterns[:3])}"
            ])
        
        prompt_parts.extend([
            "",
            f"AGENTIC WORKFLOW - State-Based Decision Tree:",
            f"",
            f"START → STRATEGY PHASE:",
            f"• strategy_data = create_search_strategy(query='{base_query}', location='{location}')", 
            f"• CRITICAL: Store strategy_data['strategy'] AND strategy_data['search_params'] in memory",
            f"• strategy_data['search_params'] contains the optimal query and location for search",
            f"• strategy_data['strategy'] contains company tiers, tech priorities, bonus weights, and evaluation criteria",
            f"• Proceed to → SEARCH PHASE",
            f"",
            f"SEARCH PHASE:",
            f"• Navigate to LinkedIn and verify authentication", 
            f"• CRITICAL: Use search_params from strategy: search_results = smart_candidate_search(query=strategy_data['search_params']['query'], location=strategy_data['search_params']['location'], target_candidate_count={limit}, strategy=strategy_data['strategy'])",
            f"• Note: Strategy is required for accurate candidate quality assessment during search",
            f"• The search tool autonomously handles all quality thresholds, capacity checks, and candidate filtering",
            f"• Returns search_results['candidates'] when sufficient quality candidates found",
            f"• if search successful → GO TO EXTRACT PHASE with search_results['candidates']",
            f"",
            f"EXTRACT PHASE:",
            f"• extracted_data = extract_candidate_profiles() - get full profile data from search heap",
            f"• extracted_data.results contains list of candidate profiles with structure:",
            f"  {{candidate_info: {{...}}, profile_data: {{...}}, extraction_success: true}}",
            f"• REMEMBER: extracted_data['results'] = list of candidates for next phase",
            f"• Always proceed to → EVALUATE PHASE with extracted_data",
            f"",
            f"EVALUATE PHASE (Decision Point):",
            f"• CRITICAL: Use the strategy from Step 1: eval_results = evaluate_candidates_quality(candidates=extracted_data['results'], strategy=strategy_data['strategy'], min_quality_threshold=6.0)",
            f"• The strategy parameter is ESSENTIAL for strategic bonuses and proper scoring",
            f"• STORE eval_results['quality_candidates'] for outreach phase",
            f"• CHECK 'quality_sufficient' and 'fallback_recommendation' in result:",
            f"",
            f"IF quality_sufficient=True:",
            f"  → GO TO OUTREACH PHASE",
            f"",
            f"IF quality_sufficient=False, follow fallback_recommendation (in priority order):",
            f"  → 'try_heap_backups': Access backup candidates from search heap (when some decent candidates exist but not enough quality ones)",
            f"    backup_candidates = smart_candidate_search(get_heap_backup=True, backup_offset=5, backup_limit=10)",
            f"    → extract_candidate_profiles() → evaluate with backup_data['candidates']",
            f"    REASON: Get candidates beyond top results that might have been overlooked",
            f"  → 'expand_search_scope': Search more LinkedIn pages to find better candidates",
            f"    smart_candidate_search(start_page=search_results['next_start_page']) → EXTRACT PHASE → evaluate with new candidates", 
            f"    REASON: Broaden search scope when current results have insufficient quality",
            f"  → 'lower_quality_threshold': Lower standards as last resort",
            f"    evaluate_candidates_quality(candidates=extracted_data['results'], strategy=strategy_data['strategy'], threshold=4.0)",
            f"    REASON: Accept lower quality candidates when search space is exhausted",
            f"",
            f"OUTREACH PHASE (Final):",
            f"• generate_candidate_outreach(candidates=eval_results['quality_candidates'], position_title=strategy_data['search_params']['query'], location=strategy_data['search_params']['location'])",
            f"• CRITICAL: Use eval_results['quality_candidates'] from previous evaluation step",
            f"• Generate personalized messages for evaluated candidates",
            f"• WORKFLOW COMPLETE",
            "",
            f"QUALITY FOCUS:",
            f"Prioritize candidates with:",
            f"- Professional headlines matching target roles",
            f"- Relevant technology experience: {', '.join(tech_stack[:5])}" if tech_stack else "",
            f"- Appropriate seniority levels: {', '.join(seniority_keywords[:3])}" if seniority_keywords else "",
            f"- Complete and well-structured LinkedIn profiles",
            f"- Experience at reputable companies",
            "",
            f"EXTRACTION FOCUS:",
            f"Ensure comprehensive data extraction from:",
            f"- Professional headline and summary",
            f"- Current and recent work experience", 
            f"- Education background and certifications",
            f"- Skills and endorsements",
            f"- Location and contact information",
            f"",
            f"PARAMETER PASSING RULES:",
            f"- Step 1: strategy_data = create_search_strategy() → STORE strategy_data['strategy']",
            f"- Step 2: smart_candidate_search(query=strategy_data['search_params']['query'], location=strategy_data['search_params']['location'], strategy=strategy_data['strategy']) → search_results",
            f"- Step 3: extract_candidate_profiles() → extracted_data['results']",
            f"- Step 4: eval_results = evaluate_candidates_quality(candidates=extracted_data['results'], strategy=strategy_data['strategy']) → eval_results['quality_candidates']",
            f"- Step 5: generate_candidate_outreach(candidates=eval_results['quality_candidates']) → personalized messages",
            f"",
            f"STATE TRANSITION RULES:",
            f"- Always announce which PHASE you're entering: 'Entering SEARCH PHASE' or 'Moving to EXTRACT PHASE'",
            f"- CRITICAL: Keep strategy_data['strategy'] in memory throughout entire workflow",
            f"- COMPLETE CYCLES for fallbacks:",
            f"  • try_heap_backups: smart_candidate_search(get_heap_backup=True, backup_offset=5) → EXTRACT PHASE → EVALUATE PHASE (use same strategy)",
            f"  • expand_search_scope: SEARCH PHASE → EXTRACT PHASE → EVALUATE PHASE (use same strategy)", 
            f"  • lower_quality_threshold: stay in EVALUATE PHASE with same strategy, lower threshold",
            f"- After ANY candidate gathering (search/heap): you must EXTRACT then EVALUATE with strategy",
            f"- Be autonomous: use tool results to decide state transitions",
            f"- SEARCH TOOL: Handles all quality thresholds autonomously - returns candidates when ready",
            f"- PRIORITY: try heap first, then expand search, finally lower standards"
        ])
        
        return "\n".join(prompt_parts)