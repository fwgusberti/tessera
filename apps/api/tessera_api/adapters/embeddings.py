"""Ollama local EmbeddingProvider adapter."""

from __future__ import annotations

import httpx

from tessera_api.config import get_settings
from tessera_core.ports.providers import EmbeddingProvider


class OllamaEmbeddingProvider(EmbeddingProvider):
    _EMBED_PATH = "/api/embed"

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.ollama_base_url
        self._model = settings.embedding_model
        self._dimensions = settings.embedding_dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=60.0) as client:
            response = await client.post(
                self._EMBED_PATH,
                json={"model": self._model, "input": texts},
            )
            response.raise_for_status()
            return response.json()["embeddings"]
