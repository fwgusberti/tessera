from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.invitation import InvitationModel
from tessera_core.domain.invitation import Invitation
from tessera_core.domain.invitation_status import InvitationStatus
from tessera_core.ports.repositories.invitation import InvitationRepository


def _invitation_from_model(m: InvitationModel) -> Invitation:
    return Invitation(
        id=m.id,
        company_id=m.company_id,
        invited_by_user_id=m.invited_by_user_id,
        email=m.email,
        token_hash=m.token_hash,
        status=InvitationStatus(m.status),
        expires_at=m.expires_at,
        created_at=m.created_at,
        accepted_at=m.accepted_at,
    )


class SqlInvitationRepository(InvitationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, invitation: Invitation) -> Invitation:
        model = InvitationModel(
            id=invitation.id,
            company_id=invitation.company_id,
            invited_by_user_id=invitation.invited_by_user_id,
            email=invitation.email,
            token_hash=invitation.token_hash,
            status=invitation.status.value,
            expires_at=invitation.expires_at,
            accepted_at=invitation.accepted_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _invitation_from_model(model)

    async def create_bulk(self, invitations: list[Invitation]) -> list[Invitation]:
        models = [
            InvitationModel(
                id=inv.id,
                company_id=inv.company_id,
                invited_by_user_id=inv.invited_by_user_id,
                email=inv.email,
                token_hash=inv.token_hash,
                status=inv.status.value,
                expires_at=inv.expires_at,
                accepted_at=inv.accepted_at,
            )
            for inv in invitations
        ]
        for m in models:
            self._session.add(m)
        await self._session.flush()
        for m in models:
            await self._session.refresh(m)
        return [_invitation_from_model(m) for m in models]

    async def get_by_id(self, invitation_id: UUID) -> Invitation | None:
        result = await self._session.execute(
            select(InvitationModel).where(InvitationModel.id == invitation_id)
        )
        model = result.scalar_one_or_none()
        return _invitation_from_model(model) if model else None

    async def get_by_token_hash(self, token_hash: str) -> Invitation | None:
        result = await self._session.execute(
            select(InvitationModel).where(InvitationModel.token_hash == token_hash)
        )
        model = result.scalar_one_or_none()
        return _invitation_from_model(model) if model else None

    async def get_pending_for_email(self, email: str) -> list[Invitation]:
        result = await self._session.execute(
            select(InvitationModel).where(
                InvitationModel.email == email,
                InvitationModel.status == "pending",
            )
        )
        return [_invitation_from_model(m) for m in result.scalars().all()]

    async def update_status(self, invitation_id: UUID, status: InvitationStatus) -> Invitation:
        result = await self._session.execute(
            select(InvitationModel).where(InvitationModel.id == invitation_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Invitation {invitation_id} not found")
        model.status = status.value
        if status == InvitationStatus.ACCEPTED:
            model.accepted_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(model)
        return _invitation_from_model(model)

    async def cancel(self, invitation_id: UUID) -> None:
        result = await self._session.execute(
            select(InvitationModel).where(InvitationModel.id == invitation_id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.status = InvitationStatus.CANCELLED.value
            await self._session.flush()
