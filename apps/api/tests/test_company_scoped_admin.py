"""Company-scoped admin authority tests (feature 036, US1–US4).

Admin authority over company-owned data derives solely from the caller's
per-company ``CompanyRole.ADMIN`` membership in the *active* company — never from
the legacy global ``users.is_admin`` flag. Cross-company by-ID access is
indistinguishable from a genuine not-found (404 + one ``cross_tenant_denied``).
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from tessera_core.domain.entities import Space

_GENERIC_NOT_FOUND = {"error": {"code": "not_found", "message": "Not found"}}


def _make_space(company_id: uuid.UUID) -> Space:
    return Space(
        id=uuid.uuid4(),
        slug=f"space-{uuid.uuid4().hex[:8]}",
        name="A Space",
        sector="tech",
        company_id=company_id,
    )


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


def _mock_db():
    mock_get_db = MagicMock()
    mock_session = AsyncMock()
    mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_get_db


def _cross_tenant_denied_count(mock_audit) -> int:
    calls = mock_audit.await_args_list or mock_audit.call_args_list
    return sum(1 for c in calls if c.kwargs.get("action") == "cross_tenant_denied")


# ---------------------------------------------------------------------------
# US1 — Admin authority confined to the active company
# ---------------------------------------------------------------------------


class TestUS1AdminAuthorityConfined:
    def test_admin_issues_credential_in_active_company(self, admin_company_setup):
        """Admin of A issues a credential scoped to an A space → 201 bound to A."""
        token_a, company_a_id, _tb, _cb = admin_company_setup
        alpha_space = _make_space(company_a_id)

        with _bypass_onboarding_guard():
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
                mock_space.get_by_id_for_company = AsyncMock(return_value=alpha_space)
                mock_space_cls.return_value = mock_space

                mock_cred = AsyncMock()
                mock_cred.create = AsyncMock(side_effect=lambda c: c)
                mock_cred_cls.return_value = mock_cred

                from tessera_api.main import app

                with TestClient(app) as client:
                    resp = client.post(
                        "/v1/agent-credentials",
                        json={"name": "agent-a", "scoped_space_ids": [str(alpha_space.id)]},
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert resp.status_code == 201
        assert resp.json()["credential"]["company_id"] == str(company_a_id)
        # success path emits no cross-tenant denial
        assert _cross_tenant_denied_count(mock_audit) == 0

    def test_admin_revoking_other_company_credential_404(self, admin_company_setup):
        """Admin of A revoking a Company B credential by ID → 404 + exactly one audit."""
        token_a, _company_a_id, _tb, _cb = admin_company_setup
        beta_credential_id = uuid.uuid4()

        with _bypass_onboarding_guard():
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

                from tessera_api.main import app

                with TestClient(app) as client:
                    resp = client.post(
                        f"/v1/agent-credentials/{beta_credential_id}/revoke",
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert resp.status_code == 404
        assert resp.json() == _GENERIC_NOT_FOUND
        mock_cred.revoke.assert_not_awaited()
        assert _cross_tenant_denied_count(mock_audit) == 1

    def test_admin_metrics_scoped_to_active_company(self, admin_company_setup):
        """Admin of A reads metrics → 200 with only Company A aggregates, no denial."""
        token_a, company_a_id, _tb, _cb = admin_company_setup

        res_queries = MagicMock()
        res_queries.scalar.return_value = 7
        res_pending = MagicMock()
        res_pending.scalar.return_value = 3
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[res_queries, res_pending])
        mock_db = MagicMock()
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

        with _bypass_onboarding_guard():
            with patch("tessera_api.routers.metrics.get_db", mock_db):
                from tessera_api.main import app

                with TestClient(app) as client:
                    resp = client.get("/v1/metrics", headers={"Authorization": f"Bearer {token_a}"})

        assert resp.status_code == 200
        assert resp.json()["total_queries"] == 7

        from sqlalchemy.dialects import postgresql

        for c in mock_session.execute.await_args_list:
            compiled = str(
                c.args[0].compile(
                    dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
                )
            )
            assert str(company_a_id) in compiled


# ---------------------------------------------------------------------------
# US2 — No cross-company visibility from admin status
# ---------------------------------------------------------------------------


class TestUS2NoCrossCompanyVisibility:
    def test_cross_company_doc_read_is_byte_identical_to_missing(self, admin_company_setup):
        """GET a Company B doc id == GET a random non-existent id (status + body), one audit each."""
        token_a, _company_a_id, _tb, _cb = admin_company_setup
        beta_doc_id = uuid.uuid4()
        random_id = uuid.uuid4()

        from tessera_api.main import app

        results = []
        for doc_id in (beta_doc_id, random_id):
            with _bypass_onboarding_guard():
                with (
                    patch("tessera_api.routers.documents.get_db", _mock_db()),
                    patch("tessera_api.routers.documents.SqlDocumentRepository") as mock_doc_cls,
                    patch(
                        "tessera_api.routers.documents.write_audit", new_callable=AsyncMock
                    ) as mock_audit,
                ):
                    mock_doc = AsyncMock()
                    mock_doc.get_by_id_for_company = AsyncMock(return_value=None)
                    mock_doc_cls.return_value = mock_doc

                    with TestClient(app) as client:
                        resp = client.get(
                            f"/v1/documents/{doc_id}",
                            headers={"Authorization": f"Bearer {token_a}"},
                        )
            results.append((resp.status_code, resp.json(), _cross_tenant_denied_count(mock_audit)))

        # cross-company and genuinely-missing are indistinguishable
        assert results[0][0] == results[1][0] == 404
        assert results[0][1] == results[1][1] == _GENERIC_NOT_FOUND
        # exactly one cross_tenant_denied per by-ID attempt
        assert results[0][2] == 1


# ---------------------------------------------------------------------------
# US3 — Per-company authority for multi-company members
# ---------------------------------------------------------------------------


class TestUS3PerCompanyAuthority:
    def test_admin_action_succeeds_in_a_denied_in_b(self, admin_in_a_member_in_b):
        """Same user: agent-credential issue succeeds with A active, 403 with B active."""
        token_a, company_a_id, token_b, _company_b_id = admin_in_a_member_in_b
        alpha_space = _make_space(company_a_id)

        from tessera_api.main import app

        # --- A active: ADMIN → success ---
        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.agent_credentials.get_db", _mock_db()),
                patch("tessera_api.routers.agent_credentials.SqlSpaceRepository") as mock_space_cls,
                patch(
                    "tessera_api.routers.agent_credentials.SqlAgentCredentialRepository"
                ) as mock_cred_cls,
                patch("tessera_api.routers.agent_credentials.write_audit", new_callable=AsyncMock),
            ):
                mock_space = AsyncMock()
                mock_space.get_by_id_for_company = AsyncMock(return_value=alpha_space)
                mock_space_cls.return_value = mock_space
                mock_cred = AsyncMock()
                mock_cred.create = AsyncMock(side_effect=lambda c: c)
                mock_cred_cls.return_value = mock_cred

                with TestClient(app) as client:
                    resp_a = client.post(
                        "/v1/agent-credentials",
                        json={"name": "x", "scoped_space_ids": [str(alpha_space.id)]},
                        headers={"Authorization": f"Bearer {token_a}"},
                    )
        assert resp_a.status_code == 201

        # --- B active: MEMBER (not admin) → 403, NOT a cross-tenant 404 ---
        with _bypass_onboarding_guard(), TestClient(app) as client:
            resp_b = client.post(
                "/v1/agent-credentials",
                json={"name": "x", "scoped_space_ids": []},
                headers={"Authorization": f"Bearer {token_b}"},
            )
        assert resp_b.status_code == 403


# ---------------------------------------------------------------------------
# US4 — Tenant data protected from outside admins (incl. legacy global flag)
# ---------------------------------------------------------------------------


class TestUS4OutsideAdminsDenied:
    def test_legacy_global_admin_cannot_read_other_company_doc(self, legacy_global_admin_setup):
        """A→admin carrying users.is_admin=True targets a Company B doc id → 404."""
        token_a, _company_a_id, _company_b_id = legacy_global_admin_setup
        beta_doc_id = uuid.uuid4()

        with (
            _bypass_onboarding_guard(), patch("tessera_api.routers.documents.get_db", _mock_db()),
            patch("tessera_api.routers.documents.SqlDocumentRepository") as mock_doc_cls,
            patch(
                "tessera_api.routers.documents.write_audit", new_callable=AsyncMock
            ) as mock_audit,
        ):
            mock_doc = AsyncMock()
            mock_doc.get_by_id_for_company = AsyncMock(return_value=None)
            mock_doc_cls.return_value = mock_doc

            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.get(
                    f"/v1/documents/{beta_doc_id}",
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 404
        assert resp.json() == _GENERIC_NOT_FOUND
        assert _cross_tenant_denied_count(mock_audit) == 1

    def test_legacy_global_admin_cannot_reindex_other_company_doc(self, legacy_global_admin_setup):
        """The global flag confers no reindex authority over Company B (404, no mutation)."""
        token_a, _company_a_id, _company_b_id = legacy_global_admin_setup
        beta_doc_id = uuid.uuid4()

        with (
            _bypass_onboarding_guard(), patch("tessera_api.routers.documents.get_db", _mock_db()),
            patch("tessera_api.routers.documents.SqlDocumentRepository") as mock_doc_cls,
            patch("tessera_api.routers.documents.SqlDocumentVersionRepository"),
            patch(
                "tessera_api.routers.documents.write_audit", new_callable=AsyncMock
            ) as mock_audit,
            patch("tessera_api.routers.documents.get_celery_app") as mock_celery,
        ):
            mock_doc = AsyncMock()
            mock_doc.get_by_id_for_company = AsyncMock(return_value=None)
            mock_doc_cls.return_value = mock_doc

            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    f"/v1/documents/{beta_doc_id}/reindex",
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 404
        assert resp.json() == _GENERIC_NOT_FOUND
        mock_celery.return_value.send_task.assert_not_called()
        assert _cross_tenant_denied_count(mock_audit) == 1


# ---------------------------------------------------------------------------
# Feature 037 — the platform-operator surface is the single audited cross-tenant
# exception. Each /v1/admin/* space endpoint emits exactly one
# ``cross_company_admin_access`` record (FR-008/FR-009, contract C-005).
# ---------------------------------------------------------------------------


def _admin_user_patch(is_admin: bool, actor_id: uuid.UUID | None = None):
    actor_id = actor_id or uuid.uuid4()
    p = patch(
        "tessera_api.routers.admin.require_user",
        new=AsyncMock(
            return_value={"sub": str(actor_id), "id": str(actor_id), "is_admin": is_admin}
        ),
    )
    return actor_id, p


def _patch_audit_repo():
    """Patch admin's SqlAuditRepository, returning (mock_cls, append_mock)."""
    append_mock = AsyncMock()
    repo = MagicMock()
    repo.append = append_mock
    return patch("tessera_api.routers.admin.SqlAuditRepository", return_value=repo), append_mock


