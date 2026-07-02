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
def _with_company_member_context(
    user_id: str | None = None, company_id: uuid.UUID | None = None, role=None
):
    from tessera_api.auth.oidc import require_company_member
    from tessera_api.main import app
    from tessera_core.domain.entities import CompanyMembership, CompanyRole

    uid = user_id or str(uuid.uuid4())
    info = {"sub": uid, "id": uid, "email": "test@test.com", "is_admin": False}
    cid = company_id or uuid.uuid4()
    membership = CompanyMembership(
        id=uuid.uuid4(), user_id=uuid.UUID(uid), company_id=cid, role=role or CompanyRole.MEMBER
    )

    async def _fake():
        return info, cid, membership

    app.dependency_overrides[require_company_member] = _fake
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_company_member, None)


def _build_membership(space_id: uuid.UUID, user_id: uuid.UUID, role):
    from tessera_core.domain.entities import SpaceMembership

    return SpaceMembership(space_id=space_id, user_id=user_id, role=role)


def _build_user(user_id: uuid.UUID):
    from tessera_core.domain.entities import User

    return User(
        id=user_id,
        external_subject=f"sub-{user_id}",
        email="user@test.com",
        display_name="User",
    )


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
        patch(
            "tessera_api.routers.documents.SqlDocumentVersionRepository", return_value=mock_ver_repo
        ),
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


def _build_doc_with_owner(doc_id: uuid.UUID, space_id: uuid.UUID, owner_user_id: uuid.UUID):
    from tessera_core.domain.entities import Confidentiality, Document, DocumentLifecycleState

    return Document(
        id=doc_id,
        space_id=space_id,
        owner_user_id=owner_user_id,
        title="Test Doc",
        language="en",
        confidentiality=Confidentiality.INTERNAL,
        tags=[],
        state=DocumentLifecycleState.PUBLISHED,
    )


