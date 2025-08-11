from typing import Any, Dict, List, Optional

from adalflow.components.agent.agent import Agent
from adalflow.components.agent.runner import Runner
from adalflow.components.model_client.openai_client import OpenAIClient
from adalflow.core.func_tool import FunctionTool

from config import AgentConfig, get_model_kwargs
from tools.web_nav import GoTool, ClickTool, TypeTool, KeyTool, JsTool, WaitTool
from tools.linkedin_auth import CheckAuthTool, NavigateLinkedInTool, PromptLoginTool
from tools.smart_search import SmartCandidateSearchTool, GetCollectedCandidatesTool
from tools.targeted_extraction import ExtractCandidateProfilesTool
from tools.candidate_evaluation import CandidateEvaluationTool
from tools.candidate_outreach import (
    CandidateOutreachGenerationTool,  # New agent tool for outreach generation
    SaveOutreachResultsTool  # Used by workflow manager to save outreach results
)
from tools.strategy_creation import CreateSearchStrategyTool


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
        self.tools = [
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
            # Modern agentic workflow tools (5-step process)
            CreateSearchStrategyTool,  # 1. Generate recruitment strategy
            SmartCandidateSearchTool,  # 2. Strategy-based candidate discovery & quality heap
            GetCollectedCandidatesTool,  # 2b. Access heap backup candidates (used in fallback)
            ExtractCandidateProfilesTool,  # 3. Extract detailed profiles from candidate heap
            CandidateEvaluationTool,  # 4. Comprehensive quality evaluation with fallback recommendations
            CandidateOutreachGenerationTool,  # 5. Generate personalized outreach messages
            # Legacy tools (used by workflow manager for backwards compatibility)
            SaveOutreachResultsTool,  # Save outreach results to file
        ]

        # Initialize Agent and Runner
        self.agent = Agent(
            name="LinkedInRecruiter",
            tools=self.tools,
            model_client=model_client,
            model_kwargs=model_kwargs,
            max_steps=max_steps,
            **kwargs,
        )
        self.runner = Runner(agent=self.agent, max_steps=max_steps)

    def call(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        return self.runner.call(prompt_kwargs={"input_str": query})

    async def acall(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        return await self.runner.acall(prompt_kwargs={"input_str": query})

    def add_tool(self, tool: FunctionTool) -> None:
        # Note: Tools are now included during agent initialization
        # This method kept for compatibility but no longer needed for strategy binding
        self.tools.append(tool)
        print(f"⚠️  Tool {getattr(tool.fn, '__name__', 'tool')} added to wrapper (agent already initialized with all tools)")
    