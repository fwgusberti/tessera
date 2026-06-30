"""Integration test: access boundary enforcement — company-scoped docs returned."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from tessera_core.domain.entities import (
    Confidentiality,
    Document,
    DocumentLifecycleState,
    Space,
)


class TestAccessBoundary:
    @pytest.mark.anyio
    async def test_user_with_access_only_to_space_a_does_not_receive_space_b_documents(self):
        """User scoped to Company A MUST NOT receive documents from Company B spaces."""
        from tessera_api.routers.documents import list_documents

        company_a_id = uuid.uuid4()
        space_a = uuid.uuid4()
        space_b = uuid.uuid4()
        user_id = uuid.uuid4()
        session = AsyncMock()

        doc_a = Document(
            id=uuid.uuid4(),
            space_id=space_a,
            title="Space A Doc",
            confidentiality=Confidentiality.INTERNAL,
            state=DocumentLifecycleState.PUBLISHED,
            tags=[],
        )

        mock_space_repo = AsyncMock()
        mock_space_repo.list_by_company = AsyncMock(
            return_value=[Space(id=space_a, slug="a", name="Space A", sector="Tech", default_language="en")]
        )

        mock_doc_repo = AsyncMock()
        mock_doc_repo.list_by_space_ids_for_company = AsyncMock(return_value=[doc_a])

        ctx = ({"sub": str(user_id), "id": str(user_id)}, company_a_id)

        with (
            patch("tessera_api.routers.documents.SqlDocumentRepository", return_value=mock_doc_repo),
            patch("tessera_api.routers.documents.SqlSpaceRepository", return_value=mock_space_repo),
        ):
            result = await list_documents(ctx=ctx, session=session, space_id=None, state=None)

        returned_space_ids = {d["space_id"] for d in result["documents"]}
        assert space_b not in returned_space_ids
        assert space_a in returned_space_ids
        mock_space_repo.list_by_company.assert_called_once_with(company_a_id)

    @pytest.mark.anyio
    async def test_admin_user_scoped_to_company_receives_only_company_documents(self):
        """Admin user scoped to a company sees only that company's documents."""
        from tessera_api.routers.documents import list_documents

        company_a_id = uuid.uuid4()
        space_a = uuid.uuid4()
        space_b = uuid.uuid4()
        admin_id = uuid.uuid4()
        session = AsyncMock()

        doc_a = Document(
            id=uuid.uuid4(),
            space_id=space_a,
            title="Space A Doc",
            confidentiality=Confidentiality.INTERNAL,
            state=DocumentLifecycleState.PUBLISHED,
            tags=[],
        )
        doc_b = Document(
            id=uuid.uuid4(),
            space_id=space_b,
            title="Space B Doc",
            confidentiality=Confidentiality.INTERNAL,
            state=DocumentLifecycleState.PUBLISHED,
            tags=[],
        )

        mock_space_repo = AsyncMock()
        mock_space_repo.list_by_company = AsyncMock(
            return_value=[
                Space(id=space_a, slug="a", name="Space A", sector="Tech", default_language="en"),
                Space(id=space_b, slug="b", name="Space B", sector="Tech", default_language="en"),
            ]
        )

        mock_doc_repo = AsyncMock()
        mock_doc_repo.list_by_space_ids_for_company = AsyncMock(return_value=[doc_a, doc_b])

        ctx = ({"sub": str(admin_id), "id": str(admin_id), "is_admin": True}, company_a_id)

        with (
            patch("tessera_api.routers.documents.SqlDocumentRepository", return_value=mock_doc_repo),
            patch("tessera_api.routers.documents.SqlSpaceRepository", return_value=mock_space_repo),
        ):
            result = await list_documents(ctx=ctx, session=session, space_id=None, state=None)

        returned_space_ids = {d["space_id"] for d in result["documents"]}
        assert space_a in returned_space_ids
        assert space_b in returned_space_ids
        assert len(result["documents"]) == 2
        mock_space_repo.list_by_company.assert_called_once_with(company_a_id)
