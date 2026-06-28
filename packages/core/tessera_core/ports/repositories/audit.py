from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.audit_record import AuditRecord


class AuditRepository(ABC):
    @abstractmethod
    async def append(self, record: AuditRecord) -> None: ...

    @abstractmethod
    async def list_for_entity(self, entity_type: str, entity_id: UUID) -> list[AuditRecord]: ...
