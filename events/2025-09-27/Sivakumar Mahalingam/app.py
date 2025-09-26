import os
import re
import json
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple

from fastapi import FastAPI, Body, Query
from fastapi.responses import JSONResponse

from pydantic import BaseModel, Field
from dotenv import load_dotenv

# LangChain / OpenAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

load_dotenv()
# ---------- Env / LangSmith ----------
# Required:
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
# Optional (for tracing):
LANGCHAIN_TRACING_V2=os.getenv("LANGCHAIN_TRACING_V2")
LANGCHAIN_API_KEY=os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT=os.getenv("LANGCHAIN_PROJECT")
# os.environ.setdefault("LANGCHAIN_PROJECT", "Banking-RAG-Trust")

# ---------- Sample “Policy Pack” (versioned, jurisdiction-aware) ----------
POLICY_PACK_VERSION = "2025-09-01"
POLICY_RULES = {
    "banned_phrases": [
        "guaranteed approval",
        "we can waive any regulation",
        "ignore policy"
    ],
    "required_disclaimer": "This response is based on current bank policy and may vary by jurisdiction.",
    "jurisdiction_prompts": {
        "UAE": "Follow UAE Central Bank guidance and local KYC rules.",
        "EU": "Follow EBA and GDPR requirements; never reveal raw PII in outputs.",
        "US": "Follow FFIEC guidance; avoid sharing full SSN or full PAN."
    }
}

# ---------- Tiny Knowledge Base (SOP/policy snippets) ----------
RAW_DOCS = [
    {
        "title": "KYC_Onboarding_SOP",
        "jurisdiction": "UAE",
        "effective_from": "2025-06-01",
        "effective_to": "2026-06-01",
        "policy_id": "KYC-ONB-001",
        "text": """Customer onboarding requires valid Emirates ID and proof of address.
Never store raw Emirates ID in model prompts. Mask ID as EID-****1234.
For mismatched addresses, escalate to Level-2 KYC per SOP KYC-ONB-001 section 4."""
    },
    {
        "title": "Fee_Disclosure_Policy",
        "jurisdiction": "UAE",
        "effective_from": "2025-01-01",
        "effective_to": "2026-01-01",
        "policy_id": "FEE-DSC-007",
        "text": """All fees must be disclosed prior to account opening.
For refund eligibility, cite section 3.2 and provide web reference to official tariff page.
Do not promise fee waivers. Avoid phrases like 'guaranteed approval'."""
    },
    {
        "title": "GDPR_PII_Handling",
        "jurisdiction": "EU",
        "effective_from": "2024-01-01",
        "effective_to": "2026-01-01",
        "policy_id": "PII-GDPR-101",
        "text": """Under GDPR, do not expose raw PII (full PAN/SSN/IBAN). Mask PAN as **** **** **** 1234.
PII must be removed from LLM prompts unless strictly necessary. Log redaction maps separately."""
    }
]

# ---------- Simple PII patterns (demo-grade) ----------
PII_PATTERNS = {
    "PAN": r"\b(?:\d[ -]*?){13,19}\b",          # very loose payment card pattern
    "IBAN": r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "EID": r"\b784-\d{4}-\d{7}-\d{1}\b"         # example UAE EID format (demo)
}

MASK_TOKENS = {
    "PAN": "**** **** **** ####",
    "IBAN": "****-IBAN-****-####",
    "SSN": "***-**-####",
    "EID": "EID-****####"
}

def pii_redact(text: str) -> Tuple[str, List[Dict[str, str]]]:
    """Returns (redacted_text, redaction_map)."""
    redactions = []
    redacted = text
    for pii_type, pattern in PII_PATTERNS.items():
        def _mask(m):
            s = m.group(0)
            masked = MASK_TOKENS[pii_type]
            # simple “preserve last 4” where applicable
            tail = s[-4:] if len(s) >= 4 else s
            return masked.replace("####", tail)
        before = redacted
        redacted = re.sub(pattern, _mask, redacted)
        if before != redacted:
            redactions.append({"type": pii_type, "original_snippet": "<hidden>", "mask_pattern": MASK_TOKENS[pii_type]})
    return redacted, redactions

