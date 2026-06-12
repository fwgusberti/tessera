"""Celery application with Redis broker (ephemeral transport only)."""

import os

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://tessera:tessera@localhost:5432/tessera")

app = Celery(
    "tessera",
    broker=REDIS_URL,
    backend=None,
    include=[
        "tessera_workers.ingestion.tasks",
        "tessera_workers.indexing.tasks",
        "tessera_workers.drift.tasks",
        "tessera_workers.retention.tasks",
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Results are authoritative in Postgres — no Celery result backend
    task_ignore_result=True,
)
