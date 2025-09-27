# MCP Client example demonstrating word counter tool
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import json
from dotenv import load_dotenv
load_dotenv()

async def main():
    # Initialize MCP client with word counter server
    print("Initializing MCP client...")
    with open('mcpServers.json', 'r') as f:
        mcp_servers = json.load(f)
    
    client = MultiServerMCPClient(mcp_servers["mcpServers"])
    
    # Get tools from the MCP server
    tools = await client.get_tools()
    
    print("Available tools from MCP server:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")
    print("\n" + "="*50 + "\n")
    
    # Create agent with the model
    model = ChatOpenAI(model="gpt-4", temperature=0)
    agent = create_react_agent(model, tools)
    
    # Count words in the provided text
    text_to_analyze = "hello how are you"
    print(f"Analyzing text: '{text_to_analyze}'")
    print("Sending request to word counter MCP...\n")
    
    # Send the request to count words
    response = await agent.ainvoke({
        "messages": [("user", f"Count the words and characters in this text: '{text_to_analyze}'")]
    })
    
    # Print the result
    print("Word Counter Result:")
    print(response["messages"][-1].content)
    print("\n" + "="*50 + "\n")
    
    # Also directly count to verify
    word_count = len(text_to_analyze.split())
    char_count = len(text_to_analyze)
    print(f"Direct verification: {word_count} words, {char_count} characters")

if __name__ == "__main__":
    asyncio.run(main())
