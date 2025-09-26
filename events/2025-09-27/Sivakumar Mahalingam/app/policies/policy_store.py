import json
import os
from typing import Dict, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PACK_PATH = os.path.join(BASE_DIR, "app", "policies", "packs", "policy_pack.json")

with open(PACK_PATH, "r", encoding="utf-8") as f:
    _PACK: Dict[str, Any] = json.load(f)

POLICY_PACK_VERSION: str = _PACK["policy_pack_version"]
BANNED_PHRASES = _PACK["banned_phrases"]
REQUIRED_DISCLAIMER = _PACK["required_disclaimer"]
_JURISDICTION_PROMPTS = _PACK["jurisdiction_prompts"]

def get_jurisdiction_directive(jurisdiction: str) -> str:
    return _JURISDICTION_PROMPTS.get(jurisdiction, f"Follow local regulations for {jurisdiction}.")
