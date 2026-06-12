from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
    ) -> str:
        """Generate a completion from messages."""

    @abstractmethod
    async def classify(self, prompt: str, max_tokens: int = 256) -> str:
        """Low-cost classification call (may use a smaller model)."""


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Embedding vector dimensions."""
