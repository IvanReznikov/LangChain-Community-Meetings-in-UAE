import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import httpx


# Load environment variables from .env file in project root
load_dotenv()
# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")

# 1) Define a prompt template with a placeholder for user input.
template = """You are a friendly, concise Dubai tour guide.
Provide a short, helpful overview aimed at a tourist who just arrived.
Keep it ~3-4 sentences, mention 2-3 top attractions and one quick travel tip.

User: {user_input}
Guide:"""

prompt = PromptTemplate(input_variables=["user_input"], template=template)


# 2) Initialize the chat LLM with custom HTTPX client to disable SSL verification (not for production use)
httpx_client = httpx.Client(verify=False)
llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.6, max_tokens=200, openai_api_key=api_key, http_client=httpx_client)


# Take user input from the terminal
user_input = input("Enter your question for the Dubai guide: ")
print("User:", user_input)

# Use the new pipeline syntax: prompt | llm

response = (prompt | llm).invoke({"user_input": user_input})

# The response is an AIMessage object; print its content
print("\nGuide:", response.content.strip())


