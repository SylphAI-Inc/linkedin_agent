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
class Certification(DataClass):
    """Professional certification entry"""
    name: str = field(metadata={"desc": "Certification name"})
    issuer: Optional[str] = field(
        default=None,
        metadata={"desc": "Organization that issued the certification"}
    )
    issued_on: Optional[str] = field(
        default=None,
        metadata={"desc": "Date when the certification was issued (e.g. 'Mar 2021')"}
    )
    expires_on: Optional[str] = field(
        default=None,
        metadata={"desc": "Expiration date if applicable (e.g. 'Mar 2024' or 'No Expiration')"}
    )
    credential_id: Optional[str] = field(
        default=None,
        metadata={"desc": "Unique ID for the certification"}
    )
    credential_url: Optional[str] = field(
        default=None,
        metadata={"desc": "URL to verify the certification online"}
    )

@dataclass
class Language(DataClass):
    """Language proficiency entry"""
    name: str = field(metadata={"desc": "Language name"})
    proficiency: Optional[str] = field(
        default=None,
        metadata={"desc": "Proficiency level (e.g. 'Native', 'Fluent', 'Professional Working Proficiency')"}
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
    
    certifications: List[Certification] = field(
        default_factory=list,
        metadata={"desc": "List of professional certifications"}
    )
        
    # Skills
    skills: List[Skill] = field(
        default_factory=list,
        metadata={"desc": "List of professional skills with endorsement counts"}
    )
    
    languages: List[Language] = field(
        default_factory=list,
        metadata={"desc": "List of languages known with proficiency levels"}
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
class SearchStrategy(DataClass):
    """Structured search strategy generated by LLM"""
    
    headline_analysis: Dict[str, Any] = field(
        default_factory=dict,
        metadata={"desc": "LLM analysis of effective headline keywords"}
    )
    
    search_filtering: Dict[str, Any] = field(
        default_factory=dict,
        metadata={"desc": "Filters to apply (location, industry, etc.)"}
    )
    
    profile_evaluation_context: Dict[str, Any] = field(
        default_factory=dict,
        metadata={"desc": "Context for evaluating candidate profiles"}
    ) 
    
    evaluation_criteria: Dict[str, Any] = field(
        default_factory=dict,
        metadata={"desc": "Structured criteria for systematic candidate evaluation and strategic bonuses"}
    )
    
    search_terms: Optional[str] = field(
        default=None,
        metadata={"desc": "Optimized search terms to use on LinkedIn"}
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


@dataclass
class CandidateOutreachEvaluation(DataClass):
    """Outreach evaluation results for candidates"""
    candidate_name: str = field(metadata={"desc": "Candidate name"})
    
    overall_outreach_score: float = field(metadata={"desc": "Overall outreach suitability score (0-50)"})
    
    # Individual evaluation components
    technical_fit_score: float = field(
        default=0.0,
        metadata={"desc": "Technical skills alignment score (0-10)"}
    )
    
    experience_relevance_score: float = field(
        default=0.0,
        metadata={"desc": "Experience relevance score (0-10)"}
    )
    
    career_progression_score: float = field(
        default=0.0,
        metadata={"desc": "Career growth trajectory score (0-10)"}
    )
    
    cultural_fit_score: float = field(
        default=0.0,
        metadata={"desc": "Cultural and company fit score (0-10)"}
    )
    
    availability_likelihood_score: float = field(
        default=0.0,
        metadata={"desc": "Likelihood of being open to opportunities (0-10)"}
    )
    
    # Outreach decision
    recommend_outreach: bool = field(
        default=False,
        metadata={"desc": "Whether to recommend outreach to this candidate"}
    )
    
    outreach_priority: str = field(
        default="Low",
        metadata={"desc": "Outreach priority level (High, Medium, Low)"}
    )
    
    # Detailed analysis
    key_strengths: List[str] = field(
        default_factory=list,
        metadata={"desc": "Key strengths that make this candidate attractive"}
    )
    
    potential_concerns: List[str] = field(
        default_factory=list,
        metadata={"desc": "Potential concerns or red flags"}
    )
    
    outreach_angle: str = field(
        default="",
        metadata={"desc": "Recommended approach/angle for outreach message"}
    )
    
    personalized_message: str = field(
        default="",
        metadata={"desc": "Generated personalized outreach message"}
    )
    
    evaluation_reasoning: str = field(
        default="",
        metadata={"desc": "Detailed explanation of the evaluation and outreach recommendation"}
    )