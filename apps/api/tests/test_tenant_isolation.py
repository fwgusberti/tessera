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


# Generic denial body — must be identical for "missing" and "other company" (FR-010/SC-005).
_GENERIC_FORBIDDEN = {"error": {"code": "forbidden", "message": "Access denied"}}


@contextmanager
def _company_admin_membership():
    """Patch the membership lookup so the caller is an ADMIN of the active company.

    Overrides the MEMBER-returning patch installed by ``two_company_setup`` so that
    ``require_company_admin`` passes its role check and the handler proceeds to the
    per-resource tenant/space validation (which is what these tests exercise).
    """

    def _admin(uid, cid):
        return CompanyMembership(
            id=uuid.uuid4(), user_id=uid, company_id=cid,
            role=CompanyRole.ADMIN, joined_at=datetime.now(UTC),
        )

    repo = AsyncMock()
    repo.get_membership = AsyncMock(side_effect=_admin)
    with patch("tessera_api.auth.oidc.SqlCompanyRepository", return_value=repo):
        yield


def _assert_cross_tenant_audit(mock_audit, entity_type: str) -> None:
    """Assert write_audit was called at least once with a cross_tenant_denied record."""
    assert mock_audit.await_count >= 1 or mock_audit.call_count >= 1
    calls = mock_audit.await_args_list or mock_audit.call_args_list
    actions = [c.kwargs.get("action") for c in calls]
    entity_types = [c.kwargs.get("entity_type") for c in calls]
    assert "cross_tenant_denied" in actions
    assert entity_type in entity_types
    # every cross_tenant_denied record carries the active company id in metadata
    for c in calls:
        if c.kwargs.get("action") == "cross_tenant_denied":
            assert "company_id" in (c.kwargs.get("metadata") or {})


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


