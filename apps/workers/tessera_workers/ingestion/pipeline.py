"""Ingestion pipeline: normalize artifact → markdown + frontmatter → DocumentVersion."""

from __future__ import annotations

import re
import uuid
from uuid import UUID

from tessera_core.domain.entities import (
    Document,
    DocumentLifecycleState,
    DocumentVersion,
    Space,
)
from tessera_core.ports.connector import ArtifactRecord

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _detect_language(text: str) -> str:
    try:
        from langdetect import detect

        lang = detect(text)
        if lang == "pt":
            return "pt-BR"
        return lang
    except Exception:
        return "pt-BR"


def _extract_title(content: str, path: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return path.split("/")[-1].replace(".md", "").replace("-", " ").replace("_", " ").title()


def ingest_artifact(
    artifact: ArtifactRecord,
    space: Space,
    connector_id: UUID,
    version_number: int = 1,
    document_id: UUID | None = None,
) -> DocumentVersion:
    """Normalize a raw artifact into an immutable DocumentVersion."""
    content = artifact.raw_content or ""

    # Strip existing frontmatter if present
    body = _FRONTMATTER_RE.sub("", content).strip()
    title = _extract_title(body, artifact.path)
    language = _detect_language(body)

    frontmatter: dict = {
        "title": title,
        "sector": space.sector,
        "language": language,
        "source_path": artifact.path,
        "content_hash": artifact.content_hash,
        "source_version": artifact.source_version,
    }

    # Canonical markdown = frontmatter block + body
    fm_lines = "\n".join(f"{k}: {v}" for k, v in frontmatter.items())
    canonical_markdown = f"---\n{fm_lines}\n---\n\n{body}"

    return DocumentVersion(
        id=uuid.uuid4(),
        document_id=document_id or uuid.uuid4(),
        version_number=version_number,
        content_markdown=canonical_markdown,
        frontmatter=frontmatter,
        source_artifact_id=artifact.external_id if hasattr(artifact, "id") else None,
    )


def classify_document_state(
    version: DocumentVersion,
    owner_user_id: UUID | None,
) -> DocumentLifecycleState:
    """Return the initial lifecycle state for a freshly ingested document."""
    if owner_user_id is None:
        return DocumentLifecycleState.NO_OWNER
    return DocumentLifecycleState.INGESTED
