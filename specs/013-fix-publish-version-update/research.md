# Research: Fix Publish — Record Approval on Existing Version

## Decision 1: How to record approval on a version

**Decision**: Add an `update_approval(version_id, approver_id, approved_at)` method to the `DocumentVersionRepository` port and its SQL implementation. The `publish_document` router calls this instead of `ver_repo.create(approved_version)`.

**Rationale**: The approval metadata (`approver_user_id`, `approved_at`) are mutable attributes on an existing, immutable-content version. An UPDATE is semantically correct — we are not changing the content or creating a new version; we are recording who approved this version and when. Using `ver_repo.create(approved_version)` with a copied UUID is a semantic error: CREATE means new content, not approval recording.

**Alternatives considered**:
- Add `version_id` to the `approved_version` model_copy update — rejected: still inserts a duplicate row (same `id` → primary key violation).
- Generate a new UUID for `approved_version` before create — rejected: creates a content-duplicate version with different identity, inflates version count, violates SC-003 and FR-002.
- Bypass the repository and issue a raw SQL UPDATE directly in the router — rejected: violates Domain-Driven Architecture (Constitution Principle I); business logic must flow through domain ports.

---

## Decision 2: Port definition location

**Decision**: Add `update_approval` to the abstract `DocumentVersionRepository` in `tessera_core/ports/repositories.py`, and implement it in `SqlDocumentVersionRepository` in `apps/api/tessera_api/adapters/repo.py`.

**Rationale**: The port already defines `create`, `get_by_id`, `list_by_document`, and `next_version_number`. Adding `update_approval` keeps the repository contract complete and lets tests mock it cleanly (as demonstrated in the existing contract test pattern). The constitution's Principle I requires domain ports, not ad-hoc SQL in the router.

**Alternatives considered**:
- Inline SQLAlchemy UPDATE in the router — rejected: business logic in infrastructure layer violates Principle I.
- Reuse `update_state` pattern (add generic update method) — rejected: over-generalizes; `update_approval` has a clear, bounded semantics that should be explicit.

---

## Decision 3: Test strategy

**Decision**: Add a contract test in `apps/api/tests/contract/test_documents.py` that verifies `ver_repo.update_approval` is called (not `ver_repo.create`) during publish. Follow the existing `AsyncMock + patch` pattern. Also add a unit test in `packages/core/tests/` if the domain port gains any domain logic, but since `update_approval` is a pure persistence operation with no domain rules, only the contract layer needs testing.

**Rationale**: Contract tests already cover `publish_document`. Adding a focused test for the "no new create during publish" invariant (verifying `ver_repo.create` is NOT called and `ver_repo.update_approval` IS called) is the minimal addition needed to satisfy Constitution Principle IV (TDD).

---

## Decision 4: Atomicity

**Decision**: No additional transaction management needed. The existing `async with get_db() as session:` context manager wraps all operations in a single transaction; `session.flush()` is used after each operation. A failure at any point rolls back all writes.

**Rationale**: The session context manager already provides atomicity (FR-004). The fix replaces one session operation (`create`) with another (`update_approval`) within the same transaction scope; the atomicity guarantee is unchanged.
