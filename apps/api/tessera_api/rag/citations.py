"""Citation generation: chunk id + document version reference."""

from __future__ import annotations

from typing import Any
from uuid import UUID


def build_citation(chunk_row: dict[str, Any]) -> dict[str, Any]:
    """Build a citation dict from a raw chunk search result row."""
    return {
        "chunk_id": str(chunk_row["id"]),
        "document_version_id": str(chunk_row["document_version_id"]),
        "quote": chunk_row["text"][:200],
        "score": float(chunk_row.get("score", 0.0)),
    }
