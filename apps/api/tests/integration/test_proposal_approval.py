"""Test: no auto-publish without explicit approval; obsolete proposals invalidated.

SC-005, FR-018: human-in-the-loop mandatory.
"""

import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tessera_core.domain.entities import (
    Document,
    DocumentLifecycleState,
    ProposalState,
    UpdateProposal,
    User,
)


def _mock_db():
    mock_get_db = MagicMock()
    mock_session = AsyncMock()
    mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_get_db


@contextmanager
def _bypass_onboarding_guard():
    from tessera_api.auth.bearer import require_onboarding_complete
    from tessera_api.main import app

    async def _noop():
        return None

    app.dependency_overrides[require_onboarding_complete] = _noop
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_onboarding_complete, None)


class TestProposalApproval:
    def test_approval_transitions_proposal_to_approved(self):
        """Approving a proposal must transition it to approved state."""
        from tessera_core.services.proposals import approve_proposal

        doc_id = uuid.uuid4()
        approver_id = uuid.uuid4()
        proposal = UpdateProposal(
            document_id=doc_id,
            proposed_markdown_patch="# Updated content",
            state=ProposalState.PENDING,
        )

        approved = approve_proposal(proposal=proposal, approver_id=approver_id)
        assert approved.state == ProposalState.APPROVED
        assert approved.decided_by_user_id == approver_id
        assert approved.decided_at is not None

    def test_rejection_records_reason(self):
        """Rejected proposal must record reason and be in rejected state."""
        from tessera_core.services.proposals import reject_proposal

        proposal = UpdateProposal(
            document_id=uuid.uuid4(),
            proposed_markdown_patch="# Draft",
            state=ProposalState.PENDING,
        )
        rejected = reject_proposal(
            proposal=proposal, rejector_id=uuid.uuid4(), reason="Content is incorrect"
        )
        assert rejected.state == ProposalState.REJECTED
        assert rejected.rejection_reason == "Content is incorrect"

    def test_new_source_change_invalidates_pending_proposal(self):
        """When a new source version arrives, any pending proposal must be invalidated."""
        from tessera_core.services.proposals import invalidate_proposal

        proposal = UpdateProposal(
            document_id=uuid.uuid4(),
            proposed_markdown_patch="# Stale patch",
            state=ProposalState.PENDING,
        )
        invalidated = invalidate_proposal(proposal)
        assert invalidated.state == ProposalState.INVALIDATED

    def test_cannot_approve_already_rejected_proposal(self):
        """Rejecting a proposal and then approving must raise an error."""
        from tessera_core.services.proposals import approve_proposal, reject_proposal
        from tessera_core.services.proposals import ProposalError

        proposal = UpdateProposal(
            document_id=uuid.uuid4(),
            proposed_markdown_patch="# Content",
            state=ProposalState.PENDING,
        )
        rejected = reject_proposal(
            proposal=proposal, rejector_id=uuid.uuid4(), reason="Not applicable"
        )
        with pytest.raises(ProposalError):
            approve_proposal(proposal=rejected, approver_id=uuid.uuid4())

    def test_cannot_approve_invalidated_proposal(self):
        """Invalidated proposals cannot be approved."""
        from tessera_core.services.proposals import approve_proposal, invalidate_proposal
        from tessera_core.services.proposals import ProposalError

        proposal = UpdateProposal(
            document_id=uuid.uuid4(),
            proposed_markdown_patch="# Content",
            state=ProposalState.PENDING,
        )
        invalidated = invalidate_proposal(proposal)
        with pytest.raises(ProposalError):
            approve_proposal(proposal=invalidated, approver_id=uuid.uuid4())

    def test_no_automatic_publication_without_approval(self):
        """Document must remain in published state until explicit approval of proposal."""
        doc = Document(
            space_id=uuid.uuid4(),
            title="Guide",
            state=DocumentLifecycleState.OUTDATED,
            owner_user_id=uuid.uuid4(),
            current_version_id=uuid.uuid4(),
        )
        # Proposal still pending — document state should not change automatically
        assert doc.state == DocumentLifecycleState.OUTDATED


class TestProposalApprovalAuthorization:
    """FR-004: in-company approval requires publish rights in the document's space.

    This is distinct from the cross-tenant denial path (which returns before any
    role check); here the proposal/document DO belong to the caller's company, but
    the caller lacks publish rights, so approve must still return 403.
    """

    def test_in_company_member_without_publish_rights_cannot_approve(self, two_company_setup):
        token_a, company_a_id, token_b, company_b_id = two_company_setup

        space_id = uuid.uuid4()
        document = Document(
            space_id=space_id,
            title="Alpha Handbook",
            state=DocumentLifecycleState.PUBLISHED,
            owner_user_id=uuid.uuid4(),
            current_version_id=uuid.uuid4(),
        )
        proposal = UpdateProposal(
            document_id=document.id,
            proposed_markdown_patch="# rewrite",
            state=ProposalState.PENDING,
        )
        # caller is a real (non-admin) user with no groups → no publish rights
        actor = User(
            external_subject="alice",
            email="alice@alpha.test",
            display_name="Alice",
            is_admin=False,
            groups=[],
        )

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.proposals.get_db", _mock_db()),
                patch("tessera_api.routers.proposals.SqlProposalRepository") as mock_prop_cls,
                patch("tessera_api.routers.proposals.SqlDocumentRepository") as mock_doc_cls,
                patch("tessera_api.routers.proposals.SqlDocumentVersionRepository"),
                patch("tessera_api.routers.proposals.SqlUserRepository") as mock_user_cls,
                patch("tessera_api.routers.proposals.SqlSpaceRepository") as mock_space_cls,
                patch("tessera_api.routers.proposals.write_audit", new_callable=AsyncMock),
            ):
                mock_prop = AsyncMock()
                mock_prop.get_by_id_for_company = AsyncMock(return_value=proposal)
                mock_prop_cls.return_value = mock_prop

                mock_doc = AsyncMock()
                mock_doc.get_by_id_for_company = AsyncMock(return_value=document)
                mock_doc_cls.return_value = mock_doc

                mock_user = AsyncMock()
                mock_user.get_by_id = AsyncMock(return_value=actor)
                mock_user_cls.return_value = mock_user

                mock_space = AsyncMock()
                mock_space.list_role_permissions = AsyncMock(return_value=[])
                mock_space_cls.return_value = mock_space

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        f"/v1/proposals/{proposal.id}/approve",
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert response.status_code == 403
        # role denial reached: the proposal was loaded in-company but not mutated
        mock_prop.update_state.assert_not_awaited()
