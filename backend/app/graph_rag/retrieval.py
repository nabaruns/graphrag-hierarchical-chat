"""Retrieval primitives shared by the LangGraph nodes.

Implements the small-to-big expansion: vector search matches small child chunks,
which are then expanded to their (deduplicated) parent chunks for generation and
citation.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from ..embeddings import get_embedder
from ..models.schemas import ParentCitation, Triple
from ..stores.graph_store import get_graph_store
from ..stores.vector_store import get_vector_store


def vector_search(query: str, top_k: int) -> List[dict]:
    embedder = get_embedder()
    vstore = get_vector_store()
    query_vec = embedder.embed_one(query)
    return vstore.search(query_vec, top_k)


def expand_to_parents(hits: List[dict]) -> Tuple[List[str], Dict[str, float], Dict[str, List[str]]]:
    """Group child hits by parent. Returns parent ids ordered by best child score,
    a parent->best_score map, and a parent->matched_child_ids map."""
    best_score: Dict[str, float] = {}
    matched: Dict[str, List[str]] = {}
    for h in hits:
        pid = h.get("parent_id")
        if not pid:
            continue
        score = float(h.get("score", 0.0))
        best_score[pid] = max(best_score.get(pid, 0.0), score)
        matched.setdefault(pid, []).append(h.get("child_id"))
    ordered = sorted(best_score, key=lambda p: best_score[p], reverse=True)
    return ordered, best_score, matched


def build_citations(
    parent_ids: List[str],
    best_score: Dict[str, float],
    matched: Dict[str, List[str]],
) -> List[ParentCitation]:
    gstore = get_graph_store()
    parents = gstore.get_parents(parent_ids)
    citations: List[ParentCitation] = []
    for pid in parent_ids:
        p = parents.get(pid)
        if not p:
            continue
        citations.append(
            ParentCitation(
                parent_id=pid,
                doc_id=p.get("doc_id", ""),
                title=p.get("title"),
                text=p.get("text", ""),
                score=best_score.get(pid),
                matched_child_ids=[c for c in matched.get(pid, []) if c],
            )
        )
    return citations


def build_context(citations: List[ParentCitation], triples: List[Triple]) -> str:
    """Assemble the grounded prompt context from parent chunks + graph triples."""
    parts: List[str] = []

    if citations:
        parts.append("## Retrieved context passages")
        for i, c in enumerate(citations, 1):
            title = c.title or c.doc_id
            parts.append(f"[Passage {i}] (source: {title})\n{c.text}")

    if triples:
        parts.append("\n## Knowledge graph relationships")
        for t in triples:
            parts.append(f"- ({t.source}) -[{t.type}]-> ({t.target})")

    return "\n\n".join(parts).strip()
