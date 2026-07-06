"""Add invitations.role and a partial unique index on pending invitations (feature 054)

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-05
"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Role the invitee is granted on acceptance. Existing rows (and the legacy
    # bulk POST /invitations) backfill to 'member' via the server default.
    op.add_column(
        "invitations",
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
    )
    # At most one outstanding invitation per email per company (case-insensitive).
    # A concurrent second invite trips this and maps to the "already invited" outcome.
    op.create_index(
        "uq_invitation_pending_email",
        "invitations",
        ["company_id", sa.text("lower(email)")],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("uq_invitation_pending_email", table_name="invitations")
    op.drop_column("invitations", "role")
