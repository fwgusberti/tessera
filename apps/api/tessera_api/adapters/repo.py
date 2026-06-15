"""SQLAlchemy repository implementations."""

from __future__ import annotations

from datetime import UTC
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models import (
    AgentCredentialModel,
    AuditRecordModel,
    ConnectorModel,
    DocumentModel,
    DocumentVersionModel,
    RefreshTokenModel,
    RolePermissionModel,
    SourceArtifactModel,
    SpaceModel,
    UpdateProposalModel,
    UserModel,
)
from tessera_core.domain.entities import (
    AgentCredential,
    AuditRecord,
    Chunk,
    Confidentiality,
    Connector,
    Document,
    DocumentLifecycleState,
    DocumentVersion,
    RefreshToken,
    RolePermission,
    SourceArtifact,
    Space,
    UpdateProposal,
    User,
    UserRole,
)
from tessera_core.ports.repositories import (
    AgentCredentialRepository,
    AuditRepository,
    ChunkRepository,
    ConnectorRepository,
    DocumentRepository,
    DocumentVersionRepository,
    ProposalRepository,
    SourceArtifactRepository,
    SpaceRepository,
    UserRepository,
)


def _space_from_model(m: SpaceModel) -> Space:
    return Space(
        id=m.id,
        slug=m.slug,
        name=m.name,
        sector=m.sector,
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

    async def list_all(self) -> list[Space]:
        result = await self._session.execute(select(SpaceModel))
        return [_space_from_model(m) for m in result.scalars().all()]

    async def list_for_user(self, user: User) -> list[Space]:
        return await self.list_all()

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


class SqlChunkRepository(ChunkRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_chunks(self, chunks: list[Chunk]) -> None:
        from sqlalchemy.dialects.postgresql import insert

        for chunk in chunks:
            _stmt = insert(type("chunks", (), {"__tablename__": "chunks"})).values(  # noqa: F841
                id=chunk.id,
                document_version_id=chunk.document_version_id,
                document_id=chunk.document_id,
                space_id=chunk.space_id,
                ordinal=chunk.ordinal,
                text=chunk.text,
                confidentiality=chunk.confidentiality.value,
                language=chunk.language,
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
                AND c.confidentiality = ANY(:allowed_confidentiality)
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
                "allowed_confidentiality": allowed_levels,
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
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email)
        )
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
