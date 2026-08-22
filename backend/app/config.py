"""Central configuration loaded from environment variables.

Everything about the LLM is config-driven and OpenAI-compatible, so the same
code runs against Ollama (default, self-hosted, zero cost), a self-hosted vLLM
endpoint on k8s, or OpenRouter, purely by changing env vars.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "GraphRAG Hierarchical Indexing"

    # --- LLM (OpenAI-compatible: Ollama / vLLM / OpenRouter) ---
    openai_base_url: str = "http://ollama:11434/v1"
    openai_api_key: str = "ollama"  # placeholder; real key only for OpenRouter
    llm_model: str = "qwen2.5:3b-instruct"
    llm_temperature: float = 0.1
    llm_request_timeout: float = 600.0  # CPU inference can be slow

    # --- Embeddings (local, fastembed) ---
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    # --- Neo4j ---
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"

    # --- Qdrant ---
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "child_chunks"

    # --- Hierarchical chunking ---
    parent_tokens: int = 1000
    parent_overlap: int = 100
    child_tokens: int = 200
    child_overlap: int = 40

    # --- Retrieval ---
    top_k: int = 5
    max_hops: int = 2  # graph traversal depth
    max_iterations: int = 2  # LangGraph retrieve/traverse loops (multi-hop)

    # --- CORS ---
    cors_origins: List[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
