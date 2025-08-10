from typing import Any, Dict, List, Optional

from adalflow.components.agent.agent import Agent
from adalflow.components.agent.runner import Runner
from adalflow.components.model_client.openai_client import OpenAIClient
from adalflow.core.func_tool import FunctionTool

from config import AgentConfig, get_model_kwargs
from tools.web_nav import GoTool, ClickTool, TypeTool, KeyTool, JsTool, WaitTool
from tools.people_search import SearchPeopleTool
from tools.linkedin_auth import CheckAuthTool, NavigateLinkedInTool, PromptLoginTool
from tools.profile_extractor import ExtractCompleteProfileTool
# from tools.candidate_scorer import ScoreCandidateTool, ScoreMultipleCandidatesTool  # Commented out - using new workflow
from tools.smart_search import SmartCandidateSearchTool, GetCollectedCandidatesTool, ClearCandidateCollectionTool
from tools.targeted_extraction import ExtractCandidateProfilesTool, GetExtractionSummaryTool


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
        tools: Optional[List[Any]] = None,
        max_steps: Optional[int] = None,
        **kwargs,
    ) -> None:
        # Defaults
        model_client = model_client or OpenAIClient()
        model_kwargs = model_kwargs or get_model_kwargs()
        max_steps = max_steps or AgentConfig().max_steps

        # Prepare default tools if none provided
        if tools is None:
            tools = [
                # Navigation tools
                GoTool,
                ClickTool,
                TypeTool,
                KeyTool,
                JsTool,
                WaitTool,
                # LinkedIn-specific tools
                CheckAuthTool,
                NavigateLinkedInTool, 
                PromptLoginTool,
                # Profile extraction tools (legacy - for fallback only)
                # ExtractCompleteProfileTool,  # Commented out - using targeted extraction now
                # Search and scoring tools (legacy)
                # SearchPeopleTool,  # Commented out - using smart search now
                # ScoreCandidateTool,  # Commented out - using new workflow
                # ScoreMultipleCandidatesTool,  # Commented out - using new workflow
                # New workflow tools
                SmartCandidateSearchTool,  # Strategy-based candidate discovery
                GetCollectedCandidatesTool,  # Get quality candidate URLs
                ClearCandidateCollectionTool,  # Clear candidate collection
                ExtractCandidateProfilesTool,  # Extract profiles from URLs
                GetExtractionSummaryTool,  # Extraction status summary
            ]

        # Initialize Agent and Runner
        self.agent = Agent(
            name="LinkedInRecruiter",
            tools=tools,
            model_client=model_client,
            model_kwargs=model_kwargs,
            max_steps=max_steps,
            **kwargs,
        )
        self.runner = Runner(agent=self.agent, max_steps=max_steps)

    def call(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        # Installed AdalFlow Runner expects prompt_kwargs only; context not supported in this version
        return self.runner.call(prompt_kwargs={"input_str": query})

    async def acall(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        return await self.runner.acall(prompt_kwargs={"input_str": query})

    def add_tool(self, tool: FunctionTool) -> None:
        self.agent.tools.append(tool)
