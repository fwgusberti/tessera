from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.user import UserModel
from tessera_core.domain.user import User
from tessera_core.ports.repositories.user import UserRepository


def _user_from_model(m: UserModel) -> User:
    return User(
        id=m.id,
        external_subject=m.external_subject,
        email=m.email,
        display_name=m.display_name,
        is_admin=m.is_admin,
        groups=m.groups or [],
        default_language=m.default_language,
        password_hash=m.password_hash,
        created_at=m.created_at,
    )


class SqlUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, user: User) -> User:
        existing = await self.get_by_subject(user.external_subject)
        if existing:
            await self._session.execute(
                update(UserModel)
                .where(UserModel.id == existing.id)
                .values(
                    email=user.email,
                    display_name=user.display_name,
                    groups=user.groups,
                )
            )
            return (await self.get_by_subject(user.external_subject)) or user
        model = UserModel(
            id=user.id,
            external_subject=user.external_subject,
            email=user.email,
            display_name=user.display_name,
            is_admin=user.is_admin,
            groups=user.groups,
            default_language=user.default_language,
        )
        self._session.add(model)
        await self._session.flush()
        return _user_from_model(model)

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user_id))
        model = result.scalar_one_or_none()
        return _user_from_model(model) if model else None

    async def get_by_subject(self, subject: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.external_subject == subject)
        )
        model = result.scalar_one_or_none()
        return _user_from_model(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        model = result.scalar_one_or_none()
        return _user_from_model(model) if model else None

    async def create(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            external_subject=user.external_subject,
            email=user.email,
            display_name=user.display_name,
            is_admin=user.is_admin,
            groups=user.groups,
            default_language=user.default_language,
            password_hash=user.password_hash,
        )
        self._session.add(model)
        await self._session.flush()
        return _user_from_model(model)

    async def set_admin(self, user_id: UUID, is_admin: bool) -> User:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user_id))
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"User {user_id} not found")
        model.is_admin = is_admin
        await self._session.flush()
        await self._session.refresh(model)
        return _user_from_model(model)
