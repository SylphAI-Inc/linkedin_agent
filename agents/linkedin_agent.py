from adalflow.components.agent.agent import Agent
from adalflow.components.agent.runner import Runner
from adalflow.components.model_client.openai_client import OpenAIClient
from tools.web_nav import GoTool, ClickTool, TypeTool, KeyTool, JsTool, WaitTool
from tools.extract_profile import ExtractProfileTool
from config import AgentConfig, get_model_kwargs


def build_agent():
    model_kwargs = get_model_kwargs()
    max_steps = AgentConfig().max_steps

    agent = Agent(
        name="LinkedInRecruiter",
    tools=[GoTool, ClickTool, TypeTool, KeyTool, JsTool, WaitTool, ExtractProfileTool],
    model_client=OpenAIClient(),
    model_kwargs=model_kwargs,
        max_steps=max_steps,
    )
    runner = Runner(agent=agent, max_steps=max_steps)
    return agent, runner
