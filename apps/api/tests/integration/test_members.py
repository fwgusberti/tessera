"""Integration tests: member management flows — invite, change-role, remove, list."""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sqlalchemy as sa

from tessera_core.domain.entities import (
    CompanyMembership,
    CompanyRole,
    Space,
    SpaceMemberListing,
    SpaceMembership,
    SpaceRole,
    User,
)

# Shared company that owns the spaces under test; member-write paths are now
# company-scoped (feature 035), so tokens carry this company and the auth layer
# resolves a membership for it.
COMPANY_ID = uuid.uuid4()


def _make_jwt_header(
    user_id: uuid.UUID, is_admin: bool = False, company_id: uuid.UUID = COMPANY_ID
) -> dict:
    from tessera_api.auth.jwt_auth import create_access_token

    token = create_access_token(user_id, "actor@example.com", is_admin, company_id=company_id)
    return {"Authorization": f"Bearer {token}"}


def _mock_db():
    m = MagicMock()
    s = AsyncMock()
    m.return_value.__aenter__ = AsyncMock(return_value=s)
    m.return_value.__aexit__ = AsyncMock(return_value=None)
    return m


def _make_user(user_id: uuid.UUID | None = None, is_admin: bool = False) -> User:
    uid = user_id or uuid.uuid4()
    return User(
        id=uid,
        external_subject=f"sub-{uid}",
        email="actor@example.com",
        display_name="Actor",
        is_admin=is_admin,
    )


def _membership(space_id: uuid.UUID, user_id: uuid.UUID, role: SpaceRole) -> SpaceMembership:
    return SpaceMembership(space_id=space_id, user_id=user_id, role=role)


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


@contextmanager
def _member_write_auth():
    """Bypass onboarding + satisfy company context + in-company space for member writes.

    Patches the auth-layer membership lookup (MEMBER role is enough; the per-space
    role rule is what these tests exercise) and the space-ownership check so the
    handler proceeds to ``MembershipService``.
    """
    now = datetime.now(UTC)

    def _ms(uid, cid):
        return CompanyMembership(
            id=uuid.uuid4(),
            user_id=uid,
            company_id=cid,
            role=CompanyRole.MEMBER,
            joined_at=now,
        )

    company_repo = AsyncMock()
    company_repo.get_membership = AsyncMock(side_effect=_ms)

    space_repo = AsyncMock()
    space_repo.get_by_id_for_company = AsyncMock(
        return_value=Space(slug="s", name="S", sector="x", company_id=COMPANY_ID)
    )

    with (
        _bypass_onboarding_guard(),
        patch("tessera_api.auth.oidc.get_db", _mock_db()),
        patch("tessera_api.auth.oidc.SqlCompanyRepository", return_value=company_repo),
        patch("tessera_api.routers.members.SqlSpaceRepository", return_value=space_repo),
    ):
        yield


