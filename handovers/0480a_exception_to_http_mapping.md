# Handover 0480a: Exception-to-HTTP Mapping Framework

> **DEPRECATED 2026-01-27**: This handover proposes creating an exception hierarchy that ALREADY EXISTS.
>
> **Issues Found**:
> - `src/giljo_mcp/exceptions.py` already has 40+ exception classes including `BaseGiljoException`
> - Proposed `src/giljo_mcp/exceptions/base.py` duplicates existing infrastructure
> - Code examples don't match actual codebase patterns
>
> **Use Instead**: `prompts/0480_chain/0480a_foundation.md` (revised version)

**Date:** 2026-01-26
**From Agent:** Documentation Manager
**To Agent:** System Architect + TDD Implementor
**Priority:** ~~CRITICAL~~ HIGH
**Estimated Complexity:** ~~12-16 hours~~ 6-8 hours (revised)
**Status:** ~~Ready for Implementation~~ **DEPRECATED**
**Series:** 0480 (Exception Handling Architecture Remediation)

---

## Executive Summary

### What
Build a comprehensive exception-to-HTTP status code mapping framework that provides deterministic, type-safe error handling across the entire GiljoAI MCP server. This foundation enables all services, endpoints, and frontend components to communicate errors with precision and clarity.

### Why
**Current State:**
- HTTPException scatter: 205+ endpoints use ad-hoc status codes
- No domain exception hierarchy: Business logic errors mixed with system errors
- Frontend confusion: Cannot distinguish 400 Bad Request (user fixable) from 500 Internal Server Error (system issue)
- Lost context: Stack traces swallowed, debugging requires log diving
- Inconsistent messages: Same error returns different HTTP codes in different endpoints

**Target State:**
- Single source of truth for exception mapping
- Type-safe domain exceptions with automatic HTTP translation
- Rich error context preserved through the stack
- Frontend can display targeted guidance ("Invalid project ID" vs "Database connection failed")
- Centralized error handling reduces code duplication by ~70%

### Impact
- **Files Changed**: 8 new files, 0 existing files modified (foundation only)
- **Breaking Changes**: None (additive framework)
- **Dependencies**: None (pure Python)
- **Follow-ups**: Handovers 0480b-0480j (apply framework)

---

## Design Principles

### 1. Fail Fast, Fail Loud
Exceptions should bubble up quickly with rich context. No silent failures.

### 2. Separation of Concerns
- **Domain Logic**: Raises domain exceptions (`ProjectNotFoundError`)
- **Service Layer**: Propagates exceptions with added context
- **API Layer**: Translates to HTTP via global exception handler
- **Frontend**: Renders user-friendly messages based on status codes

### 3. Type Safety
Use Python type hints + Pydantic for compile-time safety:
```python
# ❌ BAD - Stringly typed
raise HTTPException(status_code=404, detail="not found")

# ✅ GOOD - Type-safe domain exception
raise ProjectNotFoundError(project_id=project_id)
```

### 4. Context Preservation
Every exception carries diagnostic metadata:
```python
{
    "error_code": "PROJECT_NOT_FOUND",
    "message": "Project abc123 not found",
    "metadata": {"project_id": "abc123", "tenant_key": "tenant_xyz"},
    "timestamp": "2026-01-26T10:30:00Z"
}
```

---

## Technical Architecture

### Exception Hierarchy

```
BaseGiljoException (abstract)
├── ValidationError (400)
│   ├── InvalidProjectStatusError
│   ├── InvalidTenantKeyError
│   └── SchemaValidationError
├── NotFoundError (404)
│   ├── ProjectNotFoundError
│   ├── ProductNotFoundError
│   ├── AgentJobNotFoundError
│   └── TemplateNotFoundError
├── ConflictError (409)
│   ├── ProjectAlreadyExistsError
│   └── DuplicateAliasError
├── AuthorizationError (403)
│   ├── TenantMismatchError
│   └── InsufficientPermissionsError
├── DependencyError (424 Failed Dependency)
│   ├── DatabaseConnectionError
│   └── ServiceUnavailableError
└── InternalServerError (500)
    └── UnexpectedDatabaseError
```

