# Feature Specification: Company-Scoped Admin Privileges

**Feature Branch**: `036-company-scoped-admin`

**Created**: 2026-06-26

**Status**: Draft

**Input**: User description: "make an admin user only admin on its own company and cannot see another company scope. as today an admin can access every company data"

## Clarifications

### Session 2026-06-26

- Q: When an admin acts on a resource that exists but belongs to another company, what response should the caller receive (FR-004/SC-003 require it be indistinguishable from a non-existent resource)? → A: Return the standard "not found" response — identical status and body to a genuinely missing resource — so existence is never disclosed. This supersedes the prior cross-tenant behavior of returning a distinct "forbidden" outcome.
- Q: How should existing users who rely on the platform-wide admin attribute be transitioned to per-company admin authority (FR-009)? → A: Grant an explicit company-admin membership only in companies the user created/owns; do not auto-grant admin where they hold a non-admin membership, and do not elevate ordinary members elsewhere.
- Q: Which cross-company access attempts must produce an audit record (FR-008/SC-004)? → A: Every cross-company attempt on a specific resource identified by ID — both reads and mutations — produces exactly one audit record; listing endpoints that merely omit other tenants' rows produce no denial record (no specific attempted resource).

## User Scenarios & Testing *(mandatory)*

Today, being an "admin" is a platform-wide status: a user marked as admin is implicitly treated as an administrator of **every** company, and can therefore view and act on data belonging to companies they have no membership in. This feature confines admin authority to the company (or companies) where the user actually holds the admin role.

### User Story 1 - Admin authority confined to the active company (Priority: P1)

An admin of Company A manages members, connectors, agent credentials, proposals, metrics, documents, and spaces — but only within Company A. The same admin actions, when aimed at Company B's resources, are refused.

**Why this priority**: This is the core security fix. Without it, any admin can read and mutate every tenant's data, which is a critical cross-tenant data-isolation breach (Constitution Principle VI).

**Independent Test**: Sign in as an admin of Company A, perform each admin action against a Company A resource (succeeds), then repeat each action against an equivalent Company B resource (denied). Delivers the central guarantee on its own.

**Acceptance Scenarios**:

1. **Given** a user who is admin of Company A and has the active company set to Company A, **When** they manage members / connectors / credentials / metrics / proposals / documents within Company A, **Then** the actions succeed as before.
2. **Given** the same admin of Company A, **When** they attempt any admin-gated action on a resource owned by Company B, **Then** the action is denied.
3. **Given** the same admin of Company A, **When** they request a listing (members, documents, spaces, metrics), **Then** the results contain only Company A's data and never Company B's.

### User Story 2 - No cross-company visibility from admin status (Priority: P1)

Holding the admin role in one company grants no elevated read access in any other company. An admin of Company A cannot discover, view, or enumerate Company B's documents, spaces, members, connectors, credentials, or metrics.

**Why this priority**: Read-only leakage is still a data breach. Denials must also not reveal whether the other company's resource exists.

**Independent Test**: As an admin of Company A, attempt to read a known Company B resource by its identifier; confirm the response is indistinguishable from that resource not existing, and that no Company B field is ever returned.

**Acceptance Scenarios**:

1. **Given** an admin of Company A who knows the identifier of a Company B document, **When** they request that document, **Then** the response is the same generic denial returned for a non-existent resource (existence is not disclosed).
2. **Given** an admin of Company A, **When** they request any company-scoped listing, **Then** no Company B record appears under any circumstance.

### User Story 3 - Per-company authority for multi-company members (Priority: P2)

A user who is an admin in Company A and a non-admin member in Company B holds admin authority only while Company A is active, and ordinary member authority while Company B is active. Switching the active company switches which authority applies.

**Why this priority**: Real users belong to more than one company. Authority must follow the active company, not the user globally.

**Independent Test**: With a user who is admin in Company A and member in Company B, perform an admin-only action with Company A active (succeeds) and the same action with Company B active (denied as a non-admin).

**Acceptance Scenarios**:

1. **Given** a user who is admin in Company A and member in Company B, **When** Company A is active, **Then** admin-only actions on Company A resources succeed.
2. **Given** the same user, **When** Company B is active, **Then** admin-only actions are denied because the user is not an admin of Company B.

### User Story 4 - Tenant data protected from outside admins (Priority: P2)

A company's members and owners are assured that no administrator from any other company can read, modify, or delete their data, regardless of any historical platform-wide admin marking.

**Why this priority**: Frames the guarantee from the protected tenant's perspective; ensures legacy global-admin markings cannot be used as a backdoor.

**Independent Test**: Create data in Company B as its own member; with a separate Company A admin (including one carrying the legacy global-admin marking), confirm none of Company B's data can be read or changed.

**Acceptance Scenarios**:

1. **Given** a document owned by a Company B member, **When** any admin from Company A attempts to edit or delete it, **Then** the attempt is denied and the document is unchanged.
2. **Given** a user carrying the legacy platform-wide admin marking but with no membership in Company B, **When** they attempt to act on Company B data, **Then** they are treated as having no access to Company B.

### Edge Cases

