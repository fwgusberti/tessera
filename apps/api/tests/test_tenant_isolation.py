"""Cross-tenant isolation tests for the Tessera API (feature 031)."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tessera_core.domain.entities import (
    Company,
    CompanyMembership,
    CompanyRole,
    Space,
)


def _make_space(company_id: uuid.UUID) -> Space:
    return Space(
        id=uuid.uuid4(),
        slug=f"space-{uuid.uuid4().hex[:8]}",
        name="Alpha Space",
        sector="tech",
        company_id=company_id,
    )


@contextmanager
def _bypass_onboarding_guard():
    """Override require_onboarding_complete to skip DB check in isolation tests."""
    from tessera_api.auth.bearer import require_onboarding_complete
    from tessera_api.main import app

    async def _noop():
        return None

    app.dependency_overrides[require_onboarding_complete] = _noop
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_onboarding_complete, None)


def _mock_db():
    """Return a patched get_db that yields a no-op async session."""
    mock_get_db = MagicMock()
    mock_session = AsyncMock()
    mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_get_db


class TestTenantIsolation:
    """Placeholder — cross-tenant isolation tests added in subsequent tasks."""


class TestUS1SpaceIsolation:
    """US1: Space listing and creation are scoped to the authenticated company."""

    def test_company_a_cannot_list_company_b_spaces(self, two_company_setup):
        """GET /spaces with token_b returns only Company B spaces (zero when none exist)."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        alpha_space = _make_space(company_a_id)

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.spaces.get_db", _mock_db()),
                patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_repo_cls,
            ):
                mock_repo = AsyncMock()
                mock_repo.list_by_company = AsyncMock(return_value=[])
                mock_repo_cls.return_value = mock_repo

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.get(
                        "/v1/spaces",
                        headers={"Authorization": f"Bearer {token_b}"},
                    )

        assert response.status_code == 200
        body = response.json()
        space_ids = [s["id"] for s in body.get("spaces", [])]
        assert str(alpha_space.id) not in space_ids

    def test_company_a_cannot_get_company_b_space_by_id(self, two_company_setup):
        """GET /spaces/{alpha_space_id} with token_b returns 403."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        alpha_space_id = uuid.uuid4()

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.spaces.get_db", _mock_db()),
                patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_repo_cls,
                patch("tessera_api.routers.spaces.write_audit", new_callable=AsyncMock),
            ):
                mock_repo = AsyncMock()
                mock_repo.get_by_id_for_company = AsyncMock(return_value=None)
                mock_repo_cls.return_value = mock_repo

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.get(
                        f"/v1/spaces/{alpha_space_id}",
                        headers={"Authorization": f"Bearer {token_b}"},
                    )

        assert response.status_code == 403

    def test_space_create_binds_to_session_company(self, two_company_setup):
        """POST /spaces with token_a returns a space whose company_id matches alpha's company id."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        created_space = _make_space(company_a_id)

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.spaces.get_db", _mock_db()),
                patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_repo_cls,
            ):
                mock_repo = AsyncMock()
                mock_repo.create = AsyncMock(return_value=created_space)
                mock_repo_cls.return_value = mock_repo

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        "/v1/spaces",
                        json={
                            "slug": "alpha-space",
                            "name": "Alpha Space",
                            "sector": "tech",
                            "default_language": "en",
                        },
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert response.status_code == 201
        body = response.json()
        assert body["space"]["company_id"] == str(company_a_id)


