from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.join_request import JoinRequestModel
from tessera_core.domain.join_request import JoinRequest
from tessera_core.domain.join_request_status import JoinRequestStatus
from tessera_core.ports.repositories.join_request import JoinRequestRepository


def _join_request_from_model(m: JoinRequestModel) -> JoinRequest:
    return JoinRequest(
        id=m.id,
        user_id=m.user_id,
        company_id=m.company_id,
        status=JoinRequestStatus(m.status),
        requested_at=m.requested_at,
        decided_at=m.decided_at,
        decided_by_user_id=m.decided_by_user_id,
    )


class SqlJoinRequestRepository(JoinRequestRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, request: JoinRequest) -> JoinRequest:
        model = JoinRequestModel(
            id=request.id,
            user_id=request.user_id,
            company_id=request.company_id,
            status=request.status.value,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _join_request_from_model(model)

    async def get_by_user_and_company(self, user_id: UUID, company_id: UUID) -> JoinRequest | None:
        result = await self._session.execute(
            select(JoinRequestModel).where(
                JoinRequestModel.user_id == user_id,
                JoinRequestModel.company_id == company_id,
            )
        )
        model = result.scalar_one_or_none()
        return _join_request_from_model(model) if model else None

    async def get_by_id(self, request_id: UUID) -> JoinRequest | None:
        result = await self._session.execute(
            select(JoinRequestModel).where(JoinRequestModel.id == request_id)
        )
        model = result.scalar_one_or_none()
        return _join_request_from_model(model) if model else None

    async def list_pending_for_company(self, company_id: UUID) -> list[JoinRequest]:
        result = await self._session.execute(
            select(JoinRequestModel).where(
                JoinRequestModel.company_id == company_id,
                JoinRequestModel.status == "pending",
            )
        )
        return [_join_request_from_model(m) for m in result.scalars().all()]

    async def decide(
        self, request_id: UUID, status: JoinRequestStatus, decided_by: UUID
    ) -> JoinRequest:
        result = await self._session.execute(
            select(JoinRequestModel).where(JoinRequestModel.id == request_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"JoinRequest {request_id} not found")
        model.status = status.value
        model.decided_at = datetime.now(UTC)
        model.decided_by_user_id = decided_by
        await self._session.flush()
        await self._session.refresh(model)
        return _join_request_from_model(model)

    async def cancel(self, request_id: UUID) -> None:
        result = await self._session.execute(
            select(JoinRequestModel).where(JoinRequestModel.id == request_id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.status = JoinRequestStatus.DENIED.value
            await self._session.flush()
