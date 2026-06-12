"""FAILING tests for document lifecycle state machine — TDD."""

import uuid
import pytest

from tessera_core.domain.entities import Document, DocumentLifecycleState, Confidentiality
from tessera_core.services.lifecycle import (
    DocumentLifecycleService,
    LifecycleError,
    assign_owner,
    expire_document,
    mark_outdated,
    publish_document,
    transition_to_no_owner,
)


def make_doc(**kwargs) -> Document:
    defaults = dict(
        space_id=uuid.uuid4(),
        title="Test",
        confidentiality=Confidentiality.INTERNAL,
        state=DocumentLifecycleState.INGESTED,
    )
    defaults.update(kwargs)
    return Document(**defaults)


class TestAssignOwner:
    def test_assigns_owner_to_ingested_document(self):
        doc = make_doc(state=DocumentLifecycleState.INGESTED)
        owner_id = uuid.uuid4()
        updated = assign_owner(doc, owner_id)
        assert updated.owner_user_id == owner_id

    def test_assigns_owner_to_no_owner_document(self):
        doc = make_doc(state=DocumentLifecycleState.NO_OWNER)
        owner_id = uuid.uuid4()
        updated = assign_owner(doc, owner_id)
        assert updated.owner_user_id == owner_id

    def test_state_does_not_change_on_assign(self):
        doc = make_doc(state=DocumentLifecycleState.INGESTED)
        updated = assign_owner(doc, uuid.uuid4())
        assert updated.state == DocumentLifecycleState.INGESTED

    def test_cannot_assign_owner_to_expired_document(self):
        doc = make_doc(state=DocumentLifecycleState.EXPIRED)
        with pytest.raises(LifecycleError, match="expired"):
            assign_owner(doc, uuid.uuid4())


class TestTransitionToNoOwner:
    def test_ingested_without_owner_transitions_to_no_owner(self):
        doc = make_doc(state=DocumentLifecycleState.INGESTED, owner_user_id=None)
        updated = transition_to_no_owner(doc)
        assert updated.state == DocumentLifecycleState.NO_OWNER

    def test_raises_if_document_already_has_owner(self):
        doc = make_doc(state=DocumentLifecycleState.INGESTED, owner_user_id=uuid.uuid4())
        with pytest.raises(LifecycleError, match="owner"):
            transition_to_no_owner(doc)

    def test_raises_if_document_not_ingested(self):
        doc = make_doc(state=DocumentLifecycleState.PUBLISHED)
        with pytest.raises(LifecycleError):
            transition_to_no_owner(doc)


class TestPublishDocument:
    def test_ingested_document_with_owner_can_be_published(self):
        owner_id = uuid.uuid4()
        version_id = uuid.uuid4()
        doc = make_doc(state=DocumentLifecycleState.INGESTED, owner_user_id=owner_id)
        updated = publish_document(doc, version_id=version_id, approver_id=owner_id)
        assert updated.state == DocumentLifecycleState.PUBLISHED
        assert updated.current_version_id == version_id

    def test_no_owner_document_cannot_be_published(self):
        doc = make_doc(state=DocumentLifecycleState.NO_OWNER, owner_user_id=None)
        with pytest.raises(LifecycleError, match="owner"):
            publish_document(doc, version_id=uuid.uuid4(), approver_id=uuid.uuid4())

    def test_outdated_document_can_be_re_published(self):
        owner_id = uuid.uuid4()
        version_id = uuid.uuid4()
        doc = make_doc(
            state=DocumentLifecycleState.OUTDATED,
            owner_user_id=owner_id,
            current_version_id=uuid.uuid4(),
        )
        updated = publish_document(doc, version_id=version_id, approver_id=owner_id)
        assert updated.state == DocumentLifecycleState.PUBLISHED
        assert updated.current_version_id == version_id

    def test_expired_document_cannot_be_published(self):
        doc = make_doc(state=DocumentLifecycleState.EXPIRED, owner_user_id=uuid.uuid4())
        with pytest.raises(LifecycleError, match="expired"):
            publish_document(doc, version_id=uuid.uuid4(), approver_id=uuid.uuid4())


class TestMarkOutdated:
    def test_published_document_can_be_marked_outdated(self):
        doc = make_doc(
            state=DocumentLifecycleState.PUBLISHED,
            owner_user_id=uuid.uuid4(),
            current_version_id=uuid.uuid4(),
        )
        updated = mark_outdated(doc)
        assert updated.state == DocumentLifecycleState.OUTDATED

    def test_non_published_document_cannot_be_marked_outdated(self):
        doc = make_doc(state=DocumentLifecycleState.INGESTED)
        with pytest.raises(LifecycleError):
            mark_outdated(doc)

    def test_current_version_preserved_when_marked_outdated(self):
        version_id = uuid.uuid4()
        doc = make_doc(
            state=DocumentLifecycleState.PUBLISHED,
            owner_user_id=uuid.uuid4(),
            current_version_id=version_id,
        )
        updated = mark_outdated(doc)
        assert updated.current_version_id == version_id


class TestExpireDocument:
    def test_published_document_can_expire(self):
        doc = make_doc(
            state=DocumentLifecycleState.PUBLISHED,
            owner_user_id=uuid.uuid4(),
            current_version_id=uuid.uuid4(),
        )
        updated = expire_document(doc)
        assert updated.state == DocumentLifecycleState.EXPIRED

    def test_outdated_document_can_expire(self):
        doc = make_doc(
            state=DocumentLifecycleState.OUTDATED,
            owner_user_id=uuid.uuid4(),
            current_version_id=uuid.uuid4(),
        )
        updated = expire_document(doc)
        assert updated.state == DocumentLifecycleState.EXPIRED

    def test_ingested_document_cannot_expire(self):
        doc = make_doc(state=DocumentLifecycleState.INGESTED)
        with pytest.raises(LifecycleError):
            expire_document(doc)
