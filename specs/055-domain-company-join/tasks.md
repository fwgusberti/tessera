---
description: "Task list for Domain-Based Company Matching on Sign-Up"
---

# Tasks: Domain-Based Company Matching on Sign-Up

**Input**: Design documents from `/specs/055-domain-company-join/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/domain-matching.md

**Tests**: REQUIRED. Constitution Principle IV (Test-Driven Development) is
non-negotiable for this repo, so every code change is written test-first.

**Organization**: Grouped by user story. Note the key finding from planning —
the entire join/approve flow and the whole frontend already exist and work; the
only production change is making companies *matchable* by their domain. Most of
this feature is therefore the enabler (US3) plus tests that lock in the existing
behavior US1/US2 depend on.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 / US2 / US3 (maps to spec.md user stories)

## Path Conventions

Monorepo: domain logic in `packages/core/tessera_core/domain/`, API in
`apps/api/tessera_api/`, tests in `packages/core/tests/` and `apps/api/tests/`,
migrations in `db/migrations/versions/`. Frontend `apps/web/` is **not modified**.

---

## Phase 1: Setup

**Purpose**: Confirm the working baseline before changing anything.

- [X] T001 Confirm branch `055-domain-company-join` is checked out and the backend test env runs: `pytest apps/api/tests/integration/test_companies.py -q` and `pytest packages/core/tests -q` are green (ignore the known-unrelated failures `test_ports`, `test_migration_0002`, `tessera_mcp`, and the unreachable global 85% API-coverage gate per the test-env baseline).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The public-email-domain business rule that US3 (and isolation
tests) depend on. Pure domain logic, per Constitution Principle I.

**⚠️ CRITICAL**: Must complete before US3 implementation.

- [X] T002 [P] Write failing unit tests for the email-domain classifier in `packages/core/tests/test_email_domain.py`: `extract_domain()` (lowercase, strip, substring after last `@`, `""` when no `@`) and `is_public_email_domain()` (True for gmail.com/outlook.com/etc., False for `acme.example`, case-insensitive, tolerates a leading `@`).
- [X] T003 Implement `packages/core/tessera_core/domain/email_domain.py` with `extract_domain(email)` and `is_public_email_domain(domain)` backed by the curated frozenset from research.md Decision 3; make T002 green. (Depends on T002.)
- [X] T004 [P] Re-export `extract_domain` and `is_public_email_domain` from `packages/core/tessera_core/domain/entities.py` (add to imports and `__all__`) so the API layer imports them consistently. (Depends on T003.)

**Checkpoint**: Classifier available and tested.

---

## Phase 3: User Story 3 - A company becomes matchable by its email domain (Priority: P1) 🎯 ENABLER

**Goal**: Creating a company auto-associates the founder's non-public email
domain (`request_approval`, `verified=true`); public domains never associate;
already-claimed domains are skipped without error; existing companies are
backfilled. This is the actual bug fix.

**Independent Test**: Create a company as `founder@acme.example` → a
`request_approval`/`verified` domain policy for `acme.example` exists; create one
as `founder@gmail.com` → no policy; run the backfill against seeded legacy
companies → each gets its admin's non-public domain (earliest company wins on a
shared domain).

### Tests for User Story 3 ⚠️ (write first, ensure they FAIL)

- [X] T005 [P] [US3] Failing integration tests in `apps/api/tests/integration/test_company_domain_association.py`: (a) `POST /v1/companies` with a non-public founder email creates exactly one `DomainJoinPolicy{policy: request_approval, verified: true}` and emits a `company.domain_auto_associated` audit record; (b) a public founder email creates no policy; (c) a founder email whose domain is already claimed returns 201 with no new policy; (d) `POST /v1/companies/{id}/domain-policies` with `domain: "gmail.com"` returns `422 public_domain_not_allowed` and writes nothing.
- [X] T006 [P] [US3] Failing migration test in `apps/api/tests/integration/test_migration_0016_backfill_company_domains.py`: seed companies with admins on non-public, public, and shared domains; after running migration `0016`, assert non-public unclaimed companies gain a `request_approval`/`verified` policy, public-domain companies gain none, and on a shared domain only the earliest-created company is associated.

### Implementation for User Story 3

- [X] T007 [US3] Add the domain auto-association side effect to `create_company` in `apps/api/tessera_api/routers/companies.py`: after company + admin membership, compute `d = extract_domain(email)`; if `d` non-empty, `not is_public_email_domain(d)`, and `SqlDomainPolicyRepository.get_by_domain(d)` is None, create `DomainJoinPolicy(company_id, domain=d, policy=REQUEST_APPROVAL, verified=True)` and `write_audit(action="company.domain_auto_associated", ...)`; tolerate `IntegrityError` (race) by rolling that write back without failing creation. Update the existing `test_create_company_returns_201` expectation to allow the new side effect (or switch its fixture email to a public domain). Make T005 (a)(b)(c) green. (Depends on T003, T005.)
- [X] T008 [US3] Add a public-domain guard at the top of `create_domain_policy` in `apps/api/tessera_api/routers/companies.py`: if `is_public_email_domain(body.domain.lower().lstrip("@"))`, raise `422` with `{"error": {"code": "public_domain_not_allowed", ...}}` before any DB write or verification email. Make T005 (d) green. (Depends on T003; same file as T007 — run after it.)
- [X] T009 [P] [US3] Create the data-only migration `db/migrations/versions/0016_backfill_company_domains.py` (`revision = "0016"`, `down_revision = "0015"`), modeled on `0013_backfill_space_memberships.py`: for each company lacking a domain policy, associate its `admin_user`'s email domain when non-public and unclaimed (`request_approval`, `verified=true`), earliest company winning per shared domain; idempotent. Make T006 green. (Depends on T006; different file — parallel with T008.)

**Checkpoint**: Companies are now matchable; the reported bug's root cause is fixed.

---

## Phase 4: User Story 1 - Join an existing company by matching email domain (Priority: P1)

**Goal**: A new user on a matched non-public domain is shown the company and can
request to join → lands in "waiting for approval" with no new company created.
No production code beyond US3 — the suggestions/join endpoints and the
onboarding/pending frontend already implement this; these tasks lock it in and
prove isolation.

**Independent Test**: With a `verified` domain policy for company X, a new
`@X-domain` user sees X in `/suggestions` and `POST …/join {domain_match}`
returns `pending`; a `@other` user is never shown or able to join X.

### Tests for User Story 1 ⚠️

- [X] T010 [P] [US1] Integration tests in `apps/api/tests/integration/test_domain_match_join.py`: seed a `verified`/`request_approval` `DomainJoinPolicy` for company X; assert a same-domain user sees X in `GET /v1/companies/suggestions.domain_matches`, `POST /v1/companies/{X}/join {method: domain_match}` returns `200 {status: "pending"}` with a single `JoinRequest` (re-request stays one, no duplicate), no membership is created, and admin is notified; **isolation**: a `@other.example` user does not see X in suggestions and `POST /v1/companies/{X}/join {domain_match}` from them returns `404 no_domain_policy`; a public-domain user sees no match.

### Verification for User Story 1

- [ ] T011 [US1] Verify the onboarding UI end-to-end per quickstart.md steps 1–3 (no code change): founder creates company, a second same-domain registrant reaches `/onboarding/company`, sees the match as primary with "Create a new company" secondary, clicks Request Access, and is routed to `/onboarding/pending` with no duplicate company. Confirms existing `apps/web/app/onboarding/company/page.tsx` and `apps/web/app/onboarding/pending/page.tsx` behavior. (Depends on T007, T009.)

**Checkpoint**: New users are routed to request-to-join instead of creating duplicates.

---

## Phase 5: User Story 2 - Administrator approves or rejects a join request (Priority: P1)

**Goal**: Admin can approve (→ member) or reject a pending request; decided
requests are not re-actionable; non-admins are blocked. Fully implemented
already — this task locks in the behavior US1 depends on.

**Independent Test**: Seed a pending `JoinRequest`; admin approve → requester
becomes member + notified; admin deny → denied + notified; approve/deny an
already-decided request → 409; non-admin → 403.

### Tests for User Story 2 ⚠️

- [X] T012 [P] [US2] Integration tests in `apps/api/tests/integration/test_join_request_admin.py` (extend existing coverage if equivalent already present, don't duplicate): admin `GET /v1/companies/{id}/join-requests` lists the pending request with requester name/email; `POST …/approve` creates a `member` `CompanyMembership`, notifies the requester, writes the `company.join_request_approved` audit; approving an already-decided request returns `409 already_decided`; `POST …/deny` marks it denied and notifies; a non-admin calling list/approve/deny receives `403`.

**Checkpoint**: The full request → approval → membership loop is verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T013 [P] Run Ruff and Black on all changed files under `packages/core/` and `apps/api/` and fix violations (Constitution Principle V).
- [X] T014 [P] Confirm the new/changed lines (`email_domain.py`, `create_company`/`create_domain_policy` branches, migration `0016`) are covered by the tests above; validate by targeted coverage rather than the unreachable global 85% API gate (per test-env baseline).
- [ ] T015 Run quickstart.md automated suites and manual validation end-to-end, including the backfill check that a pre-existing `@gusba.dev` company gains a `gusba.dev` policy so the next `@gusba.dev` registrant is matched. (Depends on all prior phases.)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: after Setup. Blocks US3.
- **US3 (Phase 3)**: after Foundational. The enabler — US1's e2e verification and the real-world flow depend on it.
- **US1 (Phase 4)**: test task T010 is independent (seeds its own policy) and can run right after Foundational; verification T011 depends on US3 (T007, T009).
- **US2 (Phase 5)**: independent (seeds its own pending request); can run any time after Setup.
- **Polish (Phase 6)**: after all desired stories.

### Within Each Story

- Tests written first and must FAIL before implementation (TDD).
- T007 before T008 (same file). T009 parallel to T008 (different file).

### Parallel Opportunities

- T002 and T004 (different files, T004 after T003).
- T005, T006 (different test files) in parallel; T009 parallel with T008.
- T010 and T012 (different test files) in parallel, and independent of US3, so can be written up front.
- T013, T014 in parallel during polish.

---

## Parallel Example: Foundational + US3 tests

```bash
# After T001, write the failing tests in parallel (different files):
Task: "T002 email-domain classifier unit tests in packages/core/tests/test_email_domain.py"
Task: "T005 create_company auto-association + guard tests in apps/api/tests/integration/test_company_domain_association.py"
Task: "T006 backfill migration test in apps/api/tests/integration/test_migration_0016_backfill_company_domains.py"
Task: "T010 domain-match join + isolation tests in apps/api/tests/integration/test_domain_match_join.py"
Task: "T012 join-request admin tests in apps/api/tests/integration/test_join_request_admin.py"
```

---

## Implementation Strategy

### MVP (fixes the reported bug)

1. Phase 1 Setup → Phase 2 Foundational (classifier).
2. Phase 3 US3 (auto-association + public guard + backfill) — **this is the fix**: companies become matchable and duplicate-creation stops.
3. Phase 4 US1 verification — confirms new users are routed to request-to-join.
   → At this point the reported scenario is resolved end-to-end.

### Complete the loop

4. Phase 5 US2 — confirms admins can admit requesters (already implemented; lock it in).
5. Phase 6 Polish — lint, coverage of changed lines, quickstart validation incl. backfill.

### Notes

- No frontend changes; `apps/web` is untouched.
- No schema changes; migration `0016` is data-only backfill.
- Keep tenant isolation intact — the domain lookup is self-referential to the caller's own email domain (see plan.md Tenant Isolation section); T010's isolation assertions guard it.
