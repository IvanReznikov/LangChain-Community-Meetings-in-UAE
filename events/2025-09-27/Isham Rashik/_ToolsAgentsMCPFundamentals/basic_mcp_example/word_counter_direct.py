# Direct word counter (without MCP server)
# This provides the same functionality as the word counter MCP

def count_words_and_chars(text):
    """Count words and characters in the given text"""
    # Count words by splitting on whitespace
    words = text.split()
    word_count = len(words)
    
    # Count total characters (including spaces)
    char_count = len(text)
    
    # Count characters without spaces
    char_count_no_spaces = len(text.replace(" ", ""))
    
    return {
        "word_count": word_count,
        "character_count": char_count,
        "character_count_no_spaces": char_count_no_spaces,
        "words": words
    }

def main():
    # The text to analyze
    text = "hello how are you"
    
    print(f"Analyzing text: '{text}'")
    print("-" * 50)
    
    # Count words and characters
    result = count_words_and_chars(text)
    
    # Display results
    print(f"Word count: {result['word_count']}")
    print(f"Character count (with spaces): {result['character_count']}")
    print(f"Character count (without spaces): {result['character_count_no_spaces']}")
    print(f"Individual words: {', '.join(result['words'])}")
    
    print("\n" + "=" * 50)
    print("\nNote: The word counter MCP server would provide this same")
    print("functionality but as a tool that can be used by AI agents.")
    print("\nTo use the MCP server when it's available:")
    print("1. Ensure the server is running at http://172.22.225.23:8019/mcp")
    print("2. Run the word_counter_example.py script")
    print("3. The AI agent will use the MCP tool to count words")

if __name__ == "__main__":
    main()
