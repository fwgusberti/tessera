"""Unit tests for PasswordResetService (TDD — written before implementation)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4


class TestPasswordResetServiceCreateToken:
    def _service(self):
        from tessera_core.services.password_reset import PasswordResetService

        return PasswordResetService()

    def test_returns_token_entity_and_raw_string(self):
        svc = self._service()
        user_id = uuid4()
        token, raw = svc.create_token(user_id)
        assert token is not None
        assert isinstance(raw, str)
        assert len(raw) > 20

    def test_token_hash_is_sha256_of_raw(self):
        svc = self._service()
        user_id = uuid4()
        token, raw = svc.create_token(user_id)
        expected_hash = hashlib.sha256(raw.encode()).hexdigest()
        assert token.token_hash == expected_hash

    def test_token_user_id_matches(self):
        svc = self._service()
        user_id = uuid4()
        token, _ = svc.create_token(user_id)
        assert token.user_id == user_id

    def test_default_expiry_is_60_minutes(self):
        svc = self._service()
        user_id = uuid4()
        before = datetime.now(UTC)
        token, _ = svc.create_token(user_id)
        after = datetime.now(UTC)
        expected_min = before + timedelta(minutes=59)
        expected_max = after + timedelta(minutes=61)
        assert expected_min <= token.expires_at <= expected_max

    def test_custom_expiry_respected(self):
        svc = self._service()
        user_id = uuid4()
        before = datetime.now(UTC)
        token, _ = svc.create_token(user_id, expires_in_minutes=30)
        after = datetime.now(UTC)
        expected_min = before + timedelta(minutes=29)
        expected_max = after + timedelta(minutes=31)
        assert expected_min <= token.expires_at <= expected_max

    def test_consumed_at_is_none_on_creation(self):
        svc = self._service()
        token, _ = svc.create_token(uuid4())
        assert token.consumed_at is None

    def test_two_tokens_have_different_hashes(self):
        svc = self._service()
        user_id = uuid4()
        _, raw1 = svc.create_token(user_id)
        _, raw2 = svc.create_token(user_id)
        assert raw1 != raw2


class TestPasswordResetServiceIsValid:
    def _service(self):
        from tessera_core.services.password_reset import PasswordResetService

        return PasswordResetService()

    def _make_token(self, *, expires_delta=timedelta(hours=1), consumed=False):
        from tessera_core.domain.entities import PasswordResetToken

        now = datetime.now(UTC)
        return PasswordResetToken(
            user_id=uuid4(),
            token_hash="abc123",
            expires_at=now + expires_delta,
            consumed_at=now if consumed else None,
        )

    def test_valid_token_is_valid(self):
        svc = self._service()
        token = self._make_token()
        assert svc.is_valid(token) is True

    def test_expired_token_is_invalid(self):
        svc = self._service()
        token = self._make_token(expires_delta=timedelta(seconds=-1))
        assert svc.is_valid(token) is False

    def test_consumed_token_is_invalid(self):
        svc = self._service()
        token = self._make_token(consumed=True)
        assert svc.is_valid(token) is False

    def test_consumed_and_expired_is_invalid(self):
        svc = self._service()
        token = self._make_token(expires_delta=timedelta(seconds=-1), consumed=True)
        assert svc.is_valid(token) is False
