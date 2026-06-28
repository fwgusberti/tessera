from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.domain_join_policy import DomainJoinPolicyModel
from tessera_core.domain.domain_join_policy import DomainJoinPolicy
from tessera_core.domain.domain_policy_enum import DomainPolicy
from tessera_core.ports.repositories.domain_policy import DomainPolicyRepository


def _domain_policy_from_model(m: DomainJoinPolicyModel) -> DomainJoinPolicy:
    return DomainJoinPolicy(
        id=m.id,
        company_id=m.company_id,
        domain=m.domain,
        policy=DomainPolicy(m.policy),
        verified=m.verified,
        created_at=m.created_at,
        verified_at=m.verified_at,
    )


class SqlDomainPolicyRepository(DomainPolicyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, policy: DomainJoinPolicy) -> DomainJoinPolicy:
        model = DomainJoinPolicyModel(
            id=policy.id,
            company_id=policy.company_id,
            domain=policy.domain,
            policy=policy.policy.value,
            verified=policy.verified,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _domain_policy_from_model(model)

    async def get_by_domain(self, domain: str) -> DomainJoinPolicy | None:
        result = await self._session.execute(
            select(DomainJoinPolicyModel).where(DomainJoinPolicyModel.domain == domain)
        )
        model = result.scalar_one_or_none()
        return _domain_policy_from_model(model) if model else None

    async def get_by_id(self, policy_id: UUID) -> DomainJoinPolicy | None:
        result = await self._session.execute(
            select(DomainJoinPolicyModel).where(DomainJoinPolicyModel.id == policy_id)
        )
        model = result.scalar_one_or_none()
        return _domain_policy_from_model(model) if model else None

    async def list_by_company(self, company_id: UUID) -> list[DomainJoinPolicy]:
        result = await self._session.execute(
            select(DomainJoinPolicyModel).where(DomainJoinPolicyModel.company_id == company_id)
        )
        return [_domain_policy_from_model(m) for m in result.scalars().all()]

    async def mark_verified(self, policy_id: UUID) -> DomainJoinPolicy:
        result = await self._session.execute(
            select(DomainJoinPolicyModel).where(DomainJoinPolicyModel.id == policy_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"DomainJoinPolicy {policy_id} not found")
        model.verified = True
        model.verified_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(model)
        return _domain_policy_from_model(model)
