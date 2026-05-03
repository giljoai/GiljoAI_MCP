# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Global exception handlers for FastAPI."""

import logging
from datetime import UTC, datetime

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from giljo_mcp.exceptions import BaseGiljoError


logger = logging.getLogger(__name__)


def register_exception_handlers(app):
    """Register all exception handlers with FastAPI app."""

    @app.exception_handler(BaseGiljoError)
    async def giljo_exception_handler(request: Request, exc: BaseGiljoError):
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
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle legacy HTTPException.

        Back-compat contract: HTTPException raised with a plain string detail
        produces ``{"error_code": "HTTP_ERROR", "message": "<str>"}``.

        SEC-0001 extension: if ``exc.detail`` is a dict that already carries
        a machine-readable ``error_code`` (e.g. ``UPLOAD_TOO_LARGE``), lift
        that code to the response top level so the frontend's
        ``parseErrorResponse`` (``frontend/src/utils/errorMessages.js:140``)
        picks it up via its first branch. This matches the shape emitted by
        ``BaseGiljoError`` exceptions and keeps both paths symmetric.
        """
        detail = exc.detail
        if isinstance(detail, dict) and isinstance(detail.get("error_code"), str):
            content = {
                "error_code": detail["error_code"],
                "message": detail.get("message", ""),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            context = {k: v for k, v in detail.items() if k not in {"error_code", "message"}}
            if context:
                content["context"] = context
            return JSONResponse(status_code=exc.status_code, content=content)

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": "HTTP_ERROR",
                "message": detail,
                "timestamp": datetime.now(UTC).isoformat(),
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
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
