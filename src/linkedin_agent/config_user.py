#!/usr/bin/env python3
"""
User-Friendly Configuration System for LinkedIn Recruitment Agent

This file contains all the key parameters users typically want to adjust.
Edit these values to customize the agent's behavior.
"""

from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class SearchConfig:
    """Search behavior configuration"""
    
    # Quality Thresholds
    min_search_score: float = 7.0          # Minimum score for candidates during search
    min_evaluation_threshold: float = 6.0  # Minimum score for final evaluation
    target_quality_candidates: int = 5     # How many quality candidates we want
    
    # Search Scope  
    max_pages_per_search: int = 3          # How many LinkedIn pages to search
    max_candidates_per_page: int = 10      # LinkedIn typically shows 10 per page
    quality_mode: str = "adaptive"         # "adaptive", "quality_first", "fast"
    
    # Search Strategy
    extend_search_when_insufficient: bool = True  # Try more pages if quality low
    use_heap_backups: bool = True                 # Use backup candidates from heap
    fallback_to_lower_threshold: bool = True     # Lower threshold if needed


@dataclass 
class ExtractionConfig:
    """Profile extraction configuration"""
    
    # Timing Controls
    delay_between_extractions: float = 1.0    # Seconds between profile extractions
    extraction_timeout: float = 30.0          # Max seconds per profile extraction
    
    # Quality Controls
    validate_extraction_quality: bool = True  # Check if extraction worked well
    min_profile_completeness: float = 0.6     # Minimum profile data completeness
    
    # Behavior
    skip_private_profiles: bool = True        # Skip profiles we can't access
    retry_failed_extractions: int = 1        # How many times to retry failures


@dataclass
class EvaluationConfig:
    """Candidate evaluation configuration"""
    
    # Scoring Weights (these add up to impact final scores)
    experience_weight: float = 0.3           # How much experience matters
    education_weight: float = 0.2            # How much education matters  
    skills_weight: float = 0.2               # How much skills matter
    profile_completeness_weight: float = 0.1 # How much complete profiles matter
    strategic_alignment_weight: float = 0.2  # How much strategy matching matters
    
    # Strategic Bonuses (these are added as bonuses)
    tier1_company_bonus: float = 2.0         # Bonus for Google, Meta, etc.
    seniority_bonus: float = 2.0             # Bonus for senior/lead/principal
    tech_stack_bonus: float = 1.0            # Bonus for matching tech skills
    
    # Quality Standards
    excellent_score_threshold: float = 9.0   # What's considered excellent
    good_score_threshold: float = 7.0        # What's considered good
    acceptable_score_threshold: float = 5.0  # What's considered acceptable


@dataclass
class WorkflowConfig:
    """Overall workflow behavior"""
    
    # Phase Transition Rules
    auto_proceed_to_extraction: bool = True           # Go to extraction when search done
    auto_proceed_to_evaluation: bool = True          # Go to evaluation when extraction done
    auto_proceed_to_outreach: bool = True            # Go to outreach when evaluation done
    
    # Fallback Behavior
    max_fallback_attempts: int = 2                   # How many fallbacks to try
    prefer_heap_backups_over_new_search: bool = True # Try heap before new search
    
    # Quality Requirements
    min_candidates_for_outreach: int = 3             # Need this many for outreach
    require_quality_sufficient: bool = False         # Force quality requirements
    
    # Performance
    enable_real_time_logging: bool = True            # Show detailed progress
    save_intermediate_results: bool = True          # Save results after each phase


@dataclass  
class UserConfig:
    """Complete user configuration - edit these values!"""
    
    search: SearchConfig = field(default_factory=SearchConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)  
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    
    @classmethod
    def load_from_env(cls) -> 'UserConfig':
        """Load configuration with environment variable overrides"""
        config = cls()
        
        # Allow environment overrides for key parameters
        if os.getenv("MIN_SEARCH_SCORE"):
            config.search.min_search_score = float(os.getenv("MIN_SEARCH_SCORE"))
        if os.getenv("MIN_EVALUATION_THRESHOLD"):
            config.search.min_evaluation_threshold = float(os.getenv("MIN_EVALUATION_THRESHOLD"))
        if os.getenv("TARGET_QUALITY_CANDIDATES"):
            config.search.target_quality_candidates = int(os.getenv("TARGET_QUALITY_CANDIDATES"))
        if os.getenv("MAX_PAGES_PER_SEARCH"):
            config.search.max_pages_per_search = int(os.getenv("MAX_PAGES_PER_SEARCH"))
        if os.getenv("EXTRACTION_DELAY"):
            config.extraction.delay_between_extractions = float(os.getenv("EXTRACTION_DELAY"))
            
        return config


# Global configuration instance - users can modify this
USER_CONFIG = UserConfig.load_from_env()


# Convenience functions for easy access
def get_search_config() -> SearchConfig:
    """Get current search configuration"""
    return USER_CONFIG.search


def get_extraction_config() -> ExtractionConfig:
    """Get current extraction configuration""" 
    return USER_CONFIG.extraction


def get_evaluation_config() -> EvaluationConfig:
    """Get current evaluation configuration"""
    return USER_CONFIG.evaluation


def get_workflow_config() -> WorkflowConfig:
    """Get current workflow configuration"""
    return USER_CONFIG.workflow


# Easy configuration examples for users
def configure_for_high_quality():
    """Configure for high-quality candidates (fewer but better)"""
    USER_CONFIG.search.min_search_score = 8.0
    USER_CONFIG.search.min_evaluation_threshold = 7.5
    USER_CONFIG.search.target_quality_candidates = 3
    USER_CONFIG.search.quality_mode = "quality_first"
    USER_CONFIG.evaluation.excellent_score_threshold = 9.5


def configure_for_volume():
    """Configure for more candidates (quantity over quality)"""
    USER_CONFIG.search.min_search_score = 6.0
    USER_CONFIG.search.min_evaluation_threshold = 5.0
    USER_CONFIG.search.target_quality_candidates = 10
    USER_CONFIG.search.max_pages_per_search = 5
    USER_CONFIG.search.quality_mode = "fast"


def configure_for_conservative():
    """Configure for careful, thorough search"""
    USER_CONFIG.extraction.delay_between_extractions = 2.0
    USER_CONFIG.extraction.retry_failed_extractions = 2
    USER_CONFIG.workflow.max_fallback_attempts = 3
    USER_CONFIG.search.extend_search_when_insufficient = True
    USER_CONFIG.search.fallback_to_lower_threshold = False


if __name__ == "__main__":
    print("📊 Current LinkedIn Agent Configuration:")
    print(f"   Search Score Threshold: {USER_CONFIG.search.min_search_score}")
    print(f"   Evaluation Threshold: {USER_CONFIG.search.min_evaluation_threshold}")
    print(f"   Target Quality Candidates: {USER_CONFIG.search.target_quality_candidates}")
    print(f"   Max Pages Per Search: {USER_CONFIG.search.max_pages_per_search}")
    print(f"   Quality Mode: {USER_CONFIG.search.quality_mode}")
    print(f"   Extraction Delay: {USER_CONFIG.extraction.delay_between_extractions}s")
    print(f"   Auto Proceed to Extraction: {USER_CONFIG.workflow.auto_proceed_to_extraction}")
    print("\n💡 To customize, edit config_user.py or use environment variables!")