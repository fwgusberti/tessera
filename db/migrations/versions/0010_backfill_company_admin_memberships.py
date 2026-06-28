"""Backfill company-admin memberships for company owners (feature 036)

Data-only migration (no DDL). For every ``companies`` row, ensure a
``company_memberships`` row exists with ``role='admin'`` for the company's
``admin_user_id`` (the creator/owner). This guarantees no owner loses authority
when the global ``users.is_admin`` flag stops conferring it (FR-009, SC-007).

Policy (Session 2026-06-26 clarification):
- Insert an admin membership ONLY when the owner has no membership row at all.
- NEVER elevate an existing ``role='member'`` row to admin.
- NEVER touch ``users.is_admin`` (retained for platform-operator endpoints).

The insert is idempotent (``WHERE NOT EXISTS``) and safe to re-run. ``id`` and
``joined_at`` come from the table's server defaults (gen_random_uuid() / now()).

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-26
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

# Exposed as a module constant so the backfill can be tested directly against a
# connection without an Alembic op context (see test_migration_0010_backfill.py).
BACKFILL_SQL = """
    INSERT INTO company_memberships (user_id, company_id, role)
    SELECT c.admin_user_id, c.id, 'admin'
    FROM companies c
    WHERE NOT EXISTS (
        SELECT 1 FROM company_memberships m
        WHERE m.company_id = c.id
          AND m.user_id = c.admin_user_id
    )
"""


def upgrade() -> None:
    op.execute(BACKFILL_SQL)


def downgrade() -> None:
    # No-op: backfilled rows are indistinguishable from organically-created owner
    # memberships, and removing owner admin access would be unsafe (FR-009).
    pass
