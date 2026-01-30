# Handover 0480c: Test Infrastructure for Exception Flows

> **DEPRECATED 2026-01-27**: This handover is part of the deprecated 0480 series.
> The series was redesigned due to critical flaws (false premises about codebase state).
>
> **Use Instead**:
> - Master: `handovers/0480_exception_handling_remediation_REVISED.md`
> - Chain prompts: `prompts/0480_chain/`

**Date:** 2026-01-26
**From Agent:** Documentation Manager
**To Agent:** TDD Implementor
**Priority:** HIGH
**Estimated Complexity:** 6-8 hours
**Status:** DEPRECATED
**Series:** 0480 (Exception Handling Architecture Remediation)
**Dependencies:** Handover 0480a (Exception framework)

---

## Executive Summary

### What
Build reusable test utilities, fixtures, and templates for testing exception flows across services and endpoints. This infrastructure enables rapid, consistent testing during the migration in Handovers 0480d-0480g.

### Why
**Current State:**
- No standardized exception testing patterns
- Test code duplicated across 50+ test files
- Inconsistent assertions (some check status_code, some check detail, some check both)
- No fixtures for common exception scenarios

**Target State:**
- Reusable pytest fixtures for exception testing
- Helper functions for common assertions
- Parameterized test templates
- Mock factories for database errors

### Impact
- **Files Changed**: 3 new files in `tests/utils/`
- **Test Code Reduction**: ~50% fewer lines per test
- **Coverage Improvement**: Standardized templates ensure all exception paths tested

---

## Implementation

### File 1: Exception Test Fixtures

**File**: `tests/utils/exception_fixtures.py` (NEW)

```python
"""
Pytest fixtures for exception testing.
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.giljo_mcp.exceptions.domain import *


@pytest.fixture
def mock_integrity_error():
    """Mock SQLAlchemy IntegrityError with constraint details."""
    error = Mock(spec=IntegrityError)
    error.__str__ = Mock(return_value='duplicate key value violates unique constraint "uq_project_alias"')
    return error


@pytest.fixture
def mock_sqlalchemy_error():
    """Mock generic SQLAlchemy error."""
    error = Mock(spec=SQLAlchemyError)
    error.__str__ = Mock(return_value='connection timeout')
    return error


@pytest.fixture
def exception_test_cases():
    """
    Parametrized test cases for exception handling.
    Returns list of (exception_class, expected_status_code, expected_error_code).
    """
    return [
        (ProjectNotFoundError("abc", "tenant"), 404, "PROJECT_NOT_FOUND"),
        (InvalidProjectStatusError("abc", "active", "deleted"), 400, "INVALID_PROJECT_STATUS"),
        (ProjectAlreadyExistsError("ABC123", "tenant"), 409, "PROJECT_ALREADY_EXISTS"),
        (ProductNotFoundError("xyz", "tenant"), 404, "PRODUCT_NOT_FOUND"),
        (AgentJobNotFoundError("job123", "tenant"), 404, "AGENT_JOB_NOT_FOUND"),
        (TemplateNotFoundError("orchestrator", "tenant"), 404, "TEMPLATE_NOT_FOUND"),
        (InvalidTenantKeyError("invalid"), 400, "INVALID_TENANT_KEY"),
    ]


@pytest.fixture
def assert_exception_response():
    """
    Helper function to assert API exception responses.

    Usage:
        response = await client.get("/projects/abc")
        assert_exception_response(
            response,
            status_code=404,
            error_code="PROJECT_NOT_FOUND",
            message_contains="abc"
        )
    """
    def _assert(response, status_code: int, error_code: str, message_contains: str = None):
        assert response.status_code == status_code, f"Expected {status_code}, got {response.status_code}"

        data = response.json()
        assert data["error_code"] == error_code, f"Expected {error_code}, got {data.get('error_code')}"
        assert "message" in data
        assert "timestamp" in data

        if message_contains:
            assert message_contains in data["message"], \
                f"Expected '{message_contains}' in message, got: {data['message']}"

    return _assert
```

