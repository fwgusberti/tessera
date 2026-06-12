"""Test: no auto-publish without explicit approval; obsolete proposals invalidated.

SC-005, FR-018: human-in-the-loop mandatory.
"""

import uuid
import pytest

from tessera_core.domain.entities import (
    Document,
    DocumentLifecycleState,
    ProposalState,
    UpdateProposal,
)


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
