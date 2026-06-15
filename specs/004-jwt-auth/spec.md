# Feature Specification: JWT Authentication

**Feature Branch**: `004-jwt-auth`

**Created**: 2026-06-15

**Status**: Draft

**Input**: User description: "adicionar autenticação com JWT"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Authenticate and Receive Token (Priority: P1)

A registered user submits their credentials and receives a JWT access token that grants access to protected resources.

**Why this priority**: Without token issuance there is no authentication. All other stories depend on this one. Delivers immediate value by securing previously open endpoints.

**Independent Test**: Can be fully tested by submitting valid credentials to the login endpoint and verifying a JWT token is returned. Delivers "system is now authenticated" as standalone value.

**Acceptance Scenarios**:

1. **Given** a registered user with valid credentials, **When** they submit their username and password, **Then** the system returns a signed JWT access token and a refresh token
2. **Given** a user submitting invalid credentials, **When** they attempt to authenticate, **Then** the system returns an appropriate error without disclosing which field is wrong
3. **Given** a user account that is inactive or suspended, **When** they attempt to authenticate, **Then** the system denies access and returns a clear, non-exposing error

---

### User Story 2 - Access Protected Resources with Token (Priority: P1)

An authenticated user includes their JWT token in requests and accesses protected API endpoints without re-authenticating.

**Why this priority**: Core purpose of authentication. Users must be able to use the system after authenticating.

**Independent Test**: Can be tested by presenting a valid token to a protected endpoint and confirming the response is granted, and then presenting an invalid or absent token and confirming rejection.

**Acceptance Scenarios**:

1. **Given** a user holding a valid, non-expired JWT token, **When** they make a request to a protected endpoint, **Then** the system grants access and processes the request normally
2. **Given** a user presenting an expired JWT token, **When** they request a protected resource, **Then** the system rejects the request with a clear "token expired" indication
3. **Given** a request with no token or a malformed token, **When** it arrives at a protected endpoint, **Then** the system rejects it with an authentication error

---

### User Story 3 - Refresh Expired Access Token (Priority: P2)

An authenticated user whose access token has expired uses their refresh token to obtain a new access token without re-entering credentials.

**Why this priority**: Improves usability by avoiding repeated logins during active sessions, while keeping short-lived access tokens for security.

**Independent Test**: Can be tested by waiting for (or simulating) access token expiry, submitting the refresh token, and verifying a new valid access token is issued.

**Acceptance Scenarios**:

1. **Given** a user with an expired access token and a valid refresh token, **When** they request a token refresh, **Then** the system issues a new access token
2. **Given** a user attempting to reuse an already-used refresh token, **When** they request a refresh, **Then** the system rejects it
3. **Given** a user whose refresh token has also expired, **When** they attempt to refresh, **Then** the system requires full re-authentication

---

### User Story 4 - Log Out and Invalidate Tokens (Priority: P2)

An authenticated user explicitly logs out, rendering their tokens invalid so they cannot be reused.

**Why this priority**: Required for security hygiene. Users must be able to end their sessions definitively, especially on shared devices.

**Independent Test**: Can be tested by logging out and then attempting to use the previously valid token, confirming it is rejected.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they log out, **Then** the system invalidates both the access and refresh tokens
2. **Given** a token that was invalidated via logout, **When** it is presented to any protected endpoint, **Then** the system rejects it even if it has not yet expired by time

---

### Edge Cases

- What happens when a token is valid but was issued before a mandatory password change?
- How does the system handle concurrent refresh attempts with the same refresh token?
- What happens if the token signing key is rotated — are existing sessions automatically invalidated?
- How does the system behave under a burst of authentication requests from the same IP?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow registered users to authenticate using their credentials and receive a signed JWT access token and a refresh token upon success
- **FR-002**: The system MUST reject authentication attempts with invalid, incorrect, or missing credentials without revealing which field is wrong
- **FR-003**: Protected API endpoints MUST require a valid, non-expired JWT token; requests without one MUST be refused
- **FR-004**: The system MUST validate JWT token signature and expiry on every protected request
- **FR-005**: The system MUST provide a mechanism to obtain a new access token using a valid refresh token
- **FR-006**: The system MUST invalidate both access and refresh tokens upon explicit logout
- **FR-007**: Refresh tokens MUST be single-use; a token MUST be invalidated immediately after it is used
- **FR-008**: The system MUST emit a structured audit log entry for every authentication event (login, logout, token refresh, failed attempts)
- **FR-009**: Token configuration (expiry durations, signing algorithm) MUST be externally configurable without code changes

### Key Entities

- **User**: The actor being authenticated; has credentials (email/password) and a status (active/inactive)
- **Access Token**: Short-lived credential proving identity; carries user identity claims; used on every protected request
- **Refresh Token**: Long-lived credential used solely to obtain new access tokens; stored server-side for revocation
- **Audit Log Entry**: Record of an authentication event; captures actor identity, event type, timestamp, and outcome

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can authenticate (from credential submission to token in hand) in under 2 seconds under normal load
- **SC-002**: Protected endpoints reject 100% of requests bearing invalid, expired, or revoked tokens
- **SC-003**: A logged-out token is refused within one request cycle, with no window where it could be reused
- **SC-004**: The system sustains 500 concurrent authentication requests without degraded response times or token issuance errors
- **SC-005**: Every authentication event (success, failure, refresh, logout) is captured in the audit log with no omissions

## Assumptions

- Users are already registered in the system; this feature covers authentication only, not registration or account creation
- Credentials are email-address and password pairs; social login and SSO are out of scope for this iteration
- The platform is a web API consumed by a browser-based frontend; mobile native clients are out of scope for v1
- Access tokens are short-lived (15 minutes); refresh tokens are long-lived (7 days) — these are configurable defaults
- The constitution's mandate of OAuth 2.0 with JWT applies here; token signing algorithm and key rotation will be addressed in the engineering plan
- Network transport is secured (HTTPS/TLS) at the infrastructure layer, outside the scope of this specification
- Audit logs defined here feed into the platform-wide audit logging established in the constitution
