# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

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
        """Handle all GiljoAI domain exceptions.

        INF-5070: log severity is matched to HTTP status class so that the
        Sentry LoggingIntegration (event_level=ERROR by default) captures
        actual server failures while ignoring expected client errors.

        - 4xx: client error (bad credentials, missing field, not found, etc.).
          These are the normal "user input was wrong" path -- log at WARNING
          so journalctl still surfaces them but Sentry treats them as
          breadcrumbs, not as new issues.
        - 5xx (and anything outside 100-499): server-side failure that
          deserves an alert -- log at ERROR so Sentry creates an issue.

        Discovered during INF-5070 verification on the demo deployment:
        every failed /api/auth/login attempt was minting a new
        AUTHENTICATIONERROR Sentry issue and triggering an alert email.
        Public-demo traffic + bot probes would burn the 5K/month free-tier
        quota in days.
        """
        status_code = exc.default_status_code
        log_method = logger.warning if 400 <= status_code < 500 else logger.error
        log_method(f"{exc.error_code}: {exc.message}", extra={"context": exc.context})
        return JSONResponse(status_code=status_code, content=exc.to_dict())

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
            # Forward HTTPException headers (Retry-After on 429, WWW-Authenticate
            # on 401, etc.) — Starlette's default handler does; this one must too,
            # otherwise those headers are silently dropped.
            return JSONResponse(status_code=exc.status_code, content=content, headers=getattr(exc, "headers", None))

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": "HTTP_ERROR",
                "message": detail,
                "timestamp": datetime.now(UTC).isoformat(),
            },
            headers=getattr(exc, "headers", None),
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
