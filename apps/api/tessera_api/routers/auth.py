"""Authentication endpoints: register, login, refresh, logout, change-password, reset-password."""

from __future__ import annotations

import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.database import SessionDep
from tessera_api.adapters.repo import (
    SqlCompanyRepository,
    SqlPasswordResetTokenRepository,
    SqlRefreshTokenRepository,
    SqlUserRepository,
)
from tessera_api.auth.jwt_auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expires_at,
    verify_access_token,
    verify_password,
)
from tessera_api.auth.oidc import require_unscoped_or_full_token
from tessera_api.auth.password_strength import validate_password_strength
from tessera_api.config import get_settings
from tessera_core.domain.entities import RefreshToken, User
from tessera_core.domain.token_kind import TokenKind

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


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str
    refresh_token: str


class SelectTenantRequest(BaseModel):
    company_id: uuid.UUID


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_new_password: str


# ---------------------------------------------------------------------------
# POST /v1/auth/register
# ---------------------------------------------------------------------------


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, session: SessionDep) -> dict:
    user_repo = SqlUserRepository(session)

    existing = await user_repo.get_by_email(body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "email_already_registered",
                    "message": "Email already registered",
                }
            },
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
async def login(body: LoginRequest, session: SessionDep) -> dict:
    _INVALID = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "invalid_credentials", "message": "Invalid credentials"}},
    )

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

    company_repo = SqlCompanyRepository(session)
    memberships = await company_repo.list_memberships_for_user(user.id)

    membership_count = len(memberships)
    if membership_count == 1:
        token_kind: TokenKind = "full"
        auto_company_id = memberships[0].company_id
    elif membership_count > 1:
        token_kind = "select"
        auto_company_id = None
    else:
        token_kind = "onboarding"
        auto_company_id = None

    raw_refresh = create_refresh_token()
    refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh),
        expires_at=refresh_token_expires_at(),
        company_id=auto_company_id,
        token_kind=token_kind,
    )
    await rt_repo.create(refresh_record)

    await write_audit(
        session,
        actor_type="user",
        actor_id=user.id,
        action="auth.login.success",
        entity_type="user",
        entity_id=user.id,
        metadata={"token_kind": token_kind},
    )

    settings = get_settings()
    access_token = create_access_token(
        user.id,
        user.email,
        user.is_admin,
        company_id=auto_company_id,
        token_kind=token_kind,
    )

    response: dict = {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }
    if token_kind == "select":
        response["tenant_selection_required"] = True
    return response


# ---------------------------------------------------------------------------
# POST /v1/auth/refresh
# ---------------------------------------------------------------------------


@router.post("/refresh")
async def refresh(body: RefreshRequest, session: SessionDep) -> dict:
    _INVALID = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": {
                "code": "invalid_refresh_token",
                "message": "Invalid or expired refresh token",
            }
        },
    )

    from datetime import UTC, datetime

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

    # Preserve scope from the stored refresh token
    preserved_company_id = stored.company_id
    preserved_token_kind: TokenKind = stored.token_kind  # type: ignore[assignment]

    raw_refresh = create_refresh_token()
    new_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh),
        expires_at=refresh_token_expires_at(),
        company_id=preserved_company_id,
        token_kind=preserved_token_kind,
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
    access_token = create_access_token(
        user.id,
        user.email,
        user.is_admin,
        company_id=preserved_company_id,
        token_kind=preserved_token_kind,
    )

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


# ---------------------------------------------------------------------------
# POST /v1/auth/select-tenant
# ---------------------------------------------------------------------------


@router.post("/select-tenant")
async def select_tenant(
    body: SelectTenantRequest,
    user_info: Annotated[dict, Depends(require_unscoped_or_full_token)],
    session: SessionDep,
) -> dict:
    """Exchange a select or full token for a full token scoped to the requested company."""
    user_id = uuid.UUID(user_info["sub"])
    target_company_id = body.company_id

    company_repo = SqlCompanyRepository(session)
    rt_repo = SqlRefreshTokenRepository(session)

    company = await company_repo.get_by_id(target_company_id)
    if company is not None and hasattr(company, "is_active") and not company.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "company_suspended",
                    "message": "The company account is suspended",
                }
            },
        )

    membership = await company_repo.get_membership(user_id, target_company_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "not_a_member",
                    "message": "You are not a member of this company",
                }
            },
        )

    is_admin = membership.role.value == "admin"

    raw_refresh = create_refresh_token()
    new_record = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(raw_refresh),
        expires_at=refresh_token_expires_at(),
        company_id=target_company_id,
        token_kind="full",
    )
    await rt_repo.create(new_record)

    await write_audit(
        session,
        actor_type="user",
        actor_id=user_id,
        action="auth.credential.issued",
        entity_type="company",
        entity_id=target_company_id,
        metadata={"company_id": str(target_company_id)},
    )

    settings = get_settings()
    access_token = create_access_token(
        user_id,
        user_info.get("email", ""),
        is_admin,
        company_id=target_company_id,
        token_kind="full",
    )

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
    session: SessionDep,
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


