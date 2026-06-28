# Research: API Clean Architecture Refactor

## Question 1: SQLAlchemy 2.0 cross-file relationship handling

**Decision**: Use `from __future__ import annotations` + `TYPE_CHECKING` imports + string-based `relationship()` references.

**Rationale**: SQLAlchemy 2.0 with `DeclarativeBase` resolves `relationship("ClassName")` string references at mapper configuration time, not import time. This means model files do not need to import each other at module scope. For the `Mapped[list[RelatedModel]]` type annotations, `from __future__ import annotations` defers evaluation so Python never actually resolves the type at class definition, and the type import is gated under `TYPE_CHECKING` so it is only evaluated by type checkers (mypy/pyright) not at runtime.

**Alternatives considered**:
- Lazy imports inside methods — rejected because it hides the type contract from IDEs and type checkers
- Putting all FK-related models in the same file — rejected, defeats the purpose of the refactor
- Using `Optional[ForwardRef("RolePermissionModel")]` — more verbose and non-idiomatic for SQLAlchemy 2.x

## Question 2: Backward-compat strategy — shim file vs. deleted file + updated callers

**Decision**: Keep original filenames as thin re-export shims.

**Rationale**: The spec (FR-006, FR-008) requires no changes to test logic and no changes to import paths outside the split package. Keeping `entities.py`, `repositories.py`, `providers.py`, `models.py`, `repo.py` as shims achieves this with zero diff in caller files. The shims can be removed in a separate cleanup PR once callers have been migrated.

**Alternatives considered**:
- Mass-update all callers — rejected because it touches 30+ files outside the split packages and increases merge conflict surface
- Replace old filenames with `__init__.py` re-exports only — `from tessera_core.domain.entities import X` would break (the submodule path would not resolve); shim file is required

## Question 3: Alembic metadata discovery after models split

**Decision**: The `models/__init__.py` imports all model files in FK-dependency order. The `models.py` shim additionally imports `Base` and all models. `db/migrations/env.py` requires no change.

**Rationale**: Alembic reads `Base.metadata` which only contains table definitions for models that have been imported (and thus registered via the metaclass). As long as all models are imported before `Base.metadata` is accessed, autogenerate works correctly.

**Alternatives considered**:
- Updating `env.py` to import from the new package — valid but unnecessary if the shim handles it
- Using `Base.metadata.reflect()` — not applicable (we control all models)

## Question 4: Enum file granularity

**Decision**: One file per enum, since enums are imported independently by multiple callers.

**Rationale**: Looking at the codebase, `Confidentiality` is imported by `RolePermission`, `Document`, `Chunk`, `AgentCredential`, and multiple routers independently. If `Confidentiality` lived in `document.py`, then `chunk.py` and `role_permission.py` would have to import from `document.py`, creating a confusing dependency. Independent files prevent any inter-entity dependencies at the domain layer.

**Alternatives considered**:
- Co-locate each enum with its "primary" entity — rejected because enums are shared; creates artificial coupling
- Single enums file — rejected; defeats one-class-per-file goal

## Question 5: Repository helper functions (private `_X_from_model` functions)

**Decision**: Move each helper function into the same file as its associated `Sql*Repository` class.

**Rationale**: These functions are implementation details of the repository, not shared utilities. Each `_doc_from_model`, `_space_from_model`, etc. is used only by one `Sql*Repository` class. Co-locating them in the same file keeps cohesion high and makes each repository file self-contained.

**Alternatives considered**:
- Shared `_converters.py` file — rejected; the converters are tightly coupled to their repositories and splitting them creates an unnecessary indirection
- Inline conversion in each method — rejected; reduces readability and duplicates code within the same class

## Question 6: `RefreshTokenRepository` — abstract port mismatch

**Observation**: `RefreshTokenRepository` ABC is defined in `ports/repositories.py`, but `SqlRefreshTokenRepository` in `repo.py` does **not** inherit from it (it is a standalone class with a larger interface than the ABC). This is existing behaviour; the refactor preserves it exactly.

**Decision**: `SqlRefreshTokenRepository` goes into `adapters/repositories/refresh_token.py` as-is (not inheriting from the ABC). The `repo.py` shim re-exports it. No fix is in scope for this refactor.
