# Phase 0 Research: Fix Empty Spaces List

No open `NEEDS CLARIFICATION` markers — the one material decision (backfill
strategy) was resolved during `/speckit-clarify`. This document records the
remaining implementation-approach decisions.

## Decision: Reuse the migration-0010 backfill pattern exactly

- **Decision**: Write migration `0013_backfill_space_memberships.py` as a
  data-only migration (`op.execute(BACKFILL_SQL)`), with `BACKFILL_SQL`
  exposed as a module-level constant so it can be tested directly against a
  real connection without an Alembic op context — identical structure to
  `0010_backfill_company_admin_memberships.py`.
- **Rationale**: This codebase already has exactly one precedent for "a
  required access record is missing for existing rows, backfill it" (migration
  0010, written for feature 036). Reusing its shape means the same review
  mental model applies, and its existing test (`test_migration_0010_backfill.py`)
  is a proven template for verifying idempotency and isolation against a real
  database.
- **Alternatives considered**: A Python/SQLAlchemy ORM-based data migration
  (loop over `Space` rows, call `SqlSpaceMembershipRepository.add()`) was
  considered. Rejected: slower for a bulk one-time operation, and inconsistent
  with the established raw-SQL precedent for this exact class of fix.

## Decision: Backfill targets are company admins, not a guessed "creator"

- **Decision**: For every space with zero `space_memberships` rows, insert an
  admin membership for every `company_memberships` row with `role='admin'` in
  that space's company.
- **Rationale**: `Space` has no creator/owner column (confirmed by reading the
  domain entity and the `spaces` table), so the original creator of a
  pre-existing orphaned space cannot be reconstructed. Company admins are the
  only role in this system already trusted with company-wide authority over
  spaces (mirrored by `can_manage_members`/`can_read_space_document`
  accepting an `is_company_admin` override elsewhere) — recorded explicitly
  here, in keeping with the clarification answer)
- **Alternatives considered**: Backfilling onto `companies.admin_user_id`
  only (single owner) was considered and rejected per the spec's edge case
  ("every admin... not just one arbitrarily chosen admin") — a company can
  have more than one `CompanyRole.ADMIN` member, and the bug locks all of them
  out equally.

## Decision: Creation-time grant happens inside `create_space`, not via a separate call

- **Decision**: `POST /v1/spaces` (`apps/api/tessera_api/routers/spaces.py:create_space`)
  creates the `Space` row, then immediately adds a `SpaceMembership(role=ADMIN,
  user_id=creator, space_id=created.id)` via `SqlSpaceMembershipRepository.add()`
  in the same request/session — mirroring how `create_company` already adds an
  admin `CompanyMembership` for the company creator in the same request.
- **Rationale**: Matches the one existing precedent in this codebase for
  "creating a container grants its creator membership" (`create_company`).
  No permission check is needed for this first membership — there is by
  definition no one to check permissions against yet, exactly as
  `create_company` doesn't call any membership service for the first admin.
- **Alternatives considered**: Routing through `MembershipService.invite`
  was considered and rejected — `invite` requires `can_manage_members` to
  already return true for the actor, which is circular for the very first
  membership on a brand new space (no memberships exist yet to grant that
  permission).

## Decision: Audit logging

- **Decision**: The creation-time grant calls `write_audit` (the same helper
  already used elsewhere in `spaces.py`/`members.py`) with action
  `"member_invited"` — consistent with how every other space-membership
  creation in this codebase is audited (`MembershipService.invite`).
  The migration backfill does **not** write `audit_log` rows.
- **Rationale**: Constitution Security Requirements mandates an audit trail
  for "every state-changing action" at the *application* layer. The
  precedent migration (`0010`) — the only existing example of this class of
  fix — does not audit its bulk backfill either; a one-time, reviewed,
  version-controlled migration is its own audit trail (git history + deploy
  log), consistent with existing practice.
