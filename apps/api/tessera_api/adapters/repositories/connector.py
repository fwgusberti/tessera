from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.connector import ConnectorModel
from tessera_api.adapters.models.space import SpaceModel
from tessera_core.domain.connector import Connector
from tessera_core.ports.repositories.connector import ConnectorRepository


def _connector_from_model(m: ConnectorModel) -> Connector:
    return Connector(
        id=m.id,
        space_id=m.space_id,
        type=m.type,
        config=m.config or {},
        schedule=m.schedule,
        last_sync_at=m.last_sync_at,
        status=m.status,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlConnectorRepository(ConnectorRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, connector: Connector) -> Connector:
        model = ConnectorModel(
            id=connector.id,
            space_id=connector.space_id,
            type=connector.type,
            config=connector.config,
            schedule=connector.schedule,
        )
        self._session.add(model)
        await self._session.flush()
        return _connector_from_model(model)

    async def get_by_id(self, connector_id: UUID) -> Connector | None:
        result = await self._session.execute(
            select(ConnectorModel).where(ConnectorModel.id == connector_id)
        )
        model = result.scalar_one_or_none()
        return _connector_from_model(model) if model else None

    async def get_by_id_for_company(self, connector_id: UUID, company_id: UUID) -> Connector | None:
        result = await self._session.execute(
            select(ConnectorModel)
            .join(SpaceModel, SpaceModel.id == ConnectorModel.space_id)
            .where(
                ConnectorModel.id == connector_id,
                SpaceModel.company_id == company_id,
            )
        )
        model = result.scalar_one_or_none()
        return _connector_from_model(model) if model else None

    async def list_by_space(self, space_id: UUID) -> list[Connector]:
        result = await self._session.execute(
            select(ConnectorModel).where(ConnectorModel.space_id == space_id)
        )
        return [_connector_from_model(m) for m in result.scalars().all()]

    async def update_sync_status(self, connector_id: UUID, status: str) -> Connector:
        await self._session.execute(
            update(ConnectorModel)
            .where(ConnectorModel.id == connector_id)
            .values(status=status, last_sync_at=datetime.now(UTC))
        )
        connector = await self.get_by_id(connector_id)
        assert connector is not None
        return connector
