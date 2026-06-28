from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.join_request import JoinRequest
from tessera_core.domain.join_request_status import JoinRequestStatus


class JoinRequestRepository(ABC):
    @abstractmethod
    async def create(self, request: JoinRequest) -> JoinRequest: ...

    @abstractmethod
    async def get_by_user_and_company(
        self, user_id: UUID, company_id: UUID
    ) -> JoinRequest | None: ...

    @abstractmethod
    async def get_by_id(self, request_id: UUID) -> JoinRequest | None: ...

    @abstractmethod
    async def list_pending_for_company(self, company_id: UUID) -> list[JoinRequest]: ...

    @abstractmethod
    async def decide(
        self, request_id: UUID, status: JoinRequestStatus, decided_by: UUID
    ) -> JoinRequest: ...

    @abstractmethod
    async def cancel(self, request_id: UUID) -> None: ...
