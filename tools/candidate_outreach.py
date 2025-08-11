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
        position_context: Dict[str, Any],
        strategy: Optional[Dict[str, Any]] = None
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
                
                # Apply strategic bonuses if strategy provided
                if strategy:
                    evaluation_obj = self._apply_strategic_bonuses(evaluation_obj, candidate_profile, strategy)
                
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
                                # Apply strategic bonuses if strategy provided
                                if strategy:
                                    evaluation_obj = self._apply_strategic_bonuses(evaluation_obj, candidate_profile, strategy)
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
        context_str = f"""
Role: {position_context.get('title', 'Software Engineer')}
Location: {position_context.get('location', 'San Francisco')}
Experience Level: {position_context.get('experience_level', '3-8 years')}
Key Technologies: {', '.join(position_context.get('technologies', ['Python', 'JavaScript', 'React']))}
Company Type: {position_context.get('company_type', 'Tech startup/established company')}
Remote Policy: {position_context.get('remote_policy', 'Hybrid/Remote-friendly')}"""

        # Add strategy-driven context if available
        if position_context.get('strategy_companies'):
            context_str += f"\nTarget Companies: {', '.join(position_context['strategy_companies'])}"
        
        if position_context.get('seniority_levels'):
            context_str += f"\nDesired Seniority: {', '.join(position_context['seniority_levels'])}"
            
        if position_context.get('primary_titles'):
            context_str += f"\nPrimary Job Titles: {', '.join(position_context['primary_titles'])}"
        
        return context_str
    
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
    
    def _apply_strategic_bonuses(self, evaluation_obj: CandidateOutreachEvaluation, 
                               candidate_profile: Dict[str, Any], 
                               strategy: Dict[str, Any]) -> CandidateOutreachEvaluation:
        """Apply strategic bonuses to outreach evaluation based on search strategy"""
        
        # Extract candidate headline and current info
        profile_data = candidate_profile.get('profile_data', {})
        headline = candidate_profile.get('headline', '') or profile_data.get('headline', '')
        current_company = profile_data.get('current_company', '')
        current_title = profile_data.get('current_title', '')
        
        # Combine headline and current info for analysis
        analysis_text = f"{headline} {current_title} {current_company}".lower()
        
        # Calculate strategic bonuses
        company_bonus = self._calculate_company_bonus(analysis_text, strategy)
        seniority_bonus = self._calculate_seniority_bonus(analysis_text, strategy) 
        tech_stack_bonus = self._calculate_tech_stack_bonus(analysis_text, strategy)
        
        total_bonus = company_bonus + seniority_bonus + tech_stack_bonus
        
        if total_bonus > 0:
            print(f"      📈 Strategic bonuses: Company(+{company_bonus:.1f}) + Seniority(+{seniority_bonus:.1f}) + Tech(+{tech_stack_bonus:.1f}) = +{total_bonus:.1f}")
        
        # Apply bonuses to overall score (cap at 50.0)
        original_score = evaluation_obj.overall_outreach_score
        new_score = min(original_score + total_bonus, 50.0)
        evaluation_obj.overall_outreach_score = new_score
        
        # Update recommendation based on new score
        if new_score >= 35.0 and not evaluation_obj.recommend_outreach:
            evaluation_obj.recommend_outreach = True
            print(f"      🎯 Strategic bonus triggered outreach recommendation: {original_score:.1f} → {new_score:.1f}")
        
        # Update priority based on final score
        if new_score >= 42.0:
            evaluation_obj.outreach_priority = "High"
        elif new_score >= 38.0:
            evaluation_obj.outreach_priority = "Medium"
        else:
            evaluation_obj.outreach_priority = "Low"
        
        return evaluation_obj
    
    def _calculate_company_bonus(self, analysis_text: str, strategy: Dict[str, Any]) -> float:
        """Calculate company-based bonus from strategy"""
        bonus = 0.0
        
        # Extract target companies from strategy
        target_companies = []
        if "target_companies" in strategy:
            target_companies = strategy["target_companies"]
        elif "headline_analysis" in strategy and "company_indicators" in strategy["headline_analysis"]:
            target_companies = strategy["headline_analysis"]["company_indicators"]
        
        if not target_companies:
            return 0.0
        
        # Company tier definitions (same as search system)
        tier_1_companies = ["google", "facebook", "meta", "apple", "microsoft", "amazon", "netflix", "tesla", "uber", "airbnb"]
        tier_2_companies = ["stripe", "dropbox", "slack", "salesforce", "adobe", "nvidia", "twitter", "linkedin", "pinterest", "square"]
        
        # Check for company mentions
        for company in target_companies:
            company_lower = company.lower()
            if company_lower in analysis_text:
                if company_lower in tier_1_companies:
                    bonus = max(bonus, 5.0)  # Tier 1 companies get 5 point bonus
                elif company_lower in tier_2_companies:
                    bonus = max(bonus, 3.0)  # Tier 2 companies get 3 point bonus  
                else:
                    bonus = max(bonus, 2.0)  # Other target companies get 2 point bonus
                break
                
        return bonus
    
    def _calculate_seniority_bonus(self, analysis_text: str, strategy: Dict[str, Any]) -> float:
        """Calculate seniority-based bonus from strategy"""
        bonus = 0.0
        
        # Extract seniority indicators from strategy
        seniority_indicators = []
        if "seniority_indicators" in strategy:
            seniority_indicators = [s.lower() for s in strategy["seniority_indicators"]]
        elif "headline_analysis" in strategy and "seniority_keywords" in strategy["headline_analysis"]:
            seniority_indicators = [s.lower() for s in strategy["headline_analysis"]["seniority_keywords"]]
        
        # Check for seniority matches
        for indicator in seniority_indicators:
            if indicator in analysis_text:
                # Categorize seniority level
                if any(exec_word in indicator for exec_word in ["cto", "ceo", "vp", "director", "head of"]):
                    bonus = max(bonus, 4.0)  # Executive level
                elif any(prin_word in indicator for prin_word in ["principal", "staff", "architect"]):
                    bonus = max(bonus, 3.0)  # Principal/Staff level  
                elif any(sr_word in indicator for sr_word in ["senior", "lead", "sr."]):
                    bonus = max(bonus, 2.0)  # Senior level
                else:
                    bonus = max(bonus, 1.0)  # General seniority indicator
                break
                
        return bonus
    
    def _calculate_tech_stack_bonus(self, analysis_text: str, strategy: Dict[str, Any]) -> float:
        """Calculate technology stack bonus from strategy"""
        bonus = 0.0
        
        # Extract key technologies from strategy
        key_technologies = []
        if "key_technologies" in strategy:
            key_technologies = [t.lower() for t in strategy["key_technologies"]]
        elif "headline_analysis" in strategy and "tech_stack_signals" in strategy["headline_analysis"]:
            key_technologies = [t.lower() for t in strategy["headline_analysis"]["tech_stack_signals"]]
        
        # Count technology matches
        tech_matches = [tech for tech in key_technologies if tech in analysis_text]
        if tech_matches:
            # Give bonus based on number of tech matches (max 2.0 points)
            bonus = min(len(tech_matches) * 0.5, 2.0)
            
        return bonus


