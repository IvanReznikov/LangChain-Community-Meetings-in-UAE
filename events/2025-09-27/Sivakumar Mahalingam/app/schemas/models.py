from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class Citation(BaseModel):
    title: str
    policy_id: str
    jurisdiction: str
    effective_from: str
    effective_to: str
    snippet: str

class AnswerPayload(BaseModel):
    answer: str = Field(..., description="Final, compliant answer.")
    jurisdiction: str
    policy_pack_version: str
    citations: List[Citation]
    redactions: List[Dict[str, str]]
    risk_flags: List[str]
    disclaimer: str
    run_metadata: Dict[str, Any]

class AskRequest(BaseModel):
    question: str
    jurisdiction: Optional[str] = Field(default="UAE", description="e.g., UAE, EU, US")
