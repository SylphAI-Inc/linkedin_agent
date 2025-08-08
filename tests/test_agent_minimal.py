#!/usr/bin/env python3
"""Minimal test of AdalFlow Agent + Runner to debug the parsing issue."""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adalflow.components.agent.agent import Agent
from adalflow.components.agent.runner import Runner
from adalflow.components.model_client.openai_client import OpenAIClient
from adalflow.core.func_tool import FunctionTool
from config import load_env, AgentConfig, get_model_kwargs

def simple_test_tool(message: str) -> str:
    """Simple test tool that just returns a message."""
    return f"Test response: {message}"

def main():
    print(" Testing minimal Agent + Runner setup...")
    
    # Load environment variables first
    load_env()
    print(" Environment loaded")
    
    try:
        # Create a simple tool
        test_tool = FunctionTool(fn=simple_test_tool)
        
        # Initialize model client and config
        model_client = OpenAIClient()
        model_kwargs = get_model_kwargs()
        max_steps = AgentConfig().max_steps
        
        print(" Model client and config loaded")
        
        # Create Agent
        agent = Agent(
            name="TestAgent",
            tools=[test_tool],
            model_client=model_client,
            model_kwargs=model_kwargs,
            max_steps=max_steps,
        )
        print(" Agent created successfully")
        
        # Create Runner
        runner = Runner(agent=agent, max_steps=max_steps)
        print(" Runner created successfully")
        
        # Test simple call
        print("\n Testing simple agent call...")
        result = runner.call(prompt_kwargs={"input_str": "Call the simple_test_tool with message 'hello world'"})
        
        print(f" Agent call completed!")
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")
        
        # Check for steps/history
        if hasattr(result, 'step_history'):
            print(f" Found step_history with {len(result.step_history)} steps")
        elif hasattr(result, 'steps'):
            print(f" Found steps with {len(result.steps)} steps") 
        else:
            print("️ No step history found")
            print(f"Available attributes: {dir(result)}")
        
        return result
        
    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()