"""Smoke tests for port interfaces — verify they can be subclassed."""

import inspect
import uuid
from typing import Iterator
from uuid import UUID

import pytest

from tessera_core.domain.entities import Confidentiality, Document, DocumentLifecycleState, Space
from tessera_core.ports.connector import ArtifactRecord, ConnectorPlugin
from tessera_core.ports.providers import EmbeddingProvider, LLMProvider
from tessera_core.ports.repositories import DocumentRepository, SpaceRepository


class TestSpaceRepositoryPort:
    """Contract C-006 (Constitution Principle VI): the domain port exposes no
    unscoped, ``is_admin``-driven space query. The only multi-tenant space-list
    method without a ``company_id`` argument is ``list_all()`` — reachable solely
    from the audited operator surface."""

    def test_space_repository_has_no_list_for_user(self):
        """``list_for_user`` (is_admin → all spaces; else unscoped group-join) is gone."""
        assert not hasattr(SpaceRepository, "list_for_user")

    def test_list_all_is_the_only_unscoped_space_list_method(self):
        """Every method returning ``list[Space]`` is company-scoped except ``list_all``."""
        space_list_methods = [
            name
            for name in dir(SpaceRepository)
            if name.startswith("list")
            and callable(getattr(SpaceRepository, name))
            and inspect.signature(getattr(SpaceRepository, name)).return_annotation == list[Space]
        ]
        unscoped = [
            name
            for name in space_list_methods
            if "company_id" not in inspect.signature(getattr(SpaceRepository, name)).parameters
        ]
        assert unscoped == ["list_all"]
        assert "list_for_user" not in space_list_methods


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


class ConcreteDocumentRepository(DocumentRepository):
    def __init__(self, docs: list[Document] | None = None) -> None:
        self._docs = docs or []

    async def create(self, document: Document) -> Document:
        return document

    async def get_by_id(self, document_id: UUID) -> Document | None:
        return None

    async def list_by_space(self, space_id: UUID, state: DocumentLifecycleState | None = None) -> list[Document]:
        return [d for d in self._docs if d.space_id == space_id]

    async def list_by_space_ids(
        self, space_ids: list[UUID], state: DocumentLifecycleState | None = None
    ) -> list[Document]:
        if not space_ids:
            return []
        docs = [d for d in self._docs if d.space_id in space_ids]
        if state:
            docs = [d for d in docs if d.state == state]
        return docs

    async def update_state(self, document_id: UUID, state: DocumentLifecycleState) -> Document:
        raise NotImplementedError

    async def set_current_version(self, document_id: UUID, version_id: UUID) -> Document:
        raise NotImplementedError

    async def set_owner(self, document_id: UUID, user_id: UUID) -> Document:
        raise NotImplementedError


class TestDocumentRepositoryPort:
    @pytest.mark.asyncio
    async def test_list_by_space_ids_empty_returns_empty(self):
        """list_by_space_ids([]) MUST return [] without querying any docs."""
        space_id = uuid.uuid4()
        doc = Document(
            space_id=space_id,
            title="Doc",
            confidentiality=Confidentiality.INTERNAL,
            state=DocumentLifecycleState.PUBLISHED,
        )
        repo = ConcreteDocumentRepository(docs=[doc])
        result = await repo.list_by_space_ids([])
        assert result == []

    @pytest.mark.asyncio
    async def test_list_by_space_ids_returns_matching_documents(self):
        """list_by_space_ids(space_ids) MUST return docs whose space_id is in the list."""
        space_a = uuid.uuid4()
        space_b = uuid.uuid4()
        doc_a = Document(space_id=space_a, title="A", confidentiality=Confidentiality.INTERNAL, state=DocumentLifecycleState.PUBLISHED)
        doc_b = Document(space_id=space_b, title="B", confidentiality=Confidentiality.INTERNAL, state=DocumentLifecycleState.PUBLISHED)
        repo = ConcreteDocumentRepository(docs=[doc_a, doc_b])
        result = await repo.list_by_space_ids([space_a])
        assert len(result) == 1
        assert result[0].space_id == space_a

    @pytest.mark.asyncio
    async def test_list_by_space_ids_state_filter(self):
        """list_by_space_ids with state MUST exclude docs not in that state."""
        space_id = uuid.uuid4()
        doc_pub = Document(space_id=space_id, title="Pub", confidentiality=Confidentiality.INTERNAL, state=DocumentLifecycleState.PUBLISHED)
        doc_ing = Document(space_id=space_id, title="Ing", confidentiality=Confidentiality.INTERNAL, state=DocumentLifecycleState.INGESTED)
        repo = ConcreteDocumentRepository(docs=[doc_pub, doc_ing])
        result = await repo.list_by_space_ids([space_id], state=DocumentLifecycleState.PUBLISHED)
        assert len(result) == 1
        assert result[0].title == "Pub"


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
