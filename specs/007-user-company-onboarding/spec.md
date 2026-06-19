# Feature Specification: User & Company Onboarding Flow

**Feature Branch**: `007-user-company-onboarding`

**Created**: 2026-06-15

**Status**: Draft

**Input**: User description: "Create a modern and perfect user/company onboarding flow"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Personal Profile Setup (Priority: P1)

After completing registration, a newly registered user is guided through a structured onboarding wizard starting with completing their personal profile. The user provides their full name and professional role/title so teammates can identify them correctly within the platform.

**Why this priority**: Without a personal profile, users are anonymous inside the platform — this is the minimum viable step before any collaboration can occur.

**Independent Test**: Can be fully tested by registering a new account, completing only the personal profile step, and verifying the user is identified by name throughout the app.

**Acceptance Scenarios**:

1. **Given** a newly registered user logs in for the first time, **When** they are redirected to the onboarding flow, **Then** the first step asks for their full name and role/title with a visible progress indicator showing where they are in the overall flow.
2. **Given** the user enters their full name and role/title, **When** they proceed, **Then** the information is saved and reflected in their profile immediately.
3. **Given** the user leaves the full name field blank, **When** they attempt to proceed, **Then** they are prompted that full name is required before continuing.
4. **Given** a user who has already completed onboarding logs in, **When** they reach the home screen, **Then** the onboarding wizard is NOT shown again.

---

### User Story 2 - Company Setup (Priority: P2)

After completing their personal profile, the user sets up (or joins) a company/organization. They provide essential company details that contextualize all subsequent activity on the platform.

**Why this priority**: Tessera is a team platform — most value is delivered in the context of an organization. Establishing the company is the structural prerequisite for inviting teammates and using team features.

**Independent Test**: Can be fully tested by completing personal profile and company creation steps, then verifying the user is associated with the new company and can see it in their workspace.

**Acceptance Scenarios**:

1. **Given** the user has completed their personal profile step, **When** they proceed, **Then** they see a company setup step with fields for company name, industry, and team size.
2. **Given** the user fills in company name (required) and optional fields, **When** they submit, **Then** a new company record is created and the user is set as its administrator.
3. **Given** the user leaves the company name field blank, **When** they attempt to proceed, **Then** they are prompted that company name is required.
4. **Given** the user has been invited to an existing company via email invitation, **When** they register and reach the company step, **Then** they see an option to accept the pending invitation instead of creating a new company.
5. **Given** the user's email domain matches the domain of one or more existing companies, **When** they reach the company step, **Then** they are shown those companies as suggested organizations to join, with a "Request to Join" or auto-join action depending on the company's domain-join policy.
6. **Given** the user's email domain matches an existing company AND they also have a pending invitation to that same company, **When** they reach the company step, **Then** the invitation is surfaced first (taking priority over the domain suggestion) and joining via invitation does not require additional approval.
7. **Given** the user has neither a pending invitation nor a matching domain, **When** they reach the company step, **Then** only the "Create a new company" option is presented.

---

### User Story 3 - Team Invitation (Priority: P3)

After *creating* a new company, the user is offered the opportunity to bring their team on board by sending email invitations to colleagues. This step is shown **only to company creators** and is optional — joiners (users who accepted an invitation or joined via domain match) skip directly to User Story 4.

**Why this priority**: Sending invitations during onboarding dramatically improves time-to-collaboration for new company founders; however, users can always invite people later, making this step skippable without blocking progress.

**Independent Test**: Can be fully tested by completing the first two steps as a company *creator*, entering one or more email addresses, sending invitations, and verifying recipients receive an invitation email.

**Acceptance Scenarios**:

1. **Given** the user has completed the company setup step, **When** they reach the invitation step, **Then** they see a field to enter one or more email addresses and a "Skip for now" option.
2. **Given** the user enters valid email addresses and clicks "Send Invitations," **When** invitations are dispatched, **Then** each email address receives an invitation email and the user sees a confirmation.
3. **Given** the user enters an invalid email address, **When** they attempt to send, **Then** they see an inline validation message and no invitation is sent.
4. **Given** the user clicks "Skip for now," **When** they proceed, **Then** the invitation step is bypassed and onboarding continues without any invitations being sent.

---

### User Story 4 - Onboarding Completion (Priority: P3)

