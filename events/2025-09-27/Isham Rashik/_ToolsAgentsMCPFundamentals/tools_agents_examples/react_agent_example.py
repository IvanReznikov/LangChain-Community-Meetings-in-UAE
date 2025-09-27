"""
ReAct Agent Demo
This script demonstrates the create_react_agent function using the word_counter tool.

ReAct (Reasoning and Acting) agents follow a structured approach:
1. Thought: Think about what to do
2. Action: Take an action (use a tool)
3. Observation: See the result
4. Repeat until task is complete
"""

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define the word_counter tool (same as before)
@tool
def word_counter(text: str) -> dict:
    """Count the number of words and characters in a text.
    
    Args:
        text: The text to analyze
        
    Returns:
        A dictionary with word count and character count
    """
    words = text.split()
    return {
        "word_count": len(words),
        "character_count": len(text),
        "character_count_no_spaces": len(text.replace(" ", ""))
    }


# Create the ReAct agent
def create_react_agent_demo():
    """Create a ReAct agent with the word_counter tool."""
    
    # Initialize the LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Define our tools
    tools = [word_counter]
    
    # Get the ReAct prompt from LangChain hub
    # This prompt includes the ReAct format: Thought, Action, Action Input, Observation
    prompt = hub.pull("hwchase17/react")
    
    # Create the ReAct agent
    agent = create_react_agent(llm, tools, prompt)
    
    # Create the executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,  # Shows the Thought -> Action -> Observation cycle
        handle_parsing_errors=True
    )
    
    return agent_executor


# Demonstration
if __name__ == "__main__":
    print("=== ReAct Agent Demo ===")
    print("Watch how the agent thinks through each step!\n")
    
    # Create the agent
    agent = create_react_agent_demo()
    
    # Example queries that show the ReAct pattern
    examples = [
        "How many words are in the sentence 'LangChain makes building AI apps easy'?",
        "Analyze this text: 'The quick brown fox jumps over the lazy dog'",
        "Count the characters in 'Hello, World!'",
    ]
    
    # Run examples
    for query in examples:
        print(f"\nQuery: {query}")
        print("-" * 50)
        result = agent.invoke({"input": query})
        print(f"\nResult: {result['output']}")
        print("=" * 60)
    
    print("\n✨ Notice how the agent follows the Thought -> Action -> Observation pattern!")
