#!/usr/bin/env python3
"""
Simplified LLM-based Quality Assessment System

Core components:
- LLM-powered candidate quality scoring
- Simple dataclasses for quality representation
- Heap-based candidate ranking (kept from original)
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import heapq
import statistics
import json

# AdalFlow imports for LLM generator
from adalflow.core import Generator
from adalflow.components.model_client import OpenAIClient
from adalflow.components.output_parsers.outputs import JsonOutputParserPydanticModel
from pydantic import BaseModel, Field
from ..config import get_model_kwargs
class KeySignals(BaseModel):
    """Key assessment signals and indicators"""
    role_match: bool = Field(description="Whether the candidate's role matches the target role")
    seniority_appropriate: bool = Field(description="Whether the seniority level is appropriate")
    tech_stack_match: float = Field(description="Technology stack alignment score (0.0-1.0)")
    company_tier: str = Field(description="Company tier classification (tier_1, tier_2, tier_3)")


class CandidateAssessment(BaseModel):
    """Comprehensive candidate quality assessment result"""
    overall_score: float = Field(description="Overall candidate quality score (0.0-10.0)")
    technical_score: float = Field(description="Technical skills and expertise score (0.0-10.0)")
    experience_score: float = Field(description="Experience level and career progression score (0.0-10.0)")
    cultural_fit_score: float = Field(description="Likely cultural and team fit score (0.0-10.0)")
    extraction_quality: float = Field(description="Quality of available profile data (0.0-10.0)")
    profile_completeness: float = Field(description="Profile data completeness percentage (0.0-100.0)")
    
    strengths: List[str] = Field(description="List of candidate strengths and positive indicators")
    concerns: List[str] = Field(description="List of concerns or potential issues")
    key_signals: KeySignals = Field(description="Key assessment signals and indicators")
    reasoning: str = Field(description="Detailed explanation of the assessment")


# LLM prompt template for candidate quality assessment
QUALITY_ASSESSMENT_PROMPT = r"""<ROLE>
You are an expert technical recruiter evaluating LinkedIn candidates. Your task is to assess candidate quality based on their profile information and job requirements.
</ROLE>

<CONTEXT>
You are evaluating a candidate for the following position:
Role: {{role_query}}
Job Requirements: {{job_requirements}}

Candidate Information:
- Name: {{candidate_name}}
- Headline: {{candidate_headline}}
- Profile URL: {{candidate_url}}
{% if profile_data %}
- Full Profile Data: {{profile_data}}
{% endif %}
</CONTEXT>

<TASK>
Evaluate this candidate's quality on a scale of 0-10 and provide detailed reasoning.

Consider:
1. Technical Skills Match: How well do their skills align with the role?
2. Experience Level: Is their seniority appropriate for the position?
3. Career Progression: Do they show growth and advancement?
4. Company Background: Have they worked at reputable companies?
5. Role Relevance: How relevant is their experience to this specific role?

Provide scores for:
- overall_score (0-10): Overall candidate quality
- technical_score (0-10): Technical skills and expertise
- experience_score (0-10): Experience level and career progression
- cultural_fit_score (0-10): Likely cultural and team fit
- extraction_quality (0-10): Quality of available profile data
</TASK>

<OUTPUT_FORMAT>
{{output_format_str}}
</OUTPUT_FORMAT>

<EXAMPLES>
For a "Senior Backend Engineer" role:
- High technical_score for candidates with relevant backend technologies
- High experience_score for 5+ years experience with senior titles
- Consider company quality (FAANG = higher scores)
- Look for leadership indicators in senior roles