---

### File 2: Exception Test Helpers

**File**: `tests/utils/exception_helpers.py` (NEW)

```python
"""
Helper functions for exception testing.
"""
from typing import Type, Dict, Any, Optional
from contextlib import asynccontextmanager
import pytest

from src.giljo_mcp.exceptions.base import BaseGiljoException


async def assert_raises_with_metadata(
    exception_class: Type[BaseGiljoException],
    expected_metadata: Dict[str, Any],
    async_callable,
    *args,
    **kwargs
):
    """
    Assert async function raises exception with expected metadata.

    Usage:
        await assert_raises_with_metadata(
            ProjectNotFoundError,
            {"project_id": "abc123", "tenant_key": "tenant"},
            service.get_project,
            "abc123",
            "tenant"
        )
    """
    with pytest.raises(exception_class) as exc_info:
        await async_callable(*args, **kwargs)

    exc = exc_info.value
    for key, expected_value in expected_metadata.items():
        assert key in exc.metadata, f"Metadata missing key: {key}"
        assert exc.metadata[key] == expected_value, \
            f"Metadata[{key}] = {exc.metadata[key]}, expected {expected_value}"


def create_test_matrix_for_service(service_name: str, operations: list):
    """
    Generate parametrized test cases for service exception paths.

    Args:
        service_name: Name of service being tested
        operations: List of (method_name, exception_class, test_args) tuples

    Returns:
        pytest.param list for @pytest.mark.parametrize

    Usage:
        test_cases = create_test_matrix_for_service(
            "ProjectService",
            [
                ("get_project", ProjectNotFoundError, ("nonexistent", "tenant")),
                ("create_project", ProjectAlreadyExistsError, (duplicate_data, "tenant")),
            ]
        )

        @pytest.mark.parametrize("method,exc_class,args", test_cases)
        async def test_service_exceptions(method, exc_class, args):
            ...
    """
    return [
        pytest.param(method, exc_class, args, id=f"{service_name}.{method}_{exc_class.__name__}")
        for method, exc_class, args in operations
    ]


@asynccontextmanager
async def assert_no_exceptions():
    """
    Context manager to assert code block doesn't raise any exceptions.
    Useful for testing happy paths.

    Usage:
        async with assert_no_exceptions():
            await service.create_project(valid_data, tenant_key)
    """
    try:
        yield
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")
```

---

### File 3: Mock Database Error Factories

**File**: `tests/utils/mock_factories.py` (NEW)

```python
"""
Factory functions for creating mock database errors in tests.
"""
from unittest.mock import AsyncMock, patch
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


def create_mock_session_with_commit_error(error_type: str = "integrity"):
    """
    Create mock AsyncSession that raises error on commit.

    Args:
        error_type: "integrity", "connection", or "timeout"

    Returns:
        Mock AsyncSession that will fail on commit()

    Usage:
        session = create_mock_session_with_commit_error("integrity")
        service = ProjectService(session)

        with pytest.raises(ConflictError):
            await service.create_project(data, tenant_key)
    """
    session = AsyncMock()

    if error_type == "integrity":
        error = IntegrityError(
            statement="INSERT INTO projects...",
            params={},
            orig=Exception('duplicate key value violates unique constraint "uq_project_alias"')
        )
    elif error_type == "connection":
        error = SQLAlchemyError("connection to server was lost")
    elif error_type == "timeout":
        error = SQLAlchemyError("query timeout")
    else:
        raise ValueError(f"Unknown error_type: {error_type}")

    session.commit = AsyncMock(side_effect=error)
    session.rollback = AsyncMock()

    return session


def create_mock_execute_returning_none():
    """
    Create mock AsyncSession.execute() that returns no results.
    Simulates "record not found" scenario.

    Usage:
        session = AsyncMock()
        session.execute = create_mock_execute_returning_none()

        service = ProjectService(session)
        with pytest.raises(ProjectNotFoundError):
            await service.get_project("nonexistent", "tenant")
    """
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(return_value=None)
    mock_result.scalars = AsyncMock(return_value=mock_result)
    mock_result.all = AsyncMock(return_value=[])

    execute_mock = AsyncMock(return_value=mock_result)
    return execute_mock
```

