import os
from typing import Any, Dict

# Provide a single place to add consistent tags/metadata for LangSmith
def run_config(jurisdiction: str) -> Dict[str, Any]:
    project = os.environ.get("LANGCHAIN_PROJECT", "Banking-RAG-Trust")
    return {
        "project_name": project,
        "run_name": "banking_trust_chain",
        "tags": ["banking", "rag", "compliance", f"jurisdiction:{jurisdiction}"],
        "metadata": {
            "jurisdiction": jurisdiction
        }
    }
