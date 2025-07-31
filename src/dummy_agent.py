from adalflow.components.agent.agent import Agent
from adalflow.components.agent.runner import Runner
from adalflow.core.model_client import ModelClient
from adalflow.core.func_tool import FunctionTool
from typing import Any, Dict, List, Optional


def example_tool(query: str) -> str:
    """Example tool function for the agent.
    
    Args:
        query: The input query to process
        
    Returns:
        A simple response
    """
    return f"Processed: {query}"


class DummyAgent:
    """A dummy agent implementation using AdalFlow's new Agent and Runner components.
    
    This implementation follows the new adalflow tutorial pattern with separate
    Agent (for planning/decision-making) and Runner (for execution) components.
    """
    
    def __init__(
        self,
        model_client: ModelClient,
        model_kwargs: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Any]] = None,
        max_steps: int = 5,
        **kwargs
    ):
        """
        Initialize the dummy agent with Agent and Runner components.
        
        Args:
            model_client: The model client for LLM interactions
            model_kwargs: Additional model configuration
            tools: List of tools available to the agent
            max_steps: Maximum number of steps for the agent
        """
        
        # Prepare tools
        if tools is None:
            # Create a default tool as an example
            example_func_tool = FunctionTool(
                fn=example_tool,
            )
            tools = [example_func_tool]
        
        # Initialize the Agent component for planning and decision-making
        self.agent = Agent(
            name="DummyAgent",
            tools=tools,
            model_client=model_client,
            model_kwargs=model_kwargs or {},
            max_steps=max_steps,
            **kwargs
        )
        
        # Initialize the Runner component for execution
        self.runner = Runner(agent=self.agent, max_steps=max_steps)
    
    def call(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute the agent with a query using the Runner.
        
        Args:
            query: The user query to process
            context: Optional context information
            
        Returns:
            RunnerResult object with execution details
        """
        # Use the runner to execute the agent
        result = self.runner.call(
            agent=self.agent,
            query=query,
            context=context or {}
        )
        return result
    
    async def acall(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Async version of call method.
        
        Args:
            query: The user query to process
            context: Optional context information
            
        Returns:
            RunnerResult object with execution details
        """
        result = await self.runner.acall(
            agent=self.agent,
            query=query,
            context=context or {}
        )
        return result
    
    def add_tool(self, tool: Any) -> None:
        """
        Add a tool to the agent.
        
        Args:
            tool: The tool to add
        """
        self.agent.tools.append(tool)
    



