from __future__ import annotations

from tessera_core.domain.space import Space
from tessera_core.domain.space_role import SpaceRole


class SpaceAccess:
    def __init__(self, space: Space, effective_role: SpaceRole, is_direct: bool) -> None:
        self.space = space
        self.effective_role = effective_role
        self.is_direct = is_direct
