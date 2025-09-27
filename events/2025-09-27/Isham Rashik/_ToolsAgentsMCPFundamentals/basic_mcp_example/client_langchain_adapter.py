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
    print("Initializing MCP client")
    with open('mcpServers.json', 'r') as f:
        mcp_servers = json.load(f)
    
    client = MultiServerMCPClient(mcp_servers["mcpServers"])
    
    # Get tools from the MCP server
    tools = await client.get_tools()

    print("Tools:")
    print(tools)
    print("\n" + "="*50 + "\n")

    # Create agent with proper model initialization
    # Note: Make sure you have OPENAI_API_KEY environment variable set
    model = ChatOpenAI(model="gpt-4.1", temperature=0)
    agent = create_react_agent(model, tools)
    
    # Example 1: Use the word counter tool appropriately
    text_analysis_response = await agent.ainvoke({
        "messages": [("user", "Count the words and characters in this text: 'The quick brown fox jumps over the lazy dog.'")]
    })
    print("Text Analysis Response:")
    print(text_analysis_response["messages"][-1].content)
    print("\n" + "="*50 + "\n")

    # Example 2: Use the brave-search tool appropriately
    # brave_search_response = await agent.ainvoke({
    #     "messages": [("user", "What is the present price of Tesla stock?")]
    # })
    # print("Brave Search Response:")
    # print(brave_search_response["messages"][-1].content)
    # print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(main())