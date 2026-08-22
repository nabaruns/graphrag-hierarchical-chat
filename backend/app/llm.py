"""OpenAI-compatible LLM client factory.

Points at Ollama by default; swap OPENAI_BASE_URL / OPENAI_API_KEY / LLM_MODEL
to use vLLM (k8s) or OpenRouter without any code change.
"""
from functools import lru_cache

from openai import AsyncOpenAI, OpenAI

from .config import settings


@lru_cache
def get_client() -> OpenAI:
    return OpenAI(
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
        timeout=settings.llm_request_timeout,
    )


@lru_cache
def get_async_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
        timeout=settings.llm_request_timeout,
    )
