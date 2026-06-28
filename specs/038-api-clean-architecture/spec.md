# Feature Specification: API Clean Architecture Refactor

**Feature Branch**: `038-api-clean-architecture`

**Created**: 2026-06-28

**Status**: Draft

**Input**: User description: "refactor api to clean architecture. Each class must have its own file"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Navigates to a Domain Entity (Priority: P1)

A backend developer needs to locate the `Space` domain entity to understand its
structure. Today they must scroll through a 300-line `entities.py` file shared
with 20 other classes. After the refactor, they open `domain/space.py` directly
and see only the `Space` class.

**Why this priority**: Navigation is the most frequent daily friction. Making each
class live in its own file is the core deliverable; everything else flows from it.

**Independent Test**: A developer can navigate to any single class by knowing only
its concept name — no scrolling or searching within a file required.

**Acceptance Scenarios**:

1. **Given** a developer knows the concept "Space", **When** they open
   `tessera_core/domain/space.py`, **Then** they find exactly the `Space` entity
   and nothing else.
2. **Given** a developer knows the concept "SqlSpaceRepository", **When** they
   open the repository adapter file for spaces, **Then** they see only
   `SqlSpaceRepository` — no other repository class.
3. **Given** any class is relocated to its own file, **When** the existing import
   paths (used by routers, services, tests) are updated, **Then** the application
   starts and all existing tests continue to pass without modification to test logic.

---

### User Story 2 - Developer Adds a New Entity Without Merge Conflicts (Priority: P2)

Two developers work simultaneously — one adds a `Tag` entity and another modifies
`Document`. Today both must edit the same `entities.py` file, producing merge
conflicts. After the refactor, each touches only their own file.

**Why this priority**: Parallel development friction is the second most common
pain caused by the current monolithic files.

**Independent Test**: Two branches each modifying different entity files can be
merged without conflicts on the entity layer.

**Acceptance Scenarios**:

1. **Given** two branches each create or modify different domain entity files,
   **When** the branches are merged, **Then** no merge conflict arises in any
   domain or adapter file.
2. **Given** a developer adds a new SQLAlchemy model, **When** they create a new
   file following the established one-class-per-file pattern, **Then** the new
   model is automatically discoverable by the ORM metadata without editing any
   shared registry file.

---

### User Story 3 - Developer Understands the Architecture at a Glance (Priority: P3)

A new team member joins and wants to understand what entities and repositories
the system has. After the refactor, they can list the files in each directory
and immediately see every concept modeled in the system.

**Why this priority**: Discoverability improves onboarding; it is valuable but
secondary to the mechanics of the refactor itself.

**Independent Test**: Running `ls` on `domain/`, `ports/repositories/`,
`adapters/models/`, and `adapters/repositories/` gives a human-readable index
of every concept without reading any file content.

**Acceptance Scenarios**:

1. **Given** the refactored structure, **When** a developer lists the
   `domain/` directory, **Then** every domain concept appears as a dedicated
   file (e.g., `space.py`, `document.py`, `user.py`).
2. **Given** the refactored structure, **When** a developer lists
   `adapters/repositories/`, **Then** each repository implementation appears as
   its own file (e.g., `space_repository.py`, `document_repository.py`).

---

### Edge Cases

- What happens to circular imports when entities that reference each other are
  split into separate files? The refactor must resolve inter-entity dependencies
  via explicit cross-file imports without introducing circular dependency cycles.
- How are SQLAlchemy model relationships (foreign keys, `relationship()`) preserved
  when the related models live in different files? All `Base` metadata must remain
  unified so Alembic autogeneration continues to work.
- What happens to wildcard re-exports in `__init__.py` files? Each package's
  `__init__.py` must re-export all public symbols so that any code importing from
  the package namespace continues to work unchanged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each domain entity class and enum currently in `entities.py` MUST be
  moved to its own dedicated file under `tessera_core/domain/`.
- **FR-002**: Each repository port (abstract base class) currently in
  `repositories.py` MUST be moved to its own dedicated file under
  `tessera_core/ports/repositories/`.
- **FR-003**: Each provider port (abstract base class) currently in `providers.py`
  MUST be moved to its own dedicated file under `tessera_core/ports/providers/`.
- **FR-004**: Each SQLAlchemy ORM model currently in `adapters/models.py` MUST be
  moved to its own dedicated file under `tessera_api/adapters/models/`.
- **FR-005**: Each SQL repository implementation currently in `adapters/repo.py`
  MUST be moved to its own dedicated file under `tessera_api/adapters/repositories/`.
- **FR-006**: Each package that is split MUST expose a backward-compatible
  `__init__.py` that re-exports all previously public symbols, so no caller outside
  the split package requires import-path changes.
- **FR-007**: The SQLAlchemy declarative `Base` MUST remain a single shared object
  imported by all ORM model files, ensuring Alembic metadata discovery continues
  to work without changes to migration configuration.
- **FR-008**: The full test suite MUST pass after the refactor with zero changes
  to test logic (only import paths in tests may change if they imported directly
  from the old monolithic files).
- **FR-009**: Code quality gates (Ruff, Black) MUST pass on all refactored files.
- **FR-010**: No new business logic MUST be introduced during this refactor; it is
  a structural-only change.

### Key Entities

- **Domain Entities** (`tessera_core/domain/`): The 20+ domain model classes and
  enums — `Space`, `Document`, `User`, `Company`, `Connector`, `Proposal`,
  `Invitation`, `SpaceMembership`, etc. — each becoming a standalone file.
- **Repository Ports** (`tessera_core/ports/repositories/`): The 16 abstract
  repository interfaces — `SpaceRepository`, `DocumentRepository`,
  `UserRepository`, etc. — each becoming a standalone file.
- **ORM Models** (`tessera_api/adapters/models/`): The 19 SQLAlchemy table-mapped
  classes — `SpaceModel`, `DocumentModel`, `UserModel`, etc. — each becoming a
  standalone file sharing a single `Base`.
- **SQL Repository Implementations** (`tessera_api/adapters/repositories/`): The
  17 concrete repository classes — `SqlSpaceRepository`,
  `SqlDocumentRepository`, etc. — each becoming a standalone file.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every Python file in `domain/`, `ports/repositories/`,
  `ports/providers/`, `adapters/models/`, and `adapters/repositories/` contains
  exactly one class (or one tightly related group of enums belonging to the same
  concept).
- **SC-002**: The full automated test suite passes with the same pass/fail results
  as before the refactor (no regressions introduced).
- **SC-003**: Code quality checks (linting and formatting) pass on 100% of
  refactored files.
- **SC-004**: The Alembic migration tooling detects no schema changes when run
  after the refactor, confirming ORM metadata is intact.
- **SC-005**: No file in the refactored structure exceeds 150 lines, as a proxy
  for confirming true one-class-per-file discipline.

## Assumptions

- The routers (`tessera_api/routers/`) are already one-file-per-router and are
  out of scope for this refactor.
- Services (`tessera_core/services/`) are already reasonably scoped (one service
  per file) and are out of scope unless a service file contains multiple classes.
- The `auth/`, `rag/`, `eval/`, and `adapters/audit.py` etc. modules are
  single-concern files and are out of scope unless they contain multiple classes.
- Backward-compatible `__init__.py` re-exports are sufficient; callers are not
  required to update their import paths as part of this feature.
- The refactor is purely structural; no behavioral changes, performance
  improvements, or new features are part of this scope.
- The existing 85%+ test coverage requirement applies to the refactored code.
