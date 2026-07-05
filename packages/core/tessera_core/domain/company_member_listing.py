from __future__ import annotations

from uuid import UUID

from tessera_core.domain.company_role import CompanyRole


class CompanyMemberListing:
    def __init__(
        self, user_id: UUID, display_name: str, email: str, role: CompanyRole
    ) -> None:
        self.user_id = user_id
        self.display_name = display_name
        self.email = email
        self.role = role
