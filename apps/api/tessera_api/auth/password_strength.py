"""Password strength validation (server-side authoritative check)."""

from __future__ import annotations

_WEAK_PASSWORDS = frozenset({
    "password", "password1", "password123",
    "12345678", "123456789", "1234567890",
    "qwerty12", "qwerty123", "qwertyui",
    "letmein1", "letmein!", "welcome1",
    "monkey12", "dragon12", "master12",
    "sunshine", "princess", "iloveyou",
    "football", "superman", "batman123",
})


def validate_password_strength(password: str) -> None:
    """Raise ValueError if password does not meet minimum strength requirements."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if password.lower() in _WEAK_PASSWORDS:
        raise ValueError("Password is too common. Please choose a less obvious password.")
    if len(set(password)) == 1:
        raise ValueError("Password is too simple. Please use a mix of characters.")