class TestUS1ProposalIsolation:
    """US1: proposals are scoped to the document's company; cross-company is denied."""

    def test_list_excludes_other_company_proposals(self, two_company_setup):
        """GET /proposals as Company B must not include Company A proposals."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        alpha_proposal_id = uuid.uuid4()

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.proposals.get_db", _mock_db()),
                patch("tessera_api.routers.proposals.SqlProposalRepository") as mock_repo_cls,
            ):
                mock_repo = AsyncMock()
                mock_repo.list_for_company = AsyncMock(return_value=[])
                mock_repo_cls.return_value = mock_repo

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.get(
                        "/v1/proposals",
                        headers={"Authorization": f"Bearer {token_b}"},
                    )

        assert response.status_code == 200
        ids = [p["id"] for p in response.json().get("proposals", [])]
        assert str(alpha_proposal_id) not in ids
        # the list query was scoped to Company B's id
        mock_repo.list_for_company.assert_awaited_once()
        assert mock_repo.list_for_company.await_args.args[0] == company_b_id

    def test_get_other_company_proposal_denied(self, two_company_setup):
        """GET /proposals/{A_id} as Company B → 403 generic body, no document content, audited."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        alpha_proposal_id = uuid.uuid4()

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.proposals.get_db", _mock_db()),
                patch("tessera_api.routers.proposals.SqlProposalRepository") as mock_repo_cls,
                patch("tessera_api.routers.proposals.SqlDocumentRepository"),
                patch(
                    "tessera_api.routers.proposals.write_audit", new_callable=AsyncMock
                ) as mock_audit,
            ):
                mock_repo = AsyncMock()
                mock_repo.get_by_id_for_company = AsyncMock(return_value=None)
                mock_repo_cls.return_value = mock_repo

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.get(
                        f"/v1/proposals/{alpha_proposal_id}",
                        headers={"Authorization": f"Bearer {token_b}"},
                    )

        assert response.status_code == 403
        assert response.json() == _GENERIC_FORBIDDEN
        assert "target_document" not in response.json()
        _assert_cross_tenant_audit(mock_audit, "proposal")

    def test_get_denial_body_matches_missing(self, two_company_setup):
        """SC-005: the 403 body for another company's id equals the body for a missing id."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup

        from fastapi.testclient import TestClient
        from tessera_api.main import app

        bodies = []
        for _ in range(2):
            with _bypass_onboarding_guard():
                with (
                    patch("tessera_api.routers.proposals.get_db", _mock_db()),
                    patch("tessera_api.routers.proposals.SqlProposalRepository") as mock_repo_cls,
                    patch("tessera_api.routers.proposals.SqlDocumentRepository"),
                    patch("tessera_api.routers.proposals.write_audit", new_callable=AsyncMock),
                ):
                    mock_repo = AsyncMock()
                    mock_repo.get_by_id_for_company = AsyncMock(return_value=None)
                    mock_repo_cls.return_value = mock_repo

                    with TestClient(app) as client:
                        resp = client.get(
                            f"/v1/proposals/{uuid.uuid4()}",
                            headers={"Authorization": f"Bearer {token_b}"},
                        )
            assert resp.status_code == 403
            bodies.append(resp.json())

        assert bodies[0] == bodies[1]

    def test_approve_other_company_proposal_denied(self, two_company_setup):
        """POST /proposals/{A_id}/approve as Company B → 403; no state change; audited."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        alpha_proposal_id = uuid.uuid4()

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.proposals.get_db", _mock_db()),
                patch("tessera_api.routers.proposals.SqlProposalRepository") as mock_repo_cls,
                patch("tessera_api.routers.proposals.SqlDocumentRepository"),
                patch("tessera_api.routers.proposals.SqlDocumentVersionRepository"),
                patch("tessera_api.routers.proposals.SqlUserRepository"),
                patch("tessera_api.routers.proposals.SqlSpaceRepository"),
                patch(
                    "tessera_api.routers.proposals.write_audit", new_callable=AsyncMock
                ) as mock_audit,
            ):
                mock_repo = AsyncMock()
                mock_repo.get_by_id_for_company = AsyncMock(return_value=None)
                mock_repo_cls.return_value = mock_repo

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        f"/v1/proposals/{alpha_proposal_id}/approve",
                        headers={"Authorization": f"Bearer {token_b}"},
                    )

        assert response.status_code == 403
        assert response.json() == _GENERIC_FORBIDDEN
        # A's proposal/document/version history were never mutated
        mock_repo.update_state.assert_not_awaited()
        _assert_cross_tenant_audit(mock_audit, "proposal")

    def test_reject_other_company_proposal_denied(self, two_company_setup):
        """POST /proposals/{A_id}/reject as Company B → 403; proposal state unchanged; audited."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        alpha_proposal_id = uuid.uuid4()

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.proposals.get_db", _mock_db()),
                patch("tessera_api.routers.proposals.SqlProposalRepository") as mock_repo_cls,
                patch("tessera_api.routers.proposals.SqlDocumentRepository"),
                patch("tessera_api.routers.proposals.SqlUserRepository"),
                patch("tessera_api.routers.proposals.SqlSpaceRepository"),
                patch(
                    "tessera_api.routers.proposals.write_audit", new_callable=AsyncMock
                ) as mock_audit,
            ):
                mock_repo = AsyncMock()
                mock_repo.get_by_id_for_company = AsyncMock(return_value=None)
                mock_repo_cls.return_value = mock_repo

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        f"/v1/proposals/{alpha_proposal_id}/reject",
                        json={"reason": "nope"},
                        headers={"Authorization": f"Bearer {token_b}"},
                    )

        assert response.status_code == 403
        assert response.json() == _GENERIC_FORBIDDEN
        mock_repo.update_state.assert_not_awaited()
        _assert_cross_tenant_audit(mock_audit, "proposal")


class TestUS2ConnectorIsolation:
    """US2: connector create/sync require the resource to belong to the active company."""

    def test_admin_cannot_create_connector_in_other_company_space(self, two_company_setup):
        """Company B admin POST connector on Company A space → 403, no connector created, audited."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        alpha_space_id = uuid.uuid4()

        with _bypass_onboarding_guard(), _company_admin_membership():
            with (
                patch("tessera_api.routers.connectors.get_db", _mock_db()),
                patch("tessera_api.routers.connectors.SqlSpaceRepository") as mock_space_cls,
                patch("tessera_api.routers.connectors.SqlConnectorRepository") as mock_conn_cls,
                patch(
                    "tessera_api.routers.connectors.write_audit", new_callable=AsyncMock
                ) as mock_audit,
            ):
                mock_space = AsyncMock()
                mock_space.get_by_id_for_company = AsyncMock(return_value=None)
                mock_space_cls.return_value = mock_space

                mock_conn = AsyncMock()
                mock_conn_cls.return_value = mock_conn

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        f"/v1/spaces/{alpha_space_id}/connectors",
                        json={"type": "gdrive", "config": {"folder": "secret"}},
                        headers={"Authorization": f"Bearer {token_b}"},
                    )

        assert response.status_code == 403
        assert response.json() == _GENERIC_FORBIDDEN
        mock_conn.create.assert_not_awaited()
        _assert_cross_tenant_audit(mock_audit, "space")

    def test_admin_cannot_sync_other_company_connector(self, two_company_setup):
        """Company B admin POST sync on Company A connector → 403, no Celery job, audited."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        alpha_connector_id = uuid.uuid4()

        with _bypass_onboarding_guard(), _company_admin_membership():
            with (
                patch("tessera_api.routers.connectors.get_db", _mock_db()),
                patch("tessera_api.routers.connectors.SqlConnectorRepository") as mock_conn_cls,
                patch("tessera_api.routers.connectors.sync_connector_task") as mock_task,
                patch(
                    "tessera_api.routers.connectors.write_audit", new_callable=AsyncMock
                ) as mock_audit,
            ):
                mock_conn = AsyncMock()
                mock_conn.get_by_id_for_company = AsyncMock(return_value=None)
                mock_conn_cls.return_value = mock_conn

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        f"/v1/connectors/{alpha_connector_id}/sync",
                        headers={"Authorization": f"Bearer {token_b}"},
                    )

        assert response.status_code == 403
        assert response.json() == _GENERIC_FORBIDDEN
        mock_task.delay.assert_not_called()
        _assert_cross_tenant_audit(mock_audit, "connector")


class TestUS3AgentCredentialIsolation:
    """US3: agent credentials are bound to a company; cross-company issue/revoke denied."""

    def test_admin_cannot_issue_credential_scoped_to_other_company_space(self, two_company_setup):
        """Company B admin issues a token scoped to a Company A space → 403, no credential, audited."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        alpha_space_id = uuid.uuid4()

        with _bypass_onboarding_guard(), _company_admin_membership():
            with (
                patch("tessera_api.routers.agent_credentials.get_db", _mock_db()),
                patch("tessera_api.routers.agent_credentials.SqlSpaceRepository") as mock_space_cls,
                patch(
                    "tessera_api.routers.agent_credentials.SqlAgentCredentialRepository"
                ) as mock_cred_cls,
                patch(
                    "tessera_api.routers.agent_credentials.write_audit", new_callable=AsyncMock
                ) as mock_audit,
            ):
                mock_space = AsyncMock()
                mock_space.get_by_id_for_company = AsyncMock(return_value=None)
                mock_space_cls.return_value = mock_space

                mock_cred = AsyncMock()
                mock_cred_cls.return_value = mock_cred

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        "/v1/agent-credentials",
                        json={"name": "rogue", "scoped_space_ids": [str(alpha_space_id)]},
                        headers={"Authorization": f"Bearer {token_b}"},
                    )

        assert response.status_code == 403
        assert response.json() == _GENERIC_FORBIDDEN
        mock_cred.create.assert_not_awaited()
        _assert_cross_tenant_audit(mock_audit, "agent_credential")

    def test_admin_cannot_revoke_other_company_credential(self, two_company_setup):
        """Company B admin revokes a Company A credential → 403, credential still active, audited."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        alpha_credential_id = uuid.uuid4()

        with _bypass_onboarding_guard(), _company_admin_membership():
            with (
                patch("tessera_api.routers.agent_credentials.get_db", _mock_db()),
                patch(
                    "tessera_api.routers.agent_credentials.SqlAgentCredentialRepository"
                ) as mock_cred_cls,
                patch(
                    "tessera_api.routers.agent_credentials.write_audit", new_callable=AsyncMock
                ) as mock_audit,
            ):
                mock_cred = AsyncMock()
                mock_cred.get_by_id_for_company = AsyncMock(return_value=None)
                mock_cred_cls.return_value = mock_cred

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        f"/v1/agent-credentials/{alpha_credential_id}/revoke",
                        headers={"Authorization": f"Bearer {token_b}"},
                    )

        assert response.status_code == 403
        assert response.json() == _GENERIC_FORBIDDEN
        mock_cred.revoke.assert_not_awaited()
        _assert_cross_tenant_audit(mock_audit, "agent_credential")

    def test_admin_issues_credential_bound_to_active_company(self, two_company_setup):
        """Company A admin issues a token scoped to A spaces → 200 and credential.company_id == A."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        alpha_space = _make_space(company_a_id)

        with _bypass_onboarding_guard(), _company_admin_membership():
            with (
                patch("tessera_api.routers.agent_credentials.get_db", _mock_db()),
                patch("tessera_api.routers.agent_credentials.SqlSpaceRepository") as mock_space_cls,
                patch(
                    "tessera_api.routers.agent_credentials.SqlAgentCredentialRepository"
                ) as mock_cred_cls,
                patch(
                    "tessera_api.routers.agent_credentials.write_audit", new_callable=AsyncMock
                ),
            ):
                mock_space = AsyncMock()
                mock_space.get_by_id_for_company = AsyncMock(return_value=alpha_space)
                mock_space_cls.return_value = mock_space

                mock_cred = AsyncMock()
                # echo the credential the handler built so we can inspect company_id
                mock_cred.create = AsyncMock(side_effect=lambda c: c)
                mock_cred_cls.return_value = mock_cred

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        "/v1/agent-credentials",
                        json={"name": "agent-a", "scoped_space_ids": [str(alpha_space.id)]},
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert response.status_code == 201
        body = response.json()
        assert body["credential"]["company_id"] == str(company_a_id)
        assert "token" in body
        mock_cred.create.assert_awaited_once()
        assert mock_cred.create.await_args.args[0].company_id == company_a_id


