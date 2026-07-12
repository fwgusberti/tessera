# Research: Company Page (060)

**Date**: 2026-07-11 | **Plan**: [plan.md](./plan.md)

No NEEDS CLARIFICATION markers remained after codebase inspection — every
unknown was resolvable by reading the existing implementation. Findings and
decisions below.

## R1. What already exists (codebase survey)

**Backend** (`apps/api`, `packages/core`):

- `Company` domain model (`packages/core/tessera_core/domain/company.py`)
  already has every field the page needs: `name`, `industry: str | None`,
  `team_size: str | None`, `created_at`, `updated_at`, `admin_user_id`.
- `companies` table (`apps/api/tessera_api/adapters/models/company.py`)
  matches: `name String(255) NOT NULL`, `industry String(100)`,
  `team_size String(20)`, timezone-aware `created_at`/`updated_at` with
  server defaults and `onupdate`. **No migration needed.**
- `CompanyRepository` port has `create`, `get_by_id`, membership methods —
  but **no update method**. Neither does the SQL adapter.
- The companies router exposes creation, membership, invitations,
  join-requests, and `GET /companies/me` (id/name/role list) — but **no
  endpoint returns the active company's full profile and none updates it**.
  This is the actual gap the feature fills.
- Auth dependencies (`tessera_api/auth/oidc.py`) already provide exactly the
  two tiers needed: `CompanyMemberContext` (any member of the token's active
  company; re-validates membership + company activeness per request) and
  `CompanyAdminContext` (`CompanyRole.ADMIN` required, 403 `forbidden`
  otherwise). Company id flows only from the JWT claim.
- `write_audit(session, actor_type, actor_id, action, entity_type,
  entity_id, metadata)` is the established audit channel; prior company
  actions use dotted actions (`company.created`, `company.member_added`).
- `VALID_TEAM_SIZES = {"1-10", "11-50", "51-200", "201-1000", "1000+"}` is
  defined in the companies router and enforced on creation.

**Web** (`apps/web`):

- `/settings/company/page.tsx` is a "coming soon" placeholder — and
  `CompanyMenu` already links to it, but only for admins
  (`activeCompany?.role === "admin"`).
