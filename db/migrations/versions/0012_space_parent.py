"""Add parent_space_id FK to spaces table (feature 041)

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "spaces",
        sa.Column(
            "parent_space_id",
            UUID(as_uuid=True),
            sa.ForeignKey("spaces.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_spaces_parent_space_id", "spaces", ["parent_space_id"])


def downgrade() -> None:
    op.drop_index("ix_spaces_parent_space_id", table_name="spaces")
    op.drop_column("spaces", "parent_space_id")
