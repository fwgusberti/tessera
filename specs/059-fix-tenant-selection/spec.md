# Feature Specification: Company Selection at Sign-In

**Feature Branch**: `059-fix-tenant-selection`

**Created**: 2026-07-10

**Status**: Draft

**Input**: User description: "I get Credential is not scoped to a tenant; call /auth/select-tenant first when logged with a no admin user"

## Problem Statement

When a person belongs to more than one company, signing in grants them a
credential that is not yet tied to any specific company — the system expects
them to choose a company before working with data. The web application never
offers that choice: it treats the sign-in as complete, drops the user into the
app, and every screen then fails with the raw technical error *"Credential is
not scoped to a tenant; call /auth/select-tenant first"*. The user is
effectively locked out even though their credentials are valid.

This affects any user with two or more company memberships — commonly regular
(non-admin) members who were invited to or joined additional companies — and
there is no way to recover other than contacting support.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-company user completes sign-in by choosing a company (Priority: P1)

A person who belongs to two or more companies signs in with a valid email and
password. Instead of landing on a broken screen, they are shown a list of
their companies (with their role in each) and asked to pick the one they want
to work in. After picking, they land in the application with full access to
that company's workspace.

**Why this priority**: This is the reported defect — multi-company users are
completely locked out of the product today. Nothing else in this feature
matters until this works.

**Independent Test**: Create a user with memberships in two companies, sign
in through the web application, choose one company, and verify the main
screens (spaces, documents, users) load with that company's data.

**Acceptance Scenarios**:

1. **Given** a user who is a member of two companies, **When** they sign in
   with valid credentials, **Then** they are presented with a company
   selection step listing both companies by name and role.
2. **Given** the company selection step is displayed, **When** the user picks
   a company, **Then** they are taken into the application and all pages load
   that company's data without any credential-scope errors.
3. **Given** a user who is a member of exactly one company, **When** they
   sign in, **Then** they go straight into the application with no selection
   step (existing behavior unchanged).
4. **Given** a user with no company memberships, **When** they sign in,
   **Then** they are taken to onboarding as today (existing behavior
   unchanged).

---

### User Story 2 - Unscoped session is redirected to selection instead of erroring (Priority: P2)

A user whose current session is authenticated but not yet tied to a company
(for example, they signed in earlier and their unscoped session was restored,
or they opened a bookmarked page directly) is automatically routed to the
company selection step rather than being shown failing pages or raw error
messages.

**Why this priority**: Sessions are restored across visits, so users can end
up inside the app with an unscoped credential without passing through the
sign-in form. Without this, the P1 fix only covers the happy path.

**Independent Test**: With an unscoped authenticated session already stored,
navigate directly to a protected page and verify the user is redirected to
company selection, completes it, and returns to a working application.

**Acceptance Scenarios**:

1. **Given** a stored authenticated session that is not tied to a company,
   **When** the user opens any protected page, **Then** they are redirected
   to the company selection step instead of seeing errors.
2. **Given** any screen in the application receives a "credential not scoped"
   response from the backend, **When** this happens, **Then** the user is
   sent to the company selection step and never shown the raw technical
   error text.

---

### User Story 3 - Selection failures are handled gracefully (Priority: P3)

While on the company selection step, things can go wrong: the chosen company
may have been suspended, the user's membership may have been revoked moments
earlier, or the session may have expired. The user always gets a clear,
human-readable explanation and a way forward (pick another company or sign
out) — never a dead end.

**Why this priority**: These are rarer race conditions, but without handling
them the selection step itself can become a new dead end, recreating the
original problem one screen later.

**Independent Test**: Suspend one of the user's two companies, sign in,
attempt to select the suspended company, and verify a clear message appears
and the other company can still be selected.

**Acceptance Scenarios**:

1. **Given** the selection step is shown, **When** the user picks a company
   that has been suspended, **Then** a clear message explains the company is
   unavailable and the user can pick another company or sign out.
2. **Given** the selection step is shown, **When** the user picks a company
   where their membership was revoked after sign-in, **Then** a clear message
   is shown and the remaining companies stay selectable.
3. **Given** the selection step is shown, **When** the user chooses to sign
   out instead of selecting, **Then** they are returned to the sign-in page
   with the session fully cleared.

---

### Edge Cases

- User's memberships change between sign-in and selection (e.g., reduced to
  one or zero companies): selecting a no-longer-valid company shows a clear
  error; the list can be refreshed or the user can sign out and back in.
- The unscoped session expires while the user sits on the selection screen:
  the user is returned to sign-in with a session-expired message, not a
  frozen screen.
- A company is renamed between listing and selection: selection still works
  (companies are identified by identity, not name).
- User opens the selection page while already scoped to a company: they are
  taken into the application, not shown the picker again.
- The chosen company must survive page reloads and background credential
  renewal for the lifetime of the session — the user must not be asked to
  pick again mid-session.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: After a successful sign-in that requires company selection, the
  system MUST present the user with a list of all companies they belong to,
  showing at least each company's name and the user's role in it.
- **FR-002**: The user MUST be able to complete sign-in by selecting one
  company, after which they have full, company-scoped access and are taken to
  their intended destination in the application.
- **FR-003**: Users belonging to exactly one company MUST continue to sign in
  directly with no selection step; users with no memberships MUST continue to
  be routed to onboarding. Existing single-company and onboarding flows are
  unchanged.
- **FR-004**: Whenever an authenticated but company-unscoped session attempts
  to reach any protected area of the application — via navigation, page
  refresh, bookmark, or a backend "credential not scoped" response — the
  system MUST route the user to the company selection step instead of
  displaying an error.
- **FR-005**: The raw technical message "Credential is not scoped to a
  tenant; call /auth/select-tenant first" MUST never be displayed to end
  users.
- **FR-006**: If a selection attempt fails because the company is suspended
  or the user's membership no longer exists, the system MUST show a clear,
  human-readable explanation and keep the remaining companies selectable.
- **FR-007**: The selected company MUST persist for the remainder of the
  session, surviving page reloads and background credential renewal, without
  prompting the user to select again.
- **FR-008**: The user MUST be able to sign out from the company selection
  step, fully clearing the session.

### Key Entities

- **Company membership**: The association between a user and a company,
  including the user's role; the selection list is derived from the user's
  active memberships.
- **Session credential scope**: Whether the user's current session is tied to
  a specific company (scoped), awaiting a choice (unscoped), or in onboarding;
  determines which areas of the application are reachable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users belonging to two or more companies can sign in and reach
  a working workspace 100% of the time (today this is 0% — they are locked
  out).
- **SC-002**: The raw credential-scope error message appears to end users 0
  times across all supported flows (sign-in, session restore, bookmark,
  in-app navigation).
- **SC-003**: Company selection adds at most one extra step to sign-in and
  can be completed in under 30 seconds by a first-time user.
- **SC-004**: Sign-in behavior for single-company users and users with no
  companies is unchanged (no new steps, no regressions in existing sign-in
  and onboarding tests).

## Assumptions

- The backend already provides everything needed: sign-in responses indicate
  when selection is required, the user's companies can be listed with an
  unscoped credential, and an exchange endpoint issues company-scoped
  credentials. This feature is a web-application fix; no backend behavior
  changes are expected.
- The report mentions a non-admin user, but the trigger is belonging to
  multiple companies, not the role; admins with multiple memberships are
  equally affected and equally fixed.
- Switching to a different company *after* a successful selection (an in-app
  company switcher) is out of scope; the user can sign out and back in to
  change companies.
- Remembering the last-used company across separate sign-ins (pre-selecting
  or skipping the picker on subsequent logins) is out of scope for this fix.
