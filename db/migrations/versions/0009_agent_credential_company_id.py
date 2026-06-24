"""Add company_id to agent_credentials

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_credentials",
        sa.Column("company_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_agent_credentials_company_id",
        "agent_credentials",
        "companies",
        ["company_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_agent_credentials_company",
        "agent_credentials",
        ["company_id"],
    )
    # Backfill: for credentials with at least one scoped space, adopt the
    # company of the first scoped space. Rows with no scoped spaces stay NULL.
    op.execute("""
        UPDATE agent_credentials ac
        SET company_id = (
            SELECT s.company_id
            FROM spaces s
            WHERE s.id = ac.scoped_space_ids[1]
        )
        WHERE array_length(ac.scoped_space_ids, 1) >= 1
        """)


def downgrade() -> None:
    op.drop_index("ix_agent_credentials_company", table_name="agent_credentials")
    op.drop_constraint("fk_agent_credentials_company_id", "agent_credentials", type_="foreignkey")
    op.drop_column("agent_credentials", "company_id")
