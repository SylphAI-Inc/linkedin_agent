#!/usr/bin/env python3
"""
Global Workflow State Manager - Centralized state for LinkedIn recruitment workflow

This module provides a global state system that allows the agent to coordinate 
workflow phases without passing large data structures through function parameters.

Key Benefits:
- Agent context stays lightweight (just status messages)
- No parameter size limits affecting AdalFlow performance  
- Natural data persistence across workflow phases
- Scalable to 100+ candidates without agent slowdown
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json


class WorkflowState:
    """Global state manager for LinkedIn recruitment workflow"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all workflow state"""
        self._strategy: Optional[Dict[str, Any]] = None
        self._search_results: List[Dict[str, Any]] = []
        self._extraction_results: List[Dict[str, Any]] = []
        self._evaluation_results: List[Dict[str, Any]] = []
        self._outreach_results: List[Dict[str, Any]] = []
        
        # Workflow metadata
        self._workflow_id: str = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._phase: str = "initialized"
        self._start_time: datetime = datetime.now()
        self._phase_history: List[Dict[str, Any]] = []
        
        # Statistics
        self._stats = {
            "candidates_searched": 0,
            "candidates_extracted": 0, 
            "candidates_evaluated": 0,
            "candidates_outreach": 0,
            "quality_threshold": 6.0,
            "target_count": 5
        }
    
    # Strategy Management
    def set_strategy(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Store AI-generated search strategy"""
        self._strategy = strategy
        self._update_phase("strategy_created")
        return {
            "success": True,
            "message": "Strategy stored in global state",
            "strategy_id": self._workflow_id
        }
    
    def get_strategy(self) -> Optional[Dict[str, Any]]:
        """Get stored strategy"""
        # Debug logging to track strategy retrieval
        from ..utils.logger import log_debug
        log_debug(f"get_strategy called, strategy exists: {self._strategy is not None}", phase="WORKFLOW_STATE")
        if self._strategy:
            log_debug(f"Strategy query: {self._strategy.get('original_query', 'Unknown')}", phase="WORKFLOW_STATE")
        return self._strategy
    
    # Search Results Management  
    def set_search_results(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store search results"""
        self._search_results = candidates
        self._stats["candidates_searched"] = len(candidates)
        self._update_phase("search_completed")
        return {
            "success": True,
            "candidates_found": len(candidates),
            "message": f"Stored {len(candidates)} search results in global state"
        }
    
    def get_search_results(self) -> List[Dict[str, Any]]:
        """Get stored search results for extraction"""
        return self._search_results
    
    # Extraction Results Management
    def set_extraction_results(self, extracted_profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store extraction results"""
        from ..utils.logger import log_debug
        log_debug(f"set_extraction_results called with {len(extracted_profiles)} profiles", phase="WORKFLOW_STATE")
        log_debug(f"Global state instance ID: {id(self)}", phase="WORKFLOW_STATE")
        self._extraction_results = extracted_profiles
        self._stats["candidates_extracted"] = len(extracted_profiles)
        self._update_phase("extraction_completed")
        log_debug(f"Successfully stored {len(self._extraction_results)} profiles in global state", phase="WORKFLOW_STATE")
        return {
            "success": True,
            "extracted_count": len(extracted_profiles),
            "failed_count": self._stats["candidates_searched"] - len(extracted_profiles),
            "success_rate": (len(extracted_profiles) / max(self._stats["candidates_searched"], 1)) * 100,
            "message": f"Stored {len(extracted_profiles)} extraction results in global state"
        }
    
    def get_extraction_results(self) -> List[Dict[str, Any]]:
        """Get stored extraction results for evaluation"""
        # Debug logging to track the issue
        from ..utils.logger import log_debug
        log_debug(f"get_extraction_results called, found {len(self._extraction_results)} profiles", phase="WORKFLOW_STATE")
        log_debug(f"Global state instance ID: {id(self)}", phase="WORKFLOW_STATE")
        if self._extraction_results:
            log_debug(f"First profile keys: {list(self._extraction_results[0].keys())}", phase="WORKFLOW_STATE")
        return self._extraction_results
    
    # Evaluation Results Management
    def set_evaluation_results(self, evaluation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store evaluation results"""
        evaluated_candidates = evaluation_data.get("all_evaluated_candidates", [])
        quality_candidates = evaluation_data.get("quality_candidates", [])
        
        self._evaluation_results = evaluated_candidates
        self._stats["candidates_evaluated"] = len(evaluated_candidates)
        self._stats["quality_threshold"] = evaluation_data.get("quality_stats", {}).get("threshold_used", 6.0)
        self._update_phase("evaluation_completed")
        
        return {
            "success": True,
            "candidates_evaluated": len(evaluated_candidates),
            "quality_candidates": len(quality_candidates),
            "quality_sufficient": evaluation_data.get("quality_sufficient", False),
            "average_score": evaluation_data.get("quality_stats", {}).get("average_score", 0.0),
            "message": f"Stored {len(evaluated_candidates)} evaluation results in global state"
        }
    
    def get_evaluation_results(self) -> List[Dict[str, Any]]:
        """Get stored evaluation results for outreach"""
        return self._evaluation_results
    
    def get_quality_candidates(self, min_threshold: float = None) -> List[Dict[str, Any]]:
        """Get quality candidates above threshold"""
        if min_threshold is None:
            min_threshold = self._stats["quality_threshold"]
        
        return [
            candidate for candidate in self._evaluation_results
            if candidate.get("overall_score", 0.0) >= min_threshold
        ]
    
    # Outreach Results Management
    def set_outreach_results(self, outreach_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store outreach results"""
        outreach_messages = outreach_data.get("messages", [])
        self._outreach_results = outreach_messages
        self._stats["candidates_outreach"] = len(outreach_messages)
        self._update_phase("outreach_completed")
        
        return {
            "success": True,
            "outreach_generated": len(outreach_messages),
            "recommended_count": len([m for m in outreach_messages if m.get("recommend_outreach", False)]),
            "message": f"Stored {len(outreach_messages)} outreach results in global state"
        }
    
    def get_outreach_results(self) -> List[Dict[str, Any]]:
        """Get stored outreach results"""
        return self._outreach_results
    
    # Complete Workflow Data for Final Results
    def get_complete_workflow_data(self) -> Dict[str, Any]:
        """Get all workflow data for final result compilation"""
        return {
            "workflow_id": self._workflow_id,
            "strategy": self._strategy,
            "search_results": self._search_results,
            "extraction_results": self._extraction_results,
            "evaluation_results": self._evaluation_results,
            "outreach_results": self._outreach_results,
            "stats": self._stats,
            "phase_history": self._phase_history,
            "duration_seconds": (datetime.now() - self._start_time).total_seconds()
        }
    
    # Workflow Status and Monitoring
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status (lightweight for agent)"""
        return {
            "workflow_id": self._workflow_id,
            "current_phase": self._phase,
            "candidates_found": self._stats["candidates_searched"],
            "candidates_extracted": self._stats["candidates_extracted"],
            "candidates_evaluated": self._stats["candidates_evaluated"],
            "candidates_outreach": self._stats["candidates_outreach"],
            "duration_seconds": (datetime.now() - self._start_time).total_seconds(),
            "ready_for_next_phase": self._is_ready_for_next_phase()
        }
    
    def _update_phase(self, new_phase: str):
        """Update current phase and add to history"""
        old_phase = self._phase
        self._phase = new_phase
        self._phase_history.append({
            "phase": new_phase,
            "timestamp": datetime.now().isoformat(),
            "duration_from_start": (datetime.now() - self._start_time).total_seconds()
        })
        from ..utils.logger import log_info
        log_info(f"Workflow phase: {old_phase} → {new_phase}", phase="WORKFLOW_STATE")
    
    def _is_ready_for_next_phase(self) -> bool:
        """Check if workflow is ready for next phase"""
        phase_requirements = {
            "initialized": len(self._search_results) > 0,
            "strategy_created": len(self._search_results) > 0,
            "search_completed": len(self._extraction_results) > 0,
            "extraction_completed": len(self._evaluation_results) > 0,
            "evaluation_completed": len(self._outreach_results) > 0,
            "outreach_completed": True
        }
        return phase_requirements.get(self._phase, False)


# Global workflow state instance
_workflow_state = WorkflowState()


# Public API Functions
def get_workflow_state() -> WorkflowState:
    """Get the global workflow state instance"""
    return _workflow_state


def reset_workflow() -> Dict[str, Any]:
    """Reset workflow state for new recruitment session"""
    global _workflow_state
    _workflow_state.reset()
    return {
        "success": True,
        "message": "Workflow state reset",
        "workflow_id": _workflow_state._workflow_id
    }


def get_workflow_summary() -> Dict[str, Any]:
    """Get lightweight workflow summary for agent"""
    return _workflow_state.get_workflow_status()


# Phase-specific helper functions
def store_strategy(strategy: Dict[str, Any]) -> Dict[str, Any]:
    """Store strategy and return lightweight response"""
    return _workflow_state.set_strategy(strategy)


def store_search_results(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Store search results and return lightweight response"""
    return _workflow_state.set_search_results(candidates)


def store_extraction_results(extraction_data: Dict[str, Any]) -> Dict[str, Any]:
    """Store extraction results and return lightweight response"""
    extracted_profiles = extraction_data.get("results", [])
    return _workflow_state.set_extraction_results(extracted_profiles)


def store_evaluation_results(evaluation_data: Dict[str, Any]) -> Dict[str, Any]:
    """Store evaluation results and return lightweight response"""
    return _workflow_state.set_evaluation_results(evaluation_data)


def store_outreach_results(outreach_data: Dict[str, Any]) -> Dict[str, Any]:
    """Store outreach results and return lightweight response"""
    return _workflow_state.set_outreach_results(outreach_data)


# # Data access functions (for functions that need the actual data)
# def get_strategy_for_search() -> Optional[Dict[str, Any]]:
#     """Get strategy for search function"""
#     return _workflow_state.get_strategy()


def get_candidates_for_extraction() -> List[Dict[str, Any]]:
    """Get search results for extraction function"""
    return _workflow_state.get_search_results()


def get_profiles_for_evaluation() -> List[Dict[str, Any]]:
    """Get extraction results for evaluation function"""
    return _workflow_state.get_extraction_results()


def get_candidates_for_outreach() -> List[Dict[str, Any]]:
    """Get quality candidates for outreach function"""
    return _workflow_state.get_quality_candidates()


def get_complete_workflow_data() -> Dict[str, Any]:
    """Get all workflow data for final result compilation"""
    return _workflow_state.get_complete_workflow_data()