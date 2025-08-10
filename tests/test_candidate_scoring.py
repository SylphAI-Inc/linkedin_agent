#!/usr/bin/env python3
"""
Test the new AI-powered candidate scoring system
"""
import sys
import os
import json
from pathlib import Path

# Ensure repo root on path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Set environment for testing
os.environ["HEADLESS_MODE"] = "true"

from config import load_env
from models.linkedin_profile import LinkedInProfile, JobRequirements
from tools.candidate_scorer import CandidateScorer
from tools.profile_extractor import ProfileExtractor

# Load environment
load_env()


def create_sample_job_requirements():
    """Create sample job requirements for testing"""
    return JobRequirements(
        job_title="Senior Product Manager",
        required_skills=[
            "Product Management",
            "Product Strategy", 
            "User Research",
            "Data Analysis",
            "Cross-functional Leadership"
        ],
        preferred_skills=[
            "A/B Testing",
            "SQL", 
            "Agile/Scrum",
            "Technical Background",
            "B2B SaaS Experience"
        ],
        min_experience_years=5,
        max_experience_years=10,
        industry="Technology",
        education_requirements=["Bachelor's degree"],
        location_preferences=["San Francisco Bay Area", "New York", "Remote"],
        company_preferences=["Tech companies", "High-growth startups", "Fortune 500"]
    )


def create_sample_candidate_profiles():
    """Create sample candidate profiles for testing"""
    
    # Strong candidate
    strong_candidate = LinkedInProfile(
        name="Sarah Chen",
        headline="Senior Product Manager at Stripe | Fintech & Growth Expert",
        location="San Francisco, California",
        about="Experienced Product Manager with 7+ years building fintech products that serve millions of users. Led cross-functional teams to launch payment features that increased revenue by 40%. Passionate about user research and data-driven decision making.",
        experience=[
            {
                "title": "Senior Product Manager", 
                "company": "Stripe",
                "duration": "2 years 3 months",
                "location": "San Francisco, CA",
                "description": "Led product strategy for merchant payments. Launched 3 major features that increased GMV by 25%. Collaborated with engineering, design, and data science teams."
            },
            {
                "title": "Product Manager",
                "company": "Square", 
                "duration": "3 years 1 month",
                "location": "San Francisco, CA",
                "description": "Managed point-of-sale product line. Conducted extensive user research and A/B testing. Grew active merchant base by 60%."
            },
            {
                "title": "Associate Product Manager",
                "company": "Google",
                "duration": "2 years",
                "location": "Mountain View, CA", 
                "description": "Rotational PM program. Worked on Google Pay and YouTube monetization products."
            }
        ],
        education=[
            {
                "institution": "Stanford University",
                "degree": "Master of Science in Computer Science",
                "duration": "2015 - 2017"
            },
            {
                "institution": "UC Berkeley",
                "degree": "Bachelor of Arts in Economics", 
                "duration": "2011 - 2015"
            }
        ],
        skills=[
            {"name": "Product Management", "endorsements": 45},
            {"name": "Product Strategy", "endorsements": 32},
            {"name": "User Research", "endorsements": 28}, 
            {"name": "Data Analysis", "endorsements": 35},
            {"name": "A/B Testing", "endorsements": 22},
            {"name": "SQL", "endorsements": 18},
            {"name": "Leadership", "endorsements": 40}
        ],
        linkedin_url="https://www.linkedin.com/in/sarah-chen-pm",
        total_experience_years=7,
        current_company="Stripe",
        current_title="Senior Product Manager",
        industry_keywords=["product management", "fintech", "payments", "user research", "data analysis"],
        data_completeness_score=0.95
    )
    
    # Good candidate
    good_candidate = LinkedInProfile(
        name="Michael Rodriguez", 
        headline="Product Manager at Airbnb | Growth & Marketplace Expert",
        location="San Francisco Bay Area",
        about="Product Manager focused on marketplace growth and user acquisition. 4 years of experience building products that connect supply and demand.",
        experience=[
            {
                "title": "Product Manager",
                "company": "Airbnb",
                "duration": "2 years 8 months", 
                "location": "San Francisco, CA",
                "description": "Lead growth initiatives for host acquisition. Built experimentation framework and increased host signups by 35%."
            },
            {
                "title": "Product Analyst",
                "company": "Uber",
                "duration": "1 year 6 months",
                "location": "San Francisco, CA", 
                "description": "Analyzed rider behavior and supported product decisions with data insights."
            }
        ],
        education=[
            {
                "institution": "UCLA",
                "degree": "Bachelor of Science in Economics",
                "duration": "2016 - 2020"
            }
        ],
        skills=[
            {"name": "Product Management", "endorsements": 25},
            {"name": "Growth Marketing", "endorsements": 18},
            {"name": "Data Analysis", "endorsements": 22},
            {"name": "Experimentation", "endorsements": 15}
        ],
        linkedin_url="https://www.linkedin.com/in/michael-rodriguez-growth",
        total_experience_years=4,
        current_company="Airbnb",
        current_title="Product Manager", 
        industry_keywords=["product management", "growth", "marketplace", "experimentation"],
        data_completeness_score=0.75
    )
    
    # Weak candidate
    weak_candidate = LinkedInProfile(
        name="Jennifer Kim",
        headline="Marketing Manager at Samsung | Brand & Digital Marketing",
        location="Los Angeles, California",
        about="Marketing professional with experience in brand management and digital campaigns.",
        experience=[
            {
                "title": "Marketing Manager",
                "company": "Samsung",
                "duration": "3 years",
                "location": "Los Angeles, CA",
                "description": "Managed brand campaigns for consumer electronics. Led social media strategy."
            }
        ],
        education=[
            {
                "institution": "USC",
                "degree": "Bachelor of Arts in Marketing",
                "duration": "2017 - 2021"
            }
        ],
        skills=[
            {"name": "Marketing", "endorsements": 30},
            {"name": "Brand Management", "endorsements": 20},
            {"name": "Social Media", "endorsements": 25}
        ],
        linkedin_url="https://www.linkedin.com/in/jennifer-kim-marketing",
        total_experience_years=3,
        current_company="Samsung",
        current_title="Marketing Manager",
        industry_keywords=["marketing", "brand", "campaigns"],
        data_completeness_score=0.60
    )
    
    return [strong_candidate, good_candidate, weak_candidate]


