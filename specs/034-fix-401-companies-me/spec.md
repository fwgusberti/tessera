# Feature Specification: Fix 401 on Companies/Me After Login

**Feature Branch**: `034-fix-401-companies-me`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "After last fix after login i get GET http://192.168.0.8:8000/v1/companies/me 401 (Unauthorized) and cannot access tessera"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Returning User Can Access the App After Login (Priority: P1)

A user who previously logged in (and may have a stale browser session from before a recent server update) logs in with their email and password and is immediately able to use the application — they are not logged out automatically or blocked from the main interface.

**Why this priority**: This is a complete regression — the primary user journey (login → use app) is broken. Every returning user with a prior session is affected.

**Independent Test**: Log in with a known account that has an existing browser session (cookies). Verify the main dashboard loads successfully and the user is not redirected back to login.

**Acceptance Scenarios**:

1. **Given** a user has a browser session cookie from a prior visit (possibly created before the latest server update), **When** they log in with email and password, **Then** they are successfully authenticated and can navigate the app without being immediately logged out.

2. **Given** a user logs in fresh (no prior browser session), **When** they complete login, **Then** `GET /v1/companies/me` returns successfully (200 or empty list) and the company switcher loads normally.

3. **Given** a user with an incomplete stale session cookie sends a request with a valid login token, **When** the server processes the request, **Then** the valid login token takes precedence over the stale session and the user is served the correct response.

---

### User Story 2 — Company List Loads During and After Onboarding (Priority: P2)

The company list endpoint (`/companies/me`) is accessible at all points in the user lifecycle — before, during, and after onboarding — so the navigation bar can always determine what companies to show (or show none while onboarding is in progress).

**Why this priority**: The company list provider lives in the root layout and makes this call for every authenticated user on every page, including onboarding pages. A guard that blocks this endpoint mid-onboarding causes cascading failures.

**Independent Test**: Start onboarding as a new user. Verify that `GET /companies/me` returns an empty list (not an error) while onboarding is in progress, so the nav bar renders correctly.

**Acceptance Scenarios**:

1. **Given** a user has just registered and has not completed onboarding, **When** the app loads `GET /companies/me`, **Then** the endpoint returns an empty list (not a 4xx error).

2. **Given** a user has completed onboarding and has a company membership, **When** the app loads `GET /companies/me` with a valid login token, **Then** the endpoint returns the user's companies successfully.

---

### Edge Cases

- What happens if both a browser session cookie and a JWT Bearer token are present in the same request?
- What happens if the session cookie was created by an older version of the server and is missing identity fields?
- What happens if the JWT is expired but the refresh token is valid?
- How does the system behave when the company list endpoint returns an error vs. an empty list?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The authentication layer MUST accept a valid login token (JWT Bearer) even when the browser also sends a session cookie — the login token MUST take precedence if the session cookie is incomplete or missing required identity fields.
- **FR-002**: A session cookie that does not carry a complete user identity (specifically, a unique user identifier) MUST NOT be used to authenticate a request; the system MUST fall through to token-based authentication in that case.
- **FR-003**: `GET /v1/companies/me` MUST be accessible to any authenticated user regardless of their onboarding status — the endpoint MUST return an empty list for users with no company memberships, not a 4xx error.
- **FR-004**: When a request is authenticated via a valid login token but a stale/incomplete session cookie is also present, the server MUST NOT log out or invalidate the user's session.
- **FR-005**: After the fix, a user who logs in successfully MUST be able to load the main application interface without being automatically redirected back to login.
- **FR-006**: The fix MUST NOT break the onboarding guard for other endpoints — only the company list endpoint is made universally accessible to authenticated users.

### Key Entities

- **Session Cookie**: A browser-stored credential set by the server during OIDC or partial authentication flows. May be incomplete if created by an older server version.
- **JWT Bearer Token**: A cryptographically signed, short-lived credential issued by the server's email/password login endpoint. Contains the user's unique identifier, email, and role.
- **Authentication Priority**: The rule that determines which credential takes precedence when multiple are presented in the same request.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of users who successfully log in are able to load the main application interface within 5 seconds without being redirected to the login page.
- **SC-002**: Users with a stale browser session cookie (from any prior server version) can log in and use the app without clearing their browser cookies manually.
- **SC-003**: `GET /v1/companies/me` returns a 2xx response for any authenticated user (empty list for users with no memberships), and never returns 4xx due to onboarding state.
- **SC-004**: No regression in the onboarding gate — endpoints that were previously blocked pre-onboarding remain blocked (only the company list endpoint changes).

## Assumptions

- The browser session cookie from the previous server version may contain `active_company_id` but not the user's unique identifier (`sub`). This is the specific incomplete case to handle.
- Users are using email/password authentication (JWT), not OIDC/Google login.
- The company list endpoint (`GET /companies/me`) is called from the root layout and must work on all pages, including the onboarding flow.
- Fixing the authentication priority (JWT over incomplete session) is sufficient to resolve the immediate 401/logout loop — no additional state migration or database changes are needed.
- The existing refresh-token mechanism is otherwise working correctly; the problem is specifically the stale session cookie interfering with otherwise valid JWT authentication.
