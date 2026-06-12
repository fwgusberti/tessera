"""OIDC (Google Workspace) authentication and session management."""

from __future__ import annotations

import hashlib
import secrets
from typing import Annotated, Any
from uuid import UUID

from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

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
    user = get_current_user_from_session(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


CurrentUser = Annotated[dict[str, Any], Depends(require_user)]
