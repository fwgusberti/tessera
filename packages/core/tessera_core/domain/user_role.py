from enum import StrEnum


class UserRole(StrEnum):
    READER = "reader"
    CONTRIBUTOR = "contributor"
    OWNER = "owner"
    SPACE_ADMIN = "space_admin"
