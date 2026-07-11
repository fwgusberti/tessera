# Feature Specification: Admin-Added Members Skip the "Create a Company" Onboarding Trap

**Feature Branch**: `056-fix-added-user-onboarding`

**Created**: 2026-07-06

**Status**: Draft

**Input**: User description: "Eu criei um usuário novo. Eu, loguei com esse usuário, pediu informação do meu nome. Depois já pediu pra eu criar uma companhia nova. Eu não criei a companhia nova. Eu loguei com outro usuário que é admin, e coloquei esse usuário novo na minha companhia, mas eu não consigo usar o usuário novo que apareceu. Sempre que logo com ele mesmo estando numa companhia, ele não consegue ver os documentos e sempre é direcionado para o onboarding e sou obrigado a criar uma companhia."

## Overview

A newly registered person is guided through onboarding: they enter their name, then are asked to create or join a company. If they stop *before* setting up a company, their account is left in an "onboarding not finished" state.

Separately, a company administrator can add an already-registered person directly to their company. When the administrator does this, the added person becomes a real member of that company — but the system still remembers that this person never finished their own onboarding. As a result, every time that person logs in they are pushed back into onboarding, cannot see any of their company's documents, and are told to create a new company — even though they already belong to one.

This traps the person in a loop and, if they comply, produces duplicate/unwanted companies. This feature makes company membership the source of truth: **anyone who already belongs to a company must be let straight into the app, never forced to create or re-do onboarding.**

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin-added member reaches the app instead of the onboarding trap (Priority: P1)

A person registers, enters their name, and stops without setting up a company. Later, an administrator of an existing company adds that person as a member. The next time the person logs in, they land directly in the application with access to that company's content — they are never redirected back into onboarding and are never asked to create a company.

**Why this priority**: This is the exact reported defect. Without it, admin-added members are completely unable to use the product, and the "add a user to my company" capability is effectively broken. It also causes accidental creation of duplicate companies.