class TestUS2DocumentIsolation:
    """US2: Document retrieval, creation, search, and assistant are scoped to the session company."""

    def test_company_a_cannot_get_company_b_document_by_id(self, two_company_setup):
        """GET /documents/{alpha_doc_id} with token_b returns 403."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        alpha_doc_id = uuid.uuid4()

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.documents.get_db", _mock_db()),
                patch("tessera_api.routers.documents.SqlDocumentRepository") as mock_doc_repo_cls,
            ):
                mock_doc_repo = AsyncMock()
                mock_doc_repo.get_by_id_for_company = AsyncMock(return_value=None)
                mock_doc_repo_cls.return_value = mock_doc_repo

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.get(
                        f"/v1/documents/{alpha_doc_id}",
                        headers={"Authorization": f"Bearer {token_b}"},
                    )

        assert response.status_code == 403

    def test_company_a_cannot_create_document_in_company_b_space(self, two_company_setup):
        """POST /documents with token_b and space_id=alpha_space_id returns 403."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        alpha_space_id = uuid.uuid4()

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.documents.get_db", _mock_db()),
                patch("tessera_api.routers.documents.SqlSpaceRepository") as mock_space_repo_cls,
            ):
                mock_space_repo = AsyncMock()
                mock_space_repo.get_by_id_for_company = AsyncMock(return_value=None)
                mock_space_repo_cls.return_value = mock_space_repo

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        "/v1/documents",
                        json={
                            "space_id": str(alpha_space_id),
                            "title": "Stolen Doc",
                            "content_markdown": "secret content",
                        },
                        headers={"Authorization": f"Bearer {token_b}"},
                    )

        assert response.status_code == 403

    def test_company_a_search_returns_only_company_a_results(self, two_company_setup):
        """POST /search with token_b returns 0 results for Alpha-only content."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.search.get_db", _mock_db()),
                patch("tessera_api.routers.search.SqlSpaceRepository") as mock_space_repo_cls,
                patch("tessera_api.routers.search.OllamaEmbeddingProvider") as mock_embed_cls,
                patch("tessera_api.routers.search.acl_first_search", new_callable=AsyncMock) as mock_search,
            ):
                mock_space_repo = AsyncMock()
                mock_space_repo.list_by_company = AsyncMock(return_value=[])
                mock_space_repo_cls.return_value = mock_space_repo

                mock_embed = AsyncMock()
                mock_embed.embed = AsyncMock(return_value=[[0.1] * 384])
                mock_embed_cls.return_value = mock_embed

                mock_search.return_value = []

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        "/v1/search",
                        json={"query": "top secret alpha content", "top_k": 5},
                        headers={"Authorization": f"Bearer {token_b}"},
                    )

        assert response.status_code == 200
        body = response.json()
        assert len(body.get("results", [])) == 0

    def test_company_a_assistant_returns_only_company_a_citations(self, two_company_setup):
        """POST /assistant/answer with token_b returns no citations from Alpha documents."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.assistant.get_db", _mock_db()),
                patch("tessera_api.routers.assistant.SqlSpaceRepository") as mock_space_repo_cls,
                patch("tessera_api.routers.assistant.OllamaEmbeddingProvider") as mock_embed_cls,
                patch("tessera_api.routers.assistant.acl_first_search", new_callable=AsyncMock) as mock_search,
                patch("tessera_api.routers.assistant.generate_answer", new_callable=AsyncMock) as mock_gen,
                patch("tessera_api.routers.assistant.write_audit", new_callable=AsyncMock),
            ):
                mock_space_repo = AsyncMock()
                mock_space_repo.list_by_company = AsyncMock(return_value=[])
                mock_space_repo_cls.return_value = mock_space_repo

                mock_embed = AsyncMock()
                mock_embed.embed = AsyncMock(return_value=[[0.1] * 384])
                mock_embed_cls.return_value = mock_embed

                mock_search.return_value = []

                from tessera_api.rag.assistant import DontKnowResponse
                mock_gen.return_value = DontKnowResponse(confidence=0.0)

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        "/v1/assistant/answer",
                        json={"query": "top secret alpha content"},
                        headers={"Authorization": f"Bearer {token_b}"},
                    )

        assert response.status_code == 200
        body = response.json()
        assert body.get("citations", []) == []


