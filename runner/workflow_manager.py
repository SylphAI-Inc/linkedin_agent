"""
LinkedIn Recruitment Workflow Manager
Handles the orchestration of the recruitment process in clean, decoupled steps
"""
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path
import json

# from tools.people_search import create_search_strategy  # Not used in original working flow
from src.linkedin_agent import LinkedInAgent
from utils.role_prompts import RolePromptBuilder


class LinkedInWorkflowManager:
    """Manages the LinkedIn recruitment workflow with clean separation of concerns"""
    
    def __init__(self, query: str, location: str, limit: int, **kwargs):
        self.query = query
        self.location = location
        self.limit = limit
        self.role_type = kwargs.get('role_type') or RolePromptBuilder.detect_role_type(query)
        self.enhanced_prompting = kwargs.get('enhanced_prompting', True)
        self.streaming = kwargs.get('streaming', True)
        
        # Initialize components
        self.agent = None
        self.strategy = None
        self.results = []
        
    def create_recruitment_strategy(self) -> Dict[str, Any]:
        """Step 1: Create comprehensive search strategy (DISABLED - not in original flow)"""
        print(f"🎯 Skipping strategy creation - using original flow approach")
        print(f"📍 Location: {self.location}")
        print(f"🎭 Role type: {self.role_type.replace('_', ' ').title()}")
        
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
    
    def execute_search_workflow(self, progress_tracker=None) -> List[Dict[str, Any]]:
        """Step 3: Execute the complete search workflow"""
        print(f"🔍 Starting recruitment workflow...")
        print(f"📊 Target: {self.limit} candidates")
        
        try:
            agent, prompt = self.initialize_agent()
            
            if progress_tracker:
                progress_tracker.start_workflow()
            
            # Execute agent workflow
            result = agent.call(query=prompt)
            
            # Process results based on agent execution
            candidates = self._extract_candidates_from_result(result)
            
            if progress_tracker:
                progress_tracker.log_completion(candidates)
            
            self.results = candidates
            print(f"✅ Workflow completed: {len(candidates)} candidates found")
            
            return candidates
            
        except Exception as e:
            print(f"❌ Workflow failed: {e}")
            # Try fallback direct execution
            return self._execute_fallback_workflow()
    
    def save_results(self, candidates: List[Dict[str, Any]], output_dir: str = "results") -> Dict[str, str]:
        """Step 4: Save recruitment results"""
        from runner.result_saver import save_recruitment_results
        
        search_params = {
            "query": self.query,
            "location": self.location,
            "limit": self.limit,
            "role_type": self.role_type,
            "enhanced_prompting": self.enhanced_prompting,
            "streaming": self.streaming,
            "strategy_used": bool(self.strategy)
        }
        
        return save_recruitment_results(candidates, search_params, output_dir)
    
    def _build_strategy_enhanced_prompt(self) -> str:
        """Build prompt enhanced with strategy context - simplified to match original"""
        # Use the original working approach - just build enhanced prompt directly
        return RolePromptBuilder.build_enhanced_prompt(
            base_query=self.query,
            location=self.location,
            limit=self.limit,
            role_type=self.role_type
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
                "alternative_titles": self.query.lower().split(),
                "seniority_keywords": ["senior", "staff", "principal", "lead"],
                "company_indicators": ["@", "at"],
                "tech_stack_signals": ["python", "react", "java", "aws"],
                "role_relevance_keywords": self.query.lower().split()
            },
            "profile_evaluation_context": {
                "focus_areas": ["work experience", "technical skills", "career progression"],
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
                
                # Check for profile extraction functions
                if (func_name in ['extract_profile', 'extract_complete_profile'] and 
                    observation and isinstance(observation, dict)):
                    
                    profile_data = observation
                    if profile_data.get('name'):
                        # Try to get URL from profile_data itself first (most reliable)
                        url = profile_data.get('url', 'Unknown URL')
                        
                        # If no URL in profile data, try step history
                        if url == 'Unknown URL':
                            url = self._extract_url_from_step_history(result.step_history, step)
                        
                        # Create unique identifier for deduplication
                        # Use URL if available, otherwise use name + headline combination
                        if url != 'Unknown URL':
                            profile_id = url.strip().rstrip('/').lower()
                        else:
                            profile_id = f"{profile_data.get('name', '').lower()}_{profile_data.get('headline', '').lower()}"
                        
                        # Skip if we've already seen this profile
                        if profile_id in seen_profiles:
                            print(f"🔄 Skipping duplicate profile: {profile_data.get('name', 'Unknown')} ({url})")
                            continue
                        
                        seen_profiles.add(profile_id)
                        candidates.append({
                            "search_info": {"url": url},
                            "profile_details": profile_data
                        })
        
        print(f"📊 Extracted {len(candidates)} unique candidates (filtered {len(seen_profiles) - len(candidates)} duplicates)")
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
            from tools.profile_extractor import extract_complete_profile
            from tools.web_nav import go
            
            # Direct search
            search_results = search_people(self.query, self.location, self.limit)
            
            if search_results.get("count", 0) > 0:
                candidates = []
                for i, candidate in enumerate(search_results.get("results", [])[:self.limit]):
                    print(f"📝 Extracting profile {i+1}: {candidate['name']}")
                    go(candidate["url"])
                    profile_data = extract_complete_profile()
                    candidates.append({"search_info": candidate, "profile_details": profile_data})
                
                return candidates
            else:
                print("❌ No candidates found in fallback search")
                return []
                
        except Exception as e:
            print(f"❌ Fallback workflow also failed: {e}")
            return []