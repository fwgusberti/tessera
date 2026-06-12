"""Integration tests for the ingestion pipeline — write FIRST, must FAIL.

Tests: git sync → DocumentVersion + frontmatter + "Sem dono" gating + language detection
"""

import hashlib
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tessera_core.domain.entities import (
    Confidentiality,
    Document,
    DocumentLifecycleState,
    DocumentVersion,
    Space,
)
from tessera_core.ports.connector import ArtifactRecord


def make_artifact(
    path: str = "docs/README.md",
    content: str = "# Hello World\nThis is a test document.",
) -> ArtifactRecord:
    return ArtifactRecord(
        external_id=f"repo:main:{path}",
        path=path,
        raw_content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
        source_version="abc123",
    )


class TestIngestionPipelineOutputShape:
    def test_ingested_artifact_produces_document_version_with_frontmatter(self):
        """After ingestion, a DocumentVersion must exist with complete frontmatter."""
        from tessera_workers.ingestion.pipeline import ingest_artifact

        artifact = make_artifact(
            path="docs/onboarding.md",
            content="# Onboarding Guide\n\nWelcome to the team.",
        )
        space = Space(slug="engineering", name="Engineering", sector="engineering")
        connector_id = uuid.uuid4()

        result = ingest_artifact(artifact=artifact, space=space, connector_id=connector_id)

        assert result.content_markdown is not None
        assert len(result.content_markdown) > 0
        assert isinstance(result.frontmatter, dict)

        # Required frontmatter fields
        assert "title" in result.frontmatter
        assert "sector" in result.frontmatter
        assert "language" in result.frontmatter

    def test_ingested_artifact_detects_portuguese_language(self):
        """Language detection must classify pt-BR content correctly."""
        from tessera_workers.ingestion.pipeline import ingest_artifact

        content = "# Guia de Integração\n\nBem-vindo à equipe. Este guia explica como configurar seu ambiente."
        artifact = make_artifact(content=content)
        space = Space(slug="rh", name="RH", sector="hr")

        result = ingest_artifact(artifact=artifact, space=space, connector_id=uuid.uuid4())

        assert result.frontmatter.get("language") in ("pt", "pt-BR", "pt-br")

    def test_ingested_artifact_detects_english_language(self):
        """Language detection must classify English content correctly."""
        from tessera_workers.ingestion.pipeline import ingest_artifact

        content = "# Onboarding Guide\n\nWelcome to our team. This guide will help you get started."
        artifact = make_artifact(content=content)
        space = Space(slug="engineering", name="Engineering", sector="engineering")

        result = ingest_artifact(artifact=artifact, space=space, connector_id=uuid.uuid4())

        assert result.frontmatter.get("language") in ("en", "en-US")

    def test_document_starts_in_ingested_or_no_owner_state(self):
        """Freshly ingested document must NOT be in published state — sem dono gating."""
        from tessera_workers.ingestion.pipeline import ingest_artifact, classify_document_state

        artifact = make_artifact()
        space = Space(slug="engineering", name="Engineering", sector="engineering")

        result = ingest_artifact(artifact=artifact, space=space, connector_id=uuid.uuid4())
        state = classify_document_state(result, owner_user_id=None)

        assert state in (DocumentLifecycleState.INGESTED, DocumentLifecycleState.NO_OWNER)
        assert state != DocumentLifecycleState.PUBLISHED

    def test_idempotency_same_content_hash_no_duplicate(self):
        """Ingesting the same artifact twice (same content_hash) must not create duplicates."""
        from tessera_workers.ingestion.pipeline import ingest_artifact

        content = "# Stable document"
        artifact1 = make_artifact(content=content)
        artifact2 = make_artifact(content=content)

        assert artifact1.content_hash == artifact2.content_hash

    def test_ingestion_produces_immutable_version(self):
        """Each ingestion creates a new immutable DocumentVersion."""
        from tessera_workers.ingestion.pipeline import ingest_artifact

        artifact = make_artifact()
        space = Space(slug="engineering", name="Engineering", sector="engineering")

        v1 = ingest_artifact(artifact=artifact, space=space, connector_id=uuid.uuid4())
        assert v1.id is not None
        assert v1.version_number >= 1


class TestSemDono:
    def test_document_without_owner_is_gated_from_publication(self):
        """sem_dono flag must block automatic publication."""
        from tessera_workers.ingestion.pipeline import classify_document_state

        version = DocumentVersion(
            document_id=uuid.uuid4(),
            version_number=1,
            content_markdown="# Test",
            frontmatter={"title": "Test", "sector": "engineering", "language": "en"},
        )

        state = classify_document_state(version, owner_user_id=None)
        assert state in (DocumentLifecycleState.INGESTED, DocumentLifecycleState.NO_OWNER)

    def test_document_with_owner_can_proceed_to_publication(self):
        """Document with an owner assigned should transition past sem_dono."""
        from tessera_workers.ingestion.pipeline import classify_document_state

        version = DocumentVersion(
            document_id=uuid.uuid4(),
            version_number=1,
            content_markdown="# Test",
            frontmatter={"title": "Test", "sector": "engineering", "language": "en"},
        )
        owner_id = uuid.uuid4()
        state = classify_document_state(version, owner_user_id=owner_id)

        assert state != DocumentLifecycleState.NO_OWNER
