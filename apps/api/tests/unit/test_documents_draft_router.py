"""Unit tests for the document draft endpoints (GET/PUT /draft, POST /draft/finish)."""

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
def _with_company_context(user_id: str | None = None, company_id: uuid.UUID | None = None):
    from tessera_api.auth.oidc import require_company_member
    from tessera_api.main import app
    from tessera_core.domain.entities import CompanyMembership, CompanyRole

    uid = user_id or str(uuid.uuid4())
    info = {"sub": uid, "id": uid, "email": "test@test.com", "is_admin": False}
    cid = company_id or uuid.uuid4()
    membership = CompanyMembership(
        id=uuid.uuid4(), user_id=uuid.UUID(uid), company_id=cid, role=CompanyRole.MEMBER
    )

    async def _fake():
        return info, cid, membership

    app.dependency_overrides[require_company_member] = _fake
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_company_member, None)


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


def _build_doc(doc_id: uuid.UUID, space_id: uuid.UUID, version_id: uuid.UUID | None = None):
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


def _build_version(version_id: uuid.UUID, doc_id: uuid.UUID, content_markdown: str = "content"):
    from tessera_core.domain.entities import DocumentVersion

    return DocumentVersion(
        id=version_id,
        document_id=doc_id,
        version_number=1,
        content_markdown=content_markdown,
        frontmatter={},
    )


def _build_user(user_id: uuid.UUID):
    from tessera_core.domain.entities import User

    return User(
        id=user_id,
        external_subject=f"sub-{user_id}",
        email="user@test.com",
        display_name="User",
    )


def _build_membership(space_id: uuid.UUID, user_id: uuid.UUID, role):
    from tessera_core.domain.entities import SpaceMembership

    return SpaceMembership(space_id=space_id, user_id=user_id, role=role)


def _build_draft(
    document_id: uuid.UUID, editor_user_id: uuid.UUID, content_markdown: str = "draft content"
):
    from datetime import UTC, datetime

    from tessera_core.domain.entities import DocumentDraft

    now = datetime.now(UTC)
    return DocumentDraft(
        document_id=document_id,
        content_markdown=content_markdown,
        editor_user_id=editor_user_id,
        started_at=now,
        last_autosaved_at=now,
    )


@contextmanager
def _patched_router(
    *,
    doc_repo=None,
    membership_repo=None,
    draft_repo=None,
    user_repo=None,
    version_repo=None,
    audit=None,
):
    with (
        patch(
            "tessera_api.routers.documents.SqlDocumentRepository",
            return_value=doc_repo or MagicMock(),
        ),
        patch(
            "tessera_api.routers.documents.SqlSpaceMembershipRepository",
            return_value=membership_repo or MagicMock(),
        ),
        patch(
            "tessera_api.routers.documents.SqlDocumentDraftRepository",
            return_value=draft_repo or MagicMock(),
        ),
        patch(
            "tessera_api.routers.documents.SqlUserRepository", return_value=user_repo or MagicMock()
        ),
        patch(
            "tessera_api.routers.documents.SqlDocumentVersionRepository",
            return_value=version_repo or MagicMock(),
        ),
        patch("tessera_api.routers.documents.write_audit", new=audit or AsyncMock()),
    ):
        yield


