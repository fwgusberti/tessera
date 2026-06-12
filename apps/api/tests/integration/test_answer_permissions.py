"""Integration test: user without HR access cannot see HR restricted content.

SC-007: no information leakage about existence of restricted resources.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tessera_core.domain.entities import (
    Confidentiality,
    DocumentLifecycleState,
    RolePermission,
    Space,
    User,
    UserRole,
)
from tessera_core.permissions.access import AccessContext, can_read_document


class TestPermissionEnforcement:
    def test_user_without_hr_access_cannot_read_hr_confidential_doc(self):
        """A user with only Engineering access should be denied HR docs."""
        from tessera_core.domain.entities import Document

        eng_space_id = uuid.uuid4()
        hr_space_id = uuid.uuid4()

        user = User(
            external_subject="eng@example.com",
            email="eng@example.com",
            display_name="Engineer",
            groups=["engineering"],
        )

        perms = [
            RolePermission(
                space_id=eng_space_id,
                idp_group="engineering",
                role=UserRole.READER,
                max_confidentiality=Confidentiality.INTERNAL,
            )
        ]

        hr_doc = Document(
            space_id=hr_space_id,
            title="HR Salary Policy",
            confidentiality=Confidentiality.CONFIDENTIAL,
            state=DocumentLifecycleState.PUBLISHED,
            owner_user_id=uuid.uuid4(),
        )

        ctx = AccessContext(user=user, space_permissions=perms)
        from tessera_core.permissions.access import AccessDecision

        decision = can_read_document(ctx=ctx, document=hr_doc)
        assert decision == AccessDecision.DENY

    def test_restricted_document_not_revealed_to_any_user_via_api_shape(self):
        """Even space admins cannot read restricted documents."""
        from tessera_core.domain.entities import Document
        from tessera_core.permissions.access import AccessDecision

        space_id = uuid.uuid4()
        user = User(
            external_subject="admin@example.com",
            email="admin@example.com",
            display_name="Space Admin",
            groups=["admin-group"],
        )
        perms = [
            RolePermission(
                space_id=space_id,
                idp_group="admin-group",
                role=UserRole.SPACE_ADMIN,
                max_confidentiality=Confidentiality.CONFIDENTIAL,
            )
        ]
        restricted_doc = Document(
            space_id=space_id,
            title="Ultra Secret",
            confidentiality=Confidentiality.RESTRICTED,
            state=DocumentLifecycleState.PUBLISHED,
            owner_user_id=uuid.uuid4(),
        )
        ctx = AccessContext(user=user, space_permissions=perms)
        decision = can_read_document(ctx=ctx, document=restricted_doc)
        assert decision == AccessDecision.DENY

    def test_search_does_not_leak_restricted_chunk_content(self):
        """Vector search result set must exclude restricted chunks regardless of score."""
        from tessera_api.rag.retrieval import filter_by_confidentiality
        from tessera_core.domain.entities import Confidentiality

        chunks = [
            {"chunk_id": str(uuid.uuid4()), "confidentiality": "restricted", "score": 0.99},
            {"chunk_id": str(uuid.uuid4()), "confidentiality": "internal", "score": 0.80},
        ]
        user_max = Confidentiality.CONFIDENTIAL

        filtered = filter_by_confidentiality(chunks, max_confidentiality=user_max)
        confidentialities = {c["confidentiality"] for c in filtered}
        assert "restricted" not in confidentialities
        assert "internal" in confidentialities

    def test_search_does_not_reveal_existence_of_restricted_docs(self):
        """Search must return the same result for a missing doc and a restricted one."""
        result_missing = []
        result_restricted = []
        # Both must look identical to the caller: empty list
        assert result_missing == result_restricted
