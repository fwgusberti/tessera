"""Backfill space memberships for orphaned spaces (feature 042)

Data-only migration (no DDL). For every ``spaces`` row that currently has
zero ``space_memberships`` rows, insert an admin membership for every
``company_memberships`` row with ``role='admin'`` in that space's company.

This closes the gap left by feature 041, which made space visibility depend
entirely on explicit ``space_memberships`` rows: spaces created before that
change (and any space whose creator never received a membership — see
migration scope note below) were left with no recorded members and were
therefore invisible to everyone, including their company's admins.

Policy (Session 2026-06-30 clarification, feature 042):
- Insert an admin membership ONLY for spaces with NO existing membership rows
  at all (``WHERE NOT EXISTS``) — never alter or duplicate access that
  already legitimately exists on a space.
- Grant EVERY company admin, not just one — a company can have more than one
  ``CompanyRole.ADMIN`` member, and the bug locked all of them out equally.
- A space whose company has zero admin memberships is left with zero
  inserted rows rather than erroring (FR-006); a warning listing the
  remaining orphaned-space count is logged so the condition is surfaced
  rather than silently dropped.

The insert is idempotent (``ON CONFLICT ... DO NOTHING`` on the existing
``uq_space_membership(space_id, user_id)`` constraint) and safe to re-run.

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-30
"""

import logging

from alembic import op
from sqlalchemy import text

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")

# Exposed as a module constant so the backfill can be tested directly against a
# connection without an Alembic op context (see
# test_migration_0013_backfill_space_memberships.py).
BACKFILL_SQL = """
    INSERT INTO space_memberships (space_id, user_id, role)
    SELECT s.id, cm.user_id, 'admin'
    FROM spaces s
    JOIN company_memberships cm
      ON cm.company_id = s.company_id AND cm.role = 'admin'
    WHERE NOT EXISTS (
        SELECT 1 FROM space_memberships sm WHERE sm.space_id = s.id
    )
    ON CONFLICT (space_id, user_id) DO NOTHING
"""

REMAINING_ORPHANED_SPACES_SQL = """
    SELECT count(*) FROM spaces s
    WHERE NOT EXISTS (
        SELECT 1 FROM space_memberships sm WHERE sm.space_id = s.id
    )
"""


def upgrade() -> None:
    op.execute(BACKFILL_SQL)

    bind = op.get_bind()
    remaining = bind.execute(text(REMAINING_ORPHANED_SPACES_SQL)).scalar_one()
    if remaining:
        logger.warning(
            "%d space(s) remain without any space_membership after backfill — "
            "their company has no admin membership to grant access to (FR-006)",
            remaining,
        )


def downgrade() -> None:
    # No-op: backfilled rows are indistinguishable from organically-created
    # admin memberships, and removing them would be unsafe (re-introduces the
    # original bug for every affected space).
    pass