# Global outreach manager instance
_outreach_manager = CandidateOutreachManager()


def evaluate_candidate_for_outreach(
    candidate_profile: Dict[str, Any],
    position_title: str = "Software Engineer",
    location: str = "San Francisco",
    required_technologies: List[str] = None,
    experience_level: str = "3-8 years",
    company_type: str = "Tech company",
    remote_policy: str = "Hybrid/Remote-friendly",
    strategy: Optional[Dict[str, Any]] = None
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
    
    # Build position context using strategy data when available
    technologies = required_technologies
    if not technologies and strategy:
        # Extract from strategy if not provided
        if "key_technologies" in strategy:
            technologies = strategy["key_technologies"]
        elif "headline_analysis" in strategy and "tech_stack_signals" in strategy["headline_analysis"]:
            technologies = strategy["headline_analysis"]["tech_stack_signals"]
    
    # Use strategy-provided defaults or fallback
    technologies = technologies or ["Python", "JavaScript", "React", "Node.js"]
    
    position_context = {
        "title": position_title,
        "location": location,
        "technologies": technologies,
        "experience_level": experience_level,
        "company_type": company_type,
        "remote_policy": remote_policy,
        "strategy_companies": strategy.get("target_companies", []) if strategy else [],
        "seniority_levels": strategy.get("seniority_indicators", []) if strategy else [],
        "primary_titles": strategy.get("primary_titles", strategy.get("primary_job_titles", [])) if strategy else []
    }
    
    print(f"📋 Evaluating candidate: {candidate_profile.get('name', 'Unknown')} for outreach...")
    
    return _outreach_manager.evaluate_candidate_for_outreach(
        candidate_profile=candidate_profile,
        position_context=position_context,
        strategy=strategy
    )


def bulk_evaluate_candidates_for_outreach(
    candidates: List[Dict[str, Any]],
    position_title: str = "Software Engineer",
    location: str = "San Francisco",
    required_technologies: List[str] = None,
    experience_level: str = "3-8 years",
    strategy: Optional[Dict[str, Any]] = None
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
                experience_level=experience_level,
                strategy=strategy
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
