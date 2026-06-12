"""Adversarial cross-sector/role/agent permission test suite (SC-007).

Tests both human API and MCP code paths.
"""

import uuid
import pytest

from tessera_core.domain.entities import (
    Confidentiality,
    Document,
    DocumentLifecycleState,
    RolePermission,
    User,
    UserRole,
)
from tessera_core.permissions.access import AccessContext, can_read_document, AccessDecision


ENGINEERING_SPACE = uuid.uuid4()
HR_SPACE = uuid.uuid4()


def make_user(groups: list[str], is_admin: bool = False) -> User:
    return User(
        external_subject=str(uuid.uuid4()),
        email=f"user-{uuid.uuid4()}@example.com",
        display_name="Test User",
        groups=groups,
        is_admin=is_admin,
    )


def eng_perms() -> list[RolePermission]:
    return [
        RolePermission(
            space_id=ENGINEERING_SPACE,
            idp_group="engineering",
            role=UserRole.READER,
            max_confidentiality=Confidentiality.CONFIDENTIAL,
        )
    ]


def hr_perms() -> list[RolePermission]:
    return [
        RolePermission(
            space_id=HR_SPACE,
            idp_group="hr",
            role=UserRole.READER,
            max_confidentiality=Confidentiality.CONFIDENTIAL,
        )
    ]


class TestCrossSectorLeakage:
    def test_engineering_user_cannot_read_hr_internal_document(self):
        user = make_user(groups=["engineering"])
        ctx = AccessContext(user=user, space_permissions=eng_perms())
        doc = Document(
            space_id=HR_SPACE,
            title="HR Policy",
            confidentiality=Confidentiality.INTERNAL,
            state=DocumentLifecycleState.PUBLISHED,
            owner_user_id=uuid.uuid4(),
        )
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.DENY

    def test_engineering_user_cannot_read_hr_confidential_document(self):
        user = make_user(groups=["engineering"])
        ctx = AccessContext(user=user, space_permissions=eng_perms())
        doc = Document(
            space_id=HR_SPACE,
            title="HR Salary",
            confidentiality=Confidentiality.CONFIDENTIAL,
            state=DocumentLifecycleState.PUBLISHED,
            owner_user_id=uuid.uuid4(),
        )
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.DENY

    def test_engineering_user_cannot_read_hr_restricted_document(self):
        user = make_user(groups=["engineering"])
        ctx = AccessContext(user=user, space_permissions=eng_perms())
        doc = Document(
            space_id=HR_SPACE,
            title="HR Restricted Data",
            confidentiality=Confidentiality.RESTRICTED,
            state=DocumentLifecycleState.PUBLISHED,
            owner_user_id=uuid.uuid4(),
        )
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.DENY

    def test_hr_user_cannot_read_engineering_restricted_document(self):
        user = make_user(groups=["hr"])
        all_perms = hr_perms()
        ctx = AccessContext(user=user, space_permissions=all_perms)
        doc = Document(
            space_id=ENGINEERING_SPACE,
            title="Secret Algorithm",
            confidentiality=Confidentiality.RESTRICTED,
            state=DocumentLifecycleState.PUBLISHED,
            owner_user_id=uuid.uuid4(),
        )
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.DENY

    def test_global_admin_cannot_read_restricted_document(self):
        """Even global admins cannot bypass restricted classification."""
        user = make_user(groups=[], is_admin=True)
        ctx = AccessContext(user=user, space_permissions=[])
        doc = Document(
            space_id=ENGINEERING_SPACE,
            title="Top Secret",
            confidentiality=Confidentiality.RESTRICTED,
            state=DocumentLifecycleState.PUBLISHED,
            owner_user_id=uuid.uuid4(),
        )
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.DENY


class TestAgentScopeLeak:
    def test_agent_with_eng_scope_cannot_access_hr_space(self):
        from tessera_mcp.tools.search import filter_scoped_spaces
        from tessera_core.domain.entities import AgentCredential

        credential = AgentCredential(
            name="eng-agent",
            token_hash="fake",
            scoped_space_ids=[ENGINEERING_SPACE],
            max_confidentiality=Confidentiality.INTERNAL,
        )
        effective = filter_scoped_spaces(credential=credential, requested_space_ids=[HR_SPACE])
        assert len(effective) == 0

    def test_agent_restricted_always_excluded(self):
        from tessera_mcp.tools.search import filter_agent_results
        from tessera_core.domain.entities import AgentCredential

        credential = AgentCredential(
            name="full-agent",
            token_hash="fake",
            scoped_space_ids=[ENGINEERING_SPACE, HR_SPACE],
            max_confidentiality=Confidentiality.RESTRICTED,
        )
        chunks = [{"chunk_id": str(uuid.uuid4()), "confidentiality": "restricted"}]
        assert filter_agent_results(chunks, credential=credential) == []
