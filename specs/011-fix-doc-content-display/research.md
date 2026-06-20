# Research: Fix Document Content Display

**Date**: 2026-06-19

## No open unknowns

All decisions are already resolved from direct code inspection. No external research was required.

---

## Decision 1: Fix location

**Decision**: `apps/api/tessera_api/routers/documents.py` — `create_document` endpoint, inside the existing `async with get_db() as session:` block.

**Rationale**: The bug is a missing `set_current_version` call after the `DocumentVersion` is persisted. Adding it inside the same session block ensures atomicity: either the document, version, and pointer are all committed or all rolled back on error.

**Alternatives considered**:
- Modify `SqlDocumentRepository.create()` to accept an optional `version_id` and set `current_version_id` at insert time — rejected because it would leak cross-aggregate responsibility into a single-entity method and require a pre-existing version ID before the version is created.
- Add a `current_version_id` field to the `CreateDocumentRequest` body — rejected because the version is always created by the API, not supplied by the caller.

---

## Decision 2: Which repository method to call

**Decision**: Reuse the existing `doc_repo.set_current_version(created_doc.id, created_version.id)` method already present in `SqlDocumentRepository` (used identically by `publish_document`).

**Rationale**: The method already exists, is tested by the publish flow, and is idiomatic within this codebase. No new code is needed in the repository layer.

**Alternatives considered**:
- Create a dedicated `link_initial_version` method — rejected as unnecessary indirection for the same SQL `UPDATE`.

---

## Decision 3: Return value

**Decision**: Use the `Document` returned by `set_current_version` (which re-fetches the updated row) as the `created_doc` in the response body.

**Rationale**: The current response returns `created_doc.model_dump()` whose `current_version_id` is `None`. After the fix, the returned document should reflect the newly set pointer so that callers (including the frontend modal) receive accurate state.

**Alternatives considered**:
- Keep returning the original `created_doc` and just not use the return value of `set_current_version` — rejected because it would return stale data with `current_version_id: null` to callers.

---

## Decision 4: Test placement

**Decision**: Add a new contract test file `apps/api/tests/contract/test_documents.py` using `pytest` and `unittest.mock`.

**Rationale**: Existing contract tests (e.g., `test_search.py`) use mocks to verify behaviour contracts without a running database. The same pattern applies here: mock the repository layer and assert that `set_current_version` is called with the correct IDs after version creation.

**Alternatives considered**:
- Integration test with a real database — valid long-term but out of scope for this fix; the contract test provides immediate coverage of the missing call.