- **Legacy global-admin marking**: A user previously flagged as a platform-wide admin must not gain admin authority over any company where they lack an explicit admin membership. The migration preserves their access only by granting an explicit company-admin membership in companies they created/own; a user who is merely a non-admin member of a company gains no admin authority there.
- **Admin in zero companies**: A user who holds the admin role in no company has no admin powers anywhere and is treated as an ordinary user.
- **Missing active company context**: An admin-gated request with no active company established is refused.
- **Resource exists but belongs to another company**: The caller receives the standard "not found" response (same status and body as a genuinely missing resource), so resource existence in other tenants is never disclosed.
- **Active company switched mid-session**: Authority must reflect the currently active company at the time of each action, not a stale value.
- **Platform-operator (support) access**: Legitimate cross-company support work must only be possible through a separate, explicitly modeled, audited capability — never as a side effect of ordinary company admin status.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Admin authority MUST be derived from the user's admin role within the currently active company, not from any platform-wide / global admin attribute.
- **FR-002**: Holding the admin role in one company MUST NOT grant any elevated privilege (read, write, or manage) in any other company.
- **FR-003**: Every admin-gated action MUST verify that the target resource belongs to the actor's active company before authorizing it.
- **FR-004**: When an admin attempts an action on a resource owned by a different company, the system MUST return the standard "not found" response — identical status and body to a genuinely non-existent resource — so that the existence of another company's resource is never disclosed. A distinct "forbidden" outcome MUST NOT be used for cross-company access (it would reveal that the resource exists).
- **FR-005**: A user who is an admin in multiple companies MUST have admin authority evaluated independently per company; changing the active company MUST change the applicable authority.
- **FR-006**: The system MUST NOT treat any user as an implicit administrator of spaces or documents belonging to a company where the user holds no admin membership.
- **FR-007**: Privileges over documents and spaces that were previously conferred by the platform-wide admin attribute MUST instead be derived from the user's per-company admin role.
- **FR-008**: Every cross-company access attempt on a specific resource identified by ID — whether a read or a mutation — MUST be recorded in the audit log exactly once, capturing the actor, the attempted resource, and the timestamp. Listing endpoints that merely omit other tenants' rows from results do NOT emit a denial record (there is no specific attempted resource).
- **FR-009**: Existing users who currently rely on the platform-wide admin attribute MUST be transitioned so that their effective authority over company data is determined solely by explicit per-company admin memberships. The transition MUST grant an explicit company-admin membership only in companies the user created/owns; it MUST NOT auto-grant admin in companies where the user holds a non-admin membership, and MUST NOT elevate ordinary members to admin. No legitimate access inside companies the user owns may be silently lost.
- **FR-010**: Any capability that legitimately requires cross-company access (e.g. platform operations / support) MUST remain available ONLY through an explicitly modeled, separately gated, audit-logged operation, and MUST NOT be reachable via ordinary company admin status.
- **FR-011**: All admin-gated capabilities — member management, connector management, agent-credential issuance/revocation, metrics, proposal approval/rejection, and permission management — MUST enforce company-scoped admin authorization consistently.

### Key Entities *(include if data involved)*

- **User**: An individual identity that may hold a role in one or more companies. A historical platform-wide admin attribute exists but is being retired as a source of authorization over company-owned data.
- **Company (Tenant)**: The isolation boundary that owns spaces, documents, members, connectors, agent credentials, and metrics.
- **Company Membership**: The link between a user and a company, carrying that user's role (admin or member) for that company. This is the authoritative source of admin authority.
- **Admin Role**: The company-scoped authority level that permits administrative actions, valid only within the company that granted it.
- **Audit Record**: A logged event capturing administrative actions and, in particular, cross-company access denials (actor, attempted resource, timestamp).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of admin-gated actions targeting another company's data are denied.
- **SC-002**: A user holding the admin role in exactly one company can view or modify zero resources belonging to any other company.
- **SC-003**: For every admin-gated endpoint, a cross-company access attempt returns the identical "not found" response (same status and body) as a genuinely missing resource, so resource existence is never disclosed across tenants.
- **SC-004**: Every cross-company by-ID access attempt (read or mutation) produces exactly one audit record identifying the actor and attempted resource; listing endpoints that filter out other tenants' rows produce none.
- **SC-005**: Within their own company, admins retain 100% of their prior administrative capability — all existing admin happy-path flows continue to pass (no regression).
- **SC-006**: For users who are admins in multiple companies, the correct per-company authority is applied in 100% of company-switch scenarios.
- **SC-007**: After migration, every user who created/owns a company holds an explicit company-admin membership there (no silent loss of owner access), and no user is elevated to admin in any company where they previously held only a non-admin membership.

## Assumptions

- "Admin" in this specification refers to the company-scoped admin role recorded on a company membership. The platform-wide / global admin attribute is being retired as a source of authorization over company-owned data.
- A separate platform-operator capability (for Tessera staff support tasks), as permitted by the Constitution's documented super-admin exception, remains available only through explicitly modeled, audited operations; building or expanding that capability is out of scope here. This feature only guarantees that ordinary company admin status cannot reach it.
- The active-company context is already established at sign-in and on company switch by the existing mechanism; this feature consumes it rather than redefining it.
- This feature builds directly on the tenant-isolation pattern established in features 031 and 035 (request-boundary company context, company-scoped data access, and cross-tenant denial auditing).
- Non-admin roles (member/viewer) and their permissions are unchanged except insofar as they are no longer overridden by a platform-wide admin attribute.

## Out of Scope

- Designing or building new platform-operator / support tooling beyond confirming ordinary admins cannot reach existing cross-company operations.
- Any UI redesign; this feature is an authorization-scoping change. UI surfaces only need to reflect the resulting allowed/denied outcomes.
- Changes to authentication, session management, or the company-switch mechanism themselves.

## Dependencies

- Existing company membership and role model (admin/member per company).
- Existing tenant-scoping mechanism that establishes and propagates active company context (features 031 and 035).
- Existing audit-logging facility for recording denials and administrative actions.
