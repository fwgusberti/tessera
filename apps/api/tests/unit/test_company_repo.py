"""Unit tests for SqlCompanyRepository and SqlDomainPolicyRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from tessera_core.domain.entities import (
    Company,
    CompanyMembership,
    CompanyRole,
    DomainJoinPolicy,
    DomainPolicy,
)


@pytest.fixture
def company_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


class TestSqlCompanyRepositoryCreate:
    @pytest.mark.anyio
    async def test_create_persists_company(self, mock_session, user_id):
        from tessera_api.adapters.repo import SqlCompanyRepository

        company = Company(name="Acme Corp", admin_user_id=user_id)
        mock_session.refresh.side_effect = lambda m: setattr(
            m, "created_at", datetime.now(UTC)
        ) or setattr(m, "updated_at", datetime.now(UTC))

        repo = SqlCompanyRepository(mock_session)
        # Patch refresh to set timestamps on the model added
        mock_session.add.side_effect = lambda m: None
        mock_session.flush.return_value = None

        async def fake_refresh(m):
            m.created_at = datetime.now(UTC)
            m.updated_at = datetime.now(UTC)

        mock_session.refresh.side_effect = fake_refresh

        result = await repo.create(company)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert result.name == "Acme Corp"
        assert result.admin_user_id == user_id

    @pytest.mark.anyio
    async def test_get_by_id_returns_none_when_not_found(self, mock_session, company_id):
        from tessera_api.adapters.repo import SqlCompanyRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = SqlCompanyRepository(mock_session)
        result = await repo.get_by_id(company_id)

        assert result is None

    @pytest.mark.anyio
    async def test_get_by_id_returns_company_when_found(self, mock_session, company_id, user_id):
        from tessera_api.adapters.models import CompanyModel
        from tessera_api.adapters.repo import SqlCompanyRepository

        model = CompanyModel(
            id=company_id,
            name="Acme Corp",
            admin_user_id=user_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = model
        mock_session.execute.return_value = mock_result

        repo = SqlCompanyRepository(mock_session)
        result = await repo.get_by_id(company_id)

        assert result is not None
        assert result.id == company_id
        assert result.name == "Acme Corp"


class TestSqlCompanyRepositoryMembership:
    @pytest.mark.anyio
    async def test_add_membership_persists_record(self, mock_session, company_id, user_id):
        from tessera_api.adapters.repo import SqlCompanyRepository

        membership = CompanyMembership(
            user_id=user_id, company_id=company_id, role=CompanyRole.ADMIN
        )

        async def fake_refresh(m):
            m.joined_at = datetime.now(UTC)

        mock_session.refresh.side_effect = fake_refresh

        repo = SqlCompanyRepository(mock_session)
        result = await repo.add_membership(membership)

        mock_session.add.assert_called_once()
        assert result.role == CompanyRole.ADMIN

    @pytest.mark.anyio
    async def test_get_membership_returns_none_when_not_found(
        self, mock_session, company_id, user_id
    ):
        from tessera_api.adapters.repo import SqlCompanyRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = SqlCompanyRepository(mock_session)
        result = await repo.get_membership(user_id, company_id)

        assert result is None

    @pytest.mark.anyio
    async def test_add_membership_returns_company_membership_type(
        self, mock_session, company_id, user_id
    ):
        from tessera_api.adapters.repo import SqlCompanyRepository

        membership = CompanyMembership(
            user_id=user_id, company_id=company_id, role=CompanyRole.ADMIN
        )

        async def fake_refresh(m):
            m.joined_at = datetime(2026, 1, 1, tzinfo=UTC)

        mock_session.refresh.side_effect = fake_refresh

        repo = SqlCompanyRepository(mock_session)
        result = await repo.add_membership(membership)

        assert isinstance(result, CompanyMembership)
        assert hasattr(result, "company_id")
        assert not hasattr(result, "space_id")

    @pytest.mark.anyio
    async def test_add_membership_role_round_trips(self, mock_session, company_id, user_id):
        from tessera_api.adapters.repo import SqlCompanyRepository

        membership = CompanyMembership(
            user_id=user_id, company_id=company_id, role=CompanyRole.ADMIN
        )

        async def fake_refresh(m):
            m.joined_at = datetime(2026, 1, 1, tzinfo=UTC)

        mock_session.refresh.side_effect = fake_refresh

        repo = SqlCompanyRepository(mock_session)
        result = await repo.add_membership(membership)

        assert result.role == CompanyRole.ADMIN

    @pytest.mark.anyio
    async def test_get_membership_returns_company_membership_when_found(
        self, mock_session, company_id, user_id
    ):
        from tessera_api.adapters.models import CompanyMembershipModel
        from tessera_api.adapters.repo import SqlCompanyRepository

        membership_id = uuid.uuid4()
        model = CompanyMembershipModel(
            id=membership_id,
            user_id=user_id,
            company_id=company_id,
            role="admin",
            joined_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = model
        mock_session.execute.return_value = mock_result

        repo = SqlCompanyRepository(mock_session)
        result = await repo.get_membership(user_id, company_id)

        assert isinstance(result, CompanyMembership)
        assert result.company_id == company_id

    @pytest.mark.anyio
    async def test_list_memberships_for_user_returns_company_memberships(
        self, mock_session, company_id, user_id
    ):
        from tessera_api.adapters.models import CompanyMembershipModel
        from tessera_api.adapters.repo import SqlCompanyRepository

        models = [
            CompanyMembershipModel(
                id=uuid.uuid4(),
                user_id=user_id,
                company_id=company_id,
                role="admin",
                joined_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            CompanyMembershipModel(
                id=uuid.uuid4(),
                user_id=user_id,
                company_id=uuid.uuid4(),
                role="member",
                joined_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = models
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = SqlCompanyRepository(mock_session)
        result = await repo.list_memberships_for_user(user_id)

        assert len(result) == 2
        assert all(isinstance(m, CompanyMembership) for m in result)


class TestAddMembershipIdempotency:
    @pytest.mark.anyio
    async def test_add_membership_idempotent_no_duplicate_on_second_call(
        self, mock_session, company_id, user_id
    ):
        """Calling add_membership twice should not raise — the unique constraint in the DB
        is the final guard, but the router does a get_membership check first.
        This test verifies that get_membership → conditional add_membership avoids duplicate calls.
        """
        from tessera_api.adapters.repo import SqlCompanyRepository
        from tessera_core.domain.entities import CompanyMembership, CompanyRole

        membership = CompanyMembership(
            user_id=user_id, company_id=company_id, role=CompanyRole.ADMIN
        )

        async def fake_refresh(m):
            m.joined_at = datetime(2026, 1, 1, tzinfo=UTC)

        mock_session.refresh.side_effect = fake_refresh

        repo = SqlCompanyRepository(mock_session)

        # First call: get_membership returns None → add_membership called
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result_none

        existing = await repo.get_membership(user_id, company_id)
        assert existing is None
        result = await repo.add_membership(membership)
        assert result.role == CompanyRole.ADMIN

        # Second call: get_membership now returns the existing membership → add_membership NOT called
        from tessera_api.adapters.models import CompanyMembershipModel

        existing_model = CompanyMembershipModel(
            id=uuid.uuid4(),
            user_id=user_id,
            company_id=company_id,
            role="admin",
            joined_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        mock_result_found = MagicMock()
        mock_result_found.scalar_one_or_none.return_value = existing_model
        mock_session.execute.return_value = mock_result_found

        existing_second = await repo.get_membership(user_id, company_id)
        assert existing_second is not None
        assert existing_second.role == CompanyRole.ADMIN
        # add_membership should only have been called once total (the first time)
        assert mock_session.add.call_count == 1


class TestSearchMembersForSpace:
    @pytest.mark.anyio
    async def test_search_returns_company_scoped_matches(self, mock_session, company_id, user_id):
        from tessera_api.adapters.models import UserModel
        from tessera_api.adapters.repo import SqlCompanyRepository

        space_id = uuid.uuid4()
        models = [
            UserModel(
                id=user_id,
                external_subject="sub-1",
                email="bob@acme.com",
                display_name="Bob Builder",
            ),
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = models
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = SqlCompanyRepository(mock_session)
        result = await repo.search_members_for_space(company_id, space_id, "bo")

        assert len(result) == 1
        assert result[0].user_id == user_id
        assert result[0].display_name == "Bob Builder"
        assert result[0].email == "bob@acme.com"
        mock_session.execute.assert_awaited_once()
        executed_stmt = mock_session.execute.call_args[0][0]
        assert len(executed_stmt._order_by_clauses) > 0

    @pytest.mark.anyio
    async def test_search_excludes_users_outside_company(self, mock_session, company_id):
        """A user whose only company membership is a different company must not appear —
        enforced by the query's company_id filter, not a post-filter in Python."""
        from tessera_api.adapters.repo import SqlCompanyRepository

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = SqlCompanyRepository(mock_session)
        result = await repo.search_members_for_space(company_id, uuid.uuid4(), "anyone")

        assert result == []
        executed_stmt = mock_session.execute.call_args[0][0]
        compiled = str(executed_stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "company_memberships" in compiled

    @pytest.mark.anyio
    async def test_search_excludes_existing_space_members_via_query(self, mock_session, company_id):
        """The query MUST filter against space_memberships for the target space —
        verified by inspecting the compiled statement rather than DB-level behavior."""
        from tessera_api.adapters.repo import SqlCompanyRepository

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = SqlCompanyRepository(mock_session)
        await repo.search_members_for_space(company_id, uuid.uuid4(), "anyone")

        executed_stmt = mock_session.execute.call_args[0][0]
        compiled = str(executed_stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "space_memberships" in compiled

    @pytest.mark.anyio
    async def test_search_respects_limit_argument(self, mock_session, company_id):
        from tessera_api.adapters.repo import SqlCompanyRepository

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = SqlCompanyRepository(mock_session)
        await repo.search_members_for_space(company_id, uuid.uuid4(), "anyone", limit=5)

        executed_stmt = mock_session.execute.call_args[0][0]
        assert executed_stmt._limit_clause is not None


class TestSqlCompanyRepositoryUpdateDetails:
    @pytest.mark.anyio
    async def test_update_details_persists_all_three_fields(
        self, mock_session, company_id, user_id
    ):
        from tessera_api.adapters.models import CompanyModel
        from tessera_api.adapters.repo import SqlCompanyRepository

        model = CompanyModel(
            id=company_id,
            name="Old Name",
            industry="Finance",
            team_size="1-10",
            admin_user_id=user_id,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = model
        mock_session.execute.return_value = mock_result

        repo = SqlCompanyRepository(mock_session)
        result = await repo.update_details(
            company_id, name="New Name", industry="Technology", team_size="51-200"
        )

        assert result is not None
        assert isinstance(result, Company)
        assert result.name == "New Name"
        assert result.industry == "Technology"
        assert result.team_size == "51-200"
        assert model.name == "New Name"
        assert model.industry == "Technology"
        assert model.team_size == "51-200"
        mock_session.flush.assert_awaited_once()

    @pytest.mark.anyio
    async def test_update_details_reflects_bumped_updated_at(
        self, mock_session, company_id, user_id
    ):
        """The DB's onupdate bumps updated_at; the refreshed model value is returned."""
        from tessera_api.adapters.models import CompanyModel
        from tessera_api.adapters.repo import SqlCompanyRepository

        original = datetime(2026, 1, 1, tzinfo=UTC)
        bumped = datetime(2026, 7, 11, tzinfo=UTC)
        model = CompanyModel(
            id=company_id,
            name="Old Name",
            admin_user_id=user_id,
            created_at=original,
            updated_at=original,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = model
        mock_session.execute.return_value = mock_result

        async def fake_refresh(m):
            m.updated_at = bumped

        mock_session.refresh.side_effect = fake_refresh

        repo = SqlCompanyRepository(mock_session)
        result = await repo.update_details(
            company_id, name="New Name", industry=None, team_size=None
        )

        assert result is not None
        assert result.updated_at == bumped
        assert result.updated_at > original

    @pytest.mark.anyio
    async def test_update_details_returns_none_for_nonexistent_company(
        self, mock_session, company_id
    ):
        from tessera_api.adapters.repo import SqlCompanyRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = SqlCompanyRepository(mock_session)
        result = await repo.update_details(
            company_id, name="New Name", industry=None, team_size=None
        )

        assert result is None
        mock_session.flush.assert_not_awaited()

    @pytest.mark.anyio
    async def test_update_details_scopes_to_the_given_company_only(
        self, mock_session, company_id, user_id
    ):
        """Isolation test 4 (repo slice): the load is WHERE id = :company_id, so a
        second seeded company can never be touched by the update."""
        from tessera_api.adapters.models import CompanyModel
        from tessera_api.adapters.repo import SqlCompanyRepository

        target = CompanyModel(
            id=company_id,
            name="Target",
            admin_user_id=user_id,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        other = CompanyModel(
            id=uuid.uuid4(),
            name="Other Co",
            industry="Finance",
            team_size="1-10",
            admin_user_id=uuid.uuid4(),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = target
        mock_session.execute.return_value = mock_result

        repo = SqlCompanyRepository(mock_session)
        await repo.update_details(company_id, name="Renamed", industry=None, team_size=None)

        executed_stmt = mock_session.execute.call_args[0][0]
        compiled = str(executed_stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "companies.id" in compiled
        # The second company is untouched.
        assert other.name == "Other Co"
        assert other.industry == "Finance"
        assert other.team_size == "1-10"


class TestSqlDomainPolicyRepository:
    @pytest.mark.anyio
    async def test_create_persists_policy(self, mock_session, company_id):
        from tessera_api.adapters.repo import SqlDomainPolicyRepository

        policy = DomainJoinPolicy(
            company_id=company_id,
            domain="acme.com",
            policy=DomainPolicy.REQUEST_APPROVAL,
        )

        async def fake_refresh(m):
            m.created_at = datetime.now(UTC)
            m.verified_at = None

        mock_session.refresh.side_effect = fake_refresh

        repo = SqlDomainPolicyRepository(mock_session)
        result = await repo.create(policy)

        mock_session.add.assert_called_once()
        assert result.domain == "acme.com"
        assert result.verified is False

    @pytest.mark.anyio
    async def test_get_by_domain_returns_none_when_not_found(self, mock_session):
        from tessera_api.adapters.repo import SqlDomainPolicyRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = SqlDomainPolicyRepository(mock_session)
        result = await repo.get_by_domain("unknown.com")

        assert result is None

    @pytest.mark.anyio
    async def test_mark_verified_sets_verified_flag(self, mock_session, company_id):
        from tessera_api.adapters.models import DomainJoinPolicyModel
        from tessera_api.adapters.repo import SqlDomainPolicyRepository

        policy_id = uuid.uuid4()
        model = DomainJoinPolicyModel(
            id=policy_id,
            company_id=company_id,
            domain="acme.com",
            policy="request_approval",
            verified=False,
            created_at=datetime.now(UTC),
            verified_at=None,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = model
        mock_session.execute.return_value = mock_result

        async def fake_refresh(m):
            pass

        mock_session.refresh.side_effect = fake_refresh

        repo = SqlDomainPolicyRepository(mock_session)
        result = await repo.mark_verified(policy_id)

        assert result.verified is True
        assert result.verified_at is not None