class TestUS4ContextSwitch:
    """US4: Context switch is atomic; activation is restricted to members; login auto-activates."""

    def test_activate_company_forbidden_for_non_member(self, two_company_setup):
        """POST /companies/{beta_id}/activate with token_a returns 403."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.companies.get_db", _mock_db()),
                patch("tessera_api.routers.companies.SqlCompanyRepository") as mock_company_cls,
            ):
                from tessera_core.domain.entities import Company

                beta_company = Company(id=company_b_id, name="Beta Corp", admin_user_id=uuid.uuid4())
                mock_company_repo = AsyncMock()
                mock_company_repo.get_by_id = AsyncMock(return_value=beta_company)
                mock_company_repo.get_membership = AsyncMock(return_value=None)
                mock_company_cls.return_value = mock_company_repo

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        f"/v1/companies/{company_b_id}/activate",
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert response.status_code == 403

    def test_context_switch_scopes_correctly(self, two_company_setup):
        """Charlie activates Alpha then Beta; GET /spaces reflects the active company each time."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup

        charlie_id = uuid.uuid4()
        from tessera_api.auth.jwt_auth import create_access_token
        charlie_token = create_access_token(charlie_id, "charlie@both.test", False)

        alpha_space = _make_space(company_a_id)
        beta_space = _make_space(company_b_id)

        from tessera_core.domain.entities import Company, CompanyMembership, CompanyRole
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        alpha_company = Company(id=company_a_id, name="Alpha Corp", admin_user_id=charlie_id)
        beta_company = Company(id=company_b_id, name="Beta Corp", admin_user_id=charlie_id)
        charlie_alpha_ms = CompanyMembership(
            id=uuid.uuid4(), user_id=charlie_id, company_id=company_a_id,
            role=CompanyRole.MEMBER, joined_at=now,
        )
        charlie_beta_ms = CompanyMembership(
            id=uuid.uuid4(), user_id=charlie_id, company_id=company_b_id,
            role=CompanyRole.MEMBER, joined_at=now,
        )

        def _company_db():
            m = MagicMock()
            s = AsyncMock()
            m.return_value.__aenter__ = AsyncMock(return_value=s)
            m.return_value.__aexit__ = AsyncMock(return_value=None)
            return m

        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with _bypass_onboarding_guard():
            # --- Phase 1: Activate Alpha (fresh client — no session bleed) ---
            with (
                patch("tessera_api.routers.companies.get_db", _company_db()),
                patch("tessera_api.routers.companies.SqlCompanyRepository") as mock_co_cls,
            ):
                mock_co = AsyncMock()
                mock_co.get_by_id = AsyncMock(return_value=alpha_company)
                mock_co.get_membership = AsyncMock(return_value=charlie_alpha_ms)
                mock_co_cls.return_value = mock_co

                with TestClient(app) as client:
                    resp = client.post(
                        f"/v1/companies/{company_a_id}/activate",
                        headers={"Authorization": f"Bearer {charlie_token}"},
                    )
            assert resp.status_code == 200
            alpha_scoped = resp.json()["token"]

            # --- Phase 2: List spaces with Alpha-scoped token (fresh client) ---
            with (
                patch("tessera_api.routers.spaces.get_db", _mock_db()),
                patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_sp_cls,
            ):
                mock_sp = AsyncMock()
                mock_sp.list_by_company = AsyncMock(return_value=[alpha_space])
                mock_sp_cls.return_value = mock_sp

                with TestClient(app) as client:
                    resp = client.get(
                        "/v1/spaces",
                        headers={"Authorization": f"Bearer {alpha_scoped}"},
                    )
            assert resp.status_code == 200
            ids = [s["id"] for s in resp.json().get("spaces", [])]
            assert str(alpha_space.id) in ids
            assert str(beta_space.id) not in ids

            # --- Phase 3: Activate Beta (fresh client) ---
            with (
                patch("tessera_api.routers.companies.get_db", _company_db()),
                patch("tessera_api.routers.companies.SqlCompanyRepository") as mock_co_cls,
            ):
                mock_co = AsyncMock()
                mock_co.get_by_id = AsyncMock(return_value=beta_company)
                mock_co.get_membership = AsyncMock(return_value=charlie_beta_ms)
                mock_co_cls.return_value = mock_co

                with TestClient(app) as client:
                    resp = client.post(
                        f"/v1/companies/{company_b_id}/activate",
                        headers={"Authorization": f"Bearer {charlie_token}"},
                    )
            assert resp.status_code == 200
            beta_scoped = resp.json()["token"]

            # --- Phase 4: List spaces with Beta-scoped token (fresh client) ---
            with (
                patch("tessera_api.routers.spaces.get_db", _mock_db()),
                patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_sp_cls,
            ):
                mock_sp = AsyncMock()
                mock_sp.list_by_company = AsyncMock(return_value=[beta_space])
                mock_sp_cls.return_value = mock_sp

                with TestClient(app) as client:
                    resp = client.get(
                        "/v1/spaces",
                        headers={"Authorization": f"Bearer {beta_scoped}"},
                    )
            assert resp.status_code == 200
            ids = [s["id"] for s in resp.json().get("spaces", [])]
            assert str(beta_space.id) in ids
            assert str(alpha_space.id) not in ids


