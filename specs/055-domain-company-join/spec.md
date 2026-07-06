# Feature Specification: Domain-Based Company Matching on Sign-Up

**Feature Branch**: `055-domain-company-join`

**Created**: 2026-07-06

**Status**: Draft

**Input**: User description: "eu criei um usuário novo no fluxo da tela de login com o um domínio gusba.dev. após isso disparou o fluxo de criação do companhia nova. eu esperava que ficasse aguardando aprovação para entrar na companhia Gusba dev"

## Summary

A person who registers with a work email whose domain already belongs to an existing company (e.g. `felipe@gusba.dev` when a company "Gusba dev" already exists) is currently funneled straight into the *create a new company* flow. This produces duplicate companies for the same organization. The expected behavior is that the new user is shown the existing company that matches their email domain and can **request to join it and wait for approval**, instead of unknowingly creating a competing duplicate company.

This closes a gap already promised in the onboarding specification (feature 007, User Story 2, scenario 5) that never took effect because a company's email domain is never associated with it automatically — matching only works after an admin manually adds *and email-verifies* a domain policy, which new organizations almost never do before their second teammate signs up.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Join an existing company by matching email domain (Priority: P1)

A new user registers with a work email (e.g. `felipe@gusba.dev`). During onboarding, before being offered the option to create a company, they are shown any existing company whose email domain matches theirs. They choose to join that company, which sends a request to the company's administrators and places the user in a "waiting for approval" state rather than creating a new company.

**Why this priority**: This is the exact scenario the user reported and the core value of the feature — preventing duplicate/orphan companies and getting people into the right organization. Without it, the feature delivers nothing.

**Independent Test**: With an existing company associated to `gusba.dev`, register a brand-new user with an `@gusba.dev` email, complete personal profile, and verify the company-setup step surfaces "Gusba dev" with a "Request to Join" action; after requesting, verify the user sees a "waiting for approval" state and no new company was created.

**Acceptance Scenarios**:

1. **Given** a company "Gusba dev" is associated with the email domain `gusba.dev`, **When** a new user with email `felipe@gusba.dev` reaches the company-setup step of onboarding, **Then** they are shown "Gusba dev" as a matching company with an action to request to join it.
2. **Given** the user is shown the matching company, **When** they choose to request to join, **Then** a join request is recorded, the company's administrators are notified, and the user is placed in a "waiting for approval" state instead of a new company being created.
3. **Given** the user has a pending join request, **When** they revisit onboarding or reload, **Then** they continue to see the "waiting for approval" state for that company (not the create-company form and not a duplicate request).
4. **Given** the user's email domain matches an existing company, **When** they reach the company-setup step, **Then** the "Create a new company" option is de-emphasized (secondary) relative to joining the matching company, so joining is the obvious default path.

---

### User Story 2 - Administrator approves or rejects a join request (Priority: P1)

An administrator of the matched company sees pending join requests from users whose email domain matches the company and can approve or reject each one. Approval adds the user to the company as a member; rejection informs the requester.

**Why this priority**: A "waiting for approval" state is meaningless without a way to grant approval. This is the other half of the P1 loop — together US1 + US2 form the minimum viable feature.

**Independent Test**: As an admin of "Gusba dev", after a user requests to join, verify the pending request is visible, approve it, and confirm the requester becomes a company member with access; separately reject a request and confirm the requester is denied.

**Acceptance Scenarios**:

1. **Given** a user has requested to join a company by domain match, **When** an administrator of that company views pending join requests, **Then** the request appears with the requester's identity and email.
2. **Given** a pending join request, **When** an administrator approves it, **Then** the requester becomes a member of the company, gains access to it on their next session, and is notified of the approval.
3. **Given** a pending join request, **When** an administrator rejects it, **Then** the requester is not added, is informed the request was declined, and may then create their own company or request a different one.
4. **Given** a join request has already been decided, **When** an administrator views it, **Then** it is no longer actionable as pending (no double approval).

---

### User Story 3 - A company becomes matchable by its email domain (Priority: P1)

When a founder creates a new company using a work email, the company automatically becomes matchable by that email's domain, so that future teammates who register with the same domain are routed to it. Generic/public email providers (e.g. gmail.com, outlook.com) do not make a company matchable, to avoid unrelated users being matched to each other.

**Why this priority**: This is the missing link that made the reported bug possible. Without a company being associated to its domain at creation time, US1 can never trigger for organically-created companies. It is foundational to the whole feature, hence P1.

**Independent Test**: Create a company as `founder@acme.example` (a non-public domain) and verify that a subsequent registrant with `@acme.example` is offered to join it; separately create a company as `person@gmail.com` and verify a later `@gmail.com` registrant is NOT matched to it.

**Acceptance Scenarios**:

1. **Given** a user creates a company using a work email on a non-public domain, **When** the company is created, **Then** that domain is associated with the company for matching purposes.
2. **Given** a user creates a company using a public/generic email provider domain, **When** the company is created, **Then** no domain association is made and later users on that public domain are not matched to it.
3. **Given** a domain is already associated with an existing company, **When** another user tries to create a second company using the same non-public domain, **Then** they are first shown the existing matching company and steered toward joining it rather than silently creating a duplicate.

---

### Edge Cases

