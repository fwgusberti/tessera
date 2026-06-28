from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.agent_credential import AgentCredentialModel
from tessera_core.domain.agent_credential import AgentCredential
from tessera_core.domain.confidentiality import Confidentiality
from tessera_core.ports.repositories.agent_credential import AgentCredentialRepository


def _credential_from_model(m: AgentCredentialModel) -> AgentCredential:
    return AgentCredential(
        id=m.id,
        name=m.name,
        token_hash=m.token_hash,
        scoped_space_ids=m.scoped_space_ids or [],
        max_confidentiality=Confidentiality(m.max_confidentiality),
        created_by_user_id=m.created_by_user_id,
        company_id=m.company_id,
        revoked_at=m.revoked_at,
        created_at=m.created_at,
    )


class SqlAgentCredentialRepository(AgentCredentialRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, credential: AgentCredential) -> AgentCredential:
        model = AgentCredentialModel(
            id=credential.id,
            name=credential.name,
            token_hash=credential.token_hash,
            scoped_space_ids=credential.scoped_space_ids,
            max_confidentiality=credential.max_confidentiality.value,
            created_by_user_id=credential.created_by_user_id,
            company_id=credential.company_id,
        )
        self._session.add(model)
        await self._session.flush()
        return _credential_from_model(model)

    async def get_by_token_hash(self, token_hash: str) -> AgentCredential | None:
        result = await self._session.execute(
            select(AgentCredentialModel).where(AgentCredentialModel.token_hash == token_hash)
        )
        model = result.scalar_one_or_none()
        return _credential_from_model(model) if model else None

    async def get_by_id_for_company(
        self, credential_id: UUID, company_id: UUID
    ) -> AgentCredential | None:
        result = await self._session.execute(
            select(AgentCredentialModel).where(
                AgentCredentialModel.id == credential_id,
                AgentCredentialModel.company_id == company_id,
            )
        )
        model = result.scalar_one_or_none()
        return _credential_from_model(model) if model else None

    async def revoke(self, credential_id: UUID) -> AgentCredential:
        await self._session.execute(
            update(AgentCredentialModel)
            .where(AgentCredentialModel.id == credential_id)
            .values(revoked_at=datetime.now(UTC))
        )
        result = await self._session.execute(
            select(AgentCredentialModel).where(AgentCredentialModel.id == credential_id)
        )
        model = result.scalar_one()
        return _credential_from_model(model)
