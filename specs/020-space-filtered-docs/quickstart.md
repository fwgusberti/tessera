# Quickstart: Validating Space-Filtered Document Listing

## Prerequisites

- Docker Compose stack running (`make dev` or equivalent)
- At least two spaces exist in the system with documents in each
- Two test users: one with access to both spaces, one with access to only one space

## Setup

```bash
# Start the full stack
make dev

# Verify API is healthy
curl http://localhost:8000/health
```

## Scenario 1 — Auto-load on Documents page open (FR-001, SC-001)

1. Log in as a user who belongs to a group mapped in `role_permissions` for at least one space.
2. Navigate to `/documents`.
3. **Expected**: The document list loads automatically — no space selection required. Documents from all accessible spaces appear. Page loads within 3 seconds.

API validation:
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/v1/documents
# Response: { "documents": [...] }   — not empty if user has space access
```

## Scenario 2 — Space selector narrows the view (FR-004, SC-003)

1. On the Documents page, select a specific space from the space selector.
2. **Expected**: List updates to show only that space's documents.

API validation:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/v1/documents?space_id=<uuid>"
# Response: only documents belonging to that space
```

3. Clear the space selector.
4. **Expected**: List returns to the cross-space view (all accessible spaces).

## Scenario 3 — Access boundary enforcement (FR-006, SC-002)

1. Log in as a user with access to Space A but NOT Space B.
2. Navigate to `/documents`.
3. **Expected**: Only documents from Space A are shown. Documents from Space B are absent.

API validation:
```bash
curl -H "Authorization: Bearer $RESTRICTED_TOKEN" http://localhost:8000/v1/documents
# Response: documents list contains ONLY docs from accessible spaces
# Manually verify no doc with space_id = <Space B uuid> appears
```

## Scenario 4 — Admin sees everything (FR-003)

1. Log in as a user with `is_admin = True`.
2. Navigate to `/documents`.
3. **Expected**: Documents from all spaces in the system are shown.

API validation:
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/v1/documents
# Response: documents from all spaces
```

## Scenario 5 — No space access → empty state (FR-007, SC-004)

1. Log in as a user who belongs to no groups (or groups with no `role_permissions` records).
2. Navigate to `/documents`.
3. **Expected**: "No documents found across your accessible spaces" message is shown — not an error, not a blank page.

## Automated Test Suites

See `tasks.md` for the test files to run. After implementation:

```bash
# Core port tests
cd packages/core && uv run pytest tests/ -v

# API contract + integration tests
cd apps/api && uv run pytest tests/contract/test_documents.py tests/integration/ -v

# Web unit tests (when added)
cd apps/web && npm test
```

## References

- API contract: [contracts/documents-api.md](contracts/documents-api.md)
- Data model: [data-model.md](data-model.md)
- Acceptance scenarios: [spec.md](spec.md)
