from __future__ import annotations

from uuid import UUID

from tessera_core.domain.entities import Document, DocumentLifecycleState


class LifecycleError(Exception):
    pass


def assign_owner(document: Document, owner_id: UUID) -> Document:
    if document.state == DocumentLifecycleState.EXPIRED:
        raise LifecycleError("Cannot assign owner to an expired document")
    return document.model_copy(update={"owner_user_id": owner_id})


def transition_to_no_owner(document: Document) -> Document:
    if document.owner_user_id is not None:
        raise LifecycleError("Document already has an owner")
    if document.state != DocumentLifecycleState.INGESTED:
        raise LifecycleError(
            f"Cannot transition to no-owner from state {document.state}"
        )
    return document.model_copy(update={"state": DocumentLifecycleState.NO_OWNER})


def publish_document(document: Document, version_id: UUID, approver_id: UUID) -> Document:
    if document.state == DocumentLifecycleState.EXPIRED:
        raise LifecycleError("Cannot publish an expired document")
    if document.owner_user_id is None:
        raise LifecycleError("Cannot publish a document without an owner")
    allowed_states = {
        DocumentLifecycleState.INGESTED,
        DocumentLifecycleState.OUTDATED,
    }
    if document.state not in allowed_states:
        raise LifecycleError(
            f"Cannot publish document in state {document.state}"
        )
    return document.model_copy(
        update={
            "state": DocumentLifecycleState.PUBLISHED,
            "current_version_id": version_id,
        }
    )


def mark_outdated(document: Document) -> Document:
    if document.state != DocumentLifecycleState.PUBLISHED:
        raise LifecycleError(
            f"Cannot mark document outdated from state {document.state}"
        )
    return document.model_copy(update={"state": DocumentLifecycleState.OUTDATED})


def expire_document(document: Document) -> Document:
    allowed = {DocumentLifecycleState.PUBLISHED, DocumentLifecycleState.OUTDATED}
    if document.state not in allowed:
        raise LifecycleError(
            f"Cannot expire document in state {document.state}"
        )
    return document.model_copy(update={"state": DocumentLifecycleState.EXPIRED})


class DocumentLifecycleService:
    """Convenience wrapper around the pure lifecycle functions."""

    assign_owner = staticmethod(assign_owner)
    transition_to_no_owner = staticmethod(transition_to_no_owner)
    publish = staticmethod(publish_document)
    mark_outdated = staticmethod(mark_outdated)
    expire = staticmethod(expire_document)
