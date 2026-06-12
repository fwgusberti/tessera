"""Proposal lifecycle service: pending → approved/rejected/invalidated."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from tessera_core.domain.entities import ProposalState, UpdateProposal


class ProposalError(Exception):
    pass


_TERMINAL_STATES = {ProposalState.APPROVED, ProposalState.REJECTED, ProposalState.INVALIDATED}


def approve_proposal(proposal: UpdateProposal, approver_id: UUID) -> UpdateProposal:
    if proposal.state in _TERMINAL_STATES:
        raise ProposalError(
            f"Cannot approve proposal in state {proposal.state}"
        )
    return proposal.model_copy(
        update={
            "state": ProposalState.APPROVED,
            "decided_by_user_id": approver_id,
            "decided_at": datetime.now(timezone.utc),
        }
    )


def reject_proposal(
    proposal: UpdateProposal, rejector_id: UUID, reason: str | None = None
) -> UpdateProposal:
    if proposal.state in _TERMINAL_STATES:
        raise ProposalError(
            f"Cannot reject proposal in state {proposal.state}"
        )
    return proposal.model_copy(
        update={
            "state": ProposalState.REJECTED,
            "decided_by_user_id": rejector_id,
            "decided_at": datetime.now(timezone.utc),
            "rejection_reason": reason,
        }
    )


def invalidate_proposal(proposal: UpdateProposal) -> UpdateProposal:
    """Invalidate a pending proposal when a new source version supersedes it (FR-018)."""
    if proposal.state != ProposalState.PENDING:
        return proposal
    return proposal.model_copy(update={"state": ProposalState.INVALIDATED})
