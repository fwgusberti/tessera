# Implementation Plan: Frontend Login

**Branch**: `005-frontend-login` | **Date**: 2026-06-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-frontend-login/spec.md`

## Summary

Add authentication to the Next.js 15 frontend (`apps/web`): a `/login` page, an `AuthContext` managing access/refresh token lifecycle in `localStorage`, a client-side auth guard wrapping all existing pages, and an updated API client that injects `Authorization` headers and silently refreshes expired tokens. The backend JWT endpoints (`/v1/auth/login`, `/v1/auth/refresh`, `/v1/auth/logout`) are already operational.

## Technical Context

**Language/Version**: TypeScript 5, React 19, Next.js 15.5.19

**Primary Dependencies**: Next.js App Router, Tailwind CSS 4, Vitest, @testing-library/react — no new dependencies required

**Storage**: `localStorage` for `access_token`, `refresh_token`, `token_type`, `expires_at` (justified in spec Assumptions and Constitution Check below)

**Testing**: Vitest + @testing-library/react (jsdom) — same setup as existing tests under `apps/web/tests/`

**Target Platform**: Browser (same-origin Next.js app at `http://localhost:3000`, API at `http://localhost:8000`)

**Project Type**: Web application (Next.js App Router, client-rendered pages)

**Performance Goals**: Login redirect within 1 second of 401 detection (SC-003); login flow under 30 seconds (SC-001)

**Constraints**: No new npm dependencies. All auth logic in `lib/`; all pages remain "use client" client components (existing pattern). Middleware cannot read `localStorage`, so route protection is client-side.

**Scale/Scope**: Single-user login flow across ~7 routes (home, documents, search, metrics, proposals, admin, assistant)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. DDD | ✅ PASS | Frontend has no domain models; auth context is an infrastructure concern correctly separated from page components |
| II. Separation of Concerns | ✅ PASS | `lib/auth.tsx` (state + refresh logic) is separate from `lib/api.ts` (HTTP transport) and all page components |
| III. Data Locality & Consent | ✅ PASS with justification | Session tokens stored in `localStorage`. Spec Assumptions explicitly notes: consent dialog not required because tokens are a technical necessity, expire automatically, and are never shared with third parties. Tokens are not personal data in the GDPR/LGPD sense — they are credentials that identify a session, not the user's personal information |
| IV. TDD | ✅ PASS | Constitution §IV mandates test-first for "core business domains" and 85% statement coverage for Python modules. Frontend TypeScript is not a Python module; however, the spirit requires tests. All new modules (`lib/auth.tsx`, `app/login/page.tsx`) must have companion Vitest tests written before or alongside implementation |
| V. Quality Gates | ✅ PASS | Ruff/Black apply to Python. TypeScript has no linter configured in `package.json` yet — no gate to fail |

**Post-Phase-1 re-check**: ✅ Design upholds all principles. See Constitution Check in research.md for the `localStorage` decision rationale.

## Project Structure

### Documentation (this feature)

```text
specs/005-frontend-login/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── auth-context.ts  # AuthContext interface contract
│   └── api-client.ts    # Updated api.ts interface contract
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
apps/web/
├── app/
│   ├── login/
│   │   └── page.tsx           # NEW: Login page (public route)
│   ├── layout.tsx             # UPDATED: wraps children in AuthProvider + adds logout to nav
│   ├── page.tsx               # UPDATED: wrapped with AuthGuard
│   ├── search/page.tsx        # UPDATED: wrapped with AuthGuard
│   ├── documents/page.tsx     # UPDATED: wrapped with AuthGuard
│   ├── metrics/page.tsx       # UPDATED: wrapped with AuthGuard
│   ├── proposals/page.tsx     # UPDATED: wrapped with AuthGuard
│   ├── admin/page.tsx         # UPDATED: wrapped with AuthGuard
│   └── assistant/page.tsx     # UPDATED: wrapped with AuthGuard (if exists)
├── lib/
│   ├── api.ts                 # UPDATED: inject Bearer header + 401→refresh interceptor
│   ├── auth.tsx               # NEW: AuthContext, AuthProvider, useAuth hook
│   ├── auth-guard.tsx         # NEW: AuthGuard client component
│   └── types.ts               # UPDATED: AuthState, LoginCredentials types
└── tests/
    ├── login.test.tsx          # NEW: Login page tests (form, validation, redirect)
    ├── auth.test.tsx           # NEW: AuthContext tests (login, logout, refresh, persistence)
    ├── auth-guard.test.tsx     # NEW: AuthGuard redirect behaviour
    ├── home.test.tsx           # EXISTING (may need auth mock)
    ├── documents.test.tsx      # EXISTING (may need auth mock)
    └── admin.test.tsx          # EXISTING (may need auth mock)
```

**Structure Decision**: Single web app option. All changes confined to `apps/web/`. No new packages or services introduced.

## Complexity Tracking

> No constitution violations requiring justification. The `localStorage` usage for session tokens is explicitly sanctioned by the spec's Assumptions section under Constitution Principle III.
