"""JWT access-token and refresh-token helpers."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
from joserfc import jwt
from joserfc.jwk import OctKey

from tessera_api.config import get_settings


def _signing_key() -> OctKey:
    return OctKey.import_key(get_settings().secret_key.encode())


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# Access token (JWT)
# ---------------------------------------------------------------------------

def create_access_token(user_id: UUID, email: str, is_admin: bool) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "is_admin": is_admin,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    key = _signing_key()
    token_obj = jwt.encode(header, claims, key)
    return token_obj


def verify_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises on bad signature or expired token."""
    from joserfc.jwt import JWTClaimsRegistry

    key = _signing_key()
    token_obj = jwt.decode(token, key)
    registry = JWTClaimsRegistry(exp={"essential": True})
    registry.validate(token_obj.claims)
    return dict(token_obj.claims)


# ---------------------------------------------------------------------------
# Refresh token (opaque random)
# ---------------------------------------------------------------------------

def create_refresh_token() -> str:
    """Return a cryptographically random, URL-safe refresh token string."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_token_expires_at() -> datetime:
    settings = get_settings()
    return datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
