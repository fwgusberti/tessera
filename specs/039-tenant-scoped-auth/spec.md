# Feature Specification: Tenant-Scoped Authentication

**Feature Branch**: `039-tenant-scoped-auth`

**Created**: 2026-06-28

**Status**: Draft

**Input**: User description: "Make api authentication scoped on a tenant. My authentication must be scoped on a tenant and access only information of that tenant. Also the tenant I'm scoped must be a tenant that my user has access. Admins must also be scoped"

## Clarifications

### Session 2026-06-28

- Q: How is the tenant scope declared when obtaining a credential? → A: Implicit — tenant is derived automatically from the user's single membership; falls back to a two-step token-exchange when multiple memberships exist.
- Q: How should membership revocation be enforced during request validation? → A: Active membership check on every request — revocation takes effect immediately on the next call.
- Q: When a user with zero memberships logs in, what should happen? → A: Login succeeds; a zero-tenant credential is issued that is valid only for onboarding/join flows, not for any data-access endpoints.
- Q: What can a multi-membership user's unscoped temporary credential access while awaiting tenant selection? → A: Only the tenant-selection endpoint — no data access of any kind.
- Q: Does the tenant-selection/token-exchange endpoint require a credential? → A: Yes — the temporary unscoped credential issued at login is required; the exchange endpoint is not accessible unauthenticated.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Authenticate and Scope to a Tenant (Priority: P1)

A user logs in and the system automatically scopes their credential to their tenant. If the user belongs to exactly one tenant, that tenant is selected automatically. If the user belongs to multiple tenants, authentication returns an unscoped temporary credential and the user must perform a separate tenant-selection step to obtain a fully scoped credential. The resulting credential carries the tenant context, and every subsequent request is automatically restricted to that tenant's data.

**Why this priority**: This is the foundational behaviour. Without it, no other tenant-scoping guarantee can hold — requests arriving without a declared tenant context must be rejected or default-denied.

**Independent Test**: Log in as a single-membership user; verify that the credential is automatically scoped to that membership's tenant and all subsequent API calls return only data belonging to that company.

**Acceptance Scenarios**:

1. **Given** a user who is a member of exactly one company (Company A), **When** they authenticate, **Then** their credential is automatically scoped to Company A — no additional selection step required.
2. **Given** a user who is a member of both Company A and Company B, **When** they authenticate, **Then** the response signals that tenant selection is required; a fully scoped credential is not yet issued.
3. **Given** a multi-tenant user holding an unscoped temporary credential, **When** they select Company B as the active tenant, **Then** a fully scoped credential for Company B is issued.
4. **Given** a multi-tenant user holding an unscoped temporary credential, **When** they attempt to access any endpoint other than the tenant-selection endpoint, **Then** the request is rejected with 403.
5. **Given** a valid credential scoped to Company A, **When** a request is made that would touch Company B's data, **Then** the system returns a 403 Forbidden or an empty result — never Company B's data.

---

### User Story 2 - Reject Authentication for Non-Member Tenants (Priority: P1)

A user must not be able to scope their credential to a tenant they do not belong to, even if they know the tenant's identifier.

**Why this priority**: Without this gate, any user who can guess or discover a tenant ID could obtain a scoped credential for that tenant, bypassing membership controls entirely.

**Independent Test**: Attempt to authenticate scoped to a company the user has no membership in; verify the credential is refused.

**Acceptance Scenarios**:

1. **Given** a user with no membership in Company X, **When** they attempt to authenticate scoped to Company X, **Then** the system refuses to issue a credential for Company X (401 or 403 response).
2. **Given** a user whose membership in Company Y has been removed, **When** they attempt to use an existing credential scoped to Company Y, **Then** the credential is invalidated or rejected on the next request validation.
3. **Given** a user with no memberships at all, **When** they attempt to authenticate scoped to any company, **Then** the system refuses with a clear error indicating no valid tenancy.

---

### User Story 3 - Admin Authority Confined to the Scoped Tenant (Priority: P2)

A user with administrative privileges in a tenant is an admin only within the scope of that tenant. Their admin rights do not carry over to other tenants, and their credential cannot be used to perform admin actions on data outside the active tenant.

**Why this priority**: Admin authority that is not tenant-scoped creates a privilege-escalation path — an admin of one tenant could manipulate another tenant's configuration, members, or data.

**Independent Test**: Log in as an admin of Company A; attempt an admin-only operation on Company B's resources; verify the operation is denied.

**Acceptance Scenarios**:

1. **Given** a user who is an admin of Company A (but a regular member or non-member of Company B), **When** they authenticate scoped to Company A and attempt an admin action on Company B's resources, **Then** the action is rejected (403).
2. **Given** a user who is an admin of Company A, **When** they authenticate scoped to Company A, **Then** admin-protected operations succeed only for Company A's own resources.
3. **Given** a user who is an admin of both Company A and Company B, **When** they authenticate scoped to Company A, **Then** admin rights apply only to Company A — Company B's admin operations require re-authenticating scoped to Company B.

---

### User Story 4 - Switch Active Tenant Without Full Re-Login (Priority: P3)

A user who belongs to multiple tenants can switch their active tenant context without re-entering credentials, as long as the target tenant is one they are a member of.

**Why this priority**: Convenience for multi-tenant users, but the primary correctness requirement is scoping — switching is a secondary quality-of-life feature and can be deferred.

