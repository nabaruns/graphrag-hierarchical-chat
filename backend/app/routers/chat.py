"""Chat endpoint: multi-hop GraphRAG retrieval + streamed generation over SSE.

Event sequence (Server-Sent Events):
  event: citations  -> parent chunks used as grounding
  event: subgraph   -> nodes/edges + triples for the graph inspector
  event: token      -> one generated token/delta (many)
  event: done       -> terminal marker

Citations and the subgraph are sent first so the UI can render citation cards
and the graph while the answer streams in.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from ..graph_rag.agent import run_retrieval
from ..graph_rag.generation import stream_answer
from ..models.schemas import ChatRequest
from ..security import rate_limit, verify_turnstile

router = APIRouter(tags=["chat"])


@router.post("/chat", dependencies=[Depends(verify_turnstile), Depends(rate_limit)])
async def chat(req: ChatRequest) -> EventSourceResponse:
    # Retrieval (LangGraph) is synchronous; run it off the event loop.
    retrieval = await asyncio.to_thread(
        run_retrieval, req.query, req.top_k, req.max_hops
    )

    async def event_generator():
        yield {
            "event": "citations",
            "data": json.dumps([c.model_dump() for c in retrieval.parents]),
        }
        yield {
            "event": "subgraph",
            "data": json.dumps(
                {
                    "subgraph": retrieval.subgraph.model_dump(),
                    "triples": [t.model_dump() for t in retrieval.triples],
                    "seed_entities": retrieval.seed_entities,
                }
            ),
        }
        async for token in stream_answer(req.query, retrieval.context):
            yield {"event": "token", "data": json.dumps({"text": token})}
        yield {"event": "done", "data": json.dumps({"ok": True})}

    return EventSourceResponse(event_generator())
