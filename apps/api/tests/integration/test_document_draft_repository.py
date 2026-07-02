"""Integration test for SqlDocumentDraftRepository against a live PostgreSQL instance.

Regression coverage for two bugs found in review of feature 046:
1. `upsert_for_company`'s create path did not verify that `document_id` belongs
   to `company_id` — it could write a draft row for another company's document.
2. `upsert_for_company` used a SELECT-then-branch (check, then INSERT or
   UPDATE) that was not atomic, causing a `UniqueViolation` under concurrent
   first-autosave calls for the same document.

Requires a live PostgreSQL instance. Skipped when the database is unreachable.

Run with:
    DATABASE_URL=postgresql+psycopg://tessera:tessera@localhost:5432/tessera \
    pytest apps/api/tests/integration/test_document_draft_repository.py -v
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tessera_api.adapters.models.company import CompanyModel
from tessera_api.adapters.models.document import DocumentModel
from tessera_api.adapters.models.space import SpaceModel
from tessera_api.adapters.models.user import UserModel
from tessera_api.adapters.repositories.document_draft import SqlDocumentDraftRepository

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


async def _make_document(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Insert a user/company/space/document chain; return (document_id, company_id, user_id)."""
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

    document = DocumentModel(space_id=space.id, title="Test Doc", state="ingested")
    session.add(document)
    await session.flush()

    return document.id, company.id, user.id


@requires_db
class TestSqlDocumentDraftRepositoryTenantIsolation:
    @pytest.mark.anyio
    async def test_upsert_rejects_a_document_belonging_to_another_company(self):
        engine = create_async_engine(DB_URL)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            document_id, real_company_id, editor_id = await _make_document(session)
            other_company_id = uuid.uuid4()

            repo = SqlDocumentDraftRepository(session)
            with pytest.raises(LookupError):
                await repo.upsert_for_company(
                    document_id=document_id,
                    company_id=other_company_id,
                    editor_user_id=editor_id,
                    content_markdown="should never be written",
                )

            result = await session.execute(
                sa.text("SELECT count(*) FROM document_drafts WHERE document_id = :doc_id"),
                {"doc_id": document_id},
            )
            assert result.scalar_one() == 0, "a draft row must not be created for the wrong company"

            await session.rollback()
        await engine.dispose()

    @pytest.mark.anyio
    async def test_upsert_succeeds_for_the_owning_company(self):
        engine = create_async_engine(DB_URL)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            document_id, company_id, editor_id = await _make_document(session)

            repo = SqlDocumentDraftRepository(session)
            draft = await repo.upsert_for_company(
                document_id=document_id,
                company_id=company_id,
                editor_user_id=editor_id,
                content_markdown="hello draft",
            )
            assert draft.content_markdown == "hello draft"

            await session.rollback()
        await engine.dispose()

    @pytest.mark.anyio
    async def test_concurrent_first_autosave_does_not_raise_integrity_error(self):
        """20 concurrent PUT-equivalent upserts with no pre-existing draft row must all succeed."""
        engine = create_async_engine(DB_URL)
        setup_session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with setup_session_factory() as setup_session:
            document_id, company_id, editor_id = await _make_document(setup_session)
            await setup_session.commit()

        async def _one_upsert(i: int) -> None:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                repo = SqlDocumentDraftRepository(session)
                await repo.upsert_for_company(
                    document_id=document_id,
                    company_id=company_id,
                    editor_user_id=editor_id,
                    content_markdown=f"concurrent {i}",
                )
                await session.commit()

        # Any IntegrityError propagates out of gather() and fails the test.
        await asyncio.gather(*[_one_upsert(i) for i in range(20)])

        async with setup_session_factory() as verify_session:
            result = await verify_session.execute(
                sa.text("SELECT count(*) FROM document_drafts WHERE document_id = :doc_id"),
                {"doc_id": document_id},
            )
            assert result.scalar_one() == 1, "concurrent upserts must converge on exactly one row"
        await engine.dispose()
