# Feature Specification: New User Registration

**Feature Branch**: `006-user-registration`

**Created**: 2026-06-15

**Status**: Draft

**Input**: User description: "Crie o cadastro de usuário novo no front"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete Registration Flow (Priority: P1)

A new visitor arrives at the Tessera web application and wants to create an account. They navigate to the registration page, fill in their name, email address, and a password, and submit the form. Upon success, they are automatically redirected to the main application dashboard.

**Why this priority**: This is the core user acquisition flow. Without a working registration form, no new users can join the platform without manual admin intervention.

**Independent Test**: Can be fully tested by visiting the `/register` page, filling in valid credentials, submitting, and verifying the user is redirected and logged in — delivering a complete self-service onboarding experience.

**Acceptance Scenarios**:

1. **Given** a visitor on the registration page (with no `?redirect=` parameter), **When** they fill in a valid name, email, and password (min 8 characters) and submit, **Then** their account is created and they are redirected to the home page as an authenticated user.
1a. **Given** a visitor on the registration page with a `?redirect=/documents` query parameter, **When** they complete registration successfully, **Then** they are redirected to `/documents` (not the home page).
2. **Given** a visitor on the registration page, **When** they submit the form with any required field empty, **Then** they see inline field-level error messages indicating which fields are missing, and the form is not submitted.
3. **Given** a visitor on the registration page, **When** they submit with a password shorter than 8 characters, **Then** they see an error message stating the minimum password length requirement.

---

### User Story 2 - Duplicate Email Handling (Priority: P2)

A user tries to register with an email address that already belongs to an existing account. The system informs them clearly that the email is taken and suggests they sign in instead.

**Why this priority**: This is a critical error path. Without clear feedback, users may not realize they already have an account and become confused or locked out.

**Independent Test**: Can be tested independently by attempting to register with an existing email and verifying the error message and sign-in link appear.

**Acceptance Scenarios**:

1. **Given** a visitor submitting the registration form with an already-registered email, **When** the server responds with a conflict error, **Then** the user sees a message explaining the email is already in use and a link to the sign-in page is displayed.

---

### User Story 3 - Navigation from Login Page (Priority: P3)

A visitor who arrives at the login page realizes they don't have an account yet. They see a link to the registration page and navigate to it without having to search.

**Why this priority**: Discoverability of the registration flow matters for conversion; users should not be stranded on the login page.

**Independent Test**: Can be tested by visiting `/login` and verifying that a "Create an account" link is present and leads to `/register`.

**Acceptance Scenarios**:

1. **Given** a visitor on the login page, **When** they look for an option to create a new account, **Then** they see a link that takes them to the registration page.
2. **Given** a visitor on the registration page, **When** they already have an account, **Then** they see a link back to the login page.

---

### Edge Cases

- What happens when the user submits the form and the network request fails or the server is unreachable? The user should see a generic error message and the form should remain editable so they can retry.
- What happens when an already-authenticated user navigates to `/register`? They should be redirected to the home page automatically.
- What happens when the display name contains only whitespace? The form should treat it as empty and show a validation error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a registration page accessible at `/register`.
- **FR-002**: The registration form MUST collect three fields: display name, email address, and password.
- **FR-003**: System MUST validate all fields client-side before submission: display name is non-empty (after trimming) and at most 100 characters, email is well-formed, password is at least 8 characters. The form MUST also display a non-blocking password strength indicator (e.g., weak / medium / strong) that updates as the user types; this indicator is informational only and does not prevent submission if the minimum length is met.
- **FR-004**: System MUST display inline, field-level error messages when validation fails, clearly identifying which field has the issue.
- **FR-005**: System MUST call the backend registration endpoint upon form submission with the user's credentials.
- **FR-006**: Upon successful registration, the system MUST automatically authenticate the user and redirect them to the destination specified by the `?redirect=` query parameter (if present and safe), or to the home page (`/`) otherwise. Redirect safety rules match those of the login page (must start with `/` and not start with `//`).
- **FR-007**: If the backend returns a "email already registered" error, the system MUST display a clear message to the user and provide a link to the sign-in page.
- **FR-008**: If the backend returns any other error, the system MUST display a generic failure message and allow the user to retry.
- **FR-009**: The registration page MUST redirect already-authenticated users to the home page (ignoring any `?redirect=` param for security).
- **FR-010**: The login page MUST include a visible link to the registration page.
- **FR-011**: The registration page MUST include a visible link back to the login page.
- **FR-012**: Form submission controls MUST be disabled while the request is in flight to prevent duplicate submissions.

### Key Entities *(include if feature involves data)*

- **User**: Represents a person with an account. Key attributes: display name, email address, password (stored as a hash, never in plain text). Created during registration; the backend issues a JWT on success.
- **Registration Form**: The UI artifact collecting the user's display name, email, and password before submission.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new visitor can complete the registration process — from landing on the page to being authenticated — in under 2 minutes.
- **SC-002**: 100% of attempted registrations with invalid or missing fields are rejected client-side before reaching the server.
- **SC-003**: Duplicate-email errors surface a human-readable message and a sign-in link within 1 second of the server response.
- **SC-004**: Zero successful form re-submissions occur while a registration request is in flight (no duplicate accounts created from double-clicks).
- **SC-005**: Authenticated users are redirected away from the registration page in under 500 milliseconds.

## Clarifications

### Session 2026-06-15

- Q: Should the registration page respect a `?redirect=` query parameter (like the login page) to send users to their originally intended page after registration? → A: Yes — respect `?redirect=` with the same safety rules as the login page; fall back to `/` if absent or unsafe.
- Q: Should the registration form show any additional password guidance or strength indicator beyond the 8-character minimum? → A: Yes — show a non-blocking password strength meter (weak/medium/strong) as an informational hint; minimum-length is still the only hard validation rule.
- Q: Should the frontend enforce the backend's 100-character maximum for the display name? → A: Yes — validate client-side and show an inline error if the display name exceeds 100 characters.

## Assumptions

- The backend `POST /v1/auth/register` endpoint is already implemented and returns a user object on success. A login call will be issued immediately after successful registration to obtain the JWT session (the register endpoint does not return tokens directly).
- After successful registration, the system will call the existing login flow automatically so the user is authenticated without a second manual sign-in step.
- Password confirmation (re-type) field is out of scope for this version — a single password field with a minimum-length requirement is sufficient.
- Email verification (confirmation email) is out of scope for this version — users are immediately active after registration.
- Mobile responsiveness follows the same conventions already established by the login page.
- No CAPTCHA or bot-prevention mechanism is required for this version.
