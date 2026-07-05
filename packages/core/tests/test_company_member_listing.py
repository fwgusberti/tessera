"""Core tests for the CompanyMemberListing value object and the
CompanyRepository.list_members port contract (feature 053)."""

from __future__ import annotations

import inspect
import uuid

import pytest

from tessera_core.domain.company_member_listing import CompanyMemberListing
from tessera_core.domain.company_role import CompanyRole
from tessera_core.domain.entities import CompanyMemberListing as ExportedListing
from tessera_core.ports.repositories.company import CompanyRepository


class TestCompanyMemberListingValueObject:
    def test_carries_all_display_fields(self):
        user_id = uuid.uuid4()
        listing = CompanyMemberListing(
            user_id=user_id,
            display_name="Ada Lovelace",
            email="ada@acme.example",
            role=CompanyRole.ADMIN,
        )
        assert listing.user_id == user_id
        assert listing.display_name == "Ada Lovelace"
        assert listing.email == "ada@acme.example"
        assert listing.role == CompanyRole.ADMIN

    def test_re_exported_from_entities(self):
        assert ExportedListing is CompanyMemberListing


class TestListMembersPortContract:
    def test_port_declares_list_members(self):
        assert hasattr(CompanyRepository, "list_members")
        sig = inspect.signature(CompanyRepository.list_members)
        assert "company_id" in sig.parameters

    @pytest.mark.asyncio
    async def test_concrete_impl_returns_listing_per_member_ordered_by_name(self):
        """A conforming repo yields one listing per membership joined to its user,
        ordered by display_name, carrying that member's company role."""
        company_id = uuid.uuid4()
        other_company_id = uuid.uuid4()
        grace = (uuid.uuid4(), "Grace Hopper", "grace@acme.example", CompanyRole.MEMBER)
        ada = (uuid.uuid4(), "Ada Lovelace", "ada@acme.example", CompanyRole.ADMIN)
        outsider = (uuid.uuid4(), "Zed Outsider", "zed@other.example", CompanyRole.MEMBER)

        class FakeCompanyRepository(CompanyRepository):
            async def create(self, company):  # pragma: no cover - unused
                raise NotImplementedError

            async def get_by_id(self, cid):  # pragma: no cover - unused
                raise NotImplementedError

            async def add_membership(self, membership):  # pragma: no cover - unused
                raise NotImplementedError

            async def get_membership(self, user_id, cid):  # pragma: no cover - unused
                raise NotImplementedError

            async def list_memberships_for_user(self, user_id):  # pragma: no cover
                raise NotImplementedError

            async def search_members_for_space(self, cid, space_id, query, limit=20):
                raise NotImplementedError  # pragma: no cover - unused

            async def list_members(self, cid):
                rows = {
                    company_id: [grace, ada],
                    other_company_id: [outsider],
                }.get(cid, [])
                listings = [
                    CompanyMemberListing(
                        user_id=uid, display_name=name, email=email, role=role
                    )
                    for uid, name, email, role in rows
                ]
                return sorted(listings, key=lambda m: m.display_name)

        repo = FakeCompanyRepository()
        result = await repo.list_members(company_id)

        assert [m.display_name for m in result] == ["Ada Lovelace", "Grace Hopper"]
        assert result[0].role == CompanyRole.ADMIN
        assert result[1].role == CompanyRole.MEMBER
        # A member of another company is never returned for this company.
        assert all(m.email != "zed@other.example" for m in result)
