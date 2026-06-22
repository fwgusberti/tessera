"""OIDC (Google Workspace) authentication and session management."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import Depends, HTTPException, Request, status

from tessera_api.adapters.database import get_db
from tessera_api.adapters.repo import SqlCompanyRepository
from tessera_api.config import get_settings


def get_login_url(request: Request, state: str) -> str:
    settings = get_settings()
    params = {
        "client_id": settings.oidc_client_id,
        "redirect_uri": str(request.url_for("auth_callback")),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
    from urllib.parse import urlencode

    return f"{settings.oidc_issuer}/o/oauth2/v2/auth?{urlencode(params)}"


async def exchange_code_for_user(code: str, redirect_uri: str) -> dict[str, Any]:
    settings = get_settings()
    async with AsyncOAuth2Client(
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
    ) as client:
        token = await client.fetch_token(
            f"{settings.oidc_issuer}/token",
            code=code,
            redirect_uri=redirect_uri,
        )
        userinfo = await client.get(f"{settings.oidc_issuer}/userinfo")
        userinfo.raise_for_status()
        return {"token": token, "userinfo": userinfo.json()}


def get_current_user_from_session(request: Request) -> dict[str, Any] | None:
    """Extract the authenticated user info from the session cookie."""
    return request.session.get("user")


async def require_user(request: Request) -> dict[str, Any]:
    # 1. Session cookie (existing OIDC path — backward compat)
    user = get_current_user_from_session(request)
    if user and user.get("sub"):
        return user

    # 2. JWT Bearer token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer ") :]
        try:
            from tessera_api.auth.jwt_auth import verify_access_token

            claims = verify_access_token(token)
            return {
                "sub": claims["sub"],
                "id": claims["sub"],
                "email": claims.get("email", ""),
                "is_admin": claims.get("is_admin", False),
            }
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": {"code": "invalid_token", "message": "Invalid or expired token"}},
            ) from None

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


CurrentUser = Annotated[dict[str, Any], Depends(require_user)]


async def require_company_context(request: Request) -> tuple[dict[str, Any], UUID]:
    """Returns (user_info, company_id). Raises 401 if unauthenticated, 403 if no company context."""
    user_info = await require_user(request)
    company_id: UUID | None = None

    # 1. Try JWT claim
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer ") :]
        try:
            from tessera_api.auth.jwt_auth import verify_access_token

            claims = verify_access_token(token)
            if "company_id" in claims:
                company_id = UUID(claims["company_id"])
        except Exception:
            pass

    # 2. Try session cookie
    if company_id is None:
        active = request.session.get("user", {}).get("active_company_id")
        if active:
            company_id = UUID(str(active))

    if company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {"code": "no_company_context", "message": "No active company context"}
            },
        )

    # 3. Verify membership is still active in the DB
    user_id = UUID(user_info["sub"])
    async with get_db() as session:
        repo = SqlCompanyRepository(session)
        membership = await repo.get_membership(user_id, company_id)

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "forbidden", "message": "Membership revoked or not found"}},
        )

    return user_info, company_id


CompanyContext = Annotated[tuple[dict[str, Any], Any], Depends(require_company_context)]