# ---------- Vector store / retrieval ----------
def build_vectorstore(docs: List[Dict[str, Any]]):
    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=50)
    texts, metadatas = [], []
    for d in docs:
        for chunk in splitter.split_text(d["text"]):
            texts.append(chunk)
            metadata = {k:v for k,v in d.items() if k != "text"}
            metadatas.append(metadata)
    emb = OpenAIEmbeddings()  # uses OPENAI_API_KEY
    vs = FAISS.from_texts(texts=texts, embedding=emb, metadatas=metadatas)
    return vs

VECTORSTORE = build_vectorstore(RAW_DOCS)

def filter_by_jurisdiction_and_date(
    candidates: List[Tuple[str, float, Dict[str, Any]]],
    jurisdiction: Optional[str],
    ref_date: date
) -> List[Tuple[str, float, Dict[str, Any]]]:
    out = []
    for text, score, meta in candidates:
        if jurisdiction and meta.get("jurisdiction") != jurisdiction:
            continue
        eff_from = date.fromisoformat(meta["effective_from"])
        eff_to = date.fromisoformat(meta["effective_to"])
        if eff_from <= ref_date <= eff_to:
            out.append((text, score, meta))
    return out

def retrieve(query: str, jurisdiction: Optional[str], top_k: int = 4) -> List[Dict[str, Any]]:
    # get a slightly larger pool then filter by metadata
    pool = VECTORSTORE.similarity_search_with_score(query, k=10)
    ref_date = date.today()
    # Convert to (text, score, meta)
    pool_norm = [(doc.page_content, score, doc.metadata) for (doc, score) in pool]
    filtered = filter_by_jurisdiction_and_date(pool_norm, jurisdiction, ref_date)
    # fallback: if nothing after filter, keep top few from pool
    final = filtered[:top_k] if filtered else pool_norm[:top_k]
    out = []
    for text, score, meta in final:
        out.append({"content": text, "score": float(score), "metadata": meta})
    return out

# ---------- Policy linter ----------
def policy_lint(text: str) -> List[str]:
    violations = []
    for banned in POLICY_RULES["banned_phrases"]:
        if banned.lower() in text.lower():
            violations.append(f"Contains banned phrase: '{banned}'")
    return violations

# ---------- Output Schema ----------
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

parser = PydanticOutputParser(pydantic_object=AnswerPayload)

# ---------- Prompt ----------
system_template = """You are a banking policy copilot focused on TRUST, OBSERVABILITY, and COMPLIANCE.
- Cite policy sources. If you lack sufficient citations, refuse.
- NEVER reveal raw PII; only masked forms may appear in the answer.
- Output must be concise, actionable, and policy-correct.
- Jurisdiction to follow: {jurisdiction_directive}
"""

