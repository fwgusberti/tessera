"""Core tests for the SpaceMemberListing value object and the
SpaceMembershipRepository.list_by_space_with_identity port contract (feature 065)."""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime

import pytest

from tessera_core.domain.entities import SpaceMemberListing as ExportedListing
from tessera_core.domain.space_member_listing import SpaceMemberListing
from tessera_core.domain.space_role import SpaceRole
from tessera_core.ports.repositories.space_membership import SpaceMembershipRepository


class TestSpaceMemberListingValueObject:
    def test_carries_all_membership_and_identity_fields(self):
        listing_id = uuid.uuid4()
        space_id = uuid.uuid4()
        user_id = uuid.uuid4()
        inviter_id = uuid.uuid4()
        now = datetime.now(UTC)

        listing = SpaceMemberListing(
            id=listing_id,
            space_id=space_id,
            user_id=user_id,
            display_name="Ada Lovelace",
            email="ada@acme.example",
            role=SpaceRole.ADMIN,
            invited_by_user_id=inviter_id,
            created_at=now,
            updated_at=now,
        )

        assert listing.id == listing_id
        assert listing.space_id == space_id
        assert listing.user_id == user_id
        assert listing.display_name == "Ada Lovelace"
        assert listing.email == "ada@acme.example"
        assert listing.role == SpaceRole.ADMIN
        assert listing.invited_by_user_id == inviter_id
        assert listing.created_at == now
        assert listing.updated_at == now

    def test_blank_display_name_is_preserved_verbatim(self):
        listing = SpaceMemberListing(
            id=uuid.uuid4(),
            space_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            display_name="",
            email="blank@acme.example",
            role=SpaceRole.VIEWER,
            invited_by_user_id=None,
            created_at=None,
            updated_at=None,
        )
        assert listing.display_name == ""
        assert listing.invited_by_user_id is None
        assert listing.created_at is None
        assert listing.updated_at is None

    def test_re_exported_from_entities(self):
        assert ExportedListing is SpaceMemberListing


class TestListBySpaceWithIdentityPortContract:
    def test_port_declares_list_by_space_with_identity(self):
        assert hasattr(SpaceMembershipRepository, "list_by_space_with_identity")
        sig = inspect.signature(SpaceMembershipRepository.list_by_space_with_identity)
        assert "space_id" in sig.parameters
        assert "company_id" in sig.parameters

    @pytest.mark.asyncio
    async def test_concrete_impl_returns_listing_per_member_ordered_by_name(self):
        """A conforming repo yields one listing per membership joined to its user,
        ordered by display_name, and returns nothing for the wrong company."""
        space_id = uuid.uuid4()
        company_id = uuid.uuid4()
        wrong_company_id = uuid.uuid4()
        grace = (uuid.uuid4(), "Grace Hopper", "grace@acme.example", SpaceRole.EDITOR)
        ada = (uuid.uuid4(), "Ada Lovelace", "ada@acme.example", SpaceRole.ADMIN)

        class FakeSpaceMembershipRepository(SpaceMembershipRepository):
            async def add(self, membership):  # pragma: no cover - unused
                raise NotImplementedError

            async def get(self, sid, uid):  # pragma: no cover - unused
                raise NotImplementedError

            async def list_by_space(self, sid):  # pragma: no cover - unused
                raise NotImplementedError

            async def list_by_user(self, uid):  # pragma: no cover - unused
                raise NotImplementedError

            async def update_role(self, sid, uid, role):  # pragma: no cover - unused
                raise NotImplementedError

            async def remove(self, sid, uid):  # pragma: no cover - unused
                raise NotImplementedError

            async def count_admins(self, sid):  # pragma: no cover - unused
                raise NotImplementedError

            async def list_by_space_with_identity(self, sid, cid):
                if sid != space_id or cid != company_id:
                    return []
                listings = [
                    SpaceMemberListing(
                        id=uuid.uuid4(),
                        space_id=sid,
                        user_id=uid,
                        display_name=name,
                        email=email,
                        role=role,
                        invited_by_user_id=None,
                        created_at=None,
                        updated_at=None,
                    )
                    for uid, name, email, role in [grace, ada]
                ]
                return sorted(listings, key=lambda m: m.display_name)

        repo = FakeSpaceMembershipRepository()
        result = await repo.list_by_space_with_identity(space_id, company_id)

        assert [m.display_name for m in result] == ["Ada Lovelace", "Grace Hopper"]
        assert result[0].role == SpaceRole.ADMIN
        assert result[1].role == SpaceRole.EDITOR

        # Tenant scoping: the wrong company never sees the space's members.
        assert await repo.list_by_space_with_identity(space_id, wrong_company_id) == []
