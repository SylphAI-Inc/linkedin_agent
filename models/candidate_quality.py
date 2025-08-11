"""
Comprehensive Candidate Quality Assessment Models
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from adalflow.core import DataClass
import heapq
from enum import Enum


class SearchStrategy(Enum):
    """Different search strategies based on user requirements"""
    QUALITY_FIRST = "quality_first"  # Find best candidates regardless of time
    QUANTITY_FOCUSED = "quantity_focused"  # Meet target count quickly
    BALANCED = "balanced"  # Balance quality and quantity
    BUDGET_CONSTRAINED = "budget_constrained"  # Minimize search time/cost


class CandidateLevel(Enum):
    """Candidate experience levels"""
    ENTRY = "entry"  # 0-2 years
    MID = "mid"  # 2-5 years  
    SENIOR = "senior"  # 5-10 years
    STAFF = "staff"  # 10-15 years
    PRINCIPAL = "principal"  # 15+ years
    EXECUTIVE = "executive"  # C-level, VP, Director


@dataclass
class TechnicalSkillAssessment(DataClass):
    """Detailed technical skill evaluation"""
    primary_languages: List[str] = field(
        default_factory=list,
        metadata={"desc": "Main programming languages (Python, Java, etc.)"}
    )
    frameworks_libraries: List[str] = field(
        default_factory=list,
        metadata={"desc": "Frameworks and libraries (React, Django, etc.)"}
    )
    cloud_platforms: List[str] = field(
        default_factory=list,
        metadata={"desc": "Cloud experience (AWS, Azure, GCP)"}
    )
    databases: List[str] = field(
        default_factory=list,
        metadata={"desc": "Database technologies (PostgreSQL, MongoDB, etc.)"}
    )
    devops_tools: List[str] = field(
        default_factory=list,
        metadata={"desc": "DevOps and infrastructure tools (Docker, Kubernetes, etc.)"}
    )
    architecture_patterns: List[str] = field(
        default_factory=list,
        metadata={"desc": "Architecture patterns and methodologies"}
    )
    skill_depth_score: float = field(
        default=0.0,
        metadata={"desc": "Technical depth assessment (0-10)"}
    )
    skill_breadth_score: float = field(
        default=0.0,
        metadata={"desc": "Technical breadth assessment (0-10)"}
    )
    technology_recency_score: float = field(
        default=0.0,
        metadata={"desc": "How current their tech stack is (0-10)"}
    )


@dataclass
class CareerProgressionAssessment(DataClass):
    """Career growth and trajectory analysis"""
    current_level: str = field(
        default="",
        metadata={"desc": "Current career level (entry, mid, senior, staff, principal, executive)"}
    )
    years_experience: float = field(
        default=0.0,
        metadata={"desc": "Total years of professional experience"}
    )
    progression_velocity: float = field(
        default=0.0,
        metadata={"desc": "Rate of career advancement (promotions/year)"}
    )
    leadership_experience: bool = field(
        default=False,
        metadata={"desc": "Has leadership or management experience"}
    )
    team_size_managed: int = field(
        default=0,
        metadata={"desc": "Largest team size managed"}
    )
    promotion_history: List[str] = field(
        default_factory=list,
        metadata={"desc": "List of promotions and role changes"}
    )
    job_stability_score: float = field(
        default=0.0,
        metadata={"desc": "Job tenure stability assessment (0-10)"}
    )
    growth_trajectory_score: float = field(
        default=0.0,
        metadata={"desc": "Overall career growth assessment (0-10)"}
    )


@dataclass
class ProjectImpactAssessment(DataClass):
    """Assessment of project complexity and business impact"""
    scale_indicators: List[str] = field(
        default_factory=list,
        metadata={"desc": "Indicators of large-scale work (millions of users, etc.)"}
    )
    complexity_markers: List[str] = field(
        default_factory=list,
        metadata={"desc": "Technical complexity indicators (distributed systems, etc.)"}
    )
    business_impact_mentions: List[str] = field(
        default_factory=list,
        metadata={"desc": "Mentions of business metrics, revenue impact, etc."}
    )
    innovation_indicators: List[str] = field(
        default_factory=list,
        metadata={"desc": "Signs of innovation (patents, open source, publications)"}
    )
    project_scale_score: float = field(
        default=0.0,
        metadata={"desc": "Scale of projects worked on (0-10)"}
    )
    technical_complexity_score: float = field(
        default=0.0,
        metadata={"desc": "Technical complexity of work (0-10)"}
    )
    business_impact_score: float = field(
        default=0.0,
        metadata={"desc": "Business impact potential (0-10)"}
    )


@dataclass
class CulturalFitAssessment(DataClass):
    """Cultural and soft skills assessment"""
    communication_quality: float = field(
        default=0.0,
        metadata={"desc": "Quality of written communication in profile (0-10)"}
    )
    collaboration_indicators: List[str] = field(
        default_factory=list,
        metadata={"desc": "Signs of teamwork and collaboration"}
    )
    learning_mindset: List[str] = field(
        default_factory=list,
        metadata={"desc": "Evidence of continuous learning"}
    )
    company_culture_alignment: float = field(
        default=0.0,
        metadata={"desc": "Alignment with company culture/values (0-10)"}
    )
    remote_work_experience: bool = field(
        default=False,
        metadata={"desc": "Has remote work experience"}
    )
    startup_experience: bool = field(
        default=False,
        metadata={"desc": "Has startup or fast-paced environment experience"}
    )
    enterprise_experience: bool = field(
        default=False,
        metadata={"desc": "Has enterprise/large company experience"}
    )


@dataclass
class AvailabilityIndicators(DataClass):
    """Signals that candidate might be open to opportunities"""
    recent_job_change: bool = field(
        default=False,
        metadata={"desc": "Changed jobs recently (may indicate openness)"}
    )
    profile_activity_level: float = field(
        default=0.0,
        metadata={"desc": "LinkedIn activity level (0-10)"}
    )
    open_to_work_signals: List[str] = field(
        default_factory=list,
        metadata={"desc": "Direct or indirect signals of job seeking"}
    )
    network_expansion: bool = field(
        default=False,
        metadata={"desc": "Recently expanding professional network"}
    )
    skill_development: List[str] = field(
        default_factory=list,
        metadata={"desc": "Recent certifications or skill updates"}
    )
    availability_likelihood: float = field(
        default=0.0,
        metadata={"desc": "Likelihood they're open to opportunities (0-10)"}
    )


@dataclass
class MarketValueAssessment(DataClass):
    """Assessment of candidate's market value and competitiveness"""
    industry_demand_score: float = field(
        default=0.0,
        metadata={"desc": "Demand for their skill set in market (0-10)"}
    )
    rarity_score: float = field(
        default=0.0,
        metadata={"desc": "How rare/unique their skill combination is (0-10)"}
    )
    competition_level: float = field(
        default=0.0,
        metadata={"desc": "How competitive this candidate will be (0-10)"}
    )
    salary_expectation_range: Tuple[int, int] = field(
        default=(0, 0),
        metadata={"desc": "Estimated salary range based on profile"}
    )
    negotiation_leverage: float = field(
        default=0.0,
        metadata={"desc": "Their negotiation leverage in market (0-10)"}
    )


