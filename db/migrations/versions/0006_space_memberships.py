"""Add space_memberships table

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-21
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "space_memberships",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "space_id",
            UUID(as_uuid=True),
            sa.ForeignKey("spaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column(
            "invited_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("space_id", "user_id", name="uq_space_membership"),
    )
    op.create_index("ix_space_memberships_space", "space_memberships", ["space_id"])
    op.create_index("ix_space_memberships_user", "space_memberships", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_space_memberships_user", table_name="space_memberships")
    op.drop_index("ix_space_memberships_space", table_name="space_memberships")
    op.drop_table("space_memberships")
