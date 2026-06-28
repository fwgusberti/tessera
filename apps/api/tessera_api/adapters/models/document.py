from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, Date, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tessera_api.adapters.models.base import Base

if TYPE_CHECKING:
    from tessera_api.adapters.models.document_version import DocumentVersionModel
    from tessera_api.adapters.models.space import SpaceModel
    from tessera_api.adapters.models.update_proposal import UpdateProposalModel


class DocumentModel(Base):
    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_space_state", "space_id", "state"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    space_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="pt-BR")
    confidentiality: Mapped[str] = mapped_column(String(50), nullable=False, default="internal")
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    validity_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="ingested")
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    space: Mapped[SpaceModel] = relationship("SpaceModel", back_populates="documents")
    versions: Mapped[list[DocumentVersionModel]] = relationship(
        "DocumentVersionModel",
        back_populates="document",
        foreign_keys="[DocumentVersionModel.document_id]",
    )
    proposals: Mapped[list[UpdateProposalModel]] = relationship(
        "UpdateProposalModel", back_populates="document"
    )
