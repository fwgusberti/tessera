"""slugify() — pure name-to-slug derivation for Space creation."""

from __future__ import annotations

import re
import unicodedata


def slugify(value: str, max_length: int = 100) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(c for c in normalized if not unicodedata.combining(c))
    lowered = without_marks.lower()
    hyphenated = re.sub(r"[^a-z0-9]+", "-", lowered)
    stripped = hyphenated.strip("-")
    truncated = stripped[:max_length].rstrip("-")
    return truncated or "space"
