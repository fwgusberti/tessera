"""Unit tests for proposal lifecycle service."""

import uuid
import pytest
from datetime import datetime

from tessera_core.domain.entities import ProposalState, UpdateProposal
from tessera_core.services.proposals import (
    ProposalError,
    approve_proposal,
    invalidate_proposal,
    reject_proposal,
)


def make_proposal(state: ProposalState = ProposalState.PENDING) -> UpdateProposal:
    return UpdateProposal(
        document_id=uuid.uuid4(),
        proposed_markdown_patch="# Updated content",
        state=state,
    )


class TestApproveProposal:
    def test_pending_proposal_can_be_approved(self):
        proposal = make_proposal(ProposalState.PENDING)
        approver = uuid.uuid4()
        result = approve_proposal(proposal, approver)
        assert result.state == ProposalState.APPROVED
        assert result.decided_by_user_id == approver
        assert result.decided_at is not None

    def test_approved_proposal_cannot_be_approved_again(self):
        proposal = make_proposal(ProposalState.APPROVED)
        with pytest.raises(ProposalError):
            approve_proposal(proposal, uuid.uuid4())

    def test_rejected_proposal_cannot_be_approved(self):
        proposal = make_proposal(ProposalState.REJECTED)
        with pytest.raises(ProposalError):
            approve_proposal(proposal, uuid.uuid4())

    def test_invalidated_proposal_cannot_be_approved(self):
        proposal = make_proposal(ProposalState.INVALIDATED)
        with pytest.raises(ProposalError):
            approve_proposal(proposal, uuid.uuid4())


class TestRejectProposal:
    def test_pending_proposal_can_be_rejected(self):
        proposal = make_proposal()
        rejector = uuid.uuid4()
        result = reject_proposal(proposal, rejector, reason="Not accurate")
        assert result.state == ProposalState.REJECTED
        assert result.rejection_reason == "Not accurate"
        assert result.decided_by_user_id == rejector

    def test_rejection_without_reason(self):
        proposal = make_proposal()
        result = reject_proposal(proposal, uuid.uuid4())
        assert result.state == ProposalState.REJECTED
        assert result.rejection_reason is None

    def test_approved_proposal_cannot_be_rejected(self):
        proposal = make_proposal(ProposalState.APPROVED)
        with pytest.raises(ProposalError):
            reject_proposal(proposal, uuid.uuid4())


class TestInvalidateProposal:
    def test_pending_proposal_can_be_invalidated(self):
        proposal = make_proposal(ProposalState.PENDING)
        result = invalidate_proposal(proposal)
        assert result.state == ProposalState.INVALIDATED

    def test_non_pending_proposal_returns_unchanged(self):
        approved = make_proposal(ProposalState.APPROVED)
        result = invalidate_proposal(approved)
        assert result.state == ProposalState.APPROVED

    def test_rejected_proposal_returns_unchanged_on_invalidate(self):
        rejected = make_proposal(ProposalState.REJECTED)
        result = invalidate_proposal(rejected)
        assert result.state == ProposalState.REJECTED
