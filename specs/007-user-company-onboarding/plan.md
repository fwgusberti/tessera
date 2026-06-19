# Implementation Plan: User & Company Onboarding Flow

**Branch**: `007-user-company-onboarding` | **Date**: 2026-06-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-user-company-onboarding/spec.md`

## Summary

Implement a multi-step onboarding wizard that gates access to the Tessera app for all new users. The wizard collects a personal profile (name + title), establishes a company context (create / accept-invitation / domain-match), and optionally invites teammates. Company-creators see an invitation step; joiners skip directly to a tailored completion screen. Domain joining requires email-verified domain ownership; first-claim is globally unique. Pending join requests place the user in a holding screen until a company admin acts.

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript 5 / Next.js 15 / React 19 (frontend)

**Primary Dependencies**:
- API: FastAPI 0.115, SQLAlchemy 2.0, Alembic, Pydantic v2, bcrypt, joserfc, itsdangerous, structlog, `fastapi-mail>=1.4` *(new)*
- Frontend: Next.js 15, React 19, Tailwind CSS 4, Vitest

**Storage**: PostgreSQL — 5 new tables (`companies`, `company_memberships`, `domain_join_policies`, `invitations`, `onboarding_progress`); 2 new columns on `users` (`title`, `onboarding_completed`)

**Testing**: pytest (≥85% coverage, TDD-first), Vitest + Testing Library (frontend)

**Target Platform**: Web browsers (desktop-first); API on Linux server

**Project Type**: Full-stack web application (FastAPI API + Next.js frontend, monorepo)

**Performance Goals**: Onboarding completion in <3 minutes average; each API step response in <300ms p95

**Constraints**: All persistent state in PostgreSQL; no client-side persistence of user data (Constitution III); audit log on every state-changing action (Constitution security); ≥85% Python test coverage (Constitution IV)

**Scale/Scope**: Per-user one-time flow; O(users) onboarding records; O(companies × domains) domain policies; O(invitations) — no unusual scale demands

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | ✅ PASS | New domain entities (`Company`, `CompanyMembership`, `DomainJoinPolicy`, `Invitation`, `OnboardingProgress`) are pure Pydantic in `packages/core/tessera_core/domain/entities.py`. ORM models in `apps/api/tessera_api/adapters/models.py`. No framework imports in domain layer. |
| II. Separation of Concerns | ✅ PASS | `EmailPort` abstract class in `packages/core/tessera_core/ports/`; concrete `FastMailEmailAdapter` in `apps/api`. Domain never imports `fastapi_mail`. |
| III. Data Locality & Consent | ✅ PASS | All onboarding state server-side in PostgreSQL. No local browser persistence of user profile or company data. |
| IV. Test-Driven Development | ✅ PASS | All new services and domain logic written test-first. pytest coverage ≥85% enforced by `pyproject.toml`. |
| V. Quality Gates | ✅ PASS | Ruff + Black checks enforced before commit. |
| Stack — Persistent storage | ✅ PASS | PostgreSQL for all new tables. No Cassandra or non-PostgreSQL store. |
| Stack — Caching/transport | ✅ N/A | No Redis usage in this feature. |
| Stack — IaC | ✅ PASS | New tables via Alembic migration (`0004_onboarding.py`); no undeclared infra. |
| Security — Auth | ✅ PASS | All new endpoints protected by existing JWT bearer dependency. Domain verification uses `itsdangerous` signed tokens. |
| Security — Secrets | ✅ PASS | SMTP credentials in env vars only. Verification tokens never committed. |
| Security — Audit log | ✅ PASS | `AuditRecord` emitted for: company created, invitation sent, domain policy created, domain verified, join request submitted/approved/denied, onboarding completed. |
| Docs separation | ✅ PASS | This plan holds all technical decisions. Spec holds WHAT/WHY only. |

**Post-design re-check**: All principles maintained. `fastapi-mail` is an infrastructure adapter, not a domain dependency — compliant with Principle II.

## Project Structure

### Documentation (this feature)

```text
specs/007-user-company-onboarding/
├── plan.md              # This file
├── research.md          # Phase 0 — technology decisions
├── data-model.md        # Phase 1 — entity definitions and migration plan
├── quickstart.md        # Phase 1 — end-to-end validation guide
├── contracts/
│   └── onboarding-api.md   # Phase 1 — REST API contracts
└── tasks.md             # Phase 2 output (/speckit-tasks — not yet created)
```

### Source Code

```text
packages/core/tessera_core/
├── domain/
│   └── entities.py            # +Company, CompanyMembership, DomainJoinPolicy,
│                              #  Invitation, OnboardingProgress; extend User
├── ports/
│   ├── repositories.py        # +CompanyRepository, InvitationRepository,
│   │                          #  OnboardingRepository, DomainPolicyRepository
│   └── providers.py           # +EmailPort (abstract email sender)

