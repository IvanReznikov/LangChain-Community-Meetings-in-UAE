# Agent Types Comparison

## 1. Basic Tool (tool_basic_example.py)
- **What it is**: Just a function decorated with `@tool`
- **Usage**: You manually call the tool
- **Example**: `word_counter.invoke({"text": "Hello"})`

## 2. Tool-Calling Agent (tool_calling_agent_example.py)
- **What it is**: An agent that can decide when to use tools
- **Usage**: Natural language input, agent decides if/when to use tools
- **Key function**: `create_tool_calling_agent()`
- **Example**: Ask "How many words in 'Hello'?" → Agent uses word_counter

## 3. ReAct Agent (react_agent_example.py)
- **What it is**: An agent that follows Thought → Action → Observation pattern
- **Usage**: More structured reasoning, shows thinking process
- **Key function**: `create_react_agent()`
- **Example**: Same query, but you see the agent's reasoning steps

## Key Differences

### Tool-Calling Agent
```
User: "Count words in 'Hello World'"
Agent: [Calls word_counter] → Returns result
```

### ReAct Agent
```
User: "Count words in 'Hello World'"
Agent: 
  Thought: I need to count words in the given text
  Action: word_counter
  Action Input: {"text": "Hello World"}
  Observation: {"word_count": 2, ...}
  Thought: I now have the word count
  Final Answer: The text has 2 words
```

Both achieve the same result, but ReAct shows its reasoning process!
