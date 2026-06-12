"""Ingestion Celery tasks."""

from __future__ import annotations

import uuid

from tessera_workers.celery_app import app


@app.task(name="tessera.sync_connector")
def sync_connector_task(connector_id: str) -> None:
    """Sync a connector: fetch artifacts and ingest changed ones."""
    import asyncio
    from tessera_workers.ingestion._sync import _do_sync

    asyncio.run(_do_sync(connector_id=uuid.UUID(connector_id)))