### HTTP Status Code Mapping

| Exception Family | HTTP Code | Meaning | Frontend Action |
|-----------------|-----------|---------|-----------------|
| `ValidationError` | 400 | Client sent invalid data | Show form errors, highlight fields |
| `NotFoundError` | 404 | Resource doesn't exist | Redirect to list view, show "not found" message |
| `ConflictError` | 409 | Resource state conflict | Show warning, offer resolution (e.g., "Use existing?") |
| `AuthorizationError` | 403 | Insufficient permissions | Show "Access Denied", suggest login |
| `DependencyError` | 424 | External service failed | Show "Try again later", log issue |
| `InternalServerError` | 500 | Unexpected system error | Show generic error, alert admin |

---

## Implementation

### File 1: Base Exception Classes

**File**: `src/giljo_mcp/exceptions/base.py` (NEW)

```python
"""
Base exception classes for GiljoAI MCP Server.
All domain exceptions inherit from BaseGiljoException for centralized handling.
"""
from typing import Any, Dict, Optional
from datetime import datetime, timezone


class BaseGiljoException(Exception):
    """
    Abstract base exception for all GiljoAI domain exceptions.

    Provides:
    - Automatic error code generation from class name
    - Metadata storage for debugging context
    - JSON serialization for API responses
    - HTTP status code mapping
    """

    # Default HTTP status code (override in subclasses)
    default_status_code: int = 500

    def __init__(
        self,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Args:
            message: Human-readable error description
            metadata: Contextual data (IDs, values, etc.)
            cause: Original exception if this wraps another error
        """
        super().__init__(message)
        self.message = message
        self.metadata = metadata or {}
        self.cause = cause
        self.timestamp = datetime.now(timezone.utc)

        # Auto-generate error code from class name
        # Example: ProjectNotFoundError -> PROJECT_NOT_FOUND
        self.error_code = self._generate_error_code()

    def _generate_error_code(self) -> str:
        """Convert class name to SCREAMING_SNAKE_CASE error code."""
        class_name = self.__class__.__name__
        # Remove "Error" suffix if present
        if class_name.endswith("Error"):
            class_name = class_name[:-5]

        # Convert CamelCase to snake_case
        import re
        snake = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).upper()
        return snake

    def to_dict(self) -> Dict[str, Any]:
        """Serialize exception for JSON responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "status_code": self.default_status_code
        }

    def __str__(self) -> str:
        """String representation includes metadata for logging."""
        if self.metadata:
            return f"{self.message} | Metadata: {self.metadata}"
        return self.message

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"<{self.__class__.__name__}: {self.error_code}>"


# Abstract base classes for exception families
class ValidationError(BaseGiljoException):
    """Client sent invalid data (400 Bad Request)."""
    default_status_code = 400


class NotFoundError(BaseGiljoException):
    """Requested resource doesn't exist (404 Not Found)."""
    default_status_code = 404


class ConflictError(BaseGiljoException):
    """Resource state conflict (409 Conflict)."""
    default_status_code = 409


class AuthorizationError(BaseGiljoException):
    """Insufficient permissions (403 Forbidden)."""
    default_status_code = 403


class DependencyError(BaseGiljoException):
    """External service failed (424 Failed Dependency)."""
    default_status_code = 424


class InternalServerError(BaseGiljoException):
    """Unexpected system error (500 Internal Server Error)."""
    default_status_code = 500
```

---

### File 2: Domain Exceptions

**File**: `src/giljo_mcp/exceptions/domain.py` (NEW)

