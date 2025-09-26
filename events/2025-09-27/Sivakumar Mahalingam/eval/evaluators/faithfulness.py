"""
Faithfulness evaluator: checks if the answer text is grounded in retrieved context.
This is a toy implementation for demo purposes.
"""

from typing import Dict, Any, List

def evaluate_faithfulness(run: Dict[str, Any]) -> Dict[str, Any]:
    """
    run: dict with keys {"answer": str, "citations": List[dict]}
    returns: dict with {"faithful": bool, "score": float}
    """
    answer = run.get("answer", "").lower()
    citations: List[Dict[str, Any]] = run.get("citations", [])

    # Naive heuristic: answer must contain at least one citation snippet keyword
    keywords = [c["snippet"].split()[0].lower() for c in citations if c.get("snippet")]
    faithful = any(kw in answer for kw in keywords)
    score = 1.0 if faithful else 0.0

    return {"faithful": faithful, "score": score}
