"""Metrics endpoint — product-level metrics (SC-008, FR-026)."""

from fastapi import APIRouter, Request

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def get_metrics(request: Request) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.auth.oidc import require_user
    from sqlalchemy import select, func, text
    from tessera_api.adapters.models import AuditRecordModel, UpdateProposalModel

    user_info = await require_user(request)
    if not user_info.get("is_admin"):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Admin required")

    async with get_db() as session:
        # Count query actions
        query_count = (
            await session.execute(
                select(func.count()).where(AuditRecordModel.action == "query")
            )
        ).scalar() or 0

        # Proposals stats
        pending = (
            await session.execute(
                select(func.count()).where(UpdateProposalModel.state == "pending")
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
