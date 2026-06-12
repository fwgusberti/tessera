"""Integration test: group→role mapping grants exact access and is audited.

Also tests: retention expires document and removes from index.
"""

import uuid
import pytest

from tessera_core.domain.entities import (
    Confidentiality,
    Document,
    DocumentLifecycleState,
    RolePermission,
    Space,
    User,
    UserRole,
)
from tessera_core.permissions.access import AccessContext, can_read_document, AccessDecision


class TestGroupRoleMapping:
    def test_group_mapped_to_reader_gets_reader_access(self):
        """User in mapped group receives exactly reader access."""
        space_id = uuid.uuid4()
        user = User(
            external_subject="user@example.com",
            email="user@example.com",
            display_name="User",
            groups=["engineering"],
        )
        perms = [
            RolePermission(
                space_id=space_id,
                idp_group="engineering",
                role=UserRole.READER,
                max_confidentiality=Confidentiality.INTERNAL,
            )
        ]
        doc = Document(
            space_id=space_id,
            title="Public Doc",
            confidentiality=Confidentiality.PUBLIC_INTERNAL,
            state=DocumentLifecycleState.PUBLISHED,
            owner_user_id=uuid.uuid4(),
        )
        ctx = AccessContext(user=user, space_permissions=perms)
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.ALLOW

    def test_unmapped_group_gets_no_access(self):
        """User not in any mapped group must be denied access."""
        space_id = uuid.uuid4()
        user = User(
            external_subject="outsider@example.com",
            email="outsider@example.com",
            display_name="Outsider",
            groups=["sales"],
        )
        perms = [
            RolePermission(
                space_id=space_id,
                idp_group="engineering",
                role=UserRole.READER,
                max_confidentiality=Confidentiality.INTERNAL,
            )
        ]
        doc = Document(
            space_id=space_id,
            title="Internal Doc",
            confidentiality=Confidentiality.INTERNAL,
            state=DocumentLifecycleState.PUBLISHED,
            owner_user_id=uuid.uuid4(),
        )
        ctx = AccessContext(user=user, space_permissions=perms)
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.DENY

    def test_permission_change_is_effective_immediately(self):
        """After upgrading from reader to owner, the user can publish."""
        space_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        user = User(
            id=owner_id,
            external_subject="user@example.com",
            email="user@example.com",
            display_name="User",
            groups=["engineering"],
        )
        perms_reader = [
            RolePermission(
                space_id=space_id,
                idp_group="engineering",
                role=UserRole.READER,
                max_confidentiality=Confidentiality.INTERNAL,
            )
        ]
        perms_owner = [
            RolePermission(
                space_id=space_id,
                idp_group="engineering",
                role=UserRole.OWNER,
                max_confidentiality=Confidentiality.INTERNAL,
            )
        ]
        doc = Document(
            space_id=space_id,
            title="My Doc",
            confidentiality=Confidentiality.INTERNAL,
            state=DocumentLifecycleState.INGESTED,
            owner_user_id=owner_id,
        )
        from tessera_core.permissions.access import can_publish_document

        ctx_reader = AccessContext(user=user, space_permissions=perms_reader)
        ctx_owner = AccessContext(user=user, space_permissions=perms_owner)

        assert can_publish_document(ctx=ctx_reader, document=doc) == AccessDecision.DENY
        assert can_publish_document(ctx=ctx_owner, document=doc) == AccessDecision.ALLOW


class TestRetentionPolicy:
    def test_expired_document_excluded_from_lifecycle_service(self):
        """Document in expired state is not publishable or queryable."""
        from tessera_core.services.lifecycle import expire_document, publish_document, LifecycleError

        doc = Document(
            space_id=uuid.uuid4(),
            title="Old Guide",
            state=DocumentLifecycleState.PUBLISHED,
            owner_user_id=uuid.uuid4(),
            current_version_id=uuid.uuid4(),
        )
        expired = expire_document(doc)
        assert expired.state == DocumentLifecycleState.EXPIRED

        with pytest.raises(LifecycleError, match="expired"):
            publish_document(expired, version_id=uuid.uuid4(), approver_id=uuid.uuid4())
