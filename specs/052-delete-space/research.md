# Research: Delete Space

No `NEEDS CLARIFICATION` markers remain in the Technical Context — this document records the key technical decisions made while resolving the feature's design and the alternatives considered.

## 1. Cascading deletion given `parent_space_id ON DELETE SET NULL`

**Decision**: Resolve the full descendant subtree (target space + all descendants at any depth) via a recursive CTE, then issue a single bulk `DELETE FROM spaces WHERE id IN (...)` covering the whole subtree in one statement/transaction.

**Rationale**: `spaces.parent_space_id` is defined with `ON DELETE SET NULL` (see `db/migrations/versions/0001_initial_schema.py`), because that FK exists to support *reparenting* (a child surviving its former parent's removal would otherwise be an unexpected side effect for that operation). A naive `DELETE FROM spaces WHERE id = :id` would therefore only remove the target row and silently promote its children to root spaces — the opposite of the "delete child spaces too" requirement. Every other space-owned table (`documents`, `space_memberships`, `role_permissions`, `connectors`) already has `ON DELETE CASCADE` on its `space_id` FK, and each of those in turn cascades further (`document_versions`, `document_drafts`, `chunks` all cascade off `document_id`/`space_id` with `ON DELETE CASCADE`). So including every subtree space id in the same `DELETE` statement makes the whole removal (spaces, documents, versions, drafts, chunks, memberships, permissions, connectors) fall out of existing FK cascades automatically, in one atomic transaction, with no new migration required.

**Alternatives considered**:
- *Recursive application-level walk + per-space `DELETE`*: would work but requires N round-trips instead of one CTE + one bulk delete, and doesn't change the atomicity story — rejected as unnecessary complexity.
- *Change `parent_space_id` to `ON DELETE CASCADE`*: would make a plain single-row delete "just work," but silently changes the semantics of every other place that relies on `SET NULL` today (none currently — reparenting is the only other consumer, and it never deletes) — rejected as a broader, riskier schema change than this feature needs; the recursive CTE achieves the same outcome at the application layer without touching existing FK semantics.

## 2. Password re-verification mechanism

**Decision**: `DELETE /v1/spaces/{space_id}` accepts a JSON body `{"password": "..."}`; the router fetches the caller's `User` via the existing `SqlUserRepository.get_by_id`, and checks it with the existing `verify_password(plain, hashed)` from `tessera_api.auth.jwt_auth` — the exact same helper `/v1/auth/change-password` already uses to check `current_password`. On failure, respond `401 {"error": {"code": "invalid_credentials", ...}}`, identical shape to `change-password`'s failure response. This check runs in the router, *before* `SpaceHierarchyService.delete` is called at all — it depends only on the caller's own account, not on the target space, so it can't leak anything by running first, and it keeps `delete()` a single check-and-execute call like every other space-hierarchy service method.

**Rationale**: Reuses an already-audited, already-tested code path instead of introducing a new credential-verification mechanism. No new dependency, no new hashing scheme.

**Alternatives considered**:
- *Type-to-confirm the space name (GitHub-style)*: satisfies "confirmation" but not "authentication" as separately named in the request — rejected because it doesn't verify identity, only intent.
- *Separate short-lived "step-up" reauth token endpoint*: more reusable long-term (could serve other destructive actions later), but is speculative scope beyond what this feature needs — rejected per the project's stated preference to not build for hypothetical future requirements. `verify_password` inline is enough today.

## 3. Authorization model

**Decision**: `SpaceHierarchyService.delete(actor_id, space_id, company_id, is_company_admin=False)` requires the caller to either hold `SpaceRole.ADMIN` on the target space (via the existing `SpaceMembershipRepository.get`) or have `is_company_admin=True`, resolved by the router the same way `documents.py::delete_document` already resolves it (`CompanyMemberContext` → `is_company_admin(caller_membership)`).

**Rationale**: Matches `can_delete_document`'s existing "owner OR space admin OR company admin" precedent for the sibling delete-document feature (048); spaces have no "owner" concept, so the equivalent is "space ADMIN OR company admin." Existing space-hierarchy mutations (`rename`, `set_parent`, `create`) check *only* space ADMIN with no company-admin bypass — a narrower precedent — but deletion is significantly more destructive (an entire subtree, not one field), so extending the same bypass already trusted for document deletion is the more consistent and safer choice than introducing a third, stricter authorization rule that would make company admins unable to clean up spaces at all.

**Alternatives considered**: Space-ADMIN-only (matching `rename`/`set_parent` exactly) — rejected because it would leave company admins unable to remove a space whose admins have left the company, a real operational gap that document deletion already solved for the document case.

## 4. Audit metadata for the cascaded deletion

**Decision**: `SqlSpaceRepository.delete_subtree(space_id)` returns `(deleted_space_count, deleted_document_count)`, computed via one `COUNT(*)` over the resolved subtree ids *before* the delete executes (documents) and `len(subtree_ids)` (spaces, including the target). The router writes one `space_deleted` audit record with both counts in `metadata`, after the counts are known but as part of the same request/transaction as the delete.

**Rationale**: `audit_records.entity_id` has no FK constraint (verified in `apps/api/tessera_api/adapters/models/audit_record.py`), so the audit entry naturally survives the space's removal — no special handling needed. Counting before deleting (rather than trying to count "what was deleted" after the fact) is the only order that works once the rows are gone.

**Alternatives considered**: One audit record per deleted document/space (mirroring `document_deleted`'s one-record-per-document granularity) — rejected as needless volume for a single cascaded operation the user triggered once; a single summary record with counts satisfies FR-012 without flooding the audit log.

## 5. Frontend: sending a body on `DELETE`

**Decision**: Extend `apps/web/lib/api.ts`'s `api.delete<T>(path, body?)` to accept an optional JSON body, passed through to `fetch` like `post`/`patch` already do.

**Rationale**: `fetch` and FastAPI both support a body on `DELETE` requests; this is the smallest change that lets `DeleteSpaceModal` submit the password field to the existing REST-ful `DELETE /v1/spaces/{space_id}` route, avoiding a parallel `POST /v1/spaces/{space_id}/delete` action-endpoint that would break the resource-oriented pattern every other space route already follows (`PATCH .../name`, `PATCH .../parent`, `DELETE .../parent`).

**Alternatives considered**: `POST /v1/spaces/{space_id}/delete` action endpoint — rejected as inconsistent with the existing route naming in `spaces.py`, where the HTTP verb alone (not a `/delete` suffix) already expresses the action for the sibling `remove_space_parent` route (`DELETE /v1/spaces/{space_id}/parent`).
