"""LLM-based entity + typed-relationship extraction with structured output.

Extraction runs per *parent* chunk: parents carry enough context to capture
relationships that span sentences, while keeping the number of LLM calls far
lower than per-child extraction would.
"""
from __future__ import annotations

import json
import re
from typing import List

from tenacity import retry, stop_after_attempt, wait_fixed

from ..config import settings
from ..llm import get_client
from ..models.schemas import ExtractedEntity, ExtractedRelationship, ExtractionResult

_SYSTEM_PROMPT = """You are an information-extraction engine that builds a knowledge graph.
From the given text, extract named entities (nodes) and explicit, typed relationships (edges).

Rules:
- Only extract relationships that are explicitly stated in the text. Do not infer.
- Entity `name` must be the exact surface form from the text (canonical, deduplicated).
- Entity `type` is a short label such as Person, Company, Product, Location, Technology, Organization.
- Relationship `type` is UPPER_SNAKE_CASE, e.g. ACQUIRED, FOUNDED, PARTNERED_WITH, LOCATED_IN, WORKS_FOR.
- Every relationship's source and target MUST also appear in the entities list.

Respond with ONLY a JSON object of this exact shape, no prose, no markdown:
{
  "entities": [{"name": "...", "type": "..."}],
  "relationships": [{"source": "...", "target": "...", "type": "..."}]
}"""


def _coerce_json(raw: str) -> dict:
    """Best-effort extraction of a JSON object from a model response."""
    raw = raw.strip()
    # Strip markdown fences if the model added them despite instructions.
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
def _call_llm(text: str) -> dict:
    client = get_client()
    resp = client.chat.completions.create(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Text:\n\"\"\"\n{text}\n\"\"\""},
        ],
    )
    return _coerce_json(resp.choices[0].message.content or "{}")


def extract(text: str) -> ExtractionResult:
    """Extract entities and relationships from a chunk of text."""
    try:
        data = _call_llm(text)
    except Exception:
        # Extraction must never break ingestion; return empty on hard failure.
        return ExtractionResult()

    entities: List[ExtractedEntity] = []
    seen_entities = set()
    for e in data.get("entities", []) or []:
        name = str(e.get("name", "")).strip()
        etype = str(e.get("type", "Unknown")).strip() or "Unknown"
        if name and name.lower() not in seen_entities:
            seen_entities.add(name.lower())
            entities.append(ExtractedEntity(name=name, type=etype))

    entity_names = {e.name.lower() for e in entities}
    relationships: List[ExtractedRelationship] = []
    seen_rels = set()
    for r in data.get("relationships", []) or []:
        src = str(r.get("source", "")).strip()
        tgt = str(r.get("target", "")).strip()
        rtype = str(r.get("type", "")).strip().upper().replace(" ", "_")
        if not (src and tgt and rtype):
            continue
        # Keep the graph consistent: ensure endpoints exist as entities.
        if src.lower() not in entity_names:
            entities.append(ExtractedEntity(name=src, type="Unknown"))
            entity_names.add(src.lower())
        if tgt.lower() not in entity_names:
            entities.append(ExtractedEntity(name=tgt, type="Unknown"))
            entity_names.add(tgt.lower())
        key = (src.lower(), rtype, tgt.lower())
        if key not in seen_rels:
            seen_rels.add(key)
            relationships.append(ExtractedRelationship(source=src, target=tgt, type=rtype))

    return ExtractionResult(entities=entities, relationships=relationships)
