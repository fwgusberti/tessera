# Feature Specification: User Badge

**Feature Branch**: `057-user-badge`

**Created**: 2026-07-07

**Status**: Draft

**Input**: User description: "create a user badge so I'm able to identify in which user I'm logged in"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See who I am signed in as (Priority: P1)

A signed-in person can, at any time and from any page of the application, glance
at a persistent badge that clearly shows which account they are currently using.
The badge shows an identifying label for the account (their email address, and a
name if one is available) so they can confirm their identity without navigating
away or opening a separate page.

**Why this priority**: This is the entire point of the feature. Without a visible
identity indicator, a person cannot confirm which account is active — especially
important when multiple people share a device or someone maintains more than one
account. It is the smallest change that delivers the requested value on its own.

**Independent Test**: Sign in as a known account and confirm the badge displays
that account's identifying label on every authenticated page. Sign out and
confirm the badge disappears.

**Acceptance Scenarios**:

1. **Given** I am signed in, **When** I look at the application navigation, **Then**
   I see a badge showing my account's identifying label (email, plus name if
   available).
2. **Given** I am signed in and navigate between different pages, **When** each page
   loads, **Then** the badge remains visible and shows the same account.
3. **Given** I am not signed in, **When** I view the application, **Then** no user
   badge is shown.
4. **Given** I sign out, **When** the sign-out completes, **Then** the badge is
   removed from view.

---

### User Story 2 - Distinguish accounts at a glance (Priority: P2)

When a person has more than one account, or when two people use the same browser
in turn, the badge lets them tell the accounts apart quickly — for example a
short visual marker (such as initials) alongside the identifying label — so they
notice immediately if they are signed in as the wrong account.

**Why this priority**: Adds meaningful value for the multi-account and
shared-device cases the request implies ("identify in which user I'm logged in"),
but the core identification need is already met by Story 1, so this is secondary.

**Independent Test**: Sign in as account A, note the badge's visual marker and
label; sign out and sign in as account B; confirm the badge visibly changes to
reflect account B.

**Acceptance Scenarios**:

1. **Given** I am signed in as account A, **When** I view the badge, **Then** it
   shows a visual marker derived from my identity (e.g., initials).
2. **Given** I sign out of account A and sign in as account B, **When** the badge
   updates, **Then** its label and visual marker reflect account B, not account A.

---

### Edge Cases

- **Long identifier**: When the identifying label is long (e.g., a lengthy email
  address), the badge truncates gracefully without breaking the surrounding
  layout, and the full value remains discoverable (e.g., on hover or in an
  expanded view).
- **Missing name**: When only an email is known and no display name is available,
  the badge falls back to showing the email (and derives any visual marker from
  the email).
- **Small screens**: On narrow/mobile layouts the badge remains present and
  legible, adapting to the compact navigation rather than being hidden entirely.
- **Session expiry**: When the session ends or is no longer valid, the badge is
  removed in step with the person being treated as signed out.
- **Identity temporarily unavailable**: If identity details cannot be resolved at
  the moment of display, the badge does not show a misleading or blank identity;
  it shows a neutral placeholder or is omitted until identity is known.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST display a user badge to any signed-in person that
  identifies the currently active account.
- **FR-002**: The badge MUST show the account's email address as the primary
  identifying label, and MUST additionally show a display name when one is
  available.
- **FR-003**: The badge MUST be visible and consistent across all authenticated
  areas of the application (persistent placement in the primary navigation).
- **FR-004**: The system MUST NOT display the badge when no one is signed in.
- **FR-005**: The badge MUST update to reflect the currently signed-in account
  whenever the active account changes (sign in, sign out, or switch of account).
- **FR-006**: The badge MUST derive its contents only from the currently
  authenticated session's own identity and MUST NOT expose any other account's
  identity.
- **FR-007**: The badge MUST present a short visual marker (e.g., initials)
  derived from the active account's identity to aid at-a-glance recognition.
- **FR-008**: The badge MUST handle overly long identifiers by truncating within
  its allotted space while keeping the full value discoverable.
- **FR-009**: The badge MUST remain legible and available on small/mobile
  viewports.

### Key Entities *(include if feature involves data)*

- **Signed-in account identity**: The identity of the person currently
  authenticated, as already established by the existing authentication session.
  Relevant attributes for display are the email address, an optional display
  name, and a derived visual marker (initials). No new stored data is introduced;
  the badge reflects identity already available for the active session.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On every authenticated page, a signed-in person can identify which
  account is active in under 3 seconds without navigating away or opening another
  screen.
- **SC-002**: 100% of authenticated pages display the badge with the correct
  active account.
- **SC-003**: After switching accounts (sign out then sign in as a different
  account), the badge reflects the new account on the next authenticated view
  100% of the time.
- **SC-004**: The badge never shows another account's identity — 0% cross-account
  leakage in identification tests.
- **SC-005**: The badge remains visible and legible on both desktop and mobile
  viewport widths.

## Assumptions

- The application already establishes an authenticated session and can determine
  the active account's identity (at minimum the email address); the badge
  consumes this existing identity rather than introducing new authentication.
- A display name may not always be available; email is the guaranteed
  identifying label and the default fallback.
- The badge's home is the existing primary navigation, alongside the existing
  account and sign-out controls, so it is present on every authenticated page.
- The feature is a display/identification aid. Making the badge an interactive
  entry point (e.g., a menu that consolidates account and sign-out actions) is a
  reasonable future enhancement but is out of scope for this feature unless the
  minimal effort to reuse existing controls makes it trivial.
- Visual styling follows the project's existing design system; no new visual
  language is introduced.
