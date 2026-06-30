"""Metrics endpoint — product-level metrics (SC-008, FR-026).

Company-scoped (feature 035): counts reflect only the active company. Query
volume is derived from ``query`` audit records tagged with the company id, and
pending-proposal/drift counts are scoped via the proposal → document → space join.
"""

from fastapi import APIRouter
from sqlalchemy import func, select

from tessera_api.adapters.database import SessionDep
from tessera_api.adapters.models import (
    AuditRecordModel,
    DocumentModel,
    SpaceModel,
    UpdateProposalModel,
)
from tessera_api.auth.oidc import CompanyAdminContext

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def get_metrics(ctx: CompanyAdminContext, session: SessionDep) -> dict:
    _user_info, company_id, _membership = ctx

    # Queries attributed to the active company (tagged in the "query" audit).
    query_count = (
        await session.execute(
            select(func.count()).where(
                AuditRecordModel.action == "query",
                AuditRecordModel.record_metadata["company_id"].astext == str(company_id),
            )
        )
    ).scalar() or 0

    # Pending proposals whose document's space belongs to the active company.
    pending = (
        await session.execute(
            select(func.count())
            .select_from(UpdateProposalModel)
            .join(DocumentModel, DocumentModel.id == UpdateProposalModel.document_id)
            .join(SpaceModel, SpaceModel.id == DocumentModel.space_id)
            .where(
                UpdateProposalModel.state == "pending",
                SpaceModel.company_id == company_id,
            )
        )
    ).scalar() or 0

    return {
        "correct_answer_rate": None,
        "dont_know_rate": None,
        "documents_with_drift": pending,
        "time_to_approval_p50": None,
        "time_to_approval_p90": None,
        "total_queries": query_count,
    }
