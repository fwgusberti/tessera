"""Integration tests: document permission enforcement via SpaceMembership role."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager, contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tessera_core.domain.entities import (
    Confidentiality,
    Document,
    DocumentLifecycleState,
    DocumentVersion,
    SpaceMembership,
    SpaceRole,
    User,
)


def _make_jwt_header(user_id: uuid.UUID, is_admin: bool = False) -> dict:
    from tessera_api.auth.jwt_auth import create_access_token

    token = create_access_token(user_id, "user@example.com", is_admin)
    return {"Authorization": f"Bearer {token}"}


def _make_user(user_id: uuid.UUID | None = None, is_admin: bool = False) -> User:
    uid = user_id or uuid.uuid4()
    return User(
        id=uid,
        external_subject=f"sub-{uid}",
        email="user@example.com",
        display_name="User",
        is_admin=is_admin,
    )


def _membership(space_id: uuid.UUID, user_id: uuid.UUID, role: SpaceRole) -> SpaceMembership:
    return SpaceMembership(space_id=space_id, user_id=user_id, role=role)


def _make_doc(space_id: uuid.UUID, doc_id: uuid.UUID | None = None) -> Document:
    return Document(
        id=doc_id or uuid.uuid4(),
        space_id=space_id,
        title="Test Doc",
        language="pt-BR",
        confidentiality=Confidentiality.INTERNAL,
        state=DocumentLifecycleState.INGESTED,
        tags=[],
    )


def _make_version(doc_id: uuid.UUID, version_id: uuid.UUID | None = None) -> DocumentVersion:
    return DocumentVersion(
        id=version_id or uuid.uuid4(),
        document_id=doc_id,
        version_number=1,
        content_markdown="# Hello",
        frontmatter={},
    )


@asynccontextmanager
async def _mock_db():
    yield MagicMock()


@contextmanager
def _bypass_onboarding_guard():
    from tessera_api.auth.bearer import require_onboarding_complete
    from tessera_api.main import app

    async def _noop():
        return None

    app.dependency_overrides[require_onboarding_complete] = _noop
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_onboarding_complete, None)


class TestEditorCanCreateDocument:
    @pytest.mark.anyio
    async def test_editor_gets_201_on_post_documents(self):
        from tessera_api.routers.documents import create_document, CreateDocumentRequest

        space_id = uuid.uuid4()
        editor_id = uuid.uuid4()
        editor = _make_user(editor_id)
        doc_id = uuid.uuid4()
        version_id = uuid.uuid4()
        doc = _make_doc(space_id, doc_id)
        version = _make_version(doc_id, version_id)
        doc_with_version = doc.model_copy(update={"current_version_id": version_id})

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id.return_value = editor
        mock_user_repo.get_by_subject.return_value = editor

        mock_membership_repo = AsyncMock()
        mock_membership_repo.list_by_space.return_value = [
            _membership(space_id, editor_id, SpaceRole.EDITOR)
        ]

        mock_doc_repo = AsyncMock()
        mock_doc_repo.create.return_value = doc
        mock_doc_repo.set_current_version.return_value = doc_with_version

        mock_ver_repo = AsyncMock()
        mock_ver_repo.create.return_value = version

        with (
            patch("tessera_api.adapters.database.get_db", _mock_db),
            patch("tessera_api.adapters.repo.SqlUserRepository", return_value=mock_user_repo),
            patch(
                "tessera_api.adapters.repo.SqlSpaceMembershipRepository",
                return_value=mock_membership_repo,
            ),
            patch("tessera_api.adapters.repo.SqlDocumentRepository", return_value=mock_doc_repo),
            patch(
                "tessera_api.adapters.repo.SqlDocumentVersionRepository",
                return_value=mock_ver_repo,
            ),
            patch(
                "tessera_api.auth.oidc.require_user",
                new=AsyncMock(
                    return_value={"id": str(editor_id), "sub": str(editor_id), "is_admin": False}
                ),
            ),
        ):
            body = CreateDocumentRequest(
                space_id=space_id,
                title="My Doc",
                content_markdown="# Hello",
            )
            result = await create_document(body, MagicMock())

        assert "document" in result


class TestViewerCannotCreateDocument:
    @pytest.mark.anyio
    async def test_viewer_gets_403_on_post_documents(self):
        from fastapi import HTTPException

        from tessera_api.routers.documents import create_document, CreateDocumentRequest

        space_id = uuid.uuid4()
        viewer_id = uuid.uuid4()
        viewer = _make_user(viewer_id)

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id.return_value = viewer
        mock_user_repo.get_by_subject.return_value = viewer

        mock_membership_repo = AsyncMock()
        mock_membership_repo.list_by_space.return_value = [
            _membership(space_id, viewer_id, SpaceRole.VIEWER)
        ]

        with (
            patch("tessera_api.adapters.database.get_db", _mock_db),
            patch("tessera_api.adapters.repo.SqlUserRepository", return_value=mock_user_repo),
            patch(
                "tessera_api.adapters.repo.SqlSpaceMembershipRepository",
                return_value=mock_membership_repo,
            ),
            patch(
                "tessera_api.auth.oidc.require_user",
                new=AsyncMock(
                    return_value={"id": str(viewer_id), "sub": str(viewer_id), "is_admin": False}
                ),
            ),
        ):
            body = CreateDocumentRequest(
                space_id=space_id,
                title="My Doc",
                content_markdown="# Hello",
            )
            with pytest.raises(HTTPException) as exc_info:
                await create_document(body, MagicMock())

        assert exc_info.value.status_code == 403


class TestViewerCanReadDocument:
    @pytest.mark.anyio
    async def test_viewer_gets_200_on_get_document(self):
        from tessera_api.routers.documents import get_document

        space_id = uuid.uuid4()
        viewer_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        version_id = uuid.uuid4()
        doc = _make_doc(space_id, doc_id).model_copy(update={"current_version_id": version_id})
        version = _make_version(doc_id, version_id)

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = doc

        mock_ver_repo = AsyncMock()
        mock_ver_repo.get_by_id.return_value = version

        with (
            patch("tessera_api.adapters.database.get_db", _mock_db),
            patch("tessera_api.adapters.repo.SqlDocumentRepository", return_value=mock_doc_repo),
            patch(
                "tessera_api.adapters.repo.SqlDocumentVersionRepository",
                return_value=mock_ver_repo,
            ),
            patch(
                "tessera_api.auth.oidc.require_user",
                new=AsyncMock(
                    return_value={"id": str(viewer_id), "sub": str(viewer_id), "is_admin": False}
                ),
            ),
        ):
            result = await get_document(doc_id, MagicMock())

        assert "document" in result
