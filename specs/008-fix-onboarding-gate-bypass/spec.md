# Feature Specification: Fix Onboarding Gate Bypass

**Feature Branch**: `008-fix-onboarding-gate-bypass`

**Created**: 2026-06-18

**Status**: Draft

**Input**: User description: "in onboarding/company i get this error message on front when i click create company {'code': 'onboarding_required', 'message': 'Complete onboarding before accessing this resource.'}"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create Company During Onboarding (Priority: P1)

A user who has just completed the profile step of the onboarding wizard navigates to the company step and submits the "Create Company" form. The company is created successfully and onboarding advances.

**Why this priority**: This is a blocking regression — the core onboarding path (profile → create company) is completely broken. No new user can complete onboarding.

**Independent Test**: Register a fresh user account, complete the profile step, and click "Create Company" on the company step. Verify the company is created and the user advances to the next onboarding step.

**Acceptance Scenarios**:

1. **Given** a user has completed the profile step and has not yet completed onboarding, **When** they submit the company creation form, **Then** the company is created and the user is advanced to the next onboarding step without receiving an `onboarding_required` error.
2. **Given** a user has not completed onboarding, **When** they attempt to access a post-onboarding resource (e.g., documents, spaces), **Then** they still receive the `onboarding_required` error (guard remains active for non-onboarding paths).

---

### User Story 2 - View Company Suggestions During Onboarding (Priority: P1)

A user with a pending invitation or a matching email domain arrives at the company step and the suggestion list loads correctly.

**Why this priority**: Same blocking regression — any user whose company step fetches suggestions before creating/joining will also hit the guard error.

**Independent Test**: Register a user whose email matches a domain policy or who has a pending invitation, navigate to the company step, and verify suggestions appear without error.

**Acceptance Scenarios**:

1. **Given** a user has not completed onboarding, **When** the company step loads and requests company suggestions, **Then** the suggestions are returned successfully (no `onboarding_required` error).

---

### User Story 3 - Join Company During Onboarding (Priority: P1)

A user who accepts an invitation or matches a verified domain can join an existing company from the onboarding company step.

**Why this priority**: Same class of bug — joining a company is the alternative path through the company onboarding step and is equally blocked.

**Independent Test**: Register a user with a pending invitation, navigate to the company step, accept the invitation, and verify the user's membership is created and onboarding advances.

**Acceptance Scenarios**:

1. **Given** a user has not completed onboarding, **When** they submit a join request (via invitation or domain match), **Then** the join is processed successfully and the user advances in the onboarding flow without an `onboarding_required` error.

---

### Edge Cases

- Completing onboarding through one path (create / join via invitation / join via domain) while blocked on another must not be possible — the guard only exempts the specific onboarding-time endpoints, not the whole companies namespace.
- Users who have already completed onboarding must still be gated normally when accessing post-onboarding company management endpoints.
- The holding-screen exemptions (`GET /companies/{id}/join-status` and `DELETE /companies/{id}/join-request`) must remain in place and unaffected.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The following three endpoints MUST be exempt from the `onboarding_required` access gate, because they are called as part of the onboarding wizard before onboarding is complete:
  - Retrieve company suggestions (used at the start of the company step)
  - Create a new company (the primary company-step action for new founders)
  - Join an existing company via invitation or domain match (the alternative company-step action for joiners)
- **FR-002**: All other company management endpoints (e.g., domain policies, join-request administration, invite management) MUST continue to require completed onboarding.
- **FR-003**: The existing holding-screen exemptions (poll join-request status, cancel join request) MUST remain exempt and unaffected by this change.
- **FR-004**: Users who have already completed onboarding MUST continue to be able to access all company endpoints normally.

### Key Entities

- **OnboardingGate**: The server-side rule that enforces completed onboarding before accessing protected resources. Currently missing exemptions for three onboarding-time endpoints.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A newly registered user can navigate from the profile step to the company step, create a company, and advance through onboarding without encountering an error.
- **SC-002**: Zero regression on other guarded endpoints — post-onboarding endpoints still reject unauthenticated or pre-onboarding users with `onboarding_required`.
- **SC-003**: All three onboarding-time company endpoints (suggestions, create, join) succeed for a user mid-onboarding.

## Assumptions

- The bug is isolated to missing exemptions in the onboarding gate; no other part of the onboarding flow is broken.
- The fix does not require schema or migration changes — it is purely a guard configuration change.
- Domain-match and invitation join paths are affected by the same gate failure and must be fixed together with company creation.
