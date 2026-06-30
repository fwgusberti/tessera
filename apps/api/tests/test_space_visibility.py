"""Space-visibility confinement tests (feature 037).

Locks the listing/visibility half of the tenant-isolation invariant that feature
036 did not cover. Every everyday surface that resolves a company's space set must
return exactly the active company's spaces — never another company's — even when
the caller carries the legacy global ``is_admin`` flag. Refusals to *manage* a
space are role-based (403), never visibility-based (404).

Per the `project_test_env_baseline` / async-marker memory: API tests use
``fastapi.testclient.TestClient`` (sync) and patch router-module symbols.

Updated in feature 041: GET /v1/spaces now returns only user-accessible spaces
(via list_accessible_by_user) rather than all company spaces. Tests updated to
mock list_accessible_by_user and return SpaceAccess objects.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from tessera_core.domain.entities import Space
from tessera_core.domain.space_access import SpaceAccess
from tessera_core.domain.space_role import SpaceRole

_GENERIC_NOT_FOUND = {"error": {"code": "not_found", "message": "Not found"}}
_GENERIC_FORBIDDEN = {"error": {"code": "forbidden", "message": "Access denied"}}


def _make_space(company_id: uuid.UUID) -> Space:
    return Space(
        id=uuid.uuid4(),
        slug=f"space-{uuid.uuid4().hex[:8]}",
        name="A Space",
        sector="tech",
        company_id=company_id,
    )


def _make_access(space: Space, role: SpaceRole = SpaceRole.ADMIN) -> SpaceAccess:
    return SpaceAccess(space=space, effective_role=role, is_direct=True)


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


def _cross_tenant_denied_count(mock_audit) -> int:
    calls = mock_audit.await_args_list or mock_audit.call_args_list
    return sum(1 for c in calls if c.kwargs.get("action") == "cross_tenant_denied")


# ---------------------------------------------------------------------------
# US1 — Each person sees only their active company's spaces
# ---------------------------------------------------------------------------


class TestUS1OwnCompanyVisibility:
    def test_reproduction_three_users_see_only_their_company_spaces(self, reproduction_setup):
        """SC-002: felipe→{A,B}, a@2→{C}, a@3(global admin)→{} with zero overlap."""
        s = reproduction_setup
        # Build accessible-space map per company using the new SpaceAccess shape
        accessible_by_company = {
            s.company1_id: [_make_access(s.space_a), _make_access(s.space_b)],
            s.company2_id: [_make_access(s.space_c)],
            s.company3_id: [],
        }
        expected = {
            s.felipe_token: {str(s.space_a.id), str(s.space_b.id)},
            s.a2_token: {str(s.space_c.id)},
            s.a3_token: set(),
        }

        from tessera_api.main import app

        results: dict[str, set[str]] = {}
        with _bypass_onboarding_guard():
            with patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.list_accessible_by_user = AsyncMock(
                    side_effect=lambda uid, cid: accessible_by_company.get(cid, [])
                )
                mock_repo_cls.return_value = mock_repo

                with TestClient(app) as client:
                    for token in (s.felipe_token, s.a2_token, s.a3_token):
                        resp = client.get(
                            "/v1/spaces", headers={"Authorization": f"Bearer {token}"}
                        )
                        assert resp.status_code == 200
                        results[token] = {sp["id"] for sp in resp.json().get("spaces", [])}

        # Each set matches exactly.
        for token, want in expected.items():
            assert results[token] == want
        # No space id is visible to more than one of the three users.
        seen = list(results[s.felipe_token]) + list(results[s.a2_token]) + list(results[s.a3_token])
        assert len(seen) == len(set(seen))

    def test_list_spaces_returns_only_active_company_spaces(self, two_company_setup):
        """C-001: active as Company A, GET /v1/spaces never includes Company B's space."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        a_space = _make_space(company_a_id)
        b_space = _make_space(company_b_id)
        accessible_by_company = {
            company_a_id: [_make_access(a_space)],
            company_b_id: [_make_access(b_space)],
        }

        from tessera_api.main import app

        with _bypass_onboarding_guard():
            with patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.list_accessible_by_user = AsyncMock(
                    side_effect=lambda uid, cid: accessible_by_company.get(cid, [])
                )
                mock_repo_cls.return_value = mock_repo

                with TestClient(app) as client:
                    resp = client.get("/v1/spaces", headers={"Authorization": f"Bearer {token_a}"})

        assert resp.status_code == 200
        ids = {sp["id"] for sp in resp.json().get("spaces", [])}
        assert str(a_space.id) in ids
        assert str(b_space.id) not in ids
        # The endpoint calls list_accessible_by_user scoped to the active company.
        mock_repo.list_accessible_by_user.assert_awaited_once()
        _, call_company_id = mock_repo.list_accessible_by_user.await_args.args
        assert call_company_id == company_a_id

    def test_cross_company_by_id_is_byte_identical_to_absent(self, two_company_setup):
        """SC-005/C-004: a Company B space id and a random id return the same 404 bytes;
        the Company B probe writes at least one cross_tenant_denied audit row."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        b_space_id = uuid.uuid4()
        random_id = uuid.uuid4()

        from tessera_api.main import app

        results = []
        for probe_id in (b_space_id, random_id):
            with _bypass_onboarding_guard():
                with (
                    patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_repo_cls,
                    patch(
                        "tessera_api.routers.spaces.write_audit", new_callable=AsyncMock
                    ) as mock_audit,
                ):
                    mock_repo = AsyncMock()
                    # User has no accessible spaces — probe_id won't be in accessible set
                    mock_repo.list_accessible_by_user = AsyncMock(return_value=[])
                    mock_repo.get_by_id_for_company = AsyncMock(return_value=None)
                    mock_repo_cls.return_value = mock_repo

                    with TestClient(app) as client:
                        resp = client.get(
                            f"/v1/spaces/{probe_id}",
                            headers={"Authorization": f"Bearer {token_a}"},
                        )
            results.append((resp.status_code, resp.content, _cross_tenant_denied_count(mock_audit)))

        # Indistinguishable: same status and byte-identical body.
        assert results[0][0] == results[1][0] == 404
        assert results[0][1] == results[1][1]
        # Body is the generic not-found shape (carried from 036).
        import json

        assert json.loads(results[0][1]) == _GENERIC_NOT_FOUND
        # Both probes write an audit since space_in_company returns None in both cases.
        assert results[0][2] == 1


# ---------------------------------------------------------------------------
# US2 — Membership in a company is enough to reach that company's spaces
# ---------------------------------------------------------------------------


class TestUS2MembershipAndRole:
    def test_member_without_platform_status_sees_own_company_spaces(self, two_company_setup):
        """SC-004/C-003: an ordinary member (no is_admin) of Company B sees B's spaces."""
        token_a, company_a_id, token_b, company_b_id = two_company_setup
        b_space = _make_space(company_b_id)

        from tessera_api.main import app

        with _bypass_onboarding_guard():
            with patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.list_accessible_by_user = AsyncMock(
                    return_value=[_make_access(b_space)]
                )
                mock_repo_cls.return_value = mock_repo

                with TestClient(app) as client:
                    resp = client.get("/v1/spaces", headers={"Authorization": f"Bearer {token_b}"})

        assert resp.status_code == 200
        ids = {sp["id"] for sp in resp.json().get("spaces", [])}
        # Reachability requires only membership, not any platform-wide status.
        assert str(b_space.id) in ids
        mock_repo.list_accessible_by_user.assert_awaited_once()
        _, call_company_id = mock_repo.list_accessible_by_user.await_args.args
        assert call_company_id == company_b_id

    def test_authorized_member_management_action_succeeds(self, admin_company_setup):
        """AC2: an admin of Company A manages an own-company space successfully."""
        token_a, company_a_id, _tb, _cb = admin_company_setup
        a_space = _make_space(company_a_id)

        from tessera_api.main import app
        from tessera_core.domain.entities import Confidentiality, RolePermission, UserRole

        with _bypass_onboarding_guard():
            with patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id_for_company = AsyncMock(return_value=a_space)
                mock_repo.create_role_permission = AsyncMock(
                    side_effect=lambda p: RolePermission(
                        space_id=p.space_id,
                        idp_group=p.idp_group,
                        role=p.role,
                        max_confidentiality=p.max_confidentiality,
                    )
                )
                mock_repo_cls.return_value = mock_repo

                with TestClient(app) as client:
                    resp = client.post(
                        f"/v1/spaces/{a_space.id}/permissions",
                        json={
                            "idp_group": "eng",
                            "role": UserRole.READER.value,
                            "max_confidentiality": Confidentiality.INTERNAL.value,
                        },
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert resp.status_code == 201
        mock_repo.create_role_permission.assert_awaited_once()

    def test_role_forbidden_action_is_403_not_404(self, two_company_setup):
        """AC3: a non-admin member managing an own-company space is refused 403 (role),
        NOT 404 (which would hide the space). The refusal is role-based, not visibility."""
        token_a, company_a_id, _tb, _cb = two_company_setup
        a_space_id = uuid.uuid4()

        from tessera_api.main import app

        with _bypass_onboarding_guard():
            with patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                # Even if asked, the space exists for Company A — but role gating
                # rejects before any visibility check is reached.
                mock_repo.get_by_id_for_company = AsyncMock(return_value=_make_space(company_a_id))
                mock_repo_cls.return_value = mock_repo

                with TestClient(app) as client:
                    resp = client.post(
                        f"/v1/spaces/{a_space_id}/permissions",
                        json={"idp_group": "eng", "role": "reader"},
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert resp.status_code == 403
        assert resp.json() == _GENERIC_FORBIDDEN
        # Role gate fired before the space was ever resolved — not a hidden-space 404.
        mock_repo.get_by_id_for_company.assert_not_awaited()


# ---------------------------------------------------------------------------
# US3 — Platform-wide status grants no cross-company visibility
# ---------------------------------------------------------------------------


class TestUS3PlatformStatusNoVisibility:
    def test_global_admin_in_no_space_company_sees_empty(self, reproduction_setup):
        """US3 AC1: a global admin active as a company that owns no spaces sees {}."""
        s = reproduction_setup

        from tessera_api.main import app

        with _bypass_onboarding_guard():
            with patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.list_accessible_by_user = AsyncMock(return_value=[])
                mock_repo_cls.return_value = mock_repo

                with TestClient(app) as client:
                    resp = client.get(
                        "/v1/spaces", headers={"Authorization": f"Bearer {s.a3_token}"}
                    )

        assert resp.status_code == 200
        # The legacy global is_admin flag confers no visibility — only company 3's
        # (empty) accessible space set is resolved.
        assert resp.json().get("spaces", []) == []
        mock_repo.list_accessible_by_user.assert_awaited_once()
        _, call_company_id = mock_repo.list_accessible_by_user.await_args.args
        assert call_company_id == s.company3_id
