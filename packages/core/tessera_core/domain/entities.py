from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentLifecycleState(str, Enum):
    INGESTED = "ingested"
    NO_OWNER = "no_owner"
    PUBLISHED = "published"
    OUTDATED = "outdated"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class Confidentiality(str, Enum):
    PUBLIC_INTERNAL = "public_internal"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

    def level(self) -> int:
        return {
            Confidentiality.PUBLIC_INTERNAL: 0,
            Confidentiality.INTERNAL: 1,
            Confidentiality.CONFIDENTIAL: 2,
            Confidentiality.RESTRICTED: 3,
        }[self]


class UserRole(str, Enum):
    READER = "reader"
    CONTRIBUTOR = "contributor"
    OWNER = "owner"
    SPACE_ADMIN = "space_admin"


class ProposalState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    INVALIDATED = "invalidated"


class Space(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    slug: str
    name: str
    sector: str
    taxonomy: dict[str, Any] = Field(default_factory=dict)
    retention_policy: dict[str, Any] = Field(default_factory=dict)
    confidence_threshold: float = 0.7
    default_language: str = "pt-BR"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class User(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    external_subject: str
    email: str
    display_name: str
    is_admin: bool = False
    groups: list[str] = Field(default_factory=list)
    default_language: str = "pt-BR"
    password_hash: str | None = None
    title: str | None = None
    onboarding_completed: bool = False
    created_at: datetime | None = None


class RolePermission(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    space_id: UUID
    idp_group: str
    role: UserRole
    max_confidentiality: Confidentiality = Confidentiality.INTERNAL
    created_at: datetime | None = None


class Document(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    space_id: UUID
    owner_user_id: UUID | None = None
    title: str
    language: str = "pt-BR"
    confidentiality: Confidentiality = Confidentiality.INTERNAL
    tags: list[str] = Field(default_factory=list)
    validity_until: date | None = None
    state: DocumentLifecycleState = DocumentLifecycleState.INGESTED
    current_version_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentVersion(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    document_id: UUID
    version_number: int
    content_markdown: str
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    author_user_id: UUID | None = None
    approver_user_id: UUID | None = None
    approved_at: datetime | None = None
    source_artifact_id: UUID | None = None
    created_from_proposal_id: UUID | None = None
    created_at: datetime | None = None


class Chunk(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    document_version_id: UUID
    document_id: UUID
    space_id: UUID
    ordinal: int
    text: str
    embedding: list[float] | None = None
    confidentiality: Confidentiality = Confidentiality.INTERNAL
    language: str = "pt-BR"
    created_at: datetime | None = None


class Connector(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    space_id: UUID
    type: str
    config: dict[str, Any] = Field(default_factory=dict)
    schedule: str | None = None
    last_sync_at: datetime | None = None
    status: str = "ok"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SourceArtifact(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    connector_id: UUID
    external_id: str
    path: str
    source_version: str | None = None
    raw_content: str | None = None
    content_hash: str
    fetched_at: datetime | None = None


class UpdateProposal(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    document_id: UUID
    source_artifact_id: UUID | None = None
    proposed_markdown_patch: str
    state: ProposalState = ProposalState.PENDING
    created_at: datetime | None = None
    decided_by_user_id: UUID | None = None
    decided_at: datetime | None = None
    rejection_reason: str | None = None
    drift_score: float | None = None
    summary: str | None = None


class AgentCredential(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    name: str
    token_hash: str
    scoped_space_ids: list[UUID] = Field(default_factory=list)
    max_confidentiality: Confidentiality = Confidentiality.INTERNAL
    created_by_user_id: UUID | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None


class RefreshToken(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    user_id: UUID
    token_hash: str
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    is_revoked: bool = False


class AuditRecord(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    actor_type: str
    actor_id: UUID
    action: str
    entity_type: str
    entity_id: UUID
    occurred_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Onboarding domain entities
# ---------------------------------------------------------------------------

class CompanyRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"


class DomainPolicy(str, Enum):
    AUTO_JOIN = "auto_join"
    REQUEST_APPROVAL = "request_approval"


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class JoinRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class Company(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    name: str
    industry: str | None = None
    team_size: str | None = None
    admin_user_id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CompanyMembership(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    user_id: UUID
    company_id: UUID
    role: CompanyRole
    joined_at: datetime | None = None


class DomainJoinPolicy(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    company_id: UUID
    domain: str
    policy: DomainPolicy
    verified: bool = False
    created_at: datetime | None = None
    verified_at: datetime | None = None


class Invitation(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    company_id: UUID
    invited_by_user_id: UUID | None = None
    email: str
    token_hash: str
    status: InvitationStatus = InvitationStatus.PENDING
    expires_at: datetime
    created_at: datetime | None = None
    accepted_at: datetime | None = None


class JoinRequest(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    user_id: UUID
    company_id: UUID
    status: JoinRequestStatus = JoinRequestStatus.PENDING
    requested_at: datetime | None = None
    decided_at: datetime | None = None
    decided_by_user_id: UUID | None = None


class OnboardingProgress(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    user_id: UUID
    completed_steps: list[str] = Field(default_factory=list)
    current_step: str = "profile"
    company_join_method: str | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
