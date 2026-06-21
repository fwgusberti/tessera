"""Integration test: access boundary enforcement — only accessible space documents returned."""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tessera_core.domain.entities import (
    Confidentiality,
    Document,
    DocumentLifecycleState,
    Space,
    User,
)


class TestAccessBoundary:
    @pytest.mark.anyio
    async def test_user_with_access_only_to_space_a_does_not_receive_space_b_documents(self):
        """User with access only to Space A MUST NOT receive documents from Space B."""
        from tessera_api.routers.documents import list_documents

        space_a = uuid.uuid4()
        space_b = uuid.uuid4()
        user_sub = "restricted@example.com"

        mock_user = User(
            external_subject=user_sub,
            email=user_sub,
            display_name="Restricted",
            groups=["group-a"],
        )
        doc_a = Document(
            id=uuid.uuid4(),
            space_id=space_a,
            title="Space A Doc",
            confidentiality=Confidentiality.INTERNAL,
            state=DocumentLifecycleState.PUBLISHED,
            tags=[],
        )

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_subject.return_value = mock_user

        mock_space_repo = AsyncMock()
        mock_space_repo.list_for_user.return_value = [
            Space(id=space_a, slug="a", name="Space A", sector="Tech", default_language="en")
        ]

        mock_doc_repo = AsyncMock()
        mock_doc_repo.list_by_space_ids.return_value = [doc_a]

        @asynccontextmanager
        async def mock_get_db():
            yield MagicMock()

        with (
            patch("tessera_api.adapters.database.get_db", mock_get_db),
            patch("tessera_api.adapters.repo.SqlDocumentRepository", return_value=mock_doc_repo),
            patch("tessera_api.adapters.repo.SqlSpaceRepository", return_value=mock_space_repo),
            patch("tessera_api.adapters.repo.SqlUserRepository", return_value=mock_user_repo),
            patch(
                "tessera_api.auth.oidc.require_user",
                new=AsyncMock(return_value={"sub": user_sub, "id": str(uuid.uuid4())}),
            ),
        ):
            result = await list_documents(space_id=None, state=None, request=MagicMock())

        returned_space_ids = {d["space_id"] for d in result["documents"]}
        assert space_b not in returned_space_ids
        assert space_a in returned_space_ids
        call_space_ids = mock_doc_repo.list_by_space_ids.call_args[0][0]
        assert space_b not in call_space_ids

    @pytest.mark.anyio
    async def test_admin_user_receives_documents_from_all_spaces(self):
        """Admin user (is_admin=True) MUST receive documents from all spaces via list_all()."""
        from tessera_api.routers.documents import list_documents

        space_a = uuid.uuid4()
        space_b = uuid.uuid4()
        user_sub = "admin@example.com"

        mock_admin = User(
            external_subject=user_sub,
            email=user_sub,
            display_name="Admin",
            groups=[],
            is_admin=True,
        )
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

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_subject.return_value = mock_admin

        mock_space_repo = AsyncMock()
        mock_space_repo.list_for_user.return_value = [
            Space(id=space_a, slug="a", name="Space A", sector="Tech", default_language="en"),
            Space(id=space_b, slug="b", name="Space B", sector="Tech", default_language="en"),
        ]

        mock_doc_repo = AsyncMock()
        mock_doc_repo.list_by_space_ids.return_value = [doc_a, doc_b]

        @asynccontextmanager
        async def mock_get_db():
            yield MagicMock()

        with (
            patch("tessera_api.adapters.database.get_db", mock_get_db),
            patch("tessera_api.adapters.repo.SqlDocumentRepository", return_value=mock_doc_repo),
            patch("tessera_api.adapters.repo.SqlSpaceRepository", return_value=mock_space_repo),
            patch("tessera_api.adapters.repo.SqlUserRepository", return_value=mock_user_repo),
            patch(
                "tessera_api.auth.oidc.require_user",
                new=AsyncMock(return_value={"sub": user_sub, "id": str(uuid.uuid4())}),
            ),
        ):
            result = await list_documents(space_id=None, state=None, request=MagicMock())

        returned_space_ids = {d["space_id"] for d in result["documents"]}
        assert space_a in returned_space_ids
        assert space_b in returned_space_ids
        assert len(result["documents"]) == 2
        mock_space_repo.list_for_user.assert_called_once_with(mock_admin)
