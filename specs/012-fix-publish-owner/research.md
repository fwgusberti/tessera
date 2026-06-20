# Research: Fix Document Publish — Auto-Assign Owner

## Decision 1: Where to assign the owner

**Decision**: Assign `owner_user_id` at document creation time (router layer), using the authenticated user's ID from the JWT/session token.

**Rationale**: The `Document` entity already has `owner_user_id: UUID | None`. The `create_document` router already calls `require_user(request)` and has the user identity available. Setting the owner at creation is the correct lifecycle moment — the creator is the de-facto owner until explicitly changed. The existing `assign_owner` lifecycle function in `tessera_core.services.lifecycle` is the correct domain operation and will be used by the publish fallback path.

**Alternatives considered**:
- Require the caller to pass `owner_user_id` in the request body — rejected: forces every client to pass redundant data; the creator is the obvious default.
- Add a separate "assign owner" step before publish — rejected: adds friction, breaks the zero-extra-steps success criterion (SC-004).

---

## Decision 2: Fallback for legacy documents (no owner at publish time)

**Decision**: At publish time, if `doc.owner_user_id is None`, call `assign_owner(doc, publisher_id)` (domain function) and persist via `doc_repo.set_owner(document_id, publisher_id)` before calling `lifecycle_publish`. Remove the explicit 400 rejection.

**Rationale**: This is FR-002. The `DocumentRepository.set_owner` method already exists in both the port (`tessera_core.ports.repositories`) and the SQL adapter (`SqlDocumentRepository.set_owner`). No new persistence method is needed. Calling the domain function first ensures the in-memory `doc` object passed to `lifecycle_publish` has `owner_user_id` set (since `lifecycle_publish` also checks `owner_user_id is None` and raises `LifecycleError`).

**Alternatives considered**:
- Data migration to backfill `owner_user_id` for all existing documents — rejected: adds operational complexity; lazy assignment at publish time is simpler and safe.
- Allow `lifecycle_publish` to accept `owner_id` and set it internally — rejected: changes domain service signature unnecessarily; separation of concerns.

---

## Decision 3: User ID extraction from `user_info`

**Decision**: Fix `require_user` (JWT path) to include `"id": claims["sub"]` in the returned dict. The `sub` claim is already set to `str(user.id)` (a UUID) in `create_access_token`. This makes `user_info.get("id")` reliable for both session and JWT auth paths.

**Rationale**: Currently the JWT path returns `{"sub": ..., "email": ..., "is_admin": ...}` without `"id"`. The session path returns a dict with `"id"`. All router code that uses `user_info.get("id")` (both the publish and create endpoints) silently gets `None` for JWT users. Adding `"id": claims["sub"]` to the JWT path is backward-compatible and fixes a latent bug across all endpoints.

**Alternatives considered**:
- Change all callers to use `user_info.get("id") or user_info.get("sub")` — rejected: scatters the fix; better to fix at the source.
- Add a `user_id` property to a typed wrapper — rejected: over-engineering for what is a one-line fix.

---

## Decision 4: Test strategy

**Decision**: Add contract tests in `apps/api/tests/contract/test_documents.py` for both the new `create_document` owner-setting behavior and the `publish_document` auto-assignment fallback. Use the existing mock pattern (AsyncMock + patch) established in that file.

**Rationale**: The existing test file already has the infrastructure. Constitution Principle IV requires TDD: write failing tests first, confirm they fail, then implement. Lifecycle unit tests in `packages/core/tests/test_lifecycle.py` already cover the domain layer; no new domain tests needed.
