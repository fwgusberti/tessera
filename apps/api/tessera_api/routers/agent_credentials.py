"""Agent credential issuance and revocation endpoints."""

from __future__ import annotations

import hashlib
import secrets
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from tessera_core.domain.entities import AgentCredential, Confidentiality

router = APIRouter(tags=["agent_credentials"])


class CreateCredentialRequest(BaseModel):
    name: str
    scoped_space_ids: list[UUID]
    max_confidentiality: Confidentiality = Confidentiality.INTERNAL


@router.post("/agent-credentials", status_code=status.HTTP_201_CREATED)
async def create_credential(body: CreateCredentialRequest, request: Request) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlAgentCredentialRepository
    from tessera_api.adapters.audit import write_audit
    from tessera_api.auth.oidc import require_user

    user_info = await require_user(request)
    if not user_info.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin required")

    # Generate a random token — shown once
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    credential = AgentCredential(
        name=body.name,
        token_hash=token_hash,
        scoped_space_ids=body.scoped_space_ids,
        max_confidentiality=body.max_confidentiality,
        created_by_user_id=user_info.get("id"),
    )
    async with get_db() as session:
        repo = SqlAgentCredentialRepository(session)
        created = await repo.create(credential)
        await write_audit(
            session,
            actor_type="user",
            actor_id=user_info.get("id"),
            action="create_credential",
            entity_type="agent_credential",
            entity_id=created.id,
        )

    return {"credential": created.model_dump(exclude={"token_hash"}), "token": raw_token}


@router.post("/agent-credentials/{credential_id}/revoke")
async def revoke_credential(credential_id: UUID, request: Request) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlAgentCredentialRepository
    from tessera_api.adapters.audit import write_audit
    from tessera_api.auth.oidc import require_user

    user_info = await require_user(request)
    if not user_info.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin required")

    async with get_db() as session:
        repo = SqlAgentCredentialRepository(session)
        revoked = await repo.revoke(credential_id)
        await write_audit(
            session,
            actor_type="user",
            actor_id=user_info.get("id"),
            action="revoke_credential",
            entity_type="agent_credential",
            entity_id=credential_id,
        )

    return {"credential": revoked.model_dump(exclude={"token_hash"})}
