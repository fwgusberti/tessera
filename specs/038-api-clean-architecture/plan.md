# Implementation Plan: API Clean Architecture Refactor

**Branch**: `038-api-clean-architecture` | **Date**: 2026-06-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/038-api-clean-architecture/spec.md`

## Summary

Decompose four monolithic Python files (`entities.py`, `repositories.py`, `providers.py`, `models.py`, `repo.py`) into one-class-per-file layouts under their respective packages, while preserving backward-compatible re-export shims so no caller needs to change import paths. The `Base` declarative object is extracted to a shared `base.py` and re-imported by every ORM model file so Alembic metadata discovery remains intact.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI 0.115, SQLAlchemy 2.0 (async), Pydantic 2, Alembic, pytest / pytest-asyncio / anyio

**Storage**: PostgreSQL via asyncpg; vector search via pgvector extension

**Testing**: `pytest-asyncio` for `tessera_core`; `anyio` marks for `tessera_api` integration tests; `fastapi.testclient.TestClient` (sync) for integration tests

**Target Platform**: Linux server (Docker/Kubernetes)

**Project Type**: Web-service (FastAPI) + domain library (`tessera_core` package)

**Performance Goals**: No change — this is a structural-only refactor

**Constraints**: All existing tests must pass without modification to test logic; Alembic autogeneration must detect zero schema changes after refactor; Ruff + Black gates must pass

**Scale/Scope**: ~5 source files decomposed into ~65 individual class files + re-export shims

## Constitution Check

### I. Domain-Driven Architecture ✅
The refactor strengthens this principle — each domain class gets its own file. No framework imports are introduced into domain files; they remain pure Pydantic models.

### II. Separation of Concerns ✅
No change to layer boundaries. Domain files import only `pydantic` and `uuid`/`datetime` from stdlib. Port files import only `abc` and domain files. ORM model files import only SQLAlchemy and each other's `Base`.

### III. Data Locality & Consent ✅
No new local persistence introduced. Out of scope.

### IV. Test-Driven Development ✅
FR-008 mandates the full test suite passes unchanged. No new business logic means no new tests are required beyond verifying imports resolve. Existing coverage (≥85%) is preserved by design — no code is deleted, only reorganised.

### V. Quality Gates ✅
FR-009 mandates Ruff + Black pass on all refactored files. The refactor produces cleaner, shorter files that are easier to lint.

### VI. Tenant Data Isolation ✅
This refactor does not touch query logic. All `company_id` scoping in repository implementations is preserved verbatim in the new per-class files. No new data-access paths are introduced.

**Tenant Isolation section**: This feature introduces zero new database queries and zero new tables. No cross-tenant isolation tests are needed beyond confirming existing tests still pass.

## Project Structure

### Documentation (this feature)

```text
specs/038-api-clean-architecture/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (target layout after refactor)

