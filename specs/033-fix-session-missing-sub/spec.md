# Feature Specification: Fix Missing User Identity in Session After Company Activation

**Feature Branch**: `033-fix-session-missing-sub`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "KeyError: 'sub' in require_onboarding_complete — session user dict is incomplete after company activation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Activate Company Without Crashing (Priority: P1)

A user who has just authenticated via JWT (no session cookie yet) calls the activate-company endpoint to select their active company. On the next request (any protected route), the system correctly identifies who they are without throwing a server error.

**Why this priority**: This is a crash-level regression affecting all users who activate a company from a JWT-authenticated context. Every subsequent request fails with a 500 until the session is cleared.

**Independent Test**: Can be fully tested by: (1) authenticate via JWT, (2) call activate-company, (3) make any request to a protected route that goes through the onboarding guard — the request must succeed with the correct user identity, not crash.

**Acceptance Scenarios**:

1. **Given** a user authenticated only via JWT (no session cookie), **When** they activate a company, **Then** the session stores a complete user identity record including their unique identifier, and subsequent session-based requests succeed.
2. **Given** a user who already has a session cookie with a valid user identity, **When** they activate a company, **Then** the existing identity fields are preserved and only the active company is updated.
3. **Given** a user with a session that has a complete user identity, **When** a protected route calls the onboarding guard, **Then** the guard resolves the user identity without error and enforces onboarding status correctly.

---

### User Story 2 - Onboarding Guard Handles Incomplete Sessions Gracefully (Priority: P2)

Even if a session somehow ends up with an incomplete user record (missing identity fields), the onboarding guard should not crash with an unhandled exception — it should either fall through to the next authentication method or return a clear, actionable error.

**Why this priority**: Defense-in-depth: the root cause fix (Story 1) is primary, but the guard itself should be resilient to unexpected session state rather than exposing an unhandled 500.

**Independent Test**: Can be tested by manually injecting a session with a user dict that lacks the identity field and hitting a route protected by the onboarding guard — the response must be 401 or 403, never a 500.

**Acceptance Scenarios**:

1. **Given** a session with a user dict that is missing the identity field, **When** a request hits a route guarded by the onboarding check, **Then** the system returns a 401 or 403 with a structured error — not a 500.
2. **Given** no session at all, **When** a request hits the onboarding guard, **Then** the guard returns early without crashing (existing behavior preserved).

---

### Edge Cases

- What happens when the JWT Bearer token and session cookie are both present? The session takes priority today; the fix must not change that ordering.
- What happens if a user activates a company from a browser that already has a session from a different auth path? The existing session user fields must not be overwritten.
- What if `user_info["sub"]` is present in the JWT claims but is not a valid UUID? The system should return 422 or 400, not crash.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When the activate-company endpoint creates a new session user record, it MUST include the user's unique identity field (currently `sub`) in addition to the active company identifier.
- **FR-002**: When a session user record already exists, activate-company MUST preserve all existing fields and only update the active company field.
- **FR-003**: The onboarding guard MUST NOT raise an unhandled exception when the session user record is missing the identity field; it MUST treat the session as unauthenticated and fall through to subsequent auth methods.
- **FR-004**: The onboarding guard MUST continue to allow requests from unauthenticated users to pass through (existing behavior: the JWT/OIDC guard handles 401 separately).
- **FR-005**: All existing exempt routes (company suggestions, create company, join company, join-status, cancel join-request) MUST remain accessible without any authentication check.

### Key Entities

- **Session User Record**: The user identity object stored under the `"user"` key in the encrypted session cookie. Must contain at minimum: a unique user identifier (`sub`) and an optional active company identifier. Other fields (email, admin flag) may be present.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero unhandled 500 errors attributable to a missing `sub` field in the session user record after activating a company.
- **SC-002**: The activate-company flow completes successfully for 100% of users authenticating via JWT with no prior session, with all subsequent protected routes accessible.
- **SC-003**: Existing session-based (OIDC) users are unaffected — their session contents are not altered by the fix.
- **SC-004**: The onboarding guard returns a structured 401 or 403 (never a 500) when given any malformed session state.

## Assumptions

- The `sub` value available in the JWT claims at activate-company time is the canonical user identifier and is safe to store in the session.
- Session-based (OIDC) users already have a complete user record in their session (including `sub`) written at login time; the bug only affects users who arrive via JWT with no prior session.
- The frontend uses the JWT returned by activate-company for subsequent API calls; however, the session must also be kept consistent for any session-based code paths.
- No schema migration is required — this is a logic-only fix in the activate-company endpoint and the onboarding guard.
