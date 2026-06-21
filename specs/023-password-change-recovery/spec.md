# Feature Specification: Password Change and Recovery Flow

**Feature Branch**: `023-password-change-recovery`

**Created**: 2026-06-21

**Status**: Draft

**Input**: User description: "create password change and recovery flow"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Change Password While Logged In (Priority: P1)

An authenticated user wants to update their password from within the application. They navigate to their account settings, provide their current password for verification, enter a new password, confirm it, and submit. The system validates the request and updates their credentials. Other active sessions are invalidated; the current session remains valid.

**Why this priority**: Password change is the most common credential-management action and is a security-critical baseline. It does not depend on any external service (no email required) and can be delivered independently as a complete, secure feature.

**Independent Test**: Can be fully tested by logging in with valid credentials, navigating to account settings, changing the password, logging out, and verifying login succeeds only with the new password.

**Acceptance Scenarios**:

1. **Given** a logged-in user is on the account settings page, **When** they enter their correct current password and a valid new password (entered twice, matching), **Then** the password is updated and a confirmation message is displayed.
2. **Given** a logged-in user submits a password change, **When** the current password they entered is incorrect, **Then** the system rejects the request with a clear error and does not change the password.
3. **Given** a logged-in user submits a password change, **When** the new password and its confirmation do not match, **Then** the system rejects the request with a clear inline error before submitting to the server.
4. **Given** a password change succeeds, **When** the user's other active sessions exist, **Then** those sessions are invalidated and require re-authentication.
5. **Given** a password change succeeds, **When** the event is recorded, **Then** the audit log captures the actor, timestamp, and the nature of the change.

---

### User Story 2 - Request a Password Reset by Email (Priority: P2)

A user who cannot access their account because they have forgotten their password initiates a self-service recovery. From the login page they provide their registered email address and request a reset link. The system sends an email containing a time-limited, single-use link. The system's response to the request is always the same message, regardless of whether the email is registered, to prevent revealing account existence.

**Why this priority**: Password recovery is essential for user retention and reduces reliance on support. It requires email delivery infrastructure, making it slightly more complex than a password change, but delivers critical standalone value: the reset link can be issued and validated independently of the actual password update step.

**Independent Test**: Can be tested independently by submitting a reset request for a registered email address and verifying that a reset email is received within 60 seconds. The "don't reveal email existence" behaviour can be tested by submitting with an unregistered address and confirming the displayed message is identical.

**Acceptance Scenarios**:

1. **Given** an unauthenticated user is on the password recovery page, **When** they submit a valid email address, **Then** the system displays a neutral confirmation message regardless of whether that email is registered.
2. **Given** a registered email address is submitted, **When** the recovery request is processed, **Then** the user receives an email containing a single-use reset link that expires within 1 hour.
3. **Given** a reset link has been issued, **When** the user requests another reset for the same email, **Then** only the most recently issued link is valid; all previous links for that email are invalidated.
4. **Given** the reset request page is used repeatedly in a short period, **When** a threshold of requests from the same source is exceeded, **Then** further requests are silently accepted (to avoid enumeration) but no additional emails are sent until the rate-limit window passes.

---

### User Story 3 - Use Reset Link to Set a New Password (Priority: P3)

A user clicks the reset link from their email and arrives at a page where they can set a new password. They enter and confirm the new password. On success, the password is updated, the reset link is consumed, all other sessions are invalidated, and the user is redirected to the login page.

**Why this priority**: This story completes the recovery flow and depends on US2 (the reset link must exist). It is independently testable once a valid reset token exists.

**Independent Test**: Can be tested by directly loading a valid reset URL, submitting a new password, and verifying that login succeeds with the new credentials and that the same reset link cannot be used a second time.

**Acceptance Scenarios**:

1. **Given** a user opens a valid, unexpired reset link, **When** they enter a new password and matching confirmation, **Then** the password is updated, the reset token is consumed, and they are redirected to the login page.
2. **Given** a user opens a reset link that has expired, **When** the page loads, **Then** a clear message explains that the link has expired and offers a way to request a new one.
3. **Given** a user attempts to reuse a reset link that has already been consumed, **When** they load the URL, **Then** the system treats it identically to an expired link and presents the same actionable error.
4. **Given** a password reset succeeds, **When** the event is recorded, **Then** the audit log captures the timestamp and the fact that a self-service reset occurred.

---

### Edge Cases

- What happens when the user submits a new password that does not meet the minimum strength requirement?
- How is the user notified if a password change or reset was initiated from an unfamiliar location (out of scope for v1 — assumption noted)?
- What happens if the user clicks the reset link in one browser tab and then tries to use the same link in another?
- What if the user's email address changed since the reset link was issued (not applicable — email is the user identifier in this system)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Authenticated users MUST be able to initiate a password change from their account settings.
- **FR-002**: The system MUST verify the user's current password before accepting a new one during a password change.
- **FR-003**: The system MUST require the new password to be entered twice and confirm both entries match before accepting the change.
- **FR-004**: The system MUST enforce minimum password strength (at minimum: 8 characters; no trivially weak patterns such as "password" or sequences).
- **FR-005**: Unauthenticated users MUST be able to request a password reset using their registered email address.
- **FR-006**: The system MUST send a time-limited reset link to the registered email address upon a valid recovery request.
- **FR-007**: Reset links MUST be single-use and expire after no more than 1 hour from issuance.
- **FR-008**: If multiple reset links are issued for the same account, only the most recently issued link MUST be valid; all prior links MUST be invalidated.
- **FR-009**: The system's response to a recovery request MUST be identical whether or not the supplied email address is registered (no user enumeration).
- **FR-010**: A successful password change or reset MUST invalidate all other active sessions for that user.
- **FR-011**: Every password change and reset event MUST be recorded in the audit log with the actor identity, timestamp, and event type.
- **FR-012**: Rate limiting MUST be applied to recovery request submissions to prevent abuse; excess requests MUST be silently accepted to prevent enumeration.

### Key Entities

- **PasswordResetToken**: A short-lived, single-use credential tied to a specific user account. Key attributes: the token value (opaque, unguessable), the user it belongs to, the expiry time, and whether it has been consumed.
- **UserCredential**: The stored authentication secret for a user account (hashed and salted). Key relationship: belongs to a user; a change event supersedes the prior credential.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A logged-in user can complete a password change in under 2 minutes from the moment they open the account settings page.
- **SC-002**: A password reset email arrives in the user's inbox within 60 seconds of a valid recovery request under normal conditions.
- **SC-003**: 100% of expired, consumed, or malformed reset links display a clear, actionable error message rather than a generic failure.
- **SC-004**: 100% of password change and reset events appear in the audit log within the same request that triggered them.
- **SC-005**: The response time and response body for a recovery request with a registered email and one with an unregistered email are indistinguishable to a client.
- **SC-006**: No active session persists after a password change or reset — re-authentication is required within the same session window.

## Assumptions

- The platform already has a working user authentication system with email-based accounts (JWT-based, per the existing constitution).
- A transactional email delivery mechanism is available and can be used without additional infrastructure procurement.
- Password strength validation applies the same rules for both change and reset flows.
- "Other active sessions" means all sessions other than the one performing the change; the current session remains valid after a self-service change to avoid immediately logging the user out.
- Notifying the user via email when a password change or reset occurs (security alert email) is desirable but out of scope for v1.
- Admin-initiated forced password resets are out of scope; this feature covers only self-service flows.
- The minimum password strength rule (FR-004) is enforced consistently on both the client side (immediate feedback) and the server side (authoritative check).
