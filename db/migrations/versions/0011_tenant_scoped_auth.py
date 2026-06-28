"""Add tenant-scoping columns to refresh_tokens and is_active to companies (feature 039)

Adds:
- refresh_tokens.company_id UUID FK → companies (nullable; NULL for select/onboarding tokens)
- refresh_tokens.token_kind VARCHAR(20) NOT NULL DEFAULT 'full'
- companies.is_active BOOLEAN NOT NULL DEFAULT TRUE
- index ix_refresh_tokens_company on refresh_tokens(company_id) WHERE company_id IS NOT NULL

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column("company_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_refresh_tokens_company_id",
        "refresh_tokens",
        "companies",
        ["company_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "refresh_tokens",
        sa.Column(
            "token_kind",
            sa.String(20),
            nullable=False,
            server_default="full",
        ),
    )
    op.create_index(
        "ix_refresh_tokens_company",
        "refresh_tokens",
        ["company_id"],
        postgresql_where=sa.text("company_id IS NOT NULL"),
    )
    op.add_column(
        "companies",
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("companies", "is_active")
    op.drop_index("ix_refresh_tokens_company", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "token_kind")
    op.drop_constraint("fk_refresh_tokens_company_id", "refresh_tokens", type_="foreignkey")
    op.drop_column("refresh_tokens", "company_id")
