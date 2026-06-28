# Tasks: API Clean Architecture Refactor

**Input**: Design documents from `/specs/038-api-clean-architecture/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/import-contracts.md ✅, quickstart.md ✅

**Tests**: Not requested — this is a structural-only refactor. FR-008 requires existing tests pass unchanged; no new test tasks are generated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each layer.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All tasks include exact file paths

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new package directories that host the one-class-per-file layout.

- [X] T001 Create four new package directories with empty `__init__.py` stubs: `packages/core/tessera_core/ports/repositories/`, `packages/core/tessera_core/ports/providers/`, `apps/api/tessera_api/adapters/models/`, `apps/api/tessera_api/adapters/repositories/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extract the shared SQLAlchemy `Base` before any ORM model file can be written.

**⚠️ CRITICAL**: Phase 4 (US2) cannot begin until T002 is complete.

- [X] T002 Extract `DeclarativeBase` subclass to `apps/api/tessera_api/adapters/models/base.py` — copy `Base` definition verbatim from existing `models.py`, no other content

**Checkpoint**: `base.py` exists — ORM model files can now be created in Phase 4.

---

## Phase 3: User Story 1 — Developer Navigates to a Domain Entity (P1) 🎯 MVP

**Goal**: Every domain entity, enum, repository port, and provider port lives in its own file. Legacy import paths continue to work.

**Independent Test**: `from tessera_core.domain.entities import Space` resolves AND `open packages/core/tessera_core/domain/space.py` shows only the `Space` class.

### Domain Enums (all parallelizable — no inter-file dependencies)

- [X] T003 [P] [US1] Create `packages/core/tessera_core/domain/document_lifecycle_state.py` with `DocumentLifecycleState` enum (cut from `entities.py`)
- [X] T004 [P] [US1] Create `packages/core/tessera_core/domain/confidentiality.py` with `Confidentiality` enum (cut from `entities.py`)
- [X] T005 [P] [US1] Create `packages/core/tessera_core/domain/user_role.py` with `UserRole` enum (cut from `entities.py`)
- [X] T006 [P] [US1] Create `packages/core/tessera_core/domain/proposal_state.py` with `ProposalState` enum (cut from `entities.py`)
- [X] T007 [P] [US1] Create `packages/core/tessera_core/domain/space_role.py` with `SpaceRole` enum (cut from `entities.py`)
- [X] T008 [P] [US1] Create `packages/core/tessera_core/domain/company_role.py` with `CompanyRole` enum (cut from `entities.py`)
- [X] T009 [P] [US1] Create `packages/core/tessera_core/domain/domain_policy_enum.py` with `DomainPolicy` enum (cut from `entities.py`)
- [X] T010 [P] [US1] Create `packages/core/tessera_core/domain/invitation_status.py` with `InvitationStatus` enum (cut from `entities.py`)
- [X] T011 [P] [US1] Create `packages/core/tessera_core/domain/join_request_status.py` with `JoinRequestStatus` enum (cut from `entities.py`)

### Domain Entities — No Enum Dependencies (parallelizable)

- [X] T012 [P] [US1] Create `packages/core/tessera_core/domain/space.py` with `Space` Pydantic model (cut from `entities.py`)
- [X] T013 [P] [US1] Create `packages/core/tessera_core/domain/user.py` with `User` Pydantic model (cut from `entities.py`)
- [X] T014 [P] [US1] Create `packages/core/tessera_core/domain/document_version.py` with `DocumentVersion` Pydantic model (cut from `entities.py`)
- [X] T015 [P] [US1] Create `packages/core/tessera_core/domain/connector.py` with `Connector` Pydantic model (cut from `entities.py`)
- [X] T016 [P] [US1] Create `packages/core/tessera_core/domain/source_artifact.py` with `SourceArtifact` Pydantic model (cut from `entities.py`)
- [X] T017 [P] [US1] Create `packages/core/tessera_core/domain/refresh_token.py` with `RefreshToken` Pydantic model (cut from `entities.py`)
- [X] T018 [P] [US1] Create `packages/core/tessera_core/domain/password_reset_token.py` with `PasswordResetToken` Pydantic model (cut from `entities.py`)
- [X] T019 [P] [US1] Create `packages/core/tessera_core/domain/audit_record.py` with `AuditRecord` Pydantic model (cut from `entities.py`)
- [X] T020 [P] [US1] Create `packages/core/tessera_core/domain/company.py` with `Company` Pydantic model (cut from `entities.py`)
- [X] T021 [P] [US1] Create `packages/core/tessera_core/domain/onboarding_progress.py` with `OnboardingProgress` Pydantic model (cut from `entities.py`)

