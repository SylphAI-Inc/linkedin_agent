"""
Strategy Creation Tool - Generate recruitment strategies as part of agentic workflow
"""

from typing import Dict, Any, Optional
from adalflow.core.func_tool import FunctionTool
from tools.strategy_generator import StrategyGenerator


def create_search_strategy(
    query: str,
    location: str = "Any Location",
    job_description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a comprehensive recruitment strategy for the given role and location
    
    Args:
        query: The job role to search for (e.g., "Senior Software Engineer")
        location: Target location for candidates
        job_description: Optional job description text for enhanced strategy
        
    Returns:
        Comprehensive strategy dict with evaluation criteria and search guidance
    """
    
    print(f"🎯 Creating search strategy for: '{query}' in {location}")
    if job_description:
        print(f"📋 Using job description text for enhanced strategy ({len(job_description)} chars)")
    
    try:
        generator = StrategyGenerator()
        
        # Use strategy generation with job description if provided
        strategy_result = generator.create_search_strategy(query, location, job_description)
        
        # Convert to dict if it's a dataclass
        if hasattr(strategy_result, 'to_dict'):
            strategy = strategy_result.to_dict()
        else:
            strategy = strategy_result
        
        # Add metadata for agent context
        strategy['original_query'] = query
        strategy['target_location'] = location
        strategy['tool_generated'] = True
        
        print(f"✅ Strategy created with {len(strategy)} components")
        print(f"📊 Key focus areas: {', '.join(strategy.get('evaluation_criteria', {}).get('technology_priorities', {}).get('must_have', [])[:3])}")
        
        return {
            "success": True,
            "strategy": strategy,
            "query": query,
            "location": location,
            "message": f"Strategy successfully created for {query} in {location}"
        }
        
    except Exception as e:
        print(f"⚠️ Strategy creation failed: {e}")
        
        # Fallback strategy
        generator = StrategyGenerator()
        fallback_strategy = generator.create_fallback_strategy(query, location)
        fallback_strategy['original_query'] = query
        fallback_strategy['target_location'] = location
        fallback_strategy['tool_generated'] = True
        fallback_strategy['fallback_used'] = True
        
        print(f"✅ Using fallback strategy")
        
        return {
            "success": True,
            "strategy": fallback_strategy,
            "query": query,
            "location": location,
            "message": f"Fallback strategy created for {query} in {location}",
            "warning": f"Primary strategy failed: {str(e)}"
        }


# Create the AdalFlow tool
CreateSearchStrategyTool = FunctionTool(fn=create_search_strategy)