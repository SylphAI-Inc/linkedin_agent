"""Role-specific prompts for enhanced LinkedIn agent targeting"""

from typing import Dict, List, Optional


class RolePromptBuilder:
    """Builds enhanced, role-specific prompts for LinkedIn recruitment"""
    
    # Role-specific focus areas and keywords
    ROLE_CONTEXTS = {
        "software_engineer": {
            "focus_keywords": [
                "Python", "JavaScript", "React", "Node.js", "AWS", "Docker", "Kubernetes",
                "full-stack", "backend", "frontend", "API", "microservices", "CI/CD"
            ],
            "experience_indicators": [
                "years of experience", "senior", "lead", "principal", "staff",
                "built", "developed", "architected", "scaled", "optimized"
            ],
            "priority_sections": ["experience", "skills", "projects"],
            "scoring_focus": "Look for technical depth, system design experience, and modern technology stack usage."
        },
        
        "product_manager": {
            "focus_keywords": [
                "product management", "roadmap", "strategy", "analytics", "user research",
                "A/B testing", "metrics", "stakeholder", "cross-functional", "launch"
            ],
            "experience_indicators": [
                "managed", "launched", "led", "coordinated", "delivered",
                "product owner", "scrum", "agile", "growth", "retention"
            ],
            "priority_sections": ["experience", "achievements", "leadership"],
            "scoring_focus": "Look for product leadership, data-driven decision making, and successful product launches."
        },
        
        "sales_executive": {
            "focus_keywords": [
                "sales", "revenue", "quota", "CRM", "pipeline", "forecasting",
                "enterprise", "B2B", "SaaS", "client relationship", "negotiation"
            ],
            "experience_indicators": [
                "exceeded", "achieved", "generated", "closed", "managed",
                "top performer", "president's club", "quota attainment"
            ],
            "priority_sections": ["experience", "achievements", "results"],
            "scoring_focus": "Look for quantifiable sales results, relationship building skills, and industry expertise."
        },
        
        "marketing_manager": {
            "focus_keywords": [
                "marketing", "campaigns", "digital marketing", "SEO", "SEM", "social media",
                "content", "brand", "analytics", "conversion", "growth marketing"
            ],
            "experience_indicators": [
                "increased", "improved", "optimized", "drove", "managed",
                "campaign performance", "lead generation", "brand awareness"
            ],
            "priority_sections": ["experience", "campaigns", "results"],
            "scoring_focus": "Look for creative marketing campaigns, data-driven results, and multi-channel expertise."
        },
        
        "data_scientist": {
            "focus_keywords": [
                "machine learning", "data science", "Python", "R", "SQL", "statistics",
                "modeling", "analytics", "big data", "AI", "deep learning"
            ],
            "experience_indicators": [
                "analyzed", "modeled", "predicted", "optimized", "researched",
                "PhD", "published", "algorithms", "insights", "recommendations"
            ],
            "priority_sections": ["experience", "education", "publications"],
            "scoring_focus": "Look for advanced analytics skills, research background, and business impact of data work."
        },
        
        "designer": {
            "focus_keywords": [
                "UI/UX", "design", "Figma", "Sketch", "user experience", "prototyping",
                "visual design", "interaction design", "design systems", "usability"
            ],
            "experience_indicators": [
                "designed", "created", "improved", "collaborated", "researched",
                "user-centered", "design thinking", "accessibility", "responsive"
            ],
            "priority_sections": ["experience", "portfolio", "projects"],
            "scoring_focus": "Look for design process expertise, user-centered thinking, and portfolio quality."
        }
    }
    
    @classmethod
    def detect_role_type(cls, query: str) -> str:
        """Detect the most likely role type from a search query"""
        query_lower = query.lower()
        
        # Direct role matching
        role_patterns = {
            "software_engineer": ["software engineer", "developer", "programmer", "swe", "backend", "frontend", "full stack", "full-stack"],
            "product_manager": ["product manager", "pm", "product owner", "product lead"],
            "sales_executive": ["sales", "account executive", "sales rep", "business development"],
            "marketing_manager": ["marketing", "marketing manager", "digital marketing", "growth marketing"],
            "data_scientist": ["data scientist", "data analyst", "ml engineer", "machine learning"],
            "designer": ["designer", "ui designer", "ux designer", "product designer"]
        }
        
        for role, patterns in role_patterns.items():
            for pattern in patterns:
                if pattern in query_lower:
                    return role
        
        return "software_engineer"  # Default fallback
    
    @classmethod
    def build_enhanced_prompt(
        cls, 
        base_query: str, 
        location: str, 
        limit: int,
        role_type: Optional[str] = None,
        custom_focus: Optional[List[str]] = None
    ) -> str:
        """Build an enhanced, role-specific prompt for LinkedIn search"""
        
        # Auto-detect role if not specified
        if role_type is None:
            role_type = cls.detect_role_type(base_query)
        
        # Get role context or use default
        context = cls.ROLE_CONTEXTS.get(role_type, cls.ROLE_CONTEXTS["software_engineer"])
        
        # Build the enhanced prompt
        prompt_parts = [
            f"You are an expert LinkedIn recruiter specialized in finding top {role_type.replace('_', ' ')} candidates.",
            "",
            f"SEARCH OBJECTIVE:",
            f"- Find {limit} high-quality candidates for '{base_query}' in {location}",
            f"- Focus on candidates with relevant experience and strong profiles",
            f"- Prioritize active professionals with complete LinkedIn profiles",
            "",
            f"ROLE-SPECIFIC FOCUS:",
            f"- Key skills: {', '.join(context['focus_keywords'][:8])}",
            f"- Experience indicators: {', '.join(context['experience_indicators'][:5])}",
            f"- Priority profile sections: {', '.join(context['priority_sections'])}",
            f"- {context['scoring_focus']}",
            "",
            f"EXECUTION STEPS:",
            f"1. Navigate to LinkedIn and verify authentication",
            f"2. Search for people with '{base_query}' in {location}",
            f"3. For each of the top {limit} candidates found:",
            f"   - Review their profile preview for relevance",
            f"   - Click to open their full profile",
            f"   - Extract comprehensive profile data using extract_complete_profile",
            f"   - Verify the data quality before moving to next candidate",
            f"4. Focus on candidates with:",
            f"   - Clear professional headlines matching the role",
            f"   - Relevant work experience at reputable companies",
            f"   - Active LinkedIn presence (recent posts/activity)",
            f"   - Complete profile information",
            "",
            f"QUALITY GUIDELINES:",
            f"- Skip profiles that appear incomplete or inactive",
            f"- Prioritize candidates at target companies or with target skills",
            f"- Ensure profile extraction captures key experience and education details",
            f"- Take small, deliberate actions and verify each step",
            "",
            f"EXTRACTION FOCUS:",
            f"Pay special attention to extracting clean, relevant data from these sections:",
            f"- Professional headline and summary",
            f"- Current and recent work experience",
            f"- Education background",
            f"- Skills and endorsements",
            f"- Location and contact information"
        ]
        
        return "\n".join(prompt_parts)
    
    @classmethod
    def build_scoring_context(cls, role_type: str) -> Dict[str, any]:
        """Build context for candidate scoring based on role type"""
        context = cls.ROLE_CONTEXTS.get(role_type, cls.ROLE_CONTEXTS["software_engineer"])
        
        return {
            "role_type": role_type,
            "key_skills": context["focus_keywords"],
            "experience_indicators": context["experience_indicators"],
            "scoring_focus": context["scoring_focus"],
            "priority_sections": context["priority_sections"]
        }
    
    @classmethod
    def get_role_specific_instructions(cls, role_type: str) -> str:
        """Get specific instructions for a role type"""
        context = cls.ROLE_CONTEXTS.get(role_type, cls.ROLE_CONTEXTS["software_engineer"])
        
        instructions = [
            f"For {role_type.replace('_', ' ')} candidates, focus on:",
            f"• Technical skills: {', '.join(context['focus_keywords'][:5])}",
            f"• Experience markers: {', '.join(context['experience_indicators'][:3])}",
            f"• {context['scoring_focus']}"
        ]
        
        return "\n".join(instructions)


# Example usage and testing
if __name__ == "__main__":
    # Test role detection
    test_queries = [
        "senior software engineer python",
        "product manager saas",
        "sales executive enterprise",
        "ux designer figma",
        "data scientist machine learning"
    ]
    
    builder = RolePromptBuilder()
    
    for query in test_queries:
        detected = builder.detect_role_type(query)
        print(f"Query: '{query}' -> Detected role: {detected}")
        
        # Test enhanced prompt building
        enhanced = builder.build_enhanced_prompt(query, "San Francisco Bay Area", 3)
        print(f"Enhanced prompt length: {len(enhanced)} characters")
        print("=" * 50)