class TestUS4MemberWriteIsolation:
    """US4: member writes & permission writes verify the space belongs to the company."""

    def _run_member_write(self, method, path, token, json=None):
        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.members.get_db", _mock_db()),
                patch("tessera_api.routers.members.SqlSpaceRepository") as mock_space_cls,
                patch("tessera_api.routers.members.SqlUserRepository"),
                patch("tessera_api.routers.members.SqlSpaceMembershipRepository"),
                patch("tessera_api.routers.members.SqlAuditRepository"),
                patch(
                    "tessera_api.routers.members.write_audit", new_callable=AsyncMock
                ) as mock_audit,
            ):
                mock_space = AsyncMock()
                mock_space.get_by_id_for_company = AsyncMock(return_value=None)
                mock_space_cls.return_value = mock_space

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.request(
                        method,
                        path,
                        json=json,
                        headers={"Authorization": f"Bearer {token}"},
                    )
        return response, mock_audit

    def test_member_writes_on_other_company_space_denied(self, two_company_setup):
        """invite / change-role / remove / members-me against a Company A space → 403, audited."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        alpha_space = uuid.uuid4()
        target = uuid.uuid4()

        cases = [
            ("POST", f"/v1/spaces/{alpha_space}/members", {"user_id": str(target), "role": "viewer"}),
            ("PUT", f"/v1/spaces/{alpha_space}/members/{target}", {"role": "editor"}),
            ("DELETE", f"/v1/spaces/{alpha_space}/members/{target}", None),
            ("GET", f"/v1/spaces/{alpha_space}/members/me", None),
        ]
        for method, path, body in cases:
            response, mock_audit = self._run_member_write(method, path, token_b, body)
            assert response.status_code == 403, f"{method} {path} -> {response.status_code}"
            assert response.json() == _GENERIC_FORBIDDEN
            _assert_cross_tenant_audit(mock_audit, "space")

    def test_permission_create_on_other_company_space_denied(self, two_company_setup):
        """Company B admin POST permission on a Company A space → 403, audited."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        alpha_space = uuid.uuid4()

        with _bypass_onboarding_guard(), _company_admin_membership():
            with (
                patch("tessera_api.routers.spaces.get_db", _mock_db()),
                patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_space_cls,
                patch(
                    "tessera_api.routers.spaces.write_audit", new_callable=AsyncMock
                ) as mock_audit,
            ):
                mock_space = AsyncMock()
                mock_space.get_by_id_for_company = AsyncMock(return_value=None)
                mock_space_cls.return_value = mock_space

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        f"/v1/spaces/{alpha_space}/permissions",
                        json={"idp_group": "eng", "role": "reader"},
                        headers={"Authorization": f"Bearer {token_b}"},
                    )

        assert response.status_code == 403
        assert response.json() == _GENERIC_FORBIDDEN
        _assert_cross_tenant_audit(mock_audit, "space")


