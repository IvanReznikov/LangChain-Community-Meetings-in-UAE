import asyncio
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient

def extract_text(chunk):
    """Extract text content from various chunk formats."""
    # Handle direct string
    if isinstance(chunk, str):
        return chunk
    
    # Handle dictionary with common content fields
    if isinstance(chunk, dict):
        for key in ("content", "text", "output", "delta"):
            if key in chunk and isinstance(chunk[key], str):
                return chunk[key]
    
    # Handle objects with content attribute
    if hasattr(chunk, "content") and isinstance(chunk.content, str):
        return chunk.content
    
    return None

async def main():
    # Initialize environment and MCP components
    load_dotenv()
    client = MCPClient.from_config_file("mcpServers.json")
    llm = ChatOpenAI(model="gpt-4.1")
    agent = MCPAgent(llm=llm, client=client, max_steps=30)
    
    # Query for Tesla stock price
    query = "Count the words and characters in this text: 'The quick brown fox jumps over the lazy dog.'"
    
    try:
        # Stream the response and print chunks as they arrive
        async for chunk in agent.stream(query):
            text = extract_text(chunk)
            if text:
                print(text, end="", flush=True)
        print()  # Add newline after streaming completes
        
    except Exception as e:
        # If streaming fails, try a direct invoke
        print(f"Streaming failed: {e}")
        try:
            result = await agent.ainvoke(query)
            text = extract_text(result) or str(result)
            print(text)
        except Exception as e:
            print(f"Query failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())