# stop2_followup_cli.py
import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import httpx
import sys
import traceback
from langchain.memory import ConversationBufferMemory

# Load environment variables from .env file in project root
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("ERROR: OPENAI_API_KEY not found in environment. Set it in .env or env vars.")
    sys.exit(1)

# Prompt template now accepts a short conversation history plus the user's new input.
# We keep the original style (friendly, concise), but allow the model to see the last turns.
template = """You are a friendly, concise Dubai tour guide.
Provide a short, helpful overview aimed at a tourist who just arrived.
Keep it ~3-4 sentences, mention 2-3 top attractions and one quick travel tip.

{history}
User: {input}
Guide:"""

prompt = PromptTemplate(input_variables=["history", "input"], template=template)

# Initialize the chat LLM with custom HTTPX client to disable SSL verification (not for production use)
httpx_client = httpx.Client(verify=False)
llm = ChatOpenAI(
    model_name="gpt-4o-mini",
    temperature=0.6,
    max_tokens=250,
    openai_api_key=api_key,
    http_client=httpx_client,
)


def run_cli():
    print("=== Dubai Talking Guide — Version 3 (ConversationBufferMemory) ===")
    print("Type your question and press Enter.")
    print("Commands: /exit  -> quit,   /clear -> clear conversation history\n")

    # Use ConversationBufferMemory for automatic history
    memory = ConversationBufferMemory(return_messages=True, input_key="input", memory_key="history")

    try:
        while True:
            user_input = input("You: ").strip()
            if not user_input:
                continue

            # handle simple commands
            if user_input.lower() in ("/exit", "/quit"):
                print("Exiting. Goodbye")
                break
            if user_input.lower() == "/clear":
                memory.clear()
                print("Conversation history cleared.")
                continue

            # Get current conversation history from memory
            history = memory.load_memory_variables({"input": user_input})["history"]

            # invoke pipeline: use prompt | llm style
            invoke_input = {"history": history, "input": user_input}
            try:
                response = (prompt | llm).invoke(invoke_input)
            except Exception as e:
                print("Error while calling the model:", str(e))
                traceback.print_exc()
                continue

            assistant_text = getattr(response, "content", None) or str(response)
            print("\nGuide:", assistant_text.strip(), "\n")

            # Save user and assistant messages to memory
            memory.save_context({"input": user_input}, {"output": assistant_text.strip()})

    finally:
        try:
            httpx_client.close()
        except Exception:
            pass

if __name__ == "__main__":
    run_cli()
