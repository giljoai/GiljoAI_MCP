"""Global exception handlers for FastAPI."""

import logging
from datetime import datetime, timezone

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.giljo_mcp.exceptions import BaseGiljoException


logger = logging.getLogger(__name__)


def register_exception_handlers(app):
    """Register all exception handlers with FastAPI app."""

    @app.exception_handler(BaseGiljoException)
    async def giljo_exception_handler(request: Request, exc: BaseGiljoException):
        """Handle all GiljoAI domain exceptions."""
        logger.error(f"{exc.error_code}: {exc.message}", extra={"context": exc.context})
        return JSONResponse(status_code=exc.default_status_code, content=exc.to_dict())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors."""
        # Sanitize errors for JSON serialization - convert non-serializable values to strings
        sanitized_errors = []
        for error in exc.errors():
            sanitized = {
                "loc": error.get("loc", []),
                "msg": error.get("msg", ""),
                "type": error.get("type", ""),
            }
            # Include input if it's a simple JSON-serializable type
            input_val = error.get("input")
            if input_val is not None and isinstance(input_val, (str, int, float, bool, list, dict, type(None))):
                sanitized["input"] = input_val
            sanitized_errors.append(sanitized)

        return JSONResponse(
            status_code=422,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "errors": sanitized_errors,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle legacy HTTPException (backward compatibility)."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": "HTTP_ERROR",
                "message": exc.detail,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(request: Request, exc: Exception):
        """Catch-all for unexpected exceptions."""
        logger.exception(f"Unexpected error: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
