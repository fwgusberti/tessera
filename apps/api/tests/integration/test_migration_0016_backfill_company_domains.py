"""Backfill/idempotency tests for migration 0016 (feature 055, US3).

Runs the migration's backfill SQL against the configured Postgres inside a
transaction that is always rolled back, so the dev database is never mutated.
If no database is reachable the module is skipped.

TDD: written before ``0016_backfill_company_domains.py`` exists (Principle IV).
"""

from __future__ import annotations

import importlib.util
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.anyio


def _load_backfill_sql() -> str:
    repo_root = Path(__file__).resolve().parents[4]
    path = repo_root / "db" / "migrations" / "versions" / "0016_backfill_company_domains.py"
    spec = importlib.util.spec_from_file_location("migration_0016", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BACKFILL_SQL


BACKFILL_SQL = _load_backfill_sql()


async def _insert_user(conn, *, email: str) -> uuid.UUID:
    suffix = uuid.uuid4().hex
    row = await conn.execute(
        text(
            "INSERT INTO users (external_subject, email, display_name) "
            "VALUES (:sub, :email, :name) RETURNING id"
        ),
        {"sub": f"sub-{suffix}", "email": email, "name": "Admin"},
    )
    return row.scalar_one()


async def _insert_company(conn, admin_user_id: uuid.UUID, *, created_at: datetime) -> uuid.UUID:
    row = await conn.execute(
        text(
            "INSERT INTO companies (name, admin_user_id, created_at) "
            "VALUES (:name, :admin, :created_at) RETURNING id"
        ),
        {"name": f"Co-{uuid.uuid4().hex[:8]}", "admin": admin_user_id, "created_at": created_at},
    )
    return row.scalar_one()


async def _policies_for_company(conn, company_id) -> list[tuple[str, str, bool]]:
    row = await conn.execute(
        text(
            "SELECT domain, policy, verified FROM domain_join_policies " "WHERE company_id = :cid"
        ),
        {"cid": company_id},
    )
    return [(r[0], r[1], r[2]) for r in row.fetchall()]


async def _get_conn():
    from sqlalchemy.exc import InterfaceError, OperationalError

    from tessera_api.adapters.database import get_engine

    engine = get_engine()
    try:
        return await engine.connect()
    except (OperationalError, InterfaceError) as exc:  # pragma: no cover
        pytest.skip(f"database unavailable: {exc}")


async def test_backfill_associates_non_public_unclaimed_company():
    conn = await _get_conn()
    try:
        trans = await conn.begin()
        try:
            admin = await _insert_user(conn, email=f"admin-{uuid.uuid4().hex}@acme.example")
            company = await _insert_company(conn, admin, created_at=datetime.now(UTC))

            await conn.execute(text(BACKFILL_SQL))

            policies = await _policies_for_company(conn, company)
            assert len(policies) == 1
            domain, policy, verified = policies[0]
            assert domain.endswith("acme.example")
            assert policy == "request_approval"
            assert verified is True
        finally:
            await trans.rollback()
    finally:
        await conn.close()


async def test_backfill_skips_public_domain_company():
    conn = await _get_conn()
    try:
        trans = await conn.begin()
        try:
            admin = await _insert_user(conn, email=f"admin-{uuid.uuid4().hex}@gmail.com")
            company = await _insert_company(conn, admin, created_at=datetime.now(UTC))

            await conn.execute(text(BACKFILL_SQL))

            assert await _policies_for_company(conn, company) == []
        finally:
            await trans.rollback()
    finally:
        await conn.close()


async def test_backfill_earliest_company_wins_on_shared_domain():
    conn = await _get_conn()
    try:
        trans = await conn.begin()
        try:
            # A shared, unique non-public domain across two companies.
            shared = f"shared-{uuid.uuid4().hex[:10]}.example"
            now = datetime.now(UTC)
            admin_early = await _insert_user(conn, email=f"early@{shared}")
            admin_late = await _insert_user(conn, email=f"late@{shared}")
            early = await _insert_company(conn, admin_early, created_at=now - timedelta(days=2))
            late = await _insert_company(conn, admin_late, created_at=now)

            await conn.execute(text(BACKFILL_SQL))

            early_policies = await _policies_for_company(conn, early)
            late_policies = await _policies_for_company(conn, late)
            assert len(early_policies) == 1
            assert early_policies[0][0] == shared
            assert late_policies == []
        finally:
            await trans.rollback()
    finally:
        await conn.close()


async def test_backfill_is_idempotent():
    conn = await _get_conn()
    try:
        trans = await conn.begin()
        try:
            admin = await _insert_user(conn, email=f"admin-{uuid.uuid4().hex}@acme.example")
            company = await _insert_company(conn, admin, created_at=datetime.now(UTC))

            await conn.execute(text(BACKFILL_SQL))
            after_first = await _policies_for_company(conn, company)

            await conn.execute(text(BACKFILL_SQL))
            after_second = await _policies_for_company(conn, company)

            assert len(after_first) == 1
            assert after_second == after_first
        finally:
            await trans.rollback()
    finally:
        await conn.close()