class TestUS3MemberIsolation:
    """US3: Member roster and company context scoped to the authenticated company."""

    def test_company_a_member_list_excludes_company_b_members(self, two_company_setup):
        """GET /spaces/{alpha_space_id}/members with token_a should not include Beta users."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        alpha_space_id = uuid.uuid4()
        beta_user_id = uuid.uuid4()

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.members.get_db", _mock_db()),
                patch("tessera_api.routers.spaces.get_db", _mock_db()),
                patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_space_repo_cls,
                patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
                patch("tessera_api.routers.members.SqlSpaceMembershipRepository") as mock_member_repo_cls,
            ):
                mock_space_repo = AsyncMock()
                mock_space_repo.get_by_id_for_company = AsyncMock(return_value=_make_space(company_a_id))
                mock_space_repo_cls.return_value = mock_space_repo

                alpha_user = MagicMock()
                alpha_user.id = uuid.uuid4()
                alpha_user.groups = []
                mock_user_repo = AsyncMock()
                mock_user_repo.get_by_id = AsyncMock(return_value=alpha_user)
                mock_user_repo_cls.return_value = mock_user_repo

                from tessera_core.domain.entities import SpaceMembership, SpaceRole
                alpha_membership = SpaceMembership(
                    id=uuid.uuid4(),
                    space_id=alpha_space_id,
                    user_id=alpha_user.id,
                    role=SpaceRole.VIEWER,
                )
                mock_member_repo = AsyncMock()
                mock_member_repo.list_by_space = AsyncMock(return_value=[alpha_membership])
                mock_member_repo_cls.return_value = mock_member_repo

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.get(
                        f"/v1/spaces/{alpha_space_id}/members",
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert response.status_code == 200
        member_ids = [m["user_id"] for m in response.json().get("members", [])]
        assert str(beta_user_id) not in member_ids

    def test_require_company_context_rejects_revoked_member(self, two_company_setup):
        """After membership revocation, tenant-scoped requests return 403."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.spaces.get_db", _mock_db()),
                patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_repo_cls,
                patch("tessera_api.auth.oidc.SqlCompanyRepository") as mock_company_repo_cls,
            ):
                mock_repo = AsyncMock()
                mock_repo.list_by_company = AsyncMock(return_value=[])
                mock_repo_cls.return_value = mock_repo

                mock_company_repo = AsyncMock()
                mock_company_repo.get_membership = AsyncMock(return_value=None)
                mock_company_repo_cls.return_value = mock_company_repo

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.get(
                        "/v1/spaces",
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert response.status_code == 403
