"""Local embeddings via fastembed (BAAI/bge-small-en-v1.5, 384-dim).

OpenRouter/Ollama chat endpoints do not serve embeddings, so we embed locally.
This is CPU-friendly and requires no API key.
"""
from functools import lru_cache
from typing import List

from fastembed import TextEmbedding

from .config import settings


class Embedder:
    def __init__(self, model_name: str) -> None:
        self._model = TextEmbedding(model_name=model_name)

    def embed(self, texts: List[str]) -> List[List[float]]:
        return [vec.tolist() for vec in self._model.embed(texts)]

    def embed_one(self, text: str) -> List[float]:
        return self.embed([text])[0]


@lru_cache
def get_embedder() -> Embedder:
    return Embedder(settings.embedding_model)