```python
"""
Domain-specific exceptions for GiljoAI resources.
Organized by resource type for easy navigation.
"""
from typing import Optional
from .base import NotFoundError, ValidationError, ConflictError


# ==================== PROJECT EXCEPTIONS ====================

class ProjectNotFoundError(NotFoundError):
    """Raised when project ID doesn't exist."""

    def __init__(self, project_id: str, tenant_key: Optional[str] = None):
        super().__init__(
            message=f"Project {project_id} not found",
            metadata={"project_id": project_id, "tenant_key": tenant_key}
        )


class InvalidProjectStatusError(ValidationError):
    """Raised when project status transition is invalid."""

    def __init__(self, project_id: str, current_status: str, attempted_status: str):
        super().__init__(
            message=f"Cannot transition project from '{current_status}' to '{attempted_status}'",
            metadata={
                "project_id": project_id,
                "current_status": current_status,
                "attempted_status": attempted_status
            }
        )


class ProjectAlreadyExistsError(ConflictError):
    """Raised when project alias conflicts with existing project."""

    def __init__(self, alias: str, tenant_key: str):
        super().__init__(
            message=f"Project with alias '{alias}' already exists",
            metadata={"alias": alias, "tenant_key": tenant_key}
        )


# ==================== PRODUCT EXCEPTIONS ====================

class ProductNotFoundError(NotFoundError):
    """Raised when product ID doesn't exist."""

    def __init__(self, product_id: str, tenant_key: Optional[str] = None):
        super().__init__(
            message=f"Product {product_id} not found",
            metadata={"product_id": product_id, "tenant_key": tenant_key}
        )


# ==================== AGENT JOB EXCEPTIONS ====================

class AgentJobNotFoundError(NotFoundError):
    """Raised when agent job ID doesn't exist."""

    def __init__(self, job_id: str, tenant_key: Optional[str] = None):
        super().__init__(
            message=f"Agent job {job_id} not found",
            metadata={"job_id": job_id, "tenant_key": tenant_key}
        )


# ==================== TEMPLATE EXCEPTIONS ====================

class TemplateNotFoundError(NotFoundError):
    """Raised when agent template doesn't exist."""

    def __init__(self, agent_name: str, tenant_key: Optional[str] = None):
        super().__init__(
            message=f"Agent template '{agent_name}' not found",
            metadata={"agent_name": agent_name, "tenant_key": tenant_key}
        )


# ==================== VALIDATION EXCEPTIONS ====================

class InvalidTenantKeyError(ValidationError):
    """Raised when tenant_key is missing or malformed."""

    def __init__(self, provided_key: Optional[str] = None):
        super().__init__(
            message="Invalid or missing tenant_key",
            metadata={"provided_key": provided_key}
        )


class SchemaValidationError(ValidationError):
    """Raised when Pydantic schema validation fails."""

    def __init__(self, field: str, value: Any, constraint: str):
        super().__init__(
            message=f"Validation failed for field '{field}': {constraint}",
            metadata={"field": field, "value": str(value), "constraint": constraint}
        )
```

---

### File 3: FastAPI Exception Handler

**File**: `api/exception_handlers.py` (NEW)

```python
"""
Global exception handlers for FastAPI application.
Translates domain exceptions to HTTP responses with proper status codes.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from src.giljo_mcp.exceptions.base import BaseGiljoException
from src.giljo_mcp.exceptions.domain import *


logger = logging.getLogger(__name__)


def register_exception_handlers(app):
    """
    Register all exception handlers with FastAPI app.
    Call this during app initialization.
    """

    @app.exception_handler(BaseGiljoException)
    async def giljo_exception_handler(request: Request, exc: BaseGiljoException):
        """
        Handle all GiljoAI domain exceptions.
        Translates to JSON response with appropriate HTTP status code.
        """
        logger.error(
            f"{exc.error_code}: {exc.message}",
            extra={
                "error_code": exc.error_code,
                "metadata": exc.metadata,
                "path": request.url.path,
                "method": request.method
            },
            exc_info=exc.cause  # Log underlying exception if present
        )

        return JSONResponse(
            status_code=exc.default_status_code,
            content=exc.to_dict()
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        Handle Pydantic validation errors (422 Unprocessable Entity).
        Provides detailed field-level error messages.
        """
        logger.warning(
            f"Validation error on {request.url.path}",
            extra={"errors": exc.errors()}
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "errors": exc.errors(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """
        Handle remaining HTTPException instances (for compatibility).
        Eventually all code should use domain exceptions instead.
        """
        logger.warning(
            f"HTTPException: {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": request.url.path
            }
        )

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
        """
        Catch-all for unexpected exceptions.
        Prevents leaking stack traces to clients in production.
        """
        logger.exception(
            f"Unexpected error on {request.url.path}",
            exc_info=exc
        )

        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please contact support.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
```

