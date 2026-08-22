"""End-to-end ingestion: chunk -> embed -> vector upsert -> extract -> graph write.

Provenance is computed here: for each extracted entity we find which child
chunk(s) within the parent actually mention it (substring match), producing
MENTIONED_IN edges and giving every typed relationship a concrete source child
chunk id (plus its parent id).
"""
from __future__ import annotations

from typing import List

from ..embeddings import get_embedder
from ..models.schemas import DocumentInput, JobStatus
from ..stores.graph_store import get_graph_store
from ..stores.vector_store import get_vector_store
from .chunker import ParentChunk, chunk_document
from .extractor import extract


def _child_mentioning(parent: ParentChunk, entity_name: str) -> str | None:
    """Return the id of the first child chunk whose text mentions the entity."""
    needle = entity_name.lower()
    for child in parent.children:
        if needle in child.text.lower():
            return child.id
    return parent.children[0].id if parent.children else None


def ingest_documents(documents: List[DocumentInput], status: JobStatus) -> JobStatus:
    embedder = get_embedder()
    vstore = get_vector_store()
    gstore = get_graph_store()

    for doc in documents:
        chunked = chunk_document(title=doc.title, text=doc.text, source=doc.source)

        # 1. Vector store: embed + upsert child chunks.
        children = chunked.all_children
        if children:
            vectors = embedder.embed([c.text for c in children])
            vstore.upsert_children(children, vectors)

        # 2. Graph store: persist the parent/child hierarchy.
        gstore.write_hierarchy(
            doc_id=chunked.doc_id,
            title=chunked.title,
            source=chunked.source,
            parents=[{"id": p.id, "index": p.index, "text": p.text} for p in chunked.parents],
            children=[
                {"id": c.id, "parent_id": c.parent_id, "index": c.index, "text": c.text}
                for c in children
            ],
        )

        # 3. Extract entities + relationships per parent, with provenance.
        all_entities: List[dict] = []
        all_mentions: List[dict] = []
        all_rels: List[dict] = []

        for parent in chunked.parents:
            result = extract(parent.text)
            for ent in result.entities:
                all_entities.append({"name": ent.name, "type": ent.type})
                child_id = _child_mentioning(parent, ent.name)
                if child_id:
                    all_mentions.append({"entity": ent.name, "child_id": child_id})
            for rel in result.relationships:
                all_rels.append({
                    "source": rel.source,
                    "target": rel.target,
                    "type": rel.type,
                    "source_child_id": _child_mentioning(parent, rel.source),
                    "source_parent_id": parent.id,
                })

        gstore.write_entities(all_entities)
        gstore.write_mentions(all_mentions)
        gstore.write_relationships(all_rels)

        # 4. Update running job status.
        status.documents += 1
        status.parent_chunks += len(chunked.parents)
        status.child_chunks += len(children)
        status.entities += len({e["name"] for e in all_entities})
        status.relationships += len(all_rels)

    status.status = "completed"
    status.detail = "Ingestion finished"
    return status
