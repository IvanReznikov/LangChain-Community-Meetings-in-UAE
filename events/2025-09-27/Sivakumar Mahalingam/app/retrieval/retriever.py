from datetime import date
from typing import Any, Dict, List, Tuple

from app.retrieval.indexer import VECTORSTORE

def _filter_by_jurisdiction_and_date(
    pool: List[Tuple[Any, float]],
    jurisdiction: str,
    ref_date: date,
) -> List[Tuple[Any, float]]:
    out = []
    for doc, score in pool:
        m = doc.metadata
        if m.get("jurisdiction") != jurisdiction:
            continue
        eff_from = date.fromisoformat(m["effective_from"])
        eff_to = date.fromisoformat(m["effective_to"])
        if eff_from <= ref_date <= eff_to:
            out.append((doc, score))
    return out

def retrieve(query: str, jurisdiction: str, top_k: int = 4) -> List[Dict[str, Any]]:
    pool = VECTORSTORE.similarity_search_with_score(query, k=10)
    ref_date = date.today()
    filtered = _filter_by_jurisdiction_and_date(pool, jurisdiction, ref_date)
    final = filtered[:top_k] if filtered else pool[:top_k]
    out: List[Dict[str, Any]] = []
    for doc, score in final:
        out.append({
            "content": doc.page_content,
            "score": float(score),
            "metadata": doc.metadata,
        })
    return out
