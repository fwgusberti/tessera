"""AI assistance endpoints for document creation and editing."""

from __future__ import annotations

import contextlib
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.database import SessionDep
from tessera_api.adapters.llm import AnthropicLLMProvider
from tessera_api.adapters.repo import (
    SqlSpaceMembershipRepository,
    SqlSpaceRepository,
    SqlUserRepository,
)
from tessera_api.ai_assist.prompts import generate_draft, generate_revision
from tessera_api.auth.oidc import CompanyMemberContext, is_company_admin
from tessera_api.routers.documents import _not_found, _resolve_document_for_draft_write
from tessera_core.permissions.access import can_write_document

router = APIRouter(tags=["document-assist"])


class DraftAssistRequest(BaseModel):
    space_id: UUID
    prompt: str
    previous_suggestion: str | None = None

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prompt must not be empty")
        return v


class DraftAssistResponse(BaseModel):
    content_markdown: str


@router.post("/documents/assist/draft")
async def draft_assist(
    body: DraftAssistRequest, ctx: CompanyMemberContext, session: SessionDep
) -> dict:
    user_info, company_id, caller_membership = ctx
    company_admin = is_company_admin(caller_membership)
    user_id_str = user_info.get("id") or user_info.get("sub")
    caller_id = UUID(user_id_str) if user_id_str else None

    space_repo = SqlSpaceRepository(session)
    space = await space_repo.get_by_id_for_company(body.space_id, company_id)
    if space is None:
        actor_id = caller_id or UUID(user_info["sub"])
        await write_audit(
            session,
            actor_type="user",
            actor_id=actor_id,
            action="cross_tenant_denied",
            entity_type="space",
            entity_id=body.space_id,
            metadata={"company_id": str(company_id)},
        )
        await session.commit()
        raise _not_found()

    user_repo = SqlUserRepository(session)
    actor = await user_repo.get_by_id(caller_id) if caller_id else None
    if actor is None:
        with contextlib.suppress(Exception):
            actor = await user_repo.get_by_subject(user_info.get("sub", ""))

    membership_repo = SqlSpaceMembershipRepository(session)
    memberships = await membership_repo.list_by_space(body.space_id)
    if actor is None or not can_write_document(
        actor, body.space_id, memberships, is_company_admin=company_admin
    ):
        raise HTTPException(
            status_code=403,
            detail="You must be an Editor or Admin to generate an AI draft in this space",
        )

    llm = AnthropicLLMProvider()
    content_markdown = await generate_draft(
        prompt=body.prompt,
        llm_provider=llm,
        previous_suggestion=body.previous_suggestion,
    )

    await write_audit(
        session,
        actor_type="user",
        actor_id=actor.id,
        action="ai_draft_requested",
        entity_type="space",
        entity_id=body.space_id,
        metadata={"company_id": str(company_id)},
    )

    return {"content_markdown": content_markdown}


class RevisionAssistRequest(BaseModel):
    content: str
    instruction: str = ""
    previous_suggestion: str | None = None

    @field_validator("content")
    @classmethod
    def content_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content must not be empty")
        return v


class RevisionAssistResponse(BaseModel):
    suggestion: str


@router.post("/documents/{document_id}/assist/revise")
async def revision_assist(
    document_id: UUID,
    body: RevisionAssistRequest,
    ctx: CompanyMemberContext,
    session: SessionDep,
) -> dict:
    _, company_id, caller_id = await _resolve_document_for_draft_write(document_id, ctx, session)

    llm = AnthropicLLMProvider()
    suggestion = await generate_revision(
        content=body.content,
        instruction=body.instruction,
        llm_provider=llm,
        previous_suggestion=body.previous_suggestion,
    )

    await write_audit(
        session,
        actor_type="user",
        actor_id=caller_id,
        action="ai_revision_requested",
        entity_type="document",
        entity_id=document_id,
        metadata={"company_id": str(company_id)},
    )

    return {"suggestion": suggestion}
