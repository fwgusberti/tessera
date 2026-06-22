"""SQLAlchemy repository implementations."""

from __future__ import annotations

from datetime import UTC
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models import (
    AgentCredentialModel,
    AuditRecordModel,
    CompanyMembershipModel,
    CompanyModel,
    ConnectorModel,
    DocumentModel,
    DocumentVersionModel,
    DomainJoinPolicyModel,
    InvitationModel,
    JoinRequestModel,
    OnboardingProgressModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
    RolePermissionModel,
    SourceArtifactModel,
    SpaceMembershipModel,
    SpaceModel,
    UpdateProposalModel,
    UserModel,
)
from tessera_core.domain.entities import (
    AgentCredential,
    AuditRecord,
    Chunk,
    Company,
    CompanyMembership,
    CompanyRole,
    Confidentiality,
    Connector,
    Document,
    DocumentLifecycleState,
    DocumentVersion,
    DomainJoinPolicy,
    DomainPolicy,
    Invitation,
    InvitationStatus,
    JoinRequest,
    JoinRequestStatus,
    OnboardingProgress,
    PasswordResetToken,
    RefreshToken,
    RolePermission,
    SourceArtifact,
    Space,
    SpaceMembership,
    SpaceRole,
    UpdateProposal,
    User,
    UserRole,
)
from tessera_core.ports.repositories import (
    AgentCredentialRepository,
    AuditRepository,
    ChunkRepository,
    CompanyRepository,
    ConnectorRepository,
    DocumentRepository,
    DocumentVersionRepository,
    DomainPolicyRepository,
    InvitationRepository,
    JoinRequestRepository,
    OnboardingRepository,
    PasswordResetTokenRepository,
    ProposalRepository,
    SourceArtifactRepository,
    SpaceMembershipRepository,
    SpaceRepository,
    UserRepository,
)