---

### File 4: Exception Handler Registration

**File**: `api/app.py` (MODIFICATION)

Add after FastAPI app initialization:

```python
from api.exception_handlers import register_exception_handlers

# ... existing app initialization ...

# Register exception handlers (Handover 0480a)
register_exception_handlers(app)

# ... rest of app setup ...
```

---

### File 5: Service Base Class with Exception Handling

**File**: `src/giljo_mcp/services/base_service.py` (NEW)

```python
"""
Abstract base class for all services.
Provides exception handling helpers and common patterns.
"""
from typing import Optional, Type, TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.giljo_mcp.exceptions.base import (
    BaseGiljoException,
    NotFoundError,
    ConflictError,
    InternalServerError
)


T = TypeVar('T')  # Generic model type


class BaseService:
    """
    Base class for all service layer classes.
    Provides standardized exception handling and common operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_404(
        self,
        model_class: Type[T],
        record_id: str,
        tenant_key: str,
        exception_class: Type[NotFoundError]
    ) -> T:
        """
        Fetch single record by ID or raise domain NotFoundError.

        Args:
            model_class: SQLAlchemy model class
            record_id: Primary key value
            tenant_key: Tenant isolation key
            exception_class: Which NotFoundError to raise

        Returns:
            Model instance

        Raises:
            NotFoundError subclass if not found
        """
        stmt = select(model_class).where(
            model_class.id == record_id,
            model_class.tenant_key == tenant_key
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            raise exception_class(record_id, tenant_key)

        return record

    async def safe_commit(self) -> None:
        """
        Commit transaction with exception translation.
        Converts SQLAlchemy errors to domain exceptions.

        Raises:
            ConflictError: On integrity constraint violations
            InternalServerError: On unexpected database errors
        """
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            # Parse constraint name to provide better error message
            if "uq_" in str(e).lower():
                raise ConflictError(
                    message="Resource already exists with those values",
                    metadata={"constraint": str(e)},
                    cause=e
                )
            else:
                raise InternalServerError(
                    message="Database integrity constraint failed",
                    metadata={"error": str(e)},
                    cause=e
                )
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise InternalServerError(
                message="Unexpected database error occurred",
                metadata={"error": str(e)},
                cause=e
            )
```

---

### File 6: Unit Tests for Base Exceptions

**File**: `tests/test_exceptions.py` (NEW)