def test_owner_delete_returns_200_and_calls_repo_delete():
    from tessera_api.main import app

    owner_id = uuid.uuid4()
    space_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    doc = _build_doc_with_owner(doc_id, space_id, owner_id)
    owner = _build_user(owner_id)

    mock_doc_repo = MagicMock()
    mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
    mock_doc_repo.delete = AsyncMock()
    mock_membership_repo = MagicMock()
    mock_membership_repo.list_by_space = AsyncMock(return_value=[])
    mock_user_repo = MagicMock()
    mock_user_repo.get_by_id = AsyncMock(return_value=owner)

    with (
        _bypass_onboarding(),
        _with_company_member_context(user_id=str(owner_id)),
        _with_db(),
        patch("tessera_api.routers.documents.SqlDocumentRepository", return_value=mock_doc_repo),
        patch(
            "tessera_api.routers.documents.SqlSpaceMembershipRepository",
            return_value=mock_membership_repo,
        ),
        patch("tessera_api.routers.documents.SqlUserRepository", return_value=mock_user_repo),
        patch("tessera_api.routers.documents.write_audit", new=AsyncMock()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.delete(f"/v1/documents/{doc_id}")

    assert response.status_code == 200, response.text
    assert response.json() == {"deleted": True, "document_id": str(doc_id)}
    mock_doc_repo.delete.assert_awaited_once_with(doc_id)


def test_delete_writes_audit_record():
    from tessera_api.main import app

    owner_id = uuid.uuid4()
    space_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    doc = _build_doc_with_owner(doc_id, space_id, owner_id)
    owner = _build_user(owner_id)

    mock_doc_repo = MagicMock()
    mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
    mock_doc_repo.delete = AsyncMock()
    mock_membership_repo = MagicMock()
    mock_membership_repo.list_by_space = AsyncMock(return_value=[])
    mock_user_repo = MagicMock()
    mock_user_repo.get_by_id = AsyncMock(return_value=owner)
    mock_audit = AsyncMock()

    with (
        _bypass_onboarding(),
        _with_company_member_context(user_id=str(owner_id)),
        _with_db(),
        patch("tessera_api.routers.documents.SqlDocumentRepository", return_value=mock_doc_repo),
        patch(
            "tessera_api.routers.documents.SqlSpaceMembershipRepository",
            return_value=mock_membership_repo,
        ),
        patch("tessera_api.routers.documents.SqlUserRepository", return_value=mock_user_repo),
        patch("tessera_api.routers.documents.write_audit", new=mock_audit),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.delete(f"/v1/documents/{doc_id}")

    assert response.status_code == 200, response.text
    assert mock_audit.called
    assert mock_audit.call_args.kwargs["action"] == "document_deleted"
    assert mock_audit.call_args.kwargs["entity_type"] == "document"
    assert mock_audit.call_args.kwargs["entity_id"] == doc_id


def test_non_owner_non_admin_delete_returns_403():
    from tessera_api.main import app
    from tessera_core.domain.entities import SpaceRole

    editor_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    space_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    doc = _build_doc_with_owner(doc_id, space_id, owner_id)
    editor = _build_user(editor_id)

    mock_doc_repo = MagicMock()
    mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
    mock_doc_repo.delete = AsyncMock()
    mock_membership_repo = MagicMock()
    mock_membership_repo.list_by_space = AsyncMock(
        return_value=[_build_membership(space_id, editor_id, SpaceRole.EDITOR)]
    )
    mock_user_repo = MagicMock()
    mock_user_repo.get_by_id = AsyncMock(return_value=editor)

    with (
        _bypass_onboarding(),
        _with_company_member_context(user_id=str(editor_id)),
        _with_db(),
        patch("tessera_api.routers.documents.SqlDocumentRepository", return_value=mock_doc_repo),
        patch(
            "tessera_api.routers.documents.SqlSpaceMembershipRepository",
            return_value=mock_membership_repo,
        ),
        patch("tessera_api.routers.documents.SqlUserRepository", return_value=mock_user_repo),
        patch("tessera_api.routers.documents.write_audit", new=AsyncMock()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.delete(f"/v1/documents/{doc_id}")

    assert response.status_code == 403, response.text
    assert not mock_doc_repo.delete.called


def test_delete_cross_tenant_returns_404_and_audits():
    from tessera_api.main import app

    actor_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    mock_doc_repo = MagicMock()
    mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=None)
    mock_doc_repo.delete = AsyncMock()
    mock_audit = AsyncMock()

    with (
        _bypass_onboarding(),
        _with_company_member_context(user_id=str(actor_id)),
        _with_db(),
        patch("tessera_api.routers.documents.SqlDocumentRepository", return_value=mock_doc_repo),
        patch("tessera_api.routers.documents.write_audit", new=mock_audit),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.delete(f"/v1/documents/{doc_id}")

    assert response.status_code == 404, response.text
    assert response.json() == {"error": {"code": "not_found", "message": "Not found"}}
    assert mock_audit.called
    assert mock_audit.call_args.kwargs["action"] == "cross_tenant_denied"
    assert not mock_doc_repo.delete.called


def test_space_admin_non_owner_delete_returns_200():
    from tessera_api.main import app
    from tessera_core.domain.entities import SpaceRole

    admin_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    space_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    doc = _build_doc_with_owner(doc_id, space_id, owner_id)
    admin_user = _build_user(admin_id)

    mock_doc_repo = MagicMock()
    mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
    mock_doc_repo.delete = AsyncMock()
    mock_membership_repo = MagicMock()
    mock_membership_repo.list_by_space = AsyncMock(
        return_value=[_build_membership(space_id, admin_id, SpaceRole.ADMIN)]
    )
    mock_user_repo = MagicMock()
    mock_user_repo.get_by_id = AsyncMock(return_value=admin_user)

    with (
        _bypass_onboarding(),
        _with_company_member_context(user_id=str(admin_id)),
        _with_db(),
        patch("tessera_api.routers.documents.SqlDocumentRepository", return_value=mock_doc_repo),
        patch(
            "tessera_api.routers.documents.SqlSpaceMembershipRepository",
            return_value=mock_membership_repo,
        ),
        patch("tessera_api.routers.documents.SqlUserRepository", return_value=mock_user_repo),
        patch("tessera_api.routers.documents.write_audit", new=AsyncMock()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.delete(f"/v1/documents/{doc_id}")

    assert response.status_code == 200, response.text
    mock_doc_repo.delete.assert_awaited_once_with(doc_id)


def test_company_admin_non_owner_delete_returns_200():
    from tessera_api.main import app
    from tessera_core.domain.entities import CompanyRole

    admin_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    space_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    doc = _build_doc_with_owner(doc_id, space_id, owner_id)
    admin_user = _build_user(admin_id)

    mock_doc_repo = MagicMock()
    mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
    mock_doc_repo.delete = AsyncMock()
    mock_membership_repo = MagicMock()
    mock_membership_repo.list_by_space = AsyncMock(return_value=[])
    mock_user_repo = MagicMock()
    mock_user_repo.get_by_id = AsyncMock(return_value=admin_user)

    with (
        _bypass_onboarding(),
        _with_company_member_context(user_id=str(admin_id), role=CompanyRole.ADMIN),
        _with_db(),
        patch("tessera_api.routers.documents.SqlDocumentRepository", return_value=mock_doc_repo),
        patch(
            "tessera_api.routers.documents.SqlSpaceMembershipRepository",
            return_value=mock_membership_repo,
        ),
        patch("tessera_api.routers.documents.SqlUserRepository", return_value=mock_user_repo),
        patch("tessera_api.routers.documents.write_audit", new=AsyncMock()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.delete(f"/v1/documents/{doc_id}")

    assert response.status_code == 200, response.text
    mock_doc_repo.delete.assert_awaited_once_with(doc_id)
