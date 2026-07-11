"""Integration tests: join-path parity (feature 058, US4 / FR-006, SC-002).

Every path into a company — company creation (onboarding), invitation
acceptance (054), direct add (054), and email-domain matching (055) — must
yield a member that is visible in the roster and member search, appears in the
member space-access view, can be granted space access, and then sees the space.

The whole flow runs over HTTP against shared stateful in-memory repositories,
so every membership write lands in the same store the read surfaces consume.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from tessera_core.domain.company_member_listing import CompanyMemberListing
from tessera_core.domain.company_member_match import CompanyMemberMatch
from tessera_core.domain.entities import (
    Company,
    CompanyMembership,
    CompanyRole,
    DomainJoinPolicy,
    DomainPolicy,
    Invitation,
    InvitationStatus,
    Space,
    User,
)
from tests.integration.test_member_space_access import (
    FakeSpaceMembershipRepository,
    FakeSpaceRepository,
)

DOMAIN = "acme-parity.test"

FOUNDER_ID = uuid.uuid4()
INVITEE_ID = uuid.uuid4()
DIRECT_ID = uuid.uuid4()
DOMAIN_ID = uuid.uuid4()

USERS = {
    FOUNDER_ID: User(
        id=FOUNDER_ID,
        external_subject=f"sub-{FOUNDER_ID}",
        email="founder@gmail.com",
        display_name="Founder",
        is_admin=False,
    ),
    INVITEE_ID: User(
        id=INVITEE_ID,
        external_subject=f"sub-{INVITEE_ID}",
        email="invitee@elsewhere.test",
        display_name="Invitee",
        is_admin=False,
    ),
    DIRECT_ID: User(
        id=DIRECT_ID,
        external_subject=f"sub-{DIRECT_ID}",
        email="direct@elsewhere.test",
        display_name="Direct Add",
        is_admin=False,
    ),
    DOMAIN_ID: User(
        id=DOMAIN_ID,
        external_subject=f"sub-{DOMAIN_ID}",
        email=f"matcher@{DOMAIN}",
        display_name="Domain Match",
        is_admin=False,
    ),
}


class FakeCompanyRepository:
    """Single membership store consumed by every join path and read surface."""

    def __init__(self) -> None:
        self.companies: dict[uuid.UUID, Company] = {}
        self.memberships: list[CompanyMembership] = []

    async def create(self, company: Company) -> Company:
        self.companies[company.id] = company
        return company

    async def get_by_id(self, company_id: uuid.UUID) -> Company | None:
        return self.companies.get(company_id)

    async def add_membership(self, membership: CompanyMembership) -> CompanyMembership:
        stored = membership.model_copy(update={"joined_at": datetime.now(UTC)})
        self.memberships.append(stored)
        return stored

    async def get_membership(
        self, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> CompanyMembership | None:
        return next(
            (m for m in self.memberships if m.user_id == user_id and m.company_id == company_id),
            None,
        )

    async def list_memberships_for_user(self, user_id: uuid.UUID) -> list[CompanyMembership]:
        return [m for m in self.memberships if m.user_id == user_id]

    async def list_members(self, company_id: uuid.UUID) -> list[CompanyMemberListing]:
        return [
            CompanyMemberListing(
                user_id=m.user_id,
                display_name=USERS[m.user_id].display_name,
                email=USERS[m.user_id].email,
                role=m.role,
            )
            for m in self.memberships
            if m.company_id == company_id
        ]

    async def search_members_for_space(
        self, company_id: uuid.UUID, space_id: uuid.UUID, q: str
    ) -> list[CompanyMemberMatch]:
        needle = q.lower()
        return [
            CompanyMemberMatch(
                user_id=m.user_id,
                display_name=USERS[m.user_id].display_name,
                email=USERS[m.user_id].email,
            )
            for m in self.memberships
            if m.company_id == company_id
            and (
                needle in USERS[m.user_id].display_name.lower()
                or needle in USERS[m.user_id].email.lower()
            )
        ]


def _auth_header(user_id: uuid.UUID, company_id: uuid.UUID | None = None) -> dict:
    from tessera_api.auth.jwt_auth import create_access_token

    token = create_access_token(user_id, USERS[user_id].email, False, company_id=company_id)
    return {"Authorization": f"Bearer {token}"}


@contextmanager
def _wired_app(
    company_repo: FakeCompanyRepository,
    space_repo: FakeSpaceRepository,
    membership_repo: FakeSpaceMembershipRepository,
    invitation: Invitation,
    domain_policy_holder: dict,
):
    from tessera_api.adapters.database import get_db
    from tessera_api.auth.bearer import require_onboarding_complete
    from tessera_api.main import app

    user_repo = AsyncMock()
    user_repo.get_by_id = AsyncMock(side_effect=lambda uid: USERS.get(uid))
    user_repo.get_by_email = AsyncMock(
        side_effect=lambda email: next((u for u in USERS.values() if u.email == email), None)
    )

    inv_repo = AsyncMock()
    inv_repo.get_by_id = AsyncMock(
        side_effect=lambda iid: invitation if iid == invitation.id else None
    )
    inv_repo.update_status = AsyncMock()
    inv_repo.get_pending_for_email = AsyncMock(return_value=[])

    domain_repo = AsyncMock()
    domain_repo.get_by_domain = AsyncMock(side_effect=lambda d: domain_policy_holder.get(d))

    ob_repo = AsyncMock()
    ob_repo.get_by_user_id = AsyncMock(return_value=None)

    mock_session = AsyncMock()

    async def _fake_db():
        yield mock_session

    async def _noop():
        return None

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[require_onboarding_complete] = _noop
    try:
        with (
            patch("tessera_api.auth.oidc.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.SqlInvitationRepository", return_value=inv_repo),
            patch(
                "tessera_api.routers.companies.SqlDomainPolicyRepository",
                return_value=domain_repo,
            ),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=ob_repo),
            patch("tessera_api.routers.companies.SqlSpaceRepository", return_value=space_repo),
            patch(
                "tessera_api.routers.companies.SqlSpaceMembershipRepository",
                return_value=membership_repo,
            ),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
            patch("tessera_api.routers.spaces.SqlSpaceRepository", return_value=space_repo),
            patch(
                "tessera_api.routers.spaces.SqlSpaceMembershipRepository",
                return_value=membership_repo,
            ),
            patch("tessera_api.routers.members.SqlSpaceRepository", return_value=space_repo),
            patch("tessera_api.routers.members.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.members.SqlCompanyRepository", return_value=company_repo),
            patch(
                "tessera_api.routers.members.SqlSpaceMembershipRepository",
                return_value=membership_repo,
            ),
            patch("tessera_api.routers.members.SqlAuditRepository", return_value=AsyncMock()),
            TestClient(app) as client,
        ):
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_onboarding_complete, None)


class TestJoinPathParity:
    def test_every_join_path_yields_a_grantable_member(self):
        company_repo = FakeCompanyRepository()
        membership_repo = FakeSpaceMembershipRepository()

        invitation = Invitation(
            company_id=uuid.uuid4(),  # rebound to the created company below
            email=USERS[INVITEE_ID].email,
            token_hash="a" * 64,
            status=InvitationStatus.PENDING,
            role=CompanyRole.MEMBER,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        domain_policy_holder: dict = {}

        # The space is homed under the created company once its id is known.
        space = Space(
            id=uuid.uuid4(),
            slug="parity",
            name="Parity Space",
            sector="tech",
            company_id=uuid.uuid4(),
        )
        space_repo = FakeSpaceRepository([space], membership_repo)

        with _wired_app(
            company_repo, space_repo, membership_repo, invitation, domain_policy_holder
        ) as client:
            # --- Path 1: onboarding company creation -------------------------
            resp = client.post(
                "/v1/companies",
                json={"name": "Parity Corp"},
                headers=_auth_header(FOUNDER_ID),
            )
            assert resp.status_code == 201, resp.text
            company_id = uuid.UUID(resp.json()["id"])
            assert resp.json()["role"] == "admin"

            # home the fixtures under the real company id
            space = space.model_copy(update={"company_id": company_id})
            space_repo._spaces[space.id] = space
            object.__setattr__(invitation, "company_id", company_id)
            domain_policy_holder[DOMAIN] = DomainJoinPolicy(
                company_id=company_id,
                domain=DOMAIN,
                policy=DomainPolicy.AUTO_JOIN,
                verified=True,
            )

            # --- Path 2: invitation acceptance (054) -------------------------
            resp = client.post(
                f"/v1/companies/{company_id}/join",
                json={"method": "invitation", "invitation_id": str(invitation.id)},
                headers=_auth_header(INVITEE_ID),
            )
            assert resp.status_code == 200, resp.text
            assert resp.json()["status"] == "joined"

            # --- Path 3: direct add (054) ------------------------------------
            resp = client.post(
                "/v1/companies/members",
                json={"user_id": str(DIRECT_ID)},
                headers=_auth_header(FOUNDER_ID, company_id),
            )
            assert resp.status_code == 201, resp.text

            # --- Path 4: email-domain match at sign-up (055) ------------------
            resp = client.post(
                f"/v1/companies/{company_id}/join",
                json={"method": "domain_match"},
                headers=_auth_header(DOMAIN_ID),
            )
            assert resp.status_code == 200, resp.text
            assert resp.json()["status"] == "joined"

            # --- Parity checklist, identical for every join path --------------
            admin = _auth_header(FOUNDER_ID, company_id)
            members_by_path = {
                "created": FOUNDER_ID,
                "invited": INVITEE_ID,
                "direct-added": DIRECT_ID,
                "domain-matched": DOMAIN_ID,
            }

            roster = client.get("/v1/companies/members", headers=admin)
            assert roster.status_code == 200
            roster_ids = {m["user_id"] for m in roster.json()["members"]}

            for path, member_id in members_by_path.items():
                # 1. appears in the roster
                assert str(member_id) in roster_ids, f"{path} member missing from roster"

                # 2. appears in space member search
                q = USERS[member_id].display_name.split()[0]
                search = client.get(
                    f"/v1/spaces/{space.id}/members/search",
                    params={"q": q},
                    headers=admin,
                )
                assert search.status_code == 200, f"{path}: {search.text}"
                found = {m["user_id"] for m in search.json()["members"]}
                assert str(member_id) in found, f"{path} member missing from search"

                # 3. appears in the member space-access view (US1 endpoint)
                access = client.get(
                    f"/v1/companies/members/{member_id}/space-access", headers=admin
                )
                assert access.status_code == 200, f"{path}: {access.text}"
                assert {r["id"] for r in access.json()["spaces"]} == {str(space.id)}

                # 4. grant succeeds via the existing endpoint
                if member_id != FOUNDER_ID:
                    grant = client.post(
                        f"/v1/spaces/{space.id}/members",
                        json={"user_id": str(member_id), "role": "viewer"},
                        headers=admin,
                    )
                    assert grant.status_code == 201, f"{path}: {grant.text}"

                    # 5. the member now sees the space on GET /v1/spaces
                    listing = client.get("/v1/spaces", headers=_auth_header(member_id, company_id))
                    assert listing.status_code == 200, f"{path}: {listing.text}"
                    listed = {s["id"] for s in listing.json()["spaces"]}
                    assert str(space.id) in listed, f"{path} member cannot see the space"
