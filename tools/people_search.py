from typing import List, Dict, Any
from urllib.parse import quote_plus
import time

from adalflow.core.func_tool import FunctionTool
from .web_nav import js as run_js, go as nav_go, wait as nav_wait
from .linkedin_selectors import SEARCH_INPUT, PEOPLE_TAB, SEARCH_RESULTS_CARDS
from adalflow.core import Generator
from adalflow.components.model_client import OpenAIClient
from adalflow.components.output_parsers import JsonOutputParser
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

# AdalFlow prompt for profile evaluation with strategy context
PROFILE_EVALUATION_PROMPT = r"""<ROLE>
You are an expert recruiter specializing in candidate assessment. You evaluate LinkedIn profiles against specific role requirements and provide detailed recommendations.
</ROLE>

<CONTEXT>
Search Strategy Context:
{{strategy_context}}

You are evaluating a candidate who passed initial headline screening and now have their full LinkedIn profile data.
</CONTEXT>

<TASK>
Evaluate this candidate's full profile for the target role. Provide a comprehensive assessment including scores, reasoning, and interview guidance.
</TASK>

<PROFILE_DATA>
{{profile_data}}
</PROFILE_DATA>

<EVALUATION_FRAMEWORK>
Score each area 1-10 and provide reasoning:

1. ROLE FIT: How well does their background match the target role?
   - Consider: job titles, responsibilities, industry experience
   
2. EXPERIENCE QUALITY: Assess the depth and progression of their experience
   - Consider: company reputation, role progression, tenure, accomplishments
   
3. TECHNICAL COMPETENCY: Evaluate their technical skills and expertise
   - Consider: relevant technologies, projects, certifications, continuous learning
   
4. CAREER TRAJECTORY: Analyze their professional growth and potential
   - Consider: promotions, company moves, expanding responsibilities, leadership

5. CULTURAL FIT INDICATORS: Assess alignment with typical role requirements
   - Consider: collaboration signals, communication skills, work style indicators
</EVALUATION_FRAMEWORK>

<OUTPUT_FORMAT>
Return valid JSON:
{
  "evaluation_summary": {
    "overall_recommendation": "strong_yes|yes|maybe|no",
    "overall_score": "X.X/10",
    "confidence_level": "high|medium|low",
    "summary_reasoning": "concise 2-3 sentence assessment"
  },
  "detailed_scores": {
    "role_fit": {"score": "X.X", "reasoning": "detailed explanation"},
    "experience_quality": {"score": "X.X", "reasoning": "detailed explanation"},
    "technical_competency": {"score": "X.X", "reasoning": "detailed explanation"},
    "career_trajectory": {"score": "X.X", "reasoning": "detailed explanation"},
    "cultural_fit_indicators": {"score": "X.X", "reasoning": "detailed explanation"}
  },
  "key_strengths": ["list of 3-5 strongest points"],
  "areas_of_concern": ["list of any concerns or gaps"],
  "interview_focus_areas": ["3-4 specific areas to explore in interviews"],
  "compensation_guidance": {
    "likely_current_range": "estimated based on experience",
    "target_offer_range": "recommended offer range",
    "negotiation_insights": "factors that might influence negotiation"
  }
}
</OUTPUT_FORMAT>

<INSTRUCTIONS>
- Be thorough but realistic in your assessment
- Focus on potential and growth, not just perfect matches
- Consider market context and role-specific requirements
- Provide actionable insights for hiring decisions
- Balance critical analysis with fair evaluation
- Use the strategy context to inform your evaluation priorities
</INSTRUCTIONS>"""


def _js_click_first(sel: str) -> bool:
    code = f"""
    (() => {{
      const el = document.querySelector('{sel}'.replace(/'/g, "\\'"));
      if (!el) return false;
      el.click();
      return true;
    }})()
    """
    return bool(run_js(code))

# Initialize AdalFlow generators for strategy and evaluation
_strategy_generator = None
_evaluation_generator = None

def get_strategy_generator():
    """Get or create strategy generator"""
    global _strategy_generator
    if _strategy_generator is None:
        _strategy_generator = Generator(
            model_client=OpenAIClient(),
            model_kwargs=get_model_kwargs(),
            template=SEARCH_STRATEGY_PROMPT,
            output_processors=JsonOutputParser()
        )
    return _strategy_generator

def get_evaluation_generator():
    """Get or create evaluation generator"""  
    global _evaluation_generator
    if _evaluation_generator is None:
        _evaluation_generator = Generator(
            model_client=OpenAIClient(),
            model_kwargs=get_model_kwargs(),
            template=PROFILE_EVALUATION_PROMPT,
            output_processors=JsonOutputParser()
        )
    return _evaluation_generator

def create_search_strategy(query: str, location: str = "") -> Dict[str, Any]:
    """Create comprehensive search strategy using AdalFlow"""
    try:
        generator = get_strategy_generator()
        result = generator(prompt_kwargs={
            "query": query,
            "location": location or "Any Location"
        })
        
        if hasattr(result, 'data') and result.data:
            return result.data
        else:
            # Fallback strategy if LLM call fails
            return create_fallback_strategy(query, location)
            
    except Exception as e:
        print(f"Strategy creation failed: {e}")
        return create_fallback_strategy(query, location)

