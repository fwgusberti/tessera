"""Drift detection Celery tasks."""

from __future__ import annotations

import uuid

from tessera_workers.celery_app import app


@app.task(name="tessera.detect_drift")
def detect_drift_task(connector_id: str) -> None:
    """Detect drift for all documents tied to a connector and create UpdateProposals."""
    import asyncio
    from tessera_workers.drift._pipeline import _do_detect_drift

    asyncio.run(_do_detect_drift(connector_id=uuid.UUID(connector_id)))