### Domain Entities — Enum Dependencies (parallelizable after enums, T003–T011)

- [X] T022 [P] [US1] Create `packages/core/tessera_core/domain/document.py` with `Document` Pydantic model importing `DocumentLifecycleState` from `document_lifecycle_state` and `Confidentiality` from `confidentiality` (cut from `entities.py`)
- [X] T023 [P] [US1] Create `packages/core/tessera_core/domain/chunk.py` with `Chunk` Pydantic model importing `Confidentiality` from `confidentiality` (cut from `entities.py`)
- [X] T024 [P] [US1] Create `packages/core/tessera_core/domain/role_permission.py` with `RolePermission` Pydantic model importing `UserRole` from `user_role` and `Confidentiality` from `confidentiality` (cut from `entities.py`)
- [X] T025 [P] [US1] Create `packages/core/tessera_core/domain/update_proposal.py` with `UpdateProposal` Pydantic model importing `ProposalState` from `proposal_state` (cut from `entities.py`)
- [X] T026 [P] [US1] Create `packages/core/tessera_core/domain/agent_credential.py` with `AgentCredential` Pydantic model importing `Confidentiality` from `confidentiality` (cut from `entities.py`)
- [X] T027 [P] [US1] Create `packages/core/tessera_core/domain/space_membership.py` with `SpaceMembership` Pydantic model importing `SpaceRole` from `space_role` (cut from `entities.py`)
- [X] T028 [P] [US1] Create `packages/core/tessera_core/domain/company_membership.py` with `CompanyMembership` Pydantic model importing `CompanyRole` from `company_role` (cut from `entities.py`)
- [X] T029 [P] [US1] Create `packages/core/tessera_core/domain/domain_join_policy.py` with `DomainJoinPolicy` Pydantic model importing `DomainPolicy` from `domain_policy_enum` (cut from `entities.py`)
- [X] T030 [P] [US1] Create `packages/core/tessera_core/domain/invitation.py` with `Invitation` Pydantic model importing `InvitationStatus` from `invitation_status` (cut from `entities.py`)
- [X] T031 [P] [US1] Create `packages/core/tessera_core/domain/join_request.py` with `JoinRequest` Pydantic model importing `JoinRequestStatus` from `join_request_status` (cut from `entities.py`)

### Port Providers (all parallelizable — no inter-file dependencies)

- [X] T032 [P] [US1] Create `packages/core/tessera_core/ports/providers/llm.py` with `LLMProvider` ABC (cut from `providers.py`)
- [X] T033 [P] [US1] Create `packages/core/tessera_core/ports/providers/embedding.py` with `EmbeddingProvider` ABC (cut from `providers.py`)
- [X] T034 [P] [US1] Create `packages/core/tessera_core/ports/providers/email.py` with `EmailPort` ABC (cut from `providers.py`)

### Port Repositories (all parallelizable — independent ABCs)

