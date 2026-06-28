from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.document import DocumentModel
from tessera_api.adapters.models.space import SpaceModel
from tessera_api.adapters.models.update_proposal import UpdateProposalModel
from tessera_core.domain.proposal_state import ProposalState
from tessera_core.domain.update_proposal import UpdateProposal
from tessera_core.ports.repositories.proposal import ProposalRepository


def _proposal_from_model(m: UpdateProposalModel) -> UpdateProposal:
    return UpdateProposal(
        id=m.id,
        document_id=m.document_id,
        source_artifact_id=m.source_artifact_id,
        proposed_markdown_patch=m.proposed_markdown_patch,
        state=ProposalState(m.state),
        created_at=m.created_at,
        decided_by_user_id=m.decided_by_user_id,
        decided_at=m.decided_at,
        rejection_reason=m.rejection_reason,
        drift_score=m.drift_score,
        summary=m.summary,
    )


class SqlProposalRepository(ProposalRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, proposal: UpdateProposal) -> UpdateProposal:
        model = UpdateProposalModel(
            id=proposal.id,
            document_id=proposal.document_id,
            source_artifact_id=proposal.source_artifact_id,
            proposed_markdown_patch=proposal.proposed_markdown_patch,
            state=proposal.state.value,
            drift_score=proposal.drift_score,
            summary=proposal.summary,
        )
        self._session.add(model)
        await self._session.flush()
        return _proposal_from_model(model)

    async def get_by_id(self, proposal_id: UUID) -> UpdateProposal | None:
        result = await self._session.execute(
            select(UpdateProposalModel).where(UpdateProposalModel.id == proposal_id)
        )
        model = result.scalar_one_or_none()
        return _proposal_from_model(model) if model else None

    async def get_by_id_for_company(
        self, proposal_id: UUID, company_id: UUID
    ) -> UpdateProposal | None:
        result = await self._session.execute(
            select(UpdateProposalModel)
            .join(DocumentModel, DocumentModel.id == UpdateProposalModel.document_id)
            .join(SpaceModel, SpaceModel.id == DocumentModel.space_id)
            .where(
                UpdateProposalModel.id == proposal_id,
                SpaceModel.company_id == company_id,
            )
        )
        model = result.scalar_one_or_none()
        return _proposal_from_model(model) if model else None

    async def list_for_company(
        self,
        company_id: UUID,
        state: str | None = None,
        space_id: UUID | None = None,
    ) -> list[UpdateProposal]:
        q = (
            select(UpdateProposalModel)
            .join(DocumentModel, DocumentModel.id == UpdateProposalModel.document_id)
            .join(SpaceModel, SpaceModel.id == DocumentModel.space_id)
            .where(SpaceModel.company_id == company_id)
        )
        if state:
            q = q.where(UpdateProposalModel.state == state)
        if space_id:
            q = q.where(DocumentModel.space_id == space_id)
        result = await self._session.execute(q)
        return [_proposal_from_model(m) for m in result.scalars().all()]

    async def list_pending_for_document(self, document_id: UUID) -> list[UpdateProposal]:
        result = await self._session.execute(
            select(UpdateProposalModel).where(
                UpdateProposalModel.document_id == document_id,
                UpdateProposalModel.state == "pending",
            )
        )
        return [_proposal_from_model(m) for m in result.scalars().all()]

    async def update_state(self, proposal: UpdateProposal) -> UpdateProposal:
        await self._session.execute(
            update(UpdateProposalModel)
            .where(UpdateProposalModel.id == proposal.id)
            .values(
                state=proposal.state.value,
                decided_by_user_id=proposal.decided_by_user_id,
                decided_at=proposal.decided_at,
                rejection_reason=proposal.rejection_reason,
            )
        )
        updated = await self.get_by_id(proposal.id)
        assert updated is not None
        return updated

    async def invalidate_pending_for_document(self, document_id: UUID) -> int:
        result = await self._session.execute(
            update(UpdateProposalModel)
            .where(
                UpdateProposalModel.document_id == document_id,
                UpdateProposalModel.state == "pending",
            )
            .values(state="invalidated")
        )
        return result.rowcount
