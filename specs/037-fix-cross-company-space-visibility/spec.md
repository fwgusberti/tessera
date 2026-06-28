# Feature Specification: Confine Space Visibility to the Active Company

**Feature Branch**: `037-fix-cross-company-space-visibility`

**Created**: 2026-06-28

**Status**: Draft

**Input**: User description: "As permissões estão uma completa bagunça no momento. O usuário felipe@gusba.dev loga na companhia Gusba Dev e consegue ver A, B e C. A e B pertencem a Gusba Dev, mas C pertence à companhia 2. Aí eu logo com o usuário 2 da companhia 2, a@2.com, e ele não acessa nenhum. Daí eu logo com o usuário a@3.com e ele consegue ver todos — A, B e C. Está uma completa bagunça, eu preciso que isso seja consertado."

## Overview

Today, who can see and manage a company's spaces is inconsistent and, in places,
completely wrong. A person signed in to one company can see spaces that belong to
**other** companies, while legitimate members of a company can be locked out of
**their own** company's spaces. The deciding factor has become a person's
platform-wide standing rather than the company they are actually working in.

This feature makes one rule true everywhere: **a signed-in person sees and manages
exactly the spaces of the company they are currently acting on behalf of — no
more, no less** — regardless of any platform-level status they may hold.

### Concrete reproduction (the bug we are fixing)

Three companies, three people, three spaces (A and B belong to *Gusba Dev*; C
belongs to *Company 2*):

| Person signed in        | Acting as company | Spaces they see today | Spaces they SHOULD see |
| ----------------------- | ----------------- | --------------------- | ---------------------- |
| felipe@gusba.dev        | Gusba Dev         | A, B, **C**           | A, B                   |
| a@2.com (Company 2)     | Company 2         | **none**              | C                      |
| a@3.com (Company 3)     | Company 3         | **A, B, C**           | none                   |

Today felipe leaks into Company 2's space C, Company 2's own member sees nothing,
and a Company 3 person sees everyone's spaces. After this feature, each person
sees only their own company's spaces.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Each person sees only their active company's spaces (Priority: P1)

When a person signs in and works within a company, the list of spaces they can
see and open contains every space owned by that company and nothing owned by any
other company. This is the core invariant and the exact situation in the
reproduction above.

**Why this priority**: This is a direct, two-way tenant-isolation breach. One
company's spaces are exposed to outsiders (a confidentiality breach), and
companies are simultaneously denied access to their own data. It is the highest
possible severity in a multi-tenant product and the explicit reason the user
filed this.

**Independent Test**: Reproduce the three-user table above. Sign in as each
person in turn and confirm the visible space set matches the "SHOULD see"
column exactly.

**Acceptance Scenarios**:

1. **Given** spaces A and B belong to Gusba Dev and space C belongs to Company 2,
   **When** felipe@gusba.dev is signed in and acting as Gusba Dev, **Then** they
   see A and B and do **not** see C.
2. **Given** space C belongs to Company 2, **When** a@2.com (a member of Company 2)
   is signed in and acting as Company 2, **Then** they see C.
3. **Given** Company 3 owns no spaces, **When** a@3.com is signed in and acting as
   Company 3, **Then** they see no spaces at all.
4. **Given** a person acting as Company A, **When** they attempt to open a space
   owned by Company B by any means, **Then** access is refused and the response
   does not reveal that the Company B space exists.

---

### User Story 2 - Membership in a company is enough to reach that company's spaces (Priority: P1)

A person who is a member of a company can see and manage that company's spaces by
virtue of their membership and role in that company. Reaching one's own company's
spaces must not require any platform-wide administrator status.

**Why this priority**: In the reproduction, Company 2's own member (a@2.com) can
see *nothing* — their legitimate company data is hidden because access was tied to
platform-level standing instead of company membership. A tenant being unable to
reach its own data is as serious as the leak in the other direction.

**Independent Test**: Sign in as an ordinary member of Company 2 who holds no
platform-wide administrator status and confirm they can see and manage Company 2's
spaces.

**Acceptance Scenarios**:

1. **Given** a@2.com is an active member of Company 2 with no platform-wide
   administrator status, **When** they view their spaces, **Then** Company 2's
   space C is shown.
2. **Given** an authorized member of a company, **When** they perform an allowed
   management action on one of their company's spaces (such as changing its
   retention settings or its permissions), **Then** the action succeeds.
3. **Given** a member whose company role does not permit a management action,
   **When** they attempt that action on their own company's space, **Then** it is
   refused based on their role — not because the space is hidden from them.

---

### User Story 3 - Platform-wide status grants no cross-company visibility (Priority: P2)

Holding a platform-wide administrator standing does not, by itself, let a person
see or manage spaces of companies they are not acting within. In everyday use, a
platform administrator working inside Company A sees Company A's spaces only —
exactly like any other member.

