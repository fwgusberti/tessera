# Implementation Plan: User Badge

**Branch**: `057-user-badge` | **Date**: 2026-07-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/057-user-badge/spec.md`

## Summary

Add a persistent user badge to the primary navigation so a signed-in person can
confirm, from any authenticated page, which account is active. The badge shows
the account's email (primary label), a display name when one is available, and a
short visual marker (initials) for at-a-glance recognition. It is hidden when no
one is signed in and updates immediately on sign-in / sign-out.

**Technical approach**: The email is already available client-side from the
decoded access-token (`useAuth().user`), so the badge renders identity instantly
with no network round-trip. The display name is *not* in the token, so a small
read-only endpoint `GET /v1/auth/me` returns the caller's own identity
(`id`, `email`, `display_name`, `is_admin`) keyed by the token subject. A new
`UserBadge` client component consumes both: it paints the email immediately and
enriches with the display name and initials when `/auth/me` resolves. The badge
is placed in the existing `NavBar` (desktop bar + mobile menu) alongside the
current account / sign-out controls.

## Technical Context

**Language/Version**: TypeScript 5 (Next.js 15 App Router, React 19) for the web
app; Python 3.12 (FastAPI) for the API.

**Primary Dependencies**: Next.js, React, Tailwind CSS (web); FastAPI, joserfc
(JWT), SQLAlchemy async (api). No new dependencies introduced.

**Storage**: PostgreSQL (system of record). This feature introduces **no** schema
changes — it reads the existing `users.display_name` for the caller's own row.

**Testing**: Vitest + Testing Library for the web component; pytest + anyio for
the API endpoint (integration via `fastapi.testclient.TestClient`).

**Target Platform**: Modern browsers, desktop and mobile viewports; Linux-hosted
API.

**Project Type**: Web application (Next.js frontend `apps/web` + FastAPI backend
`apps/api`).

**Performance Goals**: Badge identity visible in < 3s on every authenticated page
(SC-001) — met trivially since email renders synchronously from the in-memory
token; `/auth/me` is a single indexed primary-key read.

**Constraints**: Badge must truncate long identifiers without breaking layout,
remain legible on mobile, and must never display another account's identity
(0% cross-account leakage, SC-004).

**Scale/Scope**: One new API endpoint, one new React component, a small client
helper for initials, and wiring into `NavBar`. No migrations.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Domain-Driven Architecture** — PASS. No new domain logic. The endpoint
  reuses the existing `SqlUserRepository.get_by_id`; the initials helper is pure
  presentation logic living in the web layer, not the domain.
- **II. Separation of Concerns** — PASS. `spec.md` stays WHAT/WHY; all HOW lives
  here. No product definition depends on framework choices.
- **III. Data Locality & Consent** — PASS. No new client-side persistence. The
  badge reads identity already held in memory (decoded token) plus a transient
  fetch; nothing new is written to `localStorage`.
- **IV. Test-Driven Development (NON-NEGOTIABLE)** — PASS (planned test-first).
  API: unit/integration tests for `GET /v1/auth/me` (returns caller identity;
  401 unauthenticated) written before the handler. Web: Vitest tests for
  `UserBadge` (renders email; enriches with name; derives initials; truncates;
  hidden when unauthenticated) and for the initials helper, written first. The
  85% statement-coverage gate applies to the Python change; the new endpoint is
  small and fully covered.
- **V. Quality Gates** — PASS. Python changes pass Ruff + Black; web changes pass
  the existing lint config.
- **VI. Tenant Data Isolation (NON-NEGOTIABLE)** — PASS. See Tenant Isolation
  section below.

### Tenant Isolation

- **Tables accessed**: `users` — **only the caller's own row**, fetched by
  `get_by_id(UUID(user_info["sub"]))` where `sub` comes from the verified access
  token established at the request boundary. No user-supplied ID is accepted.
- **Multi-tenant business tables** (Space, Document, Chat, Membership) are **not**
  queried by this feature; there is no company-scoped read, so no `company_id`
  predicate is applicable — the endpoint returns the authenticated principal's
  own identity, which is intrinsically single-subject.
- **Cross-tenant risk**: None. The response is derived solely from the token
  subject; a caller cannot request another user's or another company's identity.
- **Isolation tests to be written**:
  1. `GET /v1/auth/me` without a bearer token → 401.
  2. Two users in **different** companies each call `/auth/me`; each response's
     `id`/`email` equals *their own* token subject and never the other's
     (validates SC-004, 0% cross-account leakage).
  3. The returned `email` always equals the token's `email` claim (no substitution
     of another account's identity).

## Project Structure

### Documentation (this feature)

```text
specs/057-user-badge/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── auth-me.md              # GET /v1/auth/me response contract
│   └── user-badge.md           # UserBadge component + initials contract
├── checklists/
│   └── requirements.md  # (existing) spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
apps/api/tessera_api/
├── routers/
│   └── auth.py                 # ADD: GET /v1/auth/me handler
└── tests/
    ├── integration/
    │   └── test_auth_me.py     # NEW: endpoint + isolation tests
    └── unit/                   # (as needed for handler-level coverage)

apps/web/
├── components/
│   └── UserBadge.tsx           # NEW: badge component (desktop + mobile variants)
├── lib/
│   ├── auth.tsx                # reuse: useAuth() for immediate email + status
│   └── identity.ts             # NEW: fetchMe() + initials() helper (or colocate)
├── components/
│   └── NavBar.tsx              # EDIT: mount <UserBadge/> in desktop bar + mobile menu
└── tests/
    ├── UserBadge.test.tsx      # NEW
    └── identity.test.ts        # NEW: initials derivation + truncation logic
```

**Structure Decision**: Existing web-application layout is used unchanged. The
API change is a single additive endpoint in the existing `auth.py` router; the
web change is one new presentational component plus a small identity helper,
mounted into the existing `NavBar`. No new top-level directories.

## Complexity Tracking

> No constitution violations. Section intentionally left empty.
