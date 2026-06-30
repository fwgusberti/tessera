"""API integration tests for nested-space hierarchy endpoints.

TDD: all tests were written before the implementation of T010/T021/T022.
Run: cd apps/api && uv run pytest tests/test_space_hierarchy.py -v

Uses fastapi.testclient.TestClient (sync) and patches router-module symbols
per the project test baseline.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tessera_core.domain.space import Space
from tessera_core.domain.space_access import SpaceAccess
from tessera_core.domain.space_role import SpaceRole


def _space(company_id: uuid.UUID, parent_id: uuid.UUID | None = None) -> Space:
    return Space(
        id=uuid.uuid4(),
        slug=f"sp-{uuid.uuid4().hex[:6]}",
        name="Engineering",
        sector="tech",
        company_id=company_id,
        parent_space_id=parent_id,
    )


def _access(space: Space, role: SpaceRole = SpaceRole.ADMIN, is_direct: bool = True) -> SpaceAccess:
    return SpaceAccess(space=space, effective_role=role, is_direct=is_direct)


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


# ---------------------------------------------------------------------------
# US1 — GET /v1/spaces returns user-accessible spaces with hierarchy fields
# ---------------------------------------------------------------------------


class TestListSpacesWithHierarchy:
    def test_returns_effective_role_and_is_direct_fields(self, two_company_setup):
        """GET /v1/spaces response includes effective_role and is_direct per space."""
        token_a, company_a_id, _tb, _cb = two_company_setup
        parent = _space(company_a_id)
        child = _space(company_a_id, parent_id=parent.id)

        accessible = [
            _access(parent, SpaceRole.ADMIN, is_direct=True),
            _access(child, SpaceRole.ADMIN, is_direct=False),
        ]

        from tessera_api.main import app

        with _bypass_onboarding():
            with patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_cls:
                mock_repo = AsyncMock()
                mock_repo.list_accessible_by_user = AsyncMock(return_value=accessible)
                mock_cls.return_value = mock_repo

                with TestClient(app) as client:
                    resp = client.get(
                        "/v1/spaces",
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert resp.status_code == 200
        spaces = resp.json()["spaces"]
        assert len(spaces) == 2

        parent_resp = next(s for s in spaces if s["id"] == str(parent.id))
        assert parent_resp["effective_role"] == "admin"
        assert parent_resp["is_direct"] is True
        assert parent_resp["parent_space_id"] is None

        child_resp = next(s for s in spaces if s["id"] == str(child.id))
        assert child_resp["effective_role"] == "admin"
        assert child_resp["is_direct"] is False
        assert child_resp["parent_space_id"] == str(parent.id)

    def test_user_without_memberships_sees_empty_list(self, two_company_setup):
        """User with no memberships gets an empty spaces list."""
        token_a, company_a_id, _tb, _cb = two_company_setup

        from tessera_api.main import app

        with _bypass_onboarding():
            with patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_cls:
                mock_repo = AsyncMock()
                mock_repo.list_accessible_by_user = AsyncMock(return_value=[])
                mock_cls.return_value = mock_repo

                with TestClient(app) as client:
                    resp = client.get(
                        "/v1/spaces",
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert resp.status_code == 200
        assert resp.json()["spaces"] == []

    def test_inherited_access_appears_without_direct_membership(self, two_company_setup):
        """Child space appears with is_direct=false when access is purely inherited."""
        token_a, company_a_id, _tb, _cb = two_company_setup
        parent = _space(company_a_id)
        child = _space(company_a_id, parent_id=parent.id)

        accessible = [
            _access(parent, SpaceRole.EDITOR, is_direct=True),
            _access(child, SpaceRole.EDITOR, is_direct=False),
        ]

        from tessera_api.main import app

        with _bypass_onboarding():
            with patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_cls:
                mock_repo = AsyncMock()
                mock_repo.list_accessible_by_user = AsyncMock(return_value=accessible)
                mock_cls.return_value = mock_repo

                with TestClient(app) as client:
                    resp = client.get(
                        "/v1/spaces",
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert resp.status_code == 200
        spaces = resp.json()["spaces"]
        child_resp = next(s for s in spaces if s["id"] == str(child.id))
        assert child_resp["is_direct"] is False
        assert child_resp["parent_space_id"] == str(parent.id)


# ---------------------------------------------------------------------------
# US3 — PATCH /v1/spaces/{id}/parent
# ---------------------------------------------------------------------------


class TestPatchParent:
    def test_set_parent_success(self, two_company_setup):
        """Admin user sets a parent successfully — 200 with updated space."""
        token_a, company_a_id, _tb, _cb = two_company_setup
        child = _space(company_a_id)
        parent = _space(company_a_id)
        updated = _space(company_a_id, parent_id=parent.id)
        updated = updated.model_copy(update={"id": child.id})

        from tessera_api.main import app

        with _bypass_onboarding():
            with (
                patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_repo_cls,
                patch("tessera_api.routers.spaces.SqlSpaceMembershipRepository") as mock_mem_cls,
            ):
                mock_repo = AsyncMock()
                mock_mem = AsyncMock()
                mock_repo_cls.return_value = mock_repo
                mock_mem_cls.return_value = mock_mem

                with patch("tessera_api.routers.spaces.SpaceHierarchyService") as mock_svc_cls:
                    mock_svc = AsyncMock()
                    mock_svc.set_parent = AsyncMock(return_value=updated)
                    mock_svc_cls.return_value = mock_svc

                    with TestClient(app) as client:
                        resp = client.patch(
                            f"/v1/spaces/{child.id}/parent",
                            json={"parent_space_id": str(parent.id)},
                            headers={"Authorization": f"Bearer {token_a}"},
                        )

        assert resp.status_code == 200
        assert resp.json()["space"]["id"] == str(child.id)
        assert resp.json()["space"]["parent_space_id"] == str(parent.id)

    def test_cycle_rejection_returns_400(self, two_company_setup):
        """Cycle attempt returns 400 with invalid_parent error code."""
        token_a, company_a_id, _tb, _cb = two_company_setup
        space_a = _space(company_a_id)
        space_b = _space(company_a_id, parent_id=space_a.id)

        from tessera_api.main import app

        with _bypass_onboarding():
            with (
                patch("tessera_api.routers.spaces.SqlSpaceRepository"),
                patch("tessera_api.routers.spaces.SqlSpaceMembershipRepository"),
                patch("tessera_api.routers.spaces.SpaceHierarchyService") as mock_svc_cls,
            ):
                mock_svc = AsyncMock()
                mock_svc.set_parent = AsyncMock(side_effect=ValueError("cycle"))
                mock_svc_cls.return_value = mock_svc

                with TestClient(app) as client:
                    resp = client.patch(
                        f"/v1/spaces/{space_a.id}/parent",
                        json={"parent_space_id": str(space_b.id)},
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_parent"

    def test_self_parent_returns_400(self, two_company_setup):
        """Self-parent attempt returns 400 with invalid_parent."""
        token_a, company_a_id, _tb, _cb = two_company_setup
        space = _space(company_a_id)

        from tessera_api.main import app

        with _bypass_onboarding():
            with (
                patch("tessera_api.routers.spaces.SqlSpaceRepository"),
                patch("tessera_api.routers.spaces.SqlSpaceMembershipRepository"),
                patch("tessera_api.routers.spaces.SpaceHierarchyService") as mock_svc_cls,
            ):
                mock_svc = AsyncMock()
                mock_svc.set_parent = AsyncMock(side_effect=ValueError("self_parent"))
                mock_svc_cls.return_value = mock_svc

                with TestClient(app) as client:
                    resp = client.patch(
                        f"/v1/spaces/{space.id}/parent",
                        json={"parent_space_id": str(space.id)},
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_parent"

    def test_missing_admin_returns_403(self, two_company_setup):
        """Actor lacking admin role gets 403."""
        token_a, company_a_id, _tb, _cb = two_company_setup
        child = _space(company_a_id)
        parent = _space(company_a_id)

        from tessera_api.main import app

        with _bypass_onboarding():
            with (
                patch("tessera_api.routers.spaces.SqlSpaceRepository"),
                patch("tessera_api.routers.spaces.SqlSpaceMembershipRepository"),
                patch("tessera_api.routers.spaces.SpaceHierarchyService") as mock_svc_cls,
            ):
                mock_svc = AsyncMock()
                mock_svc.set_parent = AsyncMock(side_effect=PermissionError())
                mock_svc_cls.return_value = mock_svc

                with TestClient(app) as client:
                    resp = client.patch(
                        f"/v1/spaces/{child.id}/parent",
                        json={"parent_space_id": str(parent.id)},
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "forbidden"


# ---------------------------------------------------------------------------
# US3 — DELETE /v1/spaces/{id}/parent
# ---------------------------------------------------------------------------


class TestDeleteParent:
    def test_remove_parent_success(self, two_company_setup):
        """Admin removes parent — 200 with parent_space_id=null."""
        token_a, company_a_id, _tb, _cb = two_company_setup
        child = _space(company_a_id)
        demoted = _space(company_a_id)
        demoted = demoted.model_copy(update={"id": child.id, "parent_space_id": None})

        from tessera_api.main import app

        with _bypass_onboarding():
            with (
                patch("tessera_api.routers.spaces.SqlSpaceRepository"),
                patch("tessera_api.routers.spaces.SqlSpaceMembershipRepository"),
                patch("tessera_api.routers.spaces.SpaceHierarchyService") as mock_svc_cls,
            ):
                mock_svc = AsyncMock()
                mock_svc.remove_parent = AsyncMock(return_value=demoted)
                mock_svc_cls.return_value = mock_svc

                with TestClient(app) as client:
                    resp = client.delete(
                        f"/v1/spaces/{child.id}/parent",
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert resp.status_code == 200
        assert resp.json()["space"]["parent_space_id"] is None

    def test_remove_parent_forbidden(self, two_company_setup):
        """Non-admin gets 403 on DELETE parent."""
        token_a, company_a_id, _tb, _cb = two_company_setup
        space = _space(company_a_id)

        from tessera_api.main import app

        with _bypass_onboarding():
            with (
                patch("tessera_api.routers.spaces.SqlSpaceRepository"),
                patch("tessera_api.routers.spaces.SqlSpaceMembershipRepository"),
                patch("tessera_api.routers.spaces.SpaceHierarchyService") as mock_svc_cls,
            ):
                mock_svc = AsyncMock()
                mock_svc.remove_parent = AsyncMock(side_effect=PermissionError())
                mock_svc_cls.return_value = mock_svc

                with TestClient(app) as client:
                    resp = client.delete(
                        f"/v1/spaces/{space.id}/parent",
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /v1/spaces/{id}/ancestors
# ---------------------------------------------------------------------------


class TestGetAncestors:
    def test_returns_ancestor_chain(self, two_company_setup):
        """Ancestors endpoint returns ordered chain for breadcrumb display."""
        token_a, company_a_id, _tb, _cb = two_company_setup
        root = _space(company_a_id)
        child = _space(company_a_id, parent_id=root.id)

        from tessera_api.main import app

        with _bypass_onboarding():
            with patch("tessera_api.routers.spaces.SqlSpaceRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.list_accessible_by_user = AsyncMock(
                    return_value=[_access(child, SpaceRole.VIEWER, is_direct=True)]
                )
                mock_repo.get_by_id_for_company = AsyncMock(return_value=child)
                mock_repo.get_ancestor_chain = AsyncMock(return_value=[root])
                mock_repo_cls.return_value = mock_repo

                with TestClient(app) as client:
                    resp = client.get(
                        f"/v1/spaces/{child.id}/ancestors",
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

        assert resp.status_code == 200
        ancestors = resp.json()["ancestors"]
        assert len(ancestors) == 1
        assert ancestors[0]["id"] == str(root.id)
        assert ancestors[0]["name"] == root.name
        assert ancestors[0]["slug"] == root.slug
