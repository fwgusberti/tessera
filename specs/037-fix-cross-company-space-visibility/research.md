# Phase 0 Research: Confine Space Visibility to the Active Company

This feature has no open NEEDS CLARIFICATION items — the spec plus the existing codebase
fully determine the approach. Research below records the root-cause analysis and the two
design decisions it produced.

## Root-cause analysis: where the reproduction comes from

The spec's reproduction table:

| Person (active company) | Sees today | Should see |
| ----------------------- | ---------- | ---------- |
| felipe@gusba.dev (Gusba Dev) | A, B, **C** | A, B |
| a@2.com (Company 2)     | **none**   | C |
| a@3.com (Company 3)     | **A, B, C**| none |

Tracing the space-listing surfaces:

- `GET /v1/spaces` (everyday view) → `SqlSpaceRepository.list_by_company(company_id)`
  — already correctly scoped since feature 031 (`WHERE spaces.company_id = :active`).
  A caller scoped to one company **cannot** receive a superset of their own spaces from
  this path, so it is *not* the source of "felipe sees A, B, **C**".
- `search.py`, `assistant.py`, `documents.py` → all resolve the company's space set via
  `list_by_company(company_id)`. Scoped.
- `GET /v1/admin/spaces` → `list_all()` under the global `is_admin` gate — the legitimate,
  separate platform-operator surface (feature 035/036). Used only by `app/admin/page.tsx`.
- `SpaceRepository.list_for_user(user)` → the only **unscoped** path:

  ```python
  if user.is_admin:        return await self.list_all()          # all companies
  if not user.groups:      return []
  # else: join role_permissions by idp_group across ALL companies, no company_id filter
  ```

These three branches are an exact, line-for-line match for the reproduction:
global-admin → everything (a@3.com); group match without company filter → another
company's space leaks in (felipe → C); no matching group → empty even for one's own
company (a@2.com). `list_for_user` is the encoded form of the bug.

**Reachability**: `list_for_user` has no caller anywhere in the repo outside its own
definition and the abstract port declaration (verified by grep across all apps, excluding
vendored venvs). It is dead in the request path today — but it is a published method on
the domain `SpaceRepository` port, i.e. a sanctioned, unscoped multi-tenant query that a
future caller could wire in one line. Constitution Principle VI prohibits exactly this
("Unscoped queries on multi-tenant tables are PROHIBITED"; "Methods that omit tenant
scoping MUST be rejected in code review").

## Decision 1 — Remove `list_for_user` rather than scope it

- **Decision**: Delete `list_for_user` from the `SpaceRepository` port
  (`packages/core/.../ports/repositories.py`) and from `SqlSpaceRepository`
  (`apps/api/.../adapters/repo.py`). The everyday visibility path becomes
  `list_by_company(company_id)` with no alternative.
- **Rationale**: The method's entire purpose — "spaces this *user* can see" — is the
  wrong question in a multi-tenant product; the right question is "spaces this user's
  *active company* owns," which `list_by_company` already answers. Scoping `list_for_user`
  by `company_id` would just reproduce `list_by_company` while keeping the dangerous
  `is_admin → list_all` branch alive. Removing it eliminates the leak mechanism at the
  source (FR-001, FR-003, FR-004) and shrinks the port's tenant-unsafe surface to zero.
- **Alternatives considered**:
  - *Add a `company_id` filter to `list_for_user`* — rejected: leaves a near-duplicate
    of `list_by_company` and preserves the `is_admin` shortcut; more code, same risk.
  - *Leave it (it's dead)* — rejected: it is a live entry in the domain port contract;
    Principle VI requires unscoped methods to be removed, not tolerated because no caller
    exists *yet*. SC-003 demands isolation be verified on "every space access path."
  - *Keep the method but raise/guard at runtime* — rejected: a deleted query cannot leak;
    a guarded one can be mis-guarded.

## Decision 2 — Make the platform-operator surface explicitly audited

- **Decision**: Keep `list_all()` and the `/v1/admin/*` space endpoints as the single
  documented cross-tenant exception, gated by global `is_admin`, but add a
  `cross_company_admin_access` audit emission to `list_all_spaces`,
  `update_retention_policy`, and `bulk_reindex` (recording actor, action, and the
  cross-company scope). The everyday `cross_tenant_denied` audit on by-ID misses (036) is
  retained unchanged.
- **Rationale**: FR-008 permits a cross-company capability only if it is "a clearly
  separate, audited surface"; FR-009 and the constitution's Security Requirements mandate
  a structured audit record for state-changing actions and for auditability of
  cross-company attempts. Today these endpoints read/modify across tenants with no audit
  trail, so the exception is not provably "audited." Emitting a dedicated action makes the
  exception observable and keeps it visibly distinct from the company-member view.
- **Alternatives considered**:
  - *Reuse `cross_tenant_denied`* — rejected: that action means a *denied* attempt; this
    is an *authorized* cross-company operator action and needs its own, non-alarming
    action name for clean audit queries.
  - *Audit only the read (`GET /admin/spaces`)* — rejected: the state-changing operator
    endpoints (retention, reindex) are exactly the ones the constitution most requires to
    be audited; all three get the emission.

## Decision 3 — No schema change, no migration

- **Decision**: Touch no DDL and add no Alembic migration.
- **Rationale**: Spec Assumption 3 — spaces already record `company_id` and it is indexed.
  Correct scoping is a query/contract concern. 036 introduced migration 0010 (data-only)
  for admin backfill; 037 needs no data backfill — owners and members already resolve
  their company via existing memberships, and the everyday query is already correct. The
  fix is removal + tests + audit emission.
- **Alternatives considered**: *Add Postgres RLS as defense-in-depth* — noted as a
  constitution follow-up TODO (v1.4.0 sync report), but out of scope here: it is a
  cross-cutting infra change, not part of confining space visibility, and would warrant
  its own feature.

## Test-strategy note (TDD)

Tests are written failing-first **before** the removal: the per-path isolation tests and
the reproduction test assert the corrected behavior and fail while `list_for_user`'s
semantics (or any unaudited operator read) remain reachable; they pass once the method is
removed and the audit emission is added. The existing `legacy_global_admin_setup` fixture
(global `is_admin` in Company A, a space in Company B, no membership in B) is reused
directly — it is the felipe/a@3 scenario in fixture form. A new three-company fixture
adds the literal A/B/C reproduction for SC-002.