class TestGetPutDraft:
    def test_put_draft_as_editor_creates_and_returns_draft(self):
        from tessera_api.main import app
        from tessera_core.domain.entities import SpaceRole

        editor_id = uuid.uuid4()
        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        doc = _build_doc(doc_id, space_id)
        editor = _build_user(editor_id)
        draft = _build_draft(doc_id, editor_id, content_markdown="new content")

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
        mock_membership_repo = MagicMock()
        mock_membership_repo.list_by_space = AsyncMock(
            return_value=[_build_membership(space_id, editor_id, SpaceRole.EDITOR)]
        )
        mock_draft_repo = MagicMock()
        mock_draft_repo.upsert_for_company = AsyncMock(return_value=draft)
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=editor)

        patches = _patched_router(
            doc_repo=mock_doc_repo,
            membership_repo=mock_membership_repo,
            draft_repo=mock_draft_repo,
            user_repo=mock_user_repo,
        )

        with (
            _bypass_onboarding(),
            _with_company_context(user_id=str(editor_id)),
            _with_db(),
            patches,
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.put(
                f"/v1/documents/{doc_id}/draft", json={"content_markdown": "new content"}
            )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["draft"]["content_markdown"] == "new content"
        assert mock_draft_repo.upsert_for_company.called

    def test_put_draft_as_viewer_returns_403(self):
        from tessera_api.main import app
        from tessera_core.domain.entities import SpaceRole

        viewer_id = uuid.uuid4()
        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        doc = _build_doc(doc_id, space_id)
        viewer = _build_user(viewer_id)

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
        mock_membership_repo = MagicMock()
        mock_membership_repo.list_by_space = AsyncMock(
            return_value=[_build_membership(space_id, viewer_id, SpaceRole.VIEWER)]
        )
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=viewer)

        patches = _patched_router(
            doc_repo=mock_doc_repo, membership_repo=mock_membership_repo, user_repo=mock_user_repo
        )

        with (
            _bypass_onboarding(),
            _with_company_context(user_id=str(viewer_id)),
            _with_db(),
            patches,
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.put(f"/v1/documents/{doc_id}/draft", json={"content_markdown": "x"})

        assert response.status_code == 403, response.text

    def test_put_draft_as_non_member_returns_403(self):
        from tessera_api.main import app

        non_member_id = uuid.uuid4()
        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        doc = _build_doc(doc_id, space_id)
        non_member = _build_user(non_member_id)

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
        mock_membership_repo = MagicMock()
        mock_membership_repo.list_by_space = AsyncMock(return_value=[])
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=non_member)

        patches = _patched_router(
            doc_repo=mock_doc_repo, membership_repo=mock_membership_repo, user_repo=mock_user_repo
        )

        with (
            _bypass_onboarding(),
            _with_company_context(user_id=str(non_member_id)),
            _with_db(),
            patches,
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.put(f"/v1/documents/{doc_id}/draft", json={"content_markdown": "x"})

        assert response.status_code == 403, response.text

    def test_put_draft_cross_tenant_returns_404_and_audits(self):
        from tessera_api.main import app

        actor_id = uuid.uuid4()
        doc_id = uuid.uuid4()

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=None)
        mock_audit = AsyncMock()

        patches = _patched_router(doc_repo=mock_doc_repo, audit=mock_audit)

        with (
            _bypass_onboarding(),
            _with_company_context(user_id=str(actor_id)),
            _with_db(),
            patches,
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.put(f"/v1/documents/{doc_id}/draft", json={"content_markdown": "x"})

        assert response.status_code == 404, response.text
        assert response.json() == {"error": {"code": "not_found", "message": "Not found"}}
        assert mock_audit.called
        assert mock_audit.call_args.kwargs["action"] == "cross_tenant_denied"

    def test_get_draft_cross_tenant_returns_404_and_audits(self):
        from tessera_api.main import app

        actor_id = uuid.uuid4()
        doc_id = uuid.uuid4()

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=None)
        mock_audit = AsyncMock()

        patches = _patched_router(doc_repo=mock_doc_repo, audit=mock_audit)

        with (
            _bypass_onboarding(),
            _with_company_context(user_id=str(actor_id)),
            _with_db(),
            patches,
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.get(f"/v1/documents/{doc_id}/draft")

        assert response.status_code == 404, response.text
        assert response.json() == {"error": {"code": "not_found", "message": "Not found"}}
        assert mock_audit.called
        assert mock_audit.call_args.kwargs["action"] == "cross_tenant_denied"

    def test_get_draft_returns_null_when_none_exists(self):
        from tessera_api.main import app
        from tessera_core.domain.entities import SpaceRole

        editor_id = uuid.uuid4()
        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        doc = _build_doc(doc_id, space_id)
        editor = _build_user(editor_id)

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
        mock_membership_repo = MagicMock()
        mock_membership_repo.list_by_space = AsyncMock(
            return_value=[_build_membership(space_id, editor_id, SpaceRole.EDITOR)]
        )
        mock_draft_repo = MagicMock()
        mock_draft_repo.get_by_document_id_for_company = AsyncMock(return_value=None)
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=editor)

        patches = _patched_router(
            doc_repo=mock_doc_repo,
            membership_repo=mock_membership_repo,
            draft_repo=mock_draft_repo,
            user_repo=mock_user_repo,
        )

        with (
            _bypass_onboarding(),
            _with_company_context(user_id=str(editor_id)),
            _with_db(),
            patches,
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.get(f"/v1/documents/{doc_id}/draft")

        assert response.status_code == 200, response.text
        assert response.json() == {"draft": None}

    def test_get_draft_returns_persisted_shape_after_put(self):
        from tessera_api.main import app
        from tessera_core.domain.entities import SpaceRole

        editor_id = uuid.uuid4()
        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        doc = _build_doc(doc_id, space_id)
        editor = _build_user(editor_id)
        draft = _build_draft(doc_id, editor_id, content_markdown="persisted content")

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
        mock_membership_repo = MagicMock()
        mock_membership_repo.list_by_space = AsyncMock(
            return_value=[_build_membership(space_id, editor_id, SpaceRole.EDITOR)]
        )
        mock_draft_repo = MagicMock()
        mock_draft_repo.get_by_document_id_for_company = AsyncMock(return_value=draft)
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=editor)

        patches = _patched_router(
            doc_repo=mock_doc_repo,
            membership_repo=mock_membership_repo,
            draft_repo=mock_draft_repo,
            user_repo=mock_user_repo,
        )

        with (
            _bypass_onboarding(),
            _with_company_context(user_id=str(editor_id)),
            _with_db(),
            patches,
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.get(f"/v1/documents/{doc_id}/draft")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["draft"]["content_markdown"] == "persisted content"
        assert body["draft"]["editor_user_id"] == str(editor_id)


class TestFinishDraft:
    def test_finish_with_differing_draft_creates_new_version(self):
        from tessera_api.main import app
        from tessera_core.domain.entities import SpaceRole

        editor_id = uuid.uuid4()
        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        current_version_id = uuid.uuid4()
        new_version_id = uuid.uuid4()

        doc = _build_doc(doc_id, space_id, version_id=current_version_id)
        current_version = _build_version(current_version_id, doc_id, content_markdown="old content")
        draft = _build_draft(doc_id, editor_id, content_markdown="new edited content")
        new_version = _build_version(new_version_id, doc_id, content_markdown="new edited content")
        editor = _build_user(editor_id)
        updated_doc = doc.model_copy(update={"current_version_id": new_version_id})

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
        mock_doc_repo.set_current_version = AsyncMock(return_value=updated_doc)

        mock_membership_repo = MagicMock()
        mock_membership_repo.list_by_space = AsyncMock(
            return_value=[_build_membership(space_id, editor_id, SpaceRole.EDITOR)]
        )

        mock_draft_repo = MagicMock()
        mock_draft_repo.get_by_document_id_for_company = AsyncMock(return_value=draft)
        mock_draft_repo.delete_for_company = AsyncMock()

        mock_ver_repo = MagicMock()
        mock_ver_repo.get_by_id = AsyncMock(return_value=current_version)
        mock_ver_repo.next_version_number = AsyncMock(return_value=2)
        mock_ver_repo.create = AsyncMock(return_value=new_version)

        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=editor)

        mock_audit = AsyncMock()

        patches = _patched_router(
            doc_repo=mock_doc_repo,
            membership_repo=mock_membership_repo,
            draft_repo=mock_draft_repo,
            user_repo=mock_user_repo,
            version_repo=mock_ver_repo,
            audit=mock_audit,
        )

        with (
            _bypass_onboarding(),
            _with_company_context(user_id=str(editor_id)),
            _with_db(),
            patches,
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(f"/v1/documents/{doc_id}/draft/finish")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["version"]["content_markdown"] == "new edited content"
        assert mock_ver_repo.create.called
        assert mock_doc_repo.set_current_version.called
        assert mock_draft_repo.delete_for_company.called
        assert mock_audit.call_count == 1
        assert mock_audit.call_args.kwargs["action"] == "document_edited"

    def test_finish_with_no_draft_returns_null_version(self):
        from tessera_api.main import app
        from tessera_core.domain.entities import SpaceRole

        editor_id = uuid.uuid4()
        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        current_version_id = uuid.uuid4()
        doc = _build_doc(doc_id, space_id, version_id=current_version_id)
        current_version = _build_version(current_version_id, doc_id, content_markdown="content")
        editor = _build_user(editor_id)

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
        mock_doc_repo.set_current_version = AsyncMock()

        mock_membership_repo = MagicMock()
        mock_membership_repo.list_by_space = AsyncMock(
            return_value=[_build_membership(space_id, editor_id, SpaceRole.EDITOR)]
        )

        mock_draft_repo = MagicMock()
        mock_draft_repo.get_by_document_id_for_company = AsyncMock(return_value=None)
        mock_draft_repo.delete_for_company = AsyncMock()

        mock_ver_repo = MagicMock()
        mock_ver_repo.get_by_id = AsyncMock(return_value=current_version)
        mock_ver_repo.create = AsyncMock()

        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=editor)

        mock_audit = AsyncMock()

        patches = _patched_router(
            doc_repo=mock_doc_repo,
            membership_repo=mock_membership_repo,
            draft_repo=mock_draft_repo,
            user_repo=mock_user_repo,
            version_repo=mock_ver_repo,
            audit=mock_audit,
        )

        with (
            _bypass_onboarding(),
            _with_company_context(user_id=str(editor_id)),
            _with_db(),
            patches,
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(f"/v1/documents/{doc_id}/draft/finish")

        assert response.status_code == 200, response.text
        assert response.json() == {"version": None}
        assert not mock_ver_repo.create.called
        assert not mock_doc_repo.set_current_version.called
        assert not mock_audit.called

    def test_finish_with_unchanged_content_returns_null_version_and_deletes_draft(self):
        from tessera_api.main import app
        from tessera_core.domain.entities import SpaceRole

        editor_id = uuid.uuid4()
        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        current_version_id = uuid.uuid4()
        doc = _build_doc(doc_id, space_id, version_id=current_version_id)
        current_version = _build_version(
            current_version_id, doc_id, content_markdown="same content"
        )
        draft = _build_draft(doc_id, editor_id, content_markdown="same content")
        editor = _build_user(editor_id)

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
        mock_doc_repo.set_current_version = AsyncMock()

        mock_membership_repo = MagicMock()
        mock_membership_repo.list_by_space = AsyncMock(
            return_value=[_build_membership(space_id, editor_id, SpaceRole.EDITOR)]
        )

        mock_draft_repo = MagicMock()
        mock_draft_repo.get_by_document_id_for_company = AsyncMock(return_value=draft)
        mock_draft_repo.delete_for_company = AsyncMock()

        mock_ver_repo = MagicMock()
        mock_ver_repo.get_by_id = AsyncMock(return_value=current_version)
        mock_ver_repo.create = AsyncMock()

        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=editor)

        mock_audit = AsyncMock()

        patches = _patched_router(
            doc_repo=mock_doc_repo,
            membership_repo=mock_membership_repo,
            draft_repo=mock_draft_repo,
            user_repo=mock_user_repo,
            version_repo=mock_ver_repo,
            audit=mock_audit,
        )

        with (
            _bypass_onboarding(),
            _with_company_context(user_id=str(editor_id)),
            _with_db(),
            patches,
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(f"/v1/documents/{doc_id}/draft/finish")

        assert response.status_code == 200, response.text
        assert response.json() == {"version": None}
        assert mock_draft_repo.delete_for_company.called
        assert not mock_ver_repo.create.called
        assert not mock_audit.called

    def test_finish_as_viewer_returns_403(self):
        from tessera_api.main import app
        from tessera_core.domain.entities import SpaceRole

        viewer_id = uuid.uuid4()
        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        doc = _build_doc(doc_id, space_id)
        viewer = _build_user(viewer_id)

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
        mock_membership_repo = MagicMock()
        mock_membership_repo.list_by_space = AsyncMock(
            return_value=[_build_membership(space_id, viewer_id, SpaceRole.VIEWER)]
        )
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=viewer)

        patches = _patched_router(
            doc_repo=mock_doc_repo, membership_repo=mock_membership_repo, user_repo=mock_user_repo
        )

        with (
            _bypass_onboarding(),
            _with_company_context(user_id=str(viewer_id)),
            _with_db(),
            patches,
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(f"/v1/documents/{doc_id}/draft/finish")

        assert response.status_code == 403, response.text

    def test_finish_cross_tenant_returns_404_and_audits(self):
        from tessera_api.main import app

        actor_id = uuid.uuid4()
        doc_id = uuid.uuid4()

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=None)
        mock_audit = AsyncMock()

        patches = _patched_router(doc_repo=mock_doc_repo, audit=mock_audit)

        with (
            _bypass_onboarding(),
            _with_company_context(user_id=str(actor_id)),
            _with_db(),
            patches,
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(f"/v1/documents/{doc_id}/draft/finish")

        assert response.status_code == 404, response.text
        assert response.json() == {"error": {"code": "not_found", "message": "Not found"}}
        assert mock_audit.called
        assert mock_audit.call_args.kwargs["action"] == "cross_tenant_denied"
