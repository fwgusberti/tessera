"""Celery application factory for dispatching tasks from the API."""

from __future__ import annotations

import os


def get_celery_app():
    from celery import Celery

    broker = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    return Celery("tessera", broker=broker)
