"""Unit tests for the document-assist router (draft generation, revision)."""

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


def _build_doc(doc_id: uuid.UUID, space_id: uuid.UUID):
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
    )


class TestDraftAssistEndpoint:
    def test_editor_gets_200_with_content_markdown(self):
        from tessera_api.ai_assist.prompts import LANGUAGE_MATCH_RULE
        from tessera_api.main import app
        from tessera_core.domain.entities import SpaceRole

        space_id = uuid.uuid4()
        editor_id = uuid.uuid4()
        editor = _build_user(editor_id)

        mock_space_repo = MagicMock()
        mock_space_repo.get_by_id_for_company = AsyncMock(return_value=MagicMock(id=space_id))
        mock_membership_repo = MagicMock()
        mock_membership_repo.list_by_space = AsyncMock(
            return_value=[_build_membership(space_id, editor_id, SpaceRole.EDITOR)]
        )
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=editor)

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="# Onboarding\n\nWelcome!")
        mock_audit = AsyncMock()

        with (
            _bypass_onboarding(),
            _with_company_member_context(user_id=str(editor_id)),
            _with_db(),
            patch(
                "tessera_api.routers.document_assist.SqlSpaceRepository",
                return_value=mock_space_repo,
            ),
            patch(
                "tessera_api.routers.document_assist.SqlSpaceMembershipRepository",
                return_value=mock_membership_repo,
            ),
            patch(
                "tessera_api.routers.document_assist.SqlUserRepository",
                return_value=mock_user_repo,
            ),
            patch(
                "tessera_api.routers.document_assist.AnthropicLLMProvider",
                return_value=mock_llm,
            ),
            patch("tessera_api.routers.document_assist.write_audit", new=mock_audit),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                "/v1/documents/assist/draft",
                json={"space_id": str(space_id), "prompt": "Onboarding checklist"},
            )

        assert response.status_code == 200, response.text
        assert response.json() == {"content_markdown": "# Onboarding\n\nWelcome!"}

        assert mock_llm.complete.called
        call_kwargs = mock_llm.complete.call_args.kwargs
        assert LANGUAGE_MATCH_RULE in call_kwargs["system"]
        assert "Onboarding checklist" in call_kwargs["system"]

    def test_non_editor_gets_403(self):
        from tessera_api.main import app
        from tessera_core.domain.entities import SpaceRole

        space_id = uuid.uuid4()
        viewer_id = uuid.uuid4()
        viewer = _build_user(viewer_id)

        mock_space_repo = MagicMock()
        mock_space_repo.get_by_id_for_company = AsyncMock(return_value=MagicMock(id=space_id))
        mock_membership_repo = MagicMock()
        mock_membership_repo.list_by_space = AsyncMock(
            return_value=[_build_membership(space_id, viewer_id, SpaceRole.VIEWER)]
        )
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=viewer)

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="should not be called")

        with (
            _bypass_onboarding(),
            _with_company_member_context(user_id=str(viewer_id)),
            _with_db(),
            patch(
                "tessera_api.routers.document_assist.SqlSpaceRepository",
                return_value=mock_space_repo,
            ),
            patch(
                "tessera_api.routers.document_assist.SqlSpaceMembershipRepository",
                return_value=mock_membership_repo,
            ),
            patch(
                "tessera_api.routers.document_assist.SqlUserRepository",
                return_value=mock_user_repo,
            ),
            patch(
                "tessera_api.routers.document_assist.AnthropicLLMProvider",
                return_value=mock_llm,
            ),
            patch("tessera_api.routers.document_assist.write_audit", new=AsyncMock()),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                "/v1/documents/assist/draft",
                json={"space_id": str(space_id), "prompt": "Onboarding checklist"},
            )

        assert response.status_code == 403, response.text
        assert not mock_llm.complete.called

    def test_blank_prompt_returns_422_without_calling_llm(self):
        from tessera_api.main import app

        space_id = uuid.uuid4()
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="should not be called")

        with (
            _bypass_onboarding(),
            _with_company_member_context(),
            _with_db(),
            patch(
                "tessera_api.routers.document_assist.AnthropicLLMProvider",
                return_value=mock_llm,
            ),
            patch("tessera_api.routers.document_assist.write_audit", new=AsyncMock()),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                "/v1/documents/assist/draft",
                json={"space_id": str(space_id), "prompt": "   "},
            )

        assert response.status_code == 422, response.text
        assert not mock_llm.complete.called

    def test_writes_audit_record_on_success(self):
        from tessera_api.main import app
        from tessera_core.domain.entities import SpaceRole

        space_id = uuid.uuid4()
        editor_id = uuid.uuid4()
        editor = _build_user(editor_id)

        mock_space_repo = MagicMock()
        mock_space_repo.get_by_id_for_company = AsyncMock(return_value=MagicMock(id=space_id))
        mock_membership_repo = MagicMock()
        mock_membership_repo.list_by_space = AsyncMock(
            return_value=[_build_membership(space_id, editor_id, SpaceRole.EDITOR)]
        )
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=editor)

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="# Draft")
        mock_audit = AsyncMock()

        with (
            _bypass_onboarding(),
            _with_company_member_context(user_id=str(editor_id)),
            _with_db(),
            patch(
                "tessera_api.routers.document_assist.SqlSpaceRepository",
                return_value=mock_space_repo,
            ),
            patch(
                "tessera_api.routers.document_assist.SqlSpaceMembershipRepository",
                return_value=mock_membership_repo,
            ),
            patch(
                "tessera_api.routers.document_assist.SqlUserRepository",
                return_value=mock_user_repo,
            ),
            patch(
                "tessera_api.routers.document_assist.AnthropicLLMProvider",
                return_value=mock_llm,
            ),
            patch("tessera_api.routers.document_assist.write_audit", new=mock_audit),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                "/v1/documents/assist/draft",
                json={"space_id": str(space_id), "prompt": "Onboarding checklist"},
            )

        assert response.status_code == 200, response.text
        assert mock_audit.called
        assert mock_audit.call_args.kwargs["action"] == "ai_draft_requested"
        assert mock_audit.call_args.kwargs["entity_type"] == "space"
        assert mock_audit.call_args.kwargs["entity_id"] == space_id


