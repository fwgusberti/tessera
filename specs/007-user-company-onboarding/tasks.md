# Tasks: User & Company Onboarding Flow

**Input**: Design documents from `specs/007-user-company-onboarding/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/onboarding-api.md ✅, quickstart.md ✅

**Tests**: Included — required by Constitution Principle IV (TDD, NON-NEGOTIABLE). Write tests FIRST; confirm they fail before implementing.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Exact file paths included in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add new dependencies, config, and the Alembic migration file before any domain work begins.

- [x] T001 Add `fastapi-mail>=1.4` to `apps/api/pyproject.toml` dependencies
- [x] T002 Add SMTP env vars (`MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM`, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_SUPPRESS_SEND`) to `apps/api/tessera_api/config.py` settings class
- [x] T003 Write Alembic migration `db/migrations/versions/0004_onboarding.py` per data-model.md (ALTER users + CREATE companies, company_memberships, domain_join_policies, invitations, onboarding_progress tables with all indexes and constraints)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core domain entities, ORM models, port interfaces, email adapter, and route-guard — MUST be complete before any user story.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Extend `User` domain entity with `title: str | None` and `onboarding_completed: bool = False` fields in `packages/core/tessera_core/domain/entities.py`
- [x] T005 Add `CompanyRole` enum and `Company`, `CompanyMembership` domain entities in `packages/core/tessera_core/domain/entities.py`
- [x] T006 Add `DomainPolicy` enum and `DomainJoinPolicy` domain entity in `packages/core/tessera_core/domain/entities.py`
- [x] T007 Add `InvitationStatus` enum and `Invitation` domain entity in `packages/core/tessera_core/domain/entities.py`
- [x] T008 Add `JoinRequestStatus` enum and `OnboardingProgress` domain entity in `packages/core/tessera_core/domain/entities.py`
- [x] T009 Add `EmailPort` abstract class with `send_verification`, `send_invitation`, `send_join_request_notification`, `send_join_request_decision` abstract methods in `packages/core/tessera_core/ports/providers.py`
- [x] T010 Add `OnboardingRepository`, `CompanyRepository`, `DomainPolicyRepository`, `InvitationRepository` abstract port interfaces in `packages/core/tessera_core/ports/repositories.py`
- [x] T011 Extend `UserModel` with `title` and `onboarding_completed` columns; add `CompanyModel`, `CompanyMembershipModel`, `DomainJoinPolicyModel`, `InvitationModel`, `OnboardingProgressModel` ORM classes in `apps/api/tessera_api/adapters/models.py`
- [x] T012 [P] Implement `FastMailEmailAdapter` (concrete `EmailPort`) with async SMTP dispatch and dev-mode suppression in `apps/api/tessera_api/adapters/email.py`
- [x] T013 Add `require_onboarding_complete` FastAPI dependency (checks `OnboardingProgress.completed_at IS NOT NULL`; returns `403 onboarding_required` if not) in `apps/api/tessera_api/auth/bearer.py`; **exempt** `GET /v1/companies/{id}/join-status` and `DELETE /v1/companies/{id}/join-request` from this guard — users with a pending join request must be able to poll status and cancel from the holding screen before onboarding completes
- [x] T014 Register `onboarding`, `companies`, `invitations` routers and the public `GET /v1/domain-verify/{token}` route in `apps/api/tessera_api/main.py`; apply `require_onboarding_complete` to all existing non-auth/non-onboarding routers **except** join-status and join-request-cancel routes (see T013)
- [x] T015 Add `OnboardingGuard` component to `apps/web/lib/auth-guard.tsx` that calls `GET /v1/onboarding/status` and redirects to `/onboarding` if `completed: false`; wrap app layout in `apps/web/app/layout.tsx`

**Checkpoint**: Foundation ready — all domain entities exist, ORM tables are migrated, route guard is active, email adapter is wired.

---

## Phase 3: User Story 1 — Personal Profile Setup (Priority: P1) 🎯 MVP

