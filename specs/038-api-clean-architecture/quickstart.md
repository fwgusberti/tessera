# Quickstart Validation Guide: API Clean Architecture Refactor

## Goal

Verify that the refactor is complete and correct — all classes in their own files, all existing imports still work, no schema drift.

## Prerequisites

- Python 3.12 environment with dependencies installed
- A running PostgreSQL instance (for Alembic check)
- From repo root: `cd apps/api && source .venv/bin/activate`

## Step 1: Directory Structure Check

Confirm each target directory exists and contains one file per class:

```bash
# Domain entities — should show ~29 .py files
ls packages/core/tessera_core/domain/*.py | wc -l

# Repository ports — should show ~18 .py files
ls packages/core/tessera_core/ports/repositories/*.py | wc -l

# Provider ports — should show 3 .py files
ls packages/core/tessera_core/ports/providers/*.py | wc -l

# ORM models — should show ~20 .py files
ls apps/api/tessera_api/adapters/models/*.py | wc -l

# Repository implementations — should show ~18 .py files
ls apps/api/tessera_api/adapters/repositories/*.py | wc -l
```

## Step 2: File Size Check (SC-005)

Verify no refactored file exceeds 150 lines:

```bash
# Check domain files
find packages/core/tessera_core/domain -name "*.py" ! -name "__init__.py" ! -name "entities.py" \
  -exec awk 'END{if(NR>150) print FILENAME": "NR" lines"}' {} \;

# Check ORM model files
find apps/api/tessera_api/adapters/models -name "*.py" ! -name "__init__.py" ! -name "base.py" \
  -exec awk 'END{if(NR>150) print FILENAME": "NR" lines"}' {} \;

# Check repository files
find apps/api/tessera_api/adapters/repositories -name "*.py" ! -name "__init__.py" \
  -exec awk 'END{if(NR>150) print FILENAME": "NR" lines"}' {} \;
```

Expected: no output (no files over 150 lines)

## Step 3: Import Path Compatibility Check (FR-006)

Verify all legacy import paths resolve:

```bash
cd apps/api && python -c "
from tessera_core.domain.entities import (
    Space, User, Document, DocumentVersion, Chunk,
    Connector, SourceArtifact, UpdateProposal, AgentCredential,
    RefreshToken, PasswordResetToken, AuditRecord, RolePermission,
    Company, CompanyMembership, DomainJoinPolicy, Invitation,
    JoinRequest, OnboardingProgress, SpaceMembership,
    DocumentLifecycleState, Confidentiality, UserRole, ProposalState,
    SpaceRole, CompanyRole, DomainPolicy, InvitationStatus, JoinRequestStatus,
)
from tessera_core.ports.repositories import (
    SpaceRepository, DocumentRepository, DocumentVersionRepository,
    ChunkRepository, ConnectorRepository, SourceArtifactRepository,
    ProposalRepository, UserRepository, AgentCredentialRepository,
    AuditRepository, OnboardingRepository, CompanyRepository,
    DomainPolicyRepository, InvitationRepository, JoinRequestRepository,
    PasswordResetTokenRepository, RefreshTokenRepository, SpaceMembershipRepository,
)
from tessera_core.ports.providers import LLMProvider, EmbeddingProvider, EmailPort
from tessera_api.adapters.models import (
    Base, UserModel, SpaceModel, RolePermissionModel, DocumentModel,
    DocumentVersionModel, ConnectorModel, SourceArtifactModel,
    UpdateProposalModel, AgentCredentialModel, RefreshTokenModel,
    CompanyModel, CompanyMembershipModel, DomainJoinPolicyModel,
    InvitationModel, JoinRequestModel, OnboardingProgressModel,
    PasswordResetTokenModel, AuditRecordModel, SpaceMembershipModel,
)
from tessera_api.adapters.repo import (
    SqlSpaceRepository, SqlDocumentRepository, SqlDocumentVersionRepository,
    SqlChunkRepository, SqlConnectorRepository, SqlSourceArtifactRepository,
    SqlProposalRepository, SqlUserRepository, SqlAgentCredentialRepository,
    SqlAuditRepository, SqlRefreshTokenRepository, SqlOnboardingRepository,
    SqlCompanyRepository, SqlDomainPolicyRepository, SqlInvitationRepository,
    SqlJoinRequestRepository, SqlPasswordResetTokenRepository,
    SqlSpaceMembershipRepository,
)
print('All imports OK')
"
```

Expected output: `All imports OK`

## Step 4: Alembic Metadata Check (SC-004)

Verify Alembic detects no schema changes:

```bash
cd db && alembic check
```

Expected: `No new upgrade operations detected.`

If the `alembic check` command is unavailable, use:

```bash
cd db && alembic upgrade --sql head | grep -c "CREATE TABLE\|ALTER TABLE\|DROP TABLE"
```

Expected: `0` (no DDL statements)

## Step 5: Full Test Suite (SC-002)

```bash
# tessera_core unit tests
cd packages/core && python -m pytest tests/ -v

# tessera_api full suite
cd apps/api && python -m pytest tests/ -v --tb=short
```

Expected: Same pass/fail results as before the refactor. Known pre-existing failures (`test_ports`, `migration_0002`, `tessera_mcp`) may still appear — these are NOT regressions of this refactor.

## Step 6: Code Quality Gates (SC-003)

```bash
# From repo root
ruff check packages/core/tessera_core/domain/
ruff check packages/core/tessera_core/ports/
ruff check apps/api/tessera_api/adapters/models/
ruff check apps/api/tessera_api/adapters/repositories/

black --check packages/core/tessera_core/domain/
black --check packages/core/tessera_core/ports/
black --check apps/api/tessera_api/adapters/models/
black --check apps/api/tessera_api/adapters/repositories/
```

Expected: exit code 0, no violations.

## Step 7: Conceptual Navigation Check (User Story 1)

```bash
# A developer knows "Space" — can they go directly to the file?
ls packages/core/tessera_core/domain/space.py         # should exist
grep "^class Space" packages/core/tessera_core/domain/space.py  # should show: class Space(BaseModel):

# A developer knows "SqlSpaceRepository"
ls apps/api/tessera_api/adapters/repositories/space.py
grep "^class SqlSpaceRepository" apps/api/tessera_api/adapters/repositories/space.py
```

Expected: each `ls` resolves and each `grep` returns exactly one line.
