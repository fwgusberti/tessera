# Feature Specification: Close Company & User Scope Gaps

**Feature Branch**: `035-fix-tenant-scope-gaps`

**Created**: 2026-06-23

**Status**: Draft

**Input**: User description: "check this app for company and user scopes errors"

## Overview

An audit of the platform found several places where data and actions are **not**
correctly restricted to the company (tenant) the signed-in person is currently
working in, and where actions are **not** correctly restricted to people who hold
the right role. As a result, a person signed in to Company A can, in several
flows, read or change data that belongs to Company B, and some powerful actions
are gated by a single global "administrator" flag rather than by the person's
role inside the specific company that owns the resource.

This feature closes those gaps so that **every** piece of company-owned data and
**every** company action is strictly limited to the company the person is acting
on behalf of, and to people authorized within that company.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Document change proposals stay inside the company (Priority: P1)

When a reviewer opens the list of pending document-change proposals, or opens,
approves, or rejects an individual proposal, they must only ever see and act on
proposals that belong to documents in their own company. Today, the proposal
review flow returns and acts on proposals across **all** companies and lets any
signed-in person approve or reject any proposal — including silently rewriting a
document that belongs to another company.

**Why this priority**: This is the most severe gap found. It exposes another
company's document contents (read) and allows modifying another company's
published documents (write) — a direct, two-way breach of tenant isolation.

**Independent Test**: Sign in as a member of Company B and attempt to list,
open, approve, and reject a proposal that belongs to Company A. Every attempt
must be refused (or return nothing), and Company A's document must remain
unchanged.

**Acceptance Scenarios**:

1. **Given** a pending proposal owned by Company A, **When** a Company B member
   lists proposals, **Then** the Company A proposal does not appear.
2. **Given** a proposal ID owned by Company A, **When** a Company B member opens
   it by ID, **Then** access is denied and no document content is returned.
3. **Given** a proposal ID owned by Company A, **When** a Company B member
   approves it, **Then** the action is refused and Company A's document and its
   version history are unchanged.
4. **Given** a proposal ID owned by Company A, **When** a Company B member
   rejects it, **Then** the action is refused and the proposal's state is
   unchanged.
5. **Given** a member of Company A who lacks permission to publish in the
   relevant space, **When** they approve a proposal in that space, **Then** the
   action is refused based on their role.

---

### User Story 2 - Data-source connectors stay inside the company (Priority: P1)

When an administrator creates a connector for a space or triggers a connector
sync, the target space and connector must belong to a company they administer.
Today these actions are gated only by a single global administrator flag and do
not verify that the space or connector belongs to the administrator's company,
so an administrator of one company can attach a connector to — or trigger a sync
on — another company's space.

**Why this priority**: Connectors ingest external content into a company's
knowledge base and can be pointed at arbitrary sources. Cross-company connector
creation or sync corrupts or pollutes another tenant's data and may exfiltrate
content.

**Independent Test**: Sign in as an administrator of Company B and attempt to
create a connector on a Company A space and to sync a Company A connector. Both
must be refused.

**Acceptance Scenarios**:

1. **Given** a space owned by Company A, **When** a Company B administrator
   creates a connector on it, **Then** the action is refused.
2. **Given** a connector owned by Company A, **When** a Company B administrator
   triggers a sync, **Then** the action is refused and no sync job is started.
3. **Given** a space owned by the administrator's own company, **When** they
   create a connector, **Then** it succeeds and is bound to that company.

---

### User Story 3 - Agent access tokens stay inside the company (Priority: P1)

When an administrator issues an agent access token scoped to one or more spaces,
those spaces must belong to a company they administer; and when they revoke a
token, that token must belong to their company. Today token issuance does not
verify the listed spaces belong to the administrator's company, and revocation
does not verify the token belongs to their company, so an administrator can mint
a token granting access to another company's spaces or revoke another company's
tokens.

**Why this priority**: Agent tokens grant programmatic read access to space
content. A token scoped to another company's spaces is a standing cross-tenant
data-access credential.

**Independent Test**: Sign in as an administrator of Company B and attempt to
issue a token scoped to a Company A space, and to revoke a Company A token. Both
must be refused.

**Acceptance Scenarios**:

1. **Given** a space owned by Company A, **When** a Company B administrator
   requests a token scoped to that space, **Then** the request is refused.
