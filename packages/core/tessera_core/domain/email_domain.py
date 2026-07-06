"""Email-domain classification — pure domain logic (Constitution Principle I).

Two helpers used by the sign-up domain-matching flow:

- ``extract_domain`` pulls the domain portion out of an email address.
- ``is_public_email_domain`` decides whether a domain belongs to a public /
  free email provider (gmail, outlook, …). A company must never become
  matchable by such a domain, or the first person to found a company with a
  ``@gmail.com`` address would make every future Gmail user a match.

No framework or persistence imports — unit-testable in isolation.
"""

from __future__ import annotations

# Curated public / free email-provider domains (research.md Decision 3).
# Extensible: add domains here; deterministic and network-free by design.
_PUBLIC_EMAIL_DOMAINS: frozenset[str] = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "outlook.com",
        "hotmail.com",
        "hotmail.co.uk",
        "live.com",
        "msn.com",
        "yahoo.com",
        "yahoo.co.uk",
        "ymail.com",
        "icloud.com",
        "me.com",
        "mac.com",
        "aol.com",
        "proton.me",
        "protonmail.com",
        "pm.me",
        "gmx.com",
        "gmx.net",
        "mail.com",
        "zoho.com",
        "yandex.com",
        "yandex.ru",
        "tutanota.com",
        "fastmail.com",
        "hey.com",
    }
)


def extract_domain(email: str) -> str:
    """Return the lowercased domain of ``email`` (substring after the last ``@``).

    Returns ``""`` when there is no ``@``. Surrounding whitespace is stripped.
    """
    normalized = email.strip().lower()
    if "@" not in normalized:
        return ""
    return normalized.rsplit("@", 1)[-1]


def is_public_email_domain(domain: str) -> bool:
    """True if ``domain`` is a known public / free email-provider domain.

    Case-insensitive; tolerates a leading ``@`` and surrounding whitespace.
    """
    normalized = domain.strip().lower().lstrip("@")
    return normalized in _PUBLIC_EMAIL_DOMAINS