class TestRevisionAssistEndpoint:
    def test_editor_gets_200_with_suggestion(self):
        from tessera_api.ai_assist.prompts import LANGUAGE_MATCH_RULE
        from tessera_api.main import app
        from tessera_core.domain.entities import SpaceRole

        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        editor_id = uuid.uuid4()
        editor = _build_user(editor_id)
        doc = _build_doc(doc_id, space_id)

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
        mock_membership_repo = MagicMock()
        mock_membership_repo.list_by_space = AsyncMock(
            return_value=[_build_membership(space_id, editor_id, SpaceRole.EDITOR)]
        )
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=editor)

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="Revised content.")
        mock_audit = AsyncMock()

        with (
            _bypass_onboarding(),
            _with_company_member_context(user_id=str(editor_id)),
            _with_db(),
            patch(
                "tessera_api.routers.documents.SqlDocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "tessera_api.routers.documents.SqlSpaceMembershipRepository",
                return_value=mock_membership_repo,
            ),
            patch(
                "tessera_api.routers.documents.SqlUserRepository",
                return_value=mock_user_repo,
            ),
            patch(
                "tessera_api.routers.document_assist.AnthropicLLMProvider",
                return_value=mock_llm,
            ),
            patch("tessera_api.routers.document_assist.write_audit", new=mock_audit),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                f"/v1/documents/{doc_id}/assist/revise",
                json={"content": "Original content.", "instruction": "make it shorter"},
            )

        assert response.status_code == 200, response.text
        assert response.json() == {"suggestion": "Revised content."}
        call_kwargs = mock_llm.complete.call_args.kwargs
        assert LANGUAGE_MATCH_RULE in call_kwargs["system"]

    def test_empty_instruction_falls_back_to_content_language_matching(self):
        from tessera_api.main import app
        from tessera_core.domain.entities import SpaceRole

        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        editor_id = uuid.uuid4()
        editor = _build_user(editor_id)
        doc = _build_doc(doc_id, space_id)

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
        mock_membership_repo = MagicMock()
        mock_membership_repo.list_by_space = AsyncMock(
            return_value=[_build_membership(space_id, editor_id, SpaceRole.EDITOR)]
        )
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=editor)

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="Suggestion.")

        with (
            _bypass_onboarding(),
            _with_company_member_context(user_id=str(editor_id)),
            _with_db(),
            patch(
                "tessera_api.routers.documents.SqlDocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "tessera_api.routers.documents.SqlSpaceMembershipRepository",
                return_value=mock_membership_repo,
            ),
            patch(
                "tessera_api.routers.documents.SqlUserRepository",
                return_value=mock_user_repo,
            ),
            patch(
                "tessera_api.routers.document_assist.AnthropicLLMProvider",
                return_value=mock_llm,
            ),
            patch("tessera_api.routers.document_assist.write_audit", new=AsyncMock()),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                f"/v1/documents/{doc_id}/assist/revise",
                json={"content": "Conteúdo original.", "instruction": ""},
            )

        assert response.status_code == 200, response.text
        call_kwargs = mock_llm.complete.call_args.kwargs
        assert "Instruction:" not in call_kwargs["system"]
        assert "Conteúdo original." in call_kwargs["system"]

    def test_non_editor_gets_403(self):
        from tessera_api.main import app
        from tessera_core.domain.entities import SpaceRole

        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        viewer_id = uuid.uuid4()
        viewer = _build_user(viewer_id)
        doc = _build_doc(doc_id, space_id)

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
        mock_membership_repo = MagicMock()
        mock_membership_repo.list_by_space = AsyncMock(
            return_value=[_build_membership(space_id, viewer_id, SpaceRole.VIEWER)]
        )
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=viewer)

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="should not be called")

        with (
            _bypass_onboarding(),
            _with_company_member_context(user_id=str(viewer_id)),
            _with_db(),
            patch(
                "tessera_api.routers.documents.SqlDocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "tessera_api.routers.documents.SqlSpaceMembershipRepository",
                return_value=mock_membership_repo,
            ),
            patch(
                "tessera_api.routers.documents.SqlUserRepository",
                return_value=mock_user_repo,
            ),
            patch(
                "tessera_api.routers.document_assist.AnthropicLLMProvider",
                return_value=mock_llm,
            ),
            patch("tessera_api.routers.document_assist.write_audit", new=AsyncMock()),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                f"/v1/documents/{doc_id}/assist/revise",
                json={"content": "Original content.", "instruction": "make it shorter"},
            )

        assert response.status_code == 403, response.text
        assert not mock_llm.complete.called

    def test_nonexistent_document_returns_404(self):
        from tessera_api.main import app

        doc_id = uuid.uuid4()

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=None)
        mock_audit = AsyncMock()

        with (
            _bypass_onboarding(),
            _with_company_member_context(),
            _with_db(),
            patch(
                "tessera_api.routers.documents.SqlDocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch("tessera_api.routers.documents.write_audit", new=mock_audit),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                f"/v1/documents/{doc_id}/assist/revise",
                json={"content": "Original content.", "instruction": "make it shorter"},
            )

        assert response.status_code == 404, response.text
        assert response.json() == {"error": {"code": "not_found", "message": "Not found"}}

    def test_blank_content_returns_422_without_calling_llm(self):
        from tessera_api.main import app

        doc_id = uuid.uuid4()
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="should not be called")

        with (
            _bypass_onboarding(),
            _with_company_member_context(),
            _with_db(),
            patch(
                "tessera_api.routers.document_assist.AnthropicLLMProvider",
                return_value=mock_llm,
            ),
            patch("tessera_api.routers.document_assist.write_audit", new=AsyncMock()),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                f"/v1/documents/{doc_id}/assist/revise",
                json={"content": "   ", "instruction": "fix grammar"},
            )

        assert response.status_code == 422, response.text
        assert not mock_llm.complete.called

    def test_writes_audit_record_on_success(self):
        from tessera_api.main import app
        from tessera_core.domain.entities import SpaceRole

        space_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        editor_id = uuid.uuid4()
        editor = _build_user(editor_id)
        doc = _build_doc(doc_id, space_id)

        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=doc)
        mock_membership_repo = MagicMock()
        mock_membership_repo.list_by_space = AsyncMock(
            return_value=[_build_membership(space_id, editor_id, SpaceRole.EDITOR)]
        )
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=editor)

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="Revised content.")
        mock_audit = AsyncMock()

        with (
            _bypass_onboarding(),
            _with_company_member_context(user_id=str(editor_id)),
            _with_db(),
            patch(
                "tessera_api.routers.documents.SqlDocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "tessera_api.routers.documents.SqlSpaceMembershipRepository",
                return_value=mock_membership_repo,
            ),
            patch(
                "tessera_api.routers.documents.SqlUserRepository",
                return_value=mock_user_repo,
            ),
            patch(
                "tessera_api.routers.document_assist.AnthropicLLMProvider",
                return_value=mock_llm,
            ),
            patch("tessera_api.routers.document_assist.write_audit", new=mock_audit),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                f"/v1/documents/{doc_id}/assist/revise",
                json={"content": "Original content.", "instruction": "make it shorter"},
            )

        assert response.status_code == 200, response.text
        assert mock_audit.called
        assert mock_audit.call_args.kwargs["action"] == "ai_revision_requested"
        assert mock_audit.call_args.kwargs["entity_type"] == "document"
        assert mock_audit.call_args.kwargs["entity_id"] == doc_id
