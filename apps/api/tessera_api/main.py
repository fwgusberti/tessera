"""Tessera API — FastAPI application entry point."""

from __future__ import annotations

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from tessera_api.auth.bearer import require_onboarding_complete
from tessera_api.config import get_settings
from tessera_api.routers import (
    admin,
    agent_credentials,
    assistant,
    auth,
    companies,
    connectors,
    documents,
    invitations,
    metrics,
    onboarding,
    proposals,
    search,
    spaces,
)

logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Tessera API",
        description="Tessera Living Documentation Platform",
        version="0.1.0",
        docs_url="/docs" if settings.environment != "production" else None,
    )

    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.environment == "development" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail:
            content = detail
        else:
            content = {"error": {"code": "http_error", "message": str(detail)}}
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", path=request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "An internal error occurred"}},
        )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    _onboarding_guard = [Depends(require_onboarding_complete)]

    app.include_router(auth.router, prefix="/v1")
    app.include_router(onboarding.router, prefix="/v1")
    app.include_router(companies.router, prefix="/v1", dependencies=_onboarding_guard)
    app.include_router(invitations.router, prefix="/v1", dependencies=_onboarding_guard)
    app.include_router(spaces.router, prefix="/v1", dependencies=_onboarding_guard)
    app.include_router(documents.router, prefix="/v1", dependencies=_onboarding_guard)
    app.include_router(search.router, prefix="/v1", dependencies=_onboarding_guard)
    app.include_router(assistant.router, prefix="/v1", dependencies=_onboarding_guard)
    app.include_router(proposals.router, prefix="/v1", dependencies=_onboarding_guard)
    app.include_router(connectors.router, prefix="/v1", dependencies=_onboarding_guard)
    app.include_router(agent_credentials.router, prefix="/v1", dependencies=_onboarding_guard)
    app.include_router(admin.router, prefix="/v1", dependencies=_onboarding_guard)
    app.include_router(metrics.router, prefix="/v1", dependencies=_onboarding_guard)

    return app


app = create_app()
