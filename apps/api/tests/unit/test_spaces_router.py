"""Unit/contract tests for POST /spaces (042: creator must be granted membership)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from tessera_core.domain.entities import SpaceMembership, SpaceRole


def _ctx(actor_id: uuid.UUID, company_id: uuid.UUID | None = None) -> tuple:
    return (
        {"sub": str(actor_id), "id": str(actor_id), "is_admin": False},
        company_id or uuid.uuid4(),
    )


class TestCreateSpaceGrantsCreatorMembership:
    @pytest.mark.anyio
    async def test_create_space_adds_admin_membership_for_caller(self):
        from tessera_api.routers.spaces import CreateSpaceRequest, create_space

        actor_id = uuid.uuid4()
        company_id = uuid.uuid4()
        space_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id, company_id)

        mock_space_repo = AsyncMock()
        mock_space_repo.create.return_value = type(
            "S",
            (),
            {
                "id": space_id,
                "model_dump": lambda self: {"id": str(space_id), "name": "Eng"},
            },
        )()

        mock_membership_repo = AsyncMock()

        with (
            patch("tessera_api.routers.spaces.SqlSpaceRepository", return_value=mock_space_repo),
            patch(
                "tessera_api.routers.spaces.SqlSpaceMembershipRepository",
                return_value=mock_membership_repo,
            ),
            patch("tessera_api.routers.spaces.write_audit", new=AsyncMock()) as mock_audit,
        ):
            body = CreateSpaceRequest(slug="eng", name="Eng", sector="tech")
            await create_space(body, ctx, session)

        mock_membership_repo.add.assert_awaited_once()
        added: SpaceMembership = mock_membership_repo.add.call_args[0][0]
        assert added.space_id == space_id
        assert added.user_id == actor_id
        assert added.role == SpaceRole.ADMIN
        mock_audit.assert_awaited_once()

    @pytest.mark.anyio
    async def test_create_space_response_shape_unchanged(self):
        from tessera_api.routers.spaces import CreateSpaceRequest, create_space

        actor_id = uuid.uuid4()
        company_id = uuid.uuid4()
        space_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id, company_id)

        mock_space_repo = AsyncMock()
        mock_space_repo.create.return_value = type(
            "S",
            (),
            {
                "id": space_id,
                "model_dump": lambda self: {"id": str(space_id), "name": "Eng"},
            },
        )()

        with (
            patch("tessera_api.routers.spaces.SqlSpaceRepository", return_value=mock_space_repo),
            patch(
                "tessera_api.routers.spaces.SqlSpaceMembershipRepository", return_value=AsyncMock()
            ),
            patch("tessera_api.routers.spaces.write_audit", new=AsyncMock()),
        ):
            body = CreateSpaceRequest(slug="eng", name="Eng", sector="tech")
            result = await create_space(body, ctx, session)

        assert result == {"space": {"id": str(space_id), "name": "Eng"}}


class TestRenameSpace:
    def _updated_space_stub(self, space_id: uuid.UUID, name: str):
        return type(
            "S",
            (),
            {
                "id": space_id,
                "name": name,
                "model_dump": lambda self: {"id": str(space_id), "name": name},
            },
        )()

    @pytest.mark.anyio
    async def test_admin_rename_returns_200_and_writes_audit(self):
        from tessera_api.routers.spaces import RenameSpaceRequest, rename_space

        actor_id = uuid.uuid4()
        company_id = uuid.uuid4()
        space_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id, company_id)

        updated = self._updated_space_stub(space_id, "New Name")
        mock_svc = AsyncMock()
        mock_svc.rename = AsyncMock(return_value=updated)

        with (
            patch("tessera_api.routers.spaces.SqlSpaceRepository", return_value=AsyncMock()),
            patch(
                "tessera_api.routers.spaces.SqlSpaceMembershipRepository", return_value=AsyncMock()
            ),
            patch("tessera_api.routers.spaces.SpaceHierarchyService", return_value=mock_svc),
            patch("tessera_api.routers.spaces.write_audit", new=AsyncMock()) as mock_audit,
        ):
            body = RenameSpaceRequest(name="New Name")
            result = await rename_space(space_id, body, ctx, session)

        assert result == {"space": {"id": str(space_id), "name": "New Name"}}
        mock_audit.assert_awaited_once()
        assert mock_audit.call_args.kwargs["action"] == "space_renamed"
        assert mock_audit.call_args.kwargs["entity_type"] == "space"
        assert mock_audit.call_args.kwargs["entity_id"] == space_id

    @pytest.mark.anyio
    async def test_non_admin_rename_returns_403(self):
        from tessera_api.routers.spaces import RenameSpaceRequest, rename_space

        actor_id = uuid.uuid4()
        company_id = uuid.uuid4()
        space_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id, company_id)

        mock_svc = AsyncMock()
        mock_svc.rename = AsyncMock(side_effect=PermissionError("Actor must be admin of space"))

        with (
            patch("tessera_api.routers.spaces.SqlSpaceRepository", return_value=AsyncMock()),
            patch(
                "tessera_api.routers.spaces.SqlSpaceMembershipRepository", return_value=AsyncMock()
            ),
            patch("tessera_api.routers.spaces.SpaceHierarchyService", return_value=mock_svc),
            patch("tessera_api.routers.spaces.write_audit", new=AsyncMock()) as mock_audit,
        ):
            body = RenameSpaceRequest(name="New Name")
            with pytest.raises(HTTPException) as exc_info:
                await rename_space(space_id, body, ctx, session)

        assert exc_info.value.status_code == 403
        mock_audit.assert_not_called()

    @pytest.mark.anyio
    async def test_missing_or_cross_tenant_rename_returns_404_and_audits(self):
        from tessera_api.routers.spaces import RenameSpaceRequest, rename_space

        actor_id = uuid.uuid4()
        company_id = uuid.uuid4()
        space_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id, company_id)

        mock_svc = AsyncMock()
        mock_svc.rename = AsyncMock(side_effect=ValueError("not_found"))

        with (
            patch("tessera_api.routers.spaces.SqlSpaceRepository", return_value=AsyncMock()),
            patch(
                "tessera_api.routers.spaces.SqlSpaceMembershipRepository", return_value=AsyncMock()
            ),
            patch("tessera_api.routers.spaces.SpaceHierarchyService", return_value=mock_svc),
            patch("tessera_api.routers.spaces.write_audit", new=AsyncMock()) as mock_audit,
        ):
            body = RenameSpaceRequest(name="New Name")
            with pytest.raises(HTTPException) as exc_info:
                await rename_space(space_id, body, ctx, session)

        assert exc_info.value.status_code == 404
        mock_audit.assert_awaited_once()
        assert mock_audit.call_args.kwargs["action"] == "cross_tenant_denied"

    @pytest.mark.anyio
    async def test_empty_name_rename_returns_400(self):
        from tessera_api.routers.spaces import RenameSpaceRequest, rename_space

        actor_id = uuid.uuid4()
        company_id = uuid.uuid4()
        space_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id, company_id)

        mock_svc = AsyncMock()
        mock_svc.rename = AsyncMock(side_effect=ValueError("empty_name"))

        with (
            patch("tessera_api.routers.spaces.SqlSpaceRepository", return_value=AsyncMock()),
            patch(
                "tessera_api.routers.spaces.SqlSpaceMembershipRepository", return_value=AsyncMock()
            ),
            patch("tessera_api.routers.spaces.SpaceHierarchyService", return_value=mock_svc),
            patch("tessera_api.routers.spaces.write_audit", new=AsyncMock()) as mock_audit,
        ):
            body = RenameSpaceRequest(name="   ")
            with pytest.raises(HTTPException) as exc_info:
                await rename_space(space_id, body, ctx, session)

        assert exc_info.value.status_code == 400
        mock_audit.assert_not_called()