**Independent Test**: Register a new person and advance only to the "set up a company" step without completing it. As an administrator of a separate company, add that person as a member. Log in as the added person and confirm they reach the app (and can open the company's documents) without being redirected to onboarding or shown a "create a company" prompt.

**Acceptance Scenarios**:

1. **Given** a registered person who never finished onboarding and has no company, **When** an administrator adds them to a company and the person then logs in, **Then** they are taken into the application and are not redirected to onboarding.
2. **Given** that same person now inside the application, **When** they navigate to documents, **Then** they can see the documents belonging to the company they were added to.
3. **Given** that same person, **When** they log in, **Then** they are never presented with the "create a company" step and are never required to create a company to proceed.

---

### User Story 2 - A member is never asked to create a company (Priority: P2)

Any person who belongs to at least one company is treated as having completed the company-setup part of onboarding. The "create or join a company" step never appears for them again, on this or any future login, regardless of how they came to belong to the company (self-created, approved join request, or added by an admin).

**Why this priority**: Generalizes the fix so it holds for every path into company membership, preventing the same trap from reappearing through a different route. It also removes the risk of an existing member accidentally spinning up a second, empty company.

**Independent Test**: For each way a person can gain membership (created their own company, had a join request approved, was added directly by an admin), confirm that a subsequent login goes straight to the app with no company-creation prompt.

**Acceptance Scenarios**:

1. **Given** a person who is a member of one or more companies, **When** they log in, **Then** onboarding is considered complete and they are not sent to any onboarding step.
2. **Given** a person who was added to a company but had not entered their name during onboarding, **When** they log in, **Then** they are still let into the app and are not blocked on the company-creation step.

---

### User Story 3 - Existing trapped members are recovered (Priority: P3)

People who were already added to a company before this change — and are currently stuck in the onboarding loop — are recognized as members and can log in normally without any manual intervention.

**Why this priority**: The reporter already has at least one affected account. Fixing forward-going behavior without recovering existing accounts would leave those people unable to use the product.

**Independent Test**: Take an account that is currently a company member yet still flagged as "onboarding not finished," and confirm that after this change it logs in straight to the app with document access and no company-creation prompt.

**Acceptance Scenarios**:

1. **Given** an existing account that is a company member but marked as not having finished onboarding, **When** they log in after this change, **Then** they reach the app without being redirected to onboarding.

---

### Edge Cases

- **Member of multiple companies**: A person added to more than one company is still let straight into the app; the presence of at least one membership is sufficient to bypass company-setup onboarding.
- **Added, then removed from all companies**: If a person is later removed from every company they belonged to, their access to that company's content ends. Defining the onboarding experience for a person who has been stripped of all memberships is out of scope for this fix; the priority here is that *current* members are never trapped.
- **Never even entered a name**: A person added by an admin before completing any onboarding step must still be admitted to the app. Collecting a missing display name, if desired, must not block access or force company creation.
- **Not a member of any company**: A brand-new person who genuinely has no company is unaffected — they still go through onboarding and are asked to create or join a company, as before.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST treat membership in at least one company as satisfying the company-setup portion of onboarding, so that a member is never redirected into onboarding on login.
- **FR-002**: The system MUST NOT require a person who already belongs to a company to create a new company under any circumstance.
- **FR-003**: When an administrator adds an already-registered person to a company, that person's onboarding state MUST be updated so that their next login goes straight into the application, not into onboarding.
- **FR-004**: A person who belongs to a company MUST be able to view that company's documents immediately upon logging in, without first completing or repeating onboarding.
- **FR-005**: The bypass MUST apply regardless of how membership was obtained — self-created company, approved join request, or direct admin add — so no path leaves a member trapped.
- **FR-006**: Existing accounts that are already company members but are still flagged as not having finished onboarding MUST be recognized as onboarded without requiring the person or an administrator to take any manual corrective action.
- **FR-007**: The system MUST continue to route people who genuinely belong to no company through the normal onboarding flow, including the option to create or join a company.
- **FR-008**: The bypass MUST NOT grant a person access to any company they are not a member of; document and company visibility remain limited to companies the person actually belongs to.

### Key Entities *(include if feature involves data)*

- **Person / User account**: Someone who can log in. May or may not belong to a company, and carries an onboarding state indicating whether initial setup is finished.
- **Company**: An organization that owns documents and members. A person may belong to zero, one, or many.
- **Company membership**: The link that makes a person a member of a company, with a role. Its existence is the authoritative signal that the person has "a company" and should skip company-setup onboarding.
- **Onboarding state**: The record of how far a person got through initial setup (e.g., entered name, set up a company, finished). This feature makes it consistent with membership so a member is never treated as unfinished.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of people who belong to at least one company reach the application on login without being redirected into onboarding.
- **SC-002**: 0 people who already belong to a company are asked to create a new company.
- **SC-003**: A person added to a company by an administrator can open that company's documents within their first login session, with no manual setup steps.
- **SC-004**: 100% of previously-trapped existing member accounts can log in normally after the change with no per-account manual intervention.
- **SC-005**: 0 duplicate/unwanted companies are created as a side effect of an existing member logging in.
- **SC-006**: People with no company membership continue to be offered onboarding, so the change causes no regression for genuinely new users.

## Assumptions

- Being a member of any company is sufficient to consider the company-setup step of onboarding done; the product does not require a member to also have explicitly clicked "finish onboarding."
- Collecting profile details such as a display name is a low-priority nicety and must never block a member from entering the app or viewing their documents; a missing name does not justify forcing onboarding.
- The existing "add an already-registered user to my company" administrator capability (and the approved-join-request path) are the membership sources of truth this fix keys off of.
- Recovering already-affected accounts can be done automatically based on existing membership records, without asking the affected people to do anything.
- Removing a person from all of their companies (and what onboarding they should then see) is outside the scope of this fix.