After finishing all required steps, the user lands on a completion screen. **Company creators** see a summary of their profile, company, and invitations sent. **Company joiners** (invite or domain match) see a personalized "Welcome to [Company Name]" screen instead. Both paths redirect to the main dashboard.

**Why this priority**: A clear finish line improves user confidence and reduces drop-off; the completion screen also serves as a natural entry point to product discovery.

**Independent Test**: Can be fully tested by completing all previous steps and verifying the completion screen appears with an accurate summary and a working "Go to Dashboard" action.

**Acceptance Scenarios**:

1. **Given** the user completes the last required onboarding step, **When** they are redirected, **Then** they see a completion screen summarizing their profile name, company name, and number of invitations sent.
2. **Given** the user clicks "Go to Dashboard," **When** they are redirected, **Then** they land on the main application dashboard with their profile and company context already applied.
3. **Given** the user refreshes on the completion screen, **When** they reload, **Then** they remain on the completion screen until they explicitly navigate away.

---

### Edge Cases

- What happens when a user closes the browser mid-onboarding and returns later? The system must resume from the last completed step.
- What happens when an invitation email bounces or fails to deliver? The system must surface a non-blocking error and allow the user to continue.
- What happens if a user uses the browser back button during onboarding? They should be able to revisit and edit prior steps without losing data.
- What happens if a company name is already taken? The system must inform the user and let them choose a different name.
- What happens if the user's session expires mid-onboarding? After re-authentication, they are returned to the step they were on.
- What happens if the domain verification email is never received or the link expires? The administrator can re-request a new verification email; the domain remains inactive until verified.
- What happens if a company attempts to claim a domain already verified by another company? The claim is rejected immediately with a clear message; the requesting company cannot use domain matching for that domain.
- What happens if a company administrator never acts on a join request? The user remains on the holding screen indefinitely; no automatic approval or expiry is defined in this version (deferred to post-launch).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST present a multi-step onboarding wizard immediately after a new user's first login, before they can access any other part of the application.
- **FR-002**: System MUST display a persistent progress indicator throughout the onboarding flow, showing completed, current, and upcoming steps.
- **FR-003**: System MUST allow users to set their full name (required) and professional role/title (optional) during the personal profile step.
- **FR-004**: System MUST allow users to create a new company by providing a company name (required), industry (optional), and team size range (optional).
- **FR-005**: System MUST designate the first user to create a company as the company administrator.
- **FR-006**: System MUST allow users to enter one or more colleague email addresses to send team invitations during the invitation step.
- **FR-007**: System MUST validate each email address entered in the invitation step and display an inline error for any invalid format.
- **FR-008**: System MUST allow users to skip the invitation step without sending any invitations.
- **FR-008a**: System MUST only show the invitation step to users who created a new company during onboarding; users who joined an existing company (via invite or domain match) MUST skip the invitation step entirely.
- **FR-009**: System MUST present a completion screen after all required steps are finished: company creators see a summary of their profile, company name, and invitation count; company joiners see a "Welcome to [Company Name]" screen acknowledging their membership.
- **FR-010**: System MUST redirect users to the main dashboard when they dismiss the completion screen.
- **FR-011**: System MUST persist each step's completion state so that interrupted sessions can be resumed from the last completed step.
- **FR-012**: System MUST NOT show the onboarding wizard to users who have already completed it.
- **FR-013**: System MUST send a structured invitation email to each invited colleague with a link to register and join the company. Invitation links MUST expire after 7 days; recipients must be re-invited after expiry.
- **FR-014**: System MUST allow users to navigate back to previously completed steps and edit their answers before finalizing onboarding.
- **FR-015**: System MUST detect whether the registering user's email domain matches the domain of any existing company that has enabled domain-based joining.
- **FR-016**: System MUST present matching companies to the user as suggested organizations to join, with a clear "Join [Company Name]" action.
- **FR-017**: System MUST allow company administrators to enable or disable domain-based joining for their company.
- **FR-018**: When domain-based joining is enabled for a company, System MUST automatically approve users whose email matches that company's domain without requiring manual administrator approval.
- **FR-019**: When domain-based joining is disabled, System MUST allow users with a matching domain to submit a join request that a company administrator must explicitly approve.
- **FR-020**: System MUST prioritize a pending email invitation over a domain match suggestion when both apply to the same company, surfacing the invitation flow first.
- **FR-021**: System MUST allow users to dismiss all join/invitation suggestions and proceed to create a new company instead.
- **FR-022**: System MUST require a company administrator to verify ownership of any email domain before that domain becomes active for user matching; verification is completed by clicking a link sent to an address at that domain (e.g., `verify@acme.com`).
- **FR-025**: System MUST enforce a one-company-per-domain rule: once a domain is verified by a company, any subsequent attempt to claim the same domain by another company MUST be rejected with a clear error message.
- **FR-026**: When a user submits a join request and it is pending administrator approval, System MUST display a holding screen informing the user their request is under review, with no access to any other part of the application.
- **FR-027**: System MUST allow the user to cancel a pending join request from the holding screen, which returns them to the company setup step to choose a different option.
- **FR-028**: System MUST notify the user via email when their join request is approved or denied by a company administrator.
- **FR-029**: System MUST notify the company administrator via email when a new join request is submitted, including the requesting user's name and email.
- **FR-023**: System MUST NOT use an unverified domain for user matching or auto-join suggestions.
- **FR-024**: A domain verification link MUST expire after 24 hours; administrators can re-request a new verification email if the link expires.

