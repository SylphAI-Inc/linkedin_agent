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
            f"3. For each of the top {limit} candidates found:",
            f"   - Review their profile preview for relevance",
            f"   - Look for target titles: {', '.join(target_titles[:3])}",
            f"   - Check for key technologies: {', '.join(tech_stack[:5])}" if tech_stack else "",
            f"   - Click to open their full profile",
            f"   - Extract comprehensive profile data using extract_complete_profile",
            f"   - Verify the data quality before moving to next candidate",
            f"4. Focus on candidates with:",
            f"   - Clear professional headlines matching the role",
            f"   - Relevant work experience at reputable companies",
            f"   - Active LinkedIn presence (recent posts/activity)",
            f"   - Complete profile information",
            "",
            f"EXTRACTION FOCUS:",
            f"Pay special attention to extracting clean, relevant data from these sections:",
            f"- Professional headline and summary",
            f"- Current and recent work experience",
            f"- Education background",
            f"- Skills and endorsements",
            f"- Location and contact information"
        ])
        
        return "\n".join(prompt_parts)