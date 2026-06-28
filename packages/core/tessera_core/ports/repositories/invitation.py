from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.invitation import Invitation
from tessera_core.domain.invitation_status import InvitationStatus


class InvitationRepository(ABC):
    @abstractmethod
    async def create(self, invitation: Invitation) -> Invitation: ...

    @abstractmethod
    async def create_bulk(self, invitations: list[Invitation]) -> list[Invitation]: ...

    @abstractmethod
    async def get_by_id(self, invitation_id: UUID) -> Invitation | None: ...

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> Invitation | None: ...

    @abstractmethod
    async def get_pending_for_email(self, email: str) -> list[Invitation]: ...

    @abstractmethod
    async def update_status(self, invitation_id: UUID, status: InvitationStatus) -> Invitation: ...

    @abstractmethod
    async def cancel(self, invitation_id: UUID) -> None: ...