**Why this priority**: This is the mechanism behind the leak (felipe and a@3.com
seeing everyone's spaces). Decoupling everyday data visibility from platform-wide
status closes the leak at its source. Marked P2 only because Stories 1 and 2
already assert the user-visible outcome; this story pins down the rule that makes
them hold.

**Independent Test**: Sign in as a person who holds platform-wide administrator
status while acting as a company that owns no spaces, and confirm they see no
spaces.

**Acceptance Scenarios**:

1. **Given** a person with platform-wide administrator status acting as Company 3
   (which owns no spaces), **When** they view their spaces, **Then** they see
   none.
2. **Given** a person with platform-wide administrator status acting as Gusba Dev,
   **When** they view their spaces, **Then** they see Gusba Dev's spaces only and
   not Company 2's.
3. **Given** a legitimate, explicitly-modeled platform-operator capability for
   cross-company administration exists, **When** it is used, **Then** it is a
   clearly separate, audited surface — not the everyday "my company's spaces"
   view — and is available only to designated platform operators.

---

### Edge Cases

- **No active company**: A signed-in person who is not currently acting within any
  company sees no spaces and can manage none.
- **Multiple company memberships**: When a person belongs to more than one company,
  the visible spaces always reflect the single company they are currently acting
  in; switching the active company switches the visible set accordingly.
- **Revoked membership**: A person whose membership in a company has been removed or
  revoked immediately loses visibility into and management of that company's
  spaces.
- **Probing another company's space by identifier**: Attempting to reach a known
  space identifier that belongs to another company is indistinguishable from the
  space not existing — it must not confirm the space's existence.
- **Space with no individual members**: A company's space that no individual has
  been explicitly added to is still visible to that company's authorized members
  (e.g., its company administrators) and never to other companies.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST restrict the set of spaces a signed-in person can see to
  those owned by the company they are currently acting on behalf of (their active
  company).
- **FR-002**: System MUST allow every active member of a company to see that
  company's spaces based on their membership and role in that company, without
  requiring any platform-wide administrator status.
- **FR-003**: System MUST prevent any signed-in person from seeing, opening, or
  managing a space owned by a company other than their active company.
- **FR-004**: A person's platform-wide administrator status MUST NOT, by itself,
  grant visibility into or management of spaces belonging to companies they are not
  currently acting within.
- **FR-005**: Management actions on a space (for example, changing retention
  settings, configuring permissions, or triggering maintenance such as
  reindexing) MUST be limited to spaces owned by the actor's active company and to
  people authorized within that company.
- **FR-006**: When a person belongs to more than one company, the set of visible
  and manageable spaces MUST reflect the single company they are currently acting
  in, and switching active company MUST switch that set accordingly.
- **FR-007**: An attempt to access a space that belongs to another company MUST NOT
  reveal whether that space exists; it MUST be indistinguishable from the space not
  existing.
- **FR-008**: Any genuinely cross-company or platform-wide space operation MUST be
  an explicitly separate, audited capability, distinct from the everyday
  company-member space view, and available only to designated platform operators.
- **FR-009**: Every attempt to access or change a space MUST be recorded with the
  acting person, the company context, and the affected space, so that cross-company
  attempts are auditable.

### Key Entities *(include if feature involves data)*

- **Company (tenant)**: The organization that owns spaces. A person acts on behalf
  of exactly one company at a time (their active company).
- **Space**: A container of company knowledge. Each space belongs to exactly one
  company and is the unit a person browses and manages.
- **Member**: A person who belongs to one or more companies, each with a role that
  governs what they may do in that company. A member may separately hold a
  platform-wide administrator status, which is unrelated to which company's spaces
  they may see.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A person acting as a given company sees 100% of that company's spaces
  and 0% of any other company's spaces.
- **SC-002**: Running the three-user reproduction yields exactly the "SHOULD see"
  column: felipe@gusba.dev sees A and B; a@2.com sees C; a@3.com sees none.
- **SC-003**: No account, regardless of platform-wide status, can view or manage
  another company's space through the everyday space view — verified by automated
  cross-company isolation tests on every space access and management path.
- **SC-004**: A legitimate company member with no platform-wide administrator
  status can see and manage their own company's spaces in 100% of attempts.
- **SC-005**: An attempt by a person acting as Company A to reach a Company B space
  returns no Company B data and does not disclose the space's existence, in 100% of
  attempts.

## Assumptions

- The spaces referred to as "A, B, and C" in the report are the product's
  knowledge spaces, and the same active-company scoping rule extends to anything
  reached through a space (its documents and settings).
- Each person operates within a single active company per session, established at
  sign-in or when switching companies, using the existing company-context
  mechanism.
- The companies, spaces, and memberships described already exist and record which
  company owns each space; expressing correct ownership scoping requires no new
  data model.
- A separate, audited platform-operator capability for legitimate cross-company
  administration may continue to exist, but it is distinct from the everyday
  company-member experience that this feature governs.
