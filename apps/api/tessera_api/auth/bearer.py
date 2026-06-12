"""Bearer token (service token) auth for agent-facing endpoints."""

from __future__ import annotations

import hashlib
from typing import Annotated

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