@dataclass
class ComprehensiveCandidateQuality(DataClass):
    """Complete candidate quality assessment"""
    candidate_name: str = field(metadata={"desc": "Candidate's full name"})
    candidate_url: str = field(metadata={"desc": "LinkedIn profile URL"})
    evaluation_timestamp: str = field(metadata={"desc": "When evaluation was performed"})
    
    # Technical Assessment
    technical_skills: TechnicalSkillAssessment = field(
        default_factory=TechnicalSkillAssessment,
        metadata={"desc": "Technical skills evaluation"}
    )
    
    # Career Assessment  
    career_progression: CareerProgressionAssessment = field(
        default_factory=CareerProgressionAssessment,
        metadata={"desc": "Career growth and trajectory"}
    )
    
    # Project Impact
    project_impact: ProjectImpactAssessment = field(
        default_factory=ProjectImpactAssessment,
        metadata={"desc": "Project scale and impact assessment"}
    )
    
    # Cultural Fit
    cultural_fit: CulturalFitAssessment = field(
        default_factory=CulturalFitAssessment,
        metadata={"desc": "Cultural and soft skills assessment"}
    )
    
    # Availability
    availability: AvailabilityIndicators = field(
        default_factory=AvailabilityIndicators,
        metadata={"desc": "Availability and interest indicators"}
    )
    
    # Market Value
    market_value: MarketValueAssessment = field(
        default_factory=MarketValueAssessment,
        metadata={"desc": "Market value and competitiveness"}
    )
    
    # Overall Scores
    overall_quality_score: float = field(
        default=0.0,
        metadata={"desc": "Overall candidate quality (0-100)"}
    )
    role_fit_score: float = field(
        default=0.0,
        metadata={"desc": "Fit for specific role (0-100)"}
    )
    hire_recommendation: str = field(
        default="",
        metadata={"desc": "Strong Hire, Hire, Maybe, No Hire"}
    )
    priority_level: str = field(
        default="",
        metadata={"desc": "High, Medium, Low priority for outreach"}
    )
    
    # Key Strengths and Concerns
    key_strengths: List[str] = field(
        default_factory=list,
        metadata={"desc": "Top 3-5 strengths for this candidate"}
    )
    key_concerns: List[str] = field(
        default_factory=list,
        metadata={"desc": "Top concerns or gaps identified"}
    )
    
    # Decision Reasoning
    quality_reasoning: str = field(
        default="",
        metadata={"desc": "Detailed reasoning for quality assessment"}
    )


@dataclass
class CandidateHeapEntry:
    """Entry for the candidate priority heap"""
    quality_score: float
    candidate_id: str
    candidate_data: Dict[str, Any]
    evaluation: ComprehensiveCandidateQuality
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __lt__(self, other):
        # For min-heap, we want higher quality scores to be "smaller"
        # so they bubble to the top
        return self.quality_score > other.quality_score