**Independent Test**: Authenticate scoped to Company A; request a tenant switch to Company B (of which the user is also a member); verify the new credential is scoped to Company B.

**Acceptance Scenarios**:

1. **Given** a credential scoped to Company A and the user is also a member of Company B, **When** the user requests a switch to Company B, **Then** a new credential scoped to Company B is issued without requiring password re-entry.
2. **Given** a credential scoped to Company A, **When** the user requests a switch to Company C where they have no membership, **Then** the switch is denied (403) and the existing credential remains scoped to Company A.

---

### Edge Cases

- What happens when a user's membership is revoked while they hold an active scoped credential? The credential must be invalidated or refused on the next validation cycle.
- What happens if a tenant is deleted or suspended while a user holds a scoped credential for it? All requests using that credential must be rejected.
- What happens when a request arrives without any tenant scope at all? The system must reject it with a clear error (not silently default to any tenant's data).
- How does the system handle a user who is a member of zero tenants? Login succeeds and a zero-tenant credential is issued; this credential grants access only to onboarding/join endpoints — all data-access endpoints must reject it with 403.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: If the authenticating user has exactly one active membership, the system MUST automatically scope the issued credential to that tenant without requiring an additional selection step. If the user has multiple active memberships, the system MUST issue a temporary unscoped credential valid solely for the tenant-selection endpoint; all other endpoints MUST reject it with 403 until a fully scoped credential is obtained.
- **FR-002**: The system MUST validate that the declaring user holds an active membership in the target tenant before issuing a scoped credential; absent membership MUST result in a 401 or 403 response.
- **FR-003**: Every scoped credential MUST embed the active tenant identifier such that it cannot be modified by the client without invalidating the credential.
- **FR-004**: All data-access operations performed with a scoped credential MUST be automatically restricted to the embedded tenant — no request-time tenant override from client-supplied headers or parameters is permitted.
- **FR-005**: Admin-level privileges encoded in the scoped credential MUST apply exclusively to the embedded tenant; admin rights MUST NOT be evaluated against any other tenant.
- **FR-006**: On every authenticated request the system MUST verify that the credential's embedded membership is still active and that the tenant is not deactivated; a credential failing either check MUST be rejected immediately (not deferred to expiry).
- **FR-007**: The system MUST provide a tenant-selection endpoint that accepts a valid temporary unscoped credential and a target tenant identifier, validates membership, and returns a fully scoped credential — without requiring password re-entry. This endpoint MUST reject unauthenticated calls and calls bearing an already fully scoped credential.
- **FR-008**: Requests arriving without a valid scoped credential MUST be rejected with an appropriate authentication error — the system MUST NOT fall back to unscoped or cross-tenant data access.
- **FR-010**: A user with zero active memberships MUST receive a zero-tenant credential upon successful login. This credential MUST be accepted only by onboarding and company-join endpoints; all other data-access endpoints MUST reject it with 403.
- **FR-009**: The system MUST log credential issuance events, recording the actor, the tenant scoped to, and the timestamp, to support audit requirements.

### Key Entities

- **User**: An authenticated principal who may hold membership in one or more tenants. A user's identity is independent of any single tenant.
- **Tenant (Company)**: The isolated organisational unit whose data must be protected. Identified by a stable, system-assigned identifier.
- **Membership**: The relationship between a User and a Tenant, which may carry a role (e.g., member, admin). Scoping is only valid if an active membership exists.
- **Scoped Credential**: The token or session object issued after authentication. Carries the user identity AND the active tenant identifier. Treated as authoritative by all data-access layers.
- **Role within Tenant**: The privilege level (member, admin, etc.) a user holds within a specific tenant. Role evaluation is always relative to the credential's embedded tenant.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of API responses accessed via a scoped credential contain only data belonging to the embedded tenant — zero cross-tenant data leakage in any automated isolation test.
- **SC-002**: Attempts to obtain a scoped credential for a tenant the user is not a member of are rejected in 100% of cases — no false grants measurable in test suite execution.
- **SC-003**: Admin operations performed with a credential scoped to Tenant A are denied for Tenant B's resources in 100% of automated cross-tenant admin tests.
- **SC-004**: Credential issuance for any tenant completes within the same response-time budget as the current unauthenticated baseline — no measurable latency regression from the scoping check.
- **SC-005**: Revoked memberships result in credential rejection on the very next request — enforced by an active membership check on each request, with zero reliance on credential expiry for revocation timing.

## Assumptions

- The system already has a concept of company membership (established in prior work); this feature builds on that relationship rather than redefining it.
- For single-membership users the active tenant is automatically resolved at login; for multi-membership users it is declared in a separate token-exchange step. In both cases the issued credential is immutable after issuance.
- There is no concept of a "super-admin" who bypasses tenant scoping in normal API flows; any such privileged access is out of scope and would require a separate, audited mechanism.
- Credential lifetime and refresh policies follow existing session management rules; this feature adds tenant-scoping to credentials but does not change expiry or rotation policies.
- Users with zero memberships receive a zero-tenant credential at login; the onboarding/join flow is responsible for granting their first membership, after which they obtain a fully scoped credential.
- The frontend client is responsible for presenting the tenant selection UI (for multi-membership users); the API layer validates and enforces the selection — UI design is out of scope for this specification.
- Switching the active tenant produces a new scoped credential, not a mutation of the existing one.
