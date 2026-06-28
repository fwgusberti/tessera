from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Embedding vector dimensions."""
