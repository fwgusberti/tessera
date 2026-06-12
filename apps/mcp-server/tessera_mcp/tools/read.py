"""MCP read_document tool."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ReadDocumentResult(BaseModel):
    document_id: UUID
    title: str
    markdown: str
    frontmatter: dict[str, Any]
    version_number: int
    citations_supported: bool = True


class NotFoundError(Exception):
    error: str = "not_found"

    def __init__(self, document_id: UUID) -> None:
        self.document_id = document_id
        super().__init__(f"Document {document_id} not found")
