# Feature Specification: UI Color Compliance

**Feature Branch**: `018-ui-color-compliance`

**Created**: 2026-06-20

**Status**: Draft

**Input**: User description: "Adjust front end colors based on constitution"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consistent Visual Identity Across All Pages (Priority: P1)

As a user navigating Tessera, every page and interactive element I encounter uses the same visual language — neutral surfaces feel cohesive, and interactive elements (buttons, links, focus indicators) share a unified accent color — so the product feels intentional and professionally designed rather than assembled from disparate parts.

**Why this priority**: Visual consistency is the primary deliverable. Every page the user can visit is affected; this is the core scope of the feature.

**Independent Test**: Open each application page (login, register, dashboard, documents, search, admin, onboarding steps) and verify that no element uses the old neutral color scale for surfaces or text, and no interactive element uses the old primary accent color.

**Acceptance Scenarios**:

1. **Given** a user visits the login page, **When** they view form inputs, buttons, and labels, **Then** all neutral text and surfaces use the updated neutral color scale, and the primary action button uses the updated accent color with correct hover and focus states.
2. **Given** a user navigates through the onboarding flow, **When** they view each step (progress stepper, company form, invite form, suggestions), **Then** all step indicators, cards, and action buttons reflect the updated design system colors.
3. **Given** a user visits the documents list and detail pages, **When** they view page chrome, cards, and action buttons, **Then** no old accent or neutral color classes appear on interactive or surface elements.
4. **Given** a user visits the search, admin, proposals, and metrics pages, **When** they view the full page layout, **Then** all neutral surfaces and interactive elements use the updated color scales.
5. **Given** a user interacts with the navigation bar or space selector, **When** they hover or focus on interactive elements, **Then** hover and focus ring states match the updated design system.

---

### User Story 2 - Accessible Focus States on All Interactive Elements (Priority: P2)

As a keyboard or assistive-technology user, focus rings on buttons, links, and form controls are clearly visible using the correct accent color, so I can always tell where focus is on the page.

**Why this priority**: Focus state correctness is part of the color migration; incorrect or absent focus rings are both a visual inconsistency and an accessibility regression.

**Independent Test**: Tab through every interactive element on the login and documents pages; verify that focus rings are visible and use the correct accent color shade.

**Acceptance Scenarios**:

1. **Given** a user tabs to a primary button, **When** the button receives focus, **Then** a visible focus ring appears in the correct accent focus color.
2. **Given** a user tabs to a secondary or outline button, **When** the button receives focus, **Then** a visible focus ring appears consistent with the primary accent focus color.
3. **Given** a user tabs to a form input, **When** the input receives focus, **Then** the border or ring highlight uses the correct accent color.

---

### User Story 3 - No Regressions in Semantic Error States (Priority: P3)

As a user encountering a validation error or destructive action, error and warning states remain visually distinct using the existing error color family, so I can still clearly identify problems without confusion.

**Why this priority**: The migration must not touch semantic error colors. This story confirms the scope boundary and prevents regression.

**Independent Test**: Trigger a login failure, a form validation error, and any destructive confirmation — verify that error states remain visually distinct and use the correct error color.

**Acceptance Scenarios**:

1. **Given** a user submits an invalid form, **When** validation fails, **Then** error messages and highlighted fields use the error color, not the primary accent color.
2. **Given** a user performs a destructive action, **When** a confirmation or warning appears, **Then** destructive state colors remain unchanged.

---

### Edge Cases

- What happens on pages that currently mix old neutral and old accent classes in the same component — are all instances caught?
- How does the `AddDocumentModal` (a layered overlay) look with updated colors against the page backdrop?
- Are there any dynamically generated class names (string concatenation) that bypass a static search?
- Does the `globals.css` define any CSS custom properties or raw hex values that also need updating?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every page and component in the web application MUST use the updated neutral color scale for all surfaces, borders, and text (neutral elements MUST NOT use the old neutral scale).
- **FR-002**: All primary interactive elements (buttons, links, active navigation items) MUST use the primary accent color for default state.
- **FR-003**: All primary interactive elements MUST use the primary accent hover color on hover.
- **FR-004**: All interactive elements MUST use the primary accent focus color for focus ring states.
- **FR-005**: Semantic error and destructive states MUST continue to use the error color family; no error element MUST be changed to a neutral or accent color.
- **FR-006**: Secondary and outline interactive elements (bordered buttons, muted links) MUST use the updated neutral color scale for borders and text, NOT the old accent or neutral variants.
- **FR-007**: The navigation bar, space selector, and all shared layout components MUST comply with FR-001 through FR-004.
- **FR-008**: No new instances of the old neutral scale or old accent color family MAY be introduced; the migration MUST be complete across all currently affected files.
- **FR-009**: All changes MUST be purely visual; no behavior, routing, data handling, or accessibility semantics MUST change as part of this feature.

### Key Entities

- **Color Scale – Neutral**: The scale used for all surfaces, borders, background tints, and body/muted text throughout the UI.
- **Color Scale – Primary Accent**: The scale used for primary interactive elements; has distinct shades for default, hover, and focus states.
- **Color Scale – Error/Destructive**: The scale used for error messages, validation states, and destructive action indicators; scope-excluded from this migration.
- **Affected Components**: The set of 23 page and component files currently using non-compliant color classes across all application areas (login, register, onboarding, documents, search, admin, proposals, metrics, navigation, modals).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero occurrences of the old accent color classes remain in any page or component file after the migration.
- **SC-002**: Zero occurrences of the old neutral color classes remain in any page or component file after the migration.
- **SC-003**: All 23 currently affected files are updated; no file is partially migrated.
- **SC-004**: All existing automated UI tests pass without modification to test assertions (visual change only, no behavioral regression).
- **SC-005**: A visual walkthrough of all application pages (login, register, onboarding, documents, search, admin, proposals, metrics) shows a consistent accent and neutral palette with no visible remnants of the old color scheme.
- **SC-006**: Focus states are visible and consistent across all interactive elements on every page.

## Assumptions

- The scope of this feature is the `apps/web` Next.js application only; no mobile app, email templates, or other front-end surfaces are in scope.
- The existing error/destructive color family is already compliant and MUST NOT be changed.
- CSS custom properties or hardcoded hex values in `globals.css` that map to old neutral or accent colors fall within scope if they produce the same non-compliant visual output.
- Dynamically constructed class names (e.g., via string interpolation) are out of scope for this ticket unless they are discovered and straightforward to fix statically.
- No new UI components or pages are added as part of this feature; scope is strictly migration of existing elements.
- The Geist Sans / Geist Mono typography stack is already loaded in the layout; typography loading is out of scope unless a gap is discovered during migration.
- All 23 identified component/page files constitute the full set of affected files; if additional files are discovered during implementation, they are included in scope.
