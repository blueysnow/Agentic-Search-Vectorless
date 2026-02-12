"""FastAPI application setup (Phase 4).

Provides the app factory, lifespan, CORS, rate limiting, and health check.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.api.middleware import ErrorHandlingMiddleware
from src.api.models import ErrorResponse, HealthResponse
from src.api.routes.documents import router as documents_router
from src.api.routes.ingest import router as ingest_router
from src.api.routes.query import router as query_router
from src.api.routes.sessions import router as sessions_router
from src.config import get_settings
from src.db.client import close_client, get_client
from src.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)

# Rate limiter (keyed by remote address)
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: setup logging and verify MongoDB on startup, cleanup on shutdown."""
    setup_logging()
    logger.info("starting_application")
    try:
        client = get_client()
        client.admin.command("ping")
        logger.info("mongodb_connection_verified")
    except Exception:
        logger.exception("mongodb_connection_failed_at_startup")
        raise
    yield
    close_client()
    logger.info("application_shut_down")


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content=ErrorResponse(
            error="Rate Limit Exceeded",
            detail="Rate limit exceeded",
            status_code=429,
        ).model_dump(by_alias=True),
    )


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Agentic Search API",
        description="Vectorless RAG System: PageIndex + MongoDB + Atlas Search + LLM Reasoning",
        version="0.1.0",
        lifespan=lifespan,
    )

    # -- Middleware (order matters: outermost first) --
    app.add_middleware(ErrorHandlingMiddleware)

    # CORS -- only enabled when cors_origins is explicitly configured
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "Authorization"],
        )

    # Rate limiting
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

    # -- Routes (no prefix overlap: ingest uses /ingest, documents uses /documents) --
    app.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
    app.include_router(query_router, prefix="/query", tags=["query"])
    app.include_router(documents_router, prefix="/documents", tags=["documents"])
    app.include_router(sessions_router, prefix="/sessions", tags=["sessions"])

    # -- Health check --
    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def health_check() -> HealthResponse:
        mongo_status = "unknown"
        try:
            get_client().admin.command("ping")
            mongo_status = "connected"
        except Exception:
            mongo_status = "disconnected"
        return HealthResponse(status="ok", mongodb=mongo_status)

    return app
