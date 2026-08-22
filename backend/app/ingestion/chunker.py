"""Hierarchical parent-child (small-to-big) chunking.

A document is split into large parent blocks (~1000 tokens) that carry enough
context for generation, and each parent is split into small child chunks
(~200 tokens) that are embedded for high-precision vector search. Children keep
a back-reference to their parent so a child match can be expanded to its parent.

Token counts use tiktoken's cl100k_base as a stable approximate tokenizer for
sizing; the actual generation model is irrelevant to how we split.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import List

import tiktoken

from ..config import settings

_ENCODER = tiktoken.get_encoding("cl100k_base")


@dataclass
class ChildChunk:
    id: str
    doc_id: str
    parent_id: str
    index: int
    text: str


@dataclass
class ParentChunk:
    id: str
    doc_id: str
    index: int
    text: str
    children: List[ChildChunk] = field(default_factory=list)


@dataclass
class ChunkedDocument:
    doc_id: str
    title: str
    source: str | None
    parents: List[ParentChunk]

    @property
    def all_children(self) -> List[ChildChunk]:
        return [c for p in self.parents for c in p.children]


def _split_by_tokens(text: str, max_tokens: int, overlap: int) -> List[str]:
    """Sliding-window token split with overlap. Returns non-empty text chunks."""
    tokens = _ENCODER.encode(text)
    if not tokens:
        return []
    if len(tokens) <= max_tokens:
        return [text]

    step = max(1, max_tokens - overlap)
    chunks: List[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        piece = _ENCODER.decode(tokens[start:end]).strip()
        if piece:
            chunks.append(piece)
        if end >= len(tokens):
            break
        start += step
    return chunks


def chunk_document(
    title: str,
    text: str,
    source: str | None = None,
    doc_id: str | None = None,
) -> ChunkedDocument:
    """Split one document into a parent->child hierarchy."""
    doc_id = doc_id or str(uuid.uuid4())

    parent_texts = _split_by_tokens(text, settings.parent_tokens, settings.parent_overlap)
    parents: List[ParentChunk] = []

    for p_idx, p_text in enumerate(parent_texts):
        parent = ParentChunk(
            id=str(uuid.uuid4()),
            doc_id=doc_id,
            index=p_idx,
            text=p_text,
        )
        child_texts = _split_by_tokens(p_text, settings.child_tokens, settings.child_overlap)
        for c_idx, c_text in enumerate(child_texts):
            parent.children.append(
                ChildChunk(
                    id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    parent_id=parent.id,
                    index=c_idx,
                    text=c_text,
                )
            )
        parents.append(parent)

    return ChunkedDocument(doc_id=doc_id, title=title, source=source, parents=parents)


def token_len(text: str) -> int:
    return len(_ENCODER.encode(text))
