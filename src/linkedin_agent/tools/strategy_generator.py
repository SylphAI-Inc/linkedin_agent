import sys
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from adalflow.core import Generator
from adalflow.components.output_parsers.dataclass_parser import DataClassParser
from adalflow.components.model_client import OpenAIClient
from ..models.linkedin_profile import SearchStrategy
from ..config import get_model_kwargs


# AdalFlow prompt template for search strategy creation
SEARCH_STRATEGY_PROMPT = r"""<ROLE>
You are an expert LinkedIn recruitment strategist. Your task is to analyze a job description and create a comprehensive strategy for finding and evaluating candidates.
</ROLE>

<CONTEXT>
LinkedIn search results provide limited information:
- Candidate Name
- Professional Headline (e.g., "Senior Software Engineer at Google | Python, React, AWS")  
- Profile URL
- Sometimes location

Full profile extraction happens later with complete job history, education, skills, etc.
</CONTEXT>

<JOB_DESCRIPTION>
{{job_description}}
</JOB_DESCRIPTION>

<TASK>
{% if extraction_mode == "job_description_extraction" %}
EXTRACTION MODE: Analyze the job description and extract the optimal search query and location, then create a targeted strategy.

From the job description, extract:
1. PRIMARY JOB TITLE: The main role title for LinkedIn search (e.g., "Senior Software Engineer", "Product Manager", "Data Scientist")
2. OPTIMAL LOCATION: Best location for search (use specific city/state if mentioned, otherwise "United States")

Then analyze and extract:
- Role title variations and alternative titles
- Required technical skills and programming languages
- Preferred frameworks, tools, and technologies
- Experience level and seniority requirements
{% elif extraction_mode == "hybrid" %}
HYBRID MODE: Create targeted strategy for "{{query}}" in {{location}} using job description context.
{% if query == "EXTRACT_FROM_JOB_DESCRIPTION" %}
Extract the optimal search query from the job description.
{% endif %}
{% if location == "EXTRACT_FROM_JOB_DESCRIPTION" %}
Extract the optimal location from the job description (default to "United States" if unclear).
{% endif %}

Analyze the job description for:
- Role requirements and technical skills
- Experience level and seniority needs
{% else %}
TRADITIONAL MODE: Create targeted strategy for "{{query}}" in {{location}}{% if job_description %} using job description context{% endif %}.

{% if job_description %}
Analyze the job description for enhanced targeting:
- Specific technical requirements matching the query
- Experience level and seniority alignment
{% endif %}
{% endif %}

Key analysis areas:
- Required technical skills and programming languages
- Preferred frameworks, tools, and technologies
- Experience level and seniority requirements
- Company type, size, and industry context
- Key responsibilities and qualifications
- Educational preferences
- Company or background preferences

Create a highly targeted strategy focusing on:
1. What to look for in headlines (limited search result info)
2. How to evaluate full profiles when extracted
3. Realistic quality standards based on requirements
4. Bonus criteria for exceptional candidates
</TASK>

<OUTPUT_FORMAT>
Return valid JSON with this exact structure:
{
  "search_params": {
    "query": "extracted or provided job title for LinkedIn search",
    "location": "extracted or provided location for search"
  },
  "headline_analysis": {
    "target_job_titles": ["exact titles to match in headlines"],
    "alternative_titles": ["similar/related titles"],
    "seniority_keywords": ["words indicating experience level"],
    "company_indicators": ["words suggesting good companies"],
    "tech_stack_signals": ["technology keywords to look for"],
    "role_relevance_keywords": ["must-have words for basic relevance"]
  },
  "search_filtering": {
    "positive_headline_patterns": ["patterns that suggest quality"],
    "negative_headline_patterns": ["patterns to avoid"],
    "minimum_headline_score": 4.0,
    "ideal_headline_score": 7.0
  },
  "profile_evaluation_context": {
    "focus_areas": ["key areas to analyze in full profile"],
    "quality_indicators": ["what makes a strong candidate"],
    "experience_evaluation": ["how to assess work experience"],
    "ideal_candidate_description": "detailed description of perfect match",
    "deal_breakers": ["absolute red flags to avoid"]
  },
  "evaluation_criteria": {
    "company_tiers": {
      "tier_1": ["list of top tier companies for max bonus"],
      "tier_2": ["list of good companies for high bonus"],
      "target_companies": ["specific companies prioritized for this role"]
    },
    "seniority_mapping": {
      "executive": ["C-level and VP titles"],
      "principal": ["Principal, Staff, Architect levels"],
      "senior": ["Senior and Lead levels"],
      "target_seniority": "preferred level for this role"
    },
    "technology_priorities": {
      "must_have": ["critical technologies - highest bonus"],
      "preferred": ["valuable technologies - medium bonus"],
      "complementary": ["nice-to-have technologies - small bonus"]
    },
    "education_criteria": {
      "top_schools": ["elite universities for max education bonus"],
      "relevant_degrees": ["degrees that are highly relevant"],
      "preferred_fields": ["fields of study that align with role"]
    },
    "bonus_weights": {
      "company_tier_multiplier": 2.5,
      "seniority_alignment_multiplier": 2.0,
      "tech_depth_multiplier": 3.0,
      "education_multiplier": 2.0,
      "progression_multiplier": 2.5,
      "market_alignment_multiplier": 2.0
    },
    "role_focus": {
      "primary_focus": "technical|leadership|product|design",
      "experience_weight": 0.35,
      "skills_weight": 0.25,
      "strategic_weight": 0.20,
      "education_weight": 0.10
    }
  },
  "search_terms": ["optimized LinkedIn search keywords to try"]
}
</OUTPUT_FORMAT>

<EXAMPLES>
Query: "senior frontend developer" in "New York"
Strategy would focus on:
- Headlines: "frontend", "front-end", "UI", "React", "Vue"
- Seniority: "senior", "lead", "staff" (target: senior level)
- Companies: Tier 1: Google, Facebook; Tier 2: Stripe, Airbnb
- Tech priorities: Must-have: React, JavaScript; Preferred: TypeScript, CSS
- Bonus weights: High tech_depth (3.0x), medium company (2.5x)

Query: "product manager" in "San Francisco" 
Strategy would focus on:
- Headlines: "product manager", "PM", "product lead", "product owner"
- Companies: B2B SaaS, consumer tech, fintech
- Tech priorities: Must-have: Analytics, A/B testing; Preferred: SQL, Python
- Bonus weights: High progression (2.5x), high strategic alignment (2.0x)
- Role focus: Strategic thinking, stakeholder management
</EXAMPLES>

<INSTRUCTIONS>
- Be realistic about headline limitations - we only see 1-2 lines of text
- Focus on achievable filtering based on minimal search result data
- Provide comprehensive guidance for later full profile evaluation
- Balance quality standards with market realities
- Consider the specific role requirements and location market
- Structure evaluation_criteria for systematic bonus calculations
- Set appropriate bonus multipliers based on role importance
- Define clear company tiers relevant to the role and location
- Prioritize technologies based on role criticality (must-have vs nice-to-have)
- Map seniority levels to role requirements (don't aim too high/low)
</INSTRUCTIONS>"""


