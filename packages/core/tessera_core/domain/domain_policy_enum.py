from enum import StrEnum


class DomainPolicy(StrEnum):
    AUTO_JOIN = "auto_join"
    REQUEST_APPROVAL = "request_approval"