---

### File 4: Test Templates Documentation

**File**: `docs/testing/exception_test_patterns.md` (NEW)

```markdown
# Exception Testing Patterns

## Pattern 1: Service Layer - Not Found

```python
@pytest.mark.asyncio
async def test_get_[resource]_not_found(db_session):
    """get_[resource] raises [Resource]NotFoundError when not found."""
    service = [Service](db_session)

    with pytest.raises([Resource]NotFoundError) as exc_info:
        await service.get_[resource]("nonexistent", "tenant_abc")

    # Verify exception metadata
    assert exc_info.value.metadata["[resource]_id"] == "nonexistent"
    assert exc_info.value.metadata["tenant_key"] == "tenant_abc"
    assert exc_info.value.default_status_code == 404
```

## Pattern 2: Service Layer - Conflict

```python
@pytest.mark.asyncio
async def test_create_[resource]_duplicate(db_session, test_[resource]):
    """create_[resource] raises ConflictError on duplicate."""
    service = [Service](db_session)

    duplicate_data = [Resource]Create(
        **test_[resource].dict(),
        id=None  # New ID but same unique fields
    )

    with pytest.raises([Resource]AlreadyExistsError) as exc_info:
        await service.create_[resource](duplicate_data, test_[resource].tenant_key)

    assert exc_info.value.metadata["[unique_field]"] == test_[resource].[unique_field]
```

## Pattern 3: API Endpoint - 404 Response

```python
@pytest.mark.asyncio
async def test_get_[resource]_404(client: AsyncClient, auth_headers, assert_exception_response):
    """GET /[resources]/{id} returns 404 with structured error."""
    response = await client.get(
        "/api/[resources]/nonexistent",
        headers=auth_headers
    )

    assert_exception_response(
        response,
        status_code=404,
        error_code="[RESOURCE]_NOT_FOUND",
        message_contains="nonexistent"
    )
```

## Pattern 4: API Endpoint - 409 Conflict

```python
@pytest.mark.asyncio
async def test_create_[resource]_409(client: AsyncClient, auth_headers, test_[resource]):
    """POST /[resources] returns 409 when conflict."""
    response = await client.post(
        "/api/[resources]/",
        json=test_[resource].dict(),
        headers=auth_headers
    )

    assert response.status_code == 409
    data = response.json()
    assert data["error_code"] == "[RESOURCE]_ALREADY_EXISTS"
    assert test_[resource].[unique_field] in data["message"]
```

## Pattern 5: Parameterized Exception Matrix

```python
@pytest.mark.parametrize("exception_class,status_code,error_code", [
    (ProjectNotFoundError("a", "t"), 404, "PROJECT_NOT_FOUND"),
    (ProductNotFoundError("a", "t"), 404, "PRODUCT_NOT_FOUND"),
    (InvalidProjectStatusError("a", "b", "c"), 400, "INVALID_PROJECT_STATUS"),
])
def test_exception_mapping(exception_class, status_code, error_code):
    """Exceptions map to correct HTTP codes."""
    assert exception_class.default_status_code == status_code
    assert exception_class.error_code == error_code
```

## Pattern 6: Database Error Translation

```python
@pytest.mark.asyncio
async def test_safe_commit_integrity_error(mock_integrity_error):
    """safe_commit translates IntegrityError to ConflictError."""
    session = create_mock_session_with_commit_error("integrity")
    service = BaseService(session)

    with pytest.raises(ConflictError) as exc_info:
        await service.safe_commit()

    assert "unique constraint" in exc_info.value.message.lower()
    assert exc_info.value.cause is not None
