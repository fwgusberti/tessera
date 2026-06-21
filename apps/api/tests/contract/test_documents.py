"""Contract tests: POST /v1/documents and POST /v1/documents/{id}/publish owner invariants."""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from tessera_core.domain.entities import (
    Confidentiality,
    Document,
    DocumentLifecycleState,
    DocumentVersion,
    Space,
    User,
)


def _make_body(space_id: uuid.UUID, content: str = "# Hello"):
    from tessera_api.routers.documents import CreateDocumentRequest

    return CreateDocumentRequest(
        space_id=space_id,
        title="Test Document",
        language="pt-BR",
        confidentiality=Confidentiality.INTERNAL,
        content_markdown=content,
        tags=[],
        frontmatter={},
    )


def _make_mocks(doc_id: uuid.UUID, version_id: uuid.UUID, space_id: uuid.UUID):
    mock_doc = Document(
        id=doc_id,
        space_id=space_id,
        title="Test Document",
        language="pt-BR",
        confidentiality=Confidentiality.INTERNAL,
        state=DocumentLifecycleState.INGESTED,
        tags=[],
        current_version_id=None,
    )
    mock_doc_updated = mock_doc.model_copy(update={"current_version_id": version_id})
    mock_version = DocumentVersion(
        id=version_id,
        document_id=doc_id,
        version_number=1,
        content_markdown="# Hello",
        frontmatter={},
    )

    mock_doc_repo = AsyncMock()
    mock_doc_repo.create.return_value = mock_doc
    mock_doc_repo.set_current_version.return_value = mock_doc_updated

    mock_ver_repo = AsyncMock()
    mock_ver_repo.create.return_value = mock_version

    @asynccontextmanager
    async def mock_get_db():
        yield MagicMock()

    return mock_doc_repo, mock_ver_repo, mock_doc_updated, mock_version, mock_get_db


class TestCreateDocumentContract:
    """Invariant: create_document MUST call set_current_version and return updated document."""

    @pytest.mark.anyio
    async def test_set_current_version_called_after_creation(self):
        """set_current_version MUST be called with (doc.id, version.id) after version creation."""
        from tessera_api.routers.documents import create_document

        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        version_id = uuid.uuid4()
        mock_doc_repo, mock_ver_repo, _, mock_version, mock_get_db = _make_mocks(
            doc_id, version_id, space_id
        )

        with (
            patch("tessera_api.adapters.database.get_db", mock_get_db),
            patch(
                "tessera_api.adapters.repo.SqlDocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "tessera_api.adapters.repo.SqlDocumentVersionRepository",
                return_value=mock_ver_repo,
            ),
            patch(
                "tessera_api.auth.oidc.require_user",
                new=AsyncMock(return_value={"id": str(uuid.uuid4())}),
            ),
        ):
            await create_document(_make_body(space_id), MagicMock())

        mock_doc_repo.set_current_version.assert_called_once_with(doc_id, version_id)

    @pytest.mark.anyio
    async def test_create_document_response_has_current_version_id(self):
        """Response document.current_version_id MUST equal version.id."""
        from tessera_api.routers.documents import create_document

        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        version_id = uuid.uuid4()
        mock_doc_repo, mock_ver_repo, _, _, mock_get_db = _make_mocks(doc_id, version_id, space_id)

        with (
            patch("tessera_api.adapters.database.get_db", mock_get_db),
            patch(
                "tessera_api.adapters.repo.SqlDocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "tessera_api.adapters.repo.SqlDocumentVersionRepository",
                return_value=mock_ver_repo,
            ),
            patch(
                "tessera_api.auth.oidc.require_user",
                new=AsyncMock(return_value={"id": str(uuid.uuid4())}),
            ),
        ):
            result = await create_document(_make_body(space_id), MagicMock())

        assert result["document"]["current_version_id"] == version_id

    @pytest.mark.anyio
    async def test_create_document_creates_version_number_1(self):
        """DocumentVersion with version_number=1 MUST be created and linked to the document."""
        from tessera_api.routers.documents import create_document

        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        version_id = uuid.uuid4()
        mock_doc_repo, mock_ver_repo, _, _, mock_get_db = _make_mocks(doc_id, version_id, space_id)

        with (
            patch("tessera_api.adapters.database.get_db", mock_get_db),
            patch(
                "tessera_api.adapters.repo.SqlDocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "tessera_api.adapters.repo.SqlDocumentVersionRepository",
                return_value=mock_ver_repo,
            ),
            patch(
                "tessera_api.auth.oidc.require_user",
                new=AsyncMock(return_value={"id": str(uuid.uuid4())}),
            ),
        ):
            await create_document(_make_body(space_id), MagicMock())

        created_version_arg = mock_ver_repo.create.call_args[0][0]
        assert created_version_arg.version_number == 1
        assert created_version_arg.document_id == doc_id


