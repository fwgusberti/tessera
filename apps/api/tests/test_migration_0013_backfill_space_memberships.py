"""Backfill/idempotency tests for migration 0013 (feature 042).

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
    path = repo_root / "db" / "migrations" / "versions" / "0013_backfill_space_memberships.py"
    spec = importlib.util.spec_from_file_location("migration_0013", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BACKFILL_SQL


BACKFILL_SQL = _load_backfill_sql()


async def _insert_user(conn, *, email: str | None = None) -> uuid.UUID:
    suffix = uuid.uuid4().hex
    row = await conn.execute(
        text(
            "INSERT INTO users (external_subject, email, display_name) "
            "VALUES (:sub, :email, :name) RETURNING id"
        ),
        {"sub": f"sub-{suffix}", "email": email or f"{suffix}@t.test", "name": "Member"},
    )
    return row.scalar_one()


async def _insert_company(conn, admin_user_id: uuid.UUID) -> uuid.UUID:
    row = await conn.execute(
        text("INSERT INTO companies (name, admin_user_id) VALUES (:name, :admin) RETURNING id"),
        {"name": f"Co-{uuid.uuid4().hex[:8]}", "admin": admin_user_id},
    )
    return row.scalar_one()


async def _insert_company_membership(conn, user_id, company_id, role: str) -> None:
    await conn.execute(
        text(
            "INSERT INTO company_memberships (user_id, company_id, role) "
            "VALUES (:uid, :cid, :role)"
        ),
        {"uid": user_id, "cid": company_id, "role": role},
    )


async def _insert_space(conn, company_id) -> uuid.UUID:
    suffix = uuid.uuid4().hex[:8]
    row = await conn.execute(
        text(
            "INSERT INTO spaces (slug, name, sector, company_id) "
            "VALUES (:slug, :name, 'tech', :cid) RETURNING id"
        ),
        {"slug": f"space-{suffix}", "name": f"Space {suffix}", "cid": company_id},
    )
    return row.scalar_one()


async def _insert_space_membership(conn, space_id, user_id, role: str) -> None:
    await conn.execute(
        text(
            "INSERT INTO space_memberships (space_id, user_id, role) " "VALUES (:sid, :uid, :role)"
        ),
        {"sid": space_id, "uid": user_id, "role": role},
    )


async def _space_membership_roles(conn, space_id, user_id) -> list[str]:
    row = await conn.execute(
        text("SELECT role FROM space_memberships WHERE space_id = :sid AND user_id = :uid"),
        {"sid": space_id, "uid": user_id},
    )
    return [r[0] for r in row.fetchall()]


async def _membership_count(conn, space_id) -> int:
    row = await conn.execute(
        text("SELECT count(*) FROM space_memberships WHERE space_id = :sid"), {"sid": space_id}
    )
    return row.scalar_one()


async def _get_conn():
    from sqlalchemy.exc import InterfaceError, OperationalError

    from tessera_api.adapters.database import get_engine

    engine = get_engine()
    try:
        return await engine.connect()
    except (OperationalError, InterfaceError) as exc:  # pragma: no cover
        pytest.skip(f"database unavailable: {exc}")


async def test_backfill_grants_admin_on_orphaned_space():
    conn = await _get_conn()
    try:
        trans = await conn.begin()
        try:
            admin = await _insert_user(conn)
            company = await _insert_company(conn, admin)
            await _insert_company_membership(conn, admin, company, "admin")
            space = await _insert_space(conn, company)

            await conn.execute(text(BACKFILL_SQL))

            assert await _space_membership_roles(conn, space, admin) == ["admin"]
        finally:
            await trans.rollback()
    finally:
        await conn.close()


async def test_backfill_grants_every_admin_in_multi_admin_company():
    conn = await _get_conn()
    try:
        trans = await conn.begin()
        try:
            admin_1 = await _insert_user(conn)
            admin_2 = await _insert_user(conn)
            company = await _insert_company(conn, admin_1)
            await _insert_company_membership(conn, admin_1, company, "admin")
            await _insert_company_membership(conn, admin_2, company, "admin")
            space = await _insert_space(conn, company)

            await conn.execute(text(BACKFILL_SQL))

            assert await _space_membership_roles(conn, space, admin_1) == ["admin"]
            assert await _space_membership_roles(conn, space, admin_2) == ["admin"]
            assert await _membership_count(conn, space) == 2
        finally:
            await trans.rollback()
    finally:
        await conn.close()


async def test_backfill_does_not_touch_space_with_existing_member():
    conn = await _get_conn()
    try:
        trans = await conn.begin()
        try:
            admin = await _insert_user(conn)
            viewer = await _insert_user(conn)
            company = await _insert_company(conn, admin)
            await _insert_company_membership(conn, admin, company, "admin")
            space = await _insert_space(conn, company)
            await _insert_space_membership(conn, space, viewer, "viewer")

            await conn.execute(text(BACKFILL_SQL))

            # Only the pre-existing viewer row — admin was NOT added.
            assert await _membership_count(conn, space) == 1
            assert await _space_membership_roles(conn, space, viewer) == ["viewer"]
            assert await _space_membership_roles(conn, space, admin) == []
        finally:
            await trans.rollback()
    finally:
        await conn.close()


async def test_backfill_is_idempotent():
    conn = await _get_conn()
    try:
        trans = await conn.begin()
        try:
            admin = await _insert_user(conn)
            company = await _insert_company(conn, admin)
            await _insert_company_membership(conn, admin, company, "admin")
            space = await _insert_space(conn, company)

            await conn.execute(text(BACKFILL_SQL))
            after_first = await _membership_count(conn, space)

            await conn.execute(text(BACKFILL_SQL))
            after_second = await _membership_count(conn, space)

            assert after_first == 1
            assert after_second == after_first
        finally:
            await trans.rollback()
    finally:
        await conn.close()


async def test_backfill_does_not_cross_tenant_boundaries():
    conn = await _get_conn()
    try:
        trans = await conn.begin()
        try:
            admin_a = await _insert_user(conn)
            admin_b = await _insert_user(conn)
            company_a = await _insert_company(conn, admin_a)
            company_b = await _insert_company(conn, admin_b)
            await _insert_company_membership(conn, admin_a, company_a, "admin")
            await _insert_company_membership(conn, admin_b, company_b, "admin")
            space_b = await _insert_space(conn, company_b)

            await conn.execute(text(BACKFILL_SQL))

            # Company A's admin must never land on company B's orphaned space.
            assert await _space_membership_roles(conn, space_b, admin_a) == []
            assert await _space_membership_roles(conn, space_b, admin_b) == ["admin"]
        finally:
            await trans.rollback()
    finally:
        await conn.close()


async def test_backfill_skips_space_whose_company_has_no_admin():
    """FR-006: a company with zero admin memberships leaves its orphaned space
    with zero inserted rows — the backfill must not error."""
    conn = await _get_conn()
    try:
        trans = await conn.begin()
        try:
            owner = await _insert_user(conn)
            member = await _insert_user(conn)
            company = await _insert_company(conn, owner)
            # Only a non-admin membership exists — no 'admin' role in this company.
            await _insert_company_membership(conn, member, company, "member")
            space = await _insert_space(conn, company)

            await conn.execute(text(BACKFILL_SQL))  # must not raise

            assert await _membership_count(conn, space) == 0
        finally:
            await trans.rollback()
    finally:
        await conn.close()
