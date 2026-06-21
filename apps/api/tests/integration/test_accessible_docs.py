"""Integration test: user.groups → list_for_user() → list_by_space_ids() → documents."""

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


class TestAccessibleDocsFlow:
    @pytest.mark.anyio
    async def test_full_flow_user_with_groups_receives_accessible_documents(self):
        """Router MUST: resolve user → get accessible spaces via list_for_user → fetch docs via list_by_space_ids."""
        from tessera_api.routers.documents import list_documents

        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        user_sub = "user@example.com"

        mock_user = User(
            external_subject=user_sub,
            email=user_sub,
            display_name="Test User",
            groups=["engineering"],
        )
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

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_subject.return_value = mock_user

        mock_space_repo = AsyncMock()
        mock_space_repo.list_for_user.return_value = [mock_space]

        mock_doc_repo = AsyncMock()
        mock_doc_repo.list_by_space_ids.return_value = [mock_doc]

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

        mock_user_repo.get_by_subject.assert_called_once_with(user_sub)
        mock_space_repo.list_for_user.assert_called_once_with(mock_user)
        mock_doc_repo.list_by_space_ids.assert_called_once_with([space_id], None)
        assert len(result["documents"]) == 1
        assert result["documents"][0]["id"] == doc_id

    @pytest.mark.anyio
    async def test_full_flow_user_with_multiple_spaces(self):
        """Documents from ALL accessible spaces MUST be returned when no space_id is given."""
        from tessera_api.routers.documents import list_documents

        space_a = uuid.uuid4()
        space_b = uuid.uuid4()
        doc_a_id = uuid.uuid4()
        doc_b_id = uuid.uuid4()
        user_sub = "multi@example.com"

        mock_user = User(
            external_subject=user_sub,
            email=user_sub,
            display_name="Multi",
            groups=["engineering", "hr"],
        )
        mock_spaces = [
            Space(id=space_a, slug="eng", name="Engineering", sector="Tech", default_language="en"),
            Space(id=space_b, slug="hr", name="HR", sector="People", default_language="en"),
        ]
        mock_docs = [
            Document(id=doc_a_id, space_id=space_a, title="Eng Doc", confidentiality=Confidentiality.INTERNAL, state=DocumentLifecycleState.PUBLISHED, tags=[]),
            Document(id=doc_b_id, space_id=space_b, title="HR Doc", confidentiality=Confidentiality.INTERNAL, state=DocumentLifecycleState.PUBLISHED, tags=[]),
        ]

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_subject.return_value = mock_user

        mock_space_repo = AsyncMock()
        mock_space_repo.list_for_user.return_value = mock_spaces

        mock_doc_repo = AsyncMock()
        mock_doc_repo.list_by_space_ids.return_value = mock_docs

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

        mock_doc_repo.list_by_space_ids.assert_called_once_with([space_a, space_b], None)
        assert len(result["documents"]) == 2