# ---------------------------------------------------------------------------
# Owner invariant helpers
# ---------------------------------------------------------------------------


def _make_publish_mocks(
    doc_id: uuid.UUID,
    version_id: uuid.UUID,
    space_id: uuid.UUID,
    owner_id: uuid.UUID | None,
):
    mock_doc = Document(
        id=doc_id,
        space_id=space_id,
        title="Test Document",
        language="pt-BR",
        confidentiality=Confidentiality.INTERNAL,
        state=DocumentLifecycleState.INGESTED,
        tags=[],
        owner_user_id=owner_id,
        current_version_id=version_id,
    )
    mock_version = DocumentVersion(
        id=version_id,
        document_id=doc_id,
        version_number=1,
        content_markdown="# Hello",
        frontmatter={},
    )

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_id.return_value = mock_doc
    mock_doc_repo.set_owner.return_value = mock_doc.model_copy(
        update={"owner_user_id": owner_id or doc_id}
    )
    mock_doc_repo.update_state.return_value = mock_doc.model_copy(
        update={"state": DocumentLifecycleState.PUBLISHED}
    )
    mock_doc_repo.set_current_version.return_value = mock_doc

    mock_ver_repo = AsyncMock()
    mock_ver_repo.list_by_document.return_value = [mock_version]
    mock_ver_repo.create.return_value = mock_version

    @asynccontextmanager
    async def mock_get_db():
        yield MagicMock()

    return mock_doc_repo, mock_ver_repo, mock_doc, mock_version, mock_get_db


class TestCreateDocumentOwnerContract:
    """Invariant: create_document MUST set owner_user_id from the authenticated user."""

    @pytest.mark.anyio
    async def test_create_document_sets_owner_from_user_info(self):
        """Document passed to doc_repo.create MUST have owner_user_id equal to the authenticated user's ID."""
        from tessera_api.routers.documents import create_document

        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        version_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_doc_repo, mock_ver_repo, _, _, mock_get_db = _make_mocks(doc_id, version_id, space_id)

        with (
            patch("tessera_api.adapters.database.get_db", mock_get_db),
            patch("tessera_api.adapters.repo.SqlDocumentRepository", return_value=mock_doc_repo),
            patch(
                "tessera_api.adapters.repo.SqlDocumentVersionRepository", return_value=mock_ver_repo
            ),
            patch(
                "tessera_api.auth.oidc.require_user",
                new=AsyncMock(return_value={"id": str(user_id), "sub": str(user_id)}),
            ),
        ):
            await create_document(_make_body(space_id), MagicMock())

        created_doc_arg = mock_doc_repo.create.call_args[0][0]
        assert created_doc_arg.owner_user_id == user_id


