"""Error handling middleware for the FastAPI application (Phase 4)."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from pymongo.errors import ConnectionFailure, PyMongoError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.utils.logger import get_logger

logger = get_logger(__name__)


def _safe_validation_detail(exc: ValidationError) -> list[dict]:
    """Extract only safe fields (loc + msg) from Pydantic errors.

    Strips ctx, url, and input to avoid leaking internal schema details.
    """
    safe = []
    for err in exc.errors():
        safe.append(
            {
                "loc": list(err.get("loc", [])),
                "msg": err.get("msg", ""),
            }
        )
    return safe


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Catches unhandled exceptions and returns structured JSON errors.

    Specific exception types are mapped to appropriate HTTP status codes.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            return await call_next(request)
        except ValidationError as exc:
            logger.warning(
                "validation_error", path=request.url.path, error_count=exc.error_count()
            )
            return JSONResponse(
                status_code=422,
                content={
                    "error": "Validation Error",
                    "detail": _safe_validation_detail(exc),
                    "statusCode": 422,
                },
            )
        except ConnectionFailure as exc:
            logger.error(
                "mongodb_connection_failure", path=request.url.path, error=str(exc)
            )
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service Unavailable",
                    "detail": "Database connection failed",
                    "statusCode": 503,
                },
            )
        except PyMongoError as exc:
            logger.error("mongodb_error", path=request.url.path, error=str(exc))
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Database Error",
                    "detail": "An internal database error occurred",
                    "statusCode": 500,
                },
            )
        except Exception:
            logger.exception("unhandled_exception", path=request.url.path)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": "An unexpected error occurred",
                    "statusCode": 500,
                },
            )
