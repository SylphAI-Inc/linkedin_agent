# AdalFlow Agent Project

A modern AI agent implementation using AdalFlow's new Agent and Runner architecture.
The goal is to automate linkedin candidate sourcing process. The manual process is as follows:

1. go to people search, fill in "full stack", select San Francisco Bay Area, click search
2. read each profile to see if they are a great candidate, if so, send a DM to poke their interest for interview

## 🚀 Quick Start for Engineers

This project uses AdalFlow's latest agent framework with separate Agent and Runner components for building autonomous AI systems.

### Prerequisites

- Python 3.12+
- Poetry (for dependency management)
- Access to an LLM provider (OpenAI, Anthropic, etc.)

## 📦 Installation

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Start Chrome with CDP

You can use our embedded launcher (vendor stub) or start Chrome yourself.

Option A: managed launcher

```bash
python vendor/claude_web/browser.py start
```

Option B: manual

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
```

### Run the LinkedIn agent

```bash
python runner/run_linkedin_agent.py \
	--query "full stack" \
	--location "San Francisco Bay Area" \
	--limit 5
```

Then load environment variables from `.env` at project root. See `.env` for defaults like CHROME_CDP_PORT and OPENAI settings.

## ▶️ Run Chrome (CDP) and the Agent

This repo vendors a minimal stub of claude-web under `vendor/claude_web`. For real browser control, swap in the actual project; the stub prints simulated actions for development.

1) Start Chrome with remote debugging (managed):

```bash
python vendor/claude_web/browser.py start
```

Or manually:

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
```

2) Run the agent end-to-end:

```bash
python -m runner.run_linkedin_agent --query "full stack" --location "San Francisco Bay Area" --limit 5
```

The default WebTool here is a dry-run CDP stub; it logs go/click/type/js. Replace `vendor/claude_web` with the real implementation to drive Chrome.

## 🏗️ Building Agents

This project follows AdalFlow's new Agent/Runner pattern. To learn how to build agents:

**📚 Official Tutorial**: https://adalflow.sylph.ai/new_tutorials/agents_runner.html

### Architecture Overview

- **Agent**: Handles planning and decision-making using Generator-based planner
- **Runner**: Manages execution, tool calling, and conversation flow
- **Tools**: Extend agent capabilities through FunctionTool wrappers

### Existing Research

Our team has done some research. We found two promissing approaches:
1. brower extension + our agent 
2. [brower use (playwright)](https://github.com/agi-inc/claude-web/blob/main/CLAUDE.md) + our agent

The second approach can be quickly hacked into `Claude` Coding agent. By giving the claude the `CLAUDE.md` file, it can use its bash command tool to run commands that call source code listed in the brower use repo.

Eventually, we should have our own agent that are capable of automating the manual task and easy to be adapted to any relevant linkedin/web task.
Feel free to use any approach you think is best.

### Process

1. initial project scoping and come with a plan
2. executing the plan 

## 🔗 Resources

- **AdalFlow Agent Tutorial**: https://adalflow.sylph.ai/new_tutorials/agents_runner.html
- **AdalFlow Documentation**: https://adalflow.sylph.ai/
- **GitHub Repository**: https://github.com/SylphAI-Inc/AdalFlow
- **Browser Use**: https://github.com/agi-inc/claude-web/