```text
packages/core/tessera_core/
├── domain/
│   ├── __init__.py                   # re-exports all symbols (backward compat)
│   ├── entities.py                   # backward-compat re-export shim (thin)
│   ├── confidentiality.py            # Confidentiality enum
│   ├── document_lifecycle_state.py   # DocumentLifecycleState enum
│   ├── user_role.py                  # UserRole enum
│   ├── proposal_state.py             # ProposalState enum
│   ├── space_role.py                 # SpaceRole enum (tightly coupled to SpaceMembership)
│   ├── company_role.py               # CompanyRole enum
│   ├── domain_policy.py              # DomainPolicy enum
│   ├── invitation_status.py          # InvitationStatus enum
│   ├── join_request_status.py        # JoinRequestStatus enum
│   ├── space.py                      # Space
│   ├── user.py                       # User
│   ├── role_permission.py            # RolePermission
│   ├── document.py                   # Document
│   ├── document_version.py           # DocumentVersion
│   ├── chunk.py                      # Chunk
│   ├── connector.py                  # Connector
│   ├── source_artifact.py            # SourceArtifact
│   ├── update_proposal.py            # UpdateProposal
│   ├── agent_credential.py           # AgentCredential
│   ├── refresh_token.py              # RefreshToken
│   ├── password_reset_token.py       # PasswordResetToken
│   ├── audit_record.py               # AuditRecord
│   ├── company.py                    # Company
│   ├── company_membership.py         # CompanyMembership
│   ├── domain_join_policy.py         # DomainJoinPolicy
│   ├── invitation.py                 # Invitation
│   ├── join_request.py               # JoinRequest
│   ├── onboarding_progress.py        # OnboardingProgress
│   └── space_membership.py           # SpaceMembership
│
└── ports/
    ├── __init__.py                    # re-exports (unchanged external API)
    ├── providers.py                   # backward-compat re-export shim
    ├── providers/
    │   ├── __init__.py               # re-exports LLMProvider, EmbeddingProvider, EmailPort
    │   ├── llm.py                    # LLMProvider
    │   ├── embedding.py              # EmbeddingProvider
    │   └── email.py                  # EmailPort
    ├── repositories.py               # backward-compat re-export shim
    └── repositories/
        ├── __init__.py               # re-exports all 18 repository ABCs
        ├── space.py                  # SpaceRepository
        ├── document.py               # DocumentRepository
        ├── document_version.py       # DocumentVersionRepository
        ├── chunk.py                  # ChunkRepository
        ├── connector.py              # ConnectorRepository
        ├── source_artifact.py        # SourceArtifactRepository
        ├── proposal.py               # ProposalRepository
        ├── user.py                   # UserRepository
        ├── agent_credential.py       # AgentCredentialRepository
        ├── audit.py                  # AuditRepository
        ├── onboarding.py             # OnboardingRepository
        ├── company.py                # CompanyRepository
        ├── domain_policy.py          # DomainPolicyRepository
        ├── invitation.py             # InvitationRepository
        ├── join_request.py           # JoinRequestRepository
        ├── password_reset_token.py   # PasswordResetTokenRepository
        ├── refresh_token.py          # RefreshTokenRepository
        └── space_membership.py       # SpaceMembershipRepository

apps/api/tessera_api/
└── adapters/
    ├── __init__.py                   # unchanged
    ├── models.py                     # backward-compat re-export shim
    ├── models/
    │   ├── __init__.py              # imports ALL models (Alembic discovery)
    │   ├── base.py                  # Base (DeclarativeBase) — single shared object
    │   ├── user.py                  # UserModel
    │   ├── space.py                 # SpaceModel
    │   ├── role_permission.py       # RolePermissionModel
    │   ├── document.py              # DocumentModel
    │   ├── document_version.py      # DocumentVersionModel
    │   ├── connector.py             # ConnectorModel
    │   ├── source_artifact.py       # SourceArtifactModel
    │   ├── update_proposal.py       # UpdateProposalModel
    │   ├── agent_credential.py      # AgentCredentialModel
    │   ├── refresh_token.py         # RefreshTokenModel
    │   ├── company.py               # CompanyModel
    │   ├── company_membership.py    # CompanyMembershipModel
    │   ├── domain_join_policy.py    # DomainJoinPolicyModel
    │   ├── invitation.py            # InvitationModel
    │   ├── join_request.py          # JoinRequestModel
    │   ├── onboarding_progress.py   # OnboardingProgressModel
    │   ├── password_reset_token.py  # PasswordResetTokenModel
    │   ├── audit_record.py          # AuditRecordModel
    │   └── space_membership.py      # SpaceMembershipModel
    ├── repo.py                      # backward-compat re-export shim
    └── repositories/
        ├── __init__.py              # re-exports all Sql* classes
        ├── space.py                 # SqlSpaceRepository + _space_from_model, _perm_from_model
        ├── document.py              # SqlDocumentRepository + _doc_from_model
        ├── document_version.py      # SqlDocumentVersionRepository + _version_from_model
        ├── chunk.py                 # SqlChunkRepository
        ├── connector.py             # SqlConnectorRepository + _connector_from_model
        ├── source_artifact.py       # SqlSourceArtifactRepository + _artifact_from_model
        ├── proposal.py              # SqlProposalRepository + _proposal_from_model
        ├── user.py                  # SqlUserRepository + _user_from_model
        ├── agent_credential.py      # SqlAgentCredentialRepository + _credential_from_model
        ├── audit.py                 # SqlAuditRepository
        ├── refresh_token.py         # SqlRefreshTokenRepository + _refresh_token_from_model
        ├── onboarding.py            # SqlOnboardingRepository + _onboarding_from_model
        ├── company.py               # SqlCompanyRepository + _company_from_model, _company_membership_from_model
        ├── domain_policy.py         # SqlDomainPolicyRepository + _domain_policy_from_model
        ├── invitation.py            # SqlInvitationRepository + _invitation_from_model
        ├── join_request.py          # SqlJoinRequestRepository + _join_request_from_model
        ├── password_reset_token.py  # SqlPasswordResetTokenRepository + _prt_from_model
        └── space_membership.py      # SqlSpaceMembershipRepository + _membership_from_model
```

