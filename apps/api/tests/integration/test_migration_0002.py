"""Integration test for Alembic migration 0002 (Ollama embeddings, 1024→768 dims).

Requires a live PostgreSQL instance. Skipped when the database is unreachable.

Run with:
    DATABASE_URL=postgresql+psycopg://tessera:tessera@localhost:5432/tessera \
    pytest apps/api/tests/integration/test_migration_0002.py -v
"""

from __future__ import annotations

import os

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def _alembic_cfg() -> Config:
    cfg = Config("db/migrations/alembic.ini")
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://tessera:tessera@localhost:5432/tessera",
    )
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _get_sync_engine():
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://tessera:tessera@localhost:5432/tessera",
    )
    return sa.create_engine(db_url)


def _current_revision(engine) -> str | None:
    from alembic.runtime.migration import MigrationContext

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        heads = ctx.get_current_heads()
        return heads[0] if heads else None


def _db_reachable() -> bool:
    try:
        engine = _get_sync_engine()
        with engine.connect():
            return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_reachable(),
    reason="PostgreSQL not reachable — set DATABASE_URL to a live instance",
)


@requires_db
class TestMigration0002:
    def setup_method(self):
        engine = _get_sync_engine()
        rev = _current_revision(engine)
        cfg = _alembic_cfg()
        if rev == "0002":
            command.downgrade(cfg, "0001")
        elif rev is None:
            command.upgrade(cfg, "0001")

    def teardown_method(self):
        engine = _get_sync_engine()
        rev = _current_revision(engine)
        if rev == "0002":
            cfg = _alembic_cfg()
            command.downgrade(cfg, "0001")

    def test_upgrade_changes_column_to_768(self):
        cfg = _alembic_cfg()
        command.upgrade(cfg, "0002")

        engine = _get_sync_engine()
        with engine.connect() as conn:
            atttypmod = conn.execute(
                sa.text(
                    "SELECT atttypmod FROM pg_attribute "
                    "JOIN pg_class ON pg_attribute.attrelid = pg_class.oid "
                    "WHERE pg_class.relname = 'chunks' AND pg_attribute.attname = 'embedding'"
                )
            ).scalar()
        assert atttypmod == 768

    def test_upgrade_recreates_hnsw_index(self):
        cfg = _alembic_cfg()
        command.upgrade(cfg, "0002")

        engine = _get_sync_engine()
        with engine.connect() as conn:
            exists = conn.execute(
                sa.text(
                    "SELECT 1 FROM pg_indexes "
                    "WHERE tablename = 'chunks' AND indexname = 'ix_chunks_embedding_hnsw'"
                )
            ).fetchone()
        assert exists is not None

    def test_downgrade_reverts_column_to_1024(self):
        cfg = _alembic_cfg()
        command.upgrade(cfg, "0002")
        command.downgrade(cfg, "0001")

        engine = _get_sync_engine()
        with engine.connect() as conn:
            atttypmod = conn.execute(
                sa.text(
                    "SELECT atttypmod FROM pg_attribute "
                    "JOIN pg_class ON pg_attribute.attrelid = pg_class.oid "
                    "WHERE pg_class.relname = 'chunks' AND pg_attribute.attname = 'embedding'"
                )
            ).scalar()
        assert atttypmod == 1024