**Goal**: New users are intercepted after first login and complete their name + role/title before accessing the app.

**Independent Test**: Register a new account → confirm redirect to `/onboarding/profile` → enter name → advance to company step → confirm `GET /v1/onboarding/status` returns `completed_steps: ["profile"]`.

> **TDD**: Write tests first (T016–T017). Confirm they FAIL. Then implement (T018–T024).

- [x] T016 [US1] Write failing unit tests for `SqlOnboardingRepository` (create, get, advance_step, complete) in `apps/api/tests/unit/test_onboarding_repo.py`
- [x] T017 [US1] Implement `SqlOnboardingRepository` in `apps/api/tessera_api/adapters/repo.py` (passes T016)
- [x] T018 [US1] Write failing integration tests for `GET /v1/onboarding/status`, `POST /v1/onboarding/profile`, `POST /v1/onboarding/complete` in `apps/api/tests/integration/test_onboarding.py`
- [x] T019 [US1] Implement `GET /v1/onboarding/status` (response includes `company_join_method: "created" | "joined" | null`), `POST /v1/onboarding/profile` (full_name required, title optional), `POST /v1/onboarding/complete` (sets both `OnboardingProgress.completed_at` AND `users.onboarding_completed = True` atomically) in `apps/api/tessera_api/routers/onboarding.py`
- [x] T020 [P] [US1] Create `ProgressStepper` component (shows completed/current/upcoming steps with visual indicator) in `apps/web/components/onboarding/ProgressStepper.tsx`
- [x] T021 [US1] Create `OnboardingLayout` using `ProgressStepper`; reads step from URL; renders step container in `apps/web/app/onboarding/layout.tsx`
- [x] T022 [US1] Create onboarding root redirect page (`/onboarding` → `/onboarding/profile`) in `apps/web/app/onboarding/page.tsx`
- [x] T023 [US1] Implement Step 1 profile page (full_name required field, title optional, calls `POST /v1/onboarding/profile`, advances to company step) in `apps/web/app/onboarding/profile/page.tsx`
- [x] T024 [US1] Create initial onboarding complete page (creator variant: shows profile name, company name, invitation count; "Go to Dashboard" button) in `apps/web/app/onboarding/complete/page.tsx`
- [x] T025 [US1] Create `onboarding.ts` API client (wrappers for `getStatus`, `saveProfile`, `completeOnboarding`) in `apps/web/lib/onboarding.ts`

**Checkpoint**: US1 complete — new users are gated to onboarding, can save profile, and see step progress. No company or invitation logic yet.

---

## Phase 4: User Story 2 — Company Setup (Priority: P2)

**Goal**: After profile, users create a new company or join an existing one via invitation or domain match. Domain admins can claim and verify a company email domain.

**Independent Test**: Complete profile → reach company step → create company → confirm `CompanyMembership` with `role=admin` exists → advance to invite step (creator path).

> **TDD**: Write tests first (T026, T028). Confirm they FAIL. Then implement.

