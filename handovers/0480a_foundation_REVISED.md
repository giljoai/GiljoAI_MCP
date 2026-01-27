# Handover 0480a: Exception Framework Foundation (REVISED)

**Date:** 2026-01-27
**From Agent:** Orchestrator
**To Agent:** System Architect + TDD Implementor
**Priority:** HIGH
**Estimated Complexity:** 6-8 hours
**Status:** Ready for Implementation
**Series:** 0480 (Exception Handling Remediation - REVISED)

---

## Executive Summary

### What
Add HTTP status code mapping to the EXISTING exception hierarchy and create a global FastAPI exception handler.

### Why
- Services currently return `{"success": False, "error": "..."}` dicts
- Existing exception classes in `src/giljo_mcp/exceptions.py` are not being used
- No automatic translation from exceptions to HTTP responses

### Critical Context
**DO NOT** create new exception files. The exception hierarchy already exists:
- Location: `src/giljo_mcp/exceptions.py`
- Contains: 40+ exception classes including `BaseGiljoException`

---

## Tasks

### Task 1: Modify BaseGiljoException

**File:** `src/giljo_mcp/exceptions.py`

Add these attributes and methods to the existing `BaseGiljoException` class:

```python
from datetime import datetime, timezone

class BaseGiljoException(Exception):
    """Base exception with HTTP status code mapping."""

    default_status_code: int = 500  # Override in subclasses

    def __init__(self, message: str, error_code: Optional[str] = None, context: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.context = context or {}
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """Serialize for JSON response."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "status_code": self.default_status_code
        }
```

### Task 2: Add HTTP Status Codes to Existing Exception Classes

Add `default_status_code` to each exception family:

```python
class ValidationError(BaseGiljoException):
    default_status_code = 400

class ResourceNotFoundError(ResourceError):
    default_status_code = 404

class AuthenticationError(APIError):
    default_status_code = 401

class AuthorizationError(APIError):
    default_status_code = 403

class DatabaseError(BaseGiljoException):
    default_status_code = 500
```

### Task 3: Create Global Exception Handler

**File:** `api/exception_handlers.py` (NEW)

```python
"""Global exception handlers for FastAPI."""
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from datetime import datetime, timezone

from src.giljo_mcp.exceptions import BaseGiljoException

logger = logging.getLogger(__name__)


def register_exception_handlers(app):
    """Register all exception handlers with FastAPI app."""

    @app.exception_handler(BaseGiljoException)
    async def giljo_exception_handler(request: Request, exc: BaseGiljoException):
        """Handle all GiljoAI domain exceptions."""
        logger.error(f"{exc.error_code}: {exc.message}", extra={"context": exc.context})
        return JSONResponse(
            status_code=exc.default_status_code,
            content=exc.to_dict()
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors."""
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "errors": exc.errors(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle legacy HTTPException (backward compatibility)."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": "HTTP_ERROR",
                "message": exc.detail,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
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
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
```

### Task 4: Register Handler in app.py

**File:** `api/app.py`

Add after FastAPI app initialization:

```python
from api.exception_handlers import register_exception_handlers

# ... existing app initialization ...

register_exception_handlers(app)
```

### Task 5: Write Tests

**File:** `tests/test_exception_handlers.py` (NEW)

Test cases:
- Exception error_code generation from class name
- to_dict() serialization includes all fields
- HTTP status code mapping per exception family
- Global handler returns correct status codes
- Legacy HTTPException still works

---

## Success Criteria

- [ ] `BaseGiljoException` has `default_status_code` and `to_dict()`
- [ ] All exception classes have appropriate HTTP status codes
- [ ] Global handler registered in FastAPI app
- [ ] Tests pass for exception → HTTP translation
- [ ] Existing functionality not broken

---

## Files Changed

| File | Action |
|------|--------|
| `src/giljo_mcp/exceptions.py` | MODIFY - add HTTP codes |
| `api/exception_handlers.py` | CREATE - global handler |
| `api/app.py` | MODIFY - register handler |
| `tests/test_exception_handlers.py` | CREATE - tests |

---

## Reference

- Existing exceptions: `src/giljo_mcp/exceptions.py`
- Master handover: `handovers/0480_exception_handling_remediation_REVISED.md`