class StrategyGenerator:
    def __init__(self):
        self.client = OpenAIClient()
        self.parser = DataClassParser(
            data_class=SearchStrategy,
            return_data_class=True,
            format_type="json"
        )
        
        # Base generator for general scoring
        self.generator = Generator(
            model_client=self.client,
            model_kwargs=get_model_kwargs(),
            template=SEARCH_STRATEGY_PROMPT,
            output_processors=self.parser
        )
        
            
    def create_search_strategy(self, query: Optional[str] = None, location: Optional[str] = None, job_description: Optional[str] = None) -> Dict[str, Any]:
        """Create comprehensive search strategy using AdalFlow with intelligent parameter handling"""
        
        # Intelligent input validation and processing
        final_query, final_location, mode = self._process_input_parameters(query, location, job_description)
        
        try:
            if mode == "job_description_extraction":
                print(f"📋 Extracting search parameters from job description ({len(job_description)} characters)")
            elif mode == "traditional":
                print(f"🎯 Creating strategy for: '{final_query}' in {final_location}")
            elif mode == "hybrid":
                print(f"🔄 Hybrid mode: using provided params + job description context")
            
            result = self.generator(prompt_kwargs={
                "query": final_query,
                "location": final_location,
                "job_description": job_description or "",
                "extraction_mode": mode
            })
            
            if hasattr(result, 'data') and result.data:
                strategy = result.data
                # Ensure search_params are included in output
                if "search_params" not in strategy:
                    strategy["search_params"] = {
                        "query": final_query,
                        "location": final_location
                    }
                return strategy
            else:
                # Fallback strategy if LLM call fails
                return self.create_fallback_strategy(final_query, final_location)
                
        except Exception as e:
            print(f"Strategy creation failed: {e}")
            return self.create_fallback_strategy(final_query, final_location)
    
    def _process_input_parameters(self, query: Optional[str], location: Optional[str], job_description: Optional[str]) -> tuple[str, str, str]:
        """Intelligently process input parameters and determine processing mode"""
        
        # Case 1: No job description - must have query
        if not job_description:
            if not query:
                raise ValueError("❌ Either 'query' or 'job_description' must be provided")
            final_query = query
            final_location = location or "United States"
            return final_query, final_location, "traditional"
        
        # Case 2: Have job description - extract missing parameters
        if not query and not location:
            # Pure job description mode - will extract both
            print("🧠 Job description only mode - will extract query and location")
            return "EXTRACT_FROM_JOB_DESCRIPTION", "EXTRACT_FROM_JOB_DESCRIPTION", "job_description_extraction"
        
        elif query and not location:
            # Hybrid: use provided query, extract location
            print(f"🔄 Hybrid mode: using query '{query}', will extract location from job description")
            return query, "EXTRACT_FROM_JOB_DESCRIPTION", "hybrid"
        
        elif not query and location:
            # Hybrid: extract query, use provided location  
            print(f"🔄 Hybrid mode: will extract query from job description, using location '{location}'")
            return "EXTRACT_FROM_JOB_DESCRIPTION", location, "hybrid"
        
        else:
            # Have all parameters - traditional mode with job description context
            print(f"✅ All parameters provided: query='{query}', location='{location}' + job description context")
            return query, location, "traditional"
    
        
        
    def create_fallback_strategy(self, query: str, location: str = "") -> Dict[str, Any]:
        """Fallback strategy when LLM is unavailable"""
        # Extract basic keywords from query
        query_words = query.lower().split()
        
        return {
            "search_params": {
                "query": query,
                "location": location or "United States"
            },
            "headline_analysis": {
                "target_job_titles": [query.lower()],
                "alternative_titles": query_words,
                "seniority_keywords": ["senior", "staff", "principal", "lead", "director"],
                "company_indicators": ["google", "facebook", "apple", "microsoft", "amazon"],
                "tech_stack_signals": ["python", "react", "java", "aws", "kubernetes"],
                "role_relevance_keywords": query_words
            },
            "search_filtering": {
                "positive_headline_patterns": ["senior", "lead", "experienced"],
                "negative_headline_patterns": ["intern", "entry", "junior"],
                "minimum_headline_score": 3.0,
                "ideal_headline_score": 6.0
            },
            "profile_evaluation_context": {
                "focus_areas": ["work experience", "technical skills", "career progression"],
                "quality_indicators": ["relevant experience", "good companies", "skill progression"],
                "experience_evaluation": ["role relevance", "company quality", "tenure"],
                "ideal_candidate_description": f"Experienced {query} with relevant background",
                "deal_breakers": ["completely irrelevant experience", "no relevant skills"]
            },
            "evaluation_criteria": {
                "company_tiers": {
                    "tier_1": ["google", "facebook", "apple", "microsoft", "amazon", "netflix"],
                    "tier_2": ["uber", "airbnb", "stripe", "dropbox", "slack", "salesforce"],
                    "target_companies": ["google", "facebook", "netflix", "uber"]
                },
                "seniority_mapping": {
                    "executive": ["cto", "vp", "director", "head of"],
                    "principal": ["principal", "staff", "architect", "distinguished"],
                    "senior": ["senior", "lead", "sr."],
                    "target_seniority": "senior"
                },
                "technology_priorities": {
                    "must_have": ["python", "javascript", "react"],
                    "preferred": ["aws", "docker", "kubernetes", "sql"],
                    "complementary": ["typescript", "node.js", "postgresql"]
                },
                "education_criteria": {
                    "top_schools": ["stanford", "mit", "berkeley", "carnegie mellon"],
                    "relevant_degrees": ["computer science", "software engineering"],
                    "preferred_fields": ["computer science", "engineering", "mathematics"]
                },
                "bonus_weights": {
                    "company_tier_multiplier": 2.5,
                    "seniority_alignment_multiplier": 2.0,
                    "tech_depth_multiplier": 3.0,
                    "education_multiplier": 2.0,
                    "progression_multiplier": 2.5,
                    "market_alignment_multiplier": 2.0
                },
                "role_focus": {
                    "primary_focus": "technical",
                    "experience_weight": 0.35,
                    "skills_weight": 0.25,
                    "strategic_weight": 0.20,
                    "education_weight": 0.10
                }
            },
            "search_terms": [query, f"{query} {location}".strip()]
        }
        