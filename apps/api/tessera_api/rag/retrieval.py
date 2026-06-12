"""ACL-first retrieval: resolve permissions → filter space/confidentiality BEFORE ANN."""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from tessera_core.domain.entities import Confidentiality


class SearchResult(BaseModel):
    document_id: UUID
    version_id: UUID
    chunk_id: UUID
    score: float
    snippet: str
    citation: dict[str, Any]


def filter_published(results: list[dict]) -> list[dict]:
    """Keep only results where state == 'published'."""
    return [r for r in results if r.get("state") == "published"]


def filter_by_confidentiality(
    results: list[dict],
    max_confidentiality: Confidentiality,
) -> list[dict]:
    """Remove results whose confidentiality exceeds the user's max level.

    Restricted documents are always excluded regardless of max_confidentiality.
    """
    max_level = max_confidentiality.level()
    return [
        r
        for r in results
        if Confidentiality(r["confidentiality"]) != Confidentiality.RESTRICTED
        and Confidentiality(r["confidentiality"]).level() <= max_level
    ]


async def acl_first_search(
    query_embedding: list[float],
    space_ids: list[UUID],
    max_confidentiality: Confidentiality,
    session,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Execute ACL-filtered vector search. Permissions resolved BEFORE ANN."""
    from tessera_api.adapters.repo import SqlChunkRepository

    repo = SqlChunkRepository(session)
    raw_results = await repo.search(
        query_embedding=query_embedding,
        space_ids=space_ids,
        max_confidentiality_level=max_confidentiality.level(),
        top_k=top_k,
    )
    return raw_results
