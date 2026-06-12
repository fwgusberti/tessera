"""Append-only audit helper."""

from __future__ import annotations

import uuid
from uuid import UUID

from tessera_core.domain.entities import AuditRecord
from tessera_api.adapters.repo import SqlAuditRepository


async def write_audit(
    session,
    actor_type: str,
    actor_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID,
    metadata: dict | None = None,
) -> None:
    record = AuditRecord(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=metadata or {},
    )
    repo = SqlAuditRepository(session)
    await repo.append(record)
