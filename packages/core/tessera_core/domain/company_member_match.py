from __future__ import annotations

from uuid import UUID


class CompanyMemberMatch:
    def __init__(self, user_id: UUID, display_name: str, email: str) -> None:
        self.user_id = user_id
        self.display_name = display_name
        self.email = email