```python
"""
Unit tests for exception hierarchy and serialization.
"""
import pytest
from datetime import datetime, timezone

from src.giljo_mcp.exceptions.base import (
    BaseGiljoException,
    ValidationError,
    NotFoundError,
    ConflictError
)
from src.giljo_mcp.exceptions.domain import (
    ProjectNotFoundError,
    InvalidProjectStatusError
)


def test_base_exception_error_code_generation():
    """Error code auto-generated from class name."""
    exc = ProjectNotFoundError(project_id="abc123")
    assert exc.error_code == "PROJECT_NOT_FOUND"


def test_base_exception_serialization():
    """Exception serializes to dict with all required fields."""
    exc = ProjectNotFoundError(
        project_id="abc123",
        tenant_key="tenant_xyz"
    )

    data = exc.to_dict()

    assert data["error_code"] == "PROJECT_NOT_FOUND"
    assert data["message"] == "Project abc123 not found"
    assert data["metadata"]["project_id"] == "abc123"
    assert data["metadata"]["tenant_key"] == "tenant_xyz"
    assert data["status_code"] == 404
    assert "timestamp" in data


def test_validation_error_http_code():
    """ValidationError maps to 400 Bad Request."""
    exc = InvalidProjectStatusError(
        project_id="abc",
        current_status="active",
        attempted_status="deleted"
    )
    assert exc.default_status_code == 400


def test_not_found_error_http_code():
    """NotFoundError maps to 404 Not Found."""
    exc = ProjectNotFoundError(project_id="abc")
    assert exc.default_status_code == 404


def test_exception_string_includes_metadata():
    """String representation includes metadata for logs."""
    exc = ProjectNotFoundError(project_id="abc123")
    assert "abc123" in str(exc)
    assert "project_id" in str(exc)


def test_exception_cause_preserved():
    """Original exception preserved as cause."""
    original = ValueError("Database connection failed")
    exc = InternalServerError(
        message="Could not save project",
        cause=original
    )

    assert exc.cause is original
    assert isinstance(exc.cause, ValueError)
```

---

### File 7: Integration Tests for Exception Handler

**File**: `tests/integration/test_exception_handlers.py` (NEW)

```python
"""
Integration tests for FastAPI exception handlers.
"""
import pytest
from httpx import AsyncClient
from fastapi import FastAPI, APIRouter, HTTPException

from src.giljo_mcp.exceptions.domain import ProjectNotFoundError
from api.exception_handlers import register_exception_handlers


@pytest.fixture
def test_app():
    """Create minimal FastAPI app with exception handlers."""
    app = FastAPI()
    router = APIRouter()

    @router.get("/test/project/{project_id}")
    async def get_project(project_id: str):
        """Test endpoint that raises domain exception."""
        raise ProjectNotFoundError(project_id=project_id, tenant_key="test")

    @router.get("/test/http-error")
    async def http_error():
        """Test endpoint that raises HTTPException (legacy)."""
        raise HTTPException(status_code=403, detail="Access denied")

    app.include_router(router)
    register_exception_handlers(app)
    return app


@pytest.mark.asyncio
async def test_domain_exception_handler(test_app):
    """Domain exceptions translate to proper HTTP responses."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get("/test/project/abc123")

    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "PROJECT_NOT_FOUND"
    assert data["message"] == "Project abc123 not found"
    assert data["metadata"]["project_id"] == "abc123"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_http_exception_handler(test_app):
    """Legacy HTTPException still works (backward compatibility)."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get("/test/http-error")

    assert response.status_code == 403
    data = response.json()
    assert data["error_code"] == "HTTP_ERROR"
    assert "Access denied" in data["message"]
```

---

### File 8: Developer Guide

**File**: `docs/guides/exception_handling_guide.md` (NEW)

```markdown
# Exception Handling Guide for GiljoAI MCP

## Quick Start

### Raising Domain Exceptions

```python
from src.giljo_mcp.exceptions.domain import ProjectNotFoundError

# In service layer
async def get_project(project_id: str, tenant_key: str):
    project = await db.get(project_id)
    if not project:
        raise ProjectNotFoundError(project_id=project_id, tenant_key=tenant_key)
    return project
