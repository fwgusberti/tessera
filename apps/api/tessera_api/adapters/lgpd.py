"""LGPD compliance helpers: data minimization, subject rights, version redaction (FR-025a)."""

from __future__ import annotations

from uuid import UUID


async def export_subject_data(user_id: UUID, session) -> dict:
    """Export all data held about a data subject (LGPD right of access)."""
    from tessera_api.adapters.repo import SqlUserRepository, SqlAuditRepository

    user_repo = SqlUserRepository(session)
    audit_repo = SqlAuditRepository(session)

    user = await user_repo.get_by_id(user_id)
    audit_records = await audit_repo.list_for_entity("user", user_id)

    return {
        "user": user.model_dump() if user else None,
        "audit_trail": [r.model_dump() for r in audit_records],
    }


async def erase_subject_data(user_id: UUID, session) -> None:
    """Erasure right: anonymize user PII while preserving audit integrity (LGPD Art. 18).

    Audit records are retained (compliance obligation) but PII fields are redacted.
    """
    from sqlalchemy import update, text
    from tessera_api.adapters.models import UserModel

    await session.execute(
        update(UserModel)
        .where(UserModel.id == user_id)
        .values(
            email="[redacted]@erased.tessera",
            display_name="[Deleted User]",
            external_subject=f"erased:{user_id}",
            groups=[],
        )
    )


async def redact_document_version(version_id: UUID, session) -> None:
    """Redact a document version's content (e.g., PII found post-ingestion) (FR-025a)."""
    from sqlalchemy import update
    from tessera_api.adapters.models import DocumentVersionModel

    await session.execute(
        update(DocumentVersionModel)
        .where(DocumentVersionModel.id == version_id)
        .values(
            content_markdown="[Content redacted for LGPD compliance]",
            frontmatter={"redacted": True},
        )
    )
