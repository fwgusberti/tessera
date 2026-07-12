"""Integration tests: company profile view/edit via /v1/companies/current (feature 060).

End-to-end through the FastAPI app with a fake in-memory company store, covering
the four isolation tests from plan.md plus persistence and audit (SC-003/SC-004).
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from tessera_core.domain.entities import Company, CompanyMembership, CompanyRole


def _token(user_id: uuid.UUID, company_id: uuid.UUID, **kwargs) -> str:
    from tessera_api.auth.jwt_auth import create_access_token

    return create_access_token(user_id, "actor@example.com", False, company_id=company_id, **kwargs)


class FakeCompanyStore:
    """In-memory companies keyed by id, mimicking the repository surface the
    profile endpoints touch (get_by_id / update_details / get_membership)."""

    def __init__(self, companies: dict[uuid.UUID, Company], roles: dict[uuid.UUID, CompanyRole]):
        self.companies = dict(companies)
        self._roles = roles  # user_id -> role in any company (simplified)

    def make_repo(self) -> AsyncMock:
        repo = AsyncMock()

        async def get_by_id(company_id):
            return self.companies.get(company_id)

        async def update_details(company_id, *, name, industry, team_size):
            current = self.companies.get(company_id)
            if current is None:
                return None
            updated = current.model_copy(
                update={
                    "name": name,
                    "industry": industry,
                    "team_size": team_size,
                    "updated_at": datetime.now(UTC),
                }
            )
            self.companies[company_id] = updated
            return updated

        async def get_membership(user_id, company_id):
            role = self._roles.get(user_id)
            if role is None:
                return None
            return CompanyMembership(
                id=uuid.uuid4(),
                user_id=user_id,
                company_id=company_id,
                role=role,
                joined_at=datetime.now(UTC),
            )

        repo.get_by_id = AsyncMock(side_effect=get_by_id)
        repo.update_details = AsyncMock(side_effect=update_details)
        repo.get_membership = AsyncMock(side_effect=get_membership)
        return repo


@contextmanager
def _app_with_store(store: FakeCompanyStore):
    """Wire the fake store into both the auth layer and the companies router."""
    from tessera_api.adapters.database import get_db
    from tessera_api.auth.bearer import require_onboarding_complete
    from tessera_api.main import app

    mock_session = AsyncMock()

    async def _fake_db():
        yield mock_session

    async def _noop():
        return None

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[require_onboarding_complete] = _noop
    try:
        with (
            patch(
                "tessera_api.auth.oidc.SqlCompanyRepository",
                side_effect=lambda s: store.make_repo(),
            ),
            patch(
                "tessera_api.routers.companies.SqlCompanyRepository",
                side_effect=lambda s: store.make_repo(),
            ),
        ):
            yield
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_onboarding_complete, None)


def _seed_two_companies():
    admin_a = uuid.uuid4()
    member_a = uuid.uuid4()
    admin_b = uuid.uuid4()
    company_a_id = uuid.uuid4()
    company_b_id = uuid.uuid4()

    company_a = Company(
        id=company_a_id,
        name="Alpha Inc",
        industry="Technology",
        team_size="11-50",
        admin_user_id=admin_a,
        created_at=datetime(2026, 1, 5, tzinfo=UTC),
        updated_at=datetime(2026, 1, 5, tzinfo=UTC),
    )
    company_b = Company(
        id=company_b_id,
        name="Beta LLC",
        industry="Finance",
        team_size="1-10",
        admin_user_id=admin_b,
        created_at=datetime(2026, 2, 6, tzinfo=UTC),
        updated_at=datetime(2026, 2, 6, tzinfo=UTC),
    )

    store = FakeCompanyStore(
        companies={company_a_id: company_a, company_b_id: company_b},
        roles={
            admin_a: CompanyRole.ADMIN,
            member_a: CompanyRole.MEMBER,
            admin_b: CompanyRole.ADMIN,
        },
    )
    return store, admin_a, member_a, company_a_id, company_b_id


class TestGetCurrentCompanyIntegration:
    def test_member_get_returns_only_the_tokens_company(self):
        """Isolation test 1: the response is the token's company, never another's."""
        store, _admin_a, member_a, company_a_id, company_b_id = _seed_two_companies()
        from tessera_api.main import app

        with _app_with_store(store), TestClient(app) as client:
            response = client.get(
                "/v1/companies/current",
                headers={"Authorization": f"Bearer {_token(member_a, company_a_id)}"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(company_a_id)
        assert body["name"] == "Alpha Inc"
        assert body["role"] == "member"
        assert body["id"] != str(company_b_id)

    def test_revoked_membership_token_forbidden(self):
        """Isolation test 2: a token whose membership was revoked → 403 not_a_member."""
        store, _admin_a, _member_a, company_a_id, _company_b_id = _seed_two_companies()
        revoked_user = uuid.uuid4()  # not in the roles map → membership resolves to None
        from tessera_api.main import app

        with _app_with_store(store), TestClient(app) as client:
            response = client.get(
                "/v1/companies/current",
                headers={"Authorization": f"Bearer {_token(revoked_user, company_a_id)}"},
            )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "not_a_member"

    def test_unauthenticated_request_unauthorized(self):
        """FR-011: no token → 401."""
        store, *_ = _seed_two_companies()
        from tessera_api.main import app

        with _app_with_store(store), TestClient(app) as client:
            response = client.get("/v1/companies/current")

        assert response.status_code == 401

    def test_company_unscoped_token_forbidden(self):
        """A select-kind (unscoped) token → 403 credential_not_scoped."""
        store, admin_a, _member_a, _company_a_id, _company_b_id = _seed_two_companies()
        from tessera_api.auth.jwt_auth import create_access_token
        from tessera_api.main import app

        select_token = create_access_token(admin_a, "actor@example.com", False, token_kind="select")

        with _app_with_store(store), TestClient(app) as client:
            response = client.get(
                "/v1/companies/current",
                headers={"Authorization": f"Bearer {select_token}"},
            )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "credential_not_scoped"


class TestPatchCurrentCompanyIntegration:
    def test_admin_patch_persists_across_fresh_get(self):
        """US2 scenario 1: the saved profile is returned and visible on a fresh GET."""
        store, admin_a, _member_a, company_a_id, _company_b_id = _seed_two_companies()
        from tessera_api.main import app

        headers = {"Authorization": f"Bearer {_token(admin_a, company_a_id)}"}
        with (
            _app_with_store(store),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
            TestClient(app) as client,
        ):
            patch_response = client.patch(
                "/v1/companies/current",
                headers=headers,
                json={"name": "Alpha Corporation", "industry": None, "team_size": "51-200"},
            )
            get_response = client.get("/v1/companies/current", headers=headers)

        assert patch_response.status_code == 200
        assert patch_response.json()["name"] == "Alpha Corporation"
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["name"] == "Alpha Corporation"
        assert body["industry"] is None
        assert body["team_size"] == "51-200"

    def test_audit_record_written_with_actor_company_and_changed_fields(self):
        """SC-004: one company.updated audit row with actor, company, changed map."""
        store, admin_a, _member_a, company_a_id, _company_b_id = _seed_two_companies()
        from tessera_api.main import app

        with (
            _app_with_store(store),
            patch(
                "tessera_api.routers.companies.write_audit", new_callable=AsyncMock
            ) as mock_audit,
            TestClient(app) as client,
        ):
            response = client.patch(
                "/v1/companies/current",
                headers={"Authorization": f"Bearer {_token(admin_a, company_a_id)}"},
                json={"name": "Alpha Renamed", "industry": "Technology", "team_size": "11-50"},
            )

        assert response.status_code == 200
        mock_audit.assert_awaited_once()
        kwargs = mock_audit.await_args.kwargs
        assert kwargs["action"] == "company.updated"
        assert kwargs["actor_id"] == admin_a
        assert kwargs["entity_id"] == company_a_id
        assert kwargs["metadata"]["company_id"] == str(company_a_id)
        assert kwargs["metadata"]["changed"] == {
            "name": {"from": "Alpha Inc", "to": "Alpha Renamed"}
        }

    def test_update_by_company_a_admin_leaves_company_b_untouched(self):
        """Isolation test 4: two companies seeded; A's update never touches B."""
        store, admin_a, _member_a, company_a_id, company_b_id = _seed_two_companies()
        before_b = store.companies[company_b_id]
        from tessera_api.main import app

        with (
            _app_with_store(store),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
            TestClient(app) as client,
        ):
            response = client.patch(
                "/v1/companies/current",
                headers={"Authorization": f"Bearer {_token(admin_a, company_a_id)}"},
                json={"name": "Alpha Only", "industry": None, "team_size": None},
            )

        assert response.status_code == 200
        after_b = store.companies[company_b_id]
        assert after_b == before_b
        assert after_b.name == "Beta LLC"

    def test_member_patch_forbidden_and_data_unchanged(self):
        """Isolation test 3 / SC-003: member PATCH → 403 forbidden; GET proves no change."""
        store, _admin_a, member_a, company_a_id, _company_b_id = _seed_two_companies()
        from tessera_api.main import app

        headers = {"Authorization": f"Bearer {_token(member_a, company_a_id)}"}
        with _app_with_store(store), TestClient(app) as client:
            patch_response = client.patch(
                "/v1/companies/current",
                headers=headers,
                json={"name": "Hacked", "industry": None, "team_size": None},
            )
            get_response = client.get("/v1/companies/current", headers=headers)

        assert patch_response.status_code == 403
        assert patch_response.json()["error"]["code"] == "forbidden"
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["name"] == "Alpha Inc"
        assert body["industry"] == "Technology"
        assert body["team_size"] == "11-50"