- `CompanyProvider` (`lib/company.tsx`) exposes `activeCompany`
  (id/name/**role**) and `reloadCompanies()` — the page can use the role for
  UI gating and the reload for name propagation after a save.
- Onboarding `CompanyForm` holds the canonical option lists:
  `INDUSTRIES` (8 values incl. "Other") and `TEAM_SIZES` (mirrors the server
  set). They are module-local today.
- The Users page (053) established the pattern this page follows: client
  component, `AuthGuard`, role from `useCompany()`, clean denial rendering on
  403, slate/indigo styling.

## R2. Endpoint shape

- **Decision**: Two endpoints on the existing companies router addressed as a
  singleton: `GET /v1/companies/current` and `PATCH /v1/companies/current`.
- **Rationale**: The tenant key never appears in the URL or body, so a
  cross-tenant request is inexpressible (Constitution VI, FR-009) — the same
  convention 053/054 used for `/companies/members`. `current` also matches
  the page's semantics: "the company of my active session" (spec edge case
  for multi-company users falls out for free, since the token carries exactly
  one `company_id`).
- **Alternatives considered**:
  - `GET/PATCH /v1/companies/{company_id}` with a context-match check —
    rejected: reintroduces a client-supplied tenant id that must be validated
    against the token on every call; one missed check is a breach. The
    existing `{company_id}` routes are onboarding/join flows that predate the
    scoped-token model.
  - Extending `GET /companies/me` with full details — rejected: `me` is a
    *memberships list* consumed by the select-company flow with select-kind
    tokens; the profile is a property of the *active* company and needs the
    member-context guard, not the bare-user guard.

## R3. Authorization split

- **Decision**: `GET` uses `CompanyMemberContext`; `PATCH` uses
  `CompanyAdminContext`. The GET response includes the caller's `role` so the
  client renders edit controls without a second request.
- **Rationale**: Matches FR-004/FR-008 exactly and reuses the audited,
  tested dependencies from 053/059 — no new auth code. Server-side
  enforcement is the real gate (US3 acceptance 2); the client gate is UX
  only.
- **Alternatives considered**: role check inside the handler via
  `_require_company_admin` — rejected: the dependency annotation is the
  established, review-enforceable pattern.

## R4. Update path & concurrency

- **Decision**: New port method
  `update_details(company_id, *, name, industry, team_size) -> Company | None`
  implemented in `SqlCompanyRepository` as a scoped read-modify-write on
  `WHERE id = :company_id`; plain last-write-wins, no version column.
- **Rationale**: Spec explicitly scopes concurrency to
  last-successful-save-wins; `updated_at` already auto-bumps via `onupdate`.
  Returning the mapped `Company` lets the router echo the authoritative
  saved state (edge case: the responding payload is always one edit, never a
  mix).
- **Alternatives considered**: optimistic locking with an `updated_at`
  precondition — rejected as out of scope per spec assumptions; can be added
  later without contract change (would become a 409).

## R5. Validation rules

- **Decision**: PATCH request model mirrors `CreateCompanyRequest`:
  `name: str (min_length=1 after strip, max_length=255)`,
  `industry: str | None (max_length=100)`, `team_size: str | None` checked
  against `VALID_TEAM_SIZES` (422 `invalid_team_size`, same code as create).
  Whitespace-only names are rejected (422) — the client also trims before
  submit, like onboarding. `null` clears an optional field.
- **Rationale**: Spec assumption pins accepted values to the onboarding set;
  reusing the create limits keeps one source of truth (FR-005, edge case for
  overlong names — 255 cap with a clear message).
- **Alternatives considered**: server-side INDUSTRIES enum — rejected:
  creation never enforced one (column is free text ≤100); tightening now
  could make existing rows un-savable. The fixed list stays a client-side
  select, consistent with onboarding.

## R6. Page location & navigation

- **Decision**: Rebuild the existing `/settings/company` placeholder as the
  company page; remove the admin gate on the `CompanyMenu` link and relabel
  it "Company".
- **Rationale**: The route, link, and page shell already exist — the
  placeholder's own copy ("Full company settings are coming soon") marks it
  as this feature's slot. Un-gating satisfies FR-001 (page for all members)
  and SC-001 (discoverable: it's in the company dropdown every member already
  uses).
- **Alternatives considered**: new top-level `/company` route + NavBar link —
  rejected: duplicates an existing route, adds a NavBar item for a
  low-frequency page, and would orphan or redirect the placeholder.

## R7. Displaying and propagating changes

- **Decision**: View mode renders a definition-list card; empty
  `industry`/`team_size` render the literal text "Not provided" in muted
  slate (FR-003). `created_at` renders as a formatted date, never editable.
  After a successful save the page swaps in the PATCH response and calls
  `reloadCompanies()` so the nav's company name updates immediately (FR-007).
  On save failure the form stays in edit mode with the entered values and an
  error banner (edge case).
- **Rationale**: `CompanyProvider` already owns every other place the name
  appears (CompanyMenu, select-company page reloads independently); one
  reload call is the smallest correct propagation channel.
- **Alternatives considered**: pushing the updated name into the provider
  directly — rejected: `reloadCompanies()` already exists and also picks up
  any server-side normalization.

## R8. Test strategy (TDD order)

- **Decision**:
  - API unit (`tests/unit/test_company_profile_router.py`, anyio marker,
    module-level-import patching per repo convention): GET happy path +
    role echo; GET as plain member; PATCH happy path + audit call assert;
    PATCH 403 non-admin; 422 empty/whitespace/overlong name; 422 bad
    team_size; nulls clear optional fields.
  - Repo unit (`tests/unit/test_company_repo.py` extension):
    `update_details` persists, bumps `updated_at`, returns `None` for a
    missing id, and leaves a second seeded company untouched.
  - Integration (`tests/integration/test_company_profile.py`, sync
    `TestClient`): member view, admin edit persists across a fresh GET,
    non-admin PATCH refused with data unchanged, revoked-membership token →
    403, unauthenticated → 401, audit row written (SC-003/SC-004).
  - Web (`tests/company-page.test.tsx` + `company-menu.test.tsx` extension):
    US1/US2/US3 acceptance scenarios incl. "Not provided", cancel restores,
    failed save preserves input, non-admin sees no edit controls, menu link
    visible to members.
- **Rationale**: Constitution IV; markers/client choices follow the repo's
  established conventions (anyio in `apps/api`, sync TestClient for
  integration). Known pre-existing failures (test_ports, migration_0002,
  tessera_mcp) and the repo-wide coverage baseline are excluded from this
  feature's pass/fail signal — see quickstart.