For a "Product Manager" role:
- Focus on strategic thinking and cross-functional experience
- Value MBA or product-specific experience
- Consider B2B/B2C alignment with role requirements
</EXAMPLES>
"""


@dataclass
class QualityThresholds:
    """Define quality scoring thresholds for different candidate tiers"""
    minimum_acceptable: float = 4.0      # Baseline - worth considering
    target_quality: float = 7.0          # Good candidates we're aiming for
    exceptional_quality: float = 9.0     # Outstanding - auto-include these
    
    # Quality plateau detection
    plateau_window: int = 10             # Look at last N candidates
    plateau_improvement_threshold: float = 0.5  # Must improve by this much


@dataclass  
class SearchBudget:
    """Define search effort constraints and extension logic"""
    initial_page_limit: int = 3          # Start with this many pages
    max_page_limit: int = 8              # Never go beyond this
    max_time_minutes: int = 20           # Total time budget
    max_candidates_evaluated: int = 100  # Evaluation budget
    
    # Extension triggers
    low_quality_threshold: float = 4.0   # Extend if average quality below this
    min_acceptable_candidates: int = 3   # Need at least this many good ones
    min_heap_capacity_pct: float = 50.0  # Minimum heap capacity utilization before extraction
    

# CandidateAssessment Pydantic model is used instead of CandidateQuality dataclass
# They represent the same structure - unified for consistency


class CandidateHeap:
    """Heap-based priority queue for maintaining top N candidates"""
    
    def __init__(self, max_size: int = 20, min_score_threshold: float = 0.0):
        self.max_size = max_size
        self.min_score_threshold = min_score_threshold
        self.heap = []  # Min-heap (lowest scores first)
        self.seen_urls = set()  # Deduplication
        
    def add_candidate(self, candidate_data: Dict[str, Any], quality: CandidateAssessment):
        """Add candidate if quality is good enough, maintaining heap size"""
        url = candidate_data.get('url', '')
        
        # Skip duplicates
        if url in self.seen_urls:
            return False, "duplicate"
        
        # Check absolute minimum threshold first
        if quality.overall_score < self.min_score_threshold:
            return False, "below_minimum_threshold"
            
        # Always add if heap not full
        if len(self.heap) < self.max_size:
            heapq.heappush(self.heap, (quality.overall_score, url, candidate_data, quality))
            self.seen_urls.add(url)
            return True, "added_to_heap"
        
        # If heap full, only add if better than worst candidate
        worst_score = self.heap[0][0]
        if quality.overall_score > worst_score:
            # Remove worst, add new
            old_item = heapq.heappop(self.heap)
            self.seen_urls.discard(old_item[1])  # Remove old URL from seen set
            
            heapq.heappush(self.heap, (quality.overall_score, url, candidate_data, quality))
            self.seen_urls.add(url)
            return True, "replaced_worse_candidate"
        
        return False, "quality_too_low"
    
    def get_top_candidates(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get top candidates sorted by quality (best first)"""
        if not self.heap:
            return []
            
        # Sort heap by score descending (best first)
        sorted_candidates = sorted(self.heap, key=lambda x: x[0], reverse=True)
        
        if limit:
            sorted_candidates = sorted_candidates[:limit]
            
        return [
            {
                **candidate_data,
                "quality_assessment": quality,
                "heap_rank": i + 1
            }
            for i, (score, url, candidate_data, quality) in enumerate(sorted_candidates)
        ]
    
    def get_quality_stats(self) -> Dict[str, float]:
        """Get quality statistics for decision making"""
        if not self.heap:
            return {"count": 0, "average": 0, "min": 0, "max": 0, "median": 0}
            
        scores = [item[0] for item in self.heap]
        return {
            "count": len(scores),
            "average": statistics.mean(scores),
            "min": min(scores),
            "max": max(scores),
            "median": statistics.median(scores)
        }
    
    def needs_more_candidates(self, thresholds: QualityThresholds) -> bool:
        """Determine if we need to continue searching"""
        if len(self.heap) == 0:
            return True
            
        stats = self.get_quality_stats()
        
        # Need more if average quality is low
        if stats["average"] < thresholds.target_quality:
            return True
            
        # Need more if we don't have enough acceptable candidates
        acceptable_count = sum(1 for score, _, _, _ in self.heap 
                             if score >= thresholds.minimum_acceptable)
        
        return acceptable_count < 3  # Need at least 3 acceptable candidates
    
    def get_capacity_utilization(self) -> float:
        """Get heap capacity utilization percentage"""
        if self.max_size == 0:
            return 100.0
        return (len(self.heap) / self.max_size) * 100.0
    
    def remove_candidate(self, url: str) -> bool:
        """Remove a specific candidate from the heap by URL"""
        if url not in self.seen_urls:
            return False
            
        # Find and remove the item with matching URL
        original_heap = self.heap[:]
        self.heap = []
        self.seen_urls.discard(url)
        
        # Rebuild heap without the target URL
        for score, candidate_url, candidate_data, quality in original_heap:
            if candidate_url != url:
                heapq.heappush(self.heap, (score, candidate_url, candidate_data, quality))
        
        return True
    
    def remove_low_quality_candidates(self, min_threshold: float) -> int:
        """Remove all candidates below a quality threshold"""
        removed_count = 0
        original_heap = self.heap[:]
        self.heap = []
        
        # Rebuild heap keeping only candidates above threshold
        for score, url, candidate_data, quality in original_heap:
            if score >= min_threshold:
                heapq.heappush(self.heap, (score, url, candidate_data, quality))
            else:
                self.seen_urls.discard(url)
                removed_count += 1
                
        return removed_count
    
    def should_continue_search_for_capacity(self, min_capacity_pct: float = 50.0) -> bool:
        """Check if we should continue searching to fill heap capacity"""
        utilization = self.get_capacity_utilization()
        return utilization < min_capacity_pct
    
    def is_ready_for_extraction(self, min_avg_threshold: float = 5.0, min_candidates: int = 3, 
                               min_capacity_pct: float = 50.0) -> tuple:
        """Enhanced extraction readiness with capacity utilization check"""
        if len(self.heap) < min_candidates:
            return False, f"insufficient_candidates_{len(self.heap)}"
            
        stats = self.get_quality_stats()
        avg_quality = stats.get('average', 0)
        
        if avg_quality < min_avg_threshold:
            return False, f"low_average_quality_{avg_quality:.1f}"
        
        # NEW: Check heap capacity utilization
        capacity_utilization = self.get_capacity_utilization()
        if capacity_utilization < min_capacity_pct:
            return False, f"low_heap_utilization_{capacity_utilization:.1f}pct"
            
        return True, f"ready_quality_{avg_quality:.1f}_capacity_{capacity_utilization:.1f}pct"