# ---------------------------------------------------------------------------
# POST /v1/auth/change-password
# ---------------------------------------------------------------------------


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: SessionDep,
) -> dict:
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

    if body.new_password != body.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "password_mismatch", "message": "Passwords do not match"}},
        )

    try:
        validate_password_strength(body.new_password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "password_too_weak", "message": str(exc)}},
        ) from exc

    user_id = uuid.UUID(claims["sub"])

    user_repo = SqlUserRepository(session)
    rt_repo = SqlRefreshTokenRepository(session)

    user = await user_repo.get_by_id(user_id)
    if (
        user is None
        or not user.password_hash
        or not verify_password(body.current_password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "invalid_credentials",
                    "message": "Current password is incorrect",
                }
            },
        )

    from sqlalchemy import update as sa_update

    from tessera_api.adapters.models import UserModel

    await session.execute(
        sa_update(UserModel)
        .where(UserModel.id == user_id)
        .values(password_hash=hash_password(body.new_password))
    )

    current_hash = hash_refresh_token(body.refresh_token)
    await rt_repo.revoke_all_except(user_id=user_id, except_hash=current_hash)
    await rt_repo.revoke(current_hash)

    raw_refresh = create_refresh_token()
    new_record = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(raw_refresh),
        expires_at=refresh_token_expires_at(),
    )
    await rt_repo.create(new_record)

    await write_audit(
        session,
        actor_type="user",
        actor_id=user_id,
        action="auth.password.change",
        entity_type="user",
        entity_id=user_id,
    )

    settings = get_settings()
    access_token = create_access_token(user_id, claims["email"], claims.get("is_admin", False))
    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


# ---------------------------------------------------------------------------
# POST /v1/auth/forgot-password
# ---------------------------------------------------------------------------

_FORGOT_PASSWORD_RESPONSE = {
    "message": "If that email is registered, you will receive a reset link shortly."
}
_RATE_LIMIT_MAX = 5
_RATE_LIMIT_WINDOW = 900  # 15 minutes


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest, request: Request, session: SessionDep
) -> dict:
    from tessera_api.adapters.email import FastMailEmailAdapter
    from tessera_api.auth.rate_limit import check_rate_limit
    from tessera_core.services.password_reset import PasswordResetService

    client_ip = (
        request.headers.get("x-forwarded-for") or request.client.host
        if request.client
        else "unknown"
    )
    rate_key = f"reset:{client_ip}"

    import redis.asyncio as aioredis

    settings = get_settings()
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        within_limit = await check_rate_limit(
            redis_client, rate_key, _RATE_LIMIT_MAX, _RATE_LIMIT_WINDOW
        )
    finally:
        await redis_client.aclose()

    if not within_limit:
        return _FORGOT_PASSWORD_RESPONSE

    user_repo = SqlUserRepository(session)
    user = await user_repo.get_by_email(body.email.lower().strip())

    if user is None:
        hash_password("dummy_timing_equaliser")
        await write_audit(
            session,
            actor_type="anonymous",
            actor_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            action="auth.password.reset_requested",
            entity_type="user",
            entity_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            metadata={"email": body.email, "found": False},
        )
        return _FORGOT_PASSWORD_RESPONSE

    prt_repo = SqlPasswordResetTokenRepository(session)
    svc = PasswordResetService()
    token_entity, raw_token = svc.create_token(user.id)
    await prt_repo.create(token_entity)

    reset_url = f"{settings.frontend_url}/reset-password?token={raw_token}"
    email_adapter = FastMailEmailAdapter()
    await email_adapter.send_password_reset(
        to=user.email, reset_url=reset_url, expires_in_minutes=60
    )

    await write_audit(
        session,
        actor_type="anonymous",
        actor_id=user.id,
        action="auth.password.reset_requested",
        entity_type="user",
        entity_id=user.id,
        metadata={"email": body.email},
    )

    return _FORGOT_PASSWORD_RESPONSE


# ---------------------------------------------------------------------------
# POST /v1/auth/reset-password
# ---------------------------------------------------------------------------


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(body: ResetPasswordRequest, session: SessionDep) -> None:
    if body.new_password != body.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "password_mismatch", "message": "Passwords do not match"}},
        )

    try:
        validate_password_strength(body.new_password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "password_too_weak", "message": str(exc)}},
        ) from exc

    _INVALID = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "error": {
                "code": "invalid_or_expired_token",
                "message": "Reset link is invalid or has expired",
            }
        },
    )

    token_hash = hashlib.sha256(body.token.encode()).hexdigest()

    from datetime import UTC, datetime

    from tessera_api.adapters.models import PasswordResetTokenModel, UserModel
    from tessera_core.services.password_reset import PasswordResetService

    prt_repo = SqlPasswordResetTokenRepository(session)
    token_entity = await prt_repo.get_by_hash(token_hash)

    if token_entity is None:
        raise _INVALID

    svc = PasswordResetService()
    if not svc.is_valid(token_entity):
        raise _INVALID

    from sqlalchemy import update as sa_update

    await session.execute(
        sa_update(PasswordResetTokenModel)
        .where(PasswordResetTokenModel.token_hash == token_hash)
        .values(consumed_at=datetime.now(UTC))
    )

    await session.execute(
        sa_update(UserModel)
        .where(UserModel.id == token_entity.user_id)
        .values(password_hash=hash_password(body.new_password))
    )

    rt_repo = SqlRefreshTokenRepository(session)
    await rt_repo.revoke_all_for_user(token_entity.user_id)

    await write_audit(
        session,
        actor_type="anonymous",
        actor_id=token_entity.user_id,
        action="auth.password.reset_completed",
        entity_type="user",
        entity_id=token_entity.user_id,
    )
