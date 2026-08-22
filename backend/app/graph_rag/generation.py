"""Streaming answer generation grounded in retrieved context."""
from __future__ import annotations

from typing import AsyncGenerator

from ..config import settings
from ..llm import get_async_client

_SYSTEM_PROMPT = """You are a precise assistant answering questions over a document knowledge base.
Answer using ONLY the information in the provided context (retrieved passages and
knowledge-graph relationships). Cite the passages you use inline as [Passage N].
If the context does not contain the answer, say you don't have enough information.
Be concise and factual."""


async def stream_answer(query: str, context: str) -> AsyncGenerator[str, None]:
    client = get_async_client()
    user_content = (
        f"Context:\n{context if context else '(no relevant context retrieved)'}\n\n"
        f"Question: {query}"
    )
    stream = await client.chat.completions.create(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        stream=True,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