- [X] T035 [P] [US1] Create `packages/core/tessera_core/ports/repositories/space.py` with `SpaceRepository` ABC importing `Space`, `RolePermission` from the new domain files (cut from `repositories.py`)
- [X] T036 [P] [US1] Create `packages/core/tessera_core/ports/repositories/document.py` with `DocumentRepository` ABC importing `Document`, `DocumentLifecycleState` from new domain files (cut from `repositories.py`)
- [X] T037 [P] [US1] Create `packages/core/tessera_core/ports/repositories/document_version.py` with `DocumentVersionRepository` ABC importing `DocumentVersion` from new domain files (cut from `repositories.py`)
- [X] T038 [P] [US1] Create `packages/core/tessera_core/ports/repositories/chunk.py` with `ChunkRepository` ABC importing `Chunk` from new domain files (cut from `repositories.py`)
- [X] T039 [P] [US1] Create `packages/core/tessera_core/ports/repositories/connector.py` with `ConnectorRepository` ABC importing `Connector` from new domain files (cut from `repositories.py`)
- [X] T040 [P] [US1] Create `packages/core/tessera_core/ports/repositories/source_artifact.py` with `SourceArtifactRepository` ABC importing `SourceArtifact` from new domain files (cut from `repositories.py`)
- [X] T041 [P] [US1] Create `packages/core/tessera_core/ports/repositories/proposal.py` with `ProposalRepository` ABC importing `UpdateProposal` from new domain files (cut from `repositories.py`)
- [X] T042 [P] [US1] Create `packages/core/tessera_core/ports/repositories/user.py` with `UserRepository` ABC importing `User` from new domain files (cut from `repositories.py`)
- [X] T043 [P] [US1] Create `packages/core/tessera_core/ports/repositories/agent_credential.py` with `AgentCredentialRepository` ABC importing `AgentCredential` from new domain files (cut from `repositories.py`)
- [X] T044 [P] [US1] Create `packages/core/tessera_core/ports/repositories/audit.py` with `AuditRepository` ABC importing `AuditRecord` from new domain files (cut from `repositories.py`)
- [X] T045 [P] [US1] Create `packages/core/tessera_core/ports/repositories/onboarding.py` with `OnboardingRepository` ABC importing `OnboardingProgress` from new domain files (cut from `repositories.py`)
- [X] T046 [P] [US1] Create `packages/core/tessera_core/ports/repositories/company.py` with `CompanyRepository` ABC importing `Company`, `CompanyMembership` from new domain files (cut from `repositories.py`)
- [X] T047 [P] [US1] Create `packages/core/tessera_core/ports/repositories/domain_policy.py` with `DomainPolicyRepository` ABC importing `DomainJoinPolicy` from new domain files (cut from `repositories.py`)
- [X] T048 [P] [US1] Create `packages/core/tessera_core/ports/repositories/invitation.py` with `InvitationRepository` ABC importing `Invitation`, `InvitationStatus` from new domain files (cut from `repositories.py`)
- [X] T049 [P] [US1] Create `packages/core/tessera_core/ports/repositories/join_request.py` with `JoinRequestRepository` ABC importing `JoinRequest`, `JoinRequestStatus` from new domain files (cut from `repositories.py`)
- [X] T050 [P] [US1] Create `packages/core/tessera_core/ports/repositories/password_reset_token.py` with `PasswordResetTokenRepository` ABC importing `PasswordResetToken` from new domain files (cut from `repositories.py`)
- [X] T051 [P] [US1] Create `packages/core/tessera_core/ports/repositories/refresh_token.py` with `RefreshTokenRepository` ABC (UUID-only interface, cut from `repositories.py`)
- [X] T052 [P] [US1] Create `packages/core/tessera_core/ports/repositories/space_membership.py` with `SpaceMembershipRepository` ABC importing `SpaceMembership`, `SpaceRole` from new domain files (cut from `repositories.py`)

### Re-export `__init__.py` files and backward-compat shims (US1)

