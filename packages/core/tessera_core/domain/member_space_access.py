from __future__ import annotations

from dataclasses import dataclass

from tessera_core.domain.space import Space
from tessera_core.domain.space_role import SpaceRole


@dataclass(frozen=True)
class MemberSpaceAccess:
    """One company space annotated with a specific member's standing on it.

    Invariant: ``is_direct == (direct_role is not None)``; inherited-only access
    has ``direct_role is None`` and ``effective_role`` set; no access has both None.
    """

    space: Space
    direct_role: SpaceRole | None
    effective_role: SpaceRole | None
    is_direct: bool
