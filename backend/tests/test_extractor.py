"""Entity/relationship extraction normalization (LLM call mocked)."""
import app.ingestion.extractor as extractor
from app.ingestion.extractor import _coerce_json, extract


def test_coerce_json_plain():
    assert _coerce_json('{"a": 1}') == {"a": 1}


def test_coerce_json_strips_markdown_fence():
    raw = '```json\n{"entities": [], "relationships": []}\n```'
    assert _coerce_json(raw) == {"entities": [], "relationships": []}


def test_coerce_json_extracts_embedded_object():
    raw = 'Sure, here it is: {"x": 2} hope that helps'
    assert _coerce_json(raw) == {"x": 2}


def test_extract_normalizes_and_backfills_endpoints(monkeypatch):
    payload = {
        "entities": [{"name": "Acme", "type": "Company"}],
        "relationships": [
            {"source": "Acme", "target": "Beta Inc", "type": "acquired"},
        ],
    }
    monkeypatch.setattr(extractor, "_call_llm", lambda text: payload)
    result = extract("Acme acquired Beta Inc.")

    names = {e.name for e in result.entities}
    assert "Acme" in names
    assert "Beta Inc" in names  # backfilled from the relationship endpoint

    rel = result.relationships[0]
    assert rel.type == "ACQUIRED"  # upper-snake normalized


def test_extract_deduplicates_relationships(monkeypatch):
    payload = {
        "entities": [{"name": "A", "type": "X"}, {"name": "B", "type": "Y"}],
        "relationships": [
            {"source": "A", "target": "B", "type": "LINKS"},
            {"source": "A", "target": "B", "type": "LINKS"},
        ],
    }
    monkeypatch.setattr(extractor, "_call_llm", lambda text: payload)
    result = extract("A links B")
    assert len(result.relationships) == 1


def test_extract_returns_empty_on_llm_failure(monkeypatch):
    def boom(text):
        raise RuntimeError("llm down")

    monkeypatch.setattr(extractor, "_call_llm", boom)
    result = extract("whatever")
    assert result.entities == []
    assert result.relationships == []
