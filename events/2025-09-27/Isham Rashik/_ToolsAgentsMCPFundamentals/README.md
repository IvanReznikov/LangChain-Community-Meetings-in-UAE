# LangChain Tools, Agents and MCP Fundamentals 

Welcome to the LangChain Tools, Agents and MCP Fundamentals! This project demonstrates the core concepts of LangChain, including tools, agents, and Model Context Protocol (MCP) integration.

## 📋 Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Workshop Sections](#workshop-sections)
  - [1. Tools and Agents](#1-tools-and-agents)
  - [2. MCP (Model Context Protocol) Demo](#2-mcp-model-context-protocol-demo)
- [Quick Start](#quick-start)
- [Resources](#resources)

## Overview

This workshop covers:

- **Tools**: Creating and using custom tools in LangChain
- **Agents**: Building intelligent agents that can decide when and how to use tools
- **MCP Integration**: Using Model Context Protocol to expose tools as services

## Project Structure

```text
langchain-workshop/fundamentals/
├── tools_agents_examples/        # Tools and agents demonstrations
│   ├── tool_basic_example.py     # Basic tool creation and usage
│   ├── tool_calling_agent_example.py  # Tool-calling agent demo
│   ├── react_agent_example.py    # ReAct agent with reasoning
│   ├── agent_comparison.md       # Comparison of different agent types
│   ├── setup_guide.md           # Setup instructions
│   └── requirements.txt         # Python dependencies
├── basic_mcp_example/           # MCP demonstration
│   ├── server.py               # MCP server implementation
│   ├── word_counter_example.py  # MCP client example
│   ├── client_langchain_adapter.py  # LangChain MCP adapter
│   ├── mcpServers.json         # MCP server configuration
│   └── word_counter_direct.py   # Direct MCP usage example
├── slides.html                  # Workshop presentation slides
└── README.md                   # This file
```

## Prerequisites

- Python 3.8 or higher
- OpenAI API key (for agent examples)
- Basic understanding of Python

## Workshop Sections

### 1. Tools and Agents

This section demonstrates the progression from basic tools to intelligent agents.

#### a) Basic Tool Usage (`tool_basic_example.py`)

Learn how to create simple tools using the `@tool` decorator:

```bash
cd tools_agents_examples
python tool_basic_example.py
```

**What you'll learn:**

- Creating tools with `@tool` decorator
- Tool schemas and metadata
- Manual tool invocation

#### b) Tool-Calling Agent (`tool_calling_agent_example.py`)

See how agents can automatically decide when to use tools:

```bash
python tool_calling_agent_example.py
```

**What you'll learn:**

- Creating agents with `create_tool_calling_agent()`
- Natural language interaction
- Automatic tool selection

#### c) ReAct Agent (`react_agent_example.py`)

Explore agents that show their reasoning process:

```bash
python react_agent_example.py
```

**What you'll learn:**

- ReAct (Reasoning + Acting) pattern
- Transparent decision-making process
- Step-by-step execution visibility

### 2. MCP (Model Context Protocol) Demo

This section shows how to expose tools as services using MCP.

#### a) Start the MCP Server

First, start the MCP server that exposes the word counter tool:

```bash
cd basic_mcp_example
python server.py
```

The server will start on `http://0.0.0.0:8113/mcp`

#### b) Run MCP Client Examples

In a new terminal, run the client examples:

```bash
# Using LangChain adapter
python word_counter_example.py

# Direct MCP usage
python word_counter_direct.py
```

**What you'll learn:**

- Creating MCP servers with FastMCP
- Connecting to MCP servers from LangChain
- Tool discovery and invocation over network

## Quick Start

For a quick demo of the core concepts:

1. **Basic Tool Demo**:

   ```bash
   cd tools_agents_examples
   python tool_basic_example.py
   ```

2. **Agent Demo**:

   ```bash
   python tool_calling_agent_example.py
   ```

3. **MCP Demo** (requires two terminals):

   ```bash
   # Terminal 1: Start server
   cd basic_mcp_example
   python server.py
   
   # Terminal 2: Run client
   python word_counter_example.py
   ```

## Key Concepts

### Tools

- Functions that can be used by agents
- Defined using `@tool` decorator
- Include descriptions for LLM understanding

### Agents

- **Tool-Calling Agent**: Decides when to use tools based on user input
- **ReAct Agent**: Shows reasoning process (Thought → Action → Observation)

### MCP (Model Context Protocol)

- Protocol for exposing tools as services
- Enables tool sharing across applications
- Supports multiple transport methods (HTTP, stdio)

## Troubleshooting

1. **ImportError**: Make sure you've installed all requirements:

   ```bash
   pip install -r tools_agents_examples/requirements.txt
   ```

2. **OpenAI API Error**: Ensure your `.env` file contains a valid API key

3. **MCP Connection Error**: Check that the MCP server is running and the URL in `mcpServers.json` is correct

## Resources

- [LangChain Documentation](https://python.langchain.com/)
- [MCP Specification](https://github.com/modelcontextprotocol/specification)
- [OpenAI API Keys](https://platform.openai.com/api-keys)