- [X] T053 [US1] Write `packages/core/tessera_core/domain/__init__.py` re-exporting all 29 domain symbols (9 enums + 20 entities) from their new individual files; `__all__` must match current `entities.py` public surface
- [X] T054 [US1] Convert `packages/core/tessera_core/domain/entities.py` to a backward-compat shim: replace body with `from tessera_core.domain.<module> import <Class>` for all 29 symbols; preserve `__all__`
- [X] T055 [US1] Write `packages/core/tessera_core/ports/providers/__init__.py` re-exporting `LLMProvider`, `EmbeddingProvider`, `EmailPort` from their new files
- [X] T056 [US1] Convert `packages/core/tessera_core/ports/providers.py` to a backward-compat shim re-exporting `LLMProvider`, `EmbeddingProvider`, `EmailPort` from `tessera_core.ports.providers.*`
- [X] T057 [US1] Write `packages/core/tessera_core/ports/repositories/__init__.py` re-exporting all 18 repository ABCs from their new individual files
- [X] T058 [US1] Convert `packages/core/tessera_core/ports/repositories.py` to a backward-compat shim re-exporting all 18 ABCs from `tessera_core.ports.repositories.*`

**Checkpoint**: US1 complete — `from tessera_core.domain.entities import Space` resolves; `cat packages/core/tessera_core/domain/space.py` shows only `Space`; all existing import paths work unchanged.

---

## Phase 4: User Story 2 — Developer Adds a New Entity Without Merge Conflicts (P2)

**Goal**: Every ORM model and SQL repository implementation lives in its own file. Alembic metadata discovery works via `models/__init__.py` import order. A new model can be added by creating a single new file.

**Independent Test**: `alembic check` reports zero schema changes; `from tessera_api.adapters.repo import SqlSpaceRepository` resolves; `cat apps/api/tessera_api/adapters/repositories/space.py` shows only `SqlSpaceRepository`.

### ORM Models (all parallelizable — each imports only `Base` from `models.base`, no cross-model imports at module scope)

- [X] T059 [P] [US2] Create `apps/api/tessera_api/adapters/models/user.py` with `UserModel` — add `from __future__ import annotations`, import `Base` from `tessera_api.adapters.models.base` (cut from `models.py`)
- [X] T060 [P] [US2] Create `apps/api/tessera_api/adapters/models/company.py` with `CompanyModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated import for `UserModel` (cut from `models.py`)
- [X] T061 [P] [US2] Create `apps/api/tessera_api/adapters/models/space.py` with `SpaceModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated import for `CompanyModel` (cut from `models.py`)
- [X] T062 [P] [US2] Create `apps/api/tessera_api/adapters/models/role_permission.py` with `RolePermissionModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated import for `SpaceModel` (cut from `models.py`)
- [X] T063 [P] [US2] Create `apps/api/tessera_api/adapters/models/document.py` with `DocumentModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated imports for `SpaceModel`, `UserModel` (cut from `models.py`)
- [X] T064 [P] [US2] Create `apps/api/tessera_api/adapters/models/document_version.py` with `DocumentVersionModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated imports for `DocumentModel`, `UserModel` (cut from `models.py`)
- [X] T065 [P] [US2] Create `apps/api/tessera_api/adapters/models/connector.py` with `ConnectorModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated import for `SpaceModel` (cut from `models.py`)
- [X] T066 [P] [US2] Create `apps/api/tessera_api/adapters/models/source_artifact.py` with `SourceArtifactModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated import for `ConnectorModel` (cut from `models.py`)
- [X] T067 [P] [US2] Create `apps/api/tessera_api/adapters/models/update_proposal.py` with `UpdateProposalModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated imports for `DocumentModel`, `SourceArtifactModel`, `UserModel` (cut from `models.py`)
- [X] T068 [P] [US2] Create `apps/api/tessera_api/adapters/models/agent_credential.py` with `AgentCredentialModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated imports for `UserModel`, `CompanyModel` (cut from `models.py`)
- [X] T069 [P] [US2] Create `apps/api/tessera_api/adapters/models/refresh_token.py` with `RefreshTokenModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated import for `UserModel` (cut from `models.py`)
- [X] T070 [P] [US2] Create `apps/api/tessera_api/adapters/models/company_membership.py` with `CompanyMembershipModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated imports for `UserModel`, `CompanyModel` (cut from `models.py`)
- [X] T071 [P] [US2] Create `apps/api/tessera_api/adapters/models/domain_join_policy.py` with `DomainJoinPolicyModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated import for `CompanyModel` (cut from `models.py`)
- [X] T072 [P] [US2] Create `apps/api/tessera_api/adapters/models/invitation.py` with `InvitationModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated imports for `CompanyModel`, `UserModel` (cut from `models.py`)
- [X] T073 [P] [US2] Create `apps/api/tessera_api/adapters/models/join_request.py` with `JoinRequestModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated imports for `UserModel`, `CompanyModel` (cut from `models.py`)
- [X] T074 [P] [US2] Create `apps/api/tessera_api/adapters/models/onboarding_progress.py` with `OnboardingProgressModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated imports for `UserModel`, `CompanyModel` (cut from `models.py`)
- [X] T075 [P] [US2] Create `apps/api/tessera_api/adapters/models/password_reset_token.py` with `PasswordResetTokenModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated import for `UserModel` (cut from `models.py`)
- [X] T076 [P] [US2] Create `apps/api/tessera_api/adapters/models/audit_record.py` with `AuditRecordModel` (no FK dependencies, cut from `models.py`)
- [X] T077 [P] [US2] Create `apps/api/tessera_api/adapters/models/space_membership.py` with `SpaceMembershipModel` — add `from __future__ import annotations`, TYPE_CHECKING-gated imports for `SpaceModel`, `UserModel` (cut from `models.py`)

