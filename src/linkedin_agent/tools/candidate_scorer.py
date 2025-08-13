"""
AI-Powered Candidate Scoring System using AdalFlow
"""
import sys
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from adalflow.core import Generator
from adalflow.components.output_parsers.dataclass_parser import DataClassParser
from adalflow.components.model_client import OpenAIClient
from adalflow.core.func_tool import FunctionTool

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ..models.linkedin_profile import LinkedInProfile, JobRequirements, CandidateScore
from ..config import get_model_kwargs


# AI-powered candidate scoring prompt using AdalFlow best practices
CANDIDATE_SCORING_PROMPT = r"""<SYS>
You are an expert technical recruiter and candidate assessment specialist. Your task is to analyze a candidate's LinkedIn profile against specific job requirements and provide a comprehensive scoring assessment.

Key responsibilities:
1. Analyze candidate's skills, experience, education, and background
2. Match against job requirements systematically  
3. Provide detailed scoring across multiple dimensions
4. Give actionable insights and recommendations
5. Be objective and thorough in your analysis

Scoring Guidelines:
- Overall Score: 0-100 (100 = perfect match, 0 = no match)
- Skills Score: Match required/preferred skills (weight: 30%)
- Experience Score: Relevance of work experience (weight: 35%) 
- Education Score: Educational background match (weight: 15%)
- Location Score: Geographic preferences (weight: 10%)
- Company Score: Previous company prestige/relevance (weight: 10%)

Recommendation Categories:
- Strong Match (80-100): Ideal candidate, proceed immediately
- Good Match (60-79): Solid candidate, worth interviewing
- Weak Match (40-59): Some potential, proceed with caution
- No Match (0-39): Poor fit, pass on candidate
</SYS>

Job Requirements:
{{ job_requirements }}

Candidate Profile:
{{ candidate_profile }}

Please analyze this candidate against the job requirements and provide a comprehensive scoring assessment in the following JSON format:

{{ format_instructions }}

Be thorough in your analysis. Provide specific examples from the candidate's profile that support your scoring. Focus on both strengths and potential concerns. Your assessment will be used to make hiring decisions."""


ROLE_SPECIFIC_PROMPTS = {
    "product_manager": r"""
Product Manager Specific Analysis:
- Focus on product strategy, user research, analytics experience
- Value cross-functional collaboration and leadership
- Look for experience with product metrics, A/B testing, roadmaps
- Consider experience with technical teams and stakeholders
- Assess communication and problem-solving skills from descriptions
""",
    
    "software_engineer": r"""
Software Engineer Specific Analysis:  
- Focus on programming languages, frameworks, and technologies
- Value system design, architecture, and technical leadership experience
- Look for contributions to open source, technical blogs, or projects
- Consider experience with relevant tech stack and methodologies
- Assess problem-solving and technical depth from project descriptions
""",
    
    "data_scientist": r"""
Data Scientist Specific Analysis:
- Focus on machine learning, statistics, and data analysis skills
- Value experience with Python, R, SQL, and data visualization tools
- Look for experience with ML models, data pipelines, and analytics
- Consider domain expertise and business impact of data projects
- Assess quantitative background and research experience
""",
    
    "sales": r"""
Sales Professional Specific Analysis:
- Focus on sales metrics, quota attainment, and revenue generation
- Value relationship building, negotiation, and communication skills
- Look for experience with relevant sales tools and methodologies
- Consider industry knowledge and customer base experience
- Assess track record of exceeding targets and building pipelines
""",
    
    "marketing": r"""
Marketing Professional Specific Analysis:
- Focus on campaign performance, growth metrics, and brand building
- Value experience with digital marketing, content, and analytics
- Look for multi-channel marketing experience and creativity
- Consider customer acquisition, retention, and lifecycle marketing
- Assess strategic thinking and data-driven decision making
"""
}


