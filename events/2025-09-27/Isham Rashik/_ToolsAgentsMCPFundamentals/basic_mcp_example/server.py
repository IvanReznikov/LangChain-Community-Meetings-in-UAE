from fastmcp import FastMCP

mcp = FastMCP("Demo 🚀")

@mcp.tool
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

if __name__ == "__main__":
    # print("Running MCP on stdio")
    # mcp.run(transport="stdio")
    print("Running MCP on streamable-http")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8113)