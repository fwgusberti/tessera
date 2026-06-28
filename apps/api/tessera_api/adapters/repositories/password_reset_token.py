from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.password_reset_token import PasswordResetTokenModel
from tessera_core.domain.password_reset_token import PasswordResetToken
from tessera_core.ports.repositories.password_reset_token import PasswordResetTokenRepository


def _prt_from_model(m: PasswordResetTokenModel) -> PasswordResetToken:
    return PasswordResetToken(
        id=m.id,
        user_id=m.user_id,
        token_hash=m.token_hash,
        created_at=m.created_at,
        expires_at=m.expires_at,
        consumed_at=m.consumed_at,
    )


class SqlPasswordResetTokenRepository(PasswordResetTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, token: PasswordResetToken) -> PasswordResetToken:
        await self.consume_all_for_user(token.user_id)
        model = PasswordResetTokenModel(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _prt_from_model(model)

    async def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        result = await self._session.execute(
            select(PasswordResetTokenModel).where(PasswordResetTokenModel.token_hash == token_hash)
        )
        model = result.scalar_one_or_none()
        return _prt_from_model(model) if model else None

    async def consume_all_for_user(self, user_id: UUID) -> None:
        await self._session.execute(
            update(PasswordResetTokenModel)
            .where(
                PasswordResetTokenModel.user_id == user_id,
                PasswordResetTokenModel.consumed_at.is_(None),
            )
            .values(consumed_at=datetime.now(UTC))
        )
