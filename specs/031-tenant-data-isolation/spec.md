# Feature Specification: Tenant Data Isolation

**Feature Branch**: `031-tenant-data-isolation`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "Companies are accessing spaces of one another. Companies must access only its own data. Data from a company must be isolated from other and comply with most rigid information security standards"

## Clarifications

### Session 2026-06-22

- Q: What HTTP status code should be returned for cross-tenant access attempts (FR-006)? → A: 404 Not Found — complete existence denial; maximally hides the resource from other tenants.
- Q: How should the migration handle existing `spaces` rows with no company association? → A: Auto-assign to the oldest company — orphaned spaces get the first-created company as owner; manual review can follow.
- Q: Is the MCP server (`apps/mcp-server`) in scope for tenant isolation enforcement? → A: In scope, but addressed in a dedicated sub-task within this feature — not in the same PR as the API changes.
- Q: What should tenant-scoped endpoints return when a user is authenticated but has no active company context? → A: HTTP 403 Forbidden with error code `"no_company_context"` — authenticated but no active tenant; client redirects to company selection.
- Q: Should failed cross-tenant access attempts (read denials) emit audit events? → A: Yes — all cross-tenant access denials are logged as audit events to enable detection of enumeration probes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Block Cross-Company Space Access (Priority: P1)

A user authenticated under Company A attempts to view, list, or interact with a Space that belongs to Company B. The system must refuse the request and return no data belonging to Company B.

**Why this priority**: This is the core security breach being reported. Unauthorized visibility into another company's Spaces is a data breach regardless of whether the user can read documents inside. Closing this gap first removes the most visible exposure.

**Independent Test**: Can be fully tested by authenticating two separate companies, creating a Space under each, then confirming that a user from Company A receives an access-denied or empty result when requesting Company B's Space list or details.

**Acceptance Scenarios**:

1. **Given** a user is authenticated as a member of Company A, **When** they request the list of Spaces, **Then** only Spaces owned by Company A are returned — no Spaces from any other company appear.
2. **Given** a user is authenticated as a member of Company A, **When** they request the details of a specific Space owned by Company B using that Space's identifier, **Then** they receive an access-denied response and no Company B data is disclosed.
3. **Given** a user is authenticated as a member of Company A, **When** they attempt to modify or delete a Space owned by Company B, **Then** the action is rejected and no change is made to Company B's data.

---

### User Story 2 - Block Cross-Company Document Access (Priority: P1)

A user authenticated under Company A attempts to read, search, or interact with Documents that belong to Company B. The system must refuse and return no Company B content.

**Why this priority**: Documents contain the primary business content and carry the highest confidentiality risk. Cross-tenant document access is a direct data breach at the content level.

**Independent Test**: Can be fully tested by creating documents under two companies, then confirming that a user from Company A cannot retrieve, read, or discover documents owned by Company B via any access path (direct ID lookup, search, listing).

**Acceptance Scenarios**:

1. **Given** a user is authenticated as a member of Company A, **When** they search for documents, **Then** only documents belonging to Company A's Spaces are returned.
2. **Given** a user is authenticated as a member of Company A, **When** they request a specific Document using an identifier belonging to Company B, **Then** they receive an access-denied response.
3. **Given** a user is authenticated as a member of Company A, **When** they interact with the AI assistant or citation features, **Then** all retrieved content originates exclusively from Company A's data.

---

### User Story 3 - Isolate Member and Organizational Data (Priority: P2)

A user authenticated under Company A cannot view the member roster, organizational settings, or any administrative data belonging to Company B.

**Why this priority**: Member data (names, emails, roles) constitutes personal information. Exposure across companies violates privacy obligations in addition to information security standards.

**Independent Test**: Can be fully tested by confirming that a Company A user's member-list and settings views contain no entries from Company B.

**Acceptance Scenarios**:

1. **Given** a user is authenticated as a member of Company A, **When** they view the company member list, **Then** only members who belong to Company A are shown.
2. **Given** a user is authenticated as a member of Company A, **When** they access company settings or profile, **Then** only Company A's organizational data is presented.

---

### User Story 4 - Enforce Isolation Across All Session and Context Switches (Priority: P2)

A user who is a member of multiple companies can switch their active company context; after switching, all data visible to them must reflect only the newly active company — no residual data from the previous context must persist.

**Why this priority**: Multi-company membership is a supported feature. Without explicit isolation on context switch, a session could carry stale tenant context and expose the wrong company's data.

**Independent Test**: Can be fully tested by authenticating as a user who belongs to both Company A and Company B, switching context from A to B, and confirming that all subsequent data views show only Company B's data.

**Acceptance Scenarios**:

1. **Given** a user belongs to both Company A and Company B and is currently operating under Company A, **When** they switch to Company B, **Then** all subsequent data requests return only Company B's data and nothing from Company A.
2. **Given** a user switches company context, **When** any cached or pre-fetched data from the previous context is present, **Then** it is not displayed or accessible in the new context.

