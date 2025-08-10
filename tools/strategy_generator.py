import sys
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from adalflow.core import Generator
from adalflow.components.output_parsers.dataclass_parser import DataClassParser
from adalflow.components.model_client import OpenAIClient
from models.linkedin_profile import SearchStrategy
from config import get_model_kwargs

# AdalFlow prompt template for search strategy creation
SEARCH_STRATEGY_PROMPT = r"""<ROLE>
You are an expert LinkedIn recruitment strategist. Your task is to analyze a search query and create a comprehensive strategy for finding and evaluating candidates.
</ROLE>

<CONTEXT>
LinkedIn search results provide limited information:
- Candidate Name
- Professional Headline (e.g., "Senior Software Engineer at Google | Python, React, AWS")  
- Profile URL
- Sometimes location

Full profile extraction happens later with complete job history, education, skills, etc.
</CONTEXT>

<TASK>
Create a search strategy for: "{{query}}" in {{location}}

Break this down into:
1. What to look for in headlines (limited search result info)
2. How to evaluate full profiles when extracted
3. Realistic quality standards
</TASK>

<OUTPUT_FORMAT>
Return valid JSON with this exact structure:
{
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
  "search_terms": ["optimized LinkedIn search keywords to try"]
}
</OUTPUT_FORMAT>

<EXAMPLES>
Query: "senior frontend developer" in "New York"
Strategy would focus on:
- Headlines containing "frontend", "front-end", "UI", "React", "Vue"
- Seniority: "senior", "lead", "staff", "principal"
- Companies: recognizable tech companies, well-funded startups
- Profile evaluation: depth of frontend experience, modern frameworks, design collaboration

Query: "product manager" in "San Francisco" 
Strategy would focus on:
- Headlines with "product manager", "PM", "product lead", "product owner"
- Companies: tech companies, startups, B2B/B2C product companies
- Profile evaluation: product launches, metrics impact, stakeholder management
</EXAMPLES>

<INSTRUCTIONS>
- Be realistic about headline limitations - we only see 1-2 lines of text
- Focus on achievable filtering based on minimal search result data
- Provide comprehensive guidance for later full profile evaluation
- Balance quality standards with market realities
- Consider the specific role requirements and location market
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
        
            
    def create_search_strategy(self, query: str, location: str = "") -> Dict[str, Any]:
        """Create comprehensive search strategy using AdalFlow"""
        try:
            result = self.generator(prompt_kwargs={
                "query": query,
                "location": location or "Any Location"
            })
            
            if hasattr(result, 'data') and result.data:
                return result.data
            else:
                # Fallback strategy if LLM call fails
                return self.create_fallback_strategy(query, location)
                
        except Exception as e:
            print(f"Strategy creation failed: {e}")
            return self.create_fallback_strategy(query, location)
        
        
    def create_fallback_strategy(self, query: str, location: str = "") -> Dict[str, Any]:
        """Fallback strategy when LLM is unavailable"""
        # Extract basic keywords from query
        query_words = query.lower().split()
        
        return {
            "headline_analysis": {
                "target_job_titles": [query.lower()],
                "alternative_titles": query_words,
                "seniority_keywords": ["senior", "staff", "principal", "lead", "director"],
                "company_indicators": ["@", "at", "inc", "corp", "ltd"],
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
            "search_terms": [query, f"{query} {location}".strip()]
        }
        