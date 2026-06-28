from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.audit_record import AuditRecordModel
from tessera_core.domain.audit_record import AuditRecord
from tessera_core.ports.repositories.audit import AuditRepository


class SqlAuditRepository(AuditRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, record: AuditRecord) -> None:
        model = AuditRecordModel(
            id=record.id,
            actor_type=record.actor_type,
            actor_id=record.actor_id,
            action=record.action,
            entity_type=record.entity_type,
            entity_id=record.entity_id,
            record_metadata=record.metadata,
        )
        self._session.add(model)

    async def list_for_entity(self, entity_type: str, entity_id: UUID) -> list[AuditRecord]:
        result = await self._session.execute(
            select(AuditRecordModel)
            .where(
                AuditRecordModel.entity_type == entity_type,
                AuditRecordModel.entity_id == entity_id,
            )
            .order_by(AuditRecordModel.occurred_at)
        )
        return [
            AuditRecord(
                id=m.id,
                actor_type=m.actor_type,
                actor_id=m.actor_id,
                action=m.action,
                entity_type=m.entity_type,
                entity_id=m.entity_id,
                occurred_at=m.occurred_at,
                metadata=m.record_metadata or {},
            )
            for m in result.scalars().all()
        ]
