# Quickstart: Frontend Login Validation

**Feature**: 005-frontend-login | **Date**: 2026-06-15

This guide documents how to validate the login feature end-to-end once implemented.

## Prerequisites

1. Backend running: `make dev-api` (or `cd apps/api && uv run uvicorn tessera_api.main:app --reload`)
2. Frontend running: `make dev-web` (or `cd apps/web && npm run dev`)
3. PostgreSQL running with migrations applied: `make db-migrate`
4. A registered user account — either registered via the API or use the seed script:
   ```bash
   curl -X POST http://localhost:8000/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"password123","display_name":"Test User"}'
   ```

## Scenario 1 — Unauthenticated redirect (US1, AC1, FR-006)

1. Open `http://localhost:3000/` in an incognito window (no stored tokens)
2. **Expected**: Browser redirects to `http://localhost:3000/login?redirect=/`
3. Submit valid credentials (`test@example.com` / `password123`)
4. **Expected**: Redirected back to `/` and the dashboard loads with data

## Scenario 2 — Invalid credentials (US1, AC2, FR-004)

1. On the login page, enter `bad@example.com` / `wrongpassword`
2. Click "Sign in"
3. **Expected**: Error message appears below the form ("Invalid credentials" or similar non-technical message)
4. Form remains on the login page with both fields still populated (email at least; password may be cleared)

## Scenario 3 — Empty field validation (US1, AC3, FR-003)

1. On the login page, leave the password field blank, enter an email
2. Click "Sign in"
3. **Expected**: Validation message appears before any network request is made (check Network tab — no POST to `/v1/auth/login`)

## Scenario 4 — Already authenticated redirect (US1, AC4, FR-007)

1. Log in successfully (follow Scenario 1)
2. Navigate directly to `http://localhost:3000/login`
3. **Expected**: Redirected to `/` without seeing the login form

## Scenario 5 — Session persistence (US2, AC1 + AC2, FR-008)

1. Log in successfully
2. Navigate to `/admin`
3. Refresh the page (`F5`)
4. **Expected**: Admin page loads; user is still authenticated (no redirect to login)

## Scenario 6 — Expired session redirect (US2, AC3, FR-009)

1. Log in, then manually clear `tessera_access_token` and `tessera_refresh_token` from `localStorage` (DevTools → Application → Local Storage)
2. Navigate to any protected page or wait for next API call
3. **Expected**: Redirect to login page with the current path preserved as `?redirect=`

## Scenario 7 — Logout (US3, AC1 + AC2, FR-010 + FR-011 + FR-012)

1. Log in successfully
2. Locate the logout button in the navigation bar (visible on all authenticated pages)
3. Click logout
4. **Expected**: Redirected to `/login`; `localStorage` is empty
5. Press the browser back button
6. **Expected**: Immediately redirected back to `/login` (no access to previous page)

## Scenario 8 — Cross-tab logout (edge case)

1. Open two tabs logged in at `http://localhost:3000/`
2. In tab 1, click logout
3. Switch to tab 2 and click any navigation link or interact with the page
4. **Expected**: Tab 2 also redirects to `/login`

## Automated Test Validation

Run the Vitest suite to verify the automated coverage:

```bash
cd apps/web
npm run test          # run all tests
npm run test -- --coverage  # check coverage report
```

Expected: All tests in `tests/login.test.tsx`, `tests/auth.test.tsx`, and `tests/auth-guard.test.tsx` pass.

## Auth Endpoints Reference

See [contracts/api-client.ts](contracts/api-client.ts) for the API call shapes.
See [data-model.md](data-model.md) for `localStorage` keys and `AuthState` types.
