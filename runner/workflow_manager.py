"""
LinkedIn Recruitment Workflow Manager
Handles the orchestration of the recruitment process in clean, decoupled steps
"""
from functools import partial
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path
import json

from agents.linkedin_agent import LinkedInAgent
from utils.role_prompts import RolePromptBuilder
from config import AgentConfig
from adalflow.core.func_tool import FunctionTool

class LinkedInWorkflowManager:
    """Manages the LinkedIn recruitment workflow with clean separation of concerns"""
    
    def __init__(self, query: str, location: str, limit: int, **kwargs):
        self.query = query
        self.location = location
        self.limit = limit
        self.enhanced_prompting = kwargs.get('enhanced_prompting', True)
        self.streaming = kwargs.get('streaming', True)
        self.job_description = kwargs.get('job_description', None)  # Job description text
        
        # Initialize components
        self.agent = None
        self.results = []
        self.config = AgentConfig()  # Initialize agent config
        self.strategy_data = None  # Store strategy data for enhanced scoring
        self.outreach_results = None  # Store outreach results for saving in Step 3
        
        
    def initialize_agent(self) -> LinkedInAgent:
        """Step 2: Initialize agent for agentic workflow"""
        print("🤖 Initializing LinkedIn agent for agentic workflow...")
        
        # Initialize the agent
        self.agent = LinkedInAgent()
        
        # Build prompt for agentic workflow
        prompt = self._build_agentic_prompt()
        print("✅ Using agentic workflow prompt with strategy generation")
        
        print("✅ Agent initialized with full agentic workflow")
        
        return self.agent, prompt
    
    def execute_search_workflow(self, progress_tracker=None) -> List[Dict[str, Any]]:
        """Step 3: Execute the complete agentic workflow"""
        print(f"🔍 Starting agentic recruitment workflow...")
        print(f"📊 Target: {self.limit} candidates")
        
        candidates = []
        
        try:
            agent, prompt = self.initialize_agent()
            
            if progress_tracker:
                progress_tracker.start_workflow()
            
            # Execute agent workflow
            result = agent.call(query=prompt)
            
            # Print agent execution steps (same format as original runner)
            self._print_agent_execution_steps(result)
            
            # Process results from 4-step agentic workflow
            agent_results = self._extract_results_from_agent(result)
            candidates = agent_results["candidates"]
            
            # Store strategy data for enhanced scoring
            self.strategy_data = agent_results.get("strategy_results")
            
            # Store outreach results for saving in Step 3
            self.outreach_results = agent_results.get("outreach_results")
            
            # If no candidates from step history, try extracting from final answer
            if len(candidates) == 0:
                print("🔍 No candidates from step history, checking final answer...")
                candidates = self._extract_candidates_from_final_answer(result)
            
            # If still no candidates, try URL re-extraction approach
            if len(candidates) == 0:
                print("🔍 No candidates from final answer, trying URL re-extraction...")
                candidates = self._retry_extraction_from_urls(result)
            
            if progress_tracker:
                progress_tracker.log_completion(candidates)
                
                # Log outreach results if available (saving will happen in Step 3 with other results)
                if agent_results.get("outreach_results"):
                    try:
                        print("📧 Processing agent outreach results...")
                        progress_tracker.log_outreach_evaluation(agent_results["outreach_results"])
                        print("📧 Outreach results will be saved with other results in Step 3")
                    except Exception as outreach_error:
                        print(f"⚠️  Outreach processing failed: {outreach_error}")
            
            self.results = candidates
            print(f"\n📊 Total candidates extracted from agent: {len(candidates)}")
            print(f"✅ Workflow completed: {len(candidates)} candidates found")
            
            return candidates
            
        except Exception as e:
            print(f"❌ Agent workflow failed: {e}")
            import traceback
            print(f"📝 Error details: {traceback.format_exc()[:200]}...")
            
            # Try fallback direct execution
            try:
                print("🔄 Attempting fallback workflow...")
                fallback_candidates = self._execute_fallback_workflow()
                if fallback_candidates:
                    return fallback_candidates
            except Exception as fallback_error:
                print(f"❌ Fallback workflow also failed: {fallback_error}")
            
            # Return any partial results we managed to extract
            print(f"📊 Returning {len(candidates)} partial results")
            return candidates
    
    def _print_agent_execution_steps(self, result) -> None:
        """Print agent execution steps using same format as original runner"""
        try:
            # Define steps before conditional block to avoid variable scoping issues
            steps = getattr(result, "step_history", getattr(result, "steps", []))
            
            print("Run complete. Steps:")
            
            if not steps:
                print("No steps recorded - agent may have encountered parsing issues")
            print(f"Result: {result}")
            
            # Extract candidates from agent steps (same logic as original)
            for i, s in enumerate(steps, 1):
                print(i, getattr(s, 'thought', getattr(s, 'action', 'step')))
                
                # Handle Function objects from AdalFlow - check step structure
                # Steps have: step, action (Function), function (Function), observation
                action = getattr(s, 'action', None)
                function = getattr(s, 'function', None)
                observation = getattr(s, 'observation', None)
                
                # Extract tool info from action or function
                func_obj = action or function
                if func_obj:
                    tool_name = getattr(func_obj, 'name', None)
                    tool_kwargs = getattr(func_obj, 'kwargs', {})
                    tool_args = getattr(func_obj, 'args', [])
                else:
                    tool_name = getattr(s, 'name', getattr(s, 'tool_name', None))
                    tool_args = getattr(s, 'args', getattr(s, 'tool_args', []))
                    tool_kwargs = getattr(s, 'kwargs', getattr(s, 'tool_kwargs', {}))
                
                tool_result = observation
                
                if tool_name:
                    print("  ->", tool_name, tool_kwargs or tool_args, "=>", (str(tool_result)[:120] if tool_result is not None else None))
                
                import time
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error printing agent steps: {e}")
    
    def save_results(self, candidates: List[Dict[str, Any]], output_dir: str = "results", strategy_data: Dict[str, Any] = None) -> Dict[str, str]:
        """Step 4: Save recruitment results with error handling"""
        try:
            from runner.result_saver import save_recruitment_results
            
            search_params = {
                "query": self.query,
                "location": self.location,
                "limit": self.limit,
                "enhanced_prompting": self.enhanced_prompting,
                "streaming": self.streaming,
                "strategy_used": True  # Strategy is now always generated by agent
            }
            
            # Use stored outreach results if not provided as parameter
            outreach_data = self.outreach_results
            
            return save_recruitment_results(candidates, search_params, output_dir, strategy_data, outreach_data)
            
        except Exception as e:
            print(f"⚠️  Failed to save results: {e}")
            print(f"📊 Found {len(candidates)} candidates (unsaved)")
            return {
                "evaluation_file": "Error: Could not save",
                "candidates_file": "Error: Could not save", 
                "txt_file": "Error: Could not save",
                "candidates_count": len(candidates)
            }
    
    def _build_agentic_prompt(self) -> str:
        """Build prompt for agentic workflow with strategy generation"""
        base_prompt = RolePromptBuilder.build_enhanced_prompt(
            base_query=self.query,
            location=self.location,
            limit=self.limit,
            strategy=None  # Strategy will be generated by agent as first step
        )
        
        # Add job description context if available
        if self.job_description:
            job_context = f"\n\nJOB DESCRIPTION CONTEXT:\n{self.job_description}\n\nUse this job description to create a highly targeted search strategy that matches the specific requirements, technologies, and qualifications mentioned above."
            base_prompt += job_context
            print(f"📋 Enhanced prompt with job description ({len(self.job_description)} characters)")
        
        return base_prompt
    
    def _build_basic_prompt(self) -> str:
        """Build basic prompt without strategy"""
        return (
            f"Open LinkedIn, search for people with '{self.query}' in {self.location}. "
            f"Collect up to {self.limit} candidates. For each, open the profile and call extract_complete_profile. "
            f"Keep actions small and verify URL/location changes."
        )
    
    def _create_fallback_strategy(self) -> Dict[str, Any]:
        """Create fallback strategy when LLM fails"""
        return {
            "headline_analysis": {
                "target_job_titles": [self.query.lower()],
                "alternative_titles": ["software developer", "full stack developer", "backend engineer", "frontend engineer"],
                "seniority_keywords": ["senior", "lead", "staff", "principal"],
                "company_indicators": ["google", "facebook", "apple", "amazon", "microsoft", "netflix", "uber", "airbnb"],
                "tech_stack_signals": ["python", "java", "javascript", "react", "node.js", "aws", "docker", "kubernetes"]
            },
            "search_filtering": {
                "negative_headline_patterns": ["intern", "student"],  # Avoid overly broad patterns
                "minimum_headline_score": 2.0  # Match smart_candidate_search default
            },
            "profile_evaluation_context": {
                "focus_areas": ["Technical skills and tech stack", "Work experience and project impact", "Education and certifications", "Contributions to open source or community"],
                "quality_indicators": ["relevant experience", "good companies"],
                "ideal_candidate_description": f"Experienced {self.query} with relevant background"
            },
            "fallback_strategy": True
        }
    
    def _extract_results_from_agent(self, result) -> Dict[str, Any]:
        """Extract results from the 5-step agentic workflow"""
        results = {
            "strategy_results": None,
            "extraction_results": None,
            "evaluation_results": None, 
            "outreach_results": None,
            "candidates": []
        }
        
        if hasattr(result, 'step_history'):
            print(f"🔍 Processing {len(result.step_history)} agent steps")
            
            # Process step history to find tool results
            for i, step in enumerate(result.step_history, 1):
                action = getattr(step, 'action', None)
                function = getattr(step, 'function', None)
                observation = getattr(step, 'observation', None)
                
                func_obj = action or function
                func_name = getattr(func_obj, 'name', None) if func_obj else None
                
                print(f"  Step {i}: {func_name or 'Unknown'} -> {type(observation).__name__ if observation else 'None'}")
                
                if func_name == 'create_search_strategy':
                    print(f"🎯 Found strategy results")
                    results["strategy_results"] = observation
                    
                elif func_name == 'extract_candidate_profiles':
                    print(f"📥 Found extraction results")
                    results["extraction_results"] = observation
                    
                elif func_name == 'evaluate_candidates_quality':
                    print(f"🎯 Found evaluation results") 
                    results["evaluation_results"] = observation
                    
                elif func_name == 'generate_candidate_outreach':
                    print(f"📧 Found outreach results")
                    results["outreach_results"] = observation
                    
                # Check for errors or issues in steps
                if func_obj and hasattr(func_obj, '_is_answer_final') and getattr(func_obj, '_is_answer_final', False):
                    print(f"⚠️  Agent marked step {i} as final: {getattr(func_obj, '_answer', 'No answer')}")
                    
        else:
            print("❌ No step_history found in agent result")
        
        # Merge data from different sources for complete candidate information
        candidates = self._merge_candidate_data(
            extraction_results=results["extraction_results"],
            evaluation_results=results["evaluation_results"], 
            outreach_results=results["outreach_results"]
        )
        
        results["candidates"] = candidates
        print(f"📊 Extracted {len(candidates)} candidates from agent workflow")
        
        return results
    
    def _merge_candidate_data(
        self, 
        extraction_results: Dict[str, Any], 
        evaluation_results: Dict[str, Any],
        outreach_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Merge candidate data from extraction, evaluation, and outreach results"""
        
        candidates = []
        
        # Start with extraction results (complete profile data)
        if extraction_results and isinstance(extraction_results, dict):
            batch_results = extraction_results.get('results', [])
            print(f"📥 Found {len(batch_results)} extraction results")
            
            # Create lookup for evaluation scores by candidate name/URL
            eval_scores = {}
            if evaluation_results and isinstance(evaluation_results, dict):
                all_evaluated = evaluation_results.get('all_evaluated_candidates', [])
                for eval_candidate in all_evaluated:
                    name = eval_candidate.get('name', '')
                    url = eval_candidate.get('url', '')
                    if name or url:
                        key = name if name else url
                        eval_scores[key] = eval_candidate
                print(f"🎯 Found {len(eval_scores)} evaluation scores")
            
            # Create lookup for outreach data by candidate name
            outreach_data = {}
            if outreach_results and isinstance(outreach_results, dict):
                outreach_messages = outreach_results.get('messages', [])
                for outreach_msg in outreach_messages:
                    name = outreach_msg.get('name', '')
                    if name:
                        outreach_data[name] = outreach_msg
                print(f"📧 Found {len(outreach_data)} outreach messages")
            
            # Merge all data sources
            for result in batch_results:
                if isinstance(result, dict) and result.get('profile_data'):
                    candidate_info = result.get('candidate_info', {})
                    profile_data = result.get('profile_data', {})
                    
                    # Get candidate identifiers
                    name = profile_data.get('name', candidate_info.get('name', ''))
                    url = candidate_info.get('url', profile_data.get('url', ''))
                    
                    # Find matching evaluation and outreach data
                    eval_data = eval_scores.get(name, eval_scores.get(url, {}))
                    outreach_msg = outreach_data.get(name, {})
                    
                    # Build complete candidate record
                    candidate = {
                        "search_info": {
                            "url": url,
                            "headline_score": candidate_info.get('headline_score', 0.0),
                            "name": name
                        },
                        "profile_details": {
                            **profile_data,  # Complete profile (experiences, education, skills, etc.)
                            "quality_assessment": eval_data.get('quality_assessment', candidate_info.get('quality_assessment', {}))
                        }
                    }
                    
                    # Add evaluation scores if available
                    if eval_data:
                        # Handle quality_assessment whether it's a dict or dataclass
                        quality_assessment = candidate["profile_details"]["quality_assessment"]
                        
                        # Convert dataclass to dict if needed using .to_dict() method
                        if hasattr(quality_assessment, 'to_dict'):
                            quality_assessment = quality_assessment.to_dict()
                        elif not isinstance(quality_assessment, dict):
                            quality_assessment = {}
                        
                        # Update with evaluation data
                        quality_assessment.update({
                            "overall_score": eval_data.get('overall_score', 0.0),
                            "component_scores": eval_data.get('component_scores', {}),
                            "meets_threshold": eval_data.get('meets_threshold', False),
                            "strengths": eval_data.get('strengths', []),
                            "concerns": eval_data.get('concerns', []),
                            "evaluation_timestamp": eval_data.get('evaluation_timestamp', ''),
                            "strategic_bonuses": eval_data.get('strategic_bonuses', {}),
                            "baseline_scores": eval_data.get('baseline_scores', {})
                        })
                        
                        # Assign back to candidate
                        candidate["profile_details"]["quality_assessment"] = quality_assessment
                    
                    # Add outreach data if available
                    if outreach_msg:
                        candidate["profile_details"]["outreach_info"] = {
                            "message": outreach_msg.get('message', ''),
                            "recommend_outreach": outreach_msg.get('recommend_outreach', False),
                            "outreach_score": outreach_msg.get('score', 0.0),
                            "outreach_reasoning": outreach_msg.get('reasoning', '')
                        }
                    
                    candidates.append(candidate)
        
        print(f"📊 Merged complete data for {len(candidates)} candidates")
        return candidates
    
    def _extract_candidates_from_evaluation(self, evaluation_results) -> List[Dict[str, Any]]:
        """Extract candidates from evaluation tool results (preferred - has quality scores)"""
        if not evaluation_results or not isinstance(evaluation_results, dict):
            return []
        
        candidates = []
        
        # Get all evaluated candidates (both quality and non-quality)
        all_candidates = evaluation_results.get('all_evaluated_candidates', [])
        quality_candidates = evaluation_results.get('quality_candidates', [])
        
        print(f"🎯 Processing {len(all_candidates)} evaluated candidates")
        
        # Use original candidate data from evaluation results for complete profile info
        for candidate in all_candidates:
            if isinstance(candidate, dict):
                # Extract the original nested structure that has complete profile data
                original_candidate = candidate.get('original_candidate', candidate)
                
                # Get candidate info and profile data
                if 'candidate_info' in original_candidate and 'profile_data' in original_candidate:
                    candidate_info = original_candidate['candidate_info']
                    profile_data = original_candidate['profile_data']
                else:
                    # Fallback to flat structure
                    candidate_info = candidate
                    profile_data = candidate
                
                candidates.append({
                    "search_info": {
                        "url": candidate_info.get('url', profile_data.get('url', '')),
                        "headline_score": candidate.get('overall_score', candidate_info.get('headline_score', 0.0)),
                        "name": profile_data.get('name', candidate_info.get('name', candidate.get('name', '')))
                    },
                    "profile_details": {
                        **profile_data,  # Include all profile data (experiences, education, skills, etc.)
                        "quality_assessment": {
                            "overall_score": candidate.get('overall_score', 0.0),
                            "component_scores": candidate.get('component_scores', {}),
                            "meets_threshold": candidate.get('meets_threshold', False),
                            "strengths": candidate.get('strengths', []),
                            "concerns": candidate.get('concerns', []),
                            "evaluation_timestamp": candidate.get('evaluation_timestamp', ''),
                            "strategic_bonuses": candidate.get('strategic_bonuses', {}),
                            "baseline_scores": candidate.get('baseline_scores', {})
                        }
                    }
                })
        
        return candidates
    
    def _extract_candidates_from_extraction(self, extraction_results) -> List[Dict[str, Any]]:
        """Extract candidates from extraction tool results (fallback)"""
        if not extraction_results or not isinstance(extraction_results, dict):
            return []
        
        candidates = []
        batch_results = extraction_results.get('results', [])
        
        print(f"📥 Processing {len(batch_results)} extraction results")
        
        for result in batch_results:
            if isinstance(result, dict) and result.get('profile_data'):
                candidate_info = result.get('candidate_info', {})
                profile_data = result.get('profile_data', {})
                
                candidates.append({
                    "search_info": {
                        "url": candidate_info.get('url', ''),
                        "headline_score": candidate_info.get('headline_score', 0.0),
                        "name": candidate_info.get('name', '')
                    },
                    "profile_details": {
                        **profile_data,
                        "quality_assessment": candidate_info.get('quality_assessment', {})
                    }
                })
        
        return candidates
    
    def _extract_url_from_step_history(self, steps, current_step) -> str:
        """Extract LinkedIn URL from step history - improved for AdalFlow structure"""
        # Look for recent 'go' action before current step
        try:
            current_index = steps.index(current_step)
        except ValueError:
            current_index = len(steps)  # If current_step not found, search all steps
        
        for i in range(current_index - 1, -1, -1):
            step = steps[i]
            
            # Handle both action and function attributes
            action = getattr(step, 'action', None)
            function = getattr(step, 'function', None)
            func_obj = action or function
            
            if func_obj:
                func_name = getattr(func_obj, 'name', None)
                func_kwargs = getattr(func_obj, 'kwargs', {})
                
                # Look for 'go' function with LinkedIn URL
                if (func_name == 'go' and 
                    isinstance(func_kwargs, dict) and
                    'linkedin.com/in/' in str(func_kwargs.get('url', ''))):
                    
                    url = func_kwargs['url']
                    # Clean up URL - remove miniProfileUrn params
                    if '?miniProfileUrn' in url:
                        url = url.split('?miniProfileUrn')[0]
                    if not url.endswith('/'):
                        url += '/'
                    return url
        
        return "Unknown URL"
    
    def _execute_fallback_workflow(self) -> List[Dict[str, Any]]:
        """Fallback workflow when agent fails"""
        print("🔄 Executing fallback workflow...")
        
        try:
            from tools.people_search import search_people
            from tools.profile_extractor import extract_profile  # Fixed import
            from tools.web_nav import go
            import time
            
            # Direct search
            search_results = search_people(self.query, self.location, self.limit)
            
            if search_results.get("count", 0) > 0:
                candidates = []
                for i, candidate in enumerate(search_results.get("results", [])[:self.limit]):
                    try:
                        print(f"📝 Extracting profile {i+1}: {candidate['name']}")
                        
                        # Add delay to avoid rate limiting
                        if i > 0:
                            time.sleep(1)
                        
                        go(candidate["url"])
                        time.sleep(0.5)  # Wait for page load
                        
                        profile_data = extract_profile()  # Fixed function call
                        
                        # Validate profile data
                        if isinstance(profile_data, dict) and profile_data.get('name'):
                            candidates.append({"search_info": candidate, "profile_details": profile_data})
                            print(f"    ✅ Successfully extracted: {profile_data.get('name')}")
                        else:
                            print(f"    ⚠️  Invalid profile data for {candidate['name']} - skipping")
                            
                    except Exception as profile_error:
                        print(f"    ❌ Failed to extract profile for {candidate['name']}: {profile_error}")
                        continue  # Continue with next candidate
                
                return candidates
            else:
                print("❌ No candidates found in fallback search")
                return []
                
        except Exception as e:
            print(f"❌ Fallback workflow also failed: {e}")
            return []
    
    def _extract_candidates_from_final_answer(self, result) -> List[Dict[str, Any]]:
        """Extract candidates from agent's final answer when step history fails"""
        candidates = []
        
        try:
            # Try multiple ways to get the final answer
            final_answer = None
            if hasattr(result, 'data') and result.data:
                if hasattr(result.data, '_answer'):
                    final_answer = result.data._answer
                elif hasattr(result.data, 'answer'):
                    final_answer = result.data.answer
            elif hasattr(result, '_answer'):
                final_answer = result._answer
            elif hasattr(result, 'answer'):
                final_answer = result.answer
            
            if final_answer and 'linkedin.com/in/' in str(final_answer):
                print("🔍 Found LinkedIn URLs in final answer")
                import re
                # Extract LinkedIn URLs
                urls = re.findall(r'https://www\.linkedin\.com/in/[a-zA-Z0-9\-_]+/?', str(final_answer))
                # Clean up URLs
                cleaned_urls = []
                for url in urls:
                    cleaned_url = url.rstrip('.,!?":\'')
                    if not cleaned_url.endswith('/'):
                        cleaned_url += '/'
                    cleaned_urls.append(cleaned_url)
                
                print(f"🔗 Found {len(cleaned_urls)} LinkedIn URLs")
                
                # Re-extract profiles from URLs
                if cleaned_urls:
                    candidates = self._retry_extraction_from_urls_list(cleaned_urls)
            
        except Exception as e:
            print(f"⚠️  Failed to extract from final answer: {e}")
        
        return candidates
    
    def _retry_extraction_from_urls(self, result) -> List[Dict[str, Any]]:
        """Retry extraction by finding URLs in result and re-extracting"""
        try:
            # First try to get URLs from final answer
            candidates = self._extract_candidates_from_final_answer(result)
            if candidates:
                return candidates
                
            # If that fails, try to find URLs in step history
            if hasattr(result, 'step_history'):
                urls = set()
                for step in result.step_history:
                    action = getattr(step, 'action', None)
                    function = getattr(step, 'function', None)
                    func_obj = action or function
                    
                    if func_obj:
                        func_name = getattr(func_obj, 'name', None)
                        func_kwargs = getattr(func_obj, 'kwargs', {})
                        
                        if (func_name == 'go' and 
                            isinstance(func_kwargs, dict) and
                            'linkedin.com/in/' in str(func_kwargs.get('url', ''))):
                            urls.add(func_kwargs['url'])
                
                if urls:
                    print(f"🔗 Found {len(urls)} URLs from step history")
                    return self._retry_extraction_from_urls_list(list(urls))
            
        except Exception as e:
            print(f"⚠️  Failed to retry extraction from URLs: {e}")
        
        return []
    
    def _retry_extraction_from_urls_list(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Re-extract profiles from a list of URLs with error handling"""
        candidates = []
        
        try:
            from tools.profile_extractor import extract_profile  # Fixed import path
            from tools.web_nav import go, get_current_url
            import time
            
            for i, url in enumerate(urls[:self.limit], 1):
                try:
                    print(f"⚙️  Re-extracting profile {i}: {url}")
                    
                    # Add delay to avoid rate limiting
                    if i > 1:
                        time.sleep(2)
                    
                    # Navigate to profile
                    go(url)
                    time.sleep(1)  # Wait for page load
                    
                    # Verify we're on the right page
                    current_url = get_current_url()
                    
                    if '/feed/' in current_url or 'linkedin.com/in/' not in current_url:
                        print(f"    ⚠️  Redirected away from profile - skipping")
                        continue
                    
                    # Extract profile
                    profile_data = extract_profile()
                    
                    # Validate extracted data
                    if (isinstance(profile_data, dict) and 
                        profile_data.get('name') and 
                        profile_data.get('name').lower() != 'feed updates'):
                        
                        candidates.append({
                            "search_info": {"url": url},
                            "profile_details": profile_data
                        })
                        print(f"    ✅ Successfully extracted: {profile_data.get('name', 'Unknown')}")
                    else:
                        print(f"    ⚠️  Invalid profile data - skipping")
                        
                except Exception as e:
                    print(f"    ❌ Failed to extract profile {i}: {e}")
                    continue  # Continue with next URL
            
            print(f"📊 Successfully re-extracted {len(candidates)} candidates from URLs")
            
        except ImportError as e:
            print(f"⚠️  Cannot import extraction tools: {e}")
        except Exception as e:
            print(f"❌ URL re-extraction failed: {e}")
        
        return candidates