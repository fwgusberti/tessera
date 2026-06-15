# Implementation Plan: New User Registration

**Branch**: `006-user-registration` | **Date**: 2026-06-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/006-user-registration/spec.md`

## Summary

Add a self-service user registration page (`/register`) to the Tessera Next.js frontend. The page collects display name, email, and password; validates them client-side; calls the existing backend `POST /v1/auth/register` endpoint; then immediately auto-logs the user in and redirects them to their intended destination (respecting `?redirect=`). A non-blocking password strength indicator is shown as the user types. The login page gains a link to `/register`.

## Technical Context

**Language/Version**: TypeScript 5, React 19, Next.js 15 (App Router)

**Primary Dependencies**: Tailwind CSS 4 (styling), Vitest 2 + @testing-library/react 16 (tests)

**Storage**: N/A — no new persistence; auth tokens follow the existing localStorage pattern established by `apps/web/lib/auth.tsx`

**Testing**: Vitest + @testing-library/react (same as all other web tests)

**Target Platform**: Web browser (Next.js SSR/CSR hybrid)

**Project Type**: Web application — Next.js frontend page

**Performance Goals**: Page render < 500ms; authenticated-user redirect < 500ms (per SC-005)

**Constraints**: Must follow the conventions already established by `apps/web/app/login/page.tsx` exactly — same Tailwind class patterns, same auth hook usage, same `?redirect=` safety rules

**Scale/Scope**: 1 new page, 1 new API function, 1 type addition, 1 update to login page, 1 test file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | ✅ Pass | No domain logic in the page component; the page calls the existing `authRegister` (infrastructure) and `login` (auth context), keeping domain concerns in the backend |
| II. Separation of Concerns | ✅ Pass | Page component → auth context hook → api.ts → backend; each layer stays independent |
| III. Data Locality & Consent | ✅ Pass | No new local persistence; auth tokens stored exactly as the existing login flow (localStorage, already documented) |
| IV. Test-Driven Development | ✅ Pass | Tests written alongside implementation; coverage target ≥ 85% applies to Python — frontend coverage not mandated by constitution, but all functional paths will be covered per existing team practice |
| V. Quality Gates | ✅ Pass | Ruff/Black are Python-only; TypeScript/linting quality gates are addressed by `tsc --noEmit` and the existing CI checks |

No violations. Complexity Tracking table omitted.

## Project Structure

### Documentation (this feature)

```text
specs/006-user-registration/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── register-api.md  # Backend registration API contract
└── tasks.md             # Phase 2 output (speckit-tasks)
```

### Source Code (repository root)

```text
apps/web/
├── app/
│   ├── login/
│   │   └── page.tsx           # MODIFIED — add "Create account" link
│   └── register/
│       └── page.tsx           # NEW — registration form page
├── lib/
│   ├── api.ts                 # MODIFIED — add authRegister() function
│   └── types.ts               # MODIFIED — add RegisterCredentials type
└── tests/
    └── register.test.tsx      # NEW — Vitest + Testing Library tests
```

**Structure Decision**: Pure frontend feature; no backend changes. Follows the existing single-project frontend layout under `apps/web/`.

## Key Architectural Decisions

### 1. Auto-login after registration

The backend `POST /v1/auth/register` returns a user object but **no JWT tokens**. To authenticate the user immediately after registration, the page will call `login({ email, password })` from `useAuth()` right after a successful register response. The email and password values are already held in component state at that point. This reuses the existing auth infrastructure with zero new code in `lib/auth.tsx`.

### 2. Password strength scoring — no external library

The strength meter uses a simple inline scoring function (pure TypeScript, < 20 lines):

- `weak`: length < 8 (blocked anyway by validation)
- `medium`: length ≥ 8, only one character class (e.g., all lowercase)
- `strong`: length ≥ 12 OR length ≥ 8 with mixed character classes (uppercase + lowercase + digit or symbol)

This avoids adding a dependency for a feature that does not affect submission — the backend enforces only the 8-char minimum.

### 3. `?redirect=` safety — identical to login page

```
redirect && redirect.startsWith("/") && !redirect.startsWith("//")
```

Same predicate as `apps/web/app/login/page.tsx:49`. The guard prevents open-redirect attacks.

### 4. Form structure mirrors login page

Same Tailwind layout, same `role="alert"` for error messages, same `disabled={submitting}` pattern, same `noValidate` on the `<form>` element.
