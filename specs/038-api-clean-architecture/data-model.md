# Data Model: API Clean Architecture Refactor

This document maps each existing class to its target file. No schema changes occur; this is a structural reorganisation only.

## Domain Layer (`tessera_core/domain/`)

| Class / Enum | Target File | Imports From |
|---|---|---|
| `DocumentLifecycleState` | `document_lifecycle_state.py` | `enum` |
| `Confidentiality` | `confidentiality.py` | `enum` |
| `UserRole` | `user_role.py` | `enum` |
| `ProposalState` | `proposal_state.py` | `enum` |
| `SpaceRole` | `space_role.py` | `enum` |
| `CompanyRole` | `company_role.py` | `enum` |
| `DomainPolicy` | `domain_policy_enum.py` | `enum` |
| `InvitationStatus` | `invitation_status.py` | `enum` |
| `JoinRequestStatus` | `join_request_status.py` | `enum` |
| `Space` | `space.py` | `pydantic`, `uuid`, `datetime` |
| `User` | `user.py` | `pydantic`, `uuid`, `datetime` |
| `RolePermission` | `role_permission.py` | `pydantic`, `uuid`, `datetime`, `user_role`, `confidentiality` |
| `Document` | `document.py` | `pydantic`, `uuid`, `datetime`, `document_lifecycle_state`, `confidentiality` |
| `DocumentVersion` | `document_version.py` | `pydantic`, `uuid`, `datetime` |
| `Chunk` | `chunk.py` | `pydantic`, `uuid`, `datetime`, `confidentiality` |
| `Connector` | `connector.py` | `pydantic`, `uuid`, `datetime` |
| `SourceArtifact` | `source_artifact.py` | `pydantic`, `uuid`, `datetime` |
| `UpdateProposal` | `update_proposal.py` | `pydantic`, `uuid`, `datetime`, `proposal_state` |
| `AgentCredential` | `agent_credential.py` | `pydantic`, `uuid`, `datetime`, `confidentiality` |
| `RefreshToken` | `refresh_token.py` | `pydantic`, `uuid`, `datetime` |
| `PasswordResetToken` | `password_reset_token.py` | `pydantic`, `uuid`, `datetime` |
| `AuditRecord` | `audit_record.py` | `pydantic`, `uuid`, `datetime` |
| `Company` | `company.py` | `pydantic`, `uuid`, `datetime` |
| `CompanyMembership` | `company_membership.py` | `pydantic`, `uuid`, `datetime`, `company_role` |
| `DomainJoinPolicy` | `domain_join_policy.py` | `pydantic`, `uuid`, `datetime`, `domain_policy_enum` |
| `Invitation` | `invitation.py` | `pydantic`, `uuid`, `datetime`, `invitation_status` |
| `JoinRequest` | `join_request.py` | `pydantic`, `uuid`, `datetime`, `join_request_status` |
| `OnboardingProgress` | `onboarding_progress.py` | `pydantic`, `uuid`, `datetime` |
| `SpaceMembership` | `space_membership.py` | `pydantic`, `uuid`, `datetime`, `space_role` |

**Key constraint**: No domain file may import from `tessera_api` or any infrastructure package (SQLAlchemy, FastAPI, etc.).

## Ports Layer (`tessera_core/ports/`)

### `ports/providers/`

| Class | Target File | Imports From |
|---|---|---|
| `LLMProvider` | `llm.py` | `abc`, `typing` |
| `EmbeddingProvider` | `embedding.py` | `abc` |
| `EmailPort` | `email.py` | `abc` |

### `ports/repositories/`

| Class | Target File | Domain Imports |
|---|---|---|
| `SpaceRepository` | `space.py` | `Space`, `RolePermission` |
| `DocumentRepository` | `document.py` | `Document`, `DocumentLifecycleState` |
| `DocumentVersionRepository` | `document_version.py` | `DocumentVersion` |
| `ChunkRepository` | `chunk.py` | `Chunk` |
| `ConnectorRepository` | `connector.py` | `Connector` |
| `SourceArtifactRepository` | `source_artifact.py` | `SourceArtifact` |
| `ProposalRepository` | `proposal.py` | `UpdateProposal` |
| `UserRepository` | `user.py` | `User` |
| `AgentCredentialRepository` | `agent_credential.py` | `AgentCredential` |
| `AuditRepository` | `audit.py` | `AuditRecord` |
| `OnboardingRepository` | `onboarding.py` | `OnboardingProgress` |
| `CompanyRepository` | `company.py` | `Company`, `CompanyMembership` |
| `DomainPolicyRepository` | `domain_policy.py` | `DomainJoinPolicy` |
| `InvitationRepository` | `invitation.py` | `Invitation`, `InvitationStatus` |
| `JoinRequestRepository` | `join_request.py` | `JoinRequest`, `JoinRequestStatus` |
| `PasswordResetTokenRepository` | `password_reset_token.py` | `PasswordResetToken` |
| `RefreshTokenRepository` | `refresh_token.py` | — (UUID only) |
| `SpaceMembershipRepository` | `space_membership.py` | `SpaceMembership`, `SpaceRole` |