human_template = """USER QUESTION:
{question}

CONTEXT (policy snippets):
{context}

CONSTRAINTS:
- Require citations.
- If context is insufficient or conflicting, say so and suggest escalation.
- Avoid banned phrases; be precise with refund/fee/KYC language.

Respond clearly for frontline use.
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_template),
        ("human", human_template),
    ]
)

# ---------- LLM ----------
def get_llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

# ---------- Chain steps ----------
def _prepare_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
    q = inputs["question"]
    jur = inputs.get("jurisdiction", "UAE")  # default for demo
    # Pre-prompt PII redaction on the user question
    red_q, red_map = pii_redact(q)
    # Retrieve context
    docs = retrieve(q, jur, top_k=4)
    # Build a readable context block + citation candidates
    context_lines = []
    cits = []
    for d in docs:
        meta = d["metadata"]
        snippet = d["content"].strip().replace("\n", " ")
        context_lines.append(f"- [{meta['title']}|{meta['policy_id']}|{meta['jurisdiction']}|{meta['effective_from']}→{meta['effective_to']}] {snippet}")
        cits.append(Citation(
            title=meta["title"],
            policy_id=meta["policy_id"],
            jurisdiction=meta["jurisdiction"],
            effective_from=meta["effective_from"],
            effective_to=meta["effective_to"],
            snippet=snippet[:300]
        ))
    context_block = "\n".join(context_lines) if context_lines else "NO_MATCH"
    jurisdiction_directive = POLICY_RULES["jurisdiction_prompts"].get(jur, f"Follow local regulations for {jur}.")
    return {
        "question": red_q,
        "jurisdiction": jur,
        "jurisdiction_directive": jurisdiction_directive,
        "context": context_block,
        "citations": cits,
        "pre_redactions": red_map
    }

def _post_process(llm_text: str, prepared: Dict[str, Any]) -> AnswerPayload:
    # Post-gen PII redaction (defense in depth)
    safe_text, post_red_map = pii_redact(llm_text)
    # Policy lint
    violations = policy_lint(safe_text)
    risk_flags = []
    if "NO_MATCH" in prepared["context"]:
        risk_flags.append("insufficient_context")
    if violations:
        risk_flags.extend([f"policy_violation:{v}" for v in violations])

    # If violations exist or insufficient context -> return refusal with guidance
    if risk_flags:
        safe_text = (
            "I cannot provide a policy-confirmed answer with the current context. "
            "Please consult a supervisor or escalate per KYC/SOP. "
            "Reason(s): " + "; ".join(risk_flags)
        )

    # Combine redaction maps
    combined_redactions = prepared["pre_redactions"] + post_red_map

    payload = AnswerPayload(
        answer=safe_text,
        jurisdiction=prepared["jurisdiction"],
        policy_pack_version=POLICY_PACK_VERSION,
        citations=prepared["citations"],
        redactions=combined_redactions,
        risk_flags=risk_flags,
        disclaimer=POLICY_RULES["required_disclaimer"],
        run_metadata={
            "model": "gpt-4.1-mini",
            "policy_pack_version": POLICY_PACK_VERSION,
            "kb_snapshot_docs": [c.policy_id for c in prepared["citations"]],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )
    return payload

# LCEL Runnable graph
chain = (
    RunnablePassthrough()
    | RunnableLambda(_prepare_inputs)
    | {
        "messages": RunnableLambda(lambda x: prompt.format_messages(
            jurisdiction_directive=x["jurisdiction_directive"],
            question=x["question"],
            context=x["context"]
        )),
        "prepared": RunnablePassthrough()
    }
    | RunnableLambda(lambda x: {
        "llm_text": get_llm().invoke(x["messages"]).content,
        "prepared": x["prepared"]
    })
    | RunnableLambda(lambda x: _post_process(x["llm_text"], x["prepared"]))
)

# ---------- FastAPI ----------
app = FastAPI(title="Audit-Ready RAG (Trust/Observability/Compliance)")

class AskRequest(BaseModel):
    question: str
    jurisdiction: Optional[str] = Field(default="UAE", description="e.g., UAE, EU, US")

@app.post("/ask")
def ask(req: AskRequest):
    # LangSmith: enrich run config metadata (visible in traces)
    config = {
        "run_name": "banking_trust_chain",
        "tags": [
            "banking", "rag", "compliance", "pii", "policy_pack:"+POLICY_PACK_VERSION
        ],
        "metadata": {
            "jurisdiction": req.jurisdiction or "UAE",
            "policy_pack_version": POLICY_PACK_VERSION
        }
    }
    result: AnswerPayload = chain.invoke({"question": req.question, "jurisdiction": req.jurisdiction}, config=config)
    return JSONResponse(json.loads(result.model_dump_json()))

@app.get("/healthz")
def health():
    return {"status": "ok", "policy_pack_version": POLICY_PACK_VERSION}
