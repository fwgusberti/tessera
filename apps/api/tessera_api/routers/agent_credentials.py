"""Agent credential issuance and revocation endpoints.

Company-scoped (feature 035): issuance requires the caller to administer the
active company, binds the credential to that company, and validates that every
scoped space belongs to it (FR-006). Revocation only ever touches credentials
owned by the active company. Cross-company by-ID attempts are audited as
``cross_tenant_denied`` and return a generic 404 body (indistinguishable from
absent, FR-004).
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.database import get_db
from tessera_api.adapters.repo import SqlAgentCredentialRepository, SqlSpaceRepository
from tessera_api.auth.oidc import require_company_admin
from tessera_core.domain.entities import AgentCredential, Confidentiality

router = APIRouter(tags=["agent_credentials"])


class CreateCredentialRequest(BaseModel):
    name: str
    scoped_space_ids: list[UUID]
    max_confidentiality: Confidentiality = Confidentiality.INTERNAL


def _not_found() -> HTTPException:
    """Generic 404 for cross-company by-ID access — indistinguishable from absent (FR-004)."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": {"code": "not_found", "message": "Not found"}},
    )


async def _audit_cross_tenant_denied(
    actor_id: UUID, credential_id: UUID, company_id: UUID, metadata_extra: dict | None = None
) -> None:
    metadata = {"company_id": str(company_id)}
    if metadata_extra:
        metadata.update(metadata_extra)
    async with get_db() as audit_session:
        await write_audit(
            audit_session,
            actor_type="user",
            actor_id=actor_id,
            action="cross_tenant_denied",
            entity_type="agent_credential",
            entity_id=credential_id,
            metadata=metadata,
        )


@router.post("/agent-credentials", status_code=status.HTTP_201_CREATED)
async def create_credential(body: CreateCredentialRequest, request: Request) -> dict:
    user_info, company_id, _membership = await require_company_admin(request)
    actor_id = UUID(user_info["sub"])
    credential_id = uuid.uuid4()

    # Every scoped space must belong to the active company (FR-006).
    async with get_db() as session:
        space_repo = SqlSpaceRepository(session)
        invalid_space_id: UUID | None = None
        for space_id in body.scoped_space_ids:
            space = await space_repo.get_by_id_for_company(space_id, company_id)
            if space is None:
                invalid_space_id = space_id
                break

    if invalid_space_id is not None:
        await _audit_cross_tenant_denied(
            actor_id, credential_id, company_id, {"space_id": str(invalid_space_id)}
        )
        raise _not_found()

    # Generate a random token — shown once
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    credential = AgentCredential(
        id=credential_id,
        name=body.name,
        token_hash=token_hash,
        scoped_space_ids=body.scoped_space_ids,
        max_confidentiality=body.max_confidentiality,
        created_by_user_id=user_info.get("id"),
        company_id=company_id,
    )
    async with get_db() as session:
        repo = SqlAgentCredentialRepository(session)
        created = await repo.create(credential)
        await write_audit(
            session,
            actor_type="user",
            actor_id=actor_id,
            action="create_credential",
            entity_type="agent_credential",
            entity_id=created.id,
            metadata={"company_id": str(company_id)},
        )

    return {"credential": created.model_dump(exclude={"token_hash"}), "token": raw_token}


@router.post("/agent-credentials/{credential_id}/revoke")
async def revoke_credential(credential_id: UUID, request: Request) -> dict:
    user_info, company_id, _membership = await require_company_admin(request)
    actor_id = UUID(user_info["sub"])

    async with get_db() as session:
        repo = SqlAgentCredentialRepository(session)
        existing = await repo.get_by_id_for_company(credential_id, company_id)

    if existing is None:
        # Not ours — leave the token active and deny indistinguishably.
        await _audit_cross_tenant_denied(actor_id, credential_id, company_id)
        raise _not_found()

    async with get_db() as session:
        repo = SqlAgentCredentialRepository(session)
        revoked = await repo.revoke(credential_id)
        await write_audit(
            session,
            actor_type="user",
            actor_id=actor_id,
            action="revoke_credential",
            entity_type="agent_credential",
            entity_id=credential_id,
            metadata={"company_id": str(company_id)},
        )

    return {"credential": revoked.model_dump(exclude={"token_hash"})}
