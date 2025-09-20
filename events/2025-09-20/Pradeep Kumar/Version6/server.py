
import os
from dotenv import load_dotenv
import httpx
from fastapi import FastAPI
from langserve import add_routes
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# Load environment variables from .env file in current directory
load_dotenv()

# Set environment variables to disable SSL verification for OpenAI/httpx
os.environ["OPENAI_API_VERIFY_SSL"] = "false"
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""

# Patch both sync and async HTTPX client creators in langchain_openai to use verify=False
import langchain_openai.chat_models.base as openai_base
def patched_get_httpx_client(*args, **kwargs):
    return httpx.Client(verify=False)
def patched_get_async_httpx_client(*args, **kwargs):
    return httpx.AsyncClient(verify=False)
openai_base._get_httpx_client = patched_get_httpx_client
openai_base._get_async_httpx_client = patched_get_async_httpx_client

app = FastAPI()

# Define the prompt and model
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful tour guide."),
    ("user", "{input}")
])
model = ChatOpenAI(model="gpt-4o-mini")
chain = prompt | model

# Add a /guide endpoint
add_routes(app, chain, path="/guide")