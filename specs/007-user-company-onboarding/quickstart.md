# Quickstart Validation Guide: User & Company Onboarding

**Feature**: 007-user-company-onboarding | **Date**: 2026-06-15

This guide describes how to validate the onboarding feature end-to-end once implemented. Use it to confirm all user stories work correctly without running the full test suite.

---

## Prerequisites

1. Dev environment running: `make dev` (starts API + Next.js + PostgreSQL)
2. Migration applied: `make migrate`
3. At least two distinct email addresses available for testing (can be `test+1@yourmail.com` style)
4. SMTP configured in `.env` (or email logs readable in console if using `MAIL_SUPPRESS_SEND=True` dev mode)

---

## Scenario 1: New User — Create Company Path (P1 + P2 + P3 + P4)

**Goal**: Validate the happy path for a company creator.

**Steps**:
1. Register a new user at `/register` with a fresh email address.
2. After registration, confirm you are redirected to `/onboarding` (not the dashboard).
3. **Step 1 — Profile**: Enter a full name and role/title. Click Next. Confirm the progress indicator advances.
4. **Step 2 — Company**: Confirm no domain suggestions or invitations are shown (fresh email domain). Click "Create a new company." Fill in company name (required), industry (optional), team size (optional). Submit. Confirm company is created.
5. **Step 3 — Invite**: Enter two colleague email addresses (comma-separated). Click "Send Invitations." Confirm a success confirmation appears. Check email logs/inbox for invitation emails. Then click "Next."
6. **Step 4 — Complete**: Confirm completion screen shows correct full name, company name, and invitation count (2).
7. Click "Go to Dashboard." Confirm redirect to main dashboard.
8. Log out and log back in. Confirm you land on the dashboard directly — no onboarding shown.

**Validates**: FR-001 through FR-014, SC-001, SC-002, SC-005, SC-006.

---

## Scenario 2: Onboarding Resume After Interruption (Edge Case)

**Goal**: Validate interrupted sessions resume correctly.

**Steps**:
1. Register a new user and complete Step 1 (profile only). Close the browser tab.
2. Reopen the app and log in. Confirm you are returned to Step 2 (company), not Step 1.
3. Confirm Step 1 data (full name, title) is pre-populated if you navigate back.

**Validates**: FR-011, SC-003.

---

## Scenario 3: Invitation-Based Join

**Goal**: Validate joining an existing company via email invitation.

**Steps**:
1. Use the creator account from Scenario 1. The invitation emails from Step 3 should be in the test inbox.
2. Register a new account using one of the invited email addresses (`/register`).
3. After registration, confirm redirect to `/onboarding`.
4. **Step 1 — Profile**: Complete profile.
5. **Step 2 — Company**: Confirm "You've been invited to Acme Corp by [creator name]" is shown as the primary suggestion. Click "Accept Invitation."
6. Confirm you skip Step 3 (invite) entirely.
7. Confirm the completion screen shows "Welcome to Acme Corp" (joiner variant, not creator summary).
8. Confirm dashboard loads with Acme Corp as the active company context.

**Validates**: FR-001, FR-008a, FR-009 (joiner variant), FR-020.

---

## Scenario 4: Domain Matching — Auto-Join Policy

**Goal**: Validate domain matching with auto-join enabled.

**Setup**: As company admin, go to company settings and add domain `acme.com` with policy `auto_join`. Complete the verification email flow.

**Steps**:
1. Register a new user with an `@acme.com` email address.
2. Complete onboarding Profile step.
3. On the Company step, confirm Acme Corp appears as a domain suggestion with an "Auto-join" indicator.
4. Click "Join Acme Corp." Confirm immediate join (no approval required) and redirect to joiner completion screen.

**Validates**: FR-015, FR-016, FR-018.

---

## Scenario 5: Domain Matching — Request-Approval Policy + Holding Screen

**Goal**: Validate the pending approval flow.

**Setup**: As company admin, configure domain `beta.com` with policy `request_approval` (verified).

**Steps**:
1. Register a new user with `@beta.com` email. Complete profile step.
2. On Company step, confirm Beta Company appears as a domain suggestion with "Request to join" label.
3. Click "Request to join." Confirm redirect to the holding screen (no access to rest of app).
4. Confirm the company admin receives a notification email about the new join request.
5. As admin, go to join requests panel and approve the request.
6. As the requesting user, confirm the holding screen updates (or refresh shows approval).
7. Confirm onboarding completes and dashboard is accessible.

**Validates**: FR-019, FR-026, FR-027, FR-028, FR-029.

---

## Scenario 6: Domain Verification Email Flow

**Goal**: Validate domain claim verification.

**Steps**:
1. As a company admin (creator), navigate to company settings → Domain.
2. Enter domain `mycompany.com` and select policy. Click "Verify domain."
3. Confirm a verification email is sent to `verify@mycompany.com` (check logs/mailhog).
4. Click the verification link. Confirm redirect to settings with `verified=true` indicator.
5. Confirm the domain is now active (a new `@mycompany.com` registration shows the company suggestion).
6. Attempt to claim `mycompany.com` from a second company. Confirm a "Domain already claimed" error.

**Validates**: FR-022, FR-023, FR-024, FR-025.

---

## Scenario 7: New User Bypass Attempt

**Goal**: Confirm there is no bypass path around onboarding.

**Steps**:
1. Register a new user. Do not complete onboarding.
2. Directly navigate to `/documents` (or any protected page).
3. Confirm redirect back to `/onboarding` (frontend guard).
4. Attempt `GET /v1/documents` with a valid access token for the user.
5. Confirm `403 onboarding_required` response.

**Validates**: FR-001, FR-012, SC-005.

---

## Key API Endpoints to Exercise

See [contracts/onboarding-api.md](contracts/onboarding-api.md) for full request/response shapes.

| Endpoint | Scenario |
|----------|----------|
| `GET /v1/onboarding/status` | All scenarios — initial state check |
| `POST /v1/onboarding/profile` | 1, 2, 3, 4, 5 |
| `POST /v1/companies` | 1 |
| `GET /v1/companies/suggestions` | 3, 4, 5 |
| `POST /v1/companies/{id}/join` | 3, 4, 5 |
| `GET /v1/companies/{id}/join-status` | 5 |
| `DELETE /v1/companies/{id}/join-request` | 5 (cancel path) |
| `POST /v1/invitations` | 1 |
| `POST /v1/companies/{id}/domain-policies` | 6 |
| `GET /v1/domain-verify/{token}` | 6 |
| `POST /v1/onboarding/complete` | All — final step |
