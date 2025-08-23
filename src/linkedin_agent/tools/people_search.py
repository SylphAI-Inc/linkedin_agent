from typing import List, Dict, Any
from urllib.parse import quote_plus
import time

from adalflow.core.func_tool import FunctionTool
from .web_nav import js as run_js, go as nav_go, wait as nav_wait
from .linkedin_selectors import SEARCH_INPUT, PEOPLE_TAB, SEARCH_RESULTS_CARDS
from adalflow.core import Generator
from adalflow.components.model_client import OpenAIClient
from adalflow.components.output_parsers import JsonOutputParser
from ..config import get_model_kwargs

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
_evaluation_generator = None

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

def evaluate_headline_with_strategy(headline: str, strategy: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate candidate headline using strategy - handles both agent and fallback formats"""
    if not headline or not strategy:
        return {"score": 0.0, "worth_extracting": False, "signals": []}
    
    headline_lower = headline.lower()
    score = 0.0
    signals = []
    
    # Handle both strategy formats: agent format and expected format
    if "headline_analysis" in strategy:
        # Expected format from fallback strategy
        target_titles = [title.lower() for title in strategy.get("headline_analysis", {}).get("target_job_titles", [])]
        alternative_titles = [title.lower() for title in strategy.get("headline_analysis", {}).get("alternative_titles", [])]
        seniority_keywords = [kw.lower() for kw in strategy.get("headline_analysis", {}).get("seniority_keywords", [])]
        company_indicators = [comp.lower() for comp in strategy.get("headline_analysis", {}).get("company_indicators", [])]
        tech_signals = [tech.lower() for tech in strategy.get("headline_analysis", {}).get("tech_stack_signals", [])]
        negative_patterns = [pattern.lower() for pattern in strategy.get("search_filtering", {}).get("negative_headline_patterns", [])]
        min_score = strategy.get("search_filtering", {}).get("minimum_headline_score", 3.0)
    else:
        # Agent format - convert to expected format
        target_titles = [title.lower() for title in strategy.get("primary_titles", [])]
        alternative_titles = [title.lower() for title in strategy.get("alternative_titles", [])]
        seniority_keywords = [kw.lower() for kw in strategy.get("seniority_indicators", [])]
        company_indicators = [comp.lower() for comp in strategy.get("target_companies", [])]
        tech_signals = [tech.lower() for tech in strategy.get("key_technologies", [])]
        negative_patterns = [pattern.lower() for pattern in strategy.get("negative_patterns", [])]
        min_score = 2.0  # Default for agent format
    
    # Job title relevance
    if any(title in headline_lower for title in target_titles):
        score += 3.0
        signals.append("exact_title_match")
    elif any(alt in headline_lower for alt in alternative_titles):
        score += 2.0
        signals.append("alternative_title_match")
    
    # Seniority indicators
    if any(keyword in headline_lower for keyword in seniority_keywords):
        score += 1.5
        signals.append("seniority_indicated")
    
    # Company indicators
    if any(indicator in headline_lower for indicator in company_indicators):
        score += 1.0
        signals.append("company_mentioned")
    
    # Tech stack signals
    matching_tech = [tech for tech in tech_signals if tech in headline_lower]
    if matching_tech:
        score += len(matching_tech) * 0.5
        signals.append(f"tech_stack: {matching_tech}")
    
    # Check for negative patterns
    if any(pattern in headline_lower for pattern in negative_patterns):
        score -= 2.0
        signals.append("negative_pattern_detected")
    
    return {
        "score": score,
        "worth_extracting": score >= min_score,
        "signals": signals
    }

def search_people(query: str, location: str = "", limit: int = 10, network_filter: str = "F") -> Dict[str, Any]:
    """Navigate LinkedIn people search and return lightweight result cards (name, subtitle, url).

    Args:
        query: Search keywords
        location: Location filter
        limit: Maximum number of results
        network_filter: Network connection filter:
            "F" = 1st degree connections only
            "S" = 2nd degree connections
            "O" = 3rd+ degree connections
            "" = All connections (default behavior)

    Returns a structured payload to help the agent reason:
      { "count": int, "results": [{ name, subtitle, url }] }
    """
    q = (query + (f" {location}" if location else "")).strip()
    
    # Navigate to LinkedIn people search
    url = f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(q)}"
    nav_go(url)
    # Wait for search results 
    nav_wait(".search-results-container li, .search-no-results", 12)
    
    # Prefer People tab when present (best-effort)
    _js_click_first(PEOPLE_TAB)
    nav_wait(".search-results-container li", 5)
    
    # Apply network connection filter for 1st degree connections
    if network_filter == "F":  # 1st degree connections
        print("[DEBUG] Attempting to apply 1st degree connection filter...")
        
        # First, try URL parameter approach with correct LinkedIn format
        current_url = run_js("window.location.href")
        if "network=" not in current_url:
            # Add network parameter to URL and reload
            new_url = f"{current_url}&network=[%22F%22]"
            nav_go(new_url)
            nav_wait(".search-results-container li, .search-no-results", 10)
        
        # Fallback: Try clicking UI filter elements
        time.sleep(2)  # Wait for page to fully load
        
        filter_applied = run_js("""
        (() => {
            console.log('Attempting to apply 1st degree connection filter...');
            
            // Method 1: Look for connection degree buttons in sidebar
            const connectionButtons = document.querySelectorAll('button, .search-s-facet__button, .search-reusables__filter-trigger');
            for (let btn of connectionButtons) {
                const text = btn.textContent.toLowerCase().trim();
                const ariaLabel = btn.getAttribute('aria-label')?.toLowerCase() || '';
                
                if (text.includes('1st') || text.includes('first') || ariaLabel.includes('1st') || ariaLabel.includes('first')) {
                    console.log('Found 1st degree button:', btn);
                    btn.click();
                    return 'clicked_1st_button';
                }
            }
            
            // Method 2: Look for "All filters" modal approach
            const allFiltersBtn = Array.from(document.querySelectorAll('button')).find(btn => 
                btn.textContent.toLowerCase().includes('filter') || btn.textContent.toLowerCase().includes('show all')
            );
            
            if (allFiltersBtn) {
                console.log('Clicking all filters button');
                allFiltersBtn.click();
                
                // Wait and look for network options in modal
                setTimeout(() => {
                    const networkOptions = document.querySelectorAll('input[type="checkbox"], label');
                    for (let option of networkOptions) {
                        const text = option.textContent?.toLowerCase() || '';
                        const value = option.value?.toLowerCase() || '';
                        
                        if (text.includes('1st') || text.includes('first') || value.includes('f')) {
                            console.log('Found network option:', option);
                            if (option.tagName === 'INPUT') {
                                option.checked = true;
                                option.dispatchEvent(new Event('change'));
                            } else {
                                option.click();
                            }
                            
                            // Apply filters
                            const applyBtn = document.querySelector('button[data-test-id="apply-filters"], button:contains("Apply")');
                            if (applyBtn) applyBtn.click();
                            
                            return 'applied_via_modal';
                        }
                    }
                }, 1000);
                
                return 'opened_modal';
            }
            
            return 'no_filter_found';
        })()
        """)
        
        print(f"[DEBUG] Filter application result: {filter_applied}")
        
        # Wait for results to update after filter
        nav_wait(".search-results-container li", 8)

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
      const containers = Array.from(document.querySelectorAll('.search-results-container li')).slice(0, {limit * 3}); // Get more results for filtering
      
      return containers.map(li => {{
        const profileLink = li.querySelector('a[href*="/in/"]');
        const lines = li.textContent.split('\\n').map(l => l.trim()).filter(l => l && l !== 'Status is offline');
        
        // Find connection degree info
        let connectionDegree = null;
        for (const line of lines) {{
          if (line.includes('1st degree connection') || line.includes('1st-degree connection')) {{
            connectionDegree = '1st';
            break;
          }} else if (line.includes('2nd degree connection') || line.includes('2nd-degree connection')) {{
            connectionDegree = '2nd';
            break;
          }} else if (line.includes('3rd degree connection') || line.includes('3rd+ degree connection')) {{
            connectionDegree = '3rd+';
            break;
          }}
        }}
        
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
          url: profileLink?.href || null,
          connection_degree: connectionDegree
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