class QualityGenerator:
    """LLM-powered quality assessment generator using AdalFlow"""
    
    def __init__(self):
        self.client = OpenAIClient()
        self.parser = JsonOutputParserPydanticModel(pydantic_model=CandidateAssessment)
        
        # Generator for quality assessment
        self.generator = Generator(
            model_client=self.client,
            model_kwargs=get_model_kwargs(),
            template=QUALITY_ASSESSMENT_PROMPT,
            prompt_kwargs={
                "output_format_str": self.parser.format_instructions()
            },
            output_processors=self.parser
        )
    
    def assess_candidate_quality_llm(self, 
                                   candidate_data: Dict[str, Any], 
                                   role_query: str,
                                   job_requirements: str = "") -> CandidateAssessment:
        """Use LLM to assess candidate quality"""
        
        # Extract candidate information
        name = candidate_data.get('name', 'Unknown')
        headline = candidate_data.get('headline', '')
        url = candidate_data.get('url', '')
        profile_data = candidate_data.get('profile_data', {})
        
        try:
            # Call LLM for quality assessment
            result = self.generator(prompt_kwargs={
                "role_query": role_query,
                "job_requirements": job_requirements,
                "candidate_name": name,
                "candidate_headline": headline,
                "candidate_url": url,
                "profile_data": json.dumps(profile_data) if profile_data else None
            })
            
            if hasattr(result, 'data') and result.data:
                llm_assessment = result.data

                return llm_assessment
            else:
                # Fallback if LLM fails
                return self._create_fallback_quality(candidate_data, role_query)
                
        except Exception as e:
            print(f"LLM quality assessment failed: {e}")
            return self._create_fallback_quality(candidate_data, role_query)
    
    def _create_fallback_quality(self, candidate_data: Dict[str, Any], role_query: str) -> CandidateAssessment:
        """Simple fallback quality assessment when LLM fails"""
        headline = candidate_data.get('headline', '').lower()
        role_lower = role_query.lower()
        
        # Simple keyword matching
        base_score = 5.0
        if any(word in headline for word in role_lower.split()):
            base_score += 2.0
        if any(word in headline for word in ['senior', 'lead', 'principal']):
            base_score += 1.0

        return CandidateAssessment(
            overall_score=min(base_score, 10.0),
            technical_score=base_score * 0.8,
            experience_score=base_score * 0.9,
            cultural_fit_score=5.0,
            strengths=["Profile available"],
            concerns=["LLM assessment unavailable"],
            key_signals=KeySignals(
                role_match=any(word in headline for word in role_lower.split()),
                seniority_appropriate=any(word in headline for word in ['senior', 'lead', 'principal']),
                tech_stack_match=0.5,  # Default middle value for fallback
                company_tier="unknown"
            ),
            extraction_quality=7.0 if candidate_data.get('name') and candidate_data.get('headline') else 3.0,
            profile_completeness=50.0,
            reasoning="Fallback assessment based on headline keywords"
        )



