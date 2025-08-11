"""
LinkedIn Recruitment Workflow Manager
Handles the orchestration of the recruitment process in clean, decoupled steps
"""
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path
import json

from tools.strategy_generator import StrategyGenerator
from src.linkedin_agent import LinkedInAgent
from utils.role_prompts import RolePromptBuilder
from config import AgentConfig


class LinkedInWorkflowManager:
    """Manages the LinkedIn recruitment workflow with clean separation of concerns"""
    
    def __init__(self, query: str, location: str, limit: int, **kwargs):
        self.query = query
        self.location = location
        self.limit = limit
        self.enhanced_prompting = kwargs.get('enhanced_prompting', True)
        self.streaming = kwargs.get('streaming', True)
        
        # Initialize components
        self.agent = None
        self.strategy_generator = StrategyGenerator()
        self.strategy = {}
        self.results = []
        self.config = AgentConfig()  # Initialize agent config
        
    def create_recruitment_strategy(self) -> Dict[str, Any]:
        """Step 1: Create comprehensive search strategy (DISABLED - not in original flow)"""
        print("🔍 Creating recruitment strategy...")
        
        try:
            self.strategy = self.strategy_generator.create_search_strategy(
                query=self.query,
                location=self.location
            )
            self.strategy = self.strategy.to_dict()
            self.strategy['original_query'] = self.query
            return self.strategy
        except Exception as e:
            print(f"⚠️  Failed to create strategy: {e}")
            print("📊 Using fallback strategy instead")

            # Use simple fallback strategy to avoid LLM calls that cause issues
            self.strategy = self._create_fallback_strategy()
            return self.strategy
        
    def initialize_agent(self) -> LinkedInAgent:
        """Step 2: Initialize agent with strategy context"""
        print("🤖 Initializing LinkedIn agent with strategy context...")
        
        # Build enhanced prompt with strategy
        if self.enhanced_prompting and self.strategy:
            prompt = self._build_strategy_enhanced_prompt()
        else:
            prompt = self._build_basic_prompt()
        
        self.agent = LinkedInAgent()
        print("✅ Agent initialized")
        
        return self.agent, prompt
    
    def execute_search_workflow(self, strategy, progress_tracker=None) -> List[Dict[str, Any]]:
        """Step 3: Execute the complete search workflow with robust error handling"""
        print(f"🔍 Starting recruitment workflow...")
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
            
            # Process results based on agent execution
            candidates = self._extract_candidates_from_result(result)
            
            # If no candidates from step history, try extracting from final answer
            if len(candidates) == 0:
                print("🔍 No candidates from step history, checking final answer...")
                candidates = self._extract_candidates_from_final_answer(result)
            
            # If still no candidates, try URL re-extraction approach
            if len(candidates) == 0:
                print("🔍 No candidates from final answer, trying URL re-extraction...")
                candidates = self._retry_extraction_from_urls(result)
            
            # Auto-evaluate candidates for outreach if we have extracted profiles
            if len(candidates) > 0 and progress_tracker and self.config.enable_outreach_evaluation:
                try:
                    print("📋 Evaluating candidates for outreach...")
                    outreach_summary = self._evaluate_candidates_for_outreach(candidates)
                    progress_tracker.log_outreach_evaluation(outreach_summary)
                except Exception as outreach_error:
                    print(f"⚠️  Outreach evaluation failed: {outreach_error}")
            
            if progress_tracker:
                progress_tracker.log_completion(candidates)
            
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
    
    def save_results(self, candidates: List[Dict[str, Any]], output_dir: str = "results") -> Dict[str, str]:
        """Step 4: Save recruitment results with error handling"""
        try:
            from runner.result_saver import save_recruitment_results
            
            search_params = {
                "query": self.query,
                "location": self.location,
                "limit": self.limit,
                "enhanced_prompting": self.enhanced_prompting,
                "streaming": self.streaming,
                "strategy_used": bool(self.strategy)
            }
            
            return save_recruitment_results(candidates, search_params, output_dir)
            
        except Exception as e:
            print(f"⚠️  Failed to save results: {e}")
            print(f"📊 Found {len(candidates)} candidates (unsaved)")
            return {
                "json_file": "Error: Could not save",
                "txt_file": "Error: Could not save",
                "candidates_count": len(candidates)
            }
    
    def _evaluate_candidates_for_outreach(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate extracted candidates for outreach and generate personalized messages"""
        try:
            from tools.candidate_outreach import bulk_evaluate_candidates_for_outreach
            
            # Extract the profile data for evaluation
            candidate_profiles = []
            for candidate in candidates:
                if isinstance(candidate, dict) and 'profile_details' in candidate:
                    profile_data = candidate['profile_details']
                    # Add search info for context
                    if 'search_info' in candidate:
                        profile_data['search_context'] = candidate['search_info']
                    candidate_profiles.append(profile_data)
                elif isinstance(candidate, dict) and 'profile_data' in candidate:
                    candidate_profiles.append(candidate['profile_data'])
                else:
                    candidate_profiles.append(candidate)
            
            # Extract technologies from strategy or use sensible defaults
            strategy_technologies = []
            if self.strategy:
                if "key_technologies" in self.strategy:
                    strategy_technologies = self.strategy["key_technologies"]
                elif "headline_analysis" in self.strategy and "tech_stack_signals" in self.strategy["headline_analysis"]:
                    strategy_technologies = self.strategy["headline_analysis"]["tech_stack_signals"]
            
            # Use strategy technologies or reasonable defaults
            required_technologies = strategy_technologies if strategy_technologies else ["Python", "JavaScript", "React", "Node.js", "AWS"]
            
            # Evaluate candidates for outreach using strategy-driven approach
            outreach_results = bulk_evaluate_candidates_for_outreach(
                candidates=candidate_profiles,
                position_title=self.query,  # Use actual user query
                location=self.location,     # Use actual user location
                required_technologies=required_technologies,  # From strategy
                experience_level="3-8 years",  # TODO: Could also extract from strategy
                strategy=self.strategy      # Pass full strategy for bonuses
            )
            
            # Save outreach results
            from tools.candidate_outreach import save_outreach_results
            outreach_file = save_outreach_results(outreach_results)
            outreach_results['saved_to'] = outreach_file
            
            return outreach_results
            
        except Exception as e:
            print(f"❌ Outreach evaluation error: {e}")
            return {"error": str(e), "candidates_evaluated": 0}
    
    def _build_strategy_enhanced_prompt(self) -> str:
        """Build prompt enhanced with strategy context - simplified to match original"""
        # Use the original working approach - just build enhanced prompt directly
        return RolePromptBuilder.build_enhanced_prompt(
            base_query=self.query,
            location=self.location,
            limit=self.limit,
            strategy=self.strategy
        )
    
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
    
    def _extract_candidates_from_result(self, result) -> List[Dict[str, Any]]:
        """Extract candidate data from agent result with deduplication"""
        candidates = []
        seen_profiles = set()  # Track seen profiles to avoid duplicates
        
        if hasattr(result, 'step_history'):
            # Process step history to find profile extractions (both extract_profile and extract_complete_profile)
            for step in result.step_history:
                # Handle both action and function attributes from AdalFlow steps
                action = getattr(step, 'action', None)
                function = getattr(step, 'function', None)
                observation = getattr(step, 'observation', None)
                
                # Get function name from action or function object
                func_obj = action or function
                func_name = getattr(func_obj, 'name', None) if func_obj else None
                
                if func_name == 'smart_candidate_search':
                    # Handle quality-driven search results
                    if observation and isinstance(observation, dict) and observation.get('quality_candidates'):
                        search_candidates = observation.get('quality_candidates', [])
                        print(f"🔍 Processing {len(search_candidates)} candidates from smart_candidate_search")
                        
                        for candidate in search_candidates:
                            if isinstance(candidate, dict):
                                url = candidate.get('url', 'Unknown URL')
                                if url not in seen_profiles:
                                    seen_profiles.add(url)
                                    # Convert quality search candidate to standard format
                                    candidates.append({
                                        "search_info": {
                                            "url": url,
                                            "headline_score": candidate.get('quality_assessment', {}).overall_score if candidate.get('quality_assessment') else 0
                                        },
                                        "profile_details": {
                                            "name": candidate.get('name', ''),
                                            "headline": candidate.get('headline', ''),
                                            "url": url,
                                            "quality_assessment": candidate.get('quality_assessment').__dict__ if candidate.get('quality_assessment') else {}
                                        }
                                    })
                
                elif func_name == 'extract_candidate_profiles':
                    # Handle batch profile extraction results
                    if observation and isinstance(observation, dict) and observation.get('results'):
                        batch_results = observation.get('results', [])
                        print(f"🔍 Processing {len(batch_results)} profiles from extract_candidate_profiles")
                        
                        for result in batch_results:
                            print(f"Extracted profile data: {result}")
                            if isinstance(result, dict) and result.get('profile_data'):
                                # Try to get URL from profile_data itself first
                                candidate_info = result.get('candidate_info', {})
                                profile_data = result.get('profile_data', {})
                                url = candidate_info.get('url', 'Unknown URL')
                                
                                if url not in seen_profiles:
                                    seen_profiles.add(url)
                                    # Create unique identifier for deduplication
                                    candidates.append({
                                        "search_info": {"url": url},
                                        "profile_details": profile_data
                                    })
        
        print(f"📊 Extracted {len(candidates)} unique candidates")
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