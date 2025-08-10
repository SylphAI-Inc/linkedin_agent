"""
Candidate Outreach Tool - Evaluate profiles and generate personalized DM messages
"""

from typing import List, Dict, Any, Optional
import json
import time
import re
from datetime import datetime

from adalflow.core.func_tool import FunctionTool
from adalflow.core import Generator
from adalflow.components.output_parsers.dataclass_parser import DataClassParser
from adalflow.components.model_client import OpenAIClient
from config import get_model_kwargs
from models.linkedin_profile import CandidateOutreachEvaluation


# AdalFlow prompt for candidate evaluation and DM generation
CANDIDATE_EVALUATION_PROMPT = r"""<ROLE>
You are an expert technical recruiter with deep knowledge of software engineering roles and candidate assessment.
</ROLE>

<CONTEXT>
You are evaluating a software engineer candidate's LinkedIn profile to determine if they would be a good fit for our open position and whether to send them a personalized recruitment message.

Position Context:
{{position_context}}

Candidate Profile:
{{candidate_profile}}
</CONTEXT>

<TASK>
1. Evaluate this candidate's profile for the target role
2. Determine if they warrant outreach based on their qualifications
3. If yes, generate a personalized, professional DM message
</TASK>

<EVALUATION_CRITERIA>
Score each area 0-10:

1. TECHNICAL FIT (0-10): Relevant technologies, programming languages, frameworks
2. EXPERIENCE RELEVANCE (0-10): Years of experience, role progression, project complexity  
3. CAREER PROGRESSION (0-10): Growth pattern, leadership potential, recent activity
4. CULTURAL FIT (0-10): Company alignment, values, work style indicators
5. AVAILABILITY LIKELIHOOD (0-10): Signs they may be open to new opportunities

OUTREACH THRESHOLD: Total score >= 35/50 (average 7/10) to warrant outreach
</EVALUATION_CRITERIA>

<DM_GUIDELINES>
If the candidate qualifies for outreach:
- Keep message under 150 words
- Personalize with specific details from their profile
- Mention relevant experience or projects
- Professional but friendly tone
- Clear call-to-action
- Include company value proposition
- Avoid generic recruitment language
</DM_GUIDELINES>

Please analyze this candidate against the job requirements and provide a comprehensive outreach evaluation in the following JSON format:

{{ format_instructions }}

<INSTRUCTIONS>
- Be thorough but efficient in evaluation
- Focus on role-relevant qualifications
- Personalize messages with specific profile details
- Be honest about concerns while highlighting strengths
- Only recommend outreach for genuinely qualified candidates
- Return structured evaluation following the exact JSON format above
</INSTRUCTIONS>"""