def test_candidate_scoring():
    """Test the AI-powered candidate scoring system"""
    print("Testing AI-Powered Candidate Scoring System")
    print("=" * 60)
    
    # Create job requirements and candidates
    job_req = create_sample_job_requirements()
    candidates = create_sample_candidate_profiles()
    
    print(f"\nJob Requirements:")
    print(f"Position: {job_req.job_title}")
    print(f"Required Skills: {', '.join(job_req.required_skills)}")
    print(f"Experience: {job_req.min_experience_years}-{job_req.max_experience_years} years")
    
    print(f"\nCandidates to Score: {len(candidates)}")
    for candidate in candidates:
        print(f"- {candidate.name}: {candidate.headline}")
    
    # Initialize scorer and score candidates
    scorer = CandidateScorer()
    
    print(f"\nStarting AI-powered scoring...")
    scores = scorer.score_multiple_candidates(candidates, job_req)
    
    # Display results
    print(f"\nSCORING RESULTS")
    print("=" * 40)
    
    for i, score in enumerate(scores):
        print(f"\n{i+1}. {score.candidate_name}")
        print(f"   Overall Score: {score.overall_score:.1f}/100")
        print(f"   Recommendation: {score.recommendation}")
        print(f"   Skills: {score.skills_score:.1f} | Experience: {score.experience_score:.1f} | Education: {score.education_score:.1f}")
        
        if score.strengths:
            print(f"   Strengths: {', '.join(score.strengths[:2])}...")
        if score.concerns:
            print(f"   Concerns: {', '.join(score.concerns[:2])}...")
    
    # Generate comprehensive report
    print(f"\n📄 Generating Comprehensive Report...")
    report = scorer.create_scoring_report(scores, job_req)
    
    # Save report
    report_file = REPO_ROOT / "candidate_scoring_report.md"
    with open(report_file, "w") as f:
        f.write(report)
    
    print(f"Report saved to: {report_file}")
    
    return scores


def test_profile_extraction():
    """Test the enhanced profile extraction (requires browser)"""
    print("\n Testing Enhanced Profile Extraction")
    print("=" * 40)
    
    extractor = ProfileExtractor()
    
    # Test with a sample LinkedIn profile URL (would need real URL)
    sample_url = "https://www.linkedin.com/in/sample-profile"
    print(f"Note: To test profile extraction, provide a real LinkedIn URL")
    print(f"Example: python -c \"from test_candidate_scoring import test_profile_extraction; test_profile_extraction()\"")
    
    # Show the capabilities
    print(f"\n Profile Extraction Capabilities:")
    print(f"- Navigate to any LinkedIn profile URL")
    print(f"- Extract comprehensive profile data (experience, education, skills)")
    print(f"- AI-powered parsing and structuring")
    print(f"- Fallback parsing if AI fails")
    print(f"- Data completeness scoring")


if __name__ == "__main__":
    try:
        # Test candidate scoring
        scores = test_candidate_scoring()
        
        # Show sample JSON output
        if scores:
            print(f"\n Sample Score JSON:")
            sample_score = scores[0].to_dict()
            print(json.dumps(sample_score, indent=2)[:500] + "...")
        
        print(f"\n All tests completed successfully!")
        print(f"\nNext steps:")
        print(f"1. Integrate with LinkedIn search to get real candidate profiles")
        print(f"2. Use extracted profiles + job requirements for scoring")
        print(f"3. Add scoring to the main agent workflow")
        
    except Exception as e:
        print(f" Test failed: {e}")
        import traceback
        traceback.print_exc()