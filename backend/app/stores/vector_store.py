"""Qdrant vector store for child chunks.

Only *child* chunks are embedded and stored here (small-to-big: precise match on
small chunks, expand to parent for generation). Each point payload carries the
provenance needed to expand and cite: child_id, parent_id, doc_id, text.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from ..config import settings
from ..ingestion.chunker import ChildChunk


class VectorStore:
    def __init__(self) -> None:
        # api_key is required by Qdrant Cloud, unused by the local instance.
        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
        self.collection = settings.qdrant_collection

    def ensure_collection(self) -> None:
        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection not in existing:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dim, distance=Distance.COSINE
                ),
            )

    def upsert_children(self, children: List[ChildChunk], vectors: List[List[float]]) -> None:
        points = [
            PointStruct(
                id=child.id,
                vector=vector,
                payload={
                    "child_id": child.id,
                    "parent_id": child.parent_id,
                    "doc_id": child.doc_id,
                    "index": child.index,
                    "text": child.text,
                },
            )
            for child, vector in zip(children, vectors)
        ]
        if points:
            self.client.upsert(collection_name=self.collection, points=points)

    def search(self, query_vector: List[float], top_k: int) -> List[dict]:
        hits = self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )
        return [{"score": h.score, **(h.payload or {})} for h in hits]

    def count(self) -> int:
        return self.client.count(collection_name=self.collection, exact=True).count


@lru_cache
def get_vector_store() -> VectorStore:
    return VectorStore()
