"""Unit tests for per-document and bulk reindex endpoints."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def _make_app():
    from tessera_api.auth.bearer import require_onboarding_complete
    from tessera_api.main import create_app

    app = create_app()

    async def _noop_onboarding():
        return None

    app.dependency_overrides[require_onboarding_complete] = _noop_onboarding
    return app


def _auth_patch(user_id: str | None = None, company_admin: bool = False):
    """Patch require_company_member; ``company_admin`` controls per-company authority."""
    from datetime import UTC, datetime

    from tessera_core.domain.entities import CompanyMembership, CompanyRole

    uid = user_id or str(uuid.uuid4())
    info = {"sub": uid, "id": uid, "email": "test@test.com", "is_admin": False}
    membership = CompanyMembership(
        id=uuid.uuid4(),
        user_id=uuid.UUID(uid),
        company_id=uuid.uuid4(),
        role=CompanyRole.ADMIN if company_admin else CompanyRole.MEMBER,
        joined_at=datetime.now(UTC),
    )
    return patch(
        "tessera_api.routers.documents.require_company_member",
        new=AsyncMock(return_value=(info, uuid.uuid4(), membership)),
    )


def _admin_auth_patch(user_id: str | None = None, is_admin: bool = False):
    uid = user_id or str(uuid.uuid4())
    return patch(
        "tessera_api.auth.oidc.require_user",
        new=AsyncMock(return_value={"sub": uid, "id": uid, "email": "test@test.com", "is_admin": is_admin}),
    )


def _build_published_doc(doc_id: uuid.UUID, space_id: uuid.UUID, owner_id: uuid.UUID, version_id: uuid.UUID):
    from tessera_core.domain.entities import Confidentiality, Document, DocumentLifecycleState

    return Document(
        id=doc_id,
        space_id=space_id,
        owner_user_id=owner_id,
        title="Test Doc",
        language="en",
        confidentiality=Confidentiality.INTERNAL,
        state=DocumentLifecycleState.PUBLISHED,
        current_version_id=version_id,
    )


def _build_draft_doc(doc_id: uuid.UUID, space_id: uuid.UUID, owner_id: uuid.UUID, version_id: uuid.UUID):
    from tessera_core.domain.entities import Confidentiality, Document, DocumentLifecycleState

    return Document(
        id=doc_id,
        space_id=space_id,
        owner_user_id=owner_id,
        title="Draft Doc",
        language="en",
        confidentiality=Confidentiality.INTERNAL,
        state=DocumentLifecycleState.INGESTED,
        current_version_id=version_id,
    )


def _build_version(version_id: uuid.UUID, doc_id: uuid.UUID):
    from tessera_core.domain.entities import DocumentVersion

    return DocumentVersion(
        id=version_id,
        document_id=doc_id,
        version_number=1,
        content_markdown="content",
        frontmatter={},
    )


# ── T008: owner can reindex ───────────────────────────────────────────────────

def test_reindex_owner_dispatches_task():
    """Document owner calling reindex receives 200 and the indexing task is dispatched."""
    app = _make_app()
    owner_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    space_id = uuid.uuid4()
    version_id = uuid.uuid4()

    doc = _build_published_doc(doc_id, space_id, owner_id, version_id)
    version = _build_version(version_id, doc_id)

    mock_doc_repo = MagicMock()
    mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
    mock_ver_repo = MagicMock()
    mock_ver_repo.list_by_document = AsyncMock(return_value=[version])
    mock_session = AsyncMock()

    @asynccontextmanager
    async def _fake_get_db():
        yield mock_session

    mock_send_task = MagicMock()

    with (
        _auth_patch(user_id=str(owner_id)),
        patch("tessera_api.routers.documents.get_db", _fake_get_db),
        patch("tessera_api.routers.documents.SqlDocumentRepository", return_value=mock_doc_repo),
        patch("tessera_api.routers.documents.SqlDocumentVersionRepository", return_value=mock_ver_repo),
        patch(
            "tessera_api.routers.documents.get_celery_app",
            return_value=MagicMock(send_task=mock_send_task),
        ),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(f"/v1/documents/{doc_id}/reindex")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert mock_send_task.called, "send_task() was not called — indexing task not dispatched"
    task_name = mock_send_task.call_args[0][0]
    assert "index_document_version" in task_name
    body = response.json()
    assert body["queued"] is True
    assert body["document_id"] == str(doc_id)


# ── T009: admin (non-owner) can reindex ──────────────────────────────────────

def test_reindex_admin_dispatches_task():
    """System admin (non-owner) calling reindex receives 200 and task is dispatched."""
    app = _make_app()
    owner_id = uuid.uuid4()
    admin_id = uuid.uuid4()  # different from owner
    doc_id = uuid.uuid4()
    space_id = uuid.uuid4()
    version_id = uuid.uuid4()

    doc = _build_published_doc(doc_id, space_id, owner_id, version_id)
    version = _build_version(version_id, doc_id)

    mock_doc_repo = MagicMock()
    mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
    mock_ver_repo = MagicMock()
    mock_ver_repo.list_by_document = AsyncMock(return_value=[version])
    mock_session = AsyncMock()

    @asynccontextmanager
    async def _fake_get_db():
        yield mock_session

    mock_send_task = MagicMock()

    with (
        _auth_patch(user_id=str(admin_id), company_admin=True),
        patch("tessera_api.routers.documents.get_db", _fake_get_db),
        patch("tessera_api.routers.documents.SqlDocumentRepository", return_value=mock_doc_repo),
        patch("tessera_api.routers.documents.SqlDocumentVersionRepository", return_value=mock_ver_repo),
        patch(
            "tessera_api.routers.documents.get_celery_app",
            return_value=MagicMock(send_task=mock_send_task),
        ),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(f"/v1/documents/{doc_id}/reindex")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert mock_send_task.called


# ── T010: non-owner non-admin gets 403 ───────────────────────────────────────

def test_reindex_non_owner_returns_403():
    """An authenticated user who is neither owner nor admin receives 403."""
    app = _make_app()
    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    space_id = uuid.uuid4()
    version_id = uuid.uuid4()

    doc = _build_published_doc(doc_id, space_id, owner_id, version_id)

    mock_doc_repo = MagicMock()
    mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
    mock_session = AsyncMock()

    @asynccontextmanager
    async def _fake_get_db():
        yield mock_session

    with (
        _auth_patch(user_id=str(other_id)),
        patch("tessera_api.routers.documents.get_db", _fake_get_db),
        patch("tessera_api.routers.documents.SqlDocumentRepository", return_value=mock_doc_repo),
        patch("tessera_api.routers.documents.SqlDocumentVersionRepository", return_value=MagicMock()),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(f"/v1/documents/{doc_id}/reindex")

    assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


# ── T011: missing document returns 403 (hides existence) ─────────────────────

def test_reindex_missing_document_returns_404():
    """Reindexing a document not found in the company scope returns 404 (hides existence)."""
    app = _make_app()
    doc_id = uuid.uuid4()

    mock_doc_repo = MagicMock()
    mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=None)
    mock_session = AsyncMock()

    @asynccontextmanager
    async def _fake_get_db():
        yield mock_session

    with (
        _auth_patch(company_admin=True),
        patch("tessera_api.routers.documents.get_db", _fake_get_db),
        patch("tessera_api.routers.documents.SqlDocumentRepository", return_value=mock_doc_repo),
        patch("tessera_api.routers.documents.SqlDocumentVersionRepository", return_value=MagicMock()),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(f"/v1/documents/{doc_id}/reindex")

    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"


# ── T012: draft document returns 400 ─────────────────────────────────────────

def test_reindex_draft_document_returns_400():
    """Reindexing a document in draft (non-published) state returns 400."""
    app = _make_app()
    owner_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    space_id = uuid.uuid4()
    version_id = uuid.uuid4()

    doc = _build_draft_doc(doc_id, space_id, owner_id, version_id)

    mock_doc_repo = MagicMock()
    mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
    mock_session = AsyncMock()

    @asynccontextmanager
    async def _fake_get_db():
        yield mock_session

    with (
        _auth_patch(user_id=str(owner_id)),
        patch("tessera_api.routers.documents.get_db", _fake_get_db),
        patch("tessera_api.routers.documents.SqlDocumentRepository", return_value=mock_doc_repo),
        patch("tessera_api.routers.documents.SqlDocumentVersionRepository", return_value=MagicMock()),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(f"/v1/documents/{doc_id}/reindex")

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"


# ── T014: admin bulk reindex dispatches tasks for unchunked docs ──────────────

def test_bulk_reindex_admin_dispatches_for_unchunked_docs():
    """Admin calling POST /admin/reindex gets tasks dispatched for all published docs with no chunks."""
    app = _make_app()
    doc1_id = uuid.uuid4()
    doc2_id = uuid.uuid4()
    ver1_id = uuid.uuid4()
    ver2_id = uuid.uuid4()
    space_id = uuid.uuid4()

    fake_rows = [
        {"id": doc1_id, "space_id": space_id, "version_id": ver1_id},
        {"id": doc2_id, "space_id": space_id, "version_id": ver2_id},
    ]

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = fake_rows
    mock_session.execute = AsyncMock(return_value=mock_result)

    @asynccontextmanager
    async def _fake_get_db():
        yield mock_session

    mock_send_task = MagicMock()

    with (
        _admin_auth_patch(is_admin=True),
        patch("tessera_api.adapters.database.get_db", _fake_get_db),
        patch(
            "tessera_api.adapters.celery.get_celery_app",
            return_value=MagicMock(send_task=mock_send_task),
        ),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/v1/admin/reindex")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert response.json() == {"dispatched": 2}
    assert mock_send_task.call_count == 2


# ── T015: non-admin gets 403 from bulk reindex ────────────────────────────────

def test_bulk_reindex_non_admin_returns_403():
    """A non-admin authenticated user calling POST /admin/reindex receives 403."""
    app = _make_app()

    with (
        _admin_auth_patch(is_admin=False),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/v1/admin/reindex")

    assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


# ── T016: bulk reindex returns 0 when all docs already have chunks ─────────────

def test_bulk_reindex_skips_docs_with_existing_chunks():
    """When all published docs already have chunks, dispatched count is 0 and no tasks are sent."""
    app = _make_app()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = []  # no docs without chunks
    mock_session.execute = AsyncMock(return_value=mock_result)

    @asynccontextmanager
    async def _fake_get_db():
        yield mock_session

    mock_send_task = MagicMock()

    with (
        _admin_auth_patch(is_admin=True),
        patch("tessera_api.adapters.database.get_db", _fake_get_db),
        patch(
            "tessera_api.adapters.celery.get_celery_app",
            return_value=MagicMock(send_task=mock_send_task),
        ),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/v1/admin/reindex")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert response.json() == {"dispatched": 0}
    assert mock_send_task.call_count == 0
