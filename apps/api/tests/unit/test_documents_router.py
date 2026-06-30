"""Unit tests for documents router — TDD for Bug 3 fix (publish dispatches indexing task)."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


@contextmanager
def _bypass_onboarding():
    from tessera_api.auth.bearer import require_onboarding_complete
    from tessera_api.main import app

    async def _noop():
        return None

    app.dependency_overrides[require_onboarding_complete] = _noop
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_onboarding_complete, None)


@contextmanager
def _with_company_context(user_id: str | None = None):
    from tessera_api.auth.oidc import require_company_context
    from tessera_api.main import app

    uid = user_id or str(uuid.uuid4())
    info = {"sub": uid, "id": uid, "email": "test@test.com", "is_admin": False}

    async def _fake():
        return info, uuid.uuid4()

    app.dependency_overrides[require_company_context] = _fake
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_company_context, None)


@contextmanager
def _with_db(mock_session=None):
    from tessera_api.adapters.database import get_db
    from tessera_api.main import app

    if mock_session is None:
        mock_session = AsyncMock()

    async def _gen():
        yield mock_session

    app.dependency_overrides[get_db] = _gen
    try:
        yield mock_session
    finally:
        app.dependency_overrides.pop(get_db, None)


def _build_doc(doc_id: uuid.UUID, space_id: uuid.UUID, version_id: uuid.UUID):
    from tessera_core.domain.entities import Confidentiality, Document, DocumentLifecycleState

    return Document(
        id=doc_id,
        space_id=space_id,
        owner_user_id=uuid.uuid4(),
        title="Test Doc",
        language="en",
        confidentiality=Confidentiality.INTERNAL,
        tags=[],
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


def test_publish_dispatches_index_task():
    """After a successful publish, index_document_version.delay() must be called."""
    from tessera_api.main import app

    doc_id = uuid.uuid4()
    space_id = uuid.uuid4()
    version_id = uuid.uuid4()
    doc = _build_doc(doc_id, space_id, version_id)
    version = _build_version(version_id, doc_id)

    mock_doc_repo = MagicMock()
    mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
    mock_doc_repo.set_owner = AsyncMock(return_value=doc)
    mock_doc_repo.update_state = AsyncMock(return_value=doc)
    mock_doc_repo.set_current_version = AsyncMock(return_value=doc)

    mock_ver_repo = MagicMock()
    mock_ver_repo.list_by_document = AsyncMock(return_value=[version])
    mock_ver_repo.update_approval = AsyncMock(return_value=version)

    mock_delay = MagicMock()

    with (
        _bypass_onboarding(),
        _with_company_context(),
        _with_db(),
        patch("tessera_api.routers.documents.SqlDocumentRepository", return_value=mock_doc_repo),
        patch("tessera_api.routers.documents.SqlDocumentVersionRepository", return_value=mock_ver_repo),
        patch("tessera_api.routers.documents.write_audit", new=AsyncMock()),
        patch(
            "tessera_api.routers.documents.get_celery_app",
            return_value=MagicMock(send_task=mock_delay),
        ),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(f"/v1/documents/{doc_id}/publish")

    assert response.status_code == 200, f"Expected 200 got {response.status_code}: {response.text}"
    assert mock_delay.called, (
        "celery_app.send_task() was never called — "
        "publish_document does not dispatch the indexing task"
    )
    call_args = mock_delay.call_args
    task_name = call_args[0][0] if call_args[0] else call_args[1].get("name", "")
    sent_args = call_args[1].get("args") or (call_args[0][1] if len(call_args[0]) > 1 else [])
    assert "index_document_version" in task_name
    assert str(version_id) in sent_args
    assert str(doc_id) in sent_args
    assert str(space_id) in sent_args
