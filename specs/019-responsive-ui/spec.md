# Feature Specification: Responsive UI for Smartphones

**Feature Branch**: `019-responsive-ui`

**Created**: 2026-06-20

**Status**: Draft

**Input**: User description: "make ui responsive and suitable for smartphones"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse and Read Documents on Mobile (Priority: P1)

A user opens the Tessera app on their smartphone and can navigate to the documents list, read document content, and search for documents without layout breaking or content being cut off.

**Why this priority**: Reading and searching documents is the primary value of Tessera. If this core flow is broken on mobile, the product is effectively unusable on smartphones — the most common personal device.

**Independent Test**: Open the app on a 390px-wide viewport, navigate to Documents, open a document, and verify all content is readable and interactive without horizontal scrolling.

**Acceptance Scenarios**:

1. **Given** a user on a smartphone opens the documents list, **When** they scroll the list, **Then** all document cards are fully visible within the screen width with no horizontal overflow.
2. **Given** a user taps a document, **When** the detail page loads, **Then** the document title, metadata, and content body all render within the screen without clipping.
3. **Given** a user opens the search page, **When** they type a query, **Then** results display in a single-column layout fully contained within the viewport.

---

### User Story 2 - Navigate the App on Mobile (Priority: P1)

A user on a smartphone can access all main sections of the app (Documents, Search, Proposals, Metrics) through a navigation element that is accessible with one thumb and does not obstruct content.

**Why this priority**: Navigation is the skeleton of the app. A desktop-only nav bar forces mobile users to zoom, scroll horizontally, or lose access to entire sections — making the product non-functional on smartphones.

**Independent Test**: On a 390px viewport, tap through all nav items and confirm each destination page loads correctly and the nav remains accessible on all pages.

**Acceptance Scenarios**:

1. **Given** a user on a smartphone views any page, **When** they look for navigation, **Then** a touch-friendly mobile navigation (hamburger menu or bottom bar) is visible and usable with a finger tap.
2. **Given** the mobile nav is open, **When** the user selects a section, **Then** the nav closes and the target page loads with no layout overflow.
3. **Given** a user on a desktop browser, **When** they resize the window below 768px, **Then** the desktop nav collapses into the mobile navigation without visual artifacts.

---

### User Story 3 - Complete Onboarding on Mobile (Priority: P2)

A new user on a smartphone can go through the full onboarding flow (profile, company, invite, complete) entering their information comfortably using the device's native keyboard and touch controls.

**Why this priority**: Onboarding is a one-time but critical funnel. If mobile users cannot complete it, they are permanently excluded from the product.

**Independent Test**: On a 390px viewport, complete all onboarding steps end-to-end and confirm every form, button, and step indicator is usable without zooming or horizontal scrolling.

**Acceptance Scenarios**:

1. **Given** a new user starts onboarding on a smartphone, **When** the keyboard appears, **Then** form fields remain visible above the keyboard and the user can submit without scrolling excessively.
2. **Given** a user is on any onboarding step, **When** they view the progress stepper, **Then** the stepper is legible and does not overflow horizontally.
3. **Given** a user taps "Continue" or "Submit" on any onboarding form, **Then** the button is large enough to tap accurately (minimum 44×44 pt touch target) and positioned where it is not obscured.

---

### User Story 4 - Log In and Register on Mobile (Priority: P2)

A user on a smartphone can log in or create an account using the login and register pages with form fields and buttons that are appropriately sized for touch input.

**Why this priority**: Authentication gates all value. A broken login experience on mobile prevents access entirely.

**Independent Test**: On a 390px viewport, complete a login and registration flow and confirm all fields and actions are operable without zooming.

**Acceptance Scenarios**:

1. **Given** a user opens the login page on a smartphone, **When** they tap email and password fields, **Then** the fields expand to full available width and the keyboard does not push the submit button off screen.
2. **Given** a user submits the login form, **When** an error occurs, **Then** the error message is visible within the viewport without scrolling.

---

### Edge Cases

- What happens on very small screens (320px width, e.g., older iPhones)?
- How does the layout behave in landscape orientation on smartphones?
- What happens when the device font size is increased via accessibility settings?
- How does the Space Selector component behave on a narrow viewport — does it overflow or truncate gracefully?
- What happens when long document titles or company names are displayed on narrow screens?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The navigation bar MUST adapt to viewport width: on screens narrower than 768px it MUST collapse into a touch-friendly mobile navigation pattern (hamburger menu or equivalent) that is dismissible.
- **FR-002**: All pages MUST render without horizontal scroll on viewport widths from 320px to 767px (smartphone range).
- **FR-003**: All interactive controls (buttons, links, form fields) MUST have a minimum touch target size of 44×44 points on mobile viewports.
- **FR-004**: Form pages (login, register, onboarding steps) MUST keep the primary action button visible and reachable when the device keyboard is active.
- **FR-005**: Document list and detail pages MUST reflow to single-column layouts on smartphone viewports, ensuring text is readable at a minimum 16px equivalent font size without user zooming.
- **FR-006**: The Space Selector component MUST NOT overflow its container on narrow viewports; it MUST truncate or wrap long space names gracefully.
- **FR-007**: The onboarding progress stepper MUST adapt its layout to narrow viewports, either compressing or converting to a simplified step indicator.
- **FR-008**: Modal dialogs (e.g., Add Document modal) MUST be fully visible and scrollable within the viewport on smartphones without content being cut off by the screen edges.
- **FR-009**: The responsive layout MUST NOT alter any visual design tokens (color palette, typography) defined in the UI Design System; only layout and spacing may change.
- **FR-010**: The desktop layout (viewport ≥ 768px) MUST remain unchanged by this feature — no desktop regressions.

### Key Entities

- **Viewport Breakpoints**: The boundary between mobile and desktop layouts. The established breakpoint is 768px (md in Tailwind).
- **Touch Target**: An interactive element's tappable area; must meet 44×44pt minimum for accessibility and usability on smartphones.
- **Navigation Component**: The top-level NavBar and SpaceSelector that currently serve as the primary wayfinding for the app.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All app pages (login, register, onboarding steps, documents list, document detail, search, proposals, metrics, admin) render without horizontal overflow on a 390px-wide viewport (iPhone 15 equivalent).
- **SC-002**: A user can complete the full critical path — log in → find a document → read it — on a smartphone without zooming or horizontal scrolling.
- **SC-003**: All interactive controls pass a touch-target audit with no element below 44×44pt on mobile viewports.
- **SC-004**: The desktop layout (≥ 768px) passes a visual regression check showing no unintended changes from this feature.
- **SC-005**: The onboarding flow can be completed end-to-end on a 390px viewport with the device keyboard visible.

## Assumptions

- The target smartphone viewport range is 320px–767px width; tablet (768px–1023px) and desktop (≥ 1024px) layouts are out of scope for this feature beyond preserving existing desktop behavior.
- Tailwind CSS breakpoints already in the project (`sm`, `md`, `lg`) will be used as the responsive utility layer; no additional CSS framework is introduced.
- The existing color palette, typography, and spacing tokens defined in the UI Design System constitution (v1.3.0) remain authoritative — responsive work only adjusts layout classes.
- Landscape smartphone orientation is a best-effort target; portrait is the primary orientation to support.
- Native app wrapping (PWA manifest, App Store packaging) is out of scope.
- Accessibility standards (WCAG 2.1 AA touch targets and text sizing) are treated as a floor, not a ceiling, for the mobile layout.