2. **Given** a token owned by Company A, **When** a Company B administrator
   revokes it, **Then** the request is refused and the token remains active.
3. **Given** spaces owned by the administrator's own company, **When** they
   issue a token, **Then** it succeeds and is bound to that company.

---

### User Story 4 - Space permissions and member management stay inside the company (Priority: P2)

When someone manages a space's role permissions or its member roster (inviting,
changing roles, removing, or viewing their own membership), the target space
must belong to the company they are acting in, and the action must be allowed by
their role. Today the member-roster read path verifies the active company, but
the matching write paths and the role-permission action do not apply the same
company check consistently.

**Why this priority**: Membership and permission changes alter who can see and
edit company content. Inconsistent company checks across read and write paths
are an exploitable gap, though narrower than the wholesale exposure in P1
stories.

**Independent Test**: Sign in as a member of Company B and attempt each member-
management and permission action against a Company A space. Every attempt must
be refused, identically to how the list-members read path already refuses it.

**Acceptance Scenarios**:

1. **Given** a space owned by Company A, **When** a Company B member invites,
   changes a role, removes a member, or sets a role permission, **Then** the
   action is refused.
2. **Given** a space owned by Company A, **When** a Company B member checks their
   own membership in it, **Then** the response does not reveal Company A data.
3. **Given** a space in the member's own company where their role does not permit
   the action, **When** they attempt it, **Then** it is refused based on role.

---

### User Story 5 - Usage metrics reflect only the active company (Priority: P2)

When an administrator views usage metrics (such as total queries and pending
proposals), the numbers must reflect only their own company. Today the metrics
are aggregated across **all** companies, so any administrator sees platform-wide
totals that include other companies' activity.

**Why this priority**: Aggregated counts leak the existence, scale, and activity
level of other tenants. It is an information-disclosure gap rather than direct
record exposure, hence P2.

**Independent Test**: With known activity in Company A and Company B, sign in as
a Company B administrator and confirm the reported metrics match Company B's
activity only.

**Acceptance Scenarios**:

1. **Given** recorded activity in both Company A and Company B, **When** a
   Company B administrator views metrics, **Then** the totals exclude Company A's
   activity.
2. **Given** an administrator of a single company, **When** they view metrics,
   **Then** every reported number is attributable to that company.

---

### User Story 6 - Administrator power is scoped to a single company (Priority: P2)

Being an administrator of one company must not, by itself, grant administrative
power over another company. Today several powerful actions (connectors, agent
tokens, role permissions, metrics) are gated by a single global administrator
indicator carried in the session rather than by the person's administrator role
**within the company that owns the resource**.

