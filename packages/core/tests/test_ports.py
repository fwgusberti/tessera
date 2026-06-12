"""Smoke tests for port interfaces — verify they can be subclassed."""

import uuid
from typing import Iterator
from uuid import UUID

import pytest

from tessera_core.ports.connector import ArtifactRecord, ConnectorPlugin
from tessera_core.ports.providers import EmbeddingProvider, LLMProvider


class ConcreteConnector(ConnectorPlugin):
    def fetch_artifacts(self, connector_id, config, since_version=None) -> Iterator[ArtifactRecord]:
        yield ArtifactRecord(
            external_id="x",
            path="a.md",
            raw_content="# Hello",
            content_hash="abc",
        )

    def current_version(self, config: dict) -> str:
        return "v1"


class ConcreteEmbedder(EmbeddingProvider):
    @property
    def dimensions(self) -> int:
        return 1024

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.dimensions for _ in texts]


class ConcreteLLM(LLMProvider):
    async def complete(self, messages, system=None, max_tokens=4096, temperature=1.0) -> str:
        return "answer"

    async def classify(self, prompt: str, max_tokens: int = 256) -> str:
        return "class"


class TestConnectorPlugin:
    def test_concrete_connector_yields_artifacts(self):
        conn = ConcreteConnector()
        results = list(conn.fetch_artifacts(uuid.uuid4(), {}))
        assert len(results) == 1
        assert results[0].path == "a.md"

    def test_artifact_record_fields(self):
        r = ArtifactRecord(
            external_id="id",
            path="docs/readme.md",
            raw_content="# Doc",
            content_hash="deadbeef",
            source_version="sha1",
            metadata={"author": "bot"},
        )
        assert r.external_id == "id"
        assert r.metadata["author"] == "bot"

    def test_current_version_returns_string(self):
        conn = ConcreteConnector()
        assert conn.current_version({}) == "v1"


class TestEmbeddingProvider:
    def test_dimensions_property(self):
        embedder = ConcreteEmbedder()
        assert embedder.dimensions == 1024

    @pytest.mark.asyncio
    async def test_embed_returns_correct_shape(self):
        embedder = ConcreteEmbedder()
        result = await embedder.embed(["hello", "world"])
        assert len(result) == 2
        assert len(result[0]) == 1024


class TestLLMProvider:
    @pytest.mark.asyncio
    async def test_complete_returns_string(self):
        llm = ConcreteLLM()
        result = await llm.complete(messages=[{"role": "user", "content": "hi"}])
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_classify_returns_string(self):
        llm = ConcreteLLM()
        result = await llm.classify("Is this drift? yes/no")
        assert isinstance(result, str)