class TestInviteMemberIntegration:
    def test_admin_can_invite_member(self):
        from fastapi.testclient import TestClient

        from tessera_api.main import app

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        actor = _make_user(actor_id)
        invited_membership = _membership(space_id, target_id, SpaceRole.EDITOR).model_copy(
            update={"invited_by_user_id": actor_id}
        )

        with _member_write_auth():
            with (
                patch("tessera_api.routers.members.get_db") as mock_get_db,
                patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
                patch(
                    "tessera_api.routers.members.SqlSpaceMembershipRepository"
                ) as mock_membership_repo_cls,
                patch("tessera_api.routers.members.SqlAuditRepository") as mock_audit_cls,
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_user_repo = AsyncMock()
                mock_user_repo.get_by_id.return_value = actor
                mock_user_repo_cls.return_value = mock_user_repo

                mock_membership_repo = AsyncMock()
                mock_membership_repo.list_by_space.return_value = [
                    _membership(space_id, actor_id, SpaceRole.ADMIN)
                ]
                mock_membership_repo.get.return_value = None
                mock_membership_repo.add.return_value = invited_membership
                mock_membership_repo_cls.return_value = mock_membership_repo

                mock_audit_cls.return_value = AsyncMock()

                with TestClient(app) as client:
                    resp = client.post(
                        f"/v1/spaces/{space_id}/members",
                        json={"user_id": str(target_id), "role": "editor"},
                        headers=_make_jwt_header(actor_id),
                    )

        assert resp.status_code == 201
        data = resp.json()
        assert data["membership"]["role"] == "editor"

    def test_non_admin_cannot_invite(self):
        from fastapi.testclient import TestClient

        from tessera_api.main import app

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        actor = _make_user(actor_id)

        with _member_write_auth():
            with (
                patch("tessera_api.routers.members.get_db") as mock_get_db,
                patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
                patch(
                    "tessera_api.routers.members.SqlSpaceMembershipRepository"
                ) as mock_membership_repo_cls,
                patch("tessera_api.routers.members.SqlAuditRepository"),
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_user_repo = AsyncMock()
                mock_user_repo.get_by_id.return_value = actor
                mock_user_repo_cls.return_value = mock_user_repo

                mock_membership_repo = AsyncMock()
                mock_membership_repo.list_by_space.return_value = [
                    _membership(space_id, actor_id, SpaceRole.EDITOR)
                ]
                mock_membership_repo_cls.return_value = mock_membership_repo

                with TestClient(app) as client:
                    resp = client.post(
                        f"/v1/spaces/{space_id}/members",
                        json={"user_id": str(uuid.uuid4()), "role": "viewer"},
                        headers=_make_jwt_header(actor_id),
                    )

        assert resp.status_code == 403


class TestChangeRoleIntegration:
    def test_admin_can_change_role(self):
        from fastapi.testclient import TestClient

        from tessera_api.main import app

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        actor = _make_user(actor_id)
        updated = _membership(space_id, target_id, SpaceRole.EDITOR)

        with _member_write_auth():
            with (
                patch("tessera_api.routers.members.get_db") as mock_get_db,
                patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
                patch(
                    "tessera_api.routers.members.SqlSpaceMembershipRepository"
                ) as mock_membership_repo_cls,
                patch("tessera_api.routers.members.SqlAuditRepository") as mock_audit_cls,
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_user_repo = AsyncMock()
                mock_user_repo.get_by_id.return_value = actor
                mock_user_repo_cls.return_value = mock_user_repo

                mock_membership_repo = AsyncMock()
                mock_membership_repo.list_by_space.return_value = [
                    _membership(space_id, actor_id, SpaceRole.ADMIN),
                    _membership(space_id, target_id, SpaceRole.VIEWER),
                ]
                mock_membership_repo.count_admins.return_value = 2
                mock_membership_repo.update_role.return_value = updated
                mock_membership_repo_cls.return_value = mock_membership_repo

                mock_audit_cls.return_value = AsyncMock()

                with TestClient(app) as client:
                    resp = client.put(
                        f"/v1/spaces/{space_id}/members/{target_id}",
                        json={"role": "editor"},
                        headers=_make_jwt_header(actor_id),
                    )

        assert resp.status_code == 200
        assert resp.json()["membership"]["role"] == "editor"

    def test_last_admin_guard_returns_409(self):
        from fastapi.testclient import TestClient

        from tessera_api.main import app

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        actor = _make_user(actor_id)

        with _member_write_auth():
            with (
                patch("tessera_api.routers.members.get_db") as mock_get_db,
                patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
                patch(
                    "tessera_api.routers.members.SqlSpaceMembershipRepository"
                ) as mock_membership_repo_cls,
                patch("tessera_api.routers.members.SqlAuditRepository"),
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_user_repo = AsyncMock()
                mock_user_repo.get_by_id.return_value = actor
                mock_user_repo_cls.return_value = mock_user_repo

                mock_membership_repo = AsyncMock()
                mock_membership_repo.list_by_space.return_value = [
                    _membership(space_id, actor_id, SpaceRole.ADMIN),
                    _membership(space_id, target_id, SpaceRole.ADMIN),
                ]
                mock_membership_repo.count_admins.return_value = 1
                mock_membership_repo_cls.return_value = mock_membership_repo

                with TestClient(app) as client:
                    resp = client.put(
                        f"/v1/spaces/{space_id}/members/{target_id}",
                        json={"role": "viewer"},
                        headers=_make_jwt_header(actor_id),
                    )

        assert resp.status_code == 409


class TestRemoveMemberIntegration:
    def test_admin_can_remove_member(self):
        from fastapi.testclient import TestClient

        from tessera_api.main import app

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        actor = _make_user(actor_id)

        with _member_write_auth():
            with (
                patch("tessera_api.routers.members.get_db") as mock_get_db,
                patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
                patch(
                    "tessera_api.routers.members.SqlSpaceMembershipRepository"
                ) as mock_membership_repo_cls,
                patch("tessera_api.routers.members.SqlAuditRepository") as mock_audit_cls,
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_user_repo = AsyncMock()
                mock_user_repo.get_by_id.return_value = actor
                mock_user_repo_cls.return_value = mock_user_repo

                mock_membership_repo = AsyncMock()
                mock_membership_repo.list_by_space.return_value = [
                    _membership(space_id, actor_id, SpaceRole.ADMIN),
                    _membership(space_id, target_id, SpaceRole.EDITOR),
                ]
                mock_membership_repo.count_admins.return_value = 1
                mock_membership_repo.remove.return_value = None
                mock_membership_repo_cls.return_value = mock_membership_repo

                mock_audit_cls.return_value = AsyncMock()

                with TestClient(app) as client:
                    resp = client.delete(
                        f"/v1/spaces/{space_id}/members/{target_id}",
                        headers=_make_jwt_header(actor_id),
                    )

        assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Feature 065: identity-enriched member list
# ---------------------------------------------------------------------------


def _listing(
    space_id: uuid.UUID,
    user_id: uuid.UUID,
    display_name: str,
    email: str,
    role: SpaceRole,
) -> SpaceMemberListing:
    now = datetime.now(UTC)
    return SpaceMemberListing(
        id=uuid.uuid4(),
        space_id=space_id,
        user_id=user_id,
        display_name=display_name,
        email=email,
        role=role,
        invited_by_user_id=None,
        created_at=now,
        updated_at=now,
    )


@contextmanager
def _member_read_auth():
    """Working HTTP auth context for member reads: overrides the get_db
    dependency (conftest pattern) + company membership resolution + onboarding."""
    from tessera_api.adapters.database import get_db
    from tessera_api.main import app

    now = datetime.now(UTC)

    def _ms(uid, cid):
        return CompanyMembership(
            id=uuid.uuid4(), user_id=uid, company_id=cid, role=CompanyRole.MEMBER, joined_at=now
        )

    mock_session = AsyncMock()

    async def _fake_db():
        yield mock_session

    company_repo = AsyncMock()
    company_repo.get_membership = AsyncMock(side_effect=_ms)
    company_repo.get_by_id = AsyncMock(return_value=None)

    app.dependency_overrides[get_db] = _fake_db
    try:
        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.auth.oidc.SqlCompanyRepository", return_value=company_repo),
        ):
            yield
    finally:
        app.dependency_overrides.pop(get_db, None)


class TestListMembersIdentityIntegration:
    def test_list_returns_identity_fields_in_display_name_order(self):
        from fastapi.testclient import TestClient

        from tessera_api.main import app

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        other_id = uuid.uuid4()
        actor = _make_user(actor_id)

        rows = [
            _listing(space_id, actor_id, "Ada Lovelace", "ada@acme.example", SpaceRole.ADMIN),
            _listing(space_id, other_id, "Grace Hopper", "grace@acme.example", SpaceRole.VIEWER),
        ]

        with (
            _member_read_auth(),
            patch(
                "tessera_api.routers.members.validate_space_for_company",
                new=AsyncMock(return_value=None),
            ),
            patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
            patch(
                "tessera_api.routers.members.SqlSpaceMembershipRepository"
            ) as mock_membership_repo_cls,
        ):
            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_id.return_value = actor
            mock_user_repo_cls.return_value = mock_user_repo

            mock_membership_repo = AsyncMock()
            mock_membership_repo.list_by_space_with_identity.return_value = rows
            mock_membership_repo_cls.return_value = mock_membership_repo

            with TestClient(app) as client:
                resp = client.get(
                    f"/v1/spaces/{space_id}/members",
                    headers=_make_jwt_header(actor_id),
                )

        assert resp.status_code == 200
        members = resp.json()["members"]
        assert len(members) == 2
        for member in members:
            assert member["display_name"]
            assert member["email"]
        assert [m["display_name"] for m in members] == ["Ada Lovelace", "Grace Hopper"]
        # The enriched read is company-scoped with the token's active company.
        mock_membership_repo.list_by_space_with_identity.assert_awaited_once_with(
            space_id, COMPANY_ID
        )

    def test_cross_tenant_list_returns_generic_404_without_identity(self):
        """Company A actor requesting Company B's space: generic 404, no identity leaks."""
        from fastapi.testclient import TestClient

        from tessera_api.main import app

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        space_repo = AsyncMock()
        space_repo.get_by_id_for_company = AsyncMock(return_value=None)

        with (
            _member_read_auth(),
            patch("tessera_api.routers.spaces.SqlSpaceRepository", return_value=space_repo),
            patch(
                "tessera_api.routers.members.SqlSpaceMembershipRepository"
            ) as mock_membership_repo_cls,
        ):
            mock_membership_repo = AsyncMock()
            mock_membership_repo_cls.return_value = mock_membership_repo

            with TestClient(app) as client:
                resp = client.get(
                    f"/v1/spaces/{space_id}/members",
                    headers=_make_jwt_header(actor_id),
                )

        assert resp.status_code == 404
        body = resp.json()
        assert body["error"] == {"code": "not_found", "message": "Not found"}
        assert "members" not in body
        assert "@" not in resp.text  # no email of any member in the body
        mock_membership_repo.list_by_space_with_identity.assert_not_awaited()


# ---------------------------------------------------------------------------
# Feature 065: repository-level tenant scoping (live PostgreSQL)
# ---------------------------------------------------------------------------

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://tessera:tessera@localhost:5432/tessera"
)


def _db_reachable() -> bool:
    try:
        engine = sa.create_engine(DB_URL)
        with engine.connect():
            return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_reachable(), reason="PostgreSQL not reachable — set DATABASE_URL to a live instance"
)


@requires_db
class TestListBySpaceWithIdentityRepository:
    @pytest.mark.anyio
    async def test_returns_identity_rows_ordered_and_scoped_to_company(self):
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from tessera_api.adapters.models.company import CompanyModel
        from tessera_api.adapters.models.space import SpaceModel
        from tessera_api.adapters.models.space_membership import SpaceMembershipModel
        from tessera_api.adapters.models.user import UserModel
        from tessera_api.adapters.repositories.space_membership import (
            SqlSpaceMembershipRepository,
        )

        engine = create_async_engine(DB_URL)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            users = []
            for name in ("Zoe Last", "Abel First"):
                user = UserModel(
                    external_subject=f"sub-{uuid.uuid4()}",
                    email=f"{uuid.uuid4()}@identity.test",
                    display_name=name,
                )
                session.add(user)
                users.append(user)
            await session.flush()

            company_a = CompanyModel(name="Identity Co A", admin_user_id=users[0].id)
            company_b = CompanyModel(name="Identity Co B", admin_user_id=users[0].id)
            session.add_all([company_a, company_b])
            await session.flush()

            space = SpaceModel(
                slug=f"space-{uuid.uuid4()}",
                name="Identity Space",
                sector="eng",
                company_id=company_a.id,
            )
            session.add(space)
            await session.flush()

            for user in users:
                session.add(SpaceMembershipModel(space_id=space.id, user_id=user.id, role="viewer"))
            await session.flush()

            repo = SqlSpaceMembershipRepository(session)

            rows = await repo.list_by_space_with_identity(space.id, company_a.id)
            assert [r.display_name for r in rows] == ["Abel First", "Zoe Last"]
            assert all(r.email.endswith("@identity.test") for r in rows)
            assert all(isinstance(r, SpaceMemberListing) for r in rows)

            # Wrong company: empty even though the space has members.
            assert await repo.list_by_space_with_identity(space.id, company_b.id) == []

            await session.rollback()
        await engine.dispose()
