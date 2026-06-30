"""Semantic search endpoint — ACL-first."""

from __future__ import annotations

from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tessera_api.adapters.database import SessionDep
from tessera_api.adapters.embeddings import OllamaEmbeddingProvider
from tessera_api.adapters.repo import SqlSpaceRepository
from tessera_api.auth.oidc import CompanyContext
from tessera_api.rag.citations import build_citation
from tessera_api.rag.retrieval import SearchResult, acl_first_search
from tessera_core.domain.entities import Confidentiality

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    query: str
    space_ids: list[UUID] | None = None
    language: str | None = None
    top_k: int = 10


@router.post("/search")
async def search(body: SearchRequest, ctx: CompanyContext, session: SessionDep) -> dict:
    _, company_id = ctx

    embedding_provider = OllamaEmbeddingProvider()
    try:
        embeddings = await embedding_provider.embed([body.query])
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Embedding service unavailable") from exc
    query_embedding = embeddings[0]

    space_repo = SqlSpaceRepository(session)
    company_spaces = await space_repo.list_by_company(company_id)
    allowed_space_ids = [s.id for s in company_spaces]

    if body.space_ids:
        allowed_set = set(allowed_space_ids)
        effective_space_ids = [sid for sid in body.space_ids if sid in allowed_set]
    else:
        effective_space_ids = allowed_space_ids

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
