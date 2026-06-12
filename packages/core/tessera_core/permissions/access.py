from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from tessera_core.domain.entities import (
    Confidentiality,
    Document,
    DocumentLifecycleState,
    RolePermission,
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
    - global admin can read any non-restricted document.
    - reader can only read published documents; contributor+ can read all states.
    - user's max_confidentiality must be >= document.confidentiality.
    """
    if document.confidentiality == Confidentiality.RESTRICTED:
        return AccessDecision.DENY

    if ctx.user.is_admin:
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
    if ctx.user.is_admin:
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
    if ctx.user.is_admin:
        return True
    perm = _resolve_permission(ctx.user, space_id, ctx.space_permissions)
    return perm is not None and perm.role == UserRole.SPACE_ADMIN