class CandidateScorer:
    """AI-powered candidate scoring and assessment"""
    
    def __init__(self):
        self.client = OpenAIClient()
        self.parser = DataClassParser(
            data_class=CandidateScore,
            return_data_class=True,
            format_type="json"
        )
        
        # Base generator for general scoring
        self.generator = Generator(
            model_client=self.client,
            model_kwargs=get_model_kwargs(),
            template=CANDIDATE_SCORING_PROMPT,
            output_processors=self.parser
        )
        
        # Role-specific generators
        self.role_generators = {}
        for role, role_prompt in ROLE_SPECIFIC_PROMPTS.items():
            enhanced_template = CANDIDATE_SCORING_PROMPT + "\n\n" + role_prompt
            self.role_generators[role] = Generator(
                model_client=self.client,
                model_kwargs=get_model_kwargs(),
                template=enhanced_template,
                output_processors=self.parser
            )
    
    def _detect_role_type(self, job_title: str) -> str:
        """Detect role type from job title for role-specific analysis"""
        title_lower = job_title.lower()
        
        if any(keyword in title_lower for keyword in ['product', 'pm', 'product manager']):
            return "product_manager"
        elif any(keyword in title_lower for keyword in ['engineer', 'developer', 'software', 'swe']):
            return "software_engineer"
        elif any(keyword in title_lower for keyword in ['data scientist', 'data science', 'ml engineer', 'machine learning']):
            return "data_scientist"
        elif any(keyword in title_lower for keyword in ['sales', 'account executive', 'sales manager', 'bdr', 'sdr']):
            return "sales"
        elif any(keyword in title_lower for keyword in ['marketing', 'growth', 'brand', 'content', 'digital marketing']):
            return "marketing"
        else:
            return "general"
    
    def score_candidate(self, 
                       candidate: LinkedInProfile, 
                       job_requirements: JobRequirements) -> Optional[CandidateScore]:
        """Score a candidate against job requirements"""
        try:
            print(f"Scoring candidate: {candidate.name} for {job_requirements.job_title}")
            
            # Detect role type for specialized analysis
            role_type = self._detect_role_type(job_requirements.job_title)
            generator = self.role_generators.get(role_type, self.generator)
            
            if role_type != "general":
                print(f"Using {role_type} specialized analysis")
            
            # Convert objects to JSON for the prompt
            candidate_json = candidate.to_json()
            job_requirements_json = job_requirements.to_json()
            
            # Generate the score using direct call with prompt_kwargs
            response = generator(
                prompt_kwargs={
                    "candidate_profile": candidate_json,
                    "job_requirements": job_requirements_json,
                    "format_instructions": self.parser.get_output_format_str()
                }
            )
            
            if response:
                # Check for parsing errors
                if hasattr(response, 'error') and response.error:
                    print(f"Parser error: {response.error}")
                
                if hasattr(response, 'data') and response.data:
                    score = response.data
                    print(f"Scoring complete: {score.overall_score:.1f}/100 ({score.recommendation})")
                    return score
                
                # Try to manually parse from raw response if DataClass parser failed
                if hasattr(response, 'raw_response') and response.raw_response:
                    try:
                        # The raw_response is a string representation, need to parse differently
                        # Check if we can extract directly from the generator response
                        text_content = None
                        
                        # Method 1: Check if raw_response contains the actual Response object string
                        if isinstance(response.raw_response, str) and 'text=' in response.raw_response:
                            import re
                            # Try multiple patterns to extract text content
                            text_patterns = [
                                r"text='([^']*)'",
                                r'text="([^"]*)"',
                                r"text=([^,)]*)",
                            ]
                            
                            for pattern in text_patterns:
                                text_match = re.search(pattern, response.raw_response)
                                if text_match:
                                    text_content = text_match.group(1)
                                    break
                                
                        # Method 2: If raw_response is the actual object (not string), use original method
                        elif hasattr(response.raw_response, 'output') and response.raw_response.output:
                            # Get the text from the response output message
                            output_msg = response.raw_response.output[0]
                            if hasattr(output_msg, 'content') and output_msg.content:
                                text_content = output_msg.content[0].text
                        
                        if text_content:
                            # Handle escaped newlines in text content
                            text_content = text_content.replace('\\n', '\n').replace('\\t', '\t')
                            
                            # Extract JSON from the text (remove markdown code blocks)
                            import re
                            json_str = None
                            
                            # Pattern 1: JSON in markdown code blocks (multi-line) - greedy match
                            json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text_content, re.DOTALL | re.MULTILINE)
                            if json_match:
                                json_str = json_match.group(1)
                            else:
                                # Pattern 2: Look for complete JSON object with overall_score
                                json_match = re.search(r'(\{[^{}]*"overall_score"[^{}]*\})', text_content, re.DOTALL)
                                if json_match:
                                    json_str = json_match.group(1)
                                else:
                                    # Pattern 3: More flexible JSON extraction
                                    json_match = re.search(r'(\{.*?"candidate_name".*?\})', text_content, re.DOTALL)
                                    if json_match:
                                        json_str = json_match.group(1)
                                    else:
                                        print(f"No JSON found in response text: {text_content[:200]}...")
                                        json_str = None
                                    
                            if json_str:
                                score_dict = json.loads(json_str)
                                
                                # Convert to CandidateScore object
                                score = CandidateScore.from_dict(score_dict)
                                print(f"Manual parsing successful: {score.overall_score:.1f}/100 ({score.recommendation})")
                                return score
                        
                    except Exception as parse_error:
                        print(f"Manual parsing failed: {parse_error}")
                    
            print("AI scoring failed - no structured data returned")
            return None
                
        except Exception as e:
            print(f"Scoring error: {e}")
            return None
    
    def score_multiple_candidates(self,
                                 candidates: List[LinkedInProfile],
                                 job_requirements: JobRequirements) -> List[CandidateScore]:
        """Score multiple candidates and return sorted by score"""
        scores = []
        
        print(f"Scoring {len(candidates)} candidates for {job_requirements.job_title}")
        
        for i, candidate in enumerate(candidates):
            print(f"\nScoring candidate {i+1}/{len(candidates)}: {candidate.name}")
            score = self.score_candidate(candidate, job_requirements)
            if score:
                scores.append(score)
        
        # Sort by overall score (highest first)
        scores.sort(key=lambda x: x.overall_score, reverse=True)
        
        print(f"\nScoring complete! Top candidate: {scores[0].candidate_name if scores else 'None'}")
        return scores
    
    def create_scoring_report(self, 
                             scores: List[CandidateScore],
                             job_requirements: JobRequirements) -> str:
        """Generate a comprehensive scoring report"""
        if not scores:
            return "No candidates scored."
        
        report = [
            f"# Candidate Scoring Report",
            f"**Position:** {job_requirements.job_title}",
            f"**Candidates Evaluated:** {len(scores)}",
            f"**Date:** {scores[0].reasoning if scores else 'N/A'}",
            "",
            "## Top Candidates",
            ""
        ]
        
        # Top candidates summary
        for i, score in enumerate(scores[:5]):  # Top 5
            report.append(f"### {i+1}. {score.candidate_name}")
            report.append(f"**Overall Score:** {score.overall_score:.1f}/100")
            report.append(f"**Recommendation:** {score.recommendation}")
            report.append("")
            report.append("**Breakdown:**")
            report.append(f"- Skills: {score.skills_score:.1f}/100")
            report.append(f"- Experience: {score.experience_score:.1f}/100") 
            report.append(f"- Education: {score.education_score:.1f}/100")
            report.append(f"- Location: {score.location_score:.1f}/100")
            report.append(f"- Company: {score.company_score:.1f}/100")
            report.append("")
            
            if score.strengths:
                report.append("**Strengths:**")
                for strength in score.strengths:
                    report.append(f"- {strength}")
                report.append("")
            
            if score.concerns:
                report.append("**Concerns:**")
                for concern in score.concerns:
                    report.append(f"- {concern}")
                report.append("")
            
            report.append(f"**Analysis:** {score.reasoning}")
            report.append("\n---\n")
        
        # Summary statistics
        avg_score = sum(s.overall_score for s in scores) / len(scores)
        strong_matches = len([s for s in scores if s.recommendation == "Strong Match"])
        good_matches = len([s for s in scores if s.recommendation == "Good Match"])
        
        report.extend([
            "## Summary Statistics",
            f"- **Average Score:** {avg_score:.1f}/100",
            f"- **Strong Matches:** {strong_matches}",
            f"- **Good Matches:** {good_matches}",
            f"- **Weak/No Matches:** {len(scores) - strong_matches - good_matches}",
            "",
            "## Recommendations",
            "1. **Immediate Interviews:** Candidates with Strong Match (80-100)",
            "2. **Secondary Review:** Candidates with Good Match (60-79)", 
            "3. **Consider for Future:** Candidates with Weak Match (40-59)",
            "4. **Pass:** Candidates with No Match (0-39)"
        ])
        
        return "\n".join(report)