### Models registry and shim

- [X] T078 [US2] Write `apps/api/tessera_api/adapters/models/__init__.py` importing all 19 model files in FK-dependency order (base → user → company → space → role_permission → document → document_version → connector → source_artifact → update_proposal → agent_credential → refresh_token → company_membership → domain_join_policy → invitation → join_request → onboarding_progress → password_reset_token → audit_record → space_membership); re-export `Base` and all model classes so `from tessera_api.adapters.models import SpaceModel` works
- [X] T079 [US2] Convert `apps/api/tessera_api/adapters/models.py` to a backward-compat shim: import `Base` and all 19 model classes from `tessera_api.adapters.models.*`; preserve `__all__` so Alembic's `from tessera_api.adapters.models import Base` continues to see fully-populated `Base.metadata`

### SQL Repository Implementations (all parallelizable — each file is independent)

- [X] T080 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/space.py` with `SqlSpaceRepository` and helpers `_space_from_model`, `_perm_from_model` (cut from `repo.py`)
- [X] T081 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/document.py` with `SqlDocumentRepository` and `_doc_from_model` (cut from `repo.py`)
- [X] T082 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/document_version.py` with `SqlDocumentVersionRepository` and `_version_from_model` (cut from `repo.py`)
- [X] T083 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/chunk.py` with `SqlChunkRepository` (no helper function, cut from `repo.py`)
- [X] T084 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/connector.py` with `SqlConnectorRepository` and `_connector_from_model` (cut from `repo.py`)
- [X] T085 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/source_artifact.py` with `SqlSourceArtifactRepository` and `_artifact_from_model` (cut from `repo.py`)
- [X] T086 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/proposal.py` with `SqlProposalRepository` and `_proposal_from_model` (cut from `repo.py`)
- [X] T087 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/user.py` with `SqlUserRepository` and `_user_from_model` (cut from `repo.py`)
- [X] T088 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/agent_credential.py` with `SqlAgentCredentialRepository` and `_credential_from_model` (cut from `repo.py`)
- [X] T089 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/audit.py` with `SqlAuditRepository` (no helper function, cut from `repo.py`)
- [X] T090 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/refresh_token.py` with `SqlRefreshTokenRepository` and `_refresh_token_from_model` — note: this class does NOT inherit from `RefreshTokenRepository` ABC (existing behaviour, preserve as-is, cut from `repo.py`)
- [X] T091 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/onboarding.py` with `SqlOnboardingRepository` and `_onboarding_from_model` (cut from `repo.py`)
- [X] T092 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/company.py` with `SqlCompanyRepository` and helpers `_company_from_model`, `_company_membership_from_model` (cut from `repo.py`)
- [X] T093 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/domain_policy.py` with `SqlDomainPolicyRepository` and `_domain_policy_from_model` (cut from `repo.py`)
- [X] T094 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/invitation.py` with `SqlInvitationRepository` and `_invitation_from_model` (cut from `repo.py`)
- [X] T095 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/join_request.py` with `SqlJoinRequestRepository` and `_join_request_from_model` (cut from `repo.py`)
- [X] T096 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/password_reset_token.py` with `SqlPasswordResetTokenRepository` and `_prt_from_model` (cut from `repo.py`)
- [X] T097 [P] [US2] Create `apps/api/tessera_api/adapters/repositories/space_membership.py` with `SqlSpaceMembershipRepository` and `_membership_from_model` (cut from `repo.py`)

### Repositories registry and shim

- [X] T098 [US2] Write `apps/api/tessera_api/adapters/repositories/__init__.py` re-exporting all 18 `Sql*Repository` classes from their new individual files
- [X] T099 [US2] Convert `apps/api/tessera_api/adapters/repo.py` to a backward-compat shim: re-export all 18 `Sql*Repository` classes from `tessera_api.adapters.repositories.*`; preserve `__all__`

**Checkpoint**: US2 complete — `alembic check` detects zero schema changes; each adapter file contains exactly one class; adding a new model requires only creating one new file and adding one import line to `models/__init__.py`.

---

## Phase 5: User Story 3 — Developer Understands the Architecture at a Glance (P3)

**Goal**: Running `ls` on any of the four refactored directories returns a human-readable, one-concept-per-file index of the system. Confirm all success criteria from quickstart.md.

**Independent Test**: `ls packages/core/tessera_core/domain/*.py | wc -l` returns ≥ 29; full test suite passes with same pass/fail baseline as before refactor.

### Validation

- [X] T100 [US3] Run quickstart.md Step 1: verify file counts — domain ≥29, ports/repositories = 18+2, ports/providers = 3+2, adapters/models ≥20, adapters/repositories ≥18 files
- [X] T101 [US3] Run quickstart.md Step 2: verify SC-005 — no refactored file exceeds 150 lines (use the `find … awk` commands from quickstart.md)
- [X] T102 [US3] Run quickstart.md Step 3: run the full import compatibility check Python script — expected output `All imports OK`
- [X] T103 [US3] Run quickstart.md Step 4: run `cd db && alembic check` — expected `No new upgrade operations detected.`
- [X] T104 [US3] Run quickstart.md Step 5: run the full test suite in `packages/core` and `apps/api` — confirm pass/fail results match pre-refactor baseline (pre-existing failures `test_ports`, `migration_0002`, `tessera_mcp` are expected)
- [X] T105 [US3] Run quickstart.md Step 6: run `ruff check` + `black --check` on all four refactored directories — expected exit 0
- [X] T106 [US3] Run quickstart.md Step 7: conceptual navigation check — `ls packages/core/tessera_core/domain/space.py` exists and `grep "^class Space" …` returns exactly one line; repeat for `SqlSpaceRepository`

**Checkpoint**: All success criteria SC-001 through SC-005 verified. Feature is shippable.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T107 [P] Remove any now-empty bodies from the original monolithic files (`entities.py`, `repositories.py`, `providers.py`, `models.py`, `repo.py`) that were not fully converted to shims — confirm shim `__all__` lists are complete and sorted alphabetically for readability
- [X] T108 Fix any Ruff or Black violations surfaced in T105 before marking feature complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — blocks Phase 4 ORM models
- **User Story 1 (Phase 3)**: Depends on Phase 1 — can run immediately after T001
  - Domain enum tasks (T003–T011): fully parallel
  - Domain entity tasks (T012–T021): parallel with each other and with enums
  - Domain entity tasks with enum deps (T022–T031): can start once their specific enum file exists
  - Port tasks (T032–T052): parallel; depend on the domain entity files they import
  - Shim/init tasks (T053–T058): depend on all entity/enum/port files in their package being created
- **User Story 2 (Phase 4)**: Depends on T002 (base.py)
  - ORM model tasks (T059–T077): all parallel — each only imports `Base`
  - T078: depends on T059–T077 all being done
  - T079: depends on T078
  - SQL repo tasks (T080–T097): parallel — depend on ORM model files existing
  - T098: depends on T080–T097
  - T099: depends on T098
- **User Story 3 (Phase 5)**: Depends on Phase 3 AND Phase 4 being complete
- **Polish (Phase 6)**: Depends on Phase 5 passing all checks

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 1 — independent of US2
- **US2 (P2)**: Starts after T002 — independent of US1 (adapters may import from new domain paths or old shim paths, both work)
- **US3 (P3)**: Requires US1 + US2 complete (validation only)

---

## Parallel Execution Examples

### Parallel burst for Phase 3 (US1) — Domain enums + leaf entities simultaneously

```
# Launch all 9 enums + 10 leaf entities together (T003–T021, all [P]):
T003  Create document_lifecycle_state.py
T004  Create confidentiality.py
T005  Create user_role.py
T006  Create proposal_state.py
T007  Create space_role.py
T008  Create company_role.py
T009  Create domain_policy_enum.py
T010  Create invitation_status.py
T011  Create join_request_status.py
T012  Create space.py
T013  Create user.py
T014  Create document_version.py
T015  Create connector.py
T016  Create source_artifact.py
T017  Create refresh_token.py
T018  Create password_reset_token.py
T019  Create audit_record.py
T020  Create company.py
T021  Create onboarding_progress.py

# Then launch entity files with enum deps (T022–T031) and port files (T032–T052):
# All 10 enum-dependent entities + 21 port files = 31 more parallel tasks
```

### Parallel burst for Phase 4 (US2) — All 19 ORM models simultaneously

```
# Launch T059–T077 together (all [P]):
T059  Create models/user.py
T060  Create models/company.py
...
T077  Create models/space_membership.py
# Then T078 (init), T079 (shim) sequentially
# Then launch T080–T097 together (all [P] SQL repos)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only — tessera_core package)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 3: US1 in parallel batches
3. **STOP and VALIDATE**: Run `python -c "from tessera_core.domain.entities import Space; print('OK')"` and `cd packages/core && python -m pytest tests/ -v`
4. Deploy/merge if tests pass

### Incremental Delivery

1. Setup (T001) → then launch US1 and US2 in parallel (US2 only needs T002 first)
2. US1 complete → core package refactored; existing callers unaffected
3. US2 complete → adapters refactored; Alembic intact
4. US3 → run quickstart.md validation; confirm all SC pass
5. Polish (Phase 6) → cleanup

### Parallel Team Strategy

- Developer A: Phase 3 domain enums + entities (T003–T031)
- Developer B: Phase 3 port providers + port repositories (T032–T058)
- Developer C: Phase 4 ORM models (T059–T079) — after T002
- Developer D: Phase 4 SQL repos (T080–T099) — after ORM models done

---

## Notes

- All tasks in this list are "cut and paste" refactors — no new business logic. Copy the existing class body verbatim; only change the import statements at the top.
- For ORM model files: string-based `relationship("ClassName")` calls already exist in `models.py` — keep them as-is; SQLAlchemy resolves them at mapper config time.
- `RefreshTokenRepository` ABC mismatch (research.md Q6): `SqlRefreshTokenRepository` does not inherit from the ABC — preserve this as-is in T090.
- Pre-existing test failures (`test_ports`, `migration_0002`, `tessera_mcp`) must NOT be counted as regressions in T104.
- Shim files (T054, T056, T058, T079, T099) MUST preserve `__all__` to avoid breaking star imports.