def create_fallback_strategy(query: str, location: str = "") -> Dict[str, Any]:
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

def evaluate_headline_with_strategy(headline: str, strategy: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate candidate headline using strategy - no LLM needed"""
    if not headline or not strategy:
        return {"score": 0.0, "worth_extracting": False, "signals": []}
    
    headline_lower = headline.lower()
    score = 0.0
    signals = []
    
    # Job title relevance
    target_titles = strategy.get("headline_analysis", {}).get("target_job_titles", [])
    alternative_titles = strategy.get("headline_analysis", {}).get("alternative_titles", [])
    
    if any(title in headline_lower for title in target_titles):
        score += 3.0
        signals.append("exact_title_match")
    elif any(alt in headline_lower for alt in alternative_titles):
        score += 2.0
        signals.append("alternative_title_match")
    
    # Seniority indicators
    seniority_keywords = strategy.get("headline_analysis", {}).get("seniority_keywords", [])
    if any(keyword in headline_lower for keyword in seniority_keywords):
        score += 1.5
        signals.append("seniority_indicated")
    
    # Company indicators
    company_indicators = strategy.get("headline_analysis", {}).get("company_indicators", [])
    if any(indicator in headline_lower for indicator in company_indicators):
        score += 1.0
        signals.append("company_mentioned")
    
    # Tech stack signals
    tech_signals = strategy.get("headline_analysis", {}).get("tech_stack_signals", [])
    matching_tech = [tech for tech in tech_signals if tech in headline_lower]
    if matching_tech:
        score += len(matching_tech) * 0.5
        signals.append(f"tech_stack: {matching_tech}")
    
    # Check for negative patterns
    negative_patterns = strategy.get("search_filtering", {}).get("negative_headline_patterns", [])
    if any(pattern in headline_lower for pattern in negative_patterns):
        score -= 2.0
        signals.append("negative_pattern_detected")
    
    min_score = strategy.get("search_filtering", {}).get("minimum_headline_score", 3.0)
    
    return {
        "score": score,
        "worth_extracting": score >= min_score,
        "signals": signals
    }

def search_people(query: str, location: str = "", limit: int = 10) -> Dict[str, Any]:
    """Navigate LinkedIn people search and return lightweight result cards (name, subtitle, url).

    Returns a structured payload to help the agent reason:
      { "count": int, "results": [{ name, subtitle, url }] }
    """
    q = (query + (f" {location}" if location else "")).strip()
    url = f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(q)}"
    nav_go(url)
    # Wait for search results 
    nav_wait(".search-results-container li, .search-no-results", 12)
    
    # Prefer People tab when present (best-effort)
    _js_click_first(PEOPLE_TAB)
    nav_wait(".search-results-container li", 5)

    # Check for results using the correct selector
    code_count = """
    (() => {
      const nodes = document.querySelectorAll('.search-results-container li');
      return nodes ? nodes.length : 0;
    })()
    """
    count = int(run_js(code_count) or 0)
    
    # Light scrolling to ensure all results are loaded
    if count > 0:
        run_js("window.scrollBy(0, 800);")
        nav_wait(".search-results-container li", 2)
        count = int(run_js(code_count) or 0)

    if count == 0:
        return {"count": 0, "results": [], "error": "No search results found"}

    code_collect = f"""
    (() => {{
      const containers = Array.from(document.querySelectorAll('.search-results-container li')).slice(0, {limit});
      
      return containers.map(li => {{
        const profileLink = li.querySelector('a[href*="/in/"]');
        const lines = li.textContent.split('\\n').map(l => l.trim()).filter(l => l && l !== 'Status is offline');
        
        // Find name using LinkedIn's pattern
        let name = null;
        for (const line of lines) {{
          if ((line.includes("'s profile") || line.includes("'s profile") || line.includes("s profile")) && 
              line.includes("View ") && !line.includes('•') && !line.includes('degree')) {{
            const viewIndex = line.indexOf('View ');
            if (viewIndex > 0) {{
              const beforeView = line.substring(0, viewIndex).trim();
              if (beforeView.length > 2 && beforeView.length < 50) {{
                name = beforeView;
                break;
              }}
            }}
          }}
        }}
        
        // Find subtitle - usually appears after connection info
        let subtitle = null;
        let foundConnectionLine = false;
        for (const line of lines) {{
          if (line.includes('degree connection')) {{
            foundConnectionLine = true;
            continue;
          }}
          if (foundConnectionLine && line && !line.includes('degree') && !line.includes('View ') && !line.includes('Status is') && line.length > 5) {{
            subtitle = line;
            break;
          }}
        }}
        
        return {{
          name: name || null,
          subtitle: subtitle || null, 
          url: profileLink?.href || null
        }};
      }}).filter(x => x.url && x.name);
    }})()
    """
    results = run_js(code_collect) or []
    # Normalize and structure output to help the planner
    if not isinstance(results, list):
        results = []
    payload = {"count": len(results), "results": results}
    return payload


SearchPeopleTool = FunctionTool(fn=search_people)
