"""Integration test proving `SqlDocumentRepository.delete` cascades at the DB level.

Deleting a `documents` row must transactionally remove its `document_versions`,
`document_drafts`, and `chunks` (search index) rows via `ON DELETE CASCADE`,
with no application-level cleanup of those tables — see
specs/048-delete-document/research.md §2.

Requires a live PostgreSQL instance. Skipped when the database is unreachable.

Run with:
    DATABASE_URL=postgresql+psycopg://tessera:tessera@localhost:5432/tessera \
    pytest apps/api/tests/integration/test_document_delete_cascade.py -v
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tessera_api.adapters.models.company import CompanyModel
from tessera_api.adapters.models.document import DocumentModel
from tessera_api.adapters.models.document_draft import DocumentDraftModel
from tessera_api.adapters.models.document_version import DocumentVersionModel
from tessera_api.adapters.models.space import SpaceModel
from tessera_api.adapters.models.user import UserModel
from tessera_api.adapters.repositories.document import SqlDocumentRepository

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://tessera:tessera@localhost:5432/tessera"
)


def _db_reachable() -> bool:
    try:
        engine = sa.create_engine(DB_URL)
        with engine.connect():
            return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_reachable(), reason="PostgreSQL not reachable — set DATABASE_URL to a live instance"
)


async def _make_document_with_dependents(session: AsyncSession) -> uuid.UUID:
    """Insert a full document graph (version, draft, chunk) and return the document id."""
    user = UserModel(
        external_subject=f"sub-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@test.local",
        display_name="Test User",
    )
    session.add(user)
    await session.flush()

    company = CompanyModel(name="Test Co", admin_user_id=user.id)
    session.add(company)
    await session.flush()

    space = SpaceModel(
        slug=f"space-{uuid.uuid4()}", name="Test Space", sector="eng", company_id=company.id
    )
    session.add(space)
    await session.flush()

    document = DocumentModel(space_id=space.id, title="Test Doc", state="published")
    session.add(document)
    await session.flush()

    version = DocumentVersionModel(
        document_id=document.id,
        version_number=1,
        content_markdown="hello world",
        frontmatter={},
    )
    session.add(version)
    await session.flush()

    draft = DocumentDraftModel(
        document_id=document.id,
        content_markdown="draft content",
        editor_user_id=user.id,
        started_at=datetime.now(UTC),
        last_autosaved_at=datetime.now(UTC),
    )
    session.add(draft)
    await session.flush()

    await session.execute(
        sa.text("""
            INSERT INTO chunks (document_version_id, document_id, space_id, ordinal, text, embedding)
            VALUES (:document_version_id, :document_id, :space_id, 0, 'hello world', NULL)
        """),
        {
            "document_version_id": version.id,
            "document_id": document.id,
            "space_id": space.id,
        },
    )
    await session.flush()

    return document.id


@requires_db
class TestSqlDocumentRepositoryDeleteCascade:
    @pytest.mark.anyio
    async def test_delete_cascades_to_versions_drafts_and_chunks(self):
        engine = create_async_engine(DB_URL)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            document_id = await _make_document_with_dependents(session)
            await session.commit()

            repo = SqlDocumentRepository(session)
            await repo.delete(document_id)
            await session.commit()

            for table in ("documents", "document_versions", "document_drafts", "chunks"):
                result = await session.execute(
                    (
                        sa.text(f"SELECT count(*) FROM {table} WHERE document_id = :doc_id")
                        if table != "documents"
                        else sa.text("SELECT count(*) FROM documents WHERE id = :doc_id")
                    ),
                    {"doc_id": document_id},
                )
                assert (
                    result.scalar_one() == 0
                ), f"{table} must have zero rows for the deleted document"

        await engine.dispose()
