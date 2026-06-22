"""Integration test: company-scoped documents via list_by_company → list_by_space_ids_for_company."""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tessera_core.domain.entities import (
    Confidentiality,
    Document,
    DocumentLifecycleState,
    Space,
)


class TestAccessibleDocsFlow:
    @pytest.mark.anyio
    async def test_full_flow_company_spaces_returns_company_documents(self):
        """Router MUST: list_by_company → list_by_space_ids_for_company → return docs."""
        from tessera_api.routers.documents import list_documents

        company_id = uuid.uuid4()
        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_space = Space(
            id=space_id,
            slug="eng",
            name="Engineering",
            sector="Tech",
            default_language="en",
        )
        mock_doc = Document(
            id=doc_id,
            space_id=space_id,
            title="Accessible Doc",
            confidentiality=Confidentiality.INTERNAL,
            state=DocumentLifecycleState.PUBLISHED,
            tags=[],
        )

        mock_space_repo = AsyncMock()
        mock_space_repo.list_by_company = AsyncMock(return_value=[mock_space])

        mock_doc_repo = AsyncMock()
        mock_doc_repo.list_by_space_ids_for_company = AsyncMock(return_value=[mock_doc])

        @asynccontextmanager
        async def mock_get_db():
            yield MagicMock()

        with (
            patch("tessera_api.routers.documents.get_db", mock_get_db),
            patch("tessera_api.routers.documents.SqlDocumentRepository", return_value=mock_doc_repo),
            patch("tessera_api.routers.documents.SqlSpaceRepository", return_value=mock_space_repo),
            patch(
                "tessera_api.routers.documents.require_company_context",
                new=AsyncMock(return_value=({"sub": str(user_id), "id": str(user_id)}, company_id)),
            ),
        ):
            result = await list_documents(space_id=None, state=None, request=MagicMock())

        mock_space_repo.list_by_company.assert_called_once_with(company_id)
        mock_doc_repo.list_by_space_ids_for_company.assert_called_once()
        assert len(result["documents"]) == 1
        assert result["documents"][0]["id"] == doc_id

    @pytest.mark.anyio
    async def test_full_flow_multiple_company_spaces_returns_all_documents(self):
        """Documents from ALL company spaces MUST be returned when no space_id is given."""
        from tessera_api.routers.documents import list_documents

        company_id = uuid.uuid4()
        space_a = uuid.uuid4()
        space_b = uuid.uuid4()
        doc_a_id = uuid.uuid4()
        doc_b_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_spaces = [
            Space(id=space_a, slug="eng", name="Engineering", sector="Tech", default_language="en"),
            Space(id=space_b, slug="hr", name="HR", sector="People", default_language="en"),
        ]
        mock_docs = [
            Document(id=doc_a_id, space_id=space_a, title="Eng Doc", confidentiality=Confidentiality.INTERNAL, state=DocumentLifecycleState.PUBLISHED, tags=[]),
            Document(id=doc_b_id, space_id=space_b, title="HR Doc", confidentiality=Confidentiality.INTERNAL, state=DocumentLifecycleState.PUBLISHED, tags=[]),
        ]

        mock_space_repo = AsyncMock()
        mock_space_repo.list_by_company = AsyncMock(return_value=mock_spaces)

        mock_doc_repo = AsyncMock()
        mock_doc_repo.list_by_space_ids_for_company = AsyncMock(return_value=mock_docs)

        @asynccontextmanager
        async def mock_get_db():
            yield MagicMock()

        with (
            patch("tessera_api.routers.documents.get_db", mock_get_db),
            patch("tessera_api.routers.documents.SqlDocumentRepository", return_value=mock_doc_repo),
            patch("tessera_api.routers.documents.SqlSpaceRepository", return_value=mock_space_repo),
            patch(
                "tessera_api.routers.documents.require_company_context",
                new=AsyncMock(return_value=({"sub": str(user_id), "id": str(user_id)}, company_id)),
            ),
        ):
            result = await list_documents(space_id=None, state=None, request=MagicMock())

        call_space_ids = mock_doc_repo.list_by_space_ids_for_company.call_args[0][0]
        assert space_a in call_space_ids
        assert space_b in call_space_ids
        assert len(result["documents"]) == 2
