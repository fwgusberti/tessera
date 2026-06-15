# Quickstart Validation Guide: New User Registration

**Feature**: 006-user-registration | **Date**: 2026-06-15

## Prerequisites

- Docker Compose stack running (API + database): `make dev` or `docker compose up -d`
- Frontend dev server running: `cd apps/web && npm run dev`
- A clean database or a test email address not yet registered

## Scenario 1 — Happy Path: New User Registers and Is Auto-logged In

1. Open `http://localhost:3000/register` in a browser.
2. Fill in **Display Name**: `Test User`, **Email**: `test@example.com`, **Password**: `password123`.
3. Observe the password strength indicator (should show "Medium" or "Strong").
4. Click **Create account**.

**Expected outcome**:
- Browser redirects to `http://localhost:3000/` (home page).
- The navigation bar shows the authenticated user (no "Sign in" link).
- No second login step is required.

---

## Scenario 2 — Redirect Parameter Respected

1. Navigate to a protected route directly, e.g., `http://localhost:3000/documents`.
2. Auth guard redirects to `http://localhost:3000/login?redirect=%2Fdocuments`.
3. Click the "Create account" link on the login page.
4. Browser navigates to `http://localhost:3000/register?redirect=%2Fdocuments`.
5. Register with a new email.

**Expected outcome**:
- After auto-login, browser redirects to `http://localhost:3000/documents` (not `/`).

---

## Scenario 3 — Duplicate Email

1. Attempt to register with an email address that is already registered.
2. Click **Create account**.

**Expected outcome**:
- Page stays on `/register`.
- Error message: "This email is already registered."
- A "Sign in" link (pointing to `/login`) is visible in or near the error message.

---

## Scenario 4 — Client-side Validation

1. Submit the form with all fields empty.

**Expected outcome**: Inline errors on all three fields; no network request fired.

2. Enter a password of 7 characters and submit.

**Expected outcome**: Password field error "Password must be at least 8 characters"; no request fired.

3. Enter a display name longer than 100 characters and submit.

**Expected outcome**: Display name field error "Display name must be 100 characters or fewer"; no request fired.

---

## Scenario 5 — Authenticated User Redirect

1. Log in normally.
2. Navigate manually to `http://localhost:3000/register`.

**Expected outcome**: Immediately redirected to `http://localhost:3000/` without seeing the registration form.

---

## Scenario 6 — Login Page Link

1. Navigate to `http://localhost:3000/login`.

**Expected outcome**: A "Create account" (or equivalent) link is visible and navigates to `/register`.

---

## Running Unit Tests

```bash
cd apps/web
npm test -- register
```

All tests in `apps/web/tests/register.test.tsx` should pass.

To run the full test suite:

```bash
npm test
```

---

## Contract Reference

See [`contracts/register-api.md`](./contracts/register-api.md) for the full `POST /v1/auth/register` request/response specification.

## Data Model Reference

See [`data-model.md`](./data-model.md) for types, validation rules, and form state transitions.
