"""Voyage AI EmbeddingProvider adapter."""

from __future__ import annotations

import httpx

from tessera_core.ports.providers import EmbeddingProvider
from tessera_api.config import get_settings


class VoyageEmbeddingProvider(EmbeddingProvider):
    _VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.voyage_api_key
        self._model = settings.embedding_model
        self._dimensions = settings.embedding_dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._VOYAGE_API_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"input": texts, "model": self._model},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]