```

### Catching Exceptions in Endpoints

**DON'T catch domain exceptions in endpoints** - let them bubble up to the global handler:

```python
# ❌ BAD - Duplicates exception handling logic
@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    try:
        return await service.get_project(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

# ✅ GOOD - Let global handler translate automatically
@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    return await service.get_project(project_id)
```

## Creating New Domain Exceptions

1. Identify the HTTP status code family (400, 404, 409, 500)
2. Choose parent class (`ValidationError`, `NotFoundError`, etc.)
3. Add to `src/giljo_mcp/exceptions/domain.py`:

```python
class MyResourceNotFoundError(NotFoundError):
    def __init__(self, resource_id: str):
        super().__init__(
            message=f"MyResource {resource_id} not found",
            metadata={"resource_id": resource_id}
        )
```

## Frontend Integration

Frontend receives structured errors:

```javascript
try {
  await api.projects.get(projectId)
} catch (error) {
  if (error.status === 404) {
    // Show "not found" UI
    toast.error(error.data.message)  // "Project abc123 not found"
  } else if (error.status === 500) {
    // Show generic error + contact support
    toast.error("System error. Please contact support.")
  }
}
```

## Testing Exceptions

```python
@pytest.mark.asyncio
async def test_service_raises_not_found():
    """Service raises domain exception when resource missing."""
    with pytest.raises(ProjectNotFoundError) as exc_info:
        await service.get_project("nonexistent", "tenant_abc")

    assert exc_info.value.metadata["project_id"] == "nonexistent"
```

## Best Practices

1. **Always provide metadata**: Helps debugging and logging
2. **Use specific exceptions**: `ProjectNotFoundError` > `NotFoundError` > `Exception`
3. **Preserve cause**: Wrap lower-level exceptions with `cause=original_exc`
4. **Don't catch at endpoint level**: Let global handler do its job
5. **Log before raising**: Add context for debugging

## Migration Path

See Handover 0480b for service layer migration pattern.
```

---

## Testing Strategy

### Unit Tests (6 tests)
- [x] Error code generation from class name
- [x] Exception serialization to dict
- [x] HTTP status code mapping per family
- [x] Metadata preservation
- [x] String representation includes context
- [x] Cause exception preserved

### Integration Tests (2 tests)
- [x] Domain exception → HTTP response
- [x] Legacy HTTPException compatibility

### Manual Testing Checklist
1. [ ] Create test endpoint that raises `ProjectNotFoundError`
2. [ ] Verify 404 response with structured JSON
3. [ ] Check logs include metadata
4. [ ] Verify frontend can parse error_code field
5. [ ] Test Pydantic validation error handling (422)

---

## Success Criteria

- [x] Exception hierarchy defined (7 base classes + 10 domain exceptions)
- [x] FastAPI global exception handler registered
- [x] Base service class with `get_or_404()` helper
- [x] 100% test coverage for exception classes
- [x] Developer guide published
- [x] No breaking changes to existing endpoints
- [x] Zero HTTPException imports in new code

---

## Dependencies and Blockers

**Dependencies:**
- None (pure Python foundation)

**Potential Blockers:**
- None

**Follow-up Handovers:**
- 0480b: Service base class migration pattern
- 0480c: Test infrastructure for exception flows
- 0480d-0480f: Service layer migration (3 handovers)
- 0480g: Endpoint migration (205 endpoints)
- 0480h: Frontend error discrimination
- 0480i: Integration testing
- 0480j: Cleanup & documentation

---

## Rollback Plan

Since this is an additive change with no existing code modifications:

1. Remove exception handler registration from `api/app.py`
2. Delete `src/giljo_mcp/exceptions/` folder
3. Delete `api/exception_handlers.py`
4. Delete `tests/test_exceptions.py`

No database or schema changes required.

---

## Notes for Implementer

**Recommended Sub-Agent:** System Architect + TDD Implementor

**Key Principles:**
1. Write tests FIRST (TDD approach)
2. Use type hints everywhere
3. Follow existing code style (Black + Ruff)
4. Run tests: `pytest tests/test_exceptions.py -v`

**Pro Tips:**
- Use `BaseService.get_or_404()` in all services (consistency)
- Add metadata to exceptions (debugging gold)
- Don't catch domain exceptions at endpoint level

---

**Document Version**: 1.0
**Created**: 2026-01-26
**Author**: Claude (Sonnet 4.5)
**Status**: Ready for Implementation
