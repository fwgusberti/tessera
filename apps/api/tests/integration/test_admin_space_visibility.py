"""Integration tests: admin-wide space visibility (feature 058, US2).

Company admins see every space of the active company on GET /v1/spaces —
non-member spaces with ``effective_role: "admin"``, ``is_direct: false`` —
and can open them via GET /v1/spaces/{id} and /ancestors. Non-admin members
keep the membership-derived view (FR-005). Response shapes are unchanged.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from tessera_core.domain.entities import Space, SpaceRole
from tessera_core.domain.space_access import SpaceAccess


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


def _space(company_id: uuid.UUID, name: str, parent_id: uuid.UUID | None = None) -> Space:
    return Space(
        id=uuid.uuid4(),
        slug=f"sp-{uuid.uuid4().hex[:6]}",
        name=name,
        sector="tech",
        company_id=company_id,
        parent_space_id=parent_id,
    )


@contextmanager
def _spaces_router_repo(accesses: list[SpaceAccess], company_spaces: list[Space]):
    with (
        patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_repo_cls,
        patch("tessera_api.routers.spaces.SqlSpaceMembershipRepository", return_value=AsyncMock()),
        patch("tessera_api.routers.spaces.write_audit", new_callable=AsyncMock),
    ):
        mock_repo = AsyncMock()
        mock_repo.list_accessible_by_user = AsyncMock(return_value=accesses)
        mock_repo.list_by_company = AsyncMock(return_value=company_spaces)
        mock_repo.get_by_id_for_company = AsyncMock(
            side_effect=lambda sid, cid: next(
                (s for s in company_spaces if s.id == sid and s.company_id == cid), None
            )
        )
        mock_repo.get_ancestor_chain = AsyncMock(return_value=[])
        mock_repo_cls.return_value = mock_repo
        yield mock_repo


class TestAdminWideVisibility:
    def test_admin_listing_includes_non_member_space_as_implicit_admin(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup
        member_space = _space(company_a_id, "Mine")
        other_space = _space(company_a_id, "Not mine")

        with (
            _bypass_onboarding_guard(),
            _spaces_router_repo(
                [SpaceAccess(space=member_space, effective_role=SpaceRole.VIEWER, is_direct=True)],
                [member_space, other_space],
            ),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.get("/v1/spaces", headers={"Authorization": f"Bearer {token_a}"})

        assert resp.status_code == 200
        spaces = {s["id"]: s for s in resp.json()["spaces"]}
        assert set(spaces) == {str(member_space.id), str(other_space.id)}

        # membership-derived entry unchanged
        assert spaces[str(member_space.id)]["effective_role"] == "viewer"
        assert spaces[str(member_space.id)]["is_direct"] is True

        # non-member entry carries the implicit admin role
        assert spaces[str(other_space.id)]["effective_role"] == "admin"
        assert spaces[str(other_space.id)]["is_direct"] is False

        # response shape unchanged: same keys on both entries
        assert set(spaces[str(member_space.id)].keys()) == set(spaces[str(other_space.id)].keys())

    def test_admin_can_open_non_member_space_and_ancestors(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup
        other_space = _space(company_a_id, "Not mine")

        with _bypass_onboarding_guard(), _spaces_router_repo([], [other_space]):
            from tessera_api.main import app

            with TestClient(app) as client:
                get_resp = client.get(
                    f"/v1/spaces/{other_space.id}",
                    headers={"Authorization": f"Bearer {token_a}"},
                )
                anc_resp = client.get(
                    f"/v1/spaces/{other_space.id}/ancestors",
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert get_resp.status_code == 200, get_resp.text
        assert get_resp.json()["space"]["id"] == str(other_space.id)
        assert anc_resp.status_code == 200, anc_resp.text
        assert anc_resp.json() == {"ancestors": []}

    def test_non_admin_member_sees_only_membership_derived_spaces(self, two_company_setup):
        token_a, company_a_id, _tb, _cb = two_company_setup
        member_space = _space(company_a_id, "Mine")
        other_space = _space(company_a_id, "Not mine")

        with (
            _bypass_onboarding_guard(),
            _spaces_router_repo(
                [SpaceAccess(space=member_space, effective_role=SpaceRole.EDITOR, is_direct=True)],
                [member_space, other_space],
            ),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                list_resp = client.get("/v1/spaces", headers={"Authorization": f"Bearer {token_a}"})
                get_resp = client.get(
                    f"/v1/spaces/{other_space.id}",
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert list_resp.status_code == 200
        ids = [s["id"] for s in list_resp.json()["spaces"]]
        assert ids == [str(member_space.id)]
        # a non-member space stays a generic 404 for plain members (FR-005)
        assert get_resp.status_code == 404