- **Multiple matching companies**: If more than one existing company is associated with the user's domain, all matches are presented and the user chooses which to request to join.
- **Both an invitation and a domain match**: If the user also has a pending email invitation to a company, the invitation takes priority and is presented first; accepting an invitation grants access without requiring approval (consistent with feature 007).
- **Public / free email providers**: Registrations from public domains (gmail.com, outlook.com, hotmail.com, yahoo.com, icloud.com, etc.) are never used for company matching, in either direction.
- **Duplicate request**: A user who already has a pending or approved membership/request for a company cannot create a second pending request for the same company.
- **Case / formatting of domains**: Matching is case-insensitive and ignores an optional leading `@`; `Gusba.DEV`, `gusba.dev`, and `@gusba.dev` are treated as the same domain.
- **Already a member**: If the user is already a member of the matching company, no join request is offered.
- **User abandons at the waiting state**: A user with only a pending request and no company has not "completed" onboarding into a company; they can still choose to create their own company or wait.
- **Admin acts on a stale request**: Approving/rejecting an already-decided request has no additional effect and reports the current status.
- **Requester leaves before decision**: A join request for a user who is later removed/deleted is cleaned up and does not appear as actionable to admins.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When a new user reaches the company-setup step of onboarding, the system MUST detect existing companies whose associated email domain matches the domain of the user's registered email and present them as companies the user can request to join.
- **FR-002**: The system MUST allow a user to request to join a domain-matched company, which creates a pending join request rather than adding the user immediately.
- **FR-003**: After requesting to join, the system MUST place the user in a "waiting for approval" state and MUST NOT create a new company on their behalf as a side effect of the domain match.
- **FR-004**: The system MUST notify the matched company's administrators when a new join request is created.
- **FR-005**: Administrators of a company MUST be able to view its pending join requests, including the requester's identity and email.
- **FR-006**: Administrators MUST be able to approve a pending join request, which adds the requester as a member of the company with a default (non-admin) role.
- **FR-007**: Administrators MUST be able to reject a pending join request, which leaves the requester unaffiliated and informs them of the outcome.
- **FR-008**: The system MUST notify the requester when their join request is approved or rejected.
- **FR-009**: When a company is created using a work email on a non-public domain, the system MUST automatically associate that company with the email's domain so future same-domain registrants are matched to it, with the default join behavior being "request approval" (not instant/auto-join).
- **FR-010**: The system MUST NOT associate a company with, or produce domain matches for, public/free email provider domains (e.g. gmail.com, outlook.com, hotmail.com, yahoo.com, icloud.com).
- **FR-011**: Domain matching MUST be case-insensitive and MUST ignore a leading `@`, so equivalent domain strings match the same company.
- **FR-012**: The system MUST prevent creating a duplicate pending join request when the user already has a pending request or an existing membership for the same company.
- **FR-013**: When a domain match exists, the company-setup step MUST present joining the matched company as the primary path and present "Create a new company" as a secondary option, so a user is not silently steered into creating a duplicate.
- **FR-014**: When the user also has a pending email invitation, the invitation MUST be presented with priority over a domain match, and accepting an invitation MUST grant membership without requiring approval.
- **FR-015**: The system MUST prevent an administrator from acting more than once on the same join request (an already-decided request is not re-decidable).
- **FR-016**: A user who becomes a member via an approved join request MUST gain access to the company (its spaces and content, per existing membership rules) on their next session.

### Key Entities *(include if data involved)*

- **Company**: An organization users belong to. Relevant here for its association to one or more email domains used for matching. Already exists.
- **Company Domain Association**: The link between a company and an email domain that makes the company matchable to registrants on that domain, including the join behavior (request-approval vs. auto-join) for that domain. Established automatically at company creation from a non-public founder email.
- **Join Request**: A pending request by a user to join a specific company, with a status (pending / approved / rejected), the requesting user, the target company, and who decided it. Already exists.
- **Company Membership**: The relationship granting a user access to a company with a role. Created when a join request is approved. Already exists.
- **Public Domain List**: The set of generic/free email provider domains that are excluded from company matching in both directions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user who registers with an email domain that matches an existing company is presented that company to join before any option to create a new company, in 100% of cases where a non-public domain match exists.
- **SC-002**: Zero new companies are created as an automatic side effect of a user choosing to join a domain-matched company (a duplicate company is only ever created by an explicit "create a new company" action).
- **SC-003**: An administrator can go from an incoming join request to an approved, access-granted member in under 1 minute of interaction.
- **SC-004**: Registrations on public/free email provider domains produce zero cross-company matches (no user is ever matched to a stranger's company via a shared public domain).
- **SC-005**: Duplicate-company creation for the same organization drops measurably after release, evidenced by a reduction in companies sharing a single non-public email domain compared to before the feature.

## Assumptions

- The default join behavior for an auto-associated domain is **request approval** (pending admin decision), matching the reporter's expectation of "waiting for approval." Auto-join without approval is not the default and, if offered at all, is an explicit admin choice out of scope here.
- Company creation, join requests, domain-join policies, company memberships, and onboarding steps already exist in the system; this feature connects and corrects them rather than introducing all-new subsystems.
- A company's matchable domain is inferred from the founder's registered email domain at creation time. Manual admin management of domain policies (and any separate email-based domain-ownership verification) continues to exist but is not required for a match to be offered.
- The set of public/free email provider domains is maintained as a curated denylist; the initial list covers the most common consumer providers and can be extended.
- Existing tenant-isolation and role rules govern what an approved member can access; this feature does not change those rules, only the path to becoming a member.
- Notifications to administrators and requesters reuse the platform's existing notification/email mechanisms.

## Dependencies

- Existing onboarding flow (feature 007) and its company-setup step.
- Existing join-request and domain-join-policy capabilities.
- Existing company membership and tenant-isolation rules (features 024, 031).
