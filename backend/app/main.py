"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import chat, graph, ingest
from .stores.graph_store import get_graph_store
from .stores.vector_store import get_vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("graphrag")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize stores (idempotent).
    try:
        get_vector_store().ensure_collection()
        get_graph_store().ensure_constraints()
        logger.info("Stores initialized")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Store initialization deferred: %s", exc)
    yield
    try:
        get_graph_store().close()
    except Exception:  # noqa: BLE001
        pass


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

_allow_all = "*" in settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # Browsers reject wildcard origin + credentials; this app is stateless
    # (no cookies), so only enable credentials for explicit origins.
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "model": settings.llm_model}


@app.get("/")
async def root() -> dict:
    return {"service": settings.app_name, "docs": "/docs", "health": "/health"}
