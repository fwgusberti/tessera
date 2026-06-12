# Quickstart: UI Compliance Validation

**Feature**: 003-fix-ui-compliance
**Date**: 2026-06-12

This guide provides end-to-end validation scenarios to confirm the UI changes work correctly.
It assumes the backend API and workers are already running (see `specs/002-ollama-embeddings/quickstart.md`
for infra startup).

---

## Prerequisites

1. All services running (API on `http://localhost:8000`, web on `http://localhost:3000`):
   ```bash
   docker compose up -d
   cd apps/web && npm run dev
   ```
2. A valid session cookie (log in via the OIDC provider, or use a dev bypass if configured).
3. At least one admin account available for admin-only scenarios.

---

## Scenario 1: Home Page Dashboard

**Goal**: Confirm the home page shows Tessera content, not the Next.js boilerplate.

**Steps**:
1. Open `http://localhost:3000/`
2. Verify: no Next.js logo, no "Deploy now" button, no "Get started by editing" text.
3. Verify: page title "Tessera" visible.
4. Verify: at least three stat cards are rendered (even if showing "–" when no data).
5. Verify: navigation links Search, Proposals, Metrics, Admin are all present.

**Expected**: Dashboard renders without errors; stats show numeric values or graceful "–".

---

## Scenario 2: Metrics Accessible via Navigation

**Goal**: Confirm the Metrics link is in the nav and works.

**Steps**:
1. From any page, look at the navigation bar.
2. Click "Metrics".
3. Verify: URL becomes `/metrics`.
4. Verify: metric cards load (same as before, now just reachable from nav).

**Expected**: Navigation to `/metrics` via the nav link succeeds.

---

## Scenario 3: Document Browsing

**Goal**: Browse documents in a space.

**Steps**:
1. Navigate to `http://localhost:3000/documents`.
2. Verify: space selector dropdown appears, populated with available spaces.
3. Select a space.
4. Verify: list of documents appears with title, state, and confidentiality.
5. Click a document row.
6. Verify: URL changes to `/documents/{id}`.
7. Verify: document title, state badge, and current version content are displayed.
8. Verify: version history table is displayed with at least one row.

**Expected**: Full browse → detail flow works without errors.

---

## Scenario 4: Document Publishing

**Goal**: Publish an ingested document via the UI.

**Precondition**: A document in `ingested` state with `owner_user_id` assigned exists.

**Steps**:
1. Navigate to `/documents`, select the owning space.
2. Open the ingested document.
3. Verify: "Publish" button is visible.
4. Click "Publish".
5. Verify: button is disabled while request is in flight.
6. Verify: after success, state badge changes to "published" and the "Publish" button disappears.

**Expected**: State transition reflected in UI without page reload.

---

## Scenario 5: Create a Space (Admin)

**Goal**: Create a new space via the Admin page form.

**Precondition**: Logged in as admin.

**Steps**:
1. Navigate to `/admin`.
2. Scroll to "Create Space" form.
3. Leave slug empty and click Submit.
4. Verify: inline validation error appears; no API call made.
5. Fill in: slug="qa-validation", name="QA Validation Space", sector="Engineering".
6. Click Submit.
7. Verify: new space appears immediately in the spaces table.
8. Verify: form fields are reset to empty.

**Expected**: Space created and listed; form validates and resets correctly.

---

## Scenario 6: Create a Connector and Trigger Sync (Admin)

**Goal**: Create a connector and trigger a manual sync.

**Precondition**: At least one space exists.

**Steps**:
1. Navigate to `/admin`, scroll to "Connectors" section.
2. Select a space from the connector space dropdown.
3. Fill in type="confluence", config=`{"base_url": "http://example.com", "token": "test"}`, leave schedule blank.
4. Click "Create Connector".
5. Verify: connector appears in the list.
6. Click "Sync Now" next to the connector.
7. Verify: a job ID or success message appears.

**Expected**: Connector created and sync triggered; job ID displayed.

---

## Scenario 7: Create Agent Credential (Admin)

**Goal**: Issue an agent credential via the Admin page.

**Precondition**: Logged in as admin. At least one space exists.

**Steps**:
1. Navigate to `/admin`, scroll to "Agent Credentials" section.
2. Fill in name="Test Agent", select one or more spaces, set max_confidentiality="internal".
3. Click "Create Credential".
4. Verify: the raw token is displayed in a highlighted box with a copy button.
5. Verify: a warning message "This token will not be shown again" is visible.
6. Verify: the credential appears in the credentials list.
7. Click "Revoke" on the credential.
8. Verify: the credential is marked as revoked in the list.

**Expected**: Token shown once on creation; credential revocable.

---

## Scenario 8: Error Resilience

**Goal**: Confirm graceful degradation when the API is unavailable.

**Steps**:
1. Stop the API server.
2. Open `http://localhost:3000/`.
3. Verify: dashboard renders; stat cards show "–" or a degraded-state message, not an unhandled error.
4. Navigate to `/documents`.
5. Verify: an inline error message appears (e.g., "Failed to load spaces"); page does not crash.

**Expected**: All pages gracefully handle API unavailability.

---

## Automated Tests (Vitest)

Run the web test suite to verify component-level behavior:

```bash
cd apps/web && npx vitest run
```

New test files to create during implementation (see `tasks.md`):

- `tests/home.test.tsx` — dashboard renders stats, handles API errors
- `tests/documents.test.tsx` — list filters by space, detail shows version history
- `tests/admin.test.tsx` — create-space form validates required fields

Coverage target: ≥85% statement coverage for all new files in `app/` and `components/`.
