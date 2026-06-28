from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tessera_api.adapters.models.base import Base

if TYPE_CHECKING:
    from tessera_api.adapters.models.connector import ConnectorModel
    from tessera_api.adapters.models.document import DocumentModel
    from tessera_api.adapters.models.role_permission import RolePermissionModel


class SpaceModel(Base):
    __tablename__ = "spaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    taxonomy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    retention_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    confidence_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    default_language: Mapped[str] = mapped_column(String(10), nullable=False, default="pt-BR")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    permissions: Mapped[list[RolePermissionModel]] = relationship(
        "RolePermissionModel", back_populates="space"
    )
    documents: Mapped[list[DocumentModel]] = relationship("DocumentModel", back_populates="space")
    connectors: Mapped[list[ConnectorModel]] = relationship(
        "ConnectorModel", back_populates="space"
    )
