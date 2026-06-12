from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from tessera_core.domain.entities import (
    AgentCredential,
    AuditRecord,
    Chunk,
    Connector,
    Document,
    DocumentLifecycleState,
    DocumentVersion,
    RolePermission,
    Space,
    SourceArtifact,
    UpdateProposal,
    User,
)


class SpaceRepository(ABC):
    @abstractmethod
    async def create(self, space: Space) -> Space: ...

    @abstractmethod
    async def get_by_id(self, space_id: UUID) -> Space | None: ...

    @abstractmethod
    async def list_all(self) -> list[Space]: ...

    @abstractmethod
    async def list_for_user(self, user: User) -> list[Space]: ...

    @abstractmethod
    async def create_role_permission(self, permission: RolePermission) -> RolePermission: ...

    @abstractmethod
    async def list_role_permissions(self, space_id: UUID) -> list[RolePermission]: ...


class DocumentRepository(ABC):
    @abstractmethod
    async def create(self, document: Document) -> Document: ...

    @abstractmethod
    async def get_by_id(self, document_id: UUID) -> Document | None: ...

    @abstractmethod
    async def list_by_space(
        self, space_id: UUID, state: DocumentLifecycleState | None = None
    ) -> list[Document]: ...

    @abstractmethod
    async def update_state(self, document_id: UUID, state: DocumentLifecycleState) -> Document: ...

    @abstractmethod
    async def set_current_version(self, document_id: UUID, version_id: UUID) -> Document: ...

    @abstractmethod
    async def set_owner(self, document_id: UUID, user_id: UUID) -> Document: ...


class DocumentVersionRepository(ABC):
    @abstractmethod
    async def create(self, version: DocumentVersion) -> DocumentVersion: ...

    @abstractmethod
    async def get_by_id(self, version_id: UUID) -> DocumentVersion | None: ...

    @abstractmethod
    async def list_by_document(self, document_id: UUID) -> list[DocumentVersion]: ...

    @abstractmethod
    async def next_version_number(self, document_id: UUID) -> int: ...


class ChunkRepository(ABC):
    @abstractmethod
    async def upsert_chunks(self, chunks: list[Chunk]) -> None: ...

    @abstractmethod
    async def delete_by_document(self, document_id: UUID) -> None: ...

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        space_ids: list[UUID],
        max_confidentiality_level: int,
        top_k: int = 10,
    ) -> list[dict[str, Any]]: ...


class ConnectorRepository(ABC):
    @abstractmethod
    async def create(self, connector: Connector) -> Connector: ...

    @abstractmethod
    async def get_by_id(self, connector_id: UUID) -> Connector | None: ...

    @abstractmethod
    async def list_by_space(self, space_id: UUID) -> list[Connector]: ...

    @abstractmethod
    async def update_sync_status(
        self, connector_id: UUID, status: str
    ) -> Connector: ...


class SourceArtifactRepository(ABC):
    @abstractmethod
    async def upsert(self, artifact: SourceArtifact) -> SourceArtifact: ...

    @abstractmethod
    async def get_by_external_id(
        self, connector_id: UUID, external_id: str
    ) -> SourceArtifact | None: ...

    @abstractmethod
    async def list_by_connector(self, connector_id: UUID) -> list[SourceArtifact]: ...


class ProposalRepository(ABC):
    @abstractmethod
    async def create(self, proposal: UpdateProposal) -> UpdateProposal: ...

    @abstractmethod
    async def get_by_id(self, proposal_id: UUID) -> UpdateProposal | None: ...

    @abstractmethod
    async def list_pending_for_document(self, document_id: UUID) -> list[UpdateProposal]: ...

    @abstractmethod
    async def update_state(self, proposal: UpdateProposal) -> UpdateProposal: ...

    @abstractmethod
    async def invalidate_pending_for_document(self, document_id: UUID) -> int: ...


class UserRepository(ABC):
    @abstractmethod
    async def upsert(self, user: User) -> User: ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def get_by_subject(self, subject: str) -> User | None: ...


class AgentCredentialRepository(ABC):
    @abstractmethod
    async def create(self, credential: AgentCredential) -> AgentCredential: ...

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> AgentCredential | None: ...

    @abstractmethod
    async def revoke(self, credential_id: UUID) -> AgentCredential: ...


class AuditRepository(ABC):
    @abstractmethod
    async def append(self, record: AuditRecord) -> None: ...

    @abstractmethod
    async def list_for_entity(
        self, entity_type: str, entity_id: UUID
    ) -> list[AuditRecord]: ...
