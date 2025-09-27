# Simple Tool-Calling Agent Demo

## Overview

This demo shows how to create a basic LangChain agent that can use tools. The agent:
- Understands what the user wants
- Decides when to use the word_counter tool
- Executes the tool and returns results

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up OpenAI API Key

Create a `.env` file and add your OpenAI API key:
```
OPENAI_API_KEY=your-api-key-here
```

Get your API key from: https://platform.openai.com/api-keys

### 3. Run the Demo

```bash
python tool_calling_agent_example.py
```

## How It Works

1. We define a `word_counter` tool that analyzes text
2. We create an agent that has access to this tool
3. The agent decides when and how to use the tool based on user queries

## Example Output

When you ask "How many words are in 'Hello World'?", the agent will:
1. Recognize it needs to count words
2. Call the word_counter tool with the text
3. Return the results in a friendly format