# Global scorer instance (created on demand)
_scorer = None

def get_global_scorer():
    """Get or create global scorer instance"""
    global _scorer
    if _scorer is None:
        _scorer = CandidateScorer()
    return _scorer


def score_candidate_against_job(candidate_data: dict, job_requirements_data: dict) -> dict:
    """Score a single candidate - function tool wrapper"""
    try:
        # Convert dicts to DataClass objects
        candidate = LinkedInProfile.from_dict(candidate_data)
        job_req = JobRequirements.from_dict(job_requirements_data)
        
        score = get_global_scorer().score_candidate(candidate, job_req)
        return score.to_dict() if score else {"error": "Scoring failed"}
        
    except Exception as e:
        return {"error": f"Scoring error: {e}"}


def score_multiple_candidates_for_job(candidates_data: list, job_requirements_data: dict) -> dict:
    """Score multiple candidates - function tool wrapper"""
    try:
        # Convert data to objects
        candidates = [LinkedInProfile.from_dict(c) for c in candidates_data]
        job_req = JobRequirements.from_dict(job_requirements_data)
        
        scores = get_global_scorer().score_multiple_candidates(candidates, job_req)
        
        return {
            "scores": [s.to_dict() for s in scores],
            "summary": {
                "total_candidates": len(scores),
                "avg_score": sum(s.overall_score for s in scores) / len(scores) if scores else 0,
                "top_candidate": scores[0].candidate_name if scores else None
            }
        }
        
    except Exception as e:
        return {"error": f"Scoring error: {e}"}


# Function tools for agent
ScoreCandidateTool = FunctionTool(fn=score_candidate_against_job)
ScoreMultipleCandidatesTool = FunctionTool(fn=score_multiple_candidates_for_job)