class TestPublishDocumentOwnerContract:
    """Invariants for publish_document owner handling."""

    @pytest.mark.anyio
    async def test_publish_document_auto_assigns_owner_when_none(self):
        """When doc.owner_user_id is None, publish MUST call set_owner with the publisher's ID and succeed."""
        from tessera_api.routers.documents import publish_document

        doc_id = uuid.uuid4()
        version_id = uuid.uuid4()
        space_id = uuid.uuid4()
        publisher_id = uuid.uuid4()

        mock_doc_repo, mock_ver_repo, _, mock_version, mock_get_db = _make_publish_mocks(
            doc_id, version_id, space_id, owner_id=None
        )

        with (
            patch("tessera_api.adapters.database.get_db", mock_get_db),
            patch("tessera_api.adapters.repo.SqlDocumentRepository", return_value=mock_doc_repo),
            patch(
                "tessera_api.adapters.repo.SqlDocumentVersionRepository", return_value=mock_ver_repo
            ),
            patch("tessera_api.adapters.audit.write_audit", new=AsyncMock()),
            patch(
                "tessera_api.auth.oidc.require_user",
                new=AsyncMock(return_value={"id": str(publisher_id), "sub": str(publisher_id)}),
            ),
        ):
            result = await publish_document(doc_id, MagicMock())

        mock_doc_repo.set_owner.assert_called_once_with(doc_id, publisher_id)
        assert result["document"]["state"] == DocumentLifecycleState.PUBLISHED
        mock_ver_repo.create.assert_not_called()
        mock_ver_repo.update_approval.assert_called_once()
        call_version_id, call_approver_id, _ = mock_ver_repo.update_approval.call_args[0]
        assert call_version_id == version_id
        assert call_approver_id == publisher_id

    @pytest.mark.anyio
    async def test_publish_document_preserves_existing_owner(self):
        """When doc.owner_user_id is already set, publish MUST NOT call set_owner and MUST succeed."""
        from tessera_api.routers.documents import publish_document

        doc_id = uuid.uuid4()
        version_id = uuid.uuid4()
        space_id = uuid.uuid4()
        existing_owner_id = uuid.uuid4()
        publisher_id = uuid.uuid4()

        mock_doc_repo, mock_ver_repo, _, _, mock_get_db = _make_publish_mocks(
            doc_id, version_id, space_id, owner_id=existing_owner_id
        )

        with (
            patch("tessera_api.adapters.database.get_db", mock_get_db),
            patch("tessera_api.adapters.repo.SqlDocumentRepository", return_value=mock_doc_repo),
            patch(
                "tessera_api.adapters.repo.SqlDocumentVersionRepository", return_value=mock_ver_repo
            ),
            patch("tessera_api.adapters.audit.write_audit", new=AsyncMock()),
            patch(
                "tessera_api.auth.oidc.require_user",
                new=AsyncMock(return_value={"id": str(publisher_id), "sub": str(publisher_id)}),
            ),
        ):
            result = await publish_document(doc_id, MagicMock())

        mock_doc_repo.set_owner.assert_not_called()
        assert result["document"]["state"] == DocumentLifecycleState.PUBLISHED


class TestPublishDocumentVersionContract:
    """Invariant: publish MUST update the existing version's approval metadata — never insert a new row."""

    @pytest.mark.anyio
    async def test_publish_document_records_approval_without_creating_version(self):
        """ver_repo.update_approval MUST be called; ver_repo.create MUST NOT be called during publish."""
        from tessera_api.routers.documents import publish_document

        doc_id = uuid.uuid4()
        version_id = uuid.uuid4()
        space_id = uuid.uuid4()
        publisher_id = uuid.uuid4()
        owner_id = uuid.uuid4()

        mock_doc_repo, mock_ver_repo, _, _, mock_get_db = _make_publish_mocks(
            doc_id, version_id, space_id, owner_id=owner_id
        )

        with (
            patch("tessera_api.adapters.database.get_db", mock_get_db),
            patch("tessera_api.adapters.repo.SqlDocumentRepository", return_value=mock_doc_repo),
            patch(
                "tessera_api.adapters.repo.SqlDocumentVersionRepository", return_value=mock_ver_repo
            ),
            patch("tessera_api.adapters.audit.write_audit", new=AsyncMock()),
            patch(
                "tessera_api.auth.oidc.require_user",
                new=AsyncMock(return_value={"id": str(publisher_id), "sub": str(publisher_id)}),
            ),
        ):
            result = await publish_document(doc_id, MagicMock())

        mock_ver_repo.create.assert_not_called()
        mock_ver_repo.update_approval.assert_called_once()
        call_version_id, call_approver_id, _ = mock_ver_repo.update_approval.call_args[0]
        assert call_version_id == version_id
        assert call_approver_id == publisher_id
        assert result["document"]["state"] == DocumentLifecycleState.PUBLISHED


