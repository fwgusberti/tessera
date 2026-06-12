"""Assistant answer endpoint."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["assistant"])


class AnswerRequest(BaseModel):
    query: str
    space_ids: list[UUID] | None = None
    language: str | None = None


@router.post("/assistant/answer")
async def answer(body: AnswerRequest, request: Request) -> dict:
    from tessera_api.adapters.audit import write_audit
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.embeddings import OllamaEmbeddingProvider
    from tessera_api.adapters.llm import AnthropicLLMProvider
    from tessera_api.adapters.repo import SqlSpaceRepository
    from tessera_api.auth.oidc import require_user
    from tessera_api.rag.assistant import generate_answer
    from tessera_api.rag.retrieval import acl_first_search
    from tessera_core.domain.entities import Confidentiality

    user_info = await require_user(request)

    embedding_provider = OllamaEmbeddingProvider()
    embeddings = await embedding_provider.embed([body.query])
    query_embedding = embeddings[0]

    async with get_db() as session:
        space_repo = SqlSpaceRepository(session)
        all_spaces = await space_repo.list_all()
        allowed_ids = [s.id for s in all_spaces]

        requested = body.space_ids or allowed_ids
        effective_ids = [sid for sid in requested if sid in set(allowed_ids)]

        # Use the first matching space's threshold or default 0.7
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
        response = await generate_answer(
            query=body.query,
            chunks=raw_results,
            space_ids=effective_ids,
            confidence_threshold=confidence_threshold,
            llm_provider=llm,
            session=session,
        )

        await write_audit(
            session,
            actor_type="user",
            actor_id=user_info.get("id", "00000000-0000-0000-0000-000000000000"),
            action="query",
            entity_type="assistant",
            entity_id="00000000-0000-0000-0000-000000000000",
        )

    return response.model_dump()
