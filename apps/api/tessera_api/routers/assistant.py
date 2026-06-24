"""Assistant answer endpoint."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, field_validator

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.database import get_db
from tessera_api.adapters.embeddings import OllamaEmbeddingProvider
from tessera_api.adapters.llm import AnthropicLLMProvider
from tessera_api.adapters.repo import SqlSpaceRepository
from tessera_api.auth.oidc import require_company_context
from tessera_api.rag.assistant import generate_answer
from tessera_api.rag.retrieval import acl_first_search
from tessera_core.domain.entities import Confidentiality

router = APIRouter(tags=["assistant"])


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

    @field_validator("content")
    @classmethod
    def content_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content must not be empty")
        return v


class AnswerRequest(BaseModel):
    query: str
    space_ids: list[UUID] | None = None
    language: str | None = None
    history: list[ChatHistoryMessage] | None = None


@router.post("/assistant/answer")
async def answer(body: AnswerRequest, request: Request) -> dict:
    user_info, company_id = await require_company_context(request)

    embedding_provider = OllamaEmbeddingProvider()
    embeddings = await embedding_provider.embed([body.query])
    query_embedding = embeddings[0]

    async with get_db() as session:
        space_repo = SqlSpaceRepository(session)
        company_spaces = await space_repo.list_by_company(company_id)
        allowed_ids = [s.id for s in company_spaces]

        if body.space_ids:
            allowed_set = set(allowed_ids)
            effective_ids = [sid for sid in body.space_ids if sid in allowed_set]
        else:
            effective_ids = allowed_ids

        confidence_threshold = 0.7
        if effective_ids:
            space = await space_repo.get_by_id(effective_ids[0])
            if space:
                confidence_threshold = space.confidence_threshold

        raw_results = await acl_first_search(
            query_embedding=query_embedding,
            space_ids=effective_ids,
            max_confidentiality=Confidentiality.CONFIDENTIAL,
            session=session,
            top_k=10,
        )

        llm = AnthropicLLMProvider()
        history = [{"role": m.role, "content": m.content} for m in (body.history or [])]
        response = await generate_answer(
            query=body.query,
            chunks=raw_results,
            space_ids=effective_ids,
            confidence_threshold=confidence_threshold,
            llm_provider=llm,
            session=session,
            history=history or None,
        )

        user_id_str = user_info.get("id") or user_info.get("sub")
        actor_id = UUID(user_id_str) if user_id_str else UUID(int=0)
        await write_audit(
            session,
            actor_type="user",
            actor_id=actor_id,
            action="query",
            entity_type="assistant",
            entity_id=UUID(int=0),
            metadata={"company_id": str(company_id)},
        )

    return response.model_dump()
