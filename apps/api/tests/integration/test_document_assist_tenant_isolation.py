"""Integration tests: tenant isolation for the document-assist endpoints."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch


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


_GENERIC_NOT_FOUND = {"error": {"code": "not_found", "message": "Not found"}}


class TestDraftAssistTenantIsolation:
    def test_cross_tenant_space_id_returns_404_and_never_calls_llm(self, two_company_setup):
        """Company A's session calling assist/draft with Company B's space_id -> 404, audited."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        beta_space_id = uuid.uuid4()

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="should never be produced")
        mock_audit = AsyncMock()

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.document_assist.SqlSpaceRepository") as mock_space_cls,
            patch(
                "tessera_api.routers.document_assist.AnthropicLLMProvider",
                return_value=mock_llm,
            ),
            patch("tessera_api.routers.document_assist.write_audit", new=mock_audit),
        ):
            mock_space_repo = AsyncMock()
            mock_space_repo.get_by_id_for_company = AsyncMock(return_value=None)
            mock_space_cls.return_value = mock_space_repo

            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/documents/assist/draft",
                    json={"space_id": str(beta_space_id), "prompt": "steal Beta's content"},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert response.status_code == 404
        assert response.json() == _GENERIC_NOT_FOUND
        assert not mock_llm.complete.called
        assert mock_audit.called
        assert mock_audit.call_args.kwargs["action"] == "cross_tenant_denied"
        assert mock_audit.call_args.kwargs["entity_type"] == "space"


class TestRevisionAssistTenantIsolation:
    def test_cross_tenant_document_id_returns_404_and_never_calls_llm(self, two_company_setup):
        """Company A's session calling assist/revise with Company B's document_id -> 404, audited."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        beta_doc_id = uuid.uuid4()

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="should never be produced")
        mock_audit = AsyncMock()

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.documents.SqlDocumentRepository") as mock_doc_cls,
            patch(
                "tessera_api.routers.document_assist.AnthropicLLMProvider",
                return_value=mock_llm,
            ),
            patch("tessera_api.routers.documents.write_audit", new=mock_audit),
        ):
            mock_doc_repo = AsyncMock()
            mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=None)
            mock_doc_cls.return_value = mock_doc_repo

            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    f"/v1/documents/{beta_doc_id}/assist/revise",
                    json={"content": "steal Beta's content", "instruction": "shorten"},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert response.status_code == 404
        assert response.json() == _GENERIC_NOT_FOUND
        assert not mock_llm.complete.called
        assert mock_audit.called
        assert mock_audit.call_args.kwargs["action"] == "cross_tenant_denied"
        assert mock_audit.call_args.kwargs["entity_type"] == "document"
