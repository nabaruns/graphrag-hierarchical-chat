"""Pydantic v2 schemas for API I/O and LLM structured output."""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Ingestion
# --------------------------------------------------------------------------- #
class DocumentInput(BaseModel):
    title: str = Field(..., description="Human-readable document title")
    text: str = Field(..., min_length=1, description="Raw document text")
    source: Optional[str] = Field(None, description="Origin, e.g. URL or filename")


class IngestRequest(BaseModel):
    documents: List[DocumentInput] = Field(..., min_length=1)


class IngestResponse(BaseModel):
    job_id: str
    status: str
    document_count: int


class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    detail: Optional[str] = None
    documents: int = 0
    parent_chunks: int = 0
    child_chunks: int = 0
    entities: int = 0
    relationships: int = 0
    error: Optional[str] = None


# --------------------------------------------------------------------------- #
# LLM structured extraction output
# --------------------------------------------------------------------------- #
class ExtractedEntity(BaseModel):
    name: str = Field(..., description="Canonical entity name as it appears in text")
    type: str = Field(..., description="Entity type, e.g. Person, Company, Product, Location, Technology")


class ExtractedRelationship(BaseModel):
    source: str = Field(..., description="Source entity name")
    target: str = Field(..., description="Target entity name")
    type: str = Field(..., description="UPPER_SNAKE_CASE relation, e.g. ACQUIRED, FOUNDED, PARTNERED_WITH")


class ExtractionResult(BaseModel):
    entities: List[ExtractedEntity] = Field(default_factory=list)
    relationships: List[ExtractedRelationship] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Chat
# --------------------------------------------------------------------------- #
class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: Optional[int] = None
    max_hops: Optional[int] = None
    session_id: Optional[str] = None


class Triple(BaseModel):
    source: str
    type: str
    target: str
    source_child_id: Optional[str] = None
    source_parent_id: Optional[str] = None


class ParentCitation(BaseModel):
    parent_id: str
    doc_id: str
    title: Optional[str] = None
    text: str
    score: Optional[float] = None
    matched_child_ids: List[str] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    """Everything the retrieval graph produced, minus the streamed answer."""
    context: str
    parents: List[ParentCitation] = Field(default_factory=list)
    triples: List[Triple] = Field(default_factory=list)
    subgraph: "SubgraphResponse"
    seed_entities: List[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Graph visualization
# --------------------------------------------------------------------------- #
class GraphNode(BaseModel):
    id: str
    label: str
    type: Optional[str] = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class SubgraphResponse(BaseModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


RetrievalResult.model_rebuild()