class QualityAnalyzer:
    """Simplified quality analyzer using LLM-based assessment"""
    
    def __init__(self, thresholds: QualityThresholds, budget: SearchBudget):
        self.thresholds = thresholds
        self.budget = budget
        self.quality_history = []  # Track quality over time
        self.quality_generator = QualityGenerator()  # LLM-powered assessment
        
    def assess_candidate_quality(self, candidate_data: Dict[str, Any], 
                                role_query: str = "Software Engineer",
                                job_requirements: str = "") -> CandidateAssessment:
        """LLM-powered quality assessment of a candidate"""
        
        # Use LLM generator for assessment
        return self.quality_generator.assess_candidate_quality_llm(
            candidate_data=candidate_data,
            role_query=role_query,
            job_requirements=job_requirements
        )
    
    def should_extend_search(self, current_stats: Dict[str, float], 
                           pages_searched: int) -> tuple:
        """Decide whether to extend search based on quality"""
        
        # Don't extend if we've hit hard limits
        if pages_searched >= self.budget.max_page_limit:
            return False, "hit_page_limit"
            
        # Extend if overall quality is low
        if current_stats["average"] < self.budget.low_quality_threshold:
            return True, f"low_average_quality_{current_stats['average']:.1f}"
            
        # Extend if we don't have enough acceptable candidates
        if current_stats["count"] < self.budget.min_acceptable_candidates:
            return True, f"insufficient_candidates_{current_stats['count']}"
            
        return False, "quality_sufficient"
    
    def detect_quality_plateau(self, recent_scores: List[float]) -> bool:
        """Detect if quality has plateaued (no improvement)"""
        if len(recent_scores) < self.thresholds.plateau_window:
            return False
            
        recent_window = recent_scores[-self.thresholds.plateau_window:]
        first_half = recent_window[:len(recent_window)//2]
        second_half = recent_window[len(recent_window)//2:]
        
        if not first_half or not second_half:
            return False
            
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        improvement = second_avg - first_avg
        return improvement < self.thresholds.plateau_improvement_threshold
    
    def detect_quality_plateau(self, recent_scores: List[float]) -> bool:
        """Detect if quality has plateaued (no improvement)"""
        if len(recent_scores) < self.thresholds.plateau_window:
            return False
            
        recent_window = recent_scores[-self.thresholds.plateau_window:]
        first_half = recent_window[:len(recent_window)//2]
        second_half = recent_window[len(recent_window)//2:]
        
        if not first_half or not second_half:
            return False
            
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        improvement = second_avg - first_avg
        return improvement < self.thresholds.plateau_improvement_threshold