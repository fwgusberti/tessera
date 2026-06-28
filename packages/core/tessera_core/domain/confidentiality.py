from enum import StrEnum


class Confidentiality(StrEnum):
    PUBLIC_INTERNAL = "public_internal"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

    def level(self) -> int:
        return {
            Confidentiality.PUBLIC_INTERNAL: 0,
            Confidentiality.INTERNAL: 1,
            Confidentiality.CONFIDENTIAL: 2,
            Confidentiality.RESTRICTED: 3,
        }[self]
