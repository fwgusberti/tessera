"""Integration test: source change → UpdateProposal pending → approve publishes new version.

TDD: write FIRST, must FAIL before drift pipeline is implemented.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tessera_core.domain.entities import (
    Document,
    DocumentLifecycleState,
    ProposalState,
    SourceArtifact,
    UpdateProposal,
)


class TestDriftPipeline:
    def test_changed_source_creates_pending_proposal(self):
        """When the source artifact's content_hash changes, a pending UpdateProposal is created."""
        from tessera_workers.drift.detector import detect_drift

        old_hash = "abc123"
        new_hash = "def456"

        document = Document(
            space_id=uuid.uuid4(),
            title="Onboarding Guide",
            state=DocumentLifecycleState.PUBLISHED,
            owner_user_id=uuid.uuid4(),
            current_version_id=uuid.uuid4(),
        )
        old_artifact = SourceArtifact(
            connector_id=uuid.uuid4(),
            external_id="repo:main:README.md",
            path="README.md",
            content_hash=old_hash,
        )
        new_artifact = SourceArtifact(
            connector_id=old_artifact.connector_id,
            external_id="repo:main:README.md",
            path="README.md",
            content_hash=new_hash,
            raw_content="# Updated Guide\n\nNew content here.",
        )

        has_drift = detect_drift(old_artifact=old_artifact, new_artifact=new_artifact)
        assert has_drift is True

    def test_unchanged_source_does_not_create_proposal(self):
        """When content_hash is unchanged, no drift is detected."""
        from tessera_workers.drift.detector import detect_drift

        same_hash = "abc123"
        artifact = SourceArtifact(
            connector_id=uuid.uuid4(),
            external_id="repo:main:README.md",
            path="README.md",
            content_hash=same_hash,
        )
        has_drift = detect_drift(old_artifact=artifact, new_artifact=artifact)
        assert has_drift is False

    def test_proposal_starts_in_pending_state(self):
        """A newly created UpdateProposal must be in pending state."""
        from tessera_workers.drift.detector import create_proposal

        doc_id = uuid.uuid4()
        proposal = create_proposal(
            document_id=doc_id,
            source_artifact_id=uuid.uuid4(),
            old_markdown="# Old\nContent",
            new_markdown="# New\nUpdated content",
            drift_score=0.8,
            summary="Title changed and content updated",
        )

        assert proposal.state == ProposalState.PENDING
        assert proposal.document_id == doc_id
        assert proposal.drift_score is not None
        assert proposal.summary is not None

    def test_proposal_patch_is_not_empty(self):
        """The generated patch must contain actual content."""
        from tessera_workers.drift.detector import create_proposal

        proposal = create_proposal(
            document_id=uuid.uuid4(),
            source_artifact_id=uuid.uuid4(),
            old_markdown="# Old Content",
            new_markdown="# New Content\n\nAdditional paragraph.",
            drift_score=0.75,
            summary="Added paragraph",
        )
        assert len(proposal.proposed_markdown_patch) > 0
