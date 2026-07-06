"""Feature 054 (T002): the Invitation domain model carries a company role.

The chosen role must survive from "admin invites" to "invitee accepts", so it
lives on the durable invitation record. These tests pin the field, its default,
and that it round-trips through (de)serialization — the domain-layer stand-in for
the DB persistence exercised by the API contract tests.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from tessera_core.domain.company_role import CompanyRole
from tessera_core.domain.invitation import Invitation


def _invitation(**overrides) -> Invitation:
    base = {
        "company_id": __import__("uuid").uuid4(),
        "email": "new.person@example.com",
        "token_hash": "a" * 64,
        "expires_at": datetime.now(UTC) + timedelta(days=7),
    }
    base.update(overrides)
    return Invitation(**base)


@pytest.mark.asyncio
async def test_role_defaults_to_member_when_unspecified():
    inv = _invitation()
    assert inv.role == CompanyRole.MEMBER


@pytest.mark.asyncio
async def test_admin_role_round_trips_through_serialization():
    inv = _invitation(role=CompanyRole.ADMIN)
    assert inv.role == CompanyRole.ADMIN

    # Serialize (persist) and reload (read back) — role survives unchanged.
    reloaded = Invitation.model_validate(inv.model_dump())
    assert reloaded.role == CompanyRole.ADMIN
    assert reloaded.role.value == "admin"


@pytest.mark.asyncio
async def test_member_role_round_trips_through_serialization():
    inv = _invitation(role=CompanyRole.MEMBER)
    reloaded = Invitation.model_validate(inv.model_dump())
    assert reloaded.role == CompanyRole.MEMBER
    assert reloaded.role.value == "member"