def _admin_access_records(append_mock):
    return [
        c.args[0]
        for c in append_mock.await_args_list
        if getattr(c.args[0], "action", None) == "cross_company_admin_access"
    ]


class TestOperatorSurfaceAudited:
    """Contract C-005: every cross-company operator read/write is audited exactly once."""

    def test_list_all_spaces_emits_one_cross_company_admin_access(self):
        actor_id, p_user = _admin_user_patch(is_admin=True)
        p_audit, append_mock = _patch_audit_repo()

        from tessera_api.main import app

        with (
            p_user,
            patch("tessera_api.routers.admin.get_db", _mock_db()),
            patch("tessera_api.routers.admin.SqlSpaceRepository") as mock_space_cls,
            p_audit,
        ):
            mock_space = AsyncMock()
            mock_space.list_all = AsyncMock(return_value=[])
            mock_space_cls.return_value = mock_space

            with TestClient(app) as client:
                resp = client.get(
                    "/v1/admin/spaces", headers={"Authorization": "Bearer x"}
                )

        assert resp.status_code == 200
        records = _admin_access_records(append_mock)
        assert len(records) == 1
        rec = records[0]
        assert rec.entity_type == "spaces"
        assert rec.actor_id == actor_id
        assert rec.metadata.get("endpoint") == "/admin/spaces"
        assert rec.metadata.get("operation") == "list"

    def test_list_all_spaces_non_admin_403(self):
        _actor_id, p_user = _admin_user_patch(is_admin=False)
        from tessera_api.main import app

        with p_user, TestClient(app) as client:
            resp = client.get("/v1/admin/spaces", headers={"Authorization": "Bearer x"})
        assert resp.status_code == 403

    def test_update_retention_emits_one_cross_company_admin_access(self):
        actor_id, p_user = _admin_user_patch(is_admin=True)
        p_audit, append_mock = _patch_audit_repo()
        space_id = uuid.uuid4()

        from tessera_api.main import app

        with (
            p_user,
            patch("tessera_api.routers.admin.get_db", _mock_db()),
            patch("tessera_api.routers.admin.SqlSpaceRepository") as mock_space_cls,
            p_audit,
        ):
            mock_space = AsyncMock()
            mock_space.get_by_id = AsyncMock(return_value=_make_space(uuid.uuid4()))
            mock_space_cls.return_value = mock_space

            with TestClient(app) as client:
                resp = client.put(
                    f"/v1/admin/spaces/{space_id}/retention",
                    json={"validity_days": 30, "action_on_expiry": "archive"},
                    headers={"Authorization": "Bearer x"},
                )

        assert resp.status_code == 200
        records = _admin_access_records(append_mock)
        assert len(records) == 1
        rec = records[0]
        assert rec.entity_type == "space"
        assert rec.entity_id == space_id
        assert rec.actor_id == actor_id
        assert rec.metadata.get("operation") == "retention"

    def test_update_retention_non_admin_403(self):
        _actor_id, p_user = _admin_user_patch(is_admin=False)
        space_id = uuid.uuid4()
        from tessera_api.main import app

        with p_user, TestClient(app) as client:
            resp = client.put(
                f"/v1/admin/spaces/{space_id}/retention",
                json={"validity_days": 30},
                headers={"Authorization": "Bearer x"},
            )
        assert resp.status_code == 403

    def test_bulk_reindex_emits_one_cross_company_admin_access(self):
        actor_id, p_user = _admin_user_patch(is_admin=True)
        p_audit, append_mock = _patch_audit_repo()

        # Two published, unchunked docs → two dispatched tasks.
        rows = [
            {"id": uuid.uuid4(), "space_id": uuid.uuid4(), "version_id": uuid.uuid4()},
            {"id": uuid.uuid4(), "space_id": uuid.uuid4(), "version_id": uuid.uuid4()},
        ]
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = rows
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_db = MagicMock()
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

        from tessera_api.main import app

        with (
            p_user,
            patch("tessera_api.routers.admin.get_db", mock_db),
            patch("tessera_api.routers.admin.get_celery_app") as mock_celery,
            p_audit,
        ):
            mock_celery.return_value.send_task = MagicMock()

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/admin/reindex", headers={"Authorization": "Bearer x"}
                )

        assert resp.status_code == 200
        assert resp.json() == {"dispatched": 2}
        records = _admin_access_records(append_mock)
        assert len(records) == 1
        rec = records[0]
        assert rec.entity_type == "spaces"
        assert rec.actor_id == actor_id
        assert rec.metadata.get("operation") == "reindex"
        assert rec.metadata.get("dispatched") == 2

    def test_bulk_reindex_non_admin_403(self):
        _actor_id, p_user = _admin_user_patch(is_admin=False)
        from tessera_api.main import app

        with p_user, TestClient(app) as client:
            resp = client.post("/v1/admin/reindex", headers={"Authorization": "Bearer x"})
        assert resp.status_code == 403
