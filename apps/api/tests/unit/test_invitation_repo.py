"""Unit tests for SqlInvitationRepository."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from tessera_core.domain.entities import Invitation, InvitationStatus


def _make_invitation(
    company_id: uuid.UUID,
    email: str = "alice@acme.com",
    status: InvitationStatus = InvitationStatus.PENDING,
    days_until_expiry: int = 7,
) -> Invitation:
    token = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
    return Invitation(
        company_id=company_id,
        email=email,
        token_hash=token,
        status=status,
        expires_at=datetime.now(UTC) + timedelta(days=days_until_expiry),
    )


@pytest.fixture
def company_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


def _make_model(inv: Invitation):
    from tessera_api.adapters.models import InvitationModel

    model = InvitationModel(
        id=inv.id,
        company_id=inv.company_id,
        invited_by_user_id=inv.invited_by_user_id,
        email=inv.email,
        token_hash=inv.token_hash,
        status=inv.status.value,
        expires_at=inv.expires_at,
        accepted_at=inv.accepted_at,
    )
    model.created_at = datetime.now(UTC)
    return model


class TestSqlInvitationRepositoryCreate:
    @pytest.mark.anyio
    async def test_create_persists_single_invitation(self, mock_session, company_id):
        from tessera_api.adapters.repo import SqlInvitationRepository

        inv = _make_invitation(company_id)

        async def fake_refresh(m):
            m.created_at = datetime.now(UTC)

        mock_session.refresh.side_effect = fake_refresh
        repo = SqlInvitationRepository(mock_session)
        result = await repo.create(inv)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert result.email == inv.email
        assert result.status == InvitationStatus.PENDING

    @pytest.mark.anyio
    async def test_create_bulk_persists_all_invitations(self, mock_session, company_id):
        from tessera_api.adapters.repo import SqlInvitationRepository

        invitations = [
            _make_invitation(company_id, email=f"user{i}@acme.com") for i in range(3)
        ]

        async def fake_refresh(m):
            m.created_at = datetime.now(UTC)

        mock_session.refresh.side_effect = fake_refresh
        repo = SqlInvitationRepository(mock_session)
        results = await repo.create_bulk(invitations)

        assert mock_session.add.call_count == 3
        assert len(results) == 3
        emails = {r.email for r in results}
        assert emails == {f"user{i}@acme.com" for i in range(3)}

    @pytest.mark.anyio
    async def test_create_bulk_empty_list_returns_empty(self, mock_session, company_id):
        from tessera_api.adapters.repo import SqlInvitationRepository

        repo = SqlInvitationRepository(mock_session)
        results = await repo.create_bulk([])

        assert results == []
        mock_session.add.assert_not_called()


class TestSqlInvitationRepositoryLookup:
    @pytest.mark.anyio
    async def test_get_by_token_hash_returns_invitation(self, mock_session, company_id):
        from tessera_api.adapters.repo import SqlInvitationRepository

        inv = _make_invitation(company_id)
        model = _make_model(inv)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = model
        mock_session.execute.return_value = mock_result

        repo = SqlInvitationRepository(mock_session)
        result = await repo.get_by_token_hash(inv.token_hash)

        assert result is not None
        assert result.token_hash == inv.token_hash
        assert result.email == inv.email

    @pytest.mark.anyio
    async def test_get_by_token_hash_returns_none_when_not_found(self, mock_session):
        from tessera_api.adapters.repo import SqlInvitationRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = SqlInvitationRepository(mock_session)
        result = await repo.get_by_token_hash("nonexistent_hash")

        assert result is None

    @pytest.mark.anyio
    async def test_get_pending_for_email_returns_matching_invitations(
        self, mock_session, company_id
    ):
        from tessera_api.adapters.repo import SqlInvitationRepository

        inv1 = _make_invitation(company_id, email="alice@acme.com")
        inv2 = _make_invitation(company_id, email="alice@acme.com")
        models = [_make_model(inv1), _make_model(inv2)]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = models
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = SqlInvitationRepository(mock_session)
        results = await repo.get_pending_for_email("alice@acme.com")

        assert len(results) == 2
        assert all(r.email == "alice@acme.com" for r in results)


class TestSqlInvitationRepositoryStatusUpdate:
    @pytest.mark.anyio
    async def test_update_status_to_accepted_sets_accepted_at(
        self, mock_session, company_id
    ):
        from tessera_api.adapters.repo import SqlInvitationRepository

        inv = _make_invitation(company_id)
        model = _make_model(inv)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = model
        mock_session.execute.return_value = mock_result

        async def fake_refresh(m):
            pass

        mock_session.refresh.side_effect = fake_refresh

        repo = SqlInvitationRepository(mock_session)
        result = await repo.update_status(inv.id, InvitationStatus.ACCEPTED)

        assert result.status == InvitationStatus.ACCEPTED
        assert model.accepted_at is not None
        mock_session.flush.assert_awaited()

    @pytest.mark.anyio
    async def test_update_status_raises_when_not_found(self, mock_session, company_id):
        from tessera_api.adapters.repo import SqlInvitationRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = SqlInvitationRepository(mock_session)
        with pytest.raises(ValueError, match="not found"):
            await repo.update_status(uuid.uuid4(), InvitationStatus.ACCEPTED)

    @pytest.mark.anyio
    async def test_cancel_sets_cancelled_status(self, mock_session, company_id):
        from tessera_api.adapters.repo import SqlInvitationRepository

        inv = _make_invitation(company_id)
        model = _make_model(inv)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = model
        mock_session.execute.return_value = mock_result

        repo = SqlInvitationRepository(mock_session)
        await repo.cancel(inv.id)

        assert model.status == InvitationStatus.CANCELLED.value
        mock_session.flush.assert_awaited()

    @pytest.mark.anyio
    async def test_cancel_is_noop_when_not_found(self, mock_session):
        from tessera_api.adapters.repo import SqlInvitationRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = SqlInvitationRepository(mock_session)
        await repo.cancel(uuid.uuid4())

        mock_session.flush.assert_not_awaited()
