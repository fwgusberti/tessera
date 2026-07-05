"""Integration test for SqlSpaceRepository.delete_subtree against a live PostgreSQL instance.

Proves that deleting a space subtree:
1. Actually removes descendant spaces (rather than orphaning them via
   `spaces.parent_space_id`'s `ON DELETE SET NULL`), and
2. Cascades to documents, versions, chunks, memberships, permissions, and
   connectors via the existing `ON DELETE CASCADE` foreign keys.

Requires a live PostgreSQL instance. Skipped when the database is unreachable.

Run with:
    DATABASE_URL=postgresql+psycopg://tessera:tessera@localhost:5432/tessera \
    pytest apps/api/tests/integration/test_space_delete_cascade.py -v
"""

from __future__ import annotations

import os
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tessera_api.adapters.models.company import CompanyModel
from tessera_api.adapters.models.connector import ConnectorModel
from tessera_api.adapters.models.document import DocumentModel
from tessera_api.adapters.models.document_version import DocumentVersionModel
from tessera_api.adapters.models.role_permission import RolePermissionModel
from tessera_api.adapters.models.space import SpaceModel
from tessera_api.adapters.models.space_membership import SpaceMembershipModel
from tessera_api.adapters.models.user import UserModel
from tessera_api.adapters.repositories.space import SqlSpaceRepository

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


@requires_db
class TestSpaceDeleteCascade:
    @pytest.mark.anyio
    async def test_delete_subtree_removes_descendants_and_cascades(self):
        engine = create_async_engine(DB_URL)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
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

            parent = SpaceModel(
                slug=f"parent-{uuid.uuid4()}",
                name="Parent Space",
                sector="eng",
                company_id=company.id,
            )
            session.add(parent)
            await session.flush()

            child = SpaceModel(
                slug=f"child-{uuid.uuid4()}",
                name="Child Space",
                sector="eng",
                company_id=company.id,
                parent_space_id=parent.id,
            )
            session.add(child)
            await session.flush()

            parent_doc = DocumentModel(space_id=parent.id, title="Parent Doc", state="ingested")
            child_doc = DocumentModel(space_id=child.id, title="Child Doc", state="ingested")
            session.add_all([parent_doc, child_doc])
            await session.flush()

            parent_ver = DocumentVersionModel(
                document_id=parent_doc.id, version_number=1, content_markdown="parent v1"
            )
            child_ver = DocumentVersionModel(
                document_id=child_doc.id, version_number=1, content_markdown="child v1"
            )
            session.add_all([parent_ver, child_ver])
            await session.flush()

            chunk_id = uuid.uuid4()
            await session.execute(
                sa.text(
                    "INSERT INTO chunks "
                    "(id, document_version_id, document_id, space_id, ordinal, text, embedding) "
                    "VALUES (:id, :dvid, :did, :sid, :ordinal, :text, NULL)"
                ),
                {
                    "id": chunk_id,
                    "dvid": parent_ver.id,
                    "did": parent_doc.id,
                    "sid": parent.id,
                    "ordinal": 0,
                    "text": "a chunk",
                },
            )

            membership = SpaceMembershipModel(space_id=parent.id, user_id=user.id, role="admin")
            permission = RolePermissionModel(
                space_id=parent.id, idp_group="eng-team", role="editor"
            )
            connector = ConnectorModel(space_id=child.id, type="confluence", config={})
            session.add_all([membership, permission, connector])
            await session.flush()

            membership_id = membership.id
            permission_id = permission.id
            connector_id = connector.id

            repo = SqlSpaceRepository(session)
            deleted = await repo.delete_subtree(parent.id)
            assert deleted == (2, 2)

            await session.commit()

            async def _count(table: str, column: str, value) -> int:
                result = await session.execute(
                    sa.text(f"SELECT count(*) FROM {table} WHERE {column} = :v"),
                    {"v": value},
                )
                return result.scalar_one()

            # Both parent and child spaces are actually removed (not orphaned).
            assert await _count("spaces", "id", parent.id) == 0
            assert await _count("spaces", "id", child.id) == 0
            # Documents in both spaces cascaded.
            assert await _count("documents", "id", parent_doc.id) == 0
            assert await _count("documents", "id", child_doc.id) == 0
            # Versions cascaded transitively.
            assert await _count("document_versions", "id", parent_ver.id) == 0
            assert await _count("document_versions", "id", child_ver.id) == 0
            # Chunk cascaded.
            assert await _count("chunks", "id", chunk_id) == 0
            # Membership / permission / connector cascaded.
            assert await _count("space_memberships", "id", membership_id) == 0
            assert await _count("role_permissions", "id", permission_id) == 0
            assert await _count("connectors", "id", connector_id) == 0

        await engine.dispose()
