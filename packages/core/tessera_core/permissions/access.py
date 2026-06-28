from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from tessera_core.domain.entities import (
    Confidentiality,
    Document,
    DocumentLifecycleState,
    RolePermission,
    SpaceMembership,
    SpaceRole,
    User,
    UserRole,
)

_ROLE_ORDER = [
    UserRole.READER,
    UserRole.CONTRIBUTOR,
    UserRole.OWNER,
    UserRole.SPACE_ADMIN,
]


class AccessDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass
class AccessContext:
    user: User
    space_permissions: list[RolePermission]
    is_company_admin: bool = False


def resolve_user_role(
    user: User,
    space_id: UUID,
    permissions: list[RolePermission],
) -> UserRole | None:
    """Return the highest role the user holds in the given space via group membership."""
    user_groups = set(user.groups)
    applicable = [
        p for p in permissions if p.space_id == space_id and p.idp_group in user_groups
    ]
    if not applicable:
        return None
    return max(applicable, key=lambda p: _ROLE_ORDER.index(p.role)).role


def _resolve_permission(
    user: User, space_id: UUID, permissions: list[RolePermission]
) -> RolePermission | None:
    """Return the permission record with the highest role for the user in a space."""
    user_groups = set(user.groups)
    applicable = [
        p for p in permissions if p.space_id == space_id and p.idp_group in user_groups
    ]
    if not applicable:
        return None
    return max(applicable, key=lambda p: _ROLE_ORDER.index(p.role))


def can_read_document(ctx: AccessContext, document: Document) -> AccessDecision:
    """Decide if the user may read the document.

    Rules:
    - restricted documents are never readable (regardless of role or admin status).
    - a company admin can read any non-restricted document in their own company.
    - reader can only read published documents; contributor+ can read all states.
    - user's max_confidentiality must be >= document.confidentiality.
    """
    if document.confidentiality == Confidentiality.RESTRICTED:
        return AccessDecision.DENY

    if ctx.is_company_admin:
        return AccessDecision.ALLOW

    perm = _resolve_permission(ctx.user, document.space_id, ctx.space_permissions)
    if perm is None:
        return AccessDecision.DENY

    # Readers can only access published/outdated; contributors+ see everything
    if perm.role == UserRole.READER:
        if document.state not in (
            DocumentLifecycleState.PUBLISHED,
            DocumentLifecycleState.OUTDATED,
        ):
            return AccessDecision.DENY

    if perm.max_confidentiality.level() < document.confidentiality.level():
        return AccessDecision.DENY

    return AccessDecision.ALLOW


def can_publish_document(ctx: AccessContext, document: Document) -> AccessDecision:
    """Decide if the user may publish the document (owner or space admin)."""
    if ctx.is_company_admin:
        return AccessDecision.ALLOW

    perm = _resolve_permission(ctx.user, document.space_id, ctx.space_permissions)
    if perm is None:
        return AccessDecision.DENY

    if perm.role == UserRole.SPACE_ADMIN:
        return AccessDecision.ALLOW

    # Owner can publish their own document
    if perm.role == UserRole.OWNER and document.owner_user_id == ctx.user.id:
        return AccessDecision.ALLOW

    return AccessDecision.DENY


def can_approve_proposal(ctx: AccessContext, document: Document) -> AccessDecision:
    """Decide if the user may approve/reject an UpdateProposal for a document."""
    return can_publish_document(ctx=ctx, document=document)


def can_admin_space(ctx: AccessContext, space_id: UUID) -> bool:
    """Return True if the user has administrative rights over the given space."""
    if ctx.is_company_admin:
        return True
    perm = _resolve_permission(ctx.user, space_id, ctx.space_permissions)
    return perm is not None and perm.role == UserRole.SPACE_ADMIN


# ---------------------------------------------------------------------------
# SpaceMembership-based permission functions (Feature 024)
# ---------------------------------------------------------------------------

_SPACE_ROLE_ORDER = [SpaceRole.VIEWER, SpaceRole.EDITOR, SpaceRole.ADMIN]


def get_space_membership_role(
    user_id: UUID,
    space_id: UUID,
    memberships: list[SpaceMembership],
) -> SpaceRole | None:
    """Return the user's direct membership role in the space, or None if not a member."""
    for m in memberships:
        if m.space_id == space_id and m.user_id == user_id:
            return m.role
    return None


def effective_space_role(
    user: User,
    space_id: UUID,
    memberships: list[SpaceMembership],
    is_company_admin: bool = False,
) -> SpaceRole | None:
    """A company admin is implicit ADMIN in spaces of their own company.

    Callers guarantee the space belongs to the active company before passing
    ``is_company_admin=True`` (feature 035 ``validate_space_for_company``), so this
    confers no cross-company reach. Defaults fail-closed (non-admin).
    """
    if is_company_admin:
        return SpaceRole.ADMIN
    return get_space_membership_role(user.id, space_id, memberships)


def can_write_document(
    user: User,
    space_id: UUID,
    memberships: list[SpaceMembership],
    is_company_admin: bool = False,
) -> bool:
    """True if effective role is EDITOR or ADMIN."""
    role = effective_space_role(user, space_id, memberships, is_company_admin)
    return role in (SpaceRole.EDITOR, SpaceRole.ADMIN)


def can_manage_members(
    user: User,
    space_id: UUID,
    memberships: list[SpaceMembership],
    is_company_admin: bool = False,
) -> bool:
    """True if effective role is ADMIN."""
    return effective_space_role(user, space_id, memberships, is_company_admin) == SpaceRole.ADMIN


def can_read_space_document(
    user: User,
    space_id: UUID,
    memberships: list[SpaceMembership],
    is_company_admin: bool = False,
) -> bool:
    """True if user is any member of the space or a company admin (own company)."""
    if is_company_admin:
        return True
    return get_space_membership_role(user.id, space_id, memberships) is not None
