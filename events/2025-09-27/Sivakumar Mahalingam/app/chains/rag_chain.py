import json
from datetime import datetime
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI

from app.policies.policy_store import (
    get_jurisdiction_directive,
    POLICY_PACK_VERSION,
    REQUIRED_DISCLAIMER,
)
from app.retrieval.retriever import retrieve
from app.guards.pii import pii_redact
from app.guards.policy_linter import policy_lint
from app.schemas.models import Citation, AnswerPayload
from app.telemetry.langsmith_client import run_config
from app.config import require_openai_key


def _prompt():
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
    return ChatPromptTemplate.from_messages([("system", system_template), ("human", human_template)])


def _prepare_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
    question = inputs["question"]
    jurisdiction = inputs.get("jurisdiction") or "UAE"

    # Pre-prompt PII redaction
    red_q, pre_redactions = pii_redact(question)

    # Retrieve context
    docs = retrieve(query=question, jurisdiction=jurisdiction, top_k=4)

    # Build context + citations
    context_lines: List[str] = []
    citations: List[Citation] = []
    for d in docs:
        meta = d["metadata"]
        snippet = d["content"].strip().replace("\n", " ")
        context_lines.append(
            f"- [{meta['title']}|{meta['policy_id']}|{meta['jurisdiction']}|{meta['effective_from']}→{meta['effective_to']}] {snippet}"
        )
        citations.append(
            Citation(
                title=meta["title"],
                policy_id=meta["policy_id"],
                jurisdiction=meta["jurisdiction"],
                effective_from=meta["effective_from"],
                effective_to=meta["effective_to"],
                snippet=snippet[:300],
            )
        )

    context_block = "\n".join(context_lines) if context_lines else "NO_MATCH"
    jurisdiction_directive = get_jurisdiction_directive(jurisdiction)

    return {
        "question": red_q,
        "jurisdiction": jurisdiction,
        "context": context_block,
        "jurisdiction_directive": jurisdiction_directive,
        "citations": citations,
        "pre_redactions": pre_redactions,
    }


def _llm_invoke(x: Dict[str, Any]) -> Dict[str, Any]:
    # Unwrap if the chain passed {"prepared": {...}}
    prepared = x.get("prepared", x) or {}

    # Backfill missing fields defensively
    jur = prepared.get("jurisdiction").strip()
    jd  = prepared.get("jurisdiction_directive") or get_jurisdiction_directive(jur)
    q   = (prepared.get("question") or "").strip()
    ctx = prepared.get("context") or "NO_MATCH"

    # Normalize the prepared dict so downstream never KeyErrors
    prepared.update({
        "jurisdiction": jur,
        "jurisdiction_directive": jd,
        "question": q,
        "context": ctx,
    })

    llm = ChatOpenAI(
        model="gpt-4o-mini",            # or any model you have access to
        temperature=0.1,
        openai_api_key=require_openai_key(),
    )

    messages = _prompt().format_messages(
        jurisdiction_directive=jd,
        question=q,
        context=ctx,
    )
    text = llm.invoke(messages).content
    return {"llm_text": text, "prepared": prepared}


def _post_process(llm_text: str, prepared: Dict[str, Any]) -> AnswerPayload:
    # Post-gen PII redaction
    safe_text, post_redactions = pii_redact(llm_text)

    # Policy lint
    violations = policy_lint(safe_text)
    risk_flags: List[str] = []
    if "NO_MATCH" in prepared["context"]:
        risk_flags.append("insufficient_context")
    if violations:
        risk_flags.extend([f"policy_violation:{v}" for v in violations])

    if risk_flags:
        safe_text = (
            "I cannot provide a policy-confirmed answer with the current context. "
            "Please consult a supervisor or escalate per KYC/SOP. "
            "Reason(s): " + "; ".join(risk_flags)
        )

    combined_redactions = prepared["pre_redactions"] + post_redactions

    payload = AnswerPayload(
        answer=safe_text,
        jurisdiction=prepared["jurisdiction"],
        policy_pack_version=POLICY_PACK_VERSION,
        citations=prepared["citations"],
        redactions=combined_redactions,
        risk_flags=risk_flags,
        disclaimer=REQUIRED_DISCLAIMER,
        run_metadata={
            "model": "gpt-4o-mini",
            "policy_pack_version": POLICY_PACK_VERSION,
            "kb_snapshot_docs": [c.policy_id for c in prepared["citations"]],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )
    return payload


# Compose chain
_chain = (
    RunnablePassthrough()
    | RunnableLambda(_prepare_inputs)
    | {
        "prepared": RunnablePassthrough(),
    }
    | RunnableLambda(lambda x: _llm_invoke(x))
    | RunnableLambda(lambda x: _post_process(x["llm_text"], x["prepared"]))
)


def ask(question: str, jurisdiction: str = "UAE") -> Dict[str, Any]:
    cfg = run_config(jurisdiction=jurisdiction)
    result: AnswerPayload = _chain.invoke({"question": question, "jurisdiction": jurisdiction}, config=cfg)
    return json.loads(result.model_dump_json())
