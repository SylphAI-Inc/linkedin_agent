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
            f"AGENTIC WORKFLOW - Global State Architecture:",
            f"",
            f"🎯 AGENT ROLE: Workflow orchestrator - coordinate phases, don't transport data",
            f"📊 DATA FLOW: All large data stored in global state, agent gets lightweight status",
            f"🚀 PERFORMANCE: No large parameters = no timeouts or slowdowns",
            f"",
            f"PHASE 1 → STRATEGY:",
            f"• strategy_status = create_search_strategy(query='{base_query}', location='{location}')", 
            f"• Returns: {{success: True, strategy_id: 'workflow_123'}} (lightweight)",
            f"• Strategy automatically stored in global state for all phases",
            f"• Proceed to → PHASE 2 (SEARCH)",
            f"",
            f"PHASE 2 → SEARCH:",
            f"• Navigate to LinkedIn: navigate_to_linkedin()",
            f"• search_status = smart_candidate_search(query='{base_query}', location='{location}', target_candidate_count={limit})",
            f"• Returns: {{success: True, candidates_found: 10}} (lightweight)",
            f"• Search results automatically stored in global state",
            f"• Strategy automatically retrieved from global state by search function",
            f"• If success → PHASE 3 (EXTRACT)",
            f"",
            f"PHASE 3 → EXTRACT:",
            f"• extract_status = extract_candidate_profiles()",
            f"• Returns: {{success: True, extracted_count: 10, failed_count: 0}} (lightweight)",
            f"• Extraction automatically gets candidates from global state",
            f"• Full profiles automatically stored in global state",
            f"• If success → PHASE 4 (EVALUATE)",
            f"",
            f"PHASE 4 → EVALUATE:",
            f"• eval_status = evaluate_candidates_quality(min_quality_threshold=6.0)",
            f"• Returns: {{success: True, candidates_evaluated: 10, quality_sufficient: True}} (lightweight)",
            f"• Evaluation automatically gets candidates and strategy from global state",
            f"• Evaluation results automatically stored in global state",
            f"• Quality candidates automatically available for outreach",
            f"• CHECK eval_status['quality_sufficient']:",
            f"",
            f"IF quality_sufficient=True:",
            f"  → GO TO OUTREACH PHASE",
            f"",
            f"IF quality_sufficient=False, follow eval_status['fallback_recommendation']:",
            f"  → 'try_heap_backup': search_status = smart_candidate_search(get_heap_backup=True)",
            f"    Returns: {{success: True, backup_candidates: 6}} (lightweight)",
            f"    → extract_status = extract_candidate_profiles() → eval_status = evaluate_candidates_quality()",
            f"    All data flows through global state automatically",
            f"",
            f"  → 'expand_search_scope': search_status = smart_candidate_search(expand_scope=True, target_candidate_count={limit})", 
            f"    Returns: {{success: True, additional_candidates: {limit}}} (lightweight)",
            f"    → extract_status = extract_candidate_profiles() → eval_status = evaluate_candidates_quality()",
            f"    All data flows through global state automatically",
            f"",
            f"  → 'lower_quality_threshold': eval_status = evaluate_candidates_quality(min_quality_threshold=4.0)",
            f"    Returns: {{success: True, quality_sufficient: True}} (lightweight)",
            f"",
            f"PHASE 5 → OUTREACH (Final):",
            f"• outreach_status = generate_candidate_outreach(position_title='{base_query}', location='{location}')",
            f"• Returns: {{success: True, outreach_generated: 8, recommended_count: 6}} (lightweight)",
            f"• Outreach automatically gets quality candidates from global state",
            f"• Personalized messages automatically stored in global state",
            f"• 🎉 WORKFLOW COMPLETE - All data available in global state for final results",
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