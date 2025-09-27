"""
Basic LangChain Tool Demo
This script demonstrates how to create and use simple tools in LangChain
"""

from langchain_core.tools import tool
from typing import Union
from dotenv import load_dotenv
load_dotenv()

# Example 1: Tool with string manipulation
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


# Demonstration of how to use the tools
if __name__ == "__main__":
    print("=== LangChain Tool Demonstration ===\n")
    
    # Using the word_counter tool
    print("Word Counter Tool:")
    sample_text = "LangChain makes it easy to build AI applications"
    result = word_counter.invoke({"text": sample_text})
    print(f"   Text: '{sample_text}'")
    print(f"   Analysis: {result}")
    print()
    
    # Showing tool schemas (useful for LLMs)
    print("Tool Schemas (for LLM integration):")
    print(f"   word_counter schema: {word_counter.__dict__}")