def _space_from_model(m: SpaceModel) -> Space:
    return Space(
        id=m.id,
        slug=m.slug,
        name=m.name,
        sector=m.sector,
        company_id=m.company_id,
        taxonomy=m.taxonomy or {},
        retention_policy=m.retention_policy or {},
        confidence_threshold=m.confidence_threshold,
        default_language=m.default_language,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _perm_from_model(m: RolePermissionModel) -> RolePermission:
    return RolePermission(
        id=m.id,
        space_id=m.space_id,
        idp_group=m.idp_group,
        role=UserRole(m.role),
        max_confidentiality=Confidentiality(m.max_confidentiality),
        created_at=m.created_at,
    )


def _doc_from_model(m: DocumentModel) -> Document:
    return Document(
        id=m.id,
        space_id=m.space_id,
        owner_user_id=m.owner_user_id,
        title=m.title,
        language=m.language,
        confidentiality=Confidentiality(m.confidentiality),
        tags=m.tags or [],
        validity_until=m.validity_until,
        state=DocumentLifecycleState(m.state),
        current_version_id=m.current_version_id,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _version_from_model(m: DocumentVersionModel) -> DocumentVersion:
    return DocumentVersion(
        id=m.id,
        document_id=m.document_id,
        version_number=m.version_number,
        content_markdown=m.content_markdown,
        frontmatter=m.frontmatter or {},
        author_user_id=m.author_user_id,
        approver_user_id=m.approver_user_id,
        approved_at=m.approved_at,
        source_artifact_id=m.source_artifact_id,
        created_from_proposal_id=m.created_from_proposal_id,
        created_at=m.created_at,
    )


def _connector_from_model(m: ConnectorModel) -> Connector:
    return Connector(
        id=m.id,
        space_id=m.space_id,
        type=m.type,
        config=m.config or {},
        schedule=m.schedule,
        last_sync_at=m.last_sync_at,
        status=m.status,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _artifact_from_model(m: SourceArtifactModel) -> SourceArtifact:
    return SourceArtifact(
        id=m.id,
        connector_id=m.connector_id,
        external_id=m.external_id,
        path=m.path,
        source_version=m.source_version,
        raw_content=m.raw_content,
        content_hash=m.content_hash,
        fetched_at=m.fetched_at,
    )


def _proposal_from_model(m: UpdateProposalModel) -> UpdateProposal:
    from tessera_core.domain.entities import ProposalState

    return UpdateProposal(
        id=m.id,
        document_id=m.document_id,
        source_artifact_id=m.source_artifact_id,
        proposed_markdown_patch=m.proposed_markdown_patch,
        state=ProposalState(m.state),
        created_at=m.created_at,
        decided_by_user_id=m.decided_by_user_id,
        decided_at=m.decided_at,
        rejection_reason=m.rejection_reason,
        drift_score=m.drift_score,
        summary=m.summary,
    )


def _user_from_model(m: UserModel) -> User:
    return User(
        id=m.id,
        external_subject=m.external_subject,
        email=m.email,
        display_name=m.display_name,
        is_admin=m.is_admin,
        groups=m.groups or [],
        default_language=m.default_language,
        password_hash=m.password_hash,
        created_at=m.created_at,
    )


def _credential_from_model(m: AgentCredentialModel) -> AgentCredential:
    return AgentCredential(
        id=m.id,
        name=m.name,
        token_hash=m.token_hash,
        scoped_space_ids=m.scoped_space_ids or [],
        max_confidentiality=Confidentiality(m.max_confidentiality),
        created_by_user_id=m.created_by_user_id,
        revoked_at=m.revoked_at,
        created_at=m.created_at,
    )


class SqlSpaceRepository(SpaceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, space: Space) -> Space:
        model = SpaceModel(
            id=space.id,
            slug=space.slug,
            name=space.name,
            sector=space.sector,
            company_id=space.company_id,
            taxonomy=space.taxonomy,
            retention_policy=space.retention_policy,
            confidence_threshold=space.confidence_threshold,
            default_language=space.default_language,
        )
        self._session.add(model)
        await self._session.flush()
        return _space_from_model(model)

    async def get_by_id(self, space_id: UUID) -> Space | None:
        result = await self._session.execute(select(SpaceModel).where(SpaceModel.id == space_id))
        model = result.scalar_one_or_none()
        return _space_from_model(model) if model else None

    async def get_by_id_for_company(self, space_id: UUID, company_id: UUID) -> Space | None:
        result = await self._session.execute(
            select(SpaceModel).where(
                SpaceModel.id == space_id,
                SpaceModel.company_id == company_id,
            )
        )
        model = result.scalar_one_or_none()
        return _space_from_model(model) if model else None

    async def list_all(self) -> list[Space]:
        result = await self._session.execute(select(SpaceModel))
        return [_space_from_model(m) for m in result.scalars().all()]

    async def list_by_company(self, company_id: UUID) -> list[Space]:
        result = await self._session.execute(
            select(SpaceModel).where(SpaceModel.company_id == company_id)
        )
        return [_space_from_model(m) for m in result.scalars().all()]

    async def list_for_user(self, user: User) -> list[Space]:
        if user.is_admin:
            return await self.list_all()
        if not user.groups:
            return []
        result = await self._session.execute(
            select(SpaceModel)
            .join(RolePermissionModel, RolePermissionModel.space_id == SpaceModel.id)
            .where(RolePermissionModel.idp_group.in_(user.groups))
            .distinct()
        )
        return [_space_from_model(m) for m in result.scalars().all()]

    async def create_role_permission(self, permission: RolePermission) -> RolePermission:
        model = RolePermissionModel(
            id=permission.id,
            space_id=permission.space_id,
            idp_group=permission.idp_group,
            role=permission.role.value,
            max_confidentiality=permission.max_confidentiality.value,
        )
        self._session.add(model)
        await self._session.flush()
        return _perm_from_model(model)

    async def list_role_permissions(self, space_id: UUID) -> list[RolePermission]:
        result = await self._session.execute(
            select(RolePermissionModel).where(RolePermissionModel.space_id == space_id)
        )
        return [_perm_from_model(m) for m in result.scalars().all()]


class SqlDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document: Document) -> Document:
        model = DocumentModel(
            id=document.id,
            space_id=document.space_id,
            owner_user_id=document.owner_user_id,
            title=document.title,
            language=document.language,
            confidentiality=document.confidentiality.value,
            tags=document.tags,
            validity_until=document.validity_until,
            state=document.state.value,
            current_version_id=document.current_version_id,
        )
        self._session.add(model)
        await self._session.flush()
        return _doc_from_model(model)

    async def get_by_id(self, document_id: UUID) -> Document | None:
        result = await self._session.execute(
            select(DocumentModel).where(DocumentModel.id == document_id)
        )
        model = result.scalar_one_or_none()
        return _doc_from_model(model) if model else None

    async def list_by_space(
        self, space_id: UUID, state: DocumentLifecycleState | None = None
    ) -> list[Document]:
        q = select(DocumentModel).where(DocumentModel.space_id == space_id)
        if state:
            q = q.where(DocumentModel.state == state.value)
        result = await self._session.execute(q)
        return [_doc_from_model(m) for m in result.scalars().all()]

    async def get_by_id_for_company(self, document_id: UUID, company_id: UUID) -> Document | None:
        result = await self._session.execute(
            select(DocumentModel)
            .join(SpaceModel, SpaceModel.id == DocumentModel.space_id)
            .where(DocumentModel.id == document_id, SpaceModel.company_id == company_id)
        )
        model = result.scalar_one_or_none()
        return _doc_from_model(model) if model else None

    async def list_by_space_ids(
        self, space_ids: list[UUID], state: DocumentLifecycleState | None = None
    ) -> list[Document]:
        if not space_ids:
            return []
        q = select(DocumentModel).where(DocumentModel.space_id.in_(space_ids))
        if state:
            q = q.where(DocumentModel.state == state.value)
        result = await self._session.execute(q)
        return [_doc_from_model(m) for m in result.scalars().all()]

    async def list_by_space_ids_for_company(
        self,
        space_ids: list[UUID],
        company_id: UUID,
        state: DocumentLifecycleState | None = None,
    ) -> list[Document]:
        if not space_ids:
            return []
        q = (
            select(DocumentModel)
            .join(SpaceModel, SpaceModel.id == DocumentModel.space_id)
            .where(
                DocumentModel.space_id.in_(space_ids),
                SpaceModel.company_id == company_id,
            )
        )
        if state:
            q = q.where(DocumentModel.state == state.value)
        result = await self._session.execute(q)
        return [_doc_from_model(m) for m in result.scalars().all()]

    async def update_state(self, document_id: UUID, state: DocumentLifecycleState) -> Document:
        await self._session.execute(
            update(DocumentModel).where(DocumentModel.id == document_id).values(state=state.value)
        )
        doc = await self.get_by_id(document_id)
        assert doc is not None
        return doc

    async def set_current_version(self, document_id: UUID, version_id: UUID) -> Document:
        await self._session.execute(
            update(DocumentModel)
            .where(DocumentModel.id == document_id)
            .values(current_version_id=version_id)
        )
        doc = await self.get_by_id(document_id)
        assert doc is not None
        return doc

    async def set_owner(self, document_id: UUID, user_id: UUID) -> Document:
        await self._session.execute(
            update(DocumentModel)
            .where(DocumentModel.id == document_id)
            .values(owner_user_id=user_id)
        )
        doc = await self.get_by_id(document_id)
        assert doc is not None
        return doc


class SqlDocumentVersionRepository(DocumentVersionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, version: DocumentVersion) -> DocumentVersion:
        model = DocumentVersionModel(
            id=version.id,
            document_id=version.document_id,
            version_number=version.version_number,
            content_markdown=version.content_markdown,
            frontmatter=version.frontmatter,
            author_user_id=version.author_user_id,
            approver_user_id=version.approver_user_id,
            approved_at=version.approved_at,
            source_artifact_id=version.source_artifact_id,
            created_from_proposal_id=version.created_from_proposal_id,
        )
        self._session.add(model)
        await self._session.flush()
        return _version_from_model(model)

    async def get_by_id(self, version_id: UUID) -> DocumentVersion | None:
        result = await self._session.execute(
            select(DocumentVersionModel).where(DocumentVersionModel.id == version_id)
        )
        model = result.scalar_one_or_none()
        return _version_from_model(model) if model else None

    async def list_by_document(self, document_id: UUID) -> list[DocumentVersion]:
        result = await self._session.execute(
            select(DocumentVersionModel)
            .where(DocumentVersionModel.document_id == document_id)
            .order_by(DocumentVersionModel.version_number)
        )
        return [_version_from_model(m) for m in result.scalars().all()]

    async def next_version_number(self, document_id: UUID) -> int:
        from sqlalchemy import func

        result = await self._session.execute(
            select(func.coalesce(func.max(DocumentVersionModel.version_number), 0)).where(
                DocumentVersionModel.document_id == document_id
            )
        )
        return (result.scalar() or 0) + 1

    async def update_approval(
        self, version_id: UUID, approver_id: UUID, approved_at: object
    ) -> DocumentVersion:
        await self._session.execute(
            update(DocumentVersionModel)
            .where(DocumentVersionModel.id == version_id)
            .values(approver_user_id=approver_id, approved_at=approved_at)
        )
        result = await self._session.execute(
            select(DocumentVersionModel).where(DocumentVersionModel.id == version_id)
        )
        model = result.scalar_one()
        return _version_from_model(model)


class SqlChunkRepository(ChunkRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_chunks(self, chunks: list[Chunk]) -> None:
        from sqlalchemy import text

        for chunk in chunks:
            await self._session.execute(
                text("""
                    INSERT INTO chunks
                        (id, document_version_id, document_id, space_id,
                         ordinal, text, confidentiality, language, embedding)
                    VALUES
                        (:id, :document_version_id, :document_id, :space_id,
                         :ordinal, :text, :confidentiality, :language,
                         CAST(:embedding AS vector))
                    ON CONFLICT (id) DO UPDATE SET
                        document_version_id = EXCLUDED.document_version_id,
                        ordinal             = EXCLUDED.ordinal,
                        text                = EXCLUDED.text,
                        confidentiality     = EXCLUDED.confidentiality,
                        language            = EXCLUDED.language,
                        embedding           = EXCLUDED.embedding
                """),
                {
                    "id": chunk.id,
                    "document_version_id": chunk.document_version_id,
                    "document_id": chunk.document_id,
                    "space_id": chunk.space_id,
                    "ordinal": chunk.ordinal,
                    "text": chunk.text,
                    "confidentiality": chunk.confidentiality.value,
                    "language": chunk.language,
                    "embedding": str(chunk.embedding) if chunk.embedding is not None else None,
                },
            )

    async def delete_by_document(self, document_id: UUID) -> None:
        from sqlalchemy import text

        await self._session.execute(
            text("DELETE FROM chunks WHERE document_id = :doc_id"),
            {"doc_id": document_id},
        )

    async def search(
        self,
        query_embedding: list[float],
        space_ids: list[UUID],
        max_confidentiality_level: int,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        from tessera_core.domain.entities import Confidentiality as Conf

        allowed_levels = [
            c.value for c in Conf if c.level() <= max_confidentiality_level and c != Conf.RESTRICTED
        ]
        space_id_strs = [str(sid) for sid in space_ids]

        from sqlalchemy import text

        sql = text("""
            SELECT
                c.id, c.document_version_id, c.document_id, c.space_id,
                c.ordinal, c.text, c.confidentiality, c.language,
                1 - (c.embedding <=> CAST(:embedding AS vector)) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE
                c.space_id = ANY(CAST(:space_ids AS uuid[]))
                AND c.confidentiality = ANY(CAST(:allowed_confidentiality AS text[]))
                AND d.state = 'published'
                AND c.embedding IS NOT NULL
            ORDER BY c.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)
        result = await self._session.execute(
            sql,
            {
                "embedding": str(query_embedding),
                "space_ids": "{" + ",".join(space_id_strs) + "}",
                "allowed_confidentiality": "{" + ",".join(allowed_levels) + "}",
                "top_k": top_k,
            },
        )
        return [dict(row._mapping) for row in result]


class SqlConnectorRepository(ConnectorRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, connector: Connector) -> Connector:
        model = ConnectorModel(
            id=connector.id,
            space_id=connector.space_id,
            type=connector.type,
            config=connector.config,
            schedule=connector.schedule,
        )
        self._session.add(model)
        await self._session.flush()
        return _connector_from_model(model)

    async def get_by_id(self, connector_id: UUID) -> Connector | None:
        result = await self._session.execute(
            select(ConnectorModel).where(ConnectorModel.id == connector_id)
        )
        model = result.scalar_one_or_none()
        return _connector_from_model(model) if model else None

    async def list_by_space(self, space_id: UUID) -> list[Connector]:
        result = await self._session.execute(
            select(ConnectorModel).where(ConnectorModel.space_id == space_id)
        )
        return [_connector_from_model(m) for m in result.scalars().all()]

    async def update_sync_status(self, connector_id: UUID, status: str) -> Connector:
        from datetime import datetime

        await self._session.execute(
            update(ConnectorModel)
            .where(ConnectorModel.id == connector_id)
            .values(status=status, last_sync_at=datetime.now(UTC))
        )
        connector = await self.get_by_id(connector_id)
        assert connector is not None
        return connector


class SqlSourceArtifactRepository(SourceArtifactRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, artifact: SourceArtifact) -> SourceArtifact:
        existing = await self.get_by_external_id(artifact.connector_id, artifact.external_id)
        if existing:
            await self._session.execute(
                update(SourceArtifactModel)
                .where(SourceArtifactModel.id == existing.id)
                .values(
                    raw_content=artifact.raw_content,
                    content_hash=artifact.content_hash,
                    source_version=artifact.source_version,
                )
            )
            return (
                await self.get_by_external_id(artifact.connector_id, artifact.external_id)
            ) or artifact
        model = SourceArtifactModel(
            id=artifact.id,
            connector_id=artifact.connector_id,
            external_id=artifact.external_id,
            path=artifact.path,
            source_version=artifact.source_version,
            raw_content=artifact.raw_content,
            content_hash=artifact.content_hash,
        )
        self._session.add(model)
        await self._session.flush()
        return _artifact_from_model(model)

    async def get_by_external_id(
        self, connector_id: UUID, external_id: str
    ) -> SourceArtifact | None:
        result = await self._session.execute(
            select(SourceArtifactModel).where(
                SourceArtifactModel.connector_id == connector_id,
                SourceArtifactModel.external_id == external_id,
            )
        )
        model = result.scalar_one_or_none()
        return _artifact_from_model(model) if model else None

    async def list_by_connector(self, connector_id: UUID) -> list[SourceArtifact]:
        result = await self._session.execute(
            select(SourceArtifactModel).where(SourceArtifactModel.connector_id == connector_id)
        )
        return [_artifact_from_model(m) for m in result.scalars().all()]


class SqlProposalRepository(ProposalRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, proposal: UpdateProposal) -> UpdateProposal:
        model = UpdateProposalModel(
            id=proposal.id,
            document_id=proposal.document_id,
            source_artifact_id=proposal.source_artifact_id,
            proposed_markdown_patch=proposal.proposed_markdown_patch,
            state=proposal.state.value,
            drift_score=proposal.drift_score,
            summary=proposal.summary,
        )
        self._session.add(model)
        await self._session.flush()
        return _proposal_from_model(model)

    async def get_by_id(self, proposal_id: UUID) -> UpdateProposal | None:
        result = await self._session.execute(
            select(UpdateProposalModel).where(UpdateProposalModel.id == proposal_id)
        )
        model = result.scalar_one_or_none()
        return _proposal_from_model(model) if model else None

    async def list_pending_for_document(self, document_id: UUID) -> list[UpdateProposal]:
        result = await self._session.execute(
            select(UpdateProposalModel).where(
                UpdateProposalModel.document_id == document_id,
                UpdateProposalModel.state == "pending",
            )
        )
        return [_proposal_from_model(m) for m in result.scalars().all()]

    async def update_state(self, proposal: UpdateProposal) -> UpdateProposal:
        await self._session.execute(
            update(UpdateProposalModel)
            .where(UpdateProposalModel.id == proposal.id)
            .values(
                state=proposal.state.value,
                decided_by_user_id=proposal.decided_by_user_id,
                decided_at=proposal.decided_at,
                rejection_reason=proposal.rejection_reason,
            )
        )
        updated = await self.get_by_id(proposal.id)
        assert updated is not None
        return updated

    async def invalidate_pending_for_document(self, document_id: UUID) -> int:

        result = await self._session.execute(
            update(UpdateProposalModel)
            .where(
                UpdateProposalModel.document_id == document_id,
                UpdateProposalModel.state == "pending",
            )
            .values(state="invalidated")
        )
        return result.rowcount


class SqlUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, user: User) -> User:
        existing = await self.get_by_subject(user.external_subject)
        if existing:
            await self._session.execute(
                update(UserModel)
                .where(UserModel.id == existing.id)
                .values(
                    email=user.email,
                    display_name=user.display_name,
                    groups=user.groups,
                )
            )
            return (await self.get_by_subject(user.external_subject)) or user
        model = UserModel(
            id=user.id,
            external_subject=user.external_subject,
            email=user.email,
            display_name=user.display_name,
            is_admin=user.is_admin,
            groups=user.groups,
            default_language=user.default_language,
        )
        self._session.add(model)
        await self._session.flush()
        return _user_from_model(model)

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user_id))
        model = result.scalar_one_or_none()
        return _user_from_model(model) if model else None

    async def get_by_subject(self, subject: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.external_subject == subject)
        )
        model = result.scalar_one_or_none()
        return _user_from_model(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        model = result.scalar_one_or_none()
        return _user_from_model(model) if model else None

    async def create(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            external_subject=user.external_subject,
            email=user.email,
            display_name=user.display_name,
            is_admin=user.is_admin,
            groups=user.groups,
            default_language=user.default_language,
            password_hash=user.password_hash,
        )
        self._session.add(model)
        await self._session.flush()
        return _user_from_model(model)

    async def set_admin(self, user_id: UUID, is_admin: bool) -> User:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user_id))
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"User {user_id} not found")
        model.is_admin = is_admin
        await self._session.flush()
        await self._session.refresh(model)
        return _user_from_model(model)


class SqlAgentCredentialRepository(AgentCredentialRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, credential: AgentCredential) -> AgentCredential:
        model = AgentCredentialModel(
            id=credential.id,
            name=credential.name,
            token_hash=credential.token_hash,
            scoped_space_ids=credential.scoped_space_ids,
            max_confidentiality=credential.max_confidentiality.value,
            created_by_user_id=credential.created_by_user_id,
        )
        self._session.add(model)
        await self._session.flush()
        return _credential_from_model(model)

    async def get_by_token_hash(self, token_hash: str) -> AgentCredential | None:
        result = await self._session.execute(
            select(AgentCredentialModel).where(AgentCredentialModel.token_hash == token_hash)
        )
        model = result.scalar_one_or_none()
        return _credential_from_model(model) if model else None

    async def revoke(self, credential_id: UUID) -> AgentCredential:
        from datetime import datetime

        await self._session.execute(
            update(AgentCredentialModel)
            .where(AgentCredentialModel.id == credential_id)
            .values(revoked_at=datetime.now(UTC))
        )
        result = await self._session.execute(
            select(AgentCredentialModel).where(AgentCredentialModel.id == credential_id)
        )
        model = result.scalar_one()
        return _credential_from_model(model)


class SqlAuditRepository(AuditRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, record: AuditRecord) -> None:
        model = AuditRecordModel(
            id=record.id,
            actor_type=record.actor_type,
            actor_id=record.actor_id,
            action=record.action,
            entity_type=record.entity_type,
            entity_id=record.entity_id,
            record_metadata=record.metadata,
        )
        self._session.add(model)

    async def list_for_entity(self, entity_type: str, entity_id: UUID) -> list[AuditRecord]:
        result = await self._session.execute(
            select(AuditRecordModel)
            .where(
                AuditRecordModel.entity_type == entity_type,
                AuditRecordModel.entity_id == entity_id,
            )
            .order_by(AuditRecordModel.occurred_at)
        )
        from tessera_core.domain.entities import AuditRecord as AR

        return [
            AR(
                id=m.id,
                actor_type=m.actor_type,
                actor_id=m.actor_id,
                action=m.action,
                entity_type=m.entity_type,
                entity_id=m.entity_id,
                occurred_at=m.occurred_at,
                metadata=m.record_metadata or {},
            )
            for m in result.scalars().all()
        ]


def _refresh_token_from_model(m: RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        id=m.id,
        user_id=m.user_id,
        token_hash=m.token_hash,
        issued_at=m.issued_at,
        expires_at=m.expires_at,
        is_revoked=m.is_revoked,
    )


class SqlRefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, token: RefreshToken) -> RefreshToken:
        model = RefreshTokenModel(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _refresh_token_from_model(model)

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        model = result.scalar_one_or_none()
        return _refresh_token_from_model(model) if model else None

    async def revoke(self, token_hash: str) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.token_hash == token_hash)
            .values(is_revoked=True)
        )

    async def delete_by_hash(self, token_hash: str) -> None:
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        model = result.scalar_one_or_none()
        if model:
            await self._session.delete(model)

    async def revoke_all_except(self, user_id: UUID, except_hash: str) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.token_hash != except_hash,
                RefreshTokenModel.is_revoked.is_(False),
            )
            .values(is_revoked=True)
        )

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.is_revoked.is_(False),
            )
            .values(is_revoked=True)
        )


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------


def _onboarding_from_model(m: OnboardingProgressModel) -> OnboardingProgress:
    return OnboardingProgress(
        id=m.id,
        user_id=m.user_id,
        completed_steps=list(m.completed_steps or []),
        current_step=m.current_step,
        company_join_method=m.company_join_method,
        company_id=m.company_id,
        completed_at=m.completed_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlOnboardingRepository(OnboardingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, progress: OnboardingProgress) -> OnboardingProgress:
        model = OnboardingProgressModel(
            id=progress.id,
            user_id=progress.user_id,
            completed_steps=list(progress.completed_steps),
            current_step=progress.current_step,
            company_join_method=progress.company_join_method,
            completed_at=progress.completed_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _onboarding_from_model(model)

    async def get_by_user_id(self, user_id: UUID) -> OnboardingProgress | None:
        result = await self._session.execute(
            select(OnboardingProgressModel).where(OnboardingProgressModel.user_id == user_id)
        )
        model = result.scalar_one_or_none()
        return _onboarding_from_model(model) if model else None

    async def advance_step(
        self,
        user_id: UUID,
        next_step: str,
        company_join_method: str | None = None,
        company_id: UUID | None = None,
    ) -> OnboardingProgress:
        from datetime import datetime

        result = await self._session.execute(
            select(OnboardingProgressModel).where(OnboardingProgressModel.user_id == user_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"OnboardingProgress for user {user_id} not found")

        # Mark the current step as completed before moving forward
        current = model.current_step
        if current and current not in list(model.completed_steps or []):
            model.completed_steps = list(model.completed_steps or []) + [current]

        model.current_step = next_step
        model.updated_at = datetime.now(UTC)
        if company_join_method is not None:
            model.company_join_method = company_join_method
        if company_id is not None:
            model.company_id = company_id

        await self._session.flush()
        await self._session.refresh(model)
        return _onboarding_from_model(model)

    async def complete(self, user_id: UUID) -> OnboardingProgress:
        from datetime import datetime

        result = await self._session.execute(
            select(OnboardingProgressModel).where(OnboardingProgressModel.user_id == user_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"OnboardingProgress for user {user_id} not found")

        now = datetime.now(UTC)
        model.completed_at = now
        model.updated_at = now
        await self._session.flush()
        await self._session.refresh(model)
        return _onboarding_from_model(model)


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------


def _company_from_model(m: CompanyModel) -> Company:
    return Company(
        id=m.id,
        name=m.name,
        industry=m.industry,
        team_size=m.team_size,
        admin_user_id=m.admin_user_id,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _company_membership_from_model(m: CompanyMembershipModel) -> CompanyMembership:
    return CompanyMembership(
        id=m.id,
        user_id=m.user_id,
        company_id=m.company_id,
        role=CompanyRole(m.role),
        joined_at=m.joined_at,
    )


class SqlCompanyRepository(CompanyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, company: Company) -> Company:
        model = CompanyModel(
            id=company.id,
            name=company.name,
            industry=company.industry,
            team_size=company.team_size,
            admin_user_id=company.admin_user_id,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _company_from_model(model)

    async def get_by_id(self, company_id: UUID) -> Company | None:
        result = await self._session.execute(
            select(CompanyModel).where(CompanyModel.id == company_id)
        )
        model = result.scalar_one_or_none()
        return _company_from_model(model) if model else None

    async def add_membership(self, membership: CompanyMembership) -> CompanyMembership:
        model = CompanyMembershipModel(
            id=membership.id,
            user_id=membership.user_id,
            company_id=membership.company_id,
            role=membership.role.value,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _company_membership_from_model(model)

    async def get_membership(self, user_id: UUID, company_id: UUID) -> CompanyMembership | None:
        result = await self._session.execute(
            select(CompanyMembershipModel).where(
                CompanyMembershipModel.user_id == user_id,
                CompanyMembershipModel.company_id == company_id,
            )
        )
        model = result.scalar_one_or_none()
        return _company_membership_from_model(model) if model else None

    async def list_memberships_for_user(self, user_id: UUID) -> list[CompanyMembership]:
        result = await self._session.execute(
            select(CompanyMembershipModel).where(CompanyMembershipModel.user_id == user_id)
        )
        return [_company_membership_from_model(m) for m in result.scalars().all()]


# ---------------------------------------------------------------------------
# Domain Policy
# ---------------------------------------------------------------------------


def _domain_policy_from_model(m: DomainJoinPolicyModel) -> DomainJoinPolicy:
    return DomainJoinPolicy(
        id=m.id,
        company_id=m.company_id,
        domain=m.domain,
        policy=DomainPolicy(m.policy),
        verified=m.verified,
        created_at=m.created_at,
        verified_at=m.verified_at,
    )


class SqlDomainPolicyRepository(DomainPolicyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, policy: DomainJoinPolicy) -> DomainJoinPolicy:
        model = DomainJoinPolicyModel(
            id=policy.id,
            company_id=policy.company_id,
            domain=policy.domain,
            policy=policy.policy.value,
            verified=policy.verified,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _domain_policy_from_model(model)

    async def get_by_domain(self, domain: str) -> DomainJoinPolicy | None:
        result = await self._session.execute(
            select(DomainJoinPolicyModel).where(DomainJoinPolicyModel.domain == domain)
        )
        model = result.scalar_one_or_none()
        return _domain_policy_from_model(model) if model else None

    async def get_by_id(self, policy_id: UUID) -> DomainJoinPolicy | None:
        result = await self._session.execute(
            select(DomainJoinPolicyModel).where(DomainJoinPolicyModel.id == policy_id)
        )
        model = result.scalar_one_or_none()
        return _domain_policy_from_model(model) if model else None

    async def list_by_company(self, company_id: UUID) -> list[DomainJoinPolicy]:
        result = await self._session.execute(
            select(DomainJoinPolicyModel).where(DomainJoinPolicyModel.company_id == company_id)
        )
        return [_domain_policy_from_model(m) for m in result.scalars().all()]

    async def mark_verified(self, policy_id: UUID) -> DomainJoinPolicy:
        from datetime import datetime

        result = await self._session.execute(
            select(DomainJoinPolicyModel).where(DomainJoinPolicyModel.id == policy_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"DomainJoinPolicy {policy_id} not found")
        model.verified = True
        model.verified_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(model)
        return _domain_policy_from_model(model)


# ---------------------------------------------------------------------------
# Invitation
# ---------------------------------------------------------------------------


def _invitation_from_model(m: InvitationModel) -> Invitation:
    return Invitation(
        id=m.id,
        company_id=m.company_id,
        invited_by_user_id=m.invited_by_user_id,
        email=m.email,
        token_hash=m.token_hash,
        status=InvitationStatus(m.status),
        expires_at=m.expires_at,
        created_at=m.created_at,
        accepted_at=m.accepted_at,
    )


class SqlInvitationRepository(InvitationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, invitation: Invitation) -> Invitation:
        model = InvitationModel(
            id=invitation.id,
            company_id=invitation.company_id,
            invited_by_user_id=invitation.invited_by_user_id,
            email=invitation.email,
            token_hash=invitation.token_hash,
            status=invitation.status.value,
            expires_at=invitation.expires_at,
            accepted_at=invitation.accepted_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _invitation_from_model(model)

    async def create_bulk(self, invitations: list[Invitation]) -> list[Invitation]:
        models = [
            InvitationModel(
                id=inv.id,
                company_id=inv.company_id,
                invited_by_user_id=inv.invited_by_user_id,
                email=inv.email,
                token_hash=inv.token_hash,
                status=inv.status.value,
                expires_at=inv.expires_at,
                accepted_at=inv.accepted_at,
            )
            for inv in invitations
        ]
        for m in models:
            self._session.add(m)
        await self._session.flush()
        for m in models:
            await self._session.refresh(m)
        return [_invitation_from_model(m) for m in models]

    async def get_by_id(self, invitation_id: UUID) -> Invitation | None:
        result = await self._session.execute(
            select(InvitationModel).where(InvitationModel.id == invitation_id)
        )
        model = result.scalar_one_or_none()
        return _invitation_from_model(model) if model else None

    async def get_by_token_hash(self, token_hash: str) -> Invitation | None:
        result = await self._session.execute(
            select(InvitationModel).where(InvitationModel.token_hash == token_hash)
        )
        model = result.scalar_one_or_none()
        return _invitation_from_model(model) if model else None

    async def get_pending_for_email(self, email: str) -> list[Invitation]:
        result = await self._session.execute(
            select(InvitationModel).where(
                InvitationModel.email == email,
                InvitationModel.status == "pending",
            )
        )
        return [_invitation_from_model(m) for m in result.scalars().all()]

    async def update_status(self, invitation_id: UUID, status: InvitationStatus) -> Invitation:
        from datetime import datetime

        result = await self._session.execute(
            select(InvitationModel).where(InvitationModel.id == invitation_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Invitation {invitation_id} not found")
        model.status = status.value
        if status == InvitationStatus.ACCEPTED:
            model.accepted_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(model)
        return _invitation_from_model(model)

    async def cancel(self, invitation_id: UUID) -> None:
        result = await self._session.execute(
            select(InvitationModel).where(InvitationModel.id == invitation_id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.status = InvitationStatus.CANCELLED.value
            await self._session.flush()


# ---------------------------------------------------------------------------
# JoinRequest
# ---------------------------------------------------------------------------


def _join_request_from_model(m: JoinRequestModel) -> JoinRequest:
    return JoinRequest(
        id=m.id,
        user_id=m.user_id,
        company_id=m.company_id,
        status=JoinRequestStatus(m.status),
        requested_at=m.requested_at,
        decided_at=m.decided_at,
        decided_by_user_id=m.decided_by_user_id,
    )


class SqlJoinRequestRepository(JoinRequestRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, request: JoinRequest) -> JoinRequest:
        model = JoinRequestModel(
            id=request.id,
            user_id=request.user_id,
            company_id=request.company_id,
            status=request.status.value,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _join_request_from_model(model)

    async def get_by_user_and_company(self, user_id: UUID, company_id: UUID) -> JoinRequest | None:
        result = await self._session.execute(
            select(JoinRequestModel).where(
                JoinRequestModel.user_id == user_id,
                JoinRequestModel.company_id == company_id,
            )
        )
        model = result.scalar_one_or_none()
        return _join_request_from_model(model) if model else None

    async def get_by_id(self, request_id: UUID) -> JoinRequest | None:
        result = await self._session.execute(
            select(JoinRequestModel).where(JoinRequestModel.id == request_id)
        )
        model = result.scalar_one_or_none()
        return _join_request_from_model(model) if model else None

    async def list_pending_for_company(self, company_id: UUID) -> list[JoinRequest]:
        result = await self._session.execute(
            select(JoinRequestModel).where(
                JoinRequestModel.company_id == company_id,
                JoinRequestModel.status == "pending",
            )
        )
        return [_join_request_from_model(m) for m in result.scalars().all()]

    async def decide(
        self, request_id: UUID, status: JoinRequestStatus, decided_by: UUID
    ) -> JoinRequest:
        from datetime import datetime

        result = await self._session.execute(
            select(JoinRequestModel).where(JoinRequestModel.id == request_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"JoinRequest {request_id} not found")
        model.status = status.value
        model.decided_at = datetime.now(UTC)
        model.decided_by_user_id = decided_by
        await self._session.flush()
        await self._session.refresh(model)
        return _join_request_from_model(model)

    async def cancel(self, request_id: UUID) -> None:
        result = await self._session.execute(
            select(JoinRequestModel).where(JoinRequestModel.id == request_id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.status = JoinRequestStatus.DENIED.value
            await self._session.flush()


# ---------------------------------------------------------------------------
# Password Reset Token
# ---------------------------------------------------------------------------


def _prt_from_model(m: PasswordResetTokenModel) -> PasswordResetToken:
    return PasswordResetToken(
        id=m.id,
        user_id=m.user_id,
        token_hash=m.token_hash,
        created_at=m.created_at,
        expires_at=m.expires_at,
        consumed_at=m.consumed_at,
    )


class SqlPasswordResetTokenRepository(PasswordResetTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, token: PasswordResetToken) -> PasswordResetToken:
        await self.consume_all_for_user(token.user_id)
        model = PasswordResetTokenModel(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _prt_from_model(model)

    async def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        result = await self._session.execute(
            select(PasswordResetTokenModel).where(PasswordResetTokenModel.token_hash == token_hash)
        )
        model = result.scalar_one_or_none()
        return _prt_from_model(model) if model else None

    async def consume_all_for_user(self, user_id: UUID) -> None:
        from datetime import datetime

        await self._session.execute(
            update(PasswordResetTokenModel)
            .where(
                PasswordResetTokenModel.user_id == user_id,
                PasswordResetTokenModel.consumed_at.is_(None),
            )
            .values(consumed_at=datetime.now(UTC))
        )


# ---------------------------------------------------------------------------
# SpaceMembership
# ---------------------------------------------------------------------------


def _membership_from_model(m: SpaceMembershipModel) -> SpaceMembership:
    return SpaceMembership(
        id=m.id,
        space_id=m.space_id,
        user_id=m.user_id,
        role=SpaceRole(m.role),
        invited_by_user_id=m.invited_by_user_id,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlSpaceMembershipRepository(SpaceMembershipRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, membership: SpaceMembership) -> SpaceMembership:
        model = SpaceMembershipModel(
            id=membership.id,
            space_id=membership.space_id,
            user_id=membership.user_id,
            role=membership.role.value,
            invited_by_user_id=membership.invited_by_user_id,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _membership_from_model(model)

    async def get(self, space_id: UUID, user_id: UUID) -> SpaceMembership | None:
        result = await self._session.execute(
            select(SpaceMembershipModel).where(
                SpaceMembershipModel.space_id == space_id,
                SpaceMembershipModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        return _membership_from_model(model) if model else None

    async def list_by_space(self, space_id: UUID) -> list[SpaceMembership]:
        result = await self._session.execute(
            select(SpaceMembershipModel).where(SpaceMembershipModel.space_id == space_id)
        )
        return [_membership_from_model(m) for m in result.scalars().all()]

    async def list_by_user(self, user_id: UUID) -> list[SpaceMembership]:
        result = await self._session.execute(
            select(SpaceMembershipModel).where(SpaceMembershipModel.user_id == user_id)
        )
        return [_membership_from_model(m) for m in result.scalars().all()]

    async def update_role(self, space_id: UUID, user_id: UUID, role: SpaceRole) -> SpaceMembership:
        result = await self._session.execute(
            select(SpaceMembershipModel).where(
                SpaceMembershipModel.space_id == space_id,
                SpaceMembershipModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError("not a member")
        model.role = role.value
        await self._session.flush()
        await self._session.refresh(model)
        return _membership_from_model(model)

    async def remove(self, space_id: UUID, user_id: UUID) -> None:
        result = await self._session.execute(
            select(SpaceMembershipModel).where(
                SpaceMembershipModel.space_id == space_id,
                SpaceMembershipModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError("not a member")
        await self._session.delete(model)
        await self._session.flush()

    async def count_admins(self, space_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).where(
                SpaceMembershipModel.space_id == space_id,
                SpaceMembershipModel.role == SpaceRole.ADMIN.value,
            )
        )
        return result.scalar_one()
