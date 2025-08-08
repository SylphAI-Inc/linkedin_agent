from adalflow.components.agent.agent import Agent
from adalflow.components.agent.runner import Runner
from adalflow.components.model_client.openai_client import OpenAIClient
from tools.web_nav import GoTool, ClickTool, TypeTool, KeyTool, JsTool, WaitTool
from tools.extract_profile import ExtractProfileTool
from config import AgentConfig, get_model_kwargs


class LinkedInAgent:
    """
    DummyAgent-style wrapper around AdalFlow Agent and Runner for LinkedIn tasks.
    Exposes call()/acall() and add_tool() and sets sensible defaults.
    """

    def __init__(self, model_client: OpenAIClient | None = None, model_kwargs: dict | None = None,
                 tools: list | None = None, max_steps: int | None = None, **kwargs) -> None:
        model_client = model_client or OpenAIClient()
        model_kwargs = model_kwargs or get_model_kwargs()
        max_steps = max_steps or AgentConfig().max_steps

        if tools is None:
            tools = [GoTool, ClickTool, TypeTool, KeyTool, JsTool, WaitTool, ExtractProfileTool]

        self.agent = Agent(
            name="LinkedInRecruiter",
            tools=tools,
            model_client=model_client,
            model_kwargs=model_kwargs,
            max_steps=max_steps,
            **kwargs,
        )
        self.runner = Runner(agent=self.agent, max_steps=max_steps)

    def call(self, query: str, context: dict | None = None):
        return self.runner.call(agent=self.agent, query=query, context=context or {})

    async def acall(self, query: str, context: dict | None = None):
        return await self.runner.acall(agent=self.agent, query=query, context=context or {})

    def add_tool(self, tool):
        self.agent.tools.append(tool)


def build_agent():
    """Back-compat builder returning (agent, runner)."""
    li = LinkedInAgent()
    return li.agent, li.runner