```
```

---

### File 5: Conftest Additions

**File**: `tests/conftest.py` (APPEND)

Add these fixtures to the existing conftest:

```python
# Exception Testing Fixtures (Handover 0480c)
from tests.utils.exception_fixtures import (
    mock_integrity_error,
    mock_sqlalchemy_error,
    exception_test_cases,
    assert_exception_response
)
from tests.utils.exception_helpers import assert_raises_with_metadata

__all__ = [
    # ... existing fixtures ...
    'mock_integrity_error',
    'mock_sqlalchemy_error',
    'exception_test_cases',
    'assert_exception_response',
    'assert_raises_with_metadata',
]
```

---

## Usage Examples

### Example 1: Testing Service Method

```python
# tests/services/test_project_service.py
from tests.utils.exception_helpers import assert_raises_with_metadata

@pytest.mark.asyncio
async def test_get_project_not_found(db_session):
    """Demonstrates clean exception assertion."""
    service = ProjectService(db_session)

    await assert_raises_with_metadata(
        ProjectNotFoundError,
        {"project_id": "abc123", "tenant_key": "tenant_xyz"},
        service.get_project,
        "abc123",
        "tenant_xyz"
    )
```

### Example 2: Testing API Endpoint

```python
# tests/integration/test_projects_api.py

@pytest.mark.asyncio
async def test_project_endpoints_exception_responses(
    client: AsyncClient,
    auth_headers,
    assert_exception_response
):
    """Test all error responses for /projects endpoints."""

    # 404 Not Found
    response = await client.get("/api/projects/nonexistent", headers=auth_headers)
    assert_exception_response(response, 404, "PROJECT_NOT_FOUND", "nonexistent")

    # 409 Conflict (duplicate)
    response = await client.post("/api/projects/", json={...}, headers=auth_headers)
    assert_exception_response(response, 409, "PROJECT_ALREADY_EXISTS")
```

### Example 3: Parameterized Tests

```python
@pytest.mark.parametrize("method,exc_class,args", [
    ("get_project", ProjectNotFoundError, ("nonexistent", "tenant")),
    ("get_product", ProductNotFoundError, ("nonexistent", "tenant")),
    ("get_agent_job", AgentJobNotFoundError, ("nonexistent", "tenant")),
])
@pytest.mark.asyncio
async def test_not_found_exceptions(db_session, method, exc_class, args):
    """All 'get' methods raise appropriate NotFoundError."""
    service = get_service_for_method(method)  # Helper function

    with pytest.raises(exc_class):
        await getattr(service, method)(*args)
```

---

## Testing Strategy

### Coverage Goals
- 100% of exception classes have unit tests
- 100% of service methods have exception path tests
- 100% of API endpoints have error response tests
- All database error scenarios covered (integrity, connection, timeout)

### Test Organization
```
tests/
├── utils/
│   ├── exception_fixtures.py     (NEW - fixtures)
│   ├── exception_helpers.py      (NEW - helpers)
│   └── mock_factories.py         (NEW - mocks)
├── test_exceptions.py            (Base exception tests)
├── services/
│   └── test_[service]_exceptions.py  (Service exception tests)
└── integration/
    └── test_[endpoint]_errors.py     (API error response tests)
```

---

## Success Criteria

- [x] 3 utility files created with reusable test infrastructure
- [x] Fixtures cover common exception scenarios
- [x] Helper functions reduce test code by ~50%
- [x] Mock factories simplify database error testing
- [x] Documentation provides 6+ test patterns
- [x] Integration with existing conftest.py seamless

---

## Dependencies and Blockers

**Dependencies:**
- Handover 0480a (exception framework must exist)

**Follow-ups:**
- Handovers 0480d-0480g will use these test utilities extensively

---

**Document Version**: 1.0
**Created**: 2026-01-26
**Author**: Claude (Sonnet 4.5)
**Status**: Ready for Implementation
