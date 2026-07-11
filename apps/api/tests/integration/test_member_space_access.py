"""Integration tests: member-centric space access flow (feature 058, US1).

Drives the full grant lifecycle over HTTP with stateful in-memory repositories:
admin reads a fresh member's access → grants via the existing per-space member
endpoint → the read model and the member's own space list reflect it → role
change and revoke reflect on re-fetch (FR-001, FR-002, FR-003, FR-008, FR-011).
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from tessera_core.domain.entities import (
    CompanyMembership,
    CompanyRole,
    Space,
    SpaceMembership,
    SpaceRole,
    User,
)
from tessera_core.domain.space_access import SpaceAccess

COMPANY_ID = uuid.uuid4()
ADMIN_ID = uuid.uuid4()
MEMBER_ID = uuid.uuid4()


def _auth_header(user_id: uuid.UUID) -> dict:
    from tessera_api.auth.jwt_auth import create_access_token

    token = create_access_token(user_id, "actor@example.com", False, company_id=COMPANY_ID)
    return {"Authorization": f"Bearer {token}"}


def _space(name: str, parent_id: uuid.UUID | None = None) -> Space:
    return Space(
        id=uuid.uuid4(),
        slug=f"sp-{uuid.uuid4().hex[:6]}",
        name=name,
        sector="tech",
        company_id=COMPANY_ID,
        parent_space_id=parent_id,
    )


class FakeSpaceRepository:
    """Company-scoped space store with CTE-equivalent access derivation."""

    def __init__(self, spaces: list[Space], memberships: FakeSpaceMembershipRepository) -> None:
        self._spaces = {s.id: s for s in spaces}
        self._memberships = memberships

    async def list_by_company(self, company_id: uuid.UUID) -> list[Space]:
        return [s for s in self._spaces.values() if s.company_id == company_id]

    async def get_by_id_for_company(
        self, space_id: uuid.UUID, company_id: uuid.UUID
    ) -> Space | None:
        space = self._spaces.get(space_id)
        return space if space is not None and space.company_id == company_id else None

    async def list_accessible_by_user(
        self, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> list[SpaceAccess]:
        direct = {
            m.space_id: m.role
            for m in self._memberships.rows
            if m.user_id == user_id and m.space_id in self._spaces
        }
        result = []
        for space in self._spaces.values():
            if space.company_id != company_id:
                continue
            # nearest ancestor (or self) holding a direct membership wins
            current: Space | None = space
            while current is not None:
                if current.id in direct:
                    result.append(
                        SpaceAccess(
                            space=space,
                            effective_role=direct[current.id],
                            is_direct=current.id == space.id,
                        )
                    )
                    break
                parent_id = current.parent_space_id
                current = self._spaces.get(parent_id) if parent_id else None
        return result


class FakeSpaceMembershipRepository:
    def __init__(self) -> None:
        self.rows: list[SpaceMembership] = []

    async def add(self, membership: SpaceMembership) -> SpaceMembership:
        self.rows.append(membership)
        return membership

    async def get(self, space_id: uuid.UUID, user_id: uuid.UUID) -> SpaceMembership | None:
        return next((m for m in self.rows if m.space_id == space_id and m.user_id == user_id), None)

    async def list_by_space(self, space_id: uuid.UUID) -> list[SpaceMembership]:
        return [m for m in self.rows if m.space_id == space_id]

    async def list_by_user(self, user_id: uuid.UUID) -> list[SpaceMembership]:
        return [m for m in self.rows if m.user_id == user_id]

    async def update_role(
        self, space_id: uuid.UUID, user_id: uuid.UUID, role: SpaceRole
    ) -> SpaceMembership:
        membership = await self.get(space_id, user_id)
        updated = membership.model_copy(update={"role": role})
        self.rows[self.rows.index(membership)] = updated
        return updated

    async def remove(self, space_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.rows = [m for m in self.rows if not (m.space_id == space_id and m.user_id == user_id)]

    async def count_admins(self, space_id: uuid.UUID) -> int:
        return sum(1 for m in self.rows if m.space_id == space_id and m.role == SpaceRole.ADMIN)


def _company_membership_for(user_id: uuid.UUID, company_id: uuid.UUID) -> CompanyMembership | None:
    role = {ADMIN_ID: CompanyRole.ADMIN, MEMBER_ID: CompanyRole.MEMBER}.get(user_id)
    if role is None or company_id != COMPANY_ID:
        return None
    return CompanyMembership(
        id=uuid.uuid4(),
        user_id=user_id,
        company_id=company_id,
        role=role,
        joined_at=datetime.now(UTC),
    )


def _user_for(user_id: uuid.UUID) -> User | None:
    names = {ADMIN_ID: ("Admin", "admin@acme.test"), MEMBER_ID: ("Member", "member@acme.test")}
    if user_id not in names:
        return None
    name, email = names[user_id]
    return User(
        id=user_id,
        external_subject=f"sub-{user_id}",
        email=email,
        display_name=name,
        is_admin=False,
    )


@contextmanager
def _wired_app(spaces: list[Space], membership_repo: FakeSpaceMembershipRepository):
    """Patch every touched router onto the shared fake repositories."""
    from tessera_api.adapters.database import get_db
    from tessera_api.auth.bearer import require_onboarding_complete
    from tessera_api.main import app

    space_repo = FakeSpaceRepository(spaces, membership_repo)

    company_repo = AsyncMock()
    company_repo.get_membership = AsyncMock(side_effect=_company_membership_for)
    company_repo.get_by_id = AsyncMock(return_value=None)

    user_repo = AsyncMock()
    user_repo.get_by_id = AsyncMock(side_effect=_user_for)

    mock_session = AsyncMock()

    async def _fake_db():
        yield mock_session

    async def _noop():
        return None

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[require_onboarding_complete] = _noop
    try:
        with (
            patch("tessera_api.auth.oidc.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.SqlSpaceRepository", return_value=space_repo),
            patch(
                "tessera_api.routers.companies.SqlSpaceMembershipRepository",
                return_value=membership_repo,
            ),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
            patch("tessera_api.routers.spaces.SqlSpaceRepository", return_value=space_repo),
            patch("tessera_api.routers.members.SqlSpaceRepository", return_value=space_repo),
            patch("tessera_api.routers.members.SqlUserRepository", return_value=user_repo),
            patch(
                "tessera_api.routers.members.SqlSpaceMembershipRepository",
                return_value=membership_repo,
            ),
            patch("tessera_api.routers.members.SqlAuditRepository", return_value=AsyncMock()),
            TestClient(app) as client,
        ):
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_onboarding_complete, None)


def _fetch_access(client: TestClient) -> dict:
    resp = client.get(
        f"/v1/companies/members/{MEMBER_ID}/space-access",
        headers=_auth_header(ADMIN_ID),
    )
    assert resp.status_code == 200, resp.text
    return {row["id"]: row for row in resp.json()["spaces"]}


class TestGrantLifecycle:
    def test_grant_change_revoke_lifecycle(self):
        parent = _space("Engineering")
        child = _space("Docs", parent_id=parent.id)
        membership_repo = FakeSpaceMembershipRepository()

        with _wired_app([parent, child], membership_repo) as client:
            # 1. Fresh member: every company space listed, no access anywhere (FR-001).
            rows = _fetch_access(client)
            assert set(rows) == {str(parent.id), str(child.id)}
            assert all(r["effective_role"] is None for r in rows.values())

            # The member's own space list is empty before any grant.
            resp = client.get("/v1/spaces", headers=_auth_header(MEMBER_ID))
            assert resp.status_code == 200
            assert resp.json()["spaces"] == []

            # 2. Grant viewer on the parent via the existing endpoint (FR-002, FR-011).
            resp = client.post(
                f"/v1/spaces/{parent.id}/members",
                json={"user_id": str(MEMBER_ID), "role": "viewer"},
                headers=_auth_header(ADMIN_ID),
            )
            assert resp.status_code == 201, resp.text

            # 3. Re-fetch: direct on parent, inherited on child (FR-008).
            rows = _fetch_access(client)
            assert rows[str(parent.id)]["direct_role"] == "viewer"
            assert rows[str(parent.id)]["is_direct"] is True
            assert rows[str(child.id)]["direct_role"] is None
            assert rows[str(child.id)]["effective_role"] == "viewer"
            assert rows[str(child.id)]["is_direct"] is False

            # 4. The member now sees the space (and its child) on GET /v1/spaces.
            resp = client.get("/v1/spaces", headers=_auth_header(MEMBER_ID))
            assert resp.status_code == 200
            listed = {s["id"] for s in resp.json()["spaces"]}
            assert listed == {str(parent.id), str(child.id)}

            # 5. Role change via PUT reflects on re-fetch (FR-003).
            resp = client.put(
                f"/v1/spaces/{parent.id}/members/{MEMBER_ID}",
                json={"role": "editor"},
                headers=_auth_header(ADMIN_ID),
            )
            assert resp.status_code == 200, resp.text
            rows = _fetch_access(client)
            assert rows[str(parent.id)]["direct_role"] == "editor"
            assert rows[str(child.id)]["effective_role"] == "editor"

            # 6. Revoke via DELETE clears both direct and inherited access (FR-003).
            resp = client.delete(
                f"/v1/spaces/{parent.id}/members/{MEMBER_ID}",
                headers=_auth_header(ADMIN_ID),
            )
            assert resp.status_code == 204
            rows = _fetch_access(client)
            assert all(r["effective_role"] is None for r in rows.values())
            resp = client.get("/v1/spaces", headers=_auth_header(MEMBER_ID))
            assert resp.json()["spaces"] == []

    def test_duplicate_grant_returns_400_and_keeps_access(self):
        space = _space("Engineering")
        membership_repo = FakeSpaceMembershipRepository()

        with _wired_app([space], membership_repo) as client:
            resp = client.post(
                f"/v1/spaces/{space.id}/members",
                json={"user_id": str(MEMBER_ID), "role": "viewer"},
                headers=_auth_header(ADMIN_ID),
            )
            assert resp.status_code == 201

            resp = client.post(
                f"/v1/spaces/{space.id}/members",
                json={"user_id": str(MEMBER_ID), "role": "editor"},
                headers=_auth_header(ADMIN_ID),
            )
            assert resp.status_code == 400

            # existing access intact — still viewer, still direct
            rows = _fetch_access(client)
            assert rows[str(space.id)]["direct_role"] == "viewer"
            assert rows[str(space.id)]["is_direct"] is True
