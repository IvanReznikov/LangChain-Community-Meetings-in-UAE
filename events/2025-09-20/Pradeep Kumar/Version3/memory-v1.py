# stop2_followup_cli.py
import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import httpx
import sys
import traceback

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

Conversation history (most recent first):
{history}

User: {user_input}
Guide:"""

prompt = PromptTemplate(input_variables=["history", "user_input"], template=template)

# Initialize the chat LLM with custom HTTPX client to disable SSL verification (not for production use)
httpx_client = httpx.Client(verify=False)
llm = ChatOpenAI(
    model_name="gpt-4o-mini",
    temperature=0.6,
    max_tokens=250,
    openai_api_key=api_key,
    http_client=httpx_client,
)

def format_history_as_text(history_list, max_turns=6):
    """
    Convert history list of (role, text) tuples into a string for the prompt.
    We include up to `max_turns` most recent user/assistant pairs to keep prompt short.
    """
    if not history_list:
        return "No prior conversation."

    # Build strings like: "User: ...\nGuide: ..."
    pairs = []
    # history_list is list of dicts: {"role":"user"/"assistant", "content": "..."}
    # We'll iterate from most recent to older and collect up to max_turns entries
    trimmed = history_list[-(max_turns * 2):]  # each turn has 2 entries (user+assistant) generally
    for entry in trimmed:
        role = entry["role"]
        text = entry["content"].strip()
        if role == "user":
            pairs.append(f"User: {text}")
        elif role == "assistant":
            pairs.append(f"Guide: {text}")
        else:
            pairs.append(f"{role.capitalize()}: {text}")

    # Show most recent first
    return "\n".join(reversed(pairs))

def run_cli():
    print("=== Dubai Talking Guide — Version 3 (Memory demo) ===")
    print("Type your question and press Enter.")
    print("Commands: /exit  -> quit,   /clear -> clear conversation history\n")

    # in-memory conversation list
    # each item: {"role": "user"|"assistant", "content": "..."}
    history = []

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
                history = []
                print("Conversation history cleared.")
                continue

            # prepare history text to send to model
            history_text = format_history_as_text(history, max_turns=6)

            # invoke pipeline: use prompt | llm style
            invoke_input = {"history": history_text, "user_input": user_input}
            try:
                response = (prompt | llm).invoke(invoke_input)
            except Exception as e:
                print("Error while calling the model:", str(e))
                # Optional: print trace for debugging in demo environment
                traceback.print_exc()
                continue

            # response is an AIMessage-like object; get its textual content
            # Many langchain wrappers return response.content
            assistant_text = getattr(response, "content", None) or str(response)

            # Print assistant reply and append to history
            print("\nGuide:", assistant_text.strip(), "\n")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": assistant_text.strip()})

    finally:
        # cleanup httpx client
        try:
            httpx_client.close()
        except Exception:
            pass

if __name__ == "__main__":
    run_cli()