**Why this priority**: This is the common root cause behind several P1/P2
stories. Fixing it (authorize by the person's role in the owning company)
hardens every administrator-gated action at once.

**Independent Test**: Take a person who is an administrator of Company A but only
a regular member (or non-member) of Company B, and confirm they cannot perform
administrator-only actions against Company B resources.

**Acceptance Scenarios**:

1. **Given** a person who administers Company A and is a regular member of
   Company B, **When** they attempt an administrator-only action on a Company B
   resource, **Then** it is refused.
2. **Given** a person who administers the company that owns the resource, **When**
   they perform the administrator-only action, **Then** it succeeds.

---

### Edge Cases

- **No active company**: A signed-in person with no active company context who
  requests company-owned data is refused, never shown data.
- **Membership revoked mid-session**: A person whose membership in the active
  company was revoked after they signed in is refused on the next request, even
  if they still hold a valid session.
- **Existing ID, wrong owner**: Requesting a real resource ID that belongs to
  another company yields a denial or "not found", never the other company's data
  — and the two cases are indistinguishable to the caller, so resource existence
  in other companies cannot be probed.
- **Legitimate cross-company person**: A person who belongs to several companies
  sees and acts only within the company currently active for the request;
  switching the active company switches the visible data atomically.
- **Intentional platform-wide operations**: Any genuinely platform-wide action
  (if one exists) must be an explicitly identified, separately authorized, and
  audit-logged exception — not an accidental side effect of a missing company
  check.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST restrict every read of company-owned data
  (proposals, documents, spaces, connectors, agent tokens, members, metrics) to
  the company that is active for the request.
- **FR-002**: The system MUST restrict every change to company-owned data to the
  company that is active for the request.
- **FR-003**: The document-change-proposal flows (list, view, approve, reject)
  MUST only return and act on proposals whose underlying document belongs to the
  active company.
- **FR-004**: Approving or rejecting a proposal MUST additionally require that
  the person holds a role permitting that action in the relevant space, not
  merely that they are signed in.
- **FR-005**: Creating a connector on a space MUST verify the space belongs to
  the active company; triggering a connector sync MUST verify the connector
  belongs to the active company.
- **FR-006**: Issuing an agent access token MUST verify every space it is scoped
  to belongs to the active company; revoking a token MUST verify the token
  belongs to the active company.
- **FR-007**: Setting a space role-permission and all member-management actions
  (invite, change role, remove, view own membership) MUST verify the target
  space belongs to the active company, consistently across read and write paths.
- **FR-008**: Usage metrics MUST be computed only from the active company's
  activity and MUST NOT include any other company's data.
- **FR-009**: Administrator-only actions MUST be authorized by the person's
  administrator role **within the company that owns the targeted resource**, not
  by a single global administrator indicator that ignores which company owns the
  resource.
- **FR-010**: When access is denied for tenant or role reasons, the system MUST
  NOT reveal whether the requested resource exists in another company; denial and
  "not found" MUST be indistinguishable to the caller.
- **FR-011**: A request without an established active-company context MUST be
  refused for any company-owned data or action.
- **FR-012**: A request from a person whose membership in the active company has
  been revoked MUST be refused, even within an otherwise-valid session.
- **FR-013**: Each blocked cross-company attempt on a sensitive resource MUST be
  recorded in the audit log with the actor, the action, and the targeted
  resource, consistent with how such denials are already recorded elsewhere.
- **FR-014**: Any intentionally platform-wide operation MUST be explicitly
  identified, separately authorized, and audit-logged; no platform-wide data
  exposure may occur as an unstated default.

### Key Entities *(include if feature involves data)*

- **Company (tenant)**: The unit of isolation. Every company-owned resource
  belongs to exactly one company; all access is scoped to the active company.
- **Person / Membership**: A person may belong to multiple companies, each with a
  role (e.g., administrator or member). Authority is determined per company.
- **Active company context**: The single company a given request acts on behalf
  of, established at sign-in or company switch.
- **Document change proposal**: A proposed edit to a company's document; owned
  transitively by the document's company.
- **Connector**: An ingestion source attached to a space; owned by the space's
  company.
- **Agent access token**: A programmatic credential scoped to one or more spaces;
  owned by the spaces' company.
- **Space permission / Space membership**: Role grants attached to a space; owned
  by the space's company.
- **Usage metrics**: Aggregated activity counts; must be partitioned by company.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of flows that return company-owned data refuse, or return
  nothing for, a request made on behalf of a different company — verified by an
  automated cross-company test for every such flow.
- **SC-002**: 100% of flows that change company-owned data refuse a request made
  on behalf of a different company, with the target data left unchanged —
  verified by an automated cross-company test for every such flow.
- **SC-003**: Zero flows expose aggregate counts or any other data that includes
  more than one company.
- **SC-004**: Every administrator-only action refuses a person who administers a
  different company but not the company that owns the targeted resource.
- **SC-005**: For every targeted resource type, a denial for a cross-company
  request is indistinguishable from a "not found" response, so resource
  existence in other companies cannot be inferred.
- **SC-006**: Every blocked cross-company attempt on a sensitive resource appears
  in the audit log with actor, action, and targeted resource.

## Assumptions

- The mechanism that establishes the active company for a request already exists
  and is trusted (it is used correctly by the space, document, search, and
  assistant flows today); this feature extends that same scoping to the flows
  currently missing it.
- "Refused" may be presented as either an access-denied or a not-found outcome,
  provided the two are indistinguishable to the caller for cross-company access.
- Distinguishing a global "platform operator" capability from a per-company
  administrator role is in scope only insofar as needed to stop per-company
  administrator actions from leaking across companies; building a full platform-
  operator console is out of scope.
- Existing audit-logging behavior for denied cross-company access is the model to
  follow for the newly guarded flows.
- No new resource types are introduced; this feature hardens scoping on resources
  that already exist.
