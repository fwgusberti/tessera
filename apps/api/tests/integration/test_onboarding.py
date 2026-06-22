"""Integration tests for onboarding endpoints.

Tests use TestClient with mocked repositories (no real DB required).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch


def _make_jwt_header(user_id: uuid.UUID | None = None) -> dict:
    from tessera_api.auth.jwt_auth import create_access_token

    uid = user_id or uuid.uuid4()
    token = create_access_token(uid, "user@example.com", False)
    return {"Authorization": f"Bearer {token}"}


def _make_progress(user_id: uuid.UUID | None = None, **kwargs):
    from tessera_core.domain.entities import OnboardingProgress

    uid = user_id or uuid.uuid4()
    defaults = dict(
        id=uuid.uuid4(),
        user_id=uid,
        completed_steps=[],
        current_step="profile",
        company_join_method=None,
        completed_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return OnboardingProgress(**defaults)


class TestGetOnboardingStatus:
    def test_returns_status_for_new_user(self):
        """GET /v1/onboarding/status returns initial state for a new user."""
        user_id = uuid.uuid4()
        progress = _make_progress(user_id=user_id)

        with (
            patch("tessera_api.routers.onboarding.get_db") as mock_get_db,
            patch("tessera_api.routers.onboarding.SqlOnboardingRepository") as mock_repo_cls,
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_repo = AsyncMock()
            mock_repo.get_by_user_id = AsyncMock(return_value=progress)
            mock_repo_cls.return_value = mock_repo

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.get(
                    "/v1/onboarding/status",
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 200
        body = response.json()
        assert body["completed"] is False
        assert body["current_step"] == "profile"
        assert body["completed_steps"] == []
        assert body["company_join_method"] is None

    def test_returns_completed_true_when_finished(self):
        """Returns completed=true when completed_at is set."""
        user_id = uuid.uuid4()
        progress = _make_progress(
            user_id=user_id,
            completed_steps=["profile", "company", "invite"],
            current_step="complete",
            company_join_method="created",
            completed_at=datetime.now(UTC),
        )

        with (
            patch("tessera_api.routers.onboarding.get_db") as mock_get_db,
            patch("tessera_api.routers.onboarding.SqlOnboardingRepository") as mock_repo_cls,
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_repo = AsyncMock()
            mock_repo.get_by_user_id = AsyncMock(return_value=progress)
            mock_repo_cls.return_value = mock_repo

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.get(
                    "/v1/onboarding/status",
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 200
        body = response.json()
        assert body["completed"] is True
        assert body["company_join_method"] == "created"

    def test_creates_progress_when_missing(self):
        """If no onboarding record exists, creates one and returns initial state."""
        user_id = uuid.uuid4()
        progress = _make_progress(user_id=user_id)

        with (
            patch("tessera_api.routers.onboarding.get_db") as mock_get_db,
            patch("tessera_api.routers.onboarding.SqlOnboardingRepository") as mock_repo_cls,
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_repo = AsyncMock()
            mock_repo.get_by_user_id = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=progress)
            mock_repo_cls.return_value = mock_repo

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.get(
                    "/v1/onboarding/status",
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 200
        mock_repo.create.assert_awaited_once()

    def test_requires_authentication(self):
        """Unauthenticated request returns 401."""
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.get("/v1/onboarding/status")
        assert response.status_code == 401


class TestPostOnboardingProfile:
    def test_saves_profile_advances_step(self):
        """POST /v1/onboarding/profile saves name/title and advances to company step."""
        user_id = uuid.uuid4()
        after_progress = _make_progress(
            user_id=user_id,
            completed_steps=["profile"],
            current_step="company",
        )

        with (
            patch("tessera_api.routers.onboarding.get_db") as mock_get_db,
            patch("tessera_api.routers.onboarding.SqlOnboardingRepository") as mock_ob_cls,
            patch("tessera_api.routers.onboarding.SqlUserRepository") as mock_user_cls,
            patch("tessera_api.routers.onboarding.write_audit", new_callable=AsyncMock),
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_ob = AsyncMock()
            mock_ob.get_by_user_id = AsyncMock(return_value=_make_progress(user_id=user_id))
            mock_ob.advance_step = AsyncMock(return_value=after_progress)
            mock_ob_cls.return_value = mock_ob

            mock_user = AsyncMock()
            mock_user.get_by_id = AsyncMock(return_value=MagicMock(id=user_id))
            mock_user_cls.return_value = mock_user

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/onboarding/profile",
                    json={"full_name": "Ana Souza", "title": "Head of Engineering"},
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 200
        body = response.json()
        assert body["current_step"] == "company"
        assert "profile" in body["completed_steps"]

    def test_full_name_required(self):
        """full_name is required — missing returns 422."""
        user_id = uuid.uuid4()

        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.post(
                "/v1/onboarding/profile",
                json={"title": "Only title, no name"},
                headers=_make_jwt_header(user_id),
            )
        assert response.status_code == 422

    def test_title_is_optional(self):
        """title is optional — omitting it should succeed."""
        user_id = uuid.uuid4()
        after_progress = _make_progress(
            user_id=user_id,
            completed_steps=["profile"],
            current_step="company",
        )

        with (
            patch("tessera_api.routers.onboarding.get_db") as mock_get_db,
            patch("tessera_api.routers.onboarding.SqlOnboardingRepository") as mock_ob_cls,
            patch("tessera_api.routers.onboarding.SqlUserRepository") as mock_user_cls,
            patch("tessera_api.routers.onboarding.write_audit", new_callable=AsyncMock),
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_ob = AsyncMock()
            mock_ob.get_by_user_id = AsyncMock(return_value=_make_progress(user_id=user_id))
            mock_ob.advance_step = AsyncMock(return_value=after_progress)
            mock_ob_cls.return_value = mock_ob

            mock_user = AsyncMock()
            mock_user.get_by_id = AsyncMock(return_value=MagicMock(id=user_id))
            mock_user_cls.return_value = mock_user

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/onboarding/profile",
                    json={"full_name": "Ana Souza"},
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 200


class TestPostOnboardingComplete:
    def test_marks_onboarding_complete(self):
        """POST /v1/onboarding/complete sets completed=true and returns completed_at."""
        user_id = uuid.uuid4()
        now = datetime.now(UTC)
        completed_progress = _make_progress(
            user_id=user_id,
            completed_steps=["profile", "company"],
            current_step="complete",
            company_join_method="created",
            completed_at=now,
        )

        with (
            patch("tessera_api.routers.onboarding.get_db") as mock_get_db,
            patch("tessera_api.routers.onboarding.SqlOnboardingRepository") as mock_ob_cls,
            patch("tessera_api.routers.onboarding.SqlUserRepository") as mock_user_cls,
            patch("tessera_api.routers.onboarding.write_audit", new_callable=AsyncMock),
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_ob = AsyncMock()
            mock_ob.complete = AsyncMock(return_value=completed_progress)
            mock_ob_cls.return_value = mock_ob

            mock_user = AsyncMock()
            mock_user.get_by_id = AsyncMock(return_value=MagicMock(id=user_id))
            mock_user_cls.return_value = mock_user

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/onboarding/complete",
                    json={},
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 200
        body = response.json()
        assert body["completed"] is True
        assert "completed_at" in body

    def test_requires_authentication(self):
        """Unauthenticated request returns 401."""
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.post("/v1/onboarding/complete", json={})
        assert response.status_code == 401

    def test_complete_assigns_admin_for_creator(self):
        """POST /onboarding/complete idempotently assigns ADMIN role for a company creator."""
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)
        completed_progress = _make_progress(
            user_id=user_id,
            completed_steps=["profile", "company", "invite"],
            current_step="complete",
            company_join_method="created",
            company_id=company_id,
            completed_at=now,
        )

        with (
            patch("tessera_api.routers.onboarding.get_db") as mock_get_db,
            patch("tessera_api.routers.onboarding.SqlOnboardingRepository") as mock_ob_cls,
            patch("tessera_api.routers.onboarding.SqlCompanyRepository") as mock_co_cls,
            patch("tessera_api.routers.onboarding.SqlUserRepository") as mock_user_cls,
            patch("tessera_api.routers.onboarding.write_audit", new_callable=AsyncMock),
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_ob = AsyncMock()
            mock_ob.complete = AsyncMock(return_value=completed_progress)
            mock_ob_cls.return_value = mock_ob

            mock_co = AsyncMock()
            mock_co.get_membership = AsyncMock(return_value=None)
            mock_co.add_membership = AsyncMock()
            mock_co_cls.return_value = mock_co

            mock_user = AsyncMock()
            mock_user_cls.return_value = mock_user

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/onboarding/complete",
                    json={},
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 200
        mock_co.get_membership.assert_awaited_once_with(user_id, company_id)
        mock_co.add_membership.assert_awaited_once()

    def test_complete_idempotent_admin_already_exists(self):
        """POST /onboarding/complete does NOT create a duplicate if ADMIN membership already exists."""
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)
        completed_progress = _make_progress(
            user_id=user_id,
            completed_steps=["profile", "company", "invite"],
            current_step="complete",
            company_join_method="created",
            company_id=company_id,
            completed_at=now,
        )
        from tessera_core.domain.entities import CompanyMembership, CompanyRole
        existing_membership = CompanyMembership(
            user_id=user_id, company_id=company_id, role=CompanyRole.ADMIN
        )

        with (
            patch("tessera_api.routers.onboarding.get_db") as mock_get_db,
            patch("tessera_api.routers.onboarding.SqlOnboardingRepository") as mock_ob_cls,
            patch("tessera_api.routers.onboarding.SqlCompanyRepository") as mock_co_cls,
            patch("tessera_api.routers.onboarding.SqlUserRepository") as mock_user_cls,
            patch("tessera_api.routers.onboarding.write_audit", new_callable=AsyncMock),
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_ob = AsyncMock()
            mock_ob.complete = AsyncMock(return_value=completed_progress)
            mock_ob_cls.return_value = mock_ob

            mock_co = AsyncMock()
            mock_co.get_membership = AsyncMock(return_value=existing_membership)
            mock_co.add_membership = AsyncMock()
            mock_co_cls.return_value = mock_co

            mock_user = AsyncMock()
            mock_user_cls.return_value = mock_user

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/onboarding/complete",
                    json={},
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 200
        mock_co.add_membership.assert_not_awaited()

    def test_complete_does_not_assign_admin_for_joiner(self):
        """POST /onboarding/complete does NOT assign admin when user joined (not created)."""
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)
        completed_progress = _make_progress(
            user_id=user_id,
            completed_steps=["profile", "company", "invite"],
            current_step="complete",
            company_join_method="joined",
            company_id=company_id,
            completed_at=now,
        )

        with (
            patch("tessera_api.routers.onboarding.get_db") as mock_get_db,
            patch("tessera_api.routers.onboarding.SqlOnboardingRepository") as mock_ob_cls,
            patch("tessera_api.routers.onboarding.SqlCompanyRepository") as mock_co_cls,
            patch("tessera_api.routers.onboarding.SqlUserRepository") as mock_user_cls,
            patch("tessera_api.routers.onboarding.write_audit", new_callable=AsyncMock),
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_ob = AsyncMock()
            mock_ob.complete = AsyncMock(return_value=completed_progress)
            mock_ob_cls.return_value = mock_ob

            mock_co = AsyncMock()
            mock_co.get_membership = AsyncMock(return_value=None)
            mock_co.add_membership = AsyncMock()
            mock_co_cls.return_value = mock_co

            mock_user = AsyncMock()
            mock_user_cls.return_value = mock_user

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/onboarding/complete",
                    json={},
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 200
        mock_co.get_membership.assert_not_awaited()
        mock_co.add_membership.assert_not_awaited()

    def test_complete_no_company_join_method_safe(self):
        """POST /onboarding/complete is safe when company_join_method and company_id are None."""
        user_id = uuid.uuid4()
        now = datetime.now(UTC)
        completed_progress = _make_progress(
            user_id=user_id,
            completed_steps=["profile"],
            current_step="complete",
            company_join_method=None,
            company_id=None,
            completed_at=now,
        )

        with (
            patch("tessera_api.routers.onboarding.get_db") as mock_get_db,
            patch("tessera_api.routers.onboarding.SqlOnboardingRepository") as mock_ob_cls,
            patch("tessera_api.routers.onboarding.SqlCompanyRepository") as mock_co_cls,
            patch("tessera_api.routers.onboarding.SqlUserRepository") as mock_user_cls,
            patch("tessera_api.routers.onboarding.write_audit", new_callable=AsyncMock),
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_ob = AsyncMock()
            mock_ob.complete = AsyncMock(return_value=completed_progress)
            mock_ob_cls.return_value = mock_ob

            mock_co = AsyncMock()
            mock_co_cls.return_value = mock_co

            mock_user = AsyncMock()
            mock_user_cls.return_value = mock_user

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/onboarding/complete",
                    json={},
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 200
        mock_co.get_membership.assert_not_awaited()
        mock_co.add_membership.assert_not_awaited()

    def test_complete_does_not_assign_admin_on_other_company(self):
        """Cross-tenant isolation: /onboarding/complete only targets progress.company_id (server-set).

        A user whose onboarding progress records company_a_id cannot trigger
        admin assignment on company_b_id — even if another company exists.
        """
        user_id = uuid.uuid4()
        company_a_id = uuid.uuid4()
        company_b_id = uuid.uuid4()
        now = datetime.now(UTC)
        completed_progress = _make_progress(
            user_id=user_id,
            completed_steps=["profile", "company", "invite"],
            current_step="complete",
            company_join_method="created",
            company_id=company_a_id,
            completed_at=now,
        )

        with (
            patch("tessera_api.routers.onboarding.get_db") as mock_get_db,
            patch("tessera_api.routers.onboarding.SqlOnboardingRepository") as mock_ob_cls,
            patch("tessera_api.routers.onboarding.SqlCompanyRepository") as mock_co_cls,
            patch("tessera_api.routers.onboarding.SqlUserRepository") as mock_user_cls,
            patch("tessera_api.routers.onboarding.write_audit", new_callable=AsyncMock),
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_ob = AsyncMock()
            mock_ob.complete = AsyncMock(return_value=completed_progress)
            mock_ob_cls.return_value = mock_ob

            mock_co = AsyncMock()
            mock_co.get_membership = AsyncMock(return_value=None)
            mock_co.add_membership = AsyncMock()
            mock_co_cls.return_value = mock_co

            mock_user = AsyncMock()
            mock_user_cls.return_value = mock_user

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/onboarding/complete",
                    json={},
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 200
        mock_co.get_membership.assert_awaited_once_with(user_id, company_a_id)
        for call in mock_co.get_membership.await_args_list:
            assert call.args[1] != company_b_id, (
                f"get_membership was called with company_b_id={company_b_id} — cross-tenant leak"
            )
        for call in mock_co.add_membership.await_args_list:
            membership_arg = call.args[0]
            assert membership_arg.company_id != company_b_id, (
                f"add_membership was called for company_b_id={company_b_id} — cross-tenant write"
            )