class CandidateOutreachManager:
    """Manages candidate evaluation and outreach message generation"""
    
    def __init__(self):
        self.model_client = OpenAIClient()
        self.model_kwargs = get_model_kwargs()
        
        # Set up DataClassParser for CandidateOutreachEvaluation
        self.parser = DataClassParser(
            data_class=CandidateOutreachEvaluation,
            return_data_class=True,
            format_type="json"
        )
        
        self.evaluator = Generator(
            model_client=self.model_client,
            model_kwargs=self.model_kwargs,
            template=CANDIDATE_EVALUATION_PROMPT,
            output_processors=self.parser
        )
        self.outreach_history = []
    
    def evaluate_candidate_for_outreach(
        self,
        candidate_profile: Dict[str, Any],
        position_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate a candidate's profile and generate personalized outreach if qualified
        
        Args:
            candidate_profile: Full candidate profile data
            position_context: Job requirements and company context
            
        Returns:
            Evaluation results with outreach recommendation and message
        """
        
        try:
            # Prepare the evaluation prompt
            prompt_data = {
                "position_context": self._format_position_context(position_context),
                "candidate_profile": self._format_candidate_profile(candidate_profile),
                "format_instructions": self.parser.get_output_format_str()
            }
            
            # Generate evaluation using AdalFlow - using call method like in candidate scorer
            evaluation_result = self.evaluator(
                prompt_kwargs=prompt_data
            )
            
            # Extract the evaluation data as dataclass object
            if hasattr(evaluation_result, 'data') and evaluation_result.data:
                evaluation_obj = evaluation_result.data
                print(f"✅ Successfully parsed dataclass: {type(evaluation_obj)}")
            elif hasattr(evaluation_result, 'raw_response'):
                print(f"⚠️  DataClass parsing failed, raw response available: {type(evaluation_result.raw_response)}")
                evaluation_obj = evaluation_result
            else:
                print(f"⚠️  Unexpected evaluation result format: {type(evaluation_result)}")
                evaluation_obj = evaluation_result
            
            # Ensure we have a CandidateOutreachEvaluation object
            if isinstance(evaluation_obj, CandidateOutreachEvaluation):
                # Update candidate name if not set
                if not evaluation_obj.candidate_name:
                    evaluation_obj.candidate_name = candidate_profile.get('name', 'Unknown')
                
                # Convert to dict for compatibility with existing code
                evaluation_data = evaluation_obj.to_dict()
                evaluation_data.update({
                    "candidate_url": candidate_profile.get('url', ''),
                    "evaluation_timestamp": datetime.now().isoformat(),
                    "evaluator_version": "v1.0"
                })
            else:
                print(f"⚠️  Attempting manual parsing from response...")
                # Fallback manual parsing like in candidate scorer
                try:
                    # Try to extract JSON from the response
                    raw_response = evaluation_result.raw_response if hasattr(evaluation_result, 'raw_response') else None
                    if raw_response and hasattr(raw_response, 'output') and raw_response.output:
                        output_msg = raw_response.output[0]
                        if hasattr(output_msg, 'content') and output_msg.content:
                            text_content = output_msg.content[0].text
                            
                            # Extract JSON from the text
                            import re
                            json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text_content, re.DOTALL)
                            if json_match:
                                json_str = json_match.group(1)
                                evaluation_dict = json.loads(json_str)
                                
                                # Convert to CandidateOutreachEvaluation object
                                evaluation_obj = CandidateOutreachEvaluation.from_dict(evaluation_dict)
                                evaluation_data = evaluation_obj.to_dict()
                                evaluation_data.update({
                                    "candidate_url": candidate_profile.get('url', ''),
                                    "evaluation_timestamp": datetime.now().isoformat(),
                                    "evaluator_version": "v1.0"
                                })
                                print(f"✅ Manual parsing successful")
                            else:
                                raise ValueError("No JSON found in response")
                    else:
                        raise ValueError("No valid response content")
                        
                except Exception as parse_error:
                    print(f"❌ Manual parsing failed: {parse_error}")
                    # Return error evaluation
                    evaluation_data = {
                        "error": f"Evaluation parsing failed: {parse_error}",
                        "candidate_name": candidate_profile.get('name', 'Unknown'),
                        "overall_outreach_score": 0.0,
                        "recommend_outreach": False,
                        "evaluation_timestamp": datetime.now().isoformat(),
                        "candidate_url": candidate_profile.get('url', ''),
                        "evaluator_version": "v1.0"
                    }
            
            # Store in history
            self.outreach_history.append(evaluation_data)
            
            return evaluation_data
            
        except Exception as e:
            print(f"❌ Error evaluating candidate: {e}")
            return {
                "error": str(e),
                "candidate_name": candidate_profile.get('name', 'Unknown'),
                "evaluation_timestamp": datetime.now().isoformat()
            }
    
    def _format_position_context(self, position_context: Dict[str, Any]) -> str:
        """Format position context for the prompt"""
        return f"""
Role: {position_context.get('title', 'Software Engineer')}
Location: {position_context.get('location', 'San Francisco')}
Experience Level: {position_context.get('experience_level', '3-8 years')}
Key Technologies: {', '.join(position_context.get('technologies', ['Python', 'JavaScript', 'React']))}
Company Type: {position_context.get('company_type', 'Tech startup/established company')}
Remote Policy: {position_context.get('remote_policy', 'Hybrid/Remote-friendly')}
Team Size: {position_context.get('team_size', '10-50 engineers')}
Special Requirements: {position_context.get('special_requirements', 'None specified')}
"""
    
    def _format_candidate_profile(self, profile: Dict[str, Any]) -> str:
        """Format candidate profile for the prompt"""
        
        # Handle nested profile data structure
        if 'profile_data' in profile:
            profile_data = profile['profile_data']
        else:
            profile_data = profile
        
        formatted = f"""
Name: {profile_data.get('name', 'N/A')}
Headline: {profile_data.get('headline', 'N/A')}
Location: {profile_data.get('location', 'N/A')}
About: {profile_data.get('about', 'N/A')[:500] if profile_data.get('about') else 'N/A'}

Experience:
"""
        
        # Format experience
        experiences = profile_data.get('experiences', [])
        for i, exp in enumerate(experiences[:3], 1):  # Show top 3 experiences
            formatted += f"""
{i}. {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')}
   Duration: {exp.get('start_date', 'N/A')} - {exp.get('end_date', 'N/A')}
   Description: {' '.join(exp.get('bullets', []))[:200] if exp.get('bullets') else 'N/A'}
"""
        
        # Format education
        education = profile_data.get('education', [])
        if education:
            formatted += "\nEducation:\n"
            for edu in education[:2]:  # Show top 2 education entries
                formatted += f"- {edu.get('degree', 'N/A')} from {edu.get('school', 'N/A')}\n"
        
        # Format skills
        skills = profile_data.get('skills', [])
        if skills:
            formatted += f"\nSkills: {', '.join(skills[:10])}\n"  # Show top 10 skills
        
        return formatted
    
    def get_outreach_summary(self) -> Dict[str, Any]:
        """Get summary of outreach evaluations"""
        total_evaluated = len(self.outreach_history)
        should_contact = sum(1 for h in self.outreach_history 
                           if h.get('outreach_decision', {}).get('should_contact', False))
        
        return {
            "total_evaluated": total_evaluated,
            "recommended_for_outreach": should_contact,
            "outreach_rate": f"{(should_contact/total_evaluated*100):.1f}%" if total_evaluated > 0 else "0%",
            "evaluations": self.outreach_history
        }


# Global outreach manager instance
_outreach_manager = CandidateOutreachManager()


def evaluate_candidate_for_outreach(
    candidate_profile: Dict[str, Any],
    position_title: str = "Software Engineer",
    location: str = "San Francisco",
    required_technologies: List[str] = None,
    experience_level: str = "3-8 years",
    company_type: str = "Tech company",
    remote_policy: str = "Hybrid/Remote-friendly"
) -> Dict[str, Any]:
    """
    Evaluate a candidate's profile for outreach and generate personalized DM if qualified
    
    Args:
        candidate_profile: Full candidate profile data
        position_title: Job title for the role
        location: Job location
        required_technologies: List of key technologies needed
        experience_level: Required experience level
        company_type: Type of company/industry
        remote_policy: Remote work policy
        
    Returns:
        Evaluation results with outreach recommendation and personalized message
    """
    
    # Build position context
    position_context = {
        "title": position_title,
        "location": location,
        "technologies": required_technologies or ["Python", "JavaScript", "React", "Node.js"],
        "experience_level": experience_level,
        "company_type": company_type,
        "remote_policy": remote_policy,
        "team_size": "10-50 engineers",
        "special_requirements": "Strong communication skills, collaborative mindset"
    }
    
    print(f"📋 Evaluating candidate: {candidate_profile.get('name', 'Unknown')} for outreach...")
    
    return _outreach_manager.evaluate_candidate_for_outreach(
        candidate_profile=candidate_profile,
        position_context=position_context
    )


def bulk_evaluate_candidates_for_outreach(
    candidates: List[Dict[str, Any]],
    position_title: str = "Software Engineer",
    location: str = "San Francisco",
    required_technologies: List[str] = None,
    experience_level: str = "3-8 years"
) -> Dict[str, Any]:
    """
    Evaluate multiple candidates for outreach in batch
    
    Args:
        candidates: List of candidate profiles
        position_title: Job title for the role
        location: Job location  
        required_technologies: List of key technologies needed
        experience_level: Required experience level
        
    Returns:
        Batch evaluation results with outreach recommendations
    """
    
    print(f"📋 Bulk evaluating {len(candidates)} candidates for outreach...")
    
    results = []
    outreach_candidates = []
    
    for i, candidate in enumerate(candidates, 1):
        try:
            print(f"   📝 Evaluating candidate {i}/{len(candidates)}: {candidate.get('name', 'Unknown')}")
            
            evaluation = evaluate_candidate_for_outreach(
                candidate_profile=candidate,
                position_title=position_title,
                location=location,
                required_technologies=required_technologies,
                experience_level=experience_level
            )
            
            results.append(evaluation)
            
            # Track candidates recommended for outreach  
            if evaluation.get('recommend_outreach', False):
                outreach_candidates.append(evaluation)
                print(f"      ✅ Recommended for outreach (score: {evaluation.get('overall_outreach_score', 'N/A')})")
            else:
                print(f"      ❌ Not recommended (score: {evaluation.get('overall_outreach_score', 'N/A')})")
            
            # Small delay to avoid overwhelming the LLM
            time.sleep(0.5)
            
        except Exception as e:
            print(f"      ❌ Error evaluating candidate: {e}")
            results.append({
                "error": str(e),
                "candidate_name": candidate.get('name', 'Unknown')
            })
    
    summary = {
        "total_evaluated": len(candidates),
        "recommended_for_outreach": len(outreach_candidates),
        "outreach_rate": f"{(len(outreach_candidates)/len(candidates)*100):.1f}%" if candidates else "0%",
        "evaluation_results": results,
        "outreach_candidates": outreach_candidates,
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"\n📊 Outreach Evaluation Summary:")
    print(f"   Total candidates: {summary['total_evaluated']}")
    print(f"   Recommended for outreach: {summary['recommended_for_outreach']}")
    print(f"   Outreach rate: {summary['outreach_rate']}")
    
    return summary


def get_outreach_summary() -> Dict[str, Any]:
    """Get summary of all outreach evaluations performed"""
    return _outreach_manager.get_outreach_summary()


def save_outreach_results(
    outreach_data: Dict[str, Any],
    output_file: str = None
) -> str:
    """
    Save outreach evaluation results to a JSON file
    
    Args:
        outreach_data: Outreach evaluation results
        output_file: Output file path (optional)
        
    Returns:
        Path to saved file
    """
    
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"results/outreach_evaluation_{timestamp}.json"
    
    # Ensure results directory exists
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(outreach_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Outreach results saved to: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"❌ Error saving outreach results: {e}")
        return f"Error: {e}"


# Create AdalFlow Function Tools
EvaluateCandidateForOutreachTool = FunctionTool(fn=evaluate_candidate_for_outreach)
BulkEvaluateCandidatesForOutreachTool = FunctionTool(fn=bulk_evaluate_candidates_for_outreach)
GetOutreachSummaryTool = FunctionTool(fn=get_outreach_summary)
SaveOutreachResultsTool = FunctionTool(fn=save_outreach_results)
