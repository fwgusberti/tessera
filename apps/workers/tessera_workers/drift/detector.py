"""Drift detection pipeline: content_hash change → semantic diff → UpdateProposal."""

from __future__ import annotations

import difflib
import uuid
from uuid import UUID

from tessera_core.domain.entities import ProposalState, SourceArtifact, UpdateProposal


def detect_drift(old_artifact: SourceArtifact, new_artifact: SourceArtifact) -> bool:
    """Return True if the source artifact's content has changed."""
    return old_artifact.content_hash != new_artifact.content_hash


def compute_patch(old_markdown: str, new_markdown: str) -> str:
    """Compute a unified diff patch between old and new markdown content."""
    old_lines = old_markdown.splitlines(keepends=True)
    new_lines = new_markdown.splitlines(keepends=True)
    diff = list(difflib.unified_diff(old_lines, new_lines, fromfile="old", tofile="new"))
    return "".join(diff) if diff else new_markdown


def create_proposal(
    document_id: UUID,
    source_artifact_id: UUID,
    old_markdown: str,
    new_markdown: str,
    drift_score: float,
    summary: str,
) -> UpdateProposal:
    """Create a pending UpdateProposal from a detected drift."""
    patch = compute_patch(old_markdown, new_markdown)
    return UpdateProposal(
        id=uuid.uuid4(),
        document_id=document_id,
        source_artifact_id=source_artifact_id,
        proposed_markdown_patch=patch or new_markdown,
        state=ProposalState.PENDING,
        drift_score=drift_score,
        summary=summary,
    )
