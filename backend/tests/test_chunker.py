"""Hierarchical chunking: parent-child mapping and token sizing."""
from app.config import settings
from app.ingestion.chunker import chunk_document, token_len


def _long_text(words: int) -> str:
    return " ".join(f"word{i}" for i in range(words))


def test_short_document_single_parent_child():
    doc = chunk_document("t", "A short sentence about Acme Corp.")
    assert len(doc.parents) == 1
    assert len(doc.parents[0].children) == 1
    assert doc.parents[0].children[0].text


def test_parent_child_backreferences_are_consistent():
    doc = chunk_document("t", _long_text(4000))
    assert len(doc.parents) > 1  # long doc splits into multiple parents
    for parent in doc.parents:
        assert parent.children, "every parent has at least one child"
        for child in parent.children:
            assert child.parent_id == parent.id
            assert child.doc_id == doc.doc_id


def test_child_chunks_respect_token_budget():
    doc = chunk_document("t", _long_text(5000))
    for child in doc.all_children:
        # allow a small margin for decode boundaries
        assert token_len(child.text) <= settings.child_tokens + 5


def test_parent_chunks_respect_token_budget():
    doc = chunk_document("t", _long_text(5000))
    for parent in doc.parents:
        assert token_len(parent.text) <= settings.parent_tokens + 5


def test_ids_are_unique():
    doc = chunk_document("t", _long_text(3000))
    parent_ids = [p.id for p in doc.parents]
    child_ids = [c.id for c in doc.all_children]
    assert len(parent_ids) == len(set(parent_ids))
    assert len(child_ids) == len(set(child_ids))
