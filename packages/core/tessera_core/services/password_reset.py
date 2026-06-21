"""Domain service for password reset token lifecycle."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from tessera_core.domain.entities import PasswordResetToken


class PasswordResetService:
    def create_token(
        self, user_id: UUID, expires_in_minutes: int = 60
    ) -> tuple[PasswordResetToken, str]:
        """Return a new (PasswordResetToken entity, raw_token_string) pair.

        The raw token must be sent to the user; only the hash is persisted.
        """
        raw = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(minutes=expires_in_minutes)
        token = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        return token, raw

    def is_valid(self, token: PasswordResetToken) -> bool:
        """Return True if the token has not been consumed and has not expired."""
        if token.consumed_at is not None:
            return False
        now = datetime.now(UTC)
        expires = token.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return expires > now
