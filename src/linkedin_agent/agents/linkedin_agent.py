from typing import Any, Dict, Optional

from adalflow.components.agent.agent import Agent
from adalflow.components.agent.runner import Runner
from adalflow.components.model_client.openai_client import OpenAIClient

from ..config import AgentConfig, get_model_kwargs
from ..tools.smart_search import SmartCandidateSearchTool
from ..tools.targeted_extraction import ExtractCandidateProfilesTool
from ..tools.candidate_evaluation import CandidateEvaluationTool
from ..tools.candidate_outreach import (
    CandidateOutreachGenerationTool,  # New agent tool for outreach generation
    SaveOutreachResultsTool  # Used by workflow manager to save outreach results
)


class LinkedInAgent:
    """
    LinkedIn agent following the same design as src/dummy_agent.py:
    - Encapsulates an AdalFlow Agent and Runner
    - Exposes call()/acall() and add_tool()
    - Provides sensible default tools (CDP nav + extract_profile)
    """

    def __init__(
        self,
        model_client: Optional[OpenAIClient] = None,
        model_kwargs: Optional[Dict[str, Any]] = None,
        max_steps: Optional[int] = None,
        role_desc: Optional[str] = None,
        **kwargs,
    ) -> None:
        # Defaults
        model_client = model_client or OpenAIClient()
        model_kwargs = model_kwargs or get_model_kwargs()
        max_steps = max_steps or AgentConfig().max_steps

        # Prepare default tools if none provided
        self.tools = [
            SmartCandidateSearchTool,  # 1. Smart candidate discovery with quality scoring
            ExtractCandidateProfilesTool,  # 2. Extract detailed profiles from search results
            CandidateEvaluationTool,  # 3. Comprehensive quality evaluation with fallback recommendations
            CandidateOutreachGenerationTool,  # 4. Generate personalized outreach messages
            SaveOutreachResultsTool,  # Save outreach results to file
        ]

        # Get default role description if not provided
        if not role_desc:
            from ..utils.role_prompts import get_agent_role
            role_desc = get_agent_role()
        
        # Initialize Agent and Runner
        self.agent = Agent(
            name="LinkedInRecruiter",
            tools=self.tools,
            model_client=model_client,
            model_kwargs=model_kwargs,
            max_steps=max_steps,
            role_desc=role_desc,
            **kwargs,
        )
        self.runner = Runner(agent=self.agent, max_steps=max_steps)

    def call(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        return self.runner.call(prompt_kwargs={"input_str": query})

    async def acall(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        return await self.runner.acall(prompt_kwargs={"input_str": query})
    