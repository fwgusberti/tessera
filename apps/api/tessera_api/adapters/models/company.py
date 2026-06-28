from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tessera_api.adapters.models.base import Base

if TYPE_CHECKING:
    from tessera_api.adapters.models.company_membership import CompanyMembershipModel
    from tessera_api.adapters.models.domain_join_policy import DomainJoinPolicyModel
    from tessera_api.adapters.models.invitation import InvitationModel
    from tessera_api.adapters.models.join_request import JoinRequestModel


class CompanyModel(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    team_size: Mapped[str | None] = mapped_column(String(20), nullable=True)
    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    memberships: Mapped[list[CompanyMembershipModel]] = relationship(
        "CompanyMembershipModel", back_populates="company", cascade="all, delete-orphan"
    )
    domain_policies: Mapped[list[DomainJoinPolicyModel]] = relationship(
        "DomainJoinPolicyModel", back_populates="company", cascade="all, delete-orphan"
    )
    invitations: Mapped[list[InvitationModel]] = relationship(
        "InvitationModel", back_populates="company", cascade="all, delete-orphan"
    )
    join_requests: Mapped[list[JoinRequestModel]] = relationship(
        "JoinRequestModel", back_populates="company", cascade="all, delete-orphan"
    )
