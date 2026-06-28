# Import Contracts: API Clean Architecture Refactor

This document specifies the public import surface that must remain stable after the refactor. All paths listed here must continue to work without modification.

## Domain Package

All symbols currently importable from `tessera_core.domain.entities` must remain importable from the same path:

```python
# These import paths must continue to work unchanged
from tessera_core.domain.entities import (
    Space, User, Document, DocumentVersion, Chunk,
    Connector, SourceArtifact, UpdateProposal,
    AgentCredential, RefreshToken, PasswordResetToken,
    AuditRecord, RolePermission, Company, CompanyMembership,
    DomainJoinPolicy, Invitation, JoinRequest, OnboardingProgress,
    SpaceMembership,
    # Enums
    DocumentLifecycleState, Confidentiality, UserRole, ProposalState,
    SpaceRole, CompanyRole, DomainPolicy, InvitationStatus, JoinRequestStatus,
)

# Also importable via package namespace (no change needed here currently)
from tessera_core.domain import Space  # via __init__.py
```

## Ports Package

```python
# Repository ABCs — unchanged
from tessera_core.ports.repositories import (
    SpaceRepository, DocumentRepository, DocumentVersionRepository,
    ChunkRepository, ConnectorRepository, SourceArtifactRepository,
    ProposalRepository, UserRepository, AgentCredentialRepository,
    AuditRepository, OnboardingRepository, CompanyRepository,
    DomainPolicyRepository, InvitationRepository, JoinRequestRepository,
    PasswordResetTokenRepository, RefreshTokenRepository, SpaceMembershipRepository,
)

# Provider ABCs — unchanged
from tessera_core.ports.providers import LLMProvider, EmbeddingProvider, EmailPort
```

## API Adapters Package

```python
# ORM Models — unchanged
from tessera_api.adapters.models import (
    Base,
    UserModel, SpaceModel, RolePermissionModel, DocumentModel,
    DocumentVersionModel, ConnectorModel, SourceArtifactModel,
    UpdateProposalModel, AgentCredentialModel, RefreshTokenModel,
    CompanyModel, CompanyMembershipModel, DomainJoinPolicyModel,
    InvitationModel, JoinRequestModel, OnboardingProgressModel,
    PasswordResetTokenModel, AuditRecordModel, SpaceMembershipModel,
)

# SQL Repositories — unchanged
from tessera_api.adapters.repo import (
    SqlSpaceRepository, SqlDocumentRepository, SqlDocumentVersionRepository,
    SqlChunkRepository, SqlConnectorRepository, SqlSourceArtifactRepository,
    SqlProposalRepository, SqlUserRepository, SqlAgentCredentialRepository,
    SqlAuditRepository, SqlRefreshTokenRepository, SqlOnboardingRepository,
    SqlCompanyRepository, SqlDomainPolicyRepository, SqlInvitationRepository,
    SqlJoinRequestRepository, SqlPasswordResetTokenRepository,
    SqlSpaceMembershipRepository,
)
```

## Alembic Contract

The following import in `db/migrations/env.py` must remain valid with zero changes:

```python
from tessera_api.adapters.models import Base
target_metadata = Base.metadata
```

After the refactor, `Base.metadata` must contain all 20 table definitions when this import executes.

## New Import Paths (Optional — for future migration)

After the refactor, the following new paths also become valid (though not required):

```python
from tessera_core.domain.space import Space
from tessera_core.domain.document import Document
from tessera_core.ports.repositories.space import SpaceRepository
from tessera_api.adapters.models.space import SpaceModel
from tessera_api.adapters.repositories.space import SqlSpaceRepository
```
