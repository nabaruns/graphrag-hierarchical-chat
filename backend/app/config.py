"""Central configuration loaded from environment variables.

Everything about the LLM is config-driven and OpenAI-compatible, so the same
code runs against Ollama (default, self-hosted, zero cost), a self-hosted vLLM
endpoint on k8s, or OpenRouter, purely by changing env vars.
"""
from functools import lru_cache
from typing import Annotated, List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
    qdrant_api_key: Optional[str] = None  # required by Qdrant Cloud
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

    # --- Abuse protection ---
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 2  # per client IP, on POST /chat and /ingest
    # Cloudflare Turnstile: verification is skipped when the secret is unset.
    turnstile_secret_key: Optional[str] = None

    # --- CORS ---
    # NoDecode disables pydantic-settings' automatic JSON decoding of this
    # list field so the validator below can accept a plain comma-separated
    # string from a host's env UI (as well as a JSON list).
    cors_origins: Annotated[List[str], NoDecode] = ["*"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v):
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return ["*"]
            if s.startswith("["):
                import json

                return json.loads(s)
            return [o.strip() for o in s.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