### Key Entities

- **OnboardingProgress**: Tracks which steps a user has completed and the current active step; linked to the user account.
- **UserProfile**: Represents a user's identity within the platform — full name, role/title, avatar.
- **Company**: Represents an organization — name, industry, team size, administrator user.
- **Invitation**: A pending invite sent to a colleague's email — includes target email, inviting user, associated company, status (pending/accepted/expired), and expiry timestamp. Invitations expire 7 days after being sent.
- **DomainJoinPolicy**: Configuration attached to a Company that defines whether users with a matching email domain may auto-join (approved automatically) or must request to join (pending administrator approval). Includes the claimed domain, verification status (pending/verified), and policy type (auto-join/request-approval).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: New users complete the full onboarding flow (all required steps) in under 3 minutes on average.
- **SC-002**: At least 80% of newly registered users complete all required onboarding steps without abandoning the flow.
- **SC-003**: Users who encounter an interrupted session can resume onboarding without re-entering previously submitted data.
- **SC-004**: At least 40% of users who reach the invitation step send at least one team invitation during onboarding.
- **SC-005**: Zero users can access the main application without completing required onboarding steps (no bypass paths exist).
- **SC-006**: Onboarding completion screen accurately reflects the user's submitted data 100% of the time.

## Clarifications

### Session 2026-06-15

- Q: How should a company prove it controls a domain before that domain can be used for auto-matching registering users? → A: Email verification — admin receives a confirmation email at a company-domain address (e.g., `verify@acme.com`) and must click a link to activate the domain claim. One-time setup per domain.
- Q: Can multiple companies claim the same email domain? → A: No — one verified company per domain; the first company to successfully verify a domain claim owns it. Subsequent claims on the same domain are rejected.
- Q: What can a user do while their domain join request awaits administrator approval? → A: Wait in a holding screen — user sees a "pending approval" screen with no further app access until an administrator approves or denies; user can cancel the request and restart onboarding.
- Q: Should users who join an existing company (via invite or domain match) see the Team Invitation step? → A: No — only users who create a new company see the invitation step. Users who join an existing company skip the invitation step and land on a "Welcome to [Company]" completion screen instead.
- Q: How long should a team invitation remain valid before expiring? → A: 7 days.

## Assumptions

- Users have already registered via the existing registration flow (specs/006-user-registration) before they reach onboarding.
- Email delivery for invitations relies on an existing or concurrently implemented transactional email service; invitation sending failure does not block onboarding completion.
- Each user belongs to exactly one company at a time; multi-company membership is out of scope for this flow.
- Mobile support (native app) is out of scope; the onboarding flow targets web browsers only.
- Onboarding is required for all new users with no admin-side bypass in this initial version.
- Profile avatar upload is deferred to post-onboarding profile settings and is out of scope for this flow.
- Domain-based joining uses the email domain of the registering user (e.g., `@acme.com`) matched against domains configured on existing companies; sub-domain matching is out of scope.
- Domain join policy (auto-approve vs. request) defaults to "request approval" for all new companies; administrators must explicitly enable auto-approve.
- A pending join request places the user in a holding screen with no further app access until the company administrator approves or denies the request; the user may cancel the request at any time and restart onboarding from the company step.
- Company logo upload is deferred to post-onboarding company settings and is out of scope for this flow.
