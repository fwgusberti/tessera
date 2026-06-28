"""FAILING unit tests for core.permissions access-decision engine.

TDD: these tests must FAIL before permissions.py is implemented.
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
from tessera_core.permissions.access import (
    AccessContext,
    AccessDecision,
    can_read_document,
    can_publish_document,
    can_approve_proposal,
    can_admin_space,
    resolve_user_role,
)


SPACE_ID = uuid.uuid4()
OTHER_SPACE_ID = uuid.uuid4()


def make_user(groups: list[str], is_admin: bool = False) -> User:
    return User(
        external_subject=str(uuid.uuid4()),
        email="test@example.com",
        display_name="Test User",
        groups=groups,
        is_admin=is_admin,
    )


def make_permission(
    space_id=SPACE_ID,
    idp_group="engineering",
    role=UserRole.READER,
    max_confidentiality=Confidentiality.INTERNAL,
) -> RolePermission:
    return RolePermission(
        space_id=space_id,
        idp_group=idp_group,
        role=role,
        max_confidentiality=max_confidentiality,
    )


def make_document(
    space_id=SPACE_ID,
    confidentiality=Confidentiality.INTERNAL,
    state=DocumentLifecycleState.PUBLISHED,
    owner_user_id=None,
) -> Document:
    return Document(
        space_id=space_id,
        title="Test Document",
        confidentiality=confidentiality,
        state=state,
        owner_user_id=owner_user_id,
    )


class TestResolveUserRole:
    def test_returns_none_when_user_has_no_groups_in_space(self):
        user = make_user(groups=["other-group"])
        perms = [make_permission(idp_group="engineering", role=UserRole.READER)]
        role = resolve_user_role(user=user, space_id=SPACE_ID, permissions=perms)
        assert role is None

    def test_returns_highest_role_when_user_in_multiple_groups(self):
        user = make_user(groups=["engineering", "eng-leads"])
        perms = [
            make_permission(idp_group="engineering", role=UserRole.READER),
            make_permission(idp_group="eng-leads", role=UserRole.SPACE_ADMIN),
        ]
        role = resolve_user_role(user=user, space_id=SPACE_ID, permissions=perms)
        assert role == UserRole.SPACE_ADMIN

    def test_returns_role_for_exact_group_match(self):
        user = make_user(groups=["engineering"])
        perms = [make_permission(idp_group="engineering", role=UserRole.CONTRIBUTOR)]
        role = resolve_user_role(user=user, space_id=SPACE_ID, permissions=perms)
        assert role == UserRole.CONTRIBUTOR

    def test_ignores_permissions_from_other_spaces(self):
        user = make_user(groups=["engineering"])
        perms = [make_permission(space_id=OTHER_SPACE_ID, idp_group="engineering", role=UserRole.OWNER)]
        role = resolve_user_role(user=user, space_id=SPACE_ID, permissions=perms)
        assert role is None

    def test_global_admin_is_not_resolved_here(self):
        """Global admin flag is handled at AccessContext level, not role resolution."""
        user = make_user(groups=[], is_admin=True)
        perms = []
        role = resolve_user_role(user=user, space_id=SPACE_ID, permissions=perms)
        assert role is None


class TestCanReadDocument:
    def test_reader_can_read_internal_published_document(self):
        user = make_user(groups=["engineering"])
        perms = [make_permission(role=UserRole.READER, max_confidentiality=Confidentiality.INTERNAL)]
        doc = make_document(confidentiality=Confidentiality.INTERNAL)
        ctx = AccessContext(user=user, space_permissions=perms)
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.ALLOW

    def test_reader_cannot_read_confidential_if_max_is_internal(self):
        user = make_user(groups=["engineering"])
        perms = [make_permission(role=UserRole.READER, max_confidentiality=Confidentiality.INTERNAL)]
        doc = make_document(confidentiality=Confidentiality.CONFIDENTIAL)
        ctx = AccessContext(user=user, space_permissions=perms)
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.DENY

    def test_nobody_can_read_restricted_document_via_normal_rbac(self):
        """Restricted documents require special handling; regular roles cannot read them."""
        user = make_user(groups=["engineering"])
        perms = [make_permission(role=UserRole.SPACE_ADMIN, max_confidentiality=Confidentiality.CONFIDENTIAL)]
        doc = make_document(confidentiality=Confidentiality.RESTRICTED)
        ctx = AccessContext(user=user, space_permissions=perms)
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.DENY

    def test_user_without_role_cannot_read_document(self):
        user = make_user(groups=["other-group"])
        perms = [make_permission(idp_group="engineering")]
        doc = make_document()
        ctx = AccessContext(user=user, space_permissions=perms)
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.DENY

    def test_unpublished_document_is_not_readable_by_reader(self):
        user = make_user(groups=["engineering"])
        perms = [make_permission(role=UserRole.READER)]
        doc = make_document(state=DocumentLifecycleState.INGESTED)
        ctx = AccessContext(user=user, space_permissions=perms)
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.DENY

    def test_contributor_can_read_ingested_document_in_same_space(self):
        user = make_user(groups=["engineering"])
        perms = [make_permission(role=UserRole.CONTRIBUTOR)]
        doc = make_document(state=DocumentLifecycleState.INGESTED)
        ctx = AccessContext(user=user, space_permissions=perms)
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.ALLOW

    def test_cannot_read_document_from_other_space(self):
        user = make_user(groups=["engineering"])
        perms = [make_permission(space_id=SPACE_ID, role=UserRole.READER)]
        doc = make_document(space_id=OTHER_SPACE_ID)
        ctx = AccessContext(user=user, space_permissions=perms)
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.DENY

    def test_company_admin_can_read_any_non_restricted_document(self):
        user = make_user(groups=[])
        doc = make_document(confidentiality=Confidentiality.CONFIDENTIAL)
        ctx = AccessContext(user=user, space_permissions=[], is_company_admin=True)
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.ALLOW

    def test_company_admin_cannot_read_restricted_document(self):
        user = make_user(groups=[])
        doc = make_document(confidentiality=Confidentiality.RESTRICTED)
        ctx = AccessContext(user=user, space_permissions=[], is_company_admin=True)
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.DENY

    def test_global_is_admin_does_not_grant_read(self):
        """The legacy global flag confers no read authority over company data."""
        user = make_user(groups=[], is_admin=True)
        doc = make_document(confidentiality=Confidentiality.CONFIDENTIAL)
        ctx = AccessContext(user=user, space_permissions=[], is_company_admin=False)
        assert can_read_document(ctx=ctx, document=doc) == AccessDecision.DENY


class TestCanPublishDocument:
    def test_owner_can_publish(self):
        owner_id = uuid.uuid4()
        user = make_user(groups=["engineering"])
        user_with_id = user.model_copy(update={"id": owner_id})
        perms = [make_permission(role=UserRole.OWNER)]
        doc = make_document(owner_user_id=owner_id, state=DocumentLifecycleState.INGESTED)
        ctx = AccessContext(user=user_with_id, space_permissions=perms)
        assert can_publish_document(ctx=ctx, document=doc) == AccessDecision.ALLOW

    def test_space_admin_can_publish(self):
        user = make_user(groups=["engineering"])
        perms = [make_permission(role=UserRole.SPACE_ADMIN)]
        doc = make_document(state=DocumentLifecycleState.INGESTED)
        ctx = AccessContext(user=user, space_permissions=perms)
        assert can_publish_document(ctx=ctx, document=doc) == AccessDecision.ALLOW

    def test_reader_cannot_publish(self):
        user = make_user(groups=["engineering"])
        perms = [make_permission(role=UserRole.READER)]
        doc = make_document(state=DocumentLifecycleState.INGESTED)
        ctx = AccessContext(user=user, space_permissions=perms)
        assert can_publish_document(ctx=ctx, document=doc) == AccessDecision.DENY

    def test_no_owner_document_cannot_be_published_by_contributor(self):
        user = make_user(groups=["engineering"])
        perms = [make_permission(role=UserRole.CONTRIBUTOR)]
        doc = make_document(owner_user_id=None, state=DocumentLifecycleState.NO_OWNER)
        ctx = AccessContext(user=user, space_permissions=perms)
        assert can_publish_document(ctx=ctx, document=doc) == AccessDecision.DENY


class TestCanApproveProposal:
    def test_owner_can_approve(self):
        owner_id = uuid.uuid4()
        user = make_user(groups=["engineering"])
        user_with_id = user.model_copy(update={"id": owner_id})
        perms = [make_permission(role=UserRole.OWNER)]
        doc = make_document(owner_user_id=owner_id)
        ctx = AccessContext(user=user_with_id, space_permissions=perms)
        assert can_approve_proposal(ctx=ctx, document=doc) == AccessDecision.ALLOW

    def test_space_admin_can_approve(self):
        user = make_user(groups=["engineering"])
        perms = [make_permission(role=UserRole.SPACE_ADMIN)]
        doc = make_document()
        ctx = AccessContext(user=user, space_permissions=perms)
        assert can_approve_proposal(ctx=ctx, document=doc) == AccessDecision.ALLOW

    def test_reader_cannot_approve(self):
        user = make_user(groups=["engineering"])
        perms = [make_permission(role=UserRole.READER)]
        doc = make_document()
        ctx = AccessContext(user=user, space_permissions=perms)
        assert can_approve_proposal(ctx=ctx, document=doc) == AccessDecision.DENY


class TestCanAdminSpace:
    def test_space_admin_can_admin(self):
        user = make_user(groups=["engineering"])
        perms = [make_permission(role=UserRole.SPACE_ADMIN)]
        ctx = AccessContext(user=user, space_permissions=perms)
        assert can_admin_space(ctx=ctx, space_id=SPACE_ID)

    def test_company_admin_can_admin(self):
        user = make_user(groups=[])
        ctx = AccessContext(user=user, space_permissions=[], is_company_admin=True)
        assert can_admin_space(ctx=ctx, space_id=SPACE_ID)

    def test_global_is_admin_does_not_grant_space_admin(self):
        user = make_user(groups=[], is_admin=True)
        ctx = AccessContext(user=user, space_permissions=[], is_company_admin=False)
        assert not can_admin_space(ctx=ctx, space_id=SPACE_ID)

    def test_reader_cannot_admin(self):
        user = make_user(groups=["engineering"])
        perms = [make_permission(role=UserRole.READER)]
        ctx = AccessContext(user=user, space_permissions=perms)
        assert not can_admin_space(ctx=ctx, space_id=SPACE_ID)


class TestCompanyAdminAuthority:
    """Feature 036: authority over company data comes from is_company_admin, not the
    legacy global ``user.is_admin`` flag."""

    def test_company_admin_can_approve_proposal(self):
        user = make_user(groups=[])
        doc = make_document()
        ctx = AccessContext(user=user, space_permissions=[], is_company_admin=True)
        assert can_approve_proposal(ctx=ctx, document=doc) == AccessDecision.ALLOW

    def test_company_admin_can_publish(self):
        user = make_user(groups=[])
        doc = make_document(state=DocumentLifecycleState.INGESTED)
        ctx = AccessContext(user=user, space_permissions=[], is_company_admin=True)
        assert can_publish_document(ctx=ctx, document=doc) == AccessDecision.ALLOW

    def test_default_context_is_fail_closed(self):
        """Omitting is_company_admin defaults to non-admin (no authority)."""
        user = make_user(groups=[], is_admin=True)
        doc = make_document()
        ctx = AccessContext(user=user, space_permissions=[])
        assert ctx.is_company_admin is False
        assert can_publish_document(ctx=ctx, document=doc) == AccessDecision.DENY
        assert can_approve_proposal(ctx=ctx, document=doc) == AccessDecision.DENY
        assert not can_admin_space(ctx=ctx, space_id=SPACE_ID)
