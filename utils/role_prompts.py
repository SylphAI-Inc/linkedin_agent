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
        """Build an enhanced prompt using strategy data - no role_type needed"""
        
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
            f"- Find {limit} high-quality candidates for '{base_query}' in {location}",
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
            f"EXECUTION STEPS:",
            f"1. Navigate to LinkedIn and verify authentication",
            f"2. Search for people with '{base_query}' in {location}",
            f"3. Use smart_candidate_search to build a curated candidate heap:",
            f"   - Required parameters: query='{base_query}', location='{location}'",
            f"   - Strategy parameter: Use the strategy information provided in this prompt",
            f"   - Optional: page_limit=3, start_page=0, min_score_threshold=7.0, target_candidate_count={limit}",
            f"   - Find candidates matching target titles: {', '.join(target_titles[:3])}",
            f"   - Apply quality scoring with strategic bonuses",
            f"   - Build ranked heap of top {limit} candidates by quality",
            f"   - Prioritize candidates from target companies: {', '.join(company_indicators[:3])}" if company_indicators else "",
            f"   - CHECK: Examine the result for 'extraction_quality_gate' status",
            f"   - If result shows 'gate_status': 'failed', consider fallback options",
            f"4. IF quality gate passed (gate_status != 'failed'), use extract_candidate_profiles:",
            f"   - Extract detailed profiles from the curated heap candidates",
            f"   - Get full experience, education, and skills data",
            f"   - Validate extraction quality for each candidate",
            f"5. IF extraction results are disappointing, you have intelligent fallback options:",
            f"   a) EXPLORE HEAP: Use get_collected_candidates to try more candidates",
            f"      - Example: get_collected_candidates(limit=10, sort_by_score=True)",
            f"      - This accesses backup candidates from your existing heap",
            f"   b) EXPAND SEARCH: Continue searching from where you left off",
            f"      - Use the next_start_page from your previous search result",
            f"      - Extract 'next_start_page' value from previous search result",
            f"      - Example: smart_candidate_search(query='{base_query}', location='{location}', start_page=3, page_limit=3)",
            f"      - This efficiently continues from the last searched page",
            f"   c) ADJUST STRATEGY: Lower quality thresholds if market is challenging",
            f"      - Use lower min_score_threshold (e.g., 4.0 instead of 7.0)",
            f"      - Use lower extraction_quality_gate (e.g., 3.0 instead of 5.0)",
            f"   d) PROGRESSIVE FALLBACK LOGIC:",
            f"      - Try heap backups first (get_collected_candidates)",
            f"      - Then expand search scope (higher page_limit)", 
            f"      - Finally adjust quality thresholds (lower min_score_threshold)",
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
            f"IMPORTANT NOTES:",
            f"- Always check tool results for success/failure status",
            f"- Look for 'extraction_quality_gate' status in smart_candidate_search results",
            f"- Extract 'next_start_page' values for efficient continuation",
            f"- Use exact parameter names: query, location, start_page, page_limit, etc.",
            f"- If tools fail, examine error messages and adjust parameters accordingly"
        ])
        
        return "\n".join(prompt_parts)