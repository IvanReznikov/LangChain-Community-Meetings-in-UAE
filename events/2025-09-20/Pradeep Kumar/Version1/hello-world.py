
import os
from dotenv import load_dotenv
import httpx
from openai import OpenAI


# Load environment variables from .env file in current directory
load_dotenv()

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")


# Create an HTTPX client with SSL verification disabled
httpx_client = httpx.Client(verify=False)

# Initialize OpenAI client with custom HTTPX client
client = OpenAI(api_key=api_key, http_client=httpx_client)

# Ask for user input in the terminal
user_message = input("Enter your message: ")

# Make a request to the model with the user's message
response = client.chat.completions.create(
    model="gpt-4o-mini",  
    messages=[
        {"role": "system", "content": "You are a helpful tour guide."},
        {"role": "user", "content": user_message}
    ]
)

# Print the guide's first response
print(response.choices[0].message.content)
