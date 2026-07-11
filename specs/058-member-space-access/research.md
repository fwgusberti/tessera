# Research: Space Access Management for Company Members (058)

All Technical Context items were resolvable from the codebase — no external
research required, no NEEDS CLARIFICATION remaining.

## R1. Why the reported account sees no spaces (root-cause confirmation)

**Finding**: `GET /v1/spaces` (`apps/api/tessera_api/routers/spaces.py:175`)
returns only `SqlSpaceRepository.list_accessible_by_user(user_id, company_id)` —
a recursive CTE over `space_memberships` (direct memberships + descendants).
A user added to a company via any path (direct add 054, invitation 054,
domain match 055) receives **no** `space_memberships` rows, so the list is
empty. This is least-privilege by design; the defect is the absence of a grant
surface and the misleading empty state
(`apps/web/app/spaces/page.tsx:71` — "No spaces available in your company.").

**Decision**: Keep least-privilege (no auto-grant). Fix visibility, grant
surface, and messaging.

## R2. Authorization for grants — is a new permission path needed?

**Finding**: `effective_space_role(user, space_id, memberships,
is_company_admin=True)` returns `SpaceRole.ADMIN`
(`packages/core/tessera_core/permissions/access.py:150`) — company admins are
implicit admins of every space in their own company (feature 036). All member
write endpoints already pass `is_company_admin` through
(`members.py`: `invite_member`, `change_member_role`, `remove_member`,
`search_members`), and each validates the space belongs to the caller's company
first (`_require_space_in_company`, feature 035/037 convention).

**Decision**: Reuse `POST /v1/spaces/{space_id}/members`,
`PUT /v1/spaces/{space_id}/members/{user_id}`,
`DELETE /v1/spaces/{space_id}/members/{user_id}` as the only write path.
**Rationale**: one authoritative path keeps per-space and per-member views
consistent (FR-011) and keeps audit records (`member_invited`,
`member_role_changed`, `member_removed`) flowing through the existing
`MembershipService`.
**Alternatives considered**: new `PUT /companies/members/{id}/space-access`
bulk endpoint — rejected: duplicates authorization + audit logic, invites
drift between the two write paths.

## R3. Admin-wide space visibility (FR-005)

**Finding**: `list_spaces`, `get_space`, `get_ancestors` all gate on
`list_accessible_by_user`, so a company admin cannot see or open spaces they
don't belong to — even though the permission layer would let them manage those
spaces' members. `SpaceRepository.list_by_company(company_id)` already exists
(`ports/repositories/space.py:23`, adapter `space.py:89`) and is tenant-scoped.

**Decision**: Add a company-admin branch to the read path: effective accesses =
membership-derived accesses (unchanged) ∪ all remaining company spaces as
`SpaceAccess(effective_role=ADMIN, is_direct=False)`. Implement in
`SpaceHierarchyService` (core) so the rule is domain-owned and unit-testable;
the router switches `list_spaces` from `CompanyContext` to
`CompanyMemberContext` to obtain the caller's company membership role. Apply
the same branch to `get_space` and `get_ancestors` access checks.
**Rationale**: consistent with the implicit-admin permission model already
ratified in feature 036; keeps `is_company_admin` derived from session-bound
membership, never input (Constitution VI).
**Alternatives considered**: (a) separate `GET /v1/admin/spaces` — rejected:
every existing UI affordance (Members link on `FolderTile`, set-parent, delete)
would need duplicate wiring; (b) widening `list_accessible_by_user` SQL itself —
rejected: repository stays mechanism-only, policy belongs in the service.

**Ripple check**: dependents of `GET /v1/spaces` (Spaces page, document
add/move space pickers, NavBar space-role probe) receive *more* rows for
admins, all within the same company — no cross-tenant surface. Document reads
already company-admin-bypass via `can_read_space_document`.

## R4. Member-centric read model

**Finding**: assembling "all company spaces × this member's access" client-side
would need one `GET /spaces/{id}/members` call per space (N+1) and would leak
ordering/inheritance logic into the UI. Building blocks exist server-side:
`list_by_company(company_id)`, `list_accessible_by_user(member_id, company_id)`
(effective role + `is_direct`), `SqlSpaceMembershipRepository.list_by_user`
(direct roles).

**Decision**: New core `MemberAccessService.space_access_for_member(member_id,
company_id)` returning, for every company space: direct role (or none),
effective role (or none), and `is_direct`; exposed via admin-gated
`GET /v1/companies/members/{user_id}/space-access` in `companies.py`.
Target-user validation: must hold a `company_memberships` row for the caller's
active company, else generic 404 (feature 053/054 convention for by-ID
cross-tenant probes).
**Rationale**: one round-trip, tenant checks server-side, inheritance semantics
computed by the same CTE used everywhere else.
**Alternatives considered**: extending `GET /companies/members` with embedded
access lists — rejected: bloats the roster payload for a per-member drill-in.

## R5. Join-path parity sweep (User Story 4, "fix any bug related")

**Finding**: all four join paths end in a `company_memberships` row:
self-created company (onboarding), invitation acceptance (054), direct add
(054 `POST /companies/members`), domain match at sign-up (055). Roster
(`GET /companies/members`) and space member search
(`search_members_for_space`) both key off `company_memberships` only — no
path-specific tables — so parity is expected. Feature 056 already fixed the
onboarding-gate trap for added members.

**Decision**: No code change anticipated; encode parity as integration tests
(one member per join path → appears in roster, appears in member search, grant
works, spaces visible after grant). If a test exposes a gap, fix within this
feature.

## R6. Frontend surface

**Decision**: `MemberSpaceAccessPanel` (client component, follows
`SpaceMembersPanel`/`AddUserPanel` patterns): opened per roster row on
`/users`; fetches the new endpoint; renders each space with role select +
grant/revoke controls; optimistic in-place updates mirroring
`handleMemberAdded` (feature 054 FR-013 pattern). Styling per constitution UI
system (slate neutrals, indigo-600 actions, red for revoke).
Spaces page empty state branches on company role: non-admin + 0 accesses →
"No spaces have been shared with you yet. A company administrator can grant
you access."; admin + 0 spaces → existing copy (company truly has no spaces).
**Alternatives considered**: dedicated route `/users/[id]/spaces` — rejected:
a panel keeps the admin in the roster context they just used to add the user
(FR-004); no deep-linking requirement exists.

## R7. Test environment baseline (validation strategy)

Pre-existing, unrelated failures to ignore when validating this feature:
`test_ports`, `migration_0002`, `tessera_mcp` suites; the API package's 85%
coverage gate is unreachable (~73% baseline) — run targeted suites
(`pytest apps/api/tests/... packages/core/tests/...` for touched areas, plus
`test_tenant_isolation.py`) and web Vitest, rather than relying on the global
gate. Marker conventions: `@pytest.mark.asyncio` in `packages/core`,
`@pytest.mark.anyio` in `apps/api`; integration tests use
`fastapi.testclient.TestClient`; routers keep module-level imports for
patchability.
