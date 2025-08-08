"""
LinkedIn Profile Data Models using AdalFlow DataClass patterns
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from adalflow.core import DataClass


@dataclass  
class Experience(DataClass):
    """Individual work experience entry"""
    title: str = field(metadata={"desc": "Job title/position"})
    company: str = field(metadata={"desc": "Company name"})
    duration: str = field(metadata={"desc": "Employment duration (e.g. '2 years 3 months')"})
    location: Optional[str] = field(
        default=None, 
        metadata={"desc": "Job location (city, state/country)"}
    )
    description: Optional[str] = field(
        default=None,
        metadata={"desc": "Job description and key accomplishments"}
    )
    start_date: Optional[str] = field(
        default=None,
        metadata={"desc": "Start date (e.g. 'Jan 2022')"}
    )
    end_date: Optional[str] = field(
        default=None, 
        metadata={"desc": "End date or 'Present' if current"}
    )


@dataclass
class Education(DataClass):
    """Educational background entry"""
    institution: str = field(metadata={"desc": "School/university name"})
    degree: Optional[str] = field(
        default=None,
        metadata={"desc": "Degree type and field (e.g. 'Bachelor of Science in Computer Science')"}
    )
    duration: Optional[str] = field(
        default=None,
        metadata={"desc": "Years attended (e.g. '2018 - 2022')"}
    )
    description: Optional[str] = field(
        default=None,
        metadata={"desc": "Activities, honors, relevant coursework"}
    )


@dataclass
class Skill(DataClass):
    """Professional skill with endorsements"""
    name: str = field(metadata={"desc": "Skill name"})
    endorsements: int = field(
        default=0,
        metadata={"desc": "Number of endorsements received"}
    )


@dataclass
class LinkedInProfile(DataClass):
    """Complete LinkedIn profile data structure"""
    # Basic Information
    name: str = field(metadata={"desc": "Full name"})
    headline: str = field(metadata={"desc": "Professional headline/title"})
    location: Optional[str] = field(
        default=None,
        metadata={"desc": "Geographic location"}
    )
    
    # Profile Content
    about: Optional[str] = field(
        default=None,
        metadata={"desc": "Complete About/Summary section"}
    )
    
    # Professional Experience
    experience: List[Experience] = field(
        default_factory=list,
        metadata={"desc": "List of work experience entries"}
    )
    
    # Education
    education: List[Education] = field(
        default_factory=list,
        metadata={"desc": "List of educational background entries"}
    )
    
    # Skills
    skills: List[Skill] = field(
        default_factory=list,
        metadata={"desc": "List of professional skills with endorsement counts"}
    )
    
    # Contact and Social
    linkedin_url: Optional[str] = field(
        default=None,
        metadata={"desc": "LinkedIn profile URL"}
    )
    
    # Extracted metadata
    total_experience_years: Optional[int] = field(
        default=None,
        metadata={"desc": "Estimated total years of professional experience"}
    )
    
    current_company: Optional[str] = field(
        default=None,
        metadata={"desc": "Current employer name"}
    )
    
    current_title: Optional[str] = field(
        default=None,
        metadata={"desc": "Current job title"}
    )
    
    # Industry indicators
    industry_keywords: List[str] = field(
        default_factory=list,
        metadata={"desc": "Key industry-related terms found in profile"}
    )
    
    # Extraction metadata
    extraction_timestamp: Optional[str] = field(
        default=None,
        metadata={"desc": "When this profile was extracted"}
    )
    
    data_completeness_score: float = field(
        default=0.0,
        metadata={"desc": "Score 0-1 indicating how complete the extracted data is"}
    )


@dataclass
class CandidateSearchResult(DataClass):
    """Search result with basic candidate info"""
    name: str = field(metadata={"desc": "Candidate name"})
    headline: str = field(metadata={"desc": "Professional headline"})
    location: Optional[str] = field(
        default=None,
        metadata={"desc": "Location"}
    )
    linkedin_url: Optional[str] = field(
        default=None,
        metadata={"desc": "LinkedIn profile URL"}
    )
    profile_snippet: Optional[str] = field(
        default=None,
        metadata={"desc": "Brief profile preview from search results"}
    )
    search_relevance_score: float = field(
        default=0.0,
        metadata={"desc": "How relevant this candidate is to the search query (0-1)"}
    )


@dataclass
class JobRequirements(DataClass):
    """Job requirements for candidate scoring"""
    job_title: str = field(metadata={"desc": "Target job title"})
    
    required_skills: List[str] = field(
        default_factory=list,
        metadata={"desc": "Must-have skills"}
    )
    
    preferred_skills: List[str] = field(
        default_factory=list,
        metadata={"desc": "Nice-to-have skills"}
    )
    
    min_experience_years: Optional[int] = field(
        default=None,
        metadata={"desc": "Minimum years of experience required"}
    )
    
    max_experience_years: Optional[int] = field(
        default=None,
        metadata={"desc": "Maximum years of experience (for leveling)"}
    )
    
    industry: Optional[str] = field(
        default=None,
        metadata={"desc": "Preferred industry background"}
    )
    
    education_requirements: List[str] = field(
        default_factory=list,
        metadata={"desc": "Education requirements (e.g. 'Bachelor degree', 'Computer Science')"}
    )
    
    location_preferences: List[str] = field(
        default_factory=list,
        metadata={"desc": "Preferred candidate locations"}
    )
    
    company_preferences: List[str] = field(
        default_factory=list,
        metadata={"desc": "Preferred previous companies or company types"}
    )


@dataclass
class CandidateScore(DataClass):
    """Candidate scoring results"""
    candidate_name: str = field(metadata={"desc": "Candidate name"})
    
    overall_score: float = field(metadata={"desc": "Overall match score (0-100)"})
    
    # Individual scoring components
    skills_score: float = field(
        default=0.0,
        metadata={"desc": "Skills match score (0-100)"}
    )
    
    experience_score: float = field(
        default=0.0,
        metadata={"desc": "Experience relevance score (0-100)"}
    )
    
    education_score: float = field(
        default=0.0,
        metadata={"desc": "Education match score (0-100)"}
    )
    
    location_score: float = field(
        default=0.0,
        metadata={"desc": "Location preference score (0-100)"}
    )
    
    company_score: float = field(
        default=0.0,
        metadata={"desc": "Company background score (0-100)"}
    )
    
    # Detailed reasoning
    strengths: List[str] = field(
        default_factory=list,
        metadata={"desc": "List of candidate strengths for this role"}
    )
    
    concerns: List[str] = field(
        default_factory=list,
        metadata={"desc": "List of potential concerns or gaps"}
    )
    
    recommendation: str = field(
        default="",
        metadata={"desc": "AI recommendation (Strong Match, Good Match, Weak Match, No Match)"}
    )
    
    reasoning: str = field(
        default="",
        metadata={"desc": "Detailed explanation of the scoring and recommendation"}
    )