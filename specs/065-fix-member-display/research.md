# Research: Human-Readable Member Identity in User Management

**Feature**: `065-fix-member-display` | **Date**: 2026-07-12

No NEEDS CLARIFICATION items remained after codebase inspection; every
decision below was resolved against the existing implementation.

## R1. Root cause of the reported defect

**Finding**: `GET /v1/spaces/{space_id}/members`
(`apps/api/tessera_api/routers/members.py:107-131`) returns
`[m.model_dump() for m in memberships]` where each `m` is the domain
`SpaceMembership` (`packages/core/tessera_core/domain/space_membership.py`),
which carries only `id`, `space_id`, `user_id`, `role`, `invited_by_user_id`,
and timestamps. The frontend row
(`apps/web/components/members/SpaceMembersPanel.tsx:86-91`) renders
`{member.display_name || member.user_id}` and only shows the email line when
present — so today every row shows a UUID and no email. The `Member`
interface already declares optional `display_name`/`email` fields: the UI was
built for the enriched shape the API never delivered.

## R2. Where to join identity onto memberships

**Decision**: Enrich the existing endpoint with a single SQL JOIN in the
repository layer: new port method
`SpaceMembershipRepository.list_by_space_with_identity(space_id, company_id)`
returning a new `SpaceMemberListing` value object, implemented in
`SqlSpaceMembershipRepository` as
`SELECT space_memberships.*, users.display_name, users.email FROM
space_memberships JOIN users ON users.id = space_memberships.user_id JOIN
spaces ON spaces.id = space_memberships.space_id AND spaces.company_id =
:company_id WHERE space_memberships.space_id = :space_id ORDER BY
users.display_name`.

**Rationale**:
- Exactly mirrors the proven precedent for the company Users page:
  `SqlCompanyRepository.list_members` joins `users` and returns
  `CompanyMemberListing(user_id, display_name, email, role)` ordered by
  `display_name` (`apps/api/tessera_api/adapters/repositories/company.py:158`).
