# Feature Specification: Fix Create Company Button Network Error

**Feature Branch**: `028-fix-create-company-fetch`

**Created**: 2026-06-21

**Status**: Draft

**Input**: User description: "create company button shows Failed to fetch"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create Company Successfully (Priority: P1)

An authenticated user completes the company creation form and clicks "Create Company." The request reaches the server, the company is created, and the user is redirected or shown a success confirmation. The "Failed to fetch" error no longer appears.

**Why this priority**: This is the core broken flow. Without it, no company can be created, blocking all downstream onboarding.

**Independent Test**: Can be fully tested by filling in a valid company name and submitting the form; the company should be persisted and the user should see a success state instead of an error.

**Acceptance Scenarios**:

1. **Given** an authenticated user is on the company creation page, **When** they fill in required fields and click "Create Company," **Then** the company is created and the user receives a success response (redirect or confirmation message).
2. **Given** an authenticated user is on the company creation page, **When** they click "Create Company," **Then** the "Failed to fetch" error message does NOT appear under any normal network conditions.
3. **Given** the user submits the form, **When** the server processes the request successfully, **Then** the new company is visible in the user's company list.

---

### User Story 2 - Clear Error Feedback on Real Failures (Priority: P2)

When a genuine network or server error occurs (e.g., the server is temporarily unavailable), the user sees a clear, actionable error message — not a raw "Failed to fetch" browser error string.

**Why this priority**: Even after the primary fix, transient errors will occur. Users need human-readable guidance so they can retry or contact support.

**Independent Test**: Can be tested by simulating a server outage; the UI must display a user-friendly message (e.g., "Could not create company. Please try again.") rather than exposing technical error text.

**Acceptance Scenarios**:

1. **Given** a genuine server failure, **When** the user clicks "Create Company," **Then** a user-friendly error message is shown (not a raw fetch/network error).
2. **Given** a user-friendly error is shown, **When** the user retries after the issue is resolved, **Then** the form is still populated and the retry succeeds.

---

### Edge Cases

- What happens when the user submits the form while offline? They should see a friendly offline/connection error, not a browser error string.
- What happens when the server returns a validation error (e.g., company name already taken)? The user should see a field-level error, not a generic fetch failure.
- What happens when the session has expired when the user clicks "Create Company"? The user should be redirected to login, not shown a fetch error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The "Create Company" button MUST successfully submit company data to the backend under normal operating conditions.
- **FR-002**: The system MUST NOT display raw browser network error text (e.g., "Failed to fetch") to the end user.
- **FR-003**: When the company creation request succeeds, the user MUST be shown a success state (redirect or confirmation).
- **FR-004**: When a network or server error occurs, the system MUST display a human-readable, actionable error message.
- **FR-005**: The company creation endpoint MUST be reachable from the frontend using the correct host, port, and path configured for the environment.
- **FR-006**: The system MUST handle expired or missing authentication gracefully (redirect to login) rather than surfacing a network error.

### Key Entities

- **Company**: The organizational entity being created; has at minimum a name and is associated with the creating user.
- **Company Creation Request**: The form payload submitted by the user; must reach the correct API endpoint.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of company creation attempts under normal conditions complete without displaying a "Failed to fetch" or any raw browser error string.
- **SC-002**: Users can create a company end-to-end in under 30 seconds from form submission to confirmation.
- **SC-003**: Any genuine failure state displays a user-readable message within 5 seconds of the error occurring.
- **SC-004**: Zero regression in existing company listing or user onboarding flows after the fix.

## Assumptions

- The "Failed to fetch" error is caused by a misconfiguration (wrong API URL, missing CORS header, or endpoint mismatch) rather than intentional gating.
- The authenticated user already has a valid session when they reach the company creation page.
- The backend endpoint for creating a company exists and is functional when reached at the correct address.
- Mobile support and multi-step onboarding flows are out of scope for this fix; only the create-company submission is being addressed.