---

### Edge Cases

- What happens when a user provides a manipulated session or token claiming membership in a company they do not belong to? The system must reject the request at the authentication boundary.
- What happens when an entity identifier (Space ID, Document ID) is guessed or enumerated by a user from a different company? The system must return **HTTP 404 Not Found** — complete existence denial — without revealing whether the entity exists in another tenant.
- What happens when a user's membership is revoked from a company while they hold an active session? Subsequent requests must enforce the updated membership state.
- How does the system behave when a company has zero Spaces or Documents? Listings return empty results — not an error, and not another company's data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST determine the active company context exclusively from the authenticated session; it MUST NOT accept or honor company identifiers supplied by the client in request bodies, query parameters, or headers.
- **FR-002**: Every operation that retrieves, modifies, or deletes Spaces MUST be filtered by the authenticated company's identifier; unscoped access to Spaces is PROHIBITED.
- **FR-003**: Every operation that retrieves, modifies, or deletes Documents MUST be filtered by the authenticated company's identifier; unscoped document access is PROHIBITED.
- **FR-004**: Every operation that retrieves or modifies company membership data MUST be filtered by the authenticated company's identifier.
- **FR-005**: Every AI-assisted operation (search, retrieval-augmented generation, citation) MUST restrict its data source to the authenticated company's data.
- **FR-006**: A cross-tenant access attempt — any request for an entity belonging to a different company — MUST result in HTTP 404 Not Found; the response MUST NOT disclose whether the entity exists in another company (complete existence denial).
- **FR-007**: Company context MUST be propagated unchanged from the request boundary through every downstream service and data-access call in the same request; no layer may re-derive or override the company context from user-provided data.
- **FR-011**: An authenticated request with no active company context (user has not yet activated a company) MUST receive HTTP 403 Forbidden with error code `"no_company_context"`. This response signals the client to redirect the user to company selection; it MUST be distinguishable from a cross-tenant denial (FR-006, which returns 404).
- **FR-012**: Every cross-tenant access denial (FR-006) MUST emit a structured audit event recording the actor user ID, the requested entity type and ID, and the authenticated company context. This enables detection of enumeration probes and suspicious access patterns.
- **FR-008**: After a company context switch, the system MUST invalidate or re-scope any in-session state (cached queries, pre-fetched lists) that was bound to the previous company context.
- **FR-009**: Automated isolation tests MUST exist for every data-access path, verifying that a request authenticated under Company A cannot retrieve data belonging to Company B.
- **FR-010**: All new data-access features MUST demonstrate tenant isolation through passing automated tests before being approved for release.

### Key Entities

- **Company (Tenant)**: The top-level organizational unit. All owned data — Spaces, Documents, Memberships — belongs to exactly one Company. The Company identifier is the isolation boundary.
- **Space**: A workspace owned by a Company. Every Space carries the owning Company's identifier. Access to Spaces is always scoped by this identifier.
- **Document**: Content residing within a Space, inheriting the Company ownership of its parent Space. Document access is scoped by the owning Company.
- **Company Membership**: The relationship between a User and a Company, including the user's role within that company. Determines which company's data the user may access during a session.
- **Session / Authentication Context**: The server-side record of the authenticated user's active company. This is the authoritative source of company context for every request; it is not user-modifiable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero cross-tenant data disclosures — every data-retrieval endpoint returns exclusively the authenticated company's data across all test scenarios.
- **SC-002**: 100% of cross-tenant access attempts in automated tests result in an access-denied response or an empty result; no attempt ever returns another company's data.
- **SC-003**: Every existing data-access path (Spaces, Documents, Memberships, AI queries, search) has at least one automated isolation test covering the cross-tenant scenario.
- **SC-004**: No new data-access feature can be merged without accompanying automated isolation tests that pass in the two-company test setup.
- **SC-005**: After a company context switch, no data from the previous company context is visible in any subsequent view within the same session.
- **SC-006**: Every cross-tenant access denial produces a structured audit record in the `audit_records` table; no denial is silent.

## Assumptions

- Users may belong to multiple companies and switch their active company context; the active context is established by the session and not by client-supplied parameters.
- The system already maintains a company identifier in the authenticated session that cannot be overridden by client-side input; this identifier is the sole source of truth for tenant scoping.
- Existing data in the database may contain records that were created without strict company scoping; an audit and remediation of existing data-access layers is considered in-scope for this feature. Any existing `spaces` rows with no company association will be auto-assigned to the oldest company in the system during the migration; manual review of these assignments is expected post-deployment.
- All access paths — web frontend, REST API, and AI/chat interfaces — are in scope for isolation enforcement. The `apps/mcp-server` MCP interface is explicitly included in scope and will be addressed in a dedicated sub-task within this feature (not in the same PR as the API changes).
- Super-admin or platform-level access (if it exists) is explicitly out of scope for this feature and will be addressed separately with its own auditing and role-gating requirements.
