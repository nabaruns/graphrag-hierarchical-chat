"""Graph visualization endpoint."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from ..config import settings
from ..models.schemas import SubgraphResponse
from ..stores.graph_store import get_graph_store

router = APIRouter(tags=["graph"])


@router.get("/graph/subgraph", response_model=SubgraphResponse)
async def subgraph(
    entity: Optional[str] = Query(None, description="Center entity (fuzzy match). Omit for a whole-graph slice."),
    hops: int = Query(default=settings.max_hops, ge=1, le=4),
    limit: int = Query(default=100, ge=1, le=500),
) -> SubgraphResponse:
    return get_graph_store().subgraph_by_entity(entity, hops, limit)


@router.get("/graph/stats")
async def graph_stats() -> dict:
    return get_graph_store().stats()
