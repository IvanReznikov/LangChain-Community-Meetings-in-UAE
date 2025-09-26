import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Load .env from repo root (works with uvicorn reload, notebooks, tests)
env_path = find_dotenv(usecwd=True)
if not env_path:
    # fallback: try <repo>/ .env relative to this file
    env_path = str(Path(__file__).resolve().parents[1] / ".env")
load_dotenv(env_path, override=False)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGCHAIN_TRACING_V2=os.getenv("LANGCHAIN_TRACING_V2")
LANGCHAIN_API_KEY=os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT=os.getenv("LANGCHAIN_PROJECT")

def require_openai_key() -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY not set. Create a .env at repo root or export it in the shell."
        )
    return OPENAI_API_KEY
