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
from core.workflow_state import get_candidates_for_outreach, store_outreach_results
from utils.logger import log_info, log_debug, log_error, log_progress


def generate_candidate_outreach(
    position_title: str = "Software Engineer",
    location: str = "San Francisco",
    required_technologies: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generate personalized outreach messages using global state architecture
    
    Args:
        position_title: Job position title for context
        location: Job location for context
        required_technologies: List of required technologies
        
    Returns:
        Lightweight status dict: {success: True, outreach_generated: 8, recommended_count: 6}
        Actual outreach results stored in global state
    """
    
    log_info(f"📧 Starting candidate outreach generation...", phase="OUTREACH")
    log_info(f"   Position: {position_title} in {location}", phase="OUTREACH")
    
    # Get quality candidates from global state
    candidates = get_candidates_for_outreach()
    
    if not candidates:
        return {
            "success": False,
            "error": "No quality candidates found in global state. Run evaluate_candidates_quality first.",
            "outreach_generated": 0
        }
    
    log_info(f"🔄 Retrieved {len(candidates)} quality candidates from global state", phase="OUTREACH")
    
    # Get strategy from global state
    from core.workflow_state import get_strategy_for_search
    strategy = get_strategy_for_search()
    
    log_info(f"📊 Generating outreach for {len(candidates)} candidates...", phase="OUTREACH")
    
    # Prepare position context
    position_context = _build_position_context(position_title, location, required_technologies, strategy)
    
    # Generate outreach messages
    outreach_results = []
    successful_outreach = 0
    
    for i, candidate in enumerate(candidates, 1):
        log_progress(f"Generating outreach for {candidate.get('name', 'Unknown')} ({i}/{len(candidates)})", "OUTREACH")
        
        try:
            # Generate message directly without evaluation (candidates are pre-qualified)
            outreach_result = _generate_message_for_candidate(candidate, position_context, position_title, location)
            outreach_results.append(outreach_result)
            successful_outreach += 1
                
        except Exception as e:
            print(f"   ❌ Outreach generation failed: {e}")
            candidate_name = _extract_candidate_name(candidate)
            outreach_results.append({
                "name": candidate_name,
                "error": str(e),
                "recommend_outreach": False,
                "message": ""
            })
    
    print(f"\n📈 OUTREACH GENERATION RESULTS:")
    print(f"   Total processed: {len(candidates)}")
    print(f"   Recommended for outreach: {successful_outreach}")
    print(f"   Success rate: {(successful_outreach/len(candidates)*100):.1f}%")
    
    # Store outreach results in global state
    outreach_data = {
        "success": True,
        "outreach_generated": len(outreach_results),
        "recommended_count": successful_outreach,
        "messages": outreach_results,
        "position_context": position_context,
        "generation_timestamp": datetime.now().isoformat()
    }
    
    global_state_result = store_outreach_results(outreach_data)
    print(f"💾 {global_state_result.get('message', 'Outreach results stored in global state')}")
    
    # Return lightweight status for agent
    return {
        "success": True,
        "outreach_generated": len(outreach_results),
        "recommended_count": successful_outreach,
        "success_rate": (successful_outreach/len(candidates)*100) if len(candidates) > 0 else 0,
        "message": f"Generated {len(outreach_results)} outreach messages, stored in global state"
    }


def _extract_candidate_name(candidate: Dict[str, Any]) -> str:
    """Extract candidate name from different data structures"""
    if 'candidate_info' in candidate and 'profile_data' in candidate:
        return candidate['profile_data'].get('name', candidate['candidate_info'].get('name', 'Unknown'))
    return candidate.get('name', 'Unknown')


def _generate_message_for_candidate(candidate: Dict[str, Any], position_context: str, 
                                  position_title: str, location: str) -> Dict[str, Any]:
    """Generate outreach message for a pre-qualified candidate"""
    
    # Extract candidate details
    candidate_name = _extract_candidate_name(candidate)
    
    # Extract profile data based on structure
    if 'candidate_info' in candidate and 'profile_data' in candidate:
        profile_data = candidate['profile_data']
        candidate_info = candidate['candidate_info']
        headline = profile_data.get('headline', candidate_info.get('headline', ''))
        url = profile_data.get('url', candidate_info.get('url', ''))
        # Extract overall_score from evaluation result - comprehensive search across all possible locations
        overall_score = candidate.get('overall_score', 0.0)
        
        # If not found at top level, search all possible nested locations
        if overall_score == 0.0:
            # Try profile_data locations first
            overall_score = (
                profile_data.get('overall_score', 0.0) or
                profile_data.get('quality_assessment', {}).get('overall_score', 0.0)
            )
        
        # If still not found, try candidate_info locations
        if overall_score == 0.0:
            overall_score = (
                candidate_info.get('overall_score', 0.0) or
                candidate_info.get('quality_assessment', {}).get('overall_score', 0.0)
            )
        
        # Debug logging to help track down the issue
        if overall_score == 0.0:
            print(f"      ⚠️ WARNING: Could not find overall_score for {candidate_name}")
            print(f"         Top level keys: {list(candidate.keys())}")
            if 'profile_data' in candidate:
                print(f"         profile_data keys: {list(profile_data.keys())}")
                if 'quality_assessment' in profile_data:
                    qa = profile_data['quality_assessment']
                    if isinstance(qa, dict):
                        print(f"         quality_assessment keys: {list(qa.keys())}")
                    else:
                        print(f"         quality_assessment type: {type(qa)}")
            if 'candidate_info' in candidate:
                print(f"         candidate_info keys: {list(candidate_info.keys())}")
        else:
            print(f"      ✅ Found overall_score: {overall_score} for {candidate_name}")
    else:
        profile_data = candidate
        headline = candidate.get('headline', '')
        url = candidate.get('url', '')
        overall_score = candidate.get('overall_score', 0.0)
        
        # If not found at top level, try nested locations for flat structure
        if overall_score == 0.0:
            overall_score = candidate.get('quality_assessment', {}).get('overall_score', 0.0)
        
        # Debug logging for flat structure too
        if overall_score == 0.0:
            candidate_name = candidate.get('name', 'Unknown')
            print(f"      ⚠️ WARNING: Could not find overall_score for {candidate_name} (flat structure)")
            print(f"         Available keys: {list(candidate.keys())}")
        else:
            candidate_name = candidate.get('name', 'Unknown')
            print(f"      ✅ Found overall_score: {overall_score} for {candidate_name} (flat structure)")
    
    # Build candidate profile for message generation
    candidate_profile = {
        "name": candidate_name,
        "headline": headline,
        "url": url,
        "current_company": _extract_current_company(candidate),
        "current_title": _extract_current_title(candidate),
        "experiences": profile_data.get("experiences", []),
        "education": profile_data.get("education", []),
        "skills": profile_data.get("skills", []),
        "about": profile_data.get("about", "")
    }
    
    # Generate LLM-powered personalized message using outreach manager
    manager = CandidateOutreachManager()
    
    try:
        # Convert position_context string to structured dict for LLM
        position_dict = _parse_position_context(position_context, position_title, location)
        
        # Use LLM-powered outreach generation instead of template
        outreach_result = manager.evaluate_candidate_for_outreach(
            candidate_profile, 
            position_dict
        )
        
        # Extract message from LLM result
        if outreach_result.get("recommend_outreach") and outreach_result.get("personalized_message"):
            message = outreach_result["personalized_message"]
        elif outreach_result.get("message"):
            message = outreach_result["message"]
        else:
            # Fallback to enhanced template if LLM fails
            message = _create_enhanced_outreach_message(candidate_profile, position_context)
        
        return {
            "name": candidate_name,
            "recommend_outreach": True,
            "message": message,
            "url": url,
            "score": overall_score,
            "reasoning": f"Pre-qualified candidate with score {overall_score:.1f}"
        }
        
    except Exception as e:
        print(f"      ❌ Message generation failed for {candidate_name}: {e}")
        return {
            "name": candidate_name,
            "recommend_outreach": False,
            "error": str(e),
            "message": ""
        }


# Note: Removed _create_simple_outreach_message - replaced with LLM generation + enhanced fallback


def _extract_company_from_headline(headline: str) -> str:
    """Extract company name from headline like 'Software Engineer@Google' or 'Engineer at Meta'"""
    if not headline:
        return ""
    
    # Common patterns in LinkedIn headlines
    patterns = [
        r'@(\w+)',  # "Software Engineer@Google"
        r' at (\w+)',  # "Engineer at Meta"
        r'@(\w+\s+\w+)',  # "Engineer@JP Morgan" (two words)
        r' at ([\w\s]+?)(?:\s*\||$)',  # "Engineer at JP Morgan | ..." (stop at | or end)
    ]
    
    for pattern in patterns:
        import re
        match = re.search(pattern, headline, re.IGNORECASE)
        if match:
            company = match.group(1).strip()
            # Clean up common suffixes
            company = re.sub(r'\s*\|\s*.*$', '', company)  # Remove everything after |
            return company
    
    return ""


def _parse_position_context(position_context: str, position_title: str, location: str) -> Dict[str, Any]:
    """Parse position context string into structured dict for LLM"""
    
    # Extract from context string
    context_dict = {
        "title": position_title,
        "location": location,
        "experience_level": "3-8 years",
        "technologies": [],
        "company_type": "Tech company",
        "remote_policy": "Hybrid/Remote-friendly"
    }
    
    # Parse context string for additional info
    if position_context:
        lines = position_context.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("Required Technologies:") or line.startswith("Key Technologies:"):
                tech_str = line.split(":")[-1].strip()
                context_dict["technologies"] = [tech.strip() for tech in tech_str.split(",") if tech.strip()]
            elif line.startswith("Target Companies:"):
                companies_str = line.split(":")[-1].strip()
                context_dict["strategy_companies"] = [comp.strip() for comp in companies_str.split(",") if comp.strip()]
            elif line.startswith("Desired Seniority:"):
                seniority_str = line.split(":")[-1].strip()
                context_dict["seniority_levels"] = [sen.strip() for sen in seniority_str.split(",") if sen.strip()]
    
    return context_dict


def _create_enhanced_outreach_message(candidate_profile: Dict[str, Any], position_context: str) -> str:
    """Enhanced fallback message generation using our personalization logic"""
    
    name = candidate_profile.get("name", "")
    headline = candidate_profile.get("headline", "")
    experiences = candidate_profile.get("experiences", [])
    education = candidate_profile.get("education", [])
    skills = candidate_profile.get("skills", [])
    about = candidate_profile.get("about", "")
    
    # Extract position details from context
    position_title = "Software Engineer"
    location = "San Francisco"
    
    if position_context:
        lines = position_context.split('\n')
        for line in lines:
            if "Position:" in line:
                position_title = line.split("Position:")[-1].strip()
            elif "Location:" in line:
                location = line.split("Location:")[-1].strip()
    
    # Build personalized content using our enhanced logic
    personalization = _build_personalization_content(
        name, headline, experiences, education, skills, about, position_title
    )
    
    # Create enhanced message
    message = f"""Hi {name},

{personalization['opening']}

{personalization['connection']}

{personalization['opportunity']}

{personalization['closing']}

Best regards,
[Your Name]"""

    return message


def _build_personalization_content(name: str, headline: str, experiences: List[Dict], 
                                  education: List[Dict], skills: List[str], 
                                  about: str, position_title: str) -> Dict[str, str]:
    """Build personalized message content using candidate's rich profile data"""
    
    # Extract current work info
    current_company = ""
    current_role = headline
    years_experience = "several years"
    
    if experiences and len(experiences) > 0:
        current_exp = experiences[0]
        company = current_exp.get("company", "")
        title = current_exp.get("title", "")
        
        # Use company if available, otherwise extract from headline
        current_company = company if company else _extract_company_from_headline(headline)
        current_role = title if title else headline
        
        # Estimate years of experience from experience list
        if len(experiences) >= 3:
            years_experience = "extensive"
        elif len(experiences) >= 2:
            years_experience = "solid"
    
    # Extract education highlights
    education_highlight = ""
    if education:
        edu = education[0]
        school = edu.get("school", "")
        degree = edu.get("degree", "")
        if school:
            if any(prestigious in school.lower() for prestigious in 
                  ["stanford", "mit", "harvard", "berkeley", "carnegie mellon", "caltech"]):
                education_highlight = f"I also noticed your {degree} from {school} - impressive background!"
            elif school:
                education_highlight = f"I see you studied at {school}."
    
    # Extract relevant skills
    relevant_skills = []
    tech_keywords = ["python", "java", "javascript", "react", "node", "aws", "docker", 
                    "kubernetes", "microservices", "api", "database", "sql", "nosql",
                    "machine learning", "ai", "data", "cloud", "devops", "agile"]
    
    if skills:
        for skill in skills[:10]:  # Check first 10 skills
            if any(tech in skill.lower() for tech in tech_keywords):
                relevant_skills.append(skill)
    
    # Build opening - personalized based on their profile
    if current_company and current_company not in ["Unknown", ""]:
        opening_options = [
            f"I came across your profile and was impressed by your work as {current_role} at {current_company}.",
            f"I noticed your impressive background as {current_role} at {current_company}.",
            f"Your experience as {current_role} at {current_company} really caught my attention."
        ]
    else:
        opening_options = [
            f"I came across your profile and was impressed by your experience as {current_role}.",
            f"Your {years_experience} experience as {current_role} really caught my attention.",
            f"I noticed your impressive background as {current_role}."
        ]
    opening = opening_options[hash(name) % len(opening_options)]
    
    # Build connection - specific reasons why they're a good fit
    connection_parts = []
    
    if relevant_skills:
        connection_parts.append(f"Your expertise in {', '.join(relevant_skills[:3])} aligns perfectly with what we're looking for.")
    
    if current_company and current_company not in ["Unknown", "", "their current company", "their current role"]:
        connection_parts.append(f"Your experience at {current_company} demonstrates the high-caliber background we seek.")
    
    if education_highlight:
        connection_parts.append(education_highlight)
    
    # If no specific connections found, use professional experience
    if not connection_parts:
        connection_parts.append(f"Your {years_experience} professional experience in software development makes you an ideal candidate.")
    
    connection = " ".join(connection_parts)
    
    # Build opportunity description - tailored to their background
    opportunity_intro = f"I have an exciting {position_title} opportunity that would be perfect for someone with your background."
    
    tech_focus = ""
    if relevant_skills:
        if any(skill.lower() in ["python", "javascript", "java"] for skill in relevant_skills):
            tech_focus = "• Work with modern tech stack including the languages and frameworks you know best"
        elif any(skill.lower() in ["aws", "cloud", "docker", "kubernetes"] for skill in relevant_skills):
            tech_focus = "• Lead cloud infrastructure and DevOps initiatives using cutting-edge technologies"
        else:
            tech_focus = "• Work with cutting-edge technology and innovative projects"
    else:
        tech_focus = "• Work with cutting-edge technology and innovative projects"
    
    opportunity_details = f"""The role offers:

{tech_focus}
• Collaborative team environment with senior engineers and growth opportunities  
• Competitive compensation package with equity
• Flexible work arrangements and excellent benefits"""
    
    opportunity = f"{opportunity_intro}\n\n{opportunity_details}"
    
    # Build closing - specific call to action
    closing = """Would you be open to a brief 15-minute conversation about this opportunity? I'd love to learn more about your current interests and share specific details about the role and team.

Looking forward to connecting!"""
    
    return {
        "opening": opening,
        "connection": connection, 
        "opportunity": opportunity,
        "closing": closing
    }


def _get_evaluated_candidates() -> List[Dict[str, Any]]:
    """Get candidates from evaluation results"""
    try:
        # Try to import and use the evaluation tool to get results
        from tools.candidate_evaluation import evaluate_candidates_quality
        
        # Get evaluation results (this will use defaults if no candidates passed)
        eval_results = evaluate_candidates_quality()
        
        if eval_results.get("success") and eval_results.get("quality_candidates"):
            print("📥 Using candidates from evaluation results")
            return eval_results["quality_candidates"]
            
    except Exception as e:
        print(f"   ⚠️ Could not get evaluation results: {e}")
    
    return []


def _build_position_context(position_title: str, location: str, 
                          required_technologies: Optional[List[str]], 
                          strategy: Optional[Dict[str, Any]]) -> str:
    """Build position context from parameters and strategy"""
    
    context_parts = [
        f"Position: {position_title}",
        f"Location: {location}"
    ]
    
    # Add technology requirements
    if required_technologies:
        context_parts.append(f"Required Technologies: {', '.join(required_technologies)}")
    elif strategy and "key_technologies" in strategy:
        context_parts.append(f"Key Technologies: {', '.join(strategy['key_technologies'][:5])}")
    
    # Add strategic context
    if strategy:
        if "target_companies" in strategy:
            context_parts.append(f"Target Companies: {', '.join(strategy['target_companies'][:3])}")
        if "seniority_indicators" in strategy:
            context_parts.append(f"Desired Seniority: {', '.join(strategy['seniority_indicators'][:3])}")
    
    return "\n".join(context_parts)


def _generate_single_outreach(candidate: Dict[str, Any], position_context: str, min_score: float) -> Dict[str, Any]:
    """Generate outreach for a single candidate using existing logic"""
    
    # Convert candidate to format expected by existing function
    candidate_profile = {
        "name": candidate.get("name", ""),
        "headline": candidate.get("headline", ""),
        "url": candidate.get("url", ""),
        "current_company": _extract_current_company(candidate),
        "current_title": _extract_current_title(candidate),
        "experiences": candidate.get("experiences", []),
        "education": candidate.get("education", []),
        "skills": candidate.get("skills", []),
        "about": candidate.get("about", "")
    }
    
    # Use existing evaluation logic
    manager = CandidateOutreachManager()
    result = manager.evaluate_candidate_for_outreach(
        candidate_profile, 
        position_context,
        include_strategic_bonuses=True,
        strategy={}  # Strategy bonuses handled in evaluation tool
    )
    
    return result


def _extract_current_company(candidate: Dict[str, Any]) -> str:
    """Extract current company from candidate data with proper nested structure handling"""
    # Handle nested structure: {candidate_info: {...}, profile_data: {...}}
    if 'profile_data' in candidate:
        profile_data = candidate['profile_data']
        experiences = profile_data.get("experiences", [])
    else:
        # Flat structure
        experiences = candidate.get("experiences", [])
    
    if experiences and isinstance(experiences, list) and len(experiences) > 0:
        company = experiences[0].get("company", "")
        return company if company else "Unknown"
    return "Unknown"


def _extract_current_title(candidate: Dict[str, Any]) -> str:
    """Extract current title from candidate data with proper nested structure handling"""
    # Handle nested structure first
    if 'profile_data' in candidate:
        profile_data = candidate['profile_data']
        headline = profile_data.get("headline", "")
        if headline:
            return headline
        experiences = profile_data.get("experiences", [])
    else:
        # Flat structure
        headline = candidate.get("headline", "")
        if headline:
            return headline
        experiences = candidate.get("experiences", [])
    
    if experiences and isinstance(experiences, list) and len(experiences) > 0:
        title = experiences[0].get("title", "")
        return title if title else "Unknown"
    
    return "Unknown"


# Export the new agent tool
CandidateOutreachGenerationTool = FunctionTool(fn=generate_candidate_outreach)


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
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error saving outreach results: {e}")
        return f"Error: {e}"


# Create AdalFlow Function Tools
SaveOutreachResultsTool = FunctionTool(fn=save_outreach_results)