class TestPublishDocumentErrorContract:
    """Invariants for clear error feedback when publish cannot proceed (US2)."""

    @pytest.mark.anyio
    async def test_publish_document_fails_with_clear_message_when_no_versions(self):
        """Publish MUST return 400 with 'No versions' detail when document has no content versions."""
        from tessera_api.routers.documents import publish_document

        doc_id = uuid.uuid4()
        version_id = uuid.uuid4()
        space_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        publisher_id = uuid.uuid4()

        mock_doc_repo, mock_ver_repo, _, _, mock_get_db = _make_publish_mocks(
            doc_id, version_id, space_id, owner_id=owner_id
        )
        mock_ver_repo.list_by_document.return_value = []

        with (
            patch("tessera_api.adapters.database.get_db", mock_get_db),
            patch("tessera_api.adapters.repo.SqlDocumentRepository", return_value=mock_doc_repo),
            patch(
                "tessera_api.adapters.repo.SqlDocumentVersionRepository", return_value=mock_ver_repo
            ),
            patch("tessera_api.adapters.audit.write_audit", new=AsyncMock()),
            patch(
                "tessera_api.auth.oidc.require_user",
                new=AsyncMock(return_value={"id": str(publisher_id), "sub": str(publisher_id)}),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await publish_document(doc_id, MagicMock())

        assert exc_info.value.status_code == 400
        assert "versions" in exc_info.value.detail.lower()


class TestListDocumentsNoSpaceIdContract:
    """Contract: GET /v1/documents without space_id MUST return accessible docs via space/user repos."""

    @pytest.mark.anyio
    async def test_list_documents_no_space_id_calls_list_by_space_ids(self):
        """Router MUST call doc_repo.list_by_space_ids with the user's accessible space IDs."""
        from tessera_api.routers.documents import list_documents

        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()

        mock_doc = Document(
            id=doc_id,
            space_id=space_id,
            title="Accessible Doc",
            confidentiality=Confidentiality.INTERNAL,
            state=DocumentLifecycleState.PUBLISHED,
            tags=[],
        )
        mock_space = Space(id=space_id, slug="eng", name="Engineering", sector="Tech", default_language="en")
        mock_user = User(external_subject="u1", email="u1@test.com", display_name="U1", groups=["eng"])

        mock_doc_repo = AsyncMock()
        mock_doc_repo.list_by_space_ids.return_value = [mock_doc]

        mock_space_repo = AsyncMock()
        mock_space_repo.list_for_user.return_value = [mock_space]

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_subject.return_value = mock_user

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
                new=AsyncMock(return_value={"sub": "u1", "id": str(uuid.uuid4())}),
            ),
        ):
            result = await list_documents(space_id=None, state=None, request=MagicMock())

        assert len(result["documents"]) == 1
        assert result["documents"][0]["id"] == doc_id
        mock_doc_repo.list_by_space_ids.assert_called_once_with([space_id], None)

    @pytest.mark.anyio
    async def test_list_documents_no_space_id_returns_empty_when_no_accessible_spaces(self):
        """When user has no accessible spaces, MUST return empty documents list."""
        from tessera_api.routers.documents import list_documents

        mock_user = User(external_subject="u1", email="u1@test.com", display_name="U1", groups=[])

        mock_doc_repo = AsyncMock()
        mock_doc_repo.list_by_space_ids.return_value = []

        mock_space_repo = AsyncMock()
        mock_space_repo.list_for_user.return_value = []

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_subject.return_value = mock_user

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
                new=AsyncMock(return_value={"sub": "u1", "id": str(uuid.uuid4())}),
            ),
        ):
            result = await list_documents(space_id=None, state=None, request=MagicMock())

        assert result["documents"] == []
