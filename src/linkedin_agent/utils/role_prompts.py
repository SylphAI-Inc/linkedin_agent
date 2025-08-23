"""Simplified LinkedIn agent prompts using AdalFlow's Prompt class"""

from typing import Optional
from adalflow.core.prompt_builder import Prompt

# Agent role description - defines what the agent is
LINKEDIN_AGENT_ROLE = r"""
You are a LinkedIn recruitment agent specialized in finding top candidates.

SEARCH STRATEGY INSTRUCTIONS:
When searching for candidates, automatically apply these strategies based on the role:

For Technical Roles (Engineer, Developer, etc.):
- Look for: Specific programming languages, frameworks, and tools in headlines
- Prioritize: Senior/Lead/Principal/Staff levels for experienced positions
- Score higher: Candidates from known tech companies (Google, Meta, Amazon, etc.)
- Key signals: GitHub, open source contributions, technical certifications

For Product/Management Roles:
- Look for: Product Manager, PM, Product Owner titles
- Prioritize: MBA, strategic thinking, cross-functional leadership
- Score higher: Experience with metrics, KPIs, roadmaps
- Key signals: Previous startup experience, growth metrics

For Data Roles:
- Look for: Data Scientist, ML Engineer, Data Analyst
- Prioritize: Python, R, SQL, machine learning frameworks
- Score higher: PhD, publications, Kaggle achievements
- Key signals: Specific ML/AI technologies mentioned

SCORING GUIDELINES:
During search and evaluation, automatically apply these scoring criteria:
- Exact title match: +3.0 points
- Seniority indicators (Senior/Lead/Principal/Staff): +1.5 points  
- Top-tier companies: +2.0 points
- Relevant tech stack: +0.5 per matching technology
- Complete profile with experience: +1.0 point
- Minimum score threshold: 6.0 for quality candidates

WORKFLOW PHASES:

1. SEARCH: Find candidates on LinkedIn
   - navigate_to_linkedin()
   - smart_candidate_search(query, location, target_candidate_count)
   - Apply scoring guidelines automatically during search
   - Returns candidate count, profiles stored in global state

2. EXTRACT: Get detailed profiles
   - extract_candidate_profiles()
   - Retrieves candidates from global state, stores full profiles

3. EVALUATE: Score candidate quality
   - evaluate_candidates_quality(min_quality_threshold=6.0)
   - Apply comprehensive scoring based on full profile data
   - If quality insufficient, follow fallback recommendations

4. OUTREACH: Generate personalized messages
   - generate_candidate_outreach(position_title, location)
   - Creates messages for quality candidates

Execute all phases sequentially. Data flows through global state automatically.
"""

# User query template - what the user wants
USER_QUERY_TEMPLATE = r"""
Find {{ limit }} high-quality {{ query }} candidates in {{ location }}.
{% if job_description %}

JOB DESCRIPTION CONTEXT:
{{ job_description }}

Use this job description to create a highly targeted search strategy that matches the specific requirements, technologies, and qualifications mentioned above.
{% endif %}
"""

def get_agent_role() -> str:
    """
    Get the LinkedIn agent's role description.
    
    Returns:
        Agent role description string
    """
    return LINKEDIN_AGENT_ROLE

def get_user_query(query: str, location: str, limit: int, job_description: Optional[str] = None) -> str:
    """
    Build the user query for the LinkedIn agent.
    
    Args:
        query: Job title or role to search for
        location: Geographic location for search
        limit: Maximum number of candidates to find
        job_description: Optional job description for enhanced targeting
        
    Returns:
        Formatted user query string
    """
    prompt = Prompt(template=USER_QUERY_TEMPLATE)
    return prompt(query=query, location=location, limit=limit, job_description=job_description)

# Backward compatibility function
def get_linkedin_prompt(query: str, location: str, limit: int, job_description: Optional[str] = None) -> str:
    """
    Get the full prompt (role + query) for backward compatibility.
    
    Args:
        query: Job title or role to search for
        location: Geographic location for search
        limit: Maximum number of candidates to find
        job_description: Optional job description for enhanced targeting
        
    Returns:
        Combined role description and user query
    """
    role = get_agent_role()
    user_query = get_user_query(query, location, limit, job_description)
    return f"{role}\n\nCURRENT TASK:\n{user_query}"