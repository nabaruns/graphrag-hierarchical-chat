"""Graph visualization endpoint."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from ..config import settings
from ..models.schemas import SubgraphResponse
from ..stores.graph_store import get_graph_store

logger = logging.getLogger("graphrag")
router = APIRouter(tags=["graph"])

_UNAVAILABLE = {"detail": "Graph store unavailable. Please try again shortly."}


@router.get("/graph/subgraph", response_model=SubgraphResponse)
async def subgraph(
    entity: Optional[str] = Query(None, description="Center entity (fuzzy match). Omit for a whole-graph slice."),
    hops: int = Query(default=settings.max_hops, ge=1, le=4),
    limit: int = Query(default=100, ge=1, le=500),
):
    try:
        return get_graph_store().subgraph_by_entity(entity, hops, limit)
    except Exception:  # noqa: BLE001
        logger.exception("Subgraph query failed")
        return JSONResponse(status_code=503, content=_UNAVAILABLE)


@router.get("/graph/stats")
async def graph_stats():
    try:
        return get_graph_store().stats()
    except Exception:  # noqa: BLE001
        logger.exception("Graph stats failed")
        return JSONResponse(status_code=503, content=_UNAVAILABLE)