class TestUS5MetricsIsolation:
    """US5: metric totals reflect only the active company (SC-003)."""

    def test_metrics_counts_scoped_to_active_company(self, two_company_setup):
        token_a, company_a_id, token_b, company_b_id = two_company_setup

        # Controlled per-query results: B has 5 queries and 2 pending proposals.
        res_queries = MagicMock()
        res_queries.scalar.return_value = 5
        res_pending = MagicMock()
        res_pending.scalar.return_value = 2

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[res_queries, res_pending])
        mock_db = MagicMock()
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

        with _bypass_onboarding_guard(), _company_admin_membership():
            with patch("tessera_api.routers.metrics.get_db", mock_db):
                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.get(
                        "/v1/metrics",
                        headers={"Authorization": f"Bearer {token_b}"},
                    )

        assert response.status_code == 200
        body = response.json()
        assert body["total_queries"] == 5
        assert body["documents_with_drift"] == 2

        # SC-003: both aggregates are filtered by Company B and never reference A.
        from sqlalchemy.dialects import postgresql

        stmts = [c.args[0] for c in mock_session.execute.await_args_list]
        assert len(stmts) == 2
        for stmt in stmts:
            compiled = str(
                stmt.compile(
                    dialect=postgresql.dialect(),
                    compile_kwargs={"literal_binds": True},
                )
            )
            assert str(company_b_id) in compiled
            assert str(company_a_id) not in compiled


