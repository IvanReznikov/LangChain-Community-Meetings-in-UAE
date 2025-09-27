"""
Simple Tool Calling Agent Demo
This script demonstrates how to create a basic agent that uses the word_counter tool
"""

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the word_counter tool from our basic example
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


# Create the agent
def create_simple_agent():
    """Create a simple tool-calling agent with the word_counter tool."""
    
    # Initialize the LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Define our tools
    tools = [word_counter]
    
    # Create the prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant that can analyze text using the word_counter tool."),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    # Create the agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    # Create the executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True  # Shows the agent's thought process
    )
    
    return agent_executor


# Demonstration
if __name__ == "__main__":
    print("=== Simple Tool-Calling Agent Demo ===\n")
    
    # Create the agent
    agent = create_simple_agent()
    
    # Example queries
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
