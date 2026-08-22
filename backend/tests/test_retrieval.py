"""Small-to-big expansion and context assembly."""
from app.graph_rag.retrieval import build_context, expand_to_parents
from app.models.schemas import ParentCitation, Triple


def test_expand_to_parents_groups_and_orders_by_best_score():
    hits = [
        {"child_id": "c1", "parent_id": "p1", "score": 0.4},
        {"child_id": "c2", "parent_id": "p1", "score": 0.9},
        {"child_id": "c3", "parent_id": "p2", "score": 0.6},
    ]
    ordered, best, matched = expand_to_parents(hits)
    assert ordered == ["p1", "p2"]  # p1 best score 0.9 > p2 0.6
    assert best["p1"] == 0.9
    assert set(matched["p1"]) == {"c1", "c2"}


def test_expand_ignores_hits_without_parent():
    ordered, best, matched = expand_to_parents([{"child_id": "c", "score": 0.5}])
    assert ordered == []


def test_build_context_includes_passages_and_triples():
    citations = [
        ParentCitation(parent_id="p1", doc_id="d1", title="Doc", text="Acme acquired Beta.")
    ]
    triples = [Triple(source="Acme", type="ACQUIRED", target="Beta")]
    ctx = build_context(citations, triples)
    assert "Passage 1" in ctx
    assert "Acme acquired Beta." in ctx
    assert "(Acme) -[ACQUIRED]-> (Beta)" in ctx