apps/api/tessera_api/
├── adapters/
│   ├── models.py              # +CompanyModel, CompanyMembershipModel,
│   │                          #  DomainJoinPolicyModel, InvitationModel,
│   │                          #  OnboardingProgressModel; extend UserModel
│   ├── repo.py                # +SqlCompanyRepository, SqlInvitationRepository,
│   │                          #  SqlOnboardingRepository, SqlDomainPolicyRepository
│   └── email.py               # FastMailEmailAdapter (concrete EmailPort)
├── routers/
│   ├── onboarding.py          # GET /status, POST /profile, POST /complete
│   ├── companies.py           # GET /suggestions, POST /, POST /{id}/join,
│   │                          #  GET /{id}/join-status, DELETE /{id}/join-request,
│   │                          #  GET /{id}/join-requests, POST /{id}/join-requests/{rid}/approve,
│   │                          #  POST /{id}/join-requests/{rid}/deny,
│   │                          #  POST /{id}/domain-policies,
│   │                          #  POST /{id}/domain-policies/{pid}/resend-verification
│   └── invitations.py         # POST /invitations
├── auth/
│   └── bearer.py              # extend: add require_onboarding_complete dependency
├── config.py                  # +SMTP env vars (MAIL_USERNAME, MAIL_PASSWORD,
│                              #  MAIL_FROM, MAIL_SERVER, MAIL_PORT, MAIL_SUPPRESS_SEND)
└── main.py                    # register companies, onboarding, invitations routers
                               # register domain-verify route (public)

db/migrations/versions/
└── 0004_onboarding.py         # New Alembic migration

apps/web/
├── app/
│   └── onboarding/
│       ├── layout.tsx         # OnboardingLayout with progress stepper
│       ├── page.tsx           # redirect to /onboarding/profile
│       ├── profile/
│       │   └── page.tsx       # Step 1
│       ├── company/
│       │   └── page.tsx       # Step 2 (create / join / suggestions)
│       ├── invite/
│       │   └── page.tsx       # Step 3 (creators only)
│       ├── complete/
│       │   └── page.tsx       # Step 4 completion screen
│       └── pending/
│           └── page.tsx       # Join-request holding screen
├── components/onboarding/
│   ├── ProgressStepper.tsx    # Step progress indicator
│   ├── CompanyForm.tsx        # New company creation form
│   ├── CompanySuggestions.tsx # Domain match + invitation suggestions
│   └── InviteForm.tsx         # Multi-email input for invitations
└── lib/
    ├── onboarding.ts          # API client for onboarding endpoints
    ├── companies.ts           # API client for company endpoints
    ├── invitations.ts         # API client for invitation endpoints
    └── auth-guard.tsx         # extend: OnboardingGuard wraps app layout
```

**Structure Decision**: Web application (backend + frontend). Backend follows the existing DDD layering: `packages/core` (domain + ports) → `apps/api/tessera_api/adapters` (infrastructure) → `apps/api/tessera_api/routers` (application). Frontend follows the existing Next.js App Router pattern with feature-scoped route groups.

## Complexity Tracking

> No constitution violations requiring justification.
