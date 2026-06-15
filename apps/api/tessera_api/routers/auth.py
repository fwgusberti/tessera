"""Authentication endpoints: register, login, refresh, logout."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.database import get_db
from tessera_api.adapters.repo import SqlRefreshTokenRepository, SqlUserRepository
from tessera_api.auth.jwt_auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expires_at,
    verify_access_token,
    verify_password,
)
from tessera_api.config import get_settings
from tessera_core.domain.entities import RefreshToken, User

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email address")
        return v.lower().strip()


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# POST /v1/auth/register
# ---------------------------------------------------------------------------

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest) -> dict:
    async with get_db() as session:
        user_repo = SqlUserRepository(session)

        existing = await user_repo.get_by_email(body.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": {"code": "email_already_registered", "message": "Email already registered"}},
            )

        new_user = User(
            external_subject=body.email,
            email=body.email,
            display_name=body.display_name,
            password_hash=hash_password(body.password),
        )
        created = await user_repo.create(new_user)

        await write_audit(
            session,
            actor_type="anonymous",
            actor_id=created.id,
            action="auth.register",
            entity_type="user",
            entity_id=created.id,
        )

    return {
        "user": {
            "id": str(created.id),
            "email": created.email,
            "display_name": created.display_name,
            "is_admin": created.is_admin,
            "created_at": created.created_at.isoformat() if created.created_at else None,
        }
    }


# ---------------------------------------------------------------------------
# POST /v1/auth/login
# ---------------------------------------------------------------------------

@router.post("/login")
async def login(body: LoginRequest) -> dict:
    _INVALID = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "invalid_credentials", "message": "Invalid credentials"}},
    )

    async with get_db() as session:
        user_repo = SqlUserRepository(session)
        rt_repo = SqlRefreshTokenRepository(session)

        user = await user_repo.get_by_email(body.email)

        # Use constant-time comparison to avoid timing attacks
        if user is None or not user.password_hash:
            # Still call verify to consume similar time
            hash_password("dummy")
            await write_audit(
                session,
                actor_type="anonymous",
                actor_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                action="auth.login.failure",
                entity_type="user",
                entity_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                metadata={"email": body.email, "reason": "user_not_found"},
            )
            raise _INVALID

        if not verify_password(body.password, user.password_hash):
            await write_audit(
                session,
                actor_type="anonymous",
                actor_id=user.id,
                action="auth.login.failure",
                entity_type="user",
                entity_id=user.id,
                metadata={"reason": "wrong_password"},
            )
            raise _INVALID

        raw_refresh = create_refresh_token()
        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=refresh_token_expires_at(),
        )
        await rt_repo.create(refresh_record)

        await write_audit(
            session,
            actor_type="user",
            actor_id=user.id,
            action="auth.login.success",
            entity_type="user",
            entity_id=user.id,
        )

    settings = get_settings()
    access_token = create_access_token(user.id, user.email, user.is_admin)

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


# ---------------------------------------------------------------------------
# POST /v1/auth/refresh
# ---------------------------------------------------------------------------

@router.post("/refresh")
async def refresh(body: RefreshRequest) -> dict:
    _INVALID = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "invalid_refresh_token", "message": "Invalid or expired refresh token"}},
    )

    from datetime import UTC, datetime

    async with get_db() as session:
        rt_repo = SqlRefreshTokenRepository(session)
        user_repo = SqlUserRepository(session)

        token_hash = hash_refresh_token(body.refresh_token)
        stored = await rt_repo.get_by_hash(token_hash)

        if stored is None or stored.is_revoked:
            raise _INVALID
        if stored.expires_at and stored.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            raise _INVALID

        # Revoke old token (single-use rotation)
        await rt_repo.revoke(token_hash)

        user = await user_repo.get_by_id(stored.user_id)
        if user is None:
            raise _INVALID

        raw_refresh = create_refresh_token()
        new_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=refresh_token_expires_at(),
        )
        await rt_repo.create(new_record)

        await write_audit(
            session,
            actor_type="user",
            actor_id=user.id,
            action="auth.token.refresh",
            entity_type="refresh_token",
            entity_id=new_record.id,
        )

    settings = get_settings()
    access_token = create_access_token(user.id, user.email, user.is_admin)

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


# ---------------------------------------------------------------------------
# POST /v1/auth/logout
# ---------------------------------------------------------------------------

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "unauthorized", "message": "Authentication required"}},
        )

    try:
        claims = verify_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "invalid_token", "message": "Invalid access token"}},
        ) from None

    user_id = uuid.UUID(claims["sub"])

    async with get_db() as session:
        rt_repo = SqlRefreshTokenRepository(session)
        token_hash = hash_refresh_token(body.refresh_token)
        await rt_repo.delete_by_hash(token_hash)

        await write_audit(
            session,
            actor_type="user",
            actor_id=user_id,
            action="auth.logout",
            entity_type="user",
            entity_id=user_id,
        )
