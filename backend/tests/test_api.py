"""API smoke tests. External stores and the LLM are mocked so these run offline."""
import app.routers.chat as chat_router
import app.routers.ingest as ingest_router
from app.models.schemas import (
    ParentCitation,
    RetrievalResult,
    SubgraphResponse,
    Triple,
)
from fastapi.testclient import TestClient


def _client(monkeypatch):
    # Neutralize lifespan store init.
    import app.main as main

    monkeypatch.setattr(main.get_vector_store(), "ensure_collection", lambda: None, raising=False)
    from app.main import app

    return TestClient(app)


def test_ingest_returns_job_id_and_status(monkeypatch):
    # Replace the real pipeline so the background task does no I/O.
    def fake_pipeline(documents, status):
        status.status = "completed"
        status.documents = len(documents)
        return status

    monkeypatch.setattr(ingest_router, "ingest_documents", fake_pipeline)
    client = _client(monkeypatch)

    resp = client.post(
        "/api/v1/ingest",
        json={"documents": [{"title": "T", "text": "Acme acquired Beta."}]},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["document_count"] == 1
    job_id = body["job_id"]

    status = client.get(f"/api/v1/ingest/{job_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "completed"


def test_ingest_status_404_for_unknown(monkeypatch):
    client = _client(monkeypatch)
    assert client.get("/api/v1/ingest/does-not-exist").status_code == 404


def test_chat_streams_sse_events(monkeypatch):
    fake_result = RetrievalResult(
        context="ctx",
        parents=[ParentCitation(parent_id="p1", doc_id="d1", text="Acme acquired Beta.")],
        triples=[Triple(source="Acme", type="ACQUIRED", target="Beta")],
        subgraph=SubgraphResponse(),
        seed_entities=["Acme"],
    )
    monkeypatch.setattr(chat_router, "run_retrieval", lambda *a, **k: fake_result)

    async def fake_stream(query, context):
        for tok in ["Acme ", "acquired ", "Beta."]:
            yield tok

    monkeypatch.setattr(chat_router, "stream_answer", fake_stream)

    client = _client(monkeypatch)
    resp = client.post("/api/v1/chat", json={"query": "who acquired Beta?"})
    assert resp.status_code == 200
    text = resp.text
    assert "citations" in text
    assert "subgraph" in text
    assert "token" in text
    assert "done" in text


def test_health(monkeypatch):
    client = _client(monkeypatch)
    assert client.get("/health").json()["status"] == "ok"