**Structure Decision**: The refactor uses the "package with backward-compat shim" pattern. Each monolithic file is replaced by a package directory of the same concept; the original file is repurposed as a thin re-export shim so that all existing `from tessera_core.domain.entities import X` import paths continue to work without modification. The `__init__.py` of each new package also re-exports all symbols for callers using the package namespace.

## Complexity Tracking

No constitution violations.

## Key Design Decisions

### SQLAlchemy Relationship Forward References

ORM models reference each other via `relationship()`. When split across files, circular imports must be avoided. The solution:

1. All model files import `Base` from `tessera_api.adapters.models.base`.
2. The `relationship()` calls already use string class names (e.g., `"RolePermissionModel"`) which SQLAlchemy resolves at mapper configuration time — no cross-file class imports needed at module load.
3. For `Mapped[list[RolePermissionModel]]` type annotations: use `from __future__ import annotations` at the top of each model file so annotations are evaluated lazily, and add `TYPE_CHECKING`-gated imports for the referenced model classes.
4. `models/__init__.py` imports all model files explicitly so all mappers are registered before any query executes. This also satisfies Alembic's `Base.metadata` discovery requirement.

### Backward-Compatible Shim Pattern

Original files (`entities.py`, `repositories.py`, `providers.py`, `models.py`, `repo.py`) become thin re-export modules:

```python
# tessera_core/domain/entities.py  (shim)
from tessera_core.domain.space import Space
from tessera_core.domain.document import Document
# ... all other exports
__all__ = ["Space", "Document", ...]
```

This approach means:
- Zero changes required to any test or router that imports from the old paths
- Each class lives in exactly one authoritative file
- The shim can be removed in a future cleanup PR once callers migrate

### Enum Co-location

Enums are co-located with their primary associated entity:
- `DocumentLifecycleState` → `document_lifecycle_state.py` (imported by `document.py`)
- `Confidentiality` → `confidentiality.py` (imported by `document.py`, `chunk.py`, `role_permission.py`, `agent_credential.py`)
- `UserRole` → `user_role.py` (imported by `role_permission.py`)
- `ProposalState` → `proposal_state.py` (imported by `update_proposal.py`)
- `SpaceRole` → `space_role.py` (imported by `space_membership.py`)
- `CompanyRole` → `company_role.py` (imported by `company_membership.py`)
- `DomainPolicy` → `domain_policy.py` (enum, imported by `domain_join_policy.py`)
- `InvitationStatus` → `invitation_status.py` (imported by `invitation.py`)
- `JoinRequestStatus` → `join_request_status.py` (imported by `join_request.py`)

Each enum gets its own file because they are imported independently by callers (e.g., `from tessera_core.domain.entities import SpaceRole` without importing `SpaceMembership`).

### Alembic Integrity

`db/migrations/env.py` currently imports `from tessera_api.adapters.models import Base`. After the refactor:
- `tessera_api/adapters/models.py` becomes a shim that imports `Base` from `models/base.py` and imports all model classes (which registers them on `Base.metadata`)
- `models/__init__.py` also does this
- Both paths remain valid so Alembic continues to work

### Import Order for SQLAlchemy

Models with FK relationships must all be loaded before SQLAlchemy configures mappers. The `models/__init__.py` imports in dependency order:
1. `base` (no deps)
2. `user` (no FK to other models, is FK target)
3. `company` (FK to `user`)
4. `space` (FK to `company`)
5. `role_permission` (FK to `space`)
6. `document` (FK to `space`, `user`)
7. `document_version` (FK to `document`, `user`)
8. `connector` (FK to `space`)
9. `source_artifact` (FK to `connector`)
10. `update_proposal` (FK to `document`, `source_artifact`, `user`)
11. `agent_credential` (FK to `user`, `company`)
12. `refresh_token` (FK to `user`)
13. `company_membership` (FK to `user`, `company`)
14. `domain_join_policy` (FK to `company`)
15. `invitation` (FK to `company`, `user`)
16. `join_request` (FK to `user`, `company`)
17. `onboarding_progress` (FK to `user`, `company`)
18. `password_reset_token` (FK to `user`)
19. `audit_record` (no FK)
20. `space_membership` (FK to `space`, `user`)
