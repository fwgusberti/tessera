# Quickstart Validation Guide: Delete Document

## Prerequisites

- Stack running locally (`make dev`), including the API and web app.
- Two registered users in the same company: `OWNER` (owns a document) and
  `OTHER_EDITOR` (an editor in the same space, but not the owner and not a
  space admin).
- A third user, `ADMIN`, who is either a space admin of the document's space
  or a platform admin.
- A document `DOC_ID` owned by `OWNER`, in space `SPACE_ID`, with at least
  one version.

## Scenario 1: Owner deletes their own document (US1)

Frontend: sign in as `OWNER`, open `/documents/DOC_ID`, click **Delete**,
confirm the browser prompt. Expect: redirected to `/spaces/SPACE_ID`, and
the document no longer appears in that space's listing.

API equivalent:
```bash
TOKEN="<OWNER access token>"
curl -s -X DELETE http://localhost:8000/v1/documents/$DOC_ID \
  -H "Authorization: Bearer $TOKEN" | jq
# Expected: {"deleted": true, "document_id": "<DOC_ID>"}

curl -s http://localhost:8000/v1/documents/$DOC_ID \
  -H "Authorization: Bearer $TOKEN" -o /dev/null -w "%{http_code}\n"
# Expected: 404
```

## Scenario 2: Admin deletes a document they don't own (US2)

Repeat with a fresh document owned by `OWNER`, but issue the `DELETE` call
as `ADMIN` instead. Expected: same `{"deleted": true, ...}` response, even
though `ADMIN` is not `owner_user_id`.

## Scenario 3: Cancel leaves the document untouched (US3)

Frontend only: sign in as `OWNER`, open the document, click **Delete**,
dismiss the browser confirm prompt. Expect: no network request is sent, the
page is unchanged, and the document is still reachable afterward.

## Scenario 4: Unauthorized user cannot delete (Edge Case, FR-002/FR-007)

```bash
TOKEN="<OTHER_EDITOR access token>"
curl -s -X DELETE http://localhost:8000/v1/documents/$DOC_ID \
  -H "Authorization: Bearer $TOKEN" -o /dev/null -w "%{http_code}\n"
# Expected: 403
```
Also verify in the frontend that `OTHER_EDITOR` does not see a Delete button
on the document page at all.

## Scenario 5: Deletion removes the document from search (FR-005, SC-003)

Only meaningful for a **published** document that has already been indexed.

```bash
# Before deleting, confirm it's findable (adjust query to match doc content)
curl -s -X POST http://localhost:8000/v1/search \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query": "<distinctive phrase from the document>"}' | jq '.results[].document_id'
# Expected: DOC_ID present

curl -s -X DELETE http://localhost:8000/v1/documents/$DOC_ID -H "Authorization: Bearer $TOKEN"

curl -s -X POST http://localhost:8000/v1/search \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query": "<same distinctive phrase>"}' | jq '.results[].document_id'
# Expected: DOC_ID absent immediately (no wait needed — cascade delete is
# synchronous, unlike indexing which is async)
```

## Scenario 6: Double-delete is handled gracefully (Edge Case)

```bash
curl -s -X DELETE http://localhost:8000/v1/documents/$DOC_ID -H "Authorization: Bearer $TOKEN" | jq
# First call: {"deleted": true, ...}
curl -s -X DELETE http://localhost:8000/v1/documents/$DOC_ID -H "Authorization: Bearer $TOKEN" -o /dev/null -w "%{http_code}\n"
# Second call: 404 (not a 500/crash)
```

## Running Unit Tests

```bash
cd apps/api
.venv/bin/python -m pytest tests/unit/test_documents_router.py -v --no-cov

cd ../../packages/core
.venv/bin/python -m pytest tests/test_membership.py -v --no-cov
```

All tests must pass, including new cases for: owner can delete, space admin
can delete, platform admin can delete, editor cannot delete, viewer cannot
delete, cross-tenant delete returns 404 + audit, delete of an
already-deleted document returns 404, and the audit record is written with
`action="document_deleted"`.

```bash
cd apps/web && npx vitest run tests/document-delete.test.tsx
```
Must include: Delete button visible for owner/admin, hidden for
non-owner/non-admin, confirm-cancel leaves state untouched, confirm-accept
calls the delete endpoint and redirects to the space page.
