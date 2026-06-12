"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("external_subject", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("groups", sa.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("default_language", sa.String(10), nullable=False, server_default="pt-BR"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "spaces",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sector", sa.String(100), nullable=False),
        sa.Column("taxonomy", JSONB, nullable=False, server_default="{}"),
        sa.Column("retention_policy", JSONB, nullable=False, server_default="{}"),
        sa.Column("confidence_threshold", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("default_language", sa.String(10), nullable=False, server_default="pt-BR"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "role_permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("space_id", UUID(as_uuid=True), sa.ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("idp_group", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("max_confidentiality", sa.String(50), nullable=False, server_default="internal"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("space_id", "idp_group", name="uq_space_group"),
    )

    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("space_id", UUID(as_uuid=True), sa.ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("language", sa.String(10), nullable=False, server_default="pt-BR"),
        sa.Column("confidentiality", sa.String(50), nullable=False, server_default="internal"),
        sa.Column("tags", sa.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("validity_until", sa.Date(), nullable=True),
        sa.Column("state", sa.String(50), nullable=False, server_default="ingested"),
        sa.Column("current_version_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_documents_space_state", "documents", ["space_id", "state"])

    op.create_table(
        "document_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("frontmatter", JSONB, nullable=False, server_default="{}"),
        sa.Column("author_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approver_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_artifact_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_from_proposal_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_version"),
    )

    op.create_table(
        "connectors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("space_id", UUID(as_uuid=True), sa.ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("schedule", sa.String(100), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="ok"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "source_artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("connector_id", UUID(as_uuid=True), sa.ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(500), nullable=False),
        sa.Column("path", sa.String(1000), nullable=False),
        sa.Column("source_version", sa.String(255), nullable=True),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("connector_id", "external_id", name="uq_connector_artifact"),
    )
    op.create_index("ix_source_artifacts_connector_hash", "source_artifacts", ["connector_id", "content_hash"])

    op.create_table(
        "update_proposals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_artifact_id", UUID(as_uuid=True), sa.ForeignKey("source_artifacts.id"), nullable=True),
        sa.Column("proposed_markdown_patch", sa.Text(), nullable=False),
        sa.Column("state", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("decided_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("drift_score", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
    )
    op.create_index("ix_update_proposals_document_state", "update_proposals", ["document_id", "state"])

    op.create_table(
        "agent_credentials",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("scoped_space_ids", sa.ARRAY(UUID(as_uuid=True)), nullable=False, server_default="{}"),
        sa.Column("max_confidentiality", sa.String(50), nullable=False, server_default="internal"),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_audit_records_entity", "audit_records", ["entity_type", "entity_id", "occurred_at"])

    # Chunks with pgvector embedding - dimensioned for Voyage AI voyage-3 (1024 dims)
    op.execute("""
        CREATE TABLE chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_version_id UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            space_id UUID NOT NULL REFERENCES spaces(id) ON DELETE CASCADE,
            ordinal INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding vector(1024),
            confidentiality VARCHAR(50) NOT NULL DEFAULT 'internal',
            language VARCHAR(10) NOT NULL DEFAULT 'pt-BR',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX ix_chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    op.create_index("ix_chunks_document_version", "chunks", ["document_version_id"])
    op.create_index("ix_chunks_space_confidentiality", "chunks", ["space_id", "confidentiality"])


def downgrade() -> None:
    op.drop_table("chunks")
    op.drop_table("audit_records")
    op.drop_table("agent_credentials")
    op.drop_table("update_proposals")
    op.drop_table("source_artifacts")
    op.drop_table("connectors")
    op.drop_table("document_versions")
    op.drop_table("documents")
    op.drop_table("role_permissions")
    op.drop_table("spaces")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
