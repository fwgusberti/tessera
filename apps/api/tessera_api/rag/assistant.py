"""Assistant answer service: RAG with confidence threshold and dont_know fallback."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, field_validator


class AssistantResponse(BaseModel):
    answer: str
    citations: list[dict[str, Any]]
    confidence: float
    dont_know: bool = False

    @field_validator("citations")
    @classmethod
    def citations_required_when_answering(cls, v: list, info) -> list:
        if len(v) == 0:
            raise ValueError("A non-dont_know answer must have at least one citation")
        return v

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        return v


class DontKnowResponse(BaseModel):
    answer: None = None
    dont_know: bool = True
    suggested_owner: dict[str, Any] | None = None
    confidence: float

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        return v


async def generate_answer(
    query: str,
    chunks: list[dict[str, Any]],
    space_ids: list[UUID],
    confidence_threshold: float,
    llm_provider,
    session,
    history: list[dict[str, str]] | None = None,
) -> AssistantResponse | DontKnowResponse:
    """Generate a grounded answer with citations, or return dont_know if confidence is low."""
    from tessera_api.rag.citations import build_citation

    if not chunks:
        suggested_owner = await _get_suggested_owner(space_ids, session)
        return DontKnowResponse(confidence=0.0, suggested_owner=suggested_owner)

    best_score = max(float(c.get("score", 0)) for c in chunks)
    if best_score < confidence_threshold:
        suggested_owner = await _get_suggested_owner(space_ids, session)
        return DontKnowResponse(confidence=best_score, suggested_owner=suggested_owner)

    context_parts = [f"[{i + 1}] {c['text']}" for i, c in enumerate(chunks)]
    context = "\n\n".join(context_parts)

    system_prompt = (
        "You are a helpful assistant that answers questions based on provided documents. "
        "Always ground your answers in the provided context. "
        "If you cannot answer from the context, say so clearly. "
        "Cite sources using [1], [2], etc. notation."
    )

    prior_turns: list[dict[str, str]] = list(history) if history else []
    current_message = {
        "role": "user",
        "content": f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer based only on the context above:",
    }
    messages = [*prior_turns, current_message]

    answer_text = await llm_provider.complete(messages=messages, system=system_prompt)
    citations = [build_citation(c) for c in chunks[:5]]

    return AssistantResponse(
        answer=answer_text,
        citations=citations,
        confidence=best_score,
    )


async def _get_suggested_owner(space_ids: list[UUID], session) -> dict[str, Any] | None:
    if not space_ids:
        return None
    from tessera_api.adapters.repo import SqlSpaceRepository

    repo = SqlSpaceRepository(session)
    space = await repo.get_by_id(space_ids[0])
    if space is None:
        return None
    return {"space_id": str(space.id), "space_name": space.name}