class AdaptiveCandidatePool:
    """Efficient candidate pool using heap for quality-based management"""
    
    def __init__(self, target_size: int = 10, quality_threshold: float = 70.0):
        self.target_size = target_size
        self.quality_threshold = quality_threshold
        self.candidates_heap: List[CandidateHeapEntry] = []
        self.candidate_urls: set = set()  # Track URLs to avoid duplicates
        self.total_evaluated = 0
        self.quality_stats = {
            "min_score": float('inf'),
            "max_score": 0.0,
            "avg_score": 0.0
        }
    
    def add_candidate(self, 
                      candidate_data: Dict[str, Any], 
                      evaluation: ComprehensiveCandidateQuality) -> bool:
        """
        Add candidate to pool if they meet quality standards
        
        Returns:
            bool: True if candidate was added, False if rejected
        """
        url = candidate_data.get('url', '')
        
        # Skip duplicates
        if url in self.candidate_urls:
            return False
        
        self.total_evaluated += 1
        quality_score = evaluation.overall_quality_score
        
        # Update stats
        self.quality_stats["min_score"] = min(self.quality_stats["min_score"], quality_score)
        self.quality_stats["max_score"] = max(self.quality_stats["max_score"], quality_score)
        
        # Check if candidate meets minimum quality threshold
        if quality_score < self.quality_threshold:
            return False
        
        entry = CandidateHeapEntry(
            quality_score=quality_score,
            candidate_id=url,
            candidate_data=candidate_data,
            evaluation=evaluation
        )
        
        # If we have space, just add
        if len(self.candidates_heap) < self.target_size:
            heapq.heappush(self.candidates_heap, entry)
            self.candidate_urls.add(url)
            return True
        
        # If this candidate is better than our worst candidate
        if quality_score > self.candidates_heap[0].quality_score:
            # Remove worst candidate
            worst = heapq.heappop(self.candidates_heap)
            self.candidate_urls.remove(worst.candidate_id)
            
            # Add new candidate
            heapq.heappush(self.candidates_heap, entry)
            self.candidate_urls.add(url)
            return True
        
        return False
    
    def get_top_candidates(self, count: Optional[int] = None) -> List[CandidateHeapEntry]:
        """Get top N candidates sorted by quality"""
        if count is None:
            count = len(self.candidates_heap)
        
        # Convert heap to sorted list (highest quality first)
        sorted_candidates = sorted(self.candidates_heap, key=lambda x: x.quality_score, reverse=True)
        return sorted_candidates[:count]
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get statistics about the candidate pool"""
        if not self.candidates_heap:
            return {
                "pool_size": 0,
                "total_evaluated": self.total_evaluated,
                "acceptance_rate": 0.0,
                "quality_range": (0, 0),
                "avg_quality": 0.0
            }
        
        qualities = [c.quality_score for c in self.candidates_heap]
        return {
            "pool_size": len(self.candidates_heap),
            "total_evaluated": self.total_evaluated,
            "acceptance_rate": len(self.candidates_heap) / self.total_evaluated if self.total_evaluated > 0 else 0,
            "quality_range": (min(qualities), max(qualities)),
            "avg_quality": sum(qualities) / len(qualities),
            "quality_threshold": self.quality_threshold
        }
    
    def should_continue_search(self, pages_searched: int, max_pages: int) -> bool:
        """
        Determine if we should continue searching based on pool quality
        
        Args:
            pages_searched: Number of pages already searched
            max_pages: Maximum pages user requested
            
        Returns:
            bool: True if should continue searching
        """
        # Always respect user's maximum
        if pages_searched >= max_pages:
            return False
        
        # If we haven't filled the target size, keep searching
        if len(self.candidates_heap) < self.target_size:
            return True
        
        # If we're finding high-quality candidates, consider continuing
        if len(self.candidates_heap) > 0:
            avg_quality = sum(c.quality_score for c in self.candidates_heap) / len(self.candidates_heap)
            
            # If average quality is very high, we might want to continue
            # to see if we can find even better candidates
            if avg_quality > 85.0 and pages_searched < max_pages * 0.8:
                return True
        
        return False
    
    def recommend_search_extension(self) -> Optional[Dict[str, Any]]:
        """
        Recommend whether to extend search beyond user's limit
        
        Returns:
            Dict with extension recommendation or None
        """
        if len(self.candidates_heap) == 0:
            return None
        
        stats = self.get_pool_stats()
        avg_quality = stats["avg_quality"]
        acceptance_rate = stats["acceptance_rate"]
        
        # High quality + high acceptance rate = recommend extension
        if avg_quality > 80.0 and acceptance_rate > 0.3:
            return {
                "recommend": True,
                "reason": f"High quality candidates found (avg: {avg_quality:.1f}) with good acceptance rate ({acceptance_rate:.1%})",
                "suggested_additional_pages": min(3, max(1, int(self.target_size * 0.5))),
                "expected_additional_candidates": int(acceptance_rate * 10)  # Rough estimate
            }
        
        return {
            "recommend": False,
            "reason": f"Current pool quality ({avg_quality:.1f}) and acceptance rate ({acceptance_rate:.1%}) don't justify extension"
        }
