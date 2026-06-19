from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from tessera_core.domain.entities import (
    AgentCredential,
    AuditRecord,
    Chunk,
    Company,
    CompanyMembership,
    CompanyRole,
    Connector,
    Document,
    DocumentLifecycleState,
    DocumentVersion,
    DomainJoinPolicy,
    Invitation,
    InvitationStatus,
    JoinRequest,
    JoinRequestStatus,
    OnboardingProgress,
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


class OnboardingRepository(ABC):
    @abstractmethod
    async def create(self, progress: OnboardingProgress) -> OnboardingProgress: ...

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> OnboardingProgress | None: ...

    @abstractmethod
    async def advance_step(self, user_id: UUID, next_step: str, company_join_method: str | None = None) -> OnboardingProgress: ...

    @abstractmethod
    async def complete(self, user_id: UUID) -> OnboardingProgress: ...


class CompanyRepository(ABC):
    @abstractmethod
    async def create(self, company: Company) -> Company: ...

    @abstractmethod
    async def get_by_id(self, company_id: UUID) -> Company | None: ...

    @abstractmethod
    async def add_membership(self, membership: CompanyMembership) -> CompanyMembership: ...

    @abstractmethod
    async def get_membership(self, user_id: UUID, company_id: UUID) -> CompanyMembership | None: ...

    @abstractmethod
    async def list_memberships_for_user(self, user_id: UUID) -> list[CompanyMembership]: ...


class DomainPolicyRepository(ABC):
    @abstractmethod
    async def create(self, policy: DomainJoinPolicy) -> DomainJoinPolicy: ...

    @abstractmethod
    async def get_by_domain(self, domain: str) -> DomainJoinPolicy | None: ...

    @abstractmethod
    async def get_by_id(self, policy_id: UUID) -> DomainJoinPolicy | None: ...

    @abstractmethod
    async def list_by_company(self, company_id: UUID) -> list[DomainJoinPolicy]: ...

    @abstractmethod
    async def mark_verified(self, policy_id: UUID) -> DomainJoinPolicy: ...


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


class JoinRequestRepository(ABC):
    @abstractmethod
    async def create(self, request: JoinRequest) -> JoinRequest: ...

    @abstractmethod
    async def get_by_user_and_company(self, user_id: UUID, company_id: UUID) -> JoinRequest | None: ...

    @abstractmethod
    async def get_by_id(self, request_id: UUID) -> JoinRequest | None: ...

    @abstractmethod
    async def list_pending_for_company(self, company_id: UUID) -> list[JoinRequest]: ...

    @abstractmethod
    async def decide(self, request_id: UUID, status: JoinRequestStatus, decided_by: UUID) -> JoinRequest: ...

    @abstractmethod
    async def cancel(self, request_id: UUID) -> None: ...
