"""Add company_id to spaces

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-22
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: add column as nullable
    op.add_column(
        "spaces",
        sa.Column("company_id", UUID(as_uuid=True), nullable=True),
    )

    # Step 2: backfill existing rows to the oldest company's id
    op.execute("""
        UPDATE spaces
        SET company_id = (
            SELECT id FROM companies ORDER BY created_at ASC LIMIT 1
        )
        WHERE company_id IS NULL
          AND EXISTS (SELECT 1 FROM companies LIMIT 1)
    """)

    # Step 3: add NOT NULL constraint
    op.alter_column("spaces", "company_id", nullable=False)

    # Step 4: add FK constraint and index
    op.create_foreign_key(
        "fk_spaces_company_id",
        "spaces",
        "companies",
        ["company_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_spaces_company", "spaces", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_spaces_company", table_name="spaces")
    op.drop_constraint("fk_spaces_company_id", "spaces", type_="foreignkey")
    op.drop_column("spaces", "company_id")
