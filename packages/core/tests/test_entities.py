"""Unit tests for domain entities."""

import uuid
from datetime import date, datetime

from tessera_core.domain.entities import (
    AgentCredential,
    AuditRecord,
    Chunk,
    Confidentiality,
    Connector,
    Document,
    DocumentLifecycleState,
    DocumentVersion,
    ProposalState,
    RolePermission,
    Space,
    SourceArtifact,
    UpdateProposal,
    User,
    UserRole,
)


class TestConfidentiality:
    def test_level_ordering_is_correct(self):
        assert Confidentiality.PUBLIC_INTERNAL.level() < Confidentiality.INTERNAL.level()
        assert Confidentiality.INTERNAL.level() < Confidentiality.CONFIDENTIAL.level()
        assert Confidentiality.CONFIDENTIAL.level() < Confidentiality.RESTRICTED.level()

    def test_restricted_has_highest_level(self):
        all_levels = [c.level() for c in Confidentiality]
        assert Confidentiality.RESTRICTED.level() == max(all_levels)


class TestSpace:
    def test_space_defaults(self):
        space = Space(slug="engineering", name="Engineering", sector="engineering")
        assert space.confidence_threshold == 0.7
        assert space.default_language == "pt-BR"
        assert isinstance(space.id, uuid.UUID)


class TestDocument:
    def test_document_defaults(self):
        doc = Document(space_id=uuid.uuid4(), title="Test")
        assert doc.state == DocumentLifecycleState.INGESTED
        assert doc.owner_user_id is None
        assert doc.current_version_id is None

    def test_document_with_confidentiality(self):
        doc = Document(
            space_id=uuid.uuid4(),
            title="Secret",
            confidentiality=Confidentiality.RESTRICTED,
        )
        assert doc.confidentiality == Confidentiality.RESTRICTED


class TestAgentCredential:
    def test_is_revoked_false_by_default(self):
        cred = AgentCredential(
            name="test",
            token_hash="abc",
            scoped_space_ids=[uuid.uuid4()],
        )
        assert cred.is_revoked is False

    def test_is_revoked_true_when_revoked_at_set(self):
        cred = AgentCredential(
            name="test",
            token_hash="abc",
            scoped_space_ids=[],
            revoked_at=datetime.now(),
        )
        assert cred.is_revoked is True


class TestUser:
    def test_user_defaults(self):
        user = User(
            external_subject="sub123",
            email="test@example.com",
            display_name="Test User",
        )
        assert user.is_admin is False
        assert user.groups == []
        assert user.default_language == "pt-BR"


class TestUpdateProposal:
    def test_proposal_defaults_to_pending(self):
        proposal = UpdateProposal(
            document_id=uuid.uuid4(),
            proposed_markdown_patch="# Patch",
        )
        assert proposal.state == ProposalState.PENDING

    def test_proposal_stores_drift_score(self):
        proposal = UpdateProposal(
            document_id=uuid.uuid4(),
            proposed_markdown_patch="# Patch",
            drift_score=0.85,
        )
        assert proposal.drift_score == 0.85
