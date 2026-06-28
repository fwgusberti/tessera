from enum import StrEnum


class DocumentLifecycleState(StrEnum):
    INGESTED = "ingested"
    NO_OWNER = "no_owner"
    PUBLISHED = "published"
    OUTDATED = "outdated"
    EXPIRED = "expired"
    ARCHIVED = "archived"
