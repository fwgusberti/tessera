"""Semantic search endpoint — ACL-first."""

from __future__ import annotations

from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    query: str
    space_ids: list[UUID] | None = None
    language: str | None = None
    top_k: int = 10


@router.post("/search")
async def search(body: SearchRequest, request: Request) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.embeddings import OllamaEmbeddingProvider
    from tessera_api.adapters.repo import SqlSpaceRepository
    from tessera_api.auth.oidc import require_user
    from tessera_api.rag.citations import build_citation
    from tessera_api.rag.retrieval import SearchResult, acl_first_search
    from tessera_core.domain.entities import Confidentiality

    await require_user(request)
    embedding_provider = OllamaEmbeddingProvider()
    try:
        embeddings = await embedding_provider.embed([body.query])
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Embedding service unavailable") from exc
    query_embedding = embeddings[0]

    async with get_db() as session:
        space_repo = SqlSpaceRepository(session)
        all_spaces = await space_repo.list_all()
        allowed_space_ids = [s.id for s in all_spaces]

        requested_space_ids = body.space_ids or allowed_space_ids
        effective_space_ids = [sid for sid in requested_space_ids if sid in set(allowed_space_ids)]

        raw_results = await acl_first_search(
            query_embedding=query_embedding,
            space_ids=effective_space_ids,
            max_confidentiality=Confidentiality.CONFIDENTIAL,
            session=session,
            top_k=body.top_k,
        )

    results = [
        SearchResult(
            document_id=r["document_id"],
            version_id=r["document_version_id"],
            chunk_id=r["id"],
            score=float(r.get("score", 0)),
            snippet=r["text"][:300],
            citation=build_citation(r),
        ).model_dump()
        for r in raw_results
    ]

    return {"results": results}
