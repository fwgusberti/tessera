"""Add company_id to onboarding_progress

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-22
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "onboarding_progress",
        sa.Column("company_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_onboarding_progress_company_id",
        "onboarding_progress",
        "companies",
        ["company_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_onboarding_progress_company_id", "onboarding_progress", type_="foreignkey")
    op.drop_column("onboarding_progress", "company_id")
