"""Retention Celery tasks: expire documents, remove from index."""

from tessera_workers.celery_app import app


@app.task(name="tessera.run_retention")
def run_retention_task() -> None:
    """Expire documents past their validity_until date and remove from index."""
    import asyncio
    from tessera_workers.retention._policy import _do_run_retention

    asyncio.run(_do_run_retention())