- One query, no N+1; satisfies FR-002 ("provide name and email wherever a
  member list is served").
- Taking `company_id` and enforcing it in the query satisfies Constitution VI
  ("no repository method returning tenant-owned data may accept a bare entity
  ID without also receiving and validating the company_id") — the legacy
  `list_by_space` relies on upstream route validation only.
- SQL `ORDER BY display_name` matches the company Users page default ordering
  (spec assumption confirmed).

**Alternatives considered**:
- *Router-level merge (fetch memberships, then batch-fetch users by ID and
  zip)*: two queries, identity-merging logic leaks into the transport layer,
  and no precedent in the codebase. Rejected.
- *New endpoint (e.g., `/members/detailed`)*: forces frontend migration and
  leaves the broken endpoint alive. Rejected — additive enrichment of the
  existing response is backward compatible.
- *Frontend joins (call `/companies/members` and correlate client-side)*:
  wrong audience (that endpoint is company-admin-only via
  `CompanyAdminContext`, while space members may be listed by any space
  member), N+1 at the UI layer, violates FR-002. Rejected.
- *Eager-loading via SQLAlchemy relationship on `SpaceMembershipModel`*:
  would return ORM models upward and encourage passing persistence objects
  into the domain; explicit column JOIN + value object keeps the port
  contract framework-free. Rejected.

## R3. Shape of the enriched response

**Decision**: Keep the response envelope `{"members": [...]}` and every
existing membership field, adding `display_name: str` and `email: str` per
row:
`{id, space_id, user_id, display_name, email, role, invited_by_user_id, created_at, updated_at}`.

**Rationale**: Purely additive — the panel's `Member` interface already
declares both new fields as optional, and mutation flows
(`PUT/DELETE /members/{user_id}`) keep using `user_id` from the same row, so
FR-005 (actions still target the right member) holds with no change to the
mutation endpoints. `search_members_for_space` already exposes exactly
`display_name`/`email` to overlapping audiences, so no new data class of
exposure is created (FR-007).

**Alternatives considered**: nesting identity under a `user: {...}` sub-object
— cleaner in the abstract but breaks the existing flat interface for no
functional gain. Rejected.

## R4. Domain value object

**Decision**: New plain class `SpaceMemberListing` in
`packages/core/tessera_core/domain/space_member_listing.py` with fields
`id`, `space_id`, `user_id`, `display_name`, `email`, `role: SpaceRole`,
`invited_by_user_id`, `created_at`, `updated_at`.

**Rationale**: Mirrors `CompanyMemberListing`
(`packages/core/tessera_core/domain/company_member_listing.py`), the
established pattern for "membership + identity" read models in this codebase.
Keeping it distinct from `SpaceMembership` preserves the entity as the write
model while the listing is a read-only projection.

**Alternatives considered**: adding optional `display_name`/`email` fields to
`SpaceMembership` itself — muddies the write model with sometimes-populated
read fields and would silently serialize `None` on every mutation response.
Rejected.

## R5. Frontend label fallback and layout

**Decision**: In `SpaceMembersPanel.tsx`, the primary label becomes
`display_name || email || "Unknown user"`; the secondary line shows `email`
only when a non-blank `display_name` exists (avoids duplicating the email on
both lines when it is the primary label). The `user_id` fallback is removed
entirely. Long values get `truncate` with a bounded cell width so the table
layout holds (edge case in spec). The same terminal fallback ("Unknown user")
is applied on the two other member-labeling surfaces that render
name-or-else: `app/users/page.tsx` (currently `display_name || email`) and
`AddMemberForm.tsx` search results (currently bare `display_name`) — Story 3
consistency sweep.

**Rationale**: Matches the spec's FR-003/FR-004 fallback rules and the
company Users page presentation (name primary, email secondary in
`text-xs text-slate-500`). "Unknown user" is a neutral placeholder for the
data-anomaly case where both fields are blank.

**Alternatives considered**: shared `<MemberIdentity>` component extracted
across the three surfaces — considered, but each surface's markup differs
(table cell vs. search-result line vs. inline selection chip) and the shared
logic is one expression; extraction is deferred until a fourth surface needs
it. Rejected for now.

## R6. Authorization check without a second query

**Decision**: `list_members` keeps its existing authorization rule
(`can_read_space_document(actor, space_id, memberships, is_company_admin=…)`)
but derives the `SpaceMembership` list needed by that permission function
from the enriched `SpaceMemberListing` rows (they carry `user_id`, `space_id`,
`role`) instead of issuing a second `list_by_space` query.

**Rationale**: keeps the endpoint at one membership query while leaving the
permission function's signature untouched (it is shared with other routes).
The audience therefore stays exactly as before (FR-007).

**Alternatives considered**: calling both `list_by_space` and the new method
(simplest diff, two queries) — acceptable but wasteful; the projection
already contains the needed fields. Rejected.

## R7. Test strategy (TDD order)

**Decision**:
1. `packages/core/tests/test_space_member_listing.py` — value object holds
   all fields (mirror of `test_company_member_listing.py`).
2. `apps/api/tests/integration/test_members.py` +
   `apps/api/tests/contract/test_members.py` — list response includes
   `display_name`/`email` per member; rows ordered by `display_name`;
   Company A admin hitting Company B's space gets generic 404 with no
   identity data; repository-level wrong-company scoping returns empty.
   (anyio markers, `fastapi.testclient.TestClient`, module-level imports —
   established API-suite conventions.)
3. `apps/web/tests/members.test.tsx` — row shows name with email beneath;
   blank name → email as primary label; both blank → "Unknown user"; the raw
   UUID never appears in the rendered output; role change and remove still
   call `/v1/spaces/{id}/members/{user_id}`.

**Rationale**: Constitution IV (test-first at each layer). Coverage: the API
package's 85% statement gate is unreachable at its pre-existing ~73%
baseline; validation asserts zero new failures against the known-failing
baseline (test_ports, migration_0002, tessera_mcp) while all new/changed code
paths are directly exercised by the tests above.