## Adapter Layer — ORM Models (`tessera_api/adapters/models/`)

| Class | Target File | SQLAlchemy FK Dependencies |
|---|---|---|
| `Base` | `base.py` | `sqlalchemy.orm.DeclarativeBase` |
| `UserModel` | `user.py` | `Base` |
| `CompanyModel` | `company.py` | `Base`, `UserModel` (FK) |
| `SpaceModel` | `space.py` | `Base`, `CompanyModel` (FK) |
| `RolePermissionModel` | `role_permission.py` | `Base`, `SpaceModel` (FK) |
| `DocumentModel` | `document.py` | `Base`, `SpaceModel` (FK), `UserModel` (FK) |
| `DocumentVersionModel` | `document_version.py` | `Base`, `DocumentModel` (FK), `UserModel` (FK) |
| `ConnectorModel` | `connector.py` | `Base`, `SpaceModel` (FK) |
| `SourceArtifactModel` | `source_artifact.py` | `Base`, `ConnectorModel` (FK) |
| `UpdateProposalModel` | `update_proposal.py` | `Base`, `DocumentModel` (FK), `SourceArtifactModel` (FK), `UserModel` (FK) |
| `AgentCredentialModel` | `agent_credential.py` | `Base`, `UserModel` (FK), `CompanyModel` (FK) |
| `RefreshTokenModel` | `refresh_token.py` | `Base`, `UserModel` (FK) |
| `CompanyMembershipModel` | `company_membership.py` | `Base`, `UserModel` (FK), `CompanyModel` (FK) |
| `DomainJoinPolicyModel` | `domain_join_policy.py` | `Base`, `CompanyModel` (FK) |
| `InvitationModel` | `invitation.py` | `Base`, `CompanyModel` (FK), `UserModel` (FK) |
| `JoinRequestModel` | `join_request.py` | `Base`, `UserModel` (FK), `CompanyModel` (FK) |
| `OnboardingProgressModel` | `onboarding_progress.py` | `Base`, `UserModel` (FK), `CompanyModel` (FK) |
| `PasswordResetTokenModel` | `password_reset_token.py` | `Base`, `UserModel` (FK) |
| `AuditRecordModel` | `audit_record.py` | `Base` |
| `SpaceMembershipModel` | `space_membership.py` | `Base`, `SpaceModel` (FK), `UserModel` (FK) |

**Note on `relationship()` cross-file imports**: All relationship class references use string names (already the case in `models.py`). Each model file uses `from __future__ import annotations` and TYPE_CHECKING-gated imports for the related model types. No circular import issues arise at runtime.

## Adapter Layer — Repository Implementations (`tessera_api/adapters/repositories/`)

Each file contains one `Sql*Repository` class plus its private `_*_from_model` helper function. The helper is an implementation detail and is not exported via `__init__.py`.

| Class | Target File | Private Helpers |
|---|---|---|
| `SqlSpaceRepository` | `space.py` | `_space_from_model`, `_perm_from_model` |
| `SqlDocumentRepository` | `document.py` | `_doc_from_model` |
| `SqlDocumentVersionRepository` | `document_version.py` | `_version_from_model` |
| `SqlChunkRepository` | `chunk.py` | — |
| `SqlConnectorRepository` | `connector.py` | `_connector_from_model` |
| `SqlSourceArtifactRepository` | `source_artifact.py` | `_artifact_from_model` |
| `SqlProposalRepository` | `proposal.py` | `_proposal_from_model` |
| `SqlUserRepository` | `user.py` | `_user_from_model` |
| `SqlAgentCredentialRepository` | `agent_credential.py` | `_credential_from_model` |
| `SqlAuditRepository` | `audit.py` | — |
| `SqlRefreshTokenRepository` | `refresh_token.py` | `_refresh_token_from_model` |
| `SqlOnboardingRepository` | `onboarding.py` | `_onboarding_from_model` |
| `SqlCompanyRepository` | `company.py` | `_company_from_model`, `_company_membership_from_model` |
| `SqlDomainPolicyRepository` | `domain_policy.py` | `_domain_policy_from_model` |
| `SqlInvitationRepository` | `invitation.py` | `_invitation_from_model` |
| `SqlJoinRequestRepository` | `join_request.py` | `_join_request_from_model` |
| `SqlPasswordResetTokenRepository` | `password_reset_token.py` | `_prt_from_model` |
| `SqlSpaceMembershipRepository` | `space_membership.py` | `_membership_from_model` |

## Backward-Compat Shim Files

These original files are converted to thin re-export modules:

| Original File | Becomes | Re-exports |
|---|---|---|
| `tessera_core/domain/entities.py` | shim | all 29 classes/enums from new domain files |
| `tessera_core/ports/repositories.py` | shim | all 18 `*Repository` ABCs |
| `tessera_core/ports/providers.py` | shim | `LLMProvider`, `EmbeddingProvider`, `EmailPort` |
| `tessera_api/adapters/models.py` | shim | `Base` + all 20 `*Model` classes |
| `tessera_api/adapters/repo.py` | shim | all 18 `Sql*Repository` classes |