- [x] T026 [US2] Write failing unit tests for `SqlCompanyRepository` (create, get, add_membership, get_membership) and `SqlDomainPolicyRepository` (create, get_by_domain, mark_verified) in `apps/api/tests/unit/test_company_repo.py`
- [x] T027 [US2] Implement `SqlCompanyRepository` in `apps/api/tessera_api/adapters/repo.py` (passes T026)
- [x] T028 [US2] Implement `SqlDomainPolicyRepository` in `apps/api/tessera_api/adapters/repo.py` (passes T026)
- [x] T029 [US2] Write failing integration tests covering create company, get suggestions (no match, domain match, pending invitation), join via invitation, join via domain (auto_join), join via domain (request_approval → pending), cancel join request, domain policy create + verify flow in `apps/api/tests/integration/test_companies.py`
- [x] T030 [US2] Implement `POST /v1/companies` (create company + membership as admin, auto-advance onboarding to `invite` step) in `apps/api/tessera_api/routers/companies.py`
- [x] T031 [US2] Implement `GET /v1/companies/suggestions` (queries pending invitations and verified domain matches for caller's email) in `apps/api/tessera_api/routers/companies.py`
- [x] T032 [US2] Implement `POST /v1/companies/{id}/join` (handles `method=invitation` → accept + create membership; `method=domain_match` → auto-join or create pending join request per policy) in `apps/api/tessera_api/routers/companies.py`
- [x] T033 [US2] Implement `GET /v1/companies/{id}/join-status` and `DELETE /v1/companies/{id}/join-request` (cancel join request, returns user to company step) in `apps/api/tessera_api/routers/companies.py`
- [x] T034 [US2] Implement `GET /v1/companies/{id}/join-requests`, `POST /v1/companies/{id}/join-requests/{rid}/approve`, `POST /v1/companies/{id}/join-requests/{rid}/deny` (admin-only) in `apps/api/tessera_api/routers/companies.py`
- [x] T035 [US2] Implement `POST /v1/companies/{id}/domain-policies` (creates policy, enforces UNIQUE domain, dispatches verification email via `EmailPort` using `itsdangerous` signed token) in `apps/api/tessera_api/routers/companies.py`
- [x] T036 [US2] Implement public `GET /v1/domain-verify/{token}` (validates `itsdangerous` token ≤24h, marks domain verified, redirects to `/settings/domain?verified=true` or `?error=expired`) and `POST .../resend-verification` in `apps/api/tessera_api/routers/companies.py`
- [x] T037 [US2] Dispatch admin notification email (join request submitted, FR-029) and user notification email (request approved/denied, FR-028) via `EmailPort` in `apps/api/tessera_api/routers/companies.py`
- [x] T038 [P] [US2] Create `CompanyForm` component (company name required, industry + team_size optional dropdowns) in `apps/web/components/onboarding/CompanyForm.tsx`
- [x] T039 [P] [US2] Create `CompanySuggestions` component (renders invitation cards and domain-match cards; prioritizes invitation over domain match for same company per FR-020) in `apps/web/components/onboarding/CompanySuggestions.tsx`
- [x] T040 [US2] Implement Step 2 company page (calls `GET /v1/companies/suggestions`; shows `CompanySuggestions` when matches exist; shows `CompanyForm` when creating; branches post-join to invite step or pending screen) in `apps/web/app/onboarding/company/page.tsx`
- [x] T041 [US2] Create pending approval holding screen (polls `GET /v1/companies/{id}/join-status`; shows status; offers "Cancel request" button calling `DELETE`; redirects on approve/deny) in `apps/web/app/onboarding/pending/page.tsx`
- [x] T042 [US2] Create `companies.ts` API client (wrappers for `getSuggestions`, `createCompany`, `joinCompany`, `getJoinStatus`, `cancelJoinRequest`) in `apps/web/lib/companies.ts`
- [x] T043 [US2] Update onboarding completion page to render joiner variant ("Welcome to [Company Name]") by reading `company_join_method` from `GET /v1/onboarding/status` response (value `"joined"` → joiner screen; `"created"` → creator screen); do NOT rely on URL query params or session state in `apps/web/app/onboarding/complete/page.tsx`

**Checkpoint**: US2 complete — users can create a company or join via invite/domain; domain verification works; pending requests show holding screen.

---

## Phase 5: User Story 3 + 4 — Team Invitation & Onboarding Completion (Priority: P3)

**Goal**: Company creators can send bulk email invitations to colleagues during Step 3. Both creator and joiner paths land on tailored completion screens and proceed to the dashboard.

**Independent Test (US3)**: Complete profile + create company as creator → reach invite step → send 2 emails → confirm `Invitation` records created with `status=pending`, `expires_at = now + 7 days`, and invitation emails dispatched.

**Independent Test (US4)**: Complete all steps → confirm `OnboardingProgress.completed_at` is set → confirm auth guard no longer blocks dashboard → confirm re-login skips onboarding.

> **TDD**: Write tests first (T044, T046). Confirm they FAIL. Then implement.

- [x] T044 [US3] Write failing unit tests for `SqlInvitationRepository` (create_bulk, get_by_token_hash, expire_stale, cancel) in `apps/api/tests/unit/test_invitation_repo.py`
- [x] T045 [US3] Implement `SqlInvitationRepository` in `apps/api/tessera_api/adapters/repo.py` (passes T044)
- [x] T046 [US3] Write failing integration tests for `POST /v1/invitations` (valid emails, duplicate deduplication, already-member error, >50 emails, invalid format) in `apps/api/tests/integration/test_invitations.py`
- [x] T047 [US3] Implement `POST /v1/invitations` (admin-only; validates emails; deduplicates; creates `Invitation` records with 7-day expiry; dispatches invitation emails via `EmailPort`; returns 207 multi-status) in `apps/api/tessera_api/routers/invitations.py`
- [x] T048 [P] [US3] Create `InviteForm` component (comma/newline-separated email textarea; client-side parse + validate + deduplicate; "Skip for now" button) in `apps/web/components/onboarding/InviteForm.tsx`
- [x] T049 [US3] Implement Step 3 invite page (shown only to creators; calls `POST /v1/invitations`; shows send confirmation or non-blocking error; "Skip" advances without sending) in `apps/web/app/onboarding/invite/page.tsx`
- [x] T050 [US3] Create `invitations.ts` API client (wrapper for `sendInvitations`) in `apps/web/lib/invitations.ts`
- [x] T051 [US3] Wire creator/joiner branching into onboarding page navigation: after company step, call `GET /v1/onboarding/status` and branch on `company_join_method` — `"created"` routes to `/onboarding/invite`; `"joined"` routes to `/onboarding/complete` (completion page reads join method from status API, not URL); update `POST /v1/companies` and `POST /v1/companies/{id}/join` to persist `company_join_method` on `OnboardingProgress` in `apps/web/app/onboarding/company/page.tsx`
- [x] T052 [US4] Confirm completion page handles both variants (creator: name + company + invite count; joiner: "Welcome to [Company]") and "Go to Dashboard" calls `POST /v1/onboarding/complete` then redirects to `/` in `apps/web/app/onboarding/complete/page.tsx`

**Checkpoint**: All 4 user stories complete — full onboarding flow works end-to-end for creators and joiners.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Audit logging, coverage validation, and end-to-end test confirmation.

- [x] T053 Add `write_audit` calls for every state-changing onboarding action (company created, invitation sent, domain policy created, domain verified, join request submitted/approved/denied, onboarding completed) in `apps/api/tessera_api/routers/onboarding.py`, `companies.py`, `invitations.py`
- [ ] T054 [P] Write frontend unit tests for `ProgressStepper`, `CompanyForm`, `CompanySuggestions`, `InviteForm` in `apps/web/tests/onboarding.test.tsx`
- [ ] T055 [P] Write frontend integration tests covering new-user redirect → profile → company-create → invite → complete flow in `apps/web/tests/onboarding-flow.test.tsx`
- [x] T056 Verify pytest coverage remains ≥85% for all new Python modules by running `uv run pytest --cov` in `apps/api/`; address any gaps
- [x] T057 Add email HTML/text templates for all 4 email types (domain verification, team invitation, join-request admin notification, join-request decision) in `apps/api/tessera_api/adapters/email.py`
- [ ] T058 Run all 7 quickstart scenarios from `specs/007-user-company-onboarding/quickstart.md` against the running dev environment and confirm each passes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Requires Phase 1 complete — BLOCKS all user stories
- **Phase 3 (US1)**: Requires Phase 2 complete — first deliverable / MVP
- **Phase 4 (US2)**: Requires Phase 3 complete (domain model built; onboarding router exists)
- **Phase 5 (US3+US4)**: Requires Phase 4 complete (company must exist before inviting)
- **Phase 6 (Polish)**: Requires Phases 3–5 complete

### User Story Dependencies

- **US1 (P1)**: Unblocks everything; implements onboarding gate and profile step
- **US2 (P2)**: Depends on US1 (onboarding progress must exist); builds company entities
- **US3 (P3)**: Depends on US2 (company must exist; only creators see invite step)
- **US4 (P3)**: Completion screen evolves across US1→US2→US3; finalized in Phase 5

### Within Each Phase

- TDD tasks (unit tests, integration tests) MUST be written and confirmed FAILING before implementation tasks
- Domain entity tasks before ORM model tasks
- ORM model tasks before repository tasks
- Repository tasks before router tasks
- Backend router tasks before frontend page tasks
- Component tasks (`[P]`) can run in parallel with each other

---

## Parallel Opportunities

### Phase 2 — Foundational

```
T004 (extend User entity)
  → T005 (Company entities)     [P with T006, T007]
  → T006 (DomainJoinPolicy)     [P with T005, T007]
  → T007 (Invitation + OnboardingProgress) [P with T005, T006]
  → T008 (EmailPort)            [P - different file]
  → T009 (repo port interfaces) [P - different file]
  ↓
T011 (ORM models — all in one file, sequential)
T012 (email adapter [P]) + T013 (bearer guard) can run in parallel
```

### Phase 3 — US1

```
T016 → T017 (repo unit tests + impl, sequential)
T018 → T019 (integration tests + router, sequential)

T020 (ProgressStepper [P]) ─┐
T021 (OnboardingLayout)    ←┘ (T020 done first or concurrent)
T022 (onboarding page.tsx [P])
T023 (profile page)
T024 (complete page [P])
T025 (onboarding.ts client [P])
```

### Phase 4 — US2

```
T026 → T027 → T028 (tests → CompanyRepo → DomainPolicyRepo)
T029 → T030–T037 (integration tests → router endpoints)
T038 (CompanyForm [P]) ─┐
T039 (CompanySuggestions [P]) ─┤ all parallel
T042 (companies.ts [P]) ──────┘
T040 (company page — needs T038, T039, T042)
T041 (pending page)
```

### Phase 5 — US3+US4

```
T044 → T045 (invitation repo tests + impl)
T046 → T047 (invitation integration tests + router)
T048 (InviteForm [P])
T050 (invitations.ts [P])
T049 (invite page — needs T048, T050)
```

---

## Implementation Strategy

### MVP First (User Story 1 + gate only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (all domain entities, ORM, guard)
3. Complete Phase 3: US1 (profile step + onboarding gate)
4. **STOP and VALIDATE**: New users are blocked until profile is saved; existing users reach dashboard normally
5. Demo/merge MVP increment

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. + US1 (Phase 3) → Onboarding gate + profile step live
3. + US2 (Phase 4) → Company creation + domain/invite joining live
4. + US3+US4 (Phase 5) → Invitation sending + completion screens live
5. + Polish (Phase 6) → Audit logs, coverage, templates, quickstart validated

### Parallel Team Strategy

After Phase 2 completes:
- **Developer A**: Phase 3 (US1 — profile, status, onboarding guard frontend)
- **Developer B**: Phase 4 domain model work (T026–T028, company repos)
- **Developer C**: Frontend components (T038, T039 — CompanyForm, CompanySuggestions)

---

## Notes

- Constitution IV (TDD) is non-negotiable: every `test_` file listed must be written and confirmed FAILING before the matching implementation task runs
- `[P]` tasks operate on distinct files and have no incomplete task dependencies — safe to run in parallel
- `[Story]` label enables traceability from task → spec user story → acceptance scenario
- Each phase checkpoint should be validated before moving to the next phase
- `write_audit` calls are deferred to Phase 6 to avoid bloating each router during initial TDD cycles — add them in T053 once all routers are stable
- Invitation expiry (7 days) and domain verification link expiry (24h) are enforced at query time and token validation time respectively — no background job needed for MVP
