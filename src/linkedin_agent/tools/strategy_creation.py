"""
Strategy Creation Tool - Generate recruitment strategies as part of agentic workflow
"""

from typing import Dict, Any, Optional
from adalflow.core.func_tool import FunctionTool
from .strategy_generator import StrategyGenerator
from ..core.workflow_state import store_strategy
from ..utils.logger import log_info, log_debug, log_error, log_progress


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
    
    log_info(f"🎯 Creating search strategy for: '{query}' in {location}", phase="STRATEGY")
    if job_description:
        log_info(f"📋 Using job description text for enhanced strategy ({len(job_description)} chars)", phase="STRATEGY")
    
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
        
        log_info(f"✅ Strategy created with {len(strategy)} components", phase="STRATEGY")
        log_info(f"📊 Key focus areas: {', '.join(strategy.get('evaluation_criteria', {}).get('technology_priorities', {}).get('must_have', [])[:3])}", phase="STRATEGY")
        
        # Store strategy in global state
        log_progress("Storing strategy in global state", "STRATEGY")
        global_state_result = store_strategy(strategy)
        log_debug(f"💾 {global_state_result.get('message', 'Strategy stored in global state')}", phase="STRATEGY")
        
        # Return lightweight status for agent
        return {
            "success": True,
            "strategy_id": global_state_result.get('strategy_id', 'workflow_generated'),
            "query": query,
            "location": location,
            "message": f"Strategy for {query} in {location} stored in global state"
        }
        
    except Exception as e:
        log_error(f"⚠️ Strategy creation failed: {e}", phase="STRATEGY", exception=e)
        
        # Fallback strategy
        log_progress("Creating fallback strategy", "STRATEGY")
        generator = StrategyGenerator()
        fallback_strategy = generator.create_fallback_strategy(query, location)
        fallback_strategy['original_query'] = query
        fallback_strategy['target_location'] = location
        fallback_strategy['tool_generated'] = True
        fallback_strategy['fallback_used'] = True
        
        log_info(f"✅ Using fallback strategy", phase="STRATEGY")
        
        # Store fallback strategy in global state
        log_progress("Storing fallback strategy in global state", "STRATEGY")
        global_state_result = store_strategy(fallback_strategy)
        log_debug(f"💾 {global_state_result.get('message', 'Fallback strategy stored in global state')}", phase="STRATEGY")
        
        return {
            "success": True,
            "strategy_id": global_state_result.get('strategy_id', 'fallback_strategy'),
            "query": query,
            "location": location,
            "message": f"Fallback strategy for {query} in {location} stored in global state",
            "warning": f"Primary strategy failed: {str(e)}"
        }


# Create the AdalFlow tool
CreateSearchStrategyTool = FunctionTool(fn=create_search_strategy)