@contextmanager
def _role_by_company(user_id, admin_company_id):
    """Patch membership lookup: ADMIN in admin_company_id, MEMBER in every other company."""

    def _ms(uid, cid):
        role = CompanyRole.ADMIN if cid == admin_company_id else CompanyRole.MEMBER
        return CompanyMembership(
            id=uuid.uuid4(), user_id=uid, company_id=cid, role=role,
            joined_at=datetime.now(UTC),
        )

    repo = AsyncMock()
    repo.get_membership = AsyncMock(side_effect=_ms)
    with patch("tessera_api.auth.oidc.SqlCompanyRepository", return_value=repo):
        yield


class TestUS6PerCompanyAdmin:
    """US6: admin authority is per-company; admin-of-A is not admin-of-B (SC-004)."""

    def test_admin_of_a_denied_admin_actions_on_b(self, two_company_setup):
        """A user who is ADMIN of A but only MEMBER of B is refused every admin action on B."""
        _ta, company_a_id, _tb, company_b_id = two_company_setup

        from tessera_api.auth.jwt_auth import create_access_token

        user_id = uuid.uuid4()
        token_b = create_access_token(user_id, "u@x.test", False, company_id=company_b_id)

        space_id = uuid.uuid4()
        cred_id = uuid.uuid4()
        connector_id = uuid.uuid4()

        admin_actions = [
            ("POST", f"/v1/spaces/{space_id}/connectors", {"type": "gdrive", "config": {}}),
            ("POST", f"/v1/connectors/{connector_id}/sync", None),
            ("POST", "/v1/agent-credentials", {"name": "x", "scoped_space_ids": []}),
            ("POST", f"/v1/agent-credentials/{cred_id}/revoke", None),
            ("POST", f"/v1/spaces/{space_id}/permissions", {"idp_group": "g", "role": "reader"}),
            ("GET", "/v1/metrics", None),
        ]

        from fastapi.testclient import TestClient
        from tessera_api.main import app

        for method, path, body in admin_actions:
            with _bypass_onboarding_guard(), _role_by_company(user_id, company_a_id):
                with TestClient(app) as client:
                    resp = client.request(
                        method, path, json=body,
                        headers={"Authorization": f"Bearer {token_b}"},
                    )
            assert resp.status_code == 403, f"{method} {path} -> {resp.status_code}"
            assert resp.json() == _GENERIC_FORBIDDEN

    def test_admin_of_a_allowed_admin_action_on_a(self, two_company_setup):
        """The same user succeeds on the identical admin action within Company A."""
        _ta, company_a_id, _tb, company_b_id = two_company_setup

        from tessera_api.auth.jwt_auth import create_access_token

        user_id = uuid.uuid4()
        token_a = create_access_token(user_id, "u@x.test", False, company_id=company_a_id)

        res_queries = MagicMock()
        res_queries.scalar.return_value = 3
        res_pending = MagicMock()
        res_pending.scalar.return_value = 1
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[res_queries, res_pending])
        mock_db = MagicMock()
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

        with _bypass_onboarding_guard(), _role_by_company(user_id, company_a_id):
            with patch("tessera_api.routers.metrics.get_db", mock_db):
                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    resp = client.get(
                        "/v1/metrics",
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert resp.status_code == 200
        assert resp.json()["total_queries"] == 3
