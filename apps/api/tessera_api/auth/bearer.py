"""Bearer token (service token) auth for agent-facing endpoints."""

from __future__ import annotations

import hashlib
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from tessera_core.domain.entities import AgentCredential

_bearer_scheme = HTTPBearer(auto_error=False)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def get_agent_credential(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    request: Request,
) -> AgentCredential | None:
    if credentials is None:
        return None
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlAgentCredentialRepository

    token_hash = hash_token(credentials.credentials)
    async with get_db() as session:
        repo = SqlAgentCredentialRepository(session)
        credential = await repo.get_by_token_hash(token_hash)
        if credential is None or credential.is_revoked:
            return None
        return credential


async def require_agent(
    credential: Annotated[AgentCredential | None, Depends(get_agent_credential)],
) -> AgentCredential:
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked service token",
        )
    return credential


async def require_onboarding_complete(request: Request) -> None:
    """Dependency that blocks access until the authenticated user has finished onboarding.

    Routes exempt from this guard (accessible before onboarding completes):
    - GET  /v1/companies/suggestions         (company step: load join suggestions)
    - POST /v1/companies                     (company step: create new company)
    - POST /v1/companies/{id}/join           (company step: join via invite or domain)
    - GET  /v1/companies/{id}/join-status    (holding screen: poll request status)
    - DELETE /v1/companies/{id}/join-request (holding screen: cancel join request)
    """
    import re

    path = request.url.path
    exempt_patterns = [
        (r"^/v1/companies/suggestions$", {"GET"}),
        (r"^/v1/companies$", {"POST"}),
        (r"^/v1/companies/[^/]+/join$", {"POST"}),
        (r"^/v1/companies/[^/]+/join-status$", {"GET"}),
        (r"^/v1/companies/[^/]+/join-request$", {"DELETE"}),
    ]
    for pattern, methods in exempt_patterns:
        if re.match(pattern, path) and request.method in methods:
            return

    from tessera_api.auth.oidc import require_user

    try:
        user_info = await require_user(request)
    except HTTPException:
        return  # No authenticated user — JWT/OIDC guard will handle 401

    user_id = UUID(user_info["sub"])

    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlOnboardingRepository

    async with get_db() as session:
        repo = SqlOnboardingRepository(session)
        progress = await repo.get_by_user_id(user_id)
        if progress is None or progress.completed_at is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "onboarding_required",
                    "message": "Complete onboarding before accessing this resource.",
                },
            )
