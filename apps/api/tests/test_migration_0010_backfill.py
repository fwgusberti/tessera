"""Backfill/idempotency tests for migration 0010 (feature 036, FR-009 / SC-007).

These run the migration's backfill SQL against the configured Postgres inside a
transaction that is always rolled back, so the dev database is never mutated.
If no database is reachable the module is skipped.
"""

from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.anyio


def _load_backfill_sql() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    path = (
        repo_root / "db" / "migrations" / "versions" / "0010_backfill_company_admin_memberships.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0010", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BACKFILL_SQL


BACKFILL_SQL = _load_backfill_sql()


async def _insert_user(conn) -> uuid.UUID:
    suffix = uuid.uuid4().hex
    row = await conn.execute(
        text(
            "INSERT INTO users (external_subject, email, display_name) "
            "VALUES (:sub, :email, :name) RETURNING id"
        ),
        {"sub": f"sub-{suffix}", "email": f"{suffix}@t.test", "name": "Owner"},
    )
    return row.scalar_one()


async def _insert_company(conn, admin_user_id: uuid.UUID) -> uuid.UUID:
    row = await conn.execute(
        text("INSERT INTO companies (name, admin_user_id) " "VALUES (:name, :admin) RETURNING id"),
        {"name": f"Co-{uuid.uuid4().hex[:8]}", "admin": admin_user_id},
    )
    return row.scalar_one()


async def _insert_membership(conn, user_id, company_id, role: str) -> None:
    await conn.execute(
        text(
            "INSERT INTO company_memberships (user_id, company_id, role) "
            "VALUES (:uid, :cid, :role)"
        ),
        {"uid": user_id, "cid": company_id, "role": role},
    )


async def _count_admin_memberships(conn) -> int:
    row = await conn.execute(text("SELECT count(*) FROM company_memberships WHERE role = 'admin'"))
    return row.scalar_one()


async def _roles_for(conn, user_id, company_id) -> list[str]:
    row = await conn.execute(
        text("SELECT role FROM company_memberships " "WHERE user_id = :uid AND company_id = :cid"),
        {"uid": user_id, "cid": company_id},
    )
    return [r[0] for r in row.fetchall()]


async def test_backfill_creates_admin_for_owner_without_membership():
    from sqlalchemy.exc import InterfaceError, OperationalError

    from tessera_api.adapters.database import get_engine

    engine = get_engine()
    try:
        conn = await engine.connect()
    except (OperationalError, InterfaceError) as exc:  # pragma: no cover
        pytest.skip(f"database unavailable: {exc}")

    try:
        trans = await conn.begin()
        try:
            owner_a = await _insert_user(conn)  # owner with NO membership row
            owner_b = await _insert_user(conn)  # owner already a plain member
            company_a = await _insert_company(conn, owner_a)
            company_b = await _insert_company(conn, owner_b)
            await _insert_membership(conn, owner_b, company_b, "member")

            admins_before = await _count_admin_memberships(conn)

            await conn.execute(text(BACKFILL_SQL))

            # Owner A gets exactly one admin membership.
            roles_a = await _roles_for(conn, owner_a, company_a)
            assert roles_a == ["admin"]

            # Owner B's existing member row is NOT elevated (still exactly one, member).
            roles_b = await _roles_for(conn, owner_b, company_b)
            assert roles_b == ["member"]

            admins_after = await _count_admin_memberships(conn)
            assert admins_after == admins_before + 1  # only company A added
            assert admins_after >= admins_before  # SC-007: never decreases

            # Idempotency: re-running is a no-op.
            await conn.execute(text(BACKFILL_SQL))
            assert await _count_admin_memberships(conn) == admins_after
            assert await _roles_for(conn, owner_a, company_a) == ["admin"]
            assert await _roles_for(conn, owner_b, company_b) == ["member"]
        finally:
            await trans.rollback()
    finally:
        await conn.close()
