"""Unit tests for JWT and password helper functions."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from tessera_api.auth.jwt_auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expires_at,
    verify_access_token,
    verify_password,
)


class TestPasswordHelpers:
    def test_hash_password_returns_bcrypt_hash(self):
        hashed = hash_password("mysecret")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_verify_password_correct(self):
        hashed = hash_password("correct")
        assert verify_password("correct", hashed) is True

    def test_verify_password_wrong(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_hash_is_not_plaintext(self):
        hashed = hash_password("secret")
        assert hashed != "secret"


class TestAccessToken:
    def test_create_and_verify_returns_claims(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id, "alice@example.com", is_admin=False)
        claims = verify_access_token(token)
        assert claims["sub"] == str(user_id)
        assert claims["email"] == "alice@example.com"
        assert claims["is_admin"] is False

    def test_admin_claim_reflected(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id, "admin@example.com", is_admin=True)
        claims = verify_access_token(token)
        assert claims["is_admin"] is True

    def test_token_has_exp_in_future(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id, "user@example.com", is_admin=False)
        claims = verify_access_token(token)
        assert claims["exp"] > int(datetime.now(UTC).timestamp())

    def test_tampered_token_raises(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id, "user@example.com", is_admin=False)
        bad_token = token[:-5] + "XXXXX"
        with pytest.raises(Exception):
            verify_access_token(bad_token)

    def test_expired_token_raises(self):
        user_id = uuid.uuid4()
        with patch("tessera_api.auth.jwt_auth.get_settings") as mock_settings:
            mock_settings.return_value.jwt_access_token_expire_minutes = -1
            mock_settings.return_value.jwt_algorithm = "HS256"
            mock_settings.return_value.secret_key = "test-secret"
            token = create_access_token(user_id, "user@example.com", is_admin=False)

        with patch("tessera_api.auth.jwt_auth.get_settings") as mock_settings:
            mock_settings.return_value.secret_key = "test-secret"
            with pytest.raises(Exception):
                verify_access_token(token)

    def test_each_token_has_unique_jti(self):
        user_id = uuid.uuid4()
        t1 = create_access_token(user_id, "u@example.com", is_admin=False)
        t2 = create_access_token(user_id, "u@example.com", is_admin=False)
        c1 = verify_access_token(t1)
        c2 = verify_access_token(t2)
        assert c1["jti"] != c2["jti"]


class TestRefreshToken:
    def test_create_refresh_token_is_url_safe_string(self):
        token = create_refresh_token()
        assert isinstance(token, str)
        assert len(token) > 20

    def test_refresh_tokens_are_unique(self):
        tokens = {create_refresh_token() for _ in range(100)}
        assert len(tokens) == 100

    def test_hash_refresh_token_is_sha256_hex(self):
        token = create_refresh_token()
        hashed = hash_refresh_token(token)
        assert len(hashed) == 64
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_same_token_same_hash(self):
        token = create_refresh_token()
        assert hash_refresh_token(token) == hash_refresh_token(token)

    def test_different_tokens_different_hashes(self):
        t1, t2 = create_refresh_token(), create_refresh_token()
        assert hash_refresh_token(t1) != hash_refresh_token(t2)

    def test_expires_at_in_future(self):
        exp = refresh_token_expires_at()
        assert exp > datetime.now(UTC)
