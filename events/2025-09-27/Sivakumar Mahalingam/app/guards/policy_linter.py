from typing import List
from app.policies.policy_store import BANNED_PHRASES

def policy_lint(text: str) -> List[str]:
    violations = []
    for banned in BANNED_PHRASES:
        if banned.lower() in text.lower():
            violations.append(f"Contains banned phrase: '{banned}'")
    return violations
