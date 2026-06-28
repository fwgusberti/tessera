"""OIDC (Google Workspace) authentication and session management."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import Depends, HTTPException, Request, status

from tessera_api.adapters.database import get_db
from tessera_api.adapters.repo import SqlCompanyRepository
from tessera_api.config import get_settings
from tessera_core.domain.entities import CompanyMembership, CompanyRole


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
                "token_kind": claims.get("token_kind", "full"),
                "company_id": claims.get("company_id"),
            }
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": {"code": "invalid_token", "message": "Invalid or expired token"}},
            ) from None

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


CurrentUser = Annotated[dict[str, Any], Depends(require_user)]


async def _resolve_company_membership(
    request: Request,
) -> tuple[dict[str, Any], UUID, CompanyMembership]:
    """Resolve (user_info, company_id, membership) from the request.

    Raises 401 if unauthenticated, 403 if the token is not fully scoped or
    there is no active company context, and 403 if the caller's membership
    in that company is revoked, missing, or the company is inactive.
    """
    user_info = await require_user(request)

    # Gate: only full-scoped tokens may access data endpoints.
    token_kind = user_info.get("token_kind", "full")
    if token_kind != "full":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "credential_not_scoped",
                    "message": "Credential is not scoped to a tenant; call /auth/select-tenant first",
                }
            },
        )

    company_id: UUID | None = None

    # 1. Try JWT claim (already decoded by require_user)
    raw_cid = user_info.get("company_id")
    if raw_cid:
        company_id = UUID(str(raw_cid))

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

    # 3. Verify company is active and membership is still valid in the DB
    user_id = UUID(user_info["sub"])
    async with get_db() as session:
        repo = SqlCompanyRepository(session)
        company = await repo.get_by_id(company_id)
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
        membership = await repo.get_membership(user_id, company_id)

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {"code": "not_a_member", "message": "Membership revoked or not found"}
            },
        )

    return user_info, company_id, membership


async def require_company_context(request: Request) -> tuple[dict[str, Any], UUID]:
    """Returns (user_info, company_id). Raises 401 if unauthenticated, 403 if no company context."""
    user_info, company_id, _ = await _resolve_company_membership(request)
    return user_info, company_id


async def require_company_member(
    request: Request,
) -> tuple[dict[str, Any], UUID, CompanyMembership]:
    """Returns (user_info, company_id, membership) for any active-company member.

    A thin wrapper over ``_resolve_company_membership`` that exposes the resolved
    membership to read-path routers so they can derive ``is_company_admin`` without
    a second DB hit. Unlike ``require_company_admin`` it does not require the ADMIN
    role — the caller decides what authority the role confers.
    """
    return await _resolve_company_membership(request)


def is_company_admin(membership: CompanyMembership) -> bool:
    """True if the membership confers company-admin authority in the active company."""
    return membership.role == CompanyRole.ADMIN


async def require_company_admin(
    request: Request,
) -> tuple[dict[str, Any], UUID, CompanyMembership]:
    """Returns (user_info, company_id, membership), requiring CompanyRole.ADMIN in the active company.

    Raises 403 with the generic body when the caller is not an admin of the active
    company. The global ``is_admin`` JWT flag is NOT consulted here — per-company
    admin authority comes only from the CompanyMembership role.
    """
    user_info, company_id, membership = await _resolve_company_membership(request)
    if membership.role != CompanyRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "forbidden", "message": "Access denied"}},
        )
    return user_info, company_id, membership


async def require_select_token(request: Request) -> dict[str, Any]:
    """Verify the request carries a select-kind token; raise 403 for any other kind."""
    user_info = await require_user(request)
    token_kind = user_info.get("token_kind", "full")
    if token_kind != "select":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "wrong_token_kind",
                    "message": f"Expected select token, got {token_kind!r}",
                }
            },
        )
    return user_info


async def require_unscoped_or_full_token(request: Request) -> dict[str, Any]:
    """Verify the request carries a select or full-kind token; reject onboarding."""
    user_info = await require_user(request)
    token_kind = user_info.get("token_kind", "full")
    if token_kind == "onboarding":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "wrong_token_kind",
                    "message": "Onboarding tokens cannot select a tenant",
                }
            },
        )
    return user_info


CompanyContext = Annotated[tuple[dict[str, Any], Any], Depends(require_company_context)]
CompanyAdminContext = Annotated[tuple[dict[str, Any], Any, Any], Depends(require_company_admin)]
