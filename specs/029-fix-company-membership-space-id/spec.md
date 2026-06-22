# Feature Specification: Fix Company Creation 500 Error

**Feature Branch**: `029-fix-company-membership-space-id`

**Created**: 2026-06-21

**Status**: Draft

**Input**: User description: "POST /v1/companies returns 500 due to AttributeError: 'CompanyMembershipModel' object has no attribute 'space_id' in _membership_from_model"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create Company Successfully (Priority: P1)

A user who has registered and logged in wants to create a new company. After submitting the form, the company is created and the user is automatically added as an owner. Currently this always fails with a 500 error.

**Why this priority**: Company creation is a critical onboarding step. Without it, users cannot access any company-scoped functionality in the product.

**Independent Test**: Can be fully tested by sending a POST /v1/companies request as an authenticated user and verifying a 2xx response with the new company data.

**Acceptance Scenarios**:

1. **Given** an authenticated user with no existing company, **When** they submit a valid company name, **Then** the company is created and the user receives a success response containing the new company details.
2. **Given** the company has been created successfully, **When** the system sets up the creator's membership, **Then** the creator is recorded as an owner of the new company with no errors.
3. **Given** the company creation request completes, **When** the response is returned, **Then** the HTTP status code is in the 2xx range and no 500 error occurs.

---

### Edge Cases

- What happens when the company name is empty or exceeds allowed length?
- What happens when the authenticated user already owns the maximum number of allowed companies?
- How does the system handle a database failure mid-creation (company inserted but membership fails)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST successfully create a company when a valid request is submitted by an authenticated user.
- **FR-002**: System MUST automatically assign the requesting user as the owner of the newly created company.
- **FR-003**: System MUST return a structured success response with company details after successful creation.
- **FR-004**: The membership record created for a company MUST use the company-membership data model, not the space-membership data model.
- **FR-005**: System MUST NOT mix company-membership and space-membership data structures when mapping database records to domain objects.

### Key Entities

- **Company**: A named organization entity created by a user; has a unique identifier and name.
- **CompanyMembership**: Records a user's role within a company (e.g., owner); belongs to a company, not a space.
- **SpaceMembership**: Records a user's role within a space; a distinct entity from CompanyMembership and MUST NOT be conflated with it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid company creation requests from authenticated users result in a 2xx response (currently 0%).
- **SC-002**: The system produces no 500 errors due to missing `space_id` attribute on company membership records.
- **SC-003**: A newly created company is immediately accessible to its creator in subsequent API calls.

## Assumptions

- The bug is a regression introduced when the space-membership mapper (`_membership_from_model`) was reused for company memberships after spec 024 (user roles) added space-scoped membership.
- Company membership and space membership are intentionally distinct concepts in the domain model; the fix should preserve that separation rather than merging them.
- No database schema changes are required; the issue is in the application-layer mapping code.
- The fix is scoped to the `add_membership` call in the company creation flow and the related mapping function.
