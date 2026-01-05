# Services Architecture

**Document Version:** 1.0
**Last Updated:** 2025-11-10
**Status:** Active
**Related:** Handover 0121 - ToolAccessor Phase 1

---

## Overview

This document describes the service layer architecture pattern introduced in **Handover 0121** as part of the ToolAccessor refactoring initiative. The service layer extracts domain-specific business logic from the monolithic ToolAccessor into focused, single-responsibility service classes.

### Goals

1. **Separation of Concerns**: Each service handles one business domain
2. **Testability**: Services can be unit tested independently
3. **Maintainability**: Smaller, focused classes are easier to understand and modify
4. **Reusability**: Services can be used directly by API endpoints or other components
5. **Backward Compatibility**: ToolAccessor delegates to services, maintaining existing API

---

## Service Layer Pattern

### Design Principles

All services in the `giljo_mcp.services` module follow these principles:

1. **Single Responsibility**: Each service focuses on one business domain
2. **Dependency Injection**: Services receive dependencies via constructor
3. **Async/Await**: Full SQLAlchemy 2.0 async support
4. **Consistent Error Handling**: All methods return `dict[str, Any]` with `success` flag
5. **Logging**: Comprehensive logging for debugging and monitoring
6. **Documentation**: Docstrings for all public methods with examples

### Service Template

```python
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from giljo_mcp.database import DatabaseManager
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class ExampleService:
    """
    Service for managing [domain] operations.

    This service handles:
    - Feature A
    - Feature B
    - Feature C

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
        """
        Initialize ExampleService.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def example_method(self, param: str) -> dict[str, Any]:
        """
        Brief description of what this method does.

        Args:
            param: Description of parameter

        Returns:
            Dict with success status and data or error

        Example:
            >>> result = await service.example_method("value")
            >>> if result["success"]:
            ...     print(result["data"])
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Implementation here
                pass

            return {"success": True, "data": "result"}

        except Exception as e:
            self._logger.exception(f"Failed to execute example_method: {e}")
            return {"success": False, "error": str(e)}
```

---

## ProjectService (Phase 1)

**File:** `src/giljo_mcp/services/project_service.py`
**Lines:** 719
**Implemented:** 2025-11-10
**Status:** ✅ Production Ready

### Responsibilities

ProjectService handles all project-related operations:

#### CRUD Operations
- `create_project()` - Create new projects with tenant isolation
- `get_project()` - Retrieve project by ID
- `list_projects()` - List projects with optional filtering
- `update_project_mission()` - Update project mission with WebSocket broadcast

#### Lifecycle Management
- `complete_project()` - Mark project as completed
- `cancel_project()` - Cancel project with reason
- `restore_project()` - Restore completed/cancelled project

#### Status & Metrics
- `get_project_status()` - Comprehensive project status with agents and messages
- `gil_activate()` - Activate project for orchestrator staging

### Integration with ToolAccessor

ToolAccessor delegates all project operations to ProjectService:

```python
class ToolAccessor:
    def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager

        # Initialize service layer
        self._project_service = ProjectService(db_manager, tenant_manager)

    async def create_project(self, name: str, mission: str, **kwargs) -> dict[str, Any]:
        """Create a new project (delegates to ProjectService)"""
        return await self._project_service.create_project(name, mission, **kwargs)

    # ... other delegating methods
```

### Benefits Achieved

1. **Reduced ToolAccessor**: From 2,677 → 2,324 lines (-353 lines, -13.2%)
2. **Standalone Service**: 719 lines of focused project logic
3. **Independent Testing**: Unit tests without ToolAccessor dependencies
4. **Reusability**: Can be used directly by API endpoints
5. **Pattern Established**: Template for extracting remaining services

### Test Coverage

**File:** `tests/unit/test_project_service.py`
**Coverage:** >80% target
**Test Classes:**
- `TestProjectServiceCRUD` - 9 tests for CRUD operations
- `TestProjectServiceLifecycle` - 4 tests for lifecycle management
- `TestProjectServiceStatus` - 4 tests for status and metrics
- `TestProjectServiceHelpers` - 2 tests for internal helpers
- `TestProjectServiceEdgeCases` - 2 tests for error handling

**Total:** 21+ comprehensive unit tests

---

## Future Services (Phase 2)

Based on the success of ProjectService, the following services are planned for extraction:

### AgentService
**Estimated Lines:** ~300
**Methods:** 8
**Responsibilities:**
- Agent job creation and management
- Agent lifecycle (spawn, decommission)
- Agent status tracking

### MessageService
**Estimated Lines:** ~250
**Methods:** 7
**Responsibilities:**
- Message creation and delivery
- Message acknowledgment
- Message queue management

### TaskService
**Estimated Lines:** ~200
**Methods:** 5
**Responsibilities:**
- Task CRUD operations
- Task assignment
- Task completion tracking

### ContextService
**Estimated Lines:** ~350
**Methods:** 8
**Responsibilities:**
- Context management
- Vision document handling
- Context budget tracking

### TemplateService
**Estimated Lines:** ~150
**Methods:** 4
**Responsibilities:**
- Template CRUD operations
- Template rendering
- Template caching

### OrchestrationService
**Estimated Lines:** ~400
**Methods:** 10+
**Responsibilities:**
- Workflow orchestration
- Agent coordination
- Project progression

### JobService
**Estimated Lines:** ~300
**Methods:** 8
**Responsibilities:**
- Job scheduling
- Job execution
- Job monitoring

---

## Migration Strategy

### For New Code

New features should use services directly:

```python
# ✅ Good - Direct service usage
from giljo_mcp.services.project_service import ProjectService

async def create_project_endpoint(db_manager, tenant_manager, data):
    service = ProjectService(db_manager, tenant_manager)
    return await service.create_project(**data)
```

### For Existing Code

Existing code can continue using ToolAccessor (delegates to services):

```python
# ✅ Also Good - Via ToolAccessor (backward compatible)
from giljo_mcp.tools.tool_accessor import ToolAccessor

async def legacy_endpoint(db_manager, tenant_manager, data):
    accessor = ToolAccessor(db_manager, tenant_manager)
    return await accessor.create_project(**data)
```

### Gradual Migration Path

1. **Phase 1** (Current): ProjectService extracted, ToolAccessor delegates
2. **Phase 2**: Extract remaining 7 services, ToolAccessor becomes thin facade
3. **Phase 3**: API endpoints migrate to direct service usage
4. **Phase 4**: Deprecate ToolAccessor, services are primary interface

---

## Best Practices

### 1. Service Initialization

```python
# ✅ Good - Service per request
async def handle_request(db_manager, tenant_manager):
    service = ProjectService(db_manager, tenant_manager)
    result = await service.create_project(...)
    return result

# ❌ Bad - Shared service instance
class MyHandler:
    def __init__(self):
        self.service = ProjectService(...)  # Don't do this!
```

### 2. Error Handling

```python
# ✅ Good - Check success flag
result = await service.create_project(...)
if result["success"]:
    project_id = result["project_id"]
else:
    logger.error(f"Failed: {result['error']}")

# ❌ Bad - Assume success
project_id = result["project_id"]  # May not exist if failed!
```

### 3. Async/Await

```python
# ✅ Good - Always await service methods
result = await service.get_project(project_id)

# ❌ Bad - Forgetting await
result = service.get_project(project_id)  # Returns coroutine, not result!
```

### 4. Dependency Injection

```python
# ✅ Good - Pass dependencies to constructor
service = ProjectService(db_manager, tenant_manager)

# ❌ Bad - Service creates its own dependencies
class ProjectService:
    def __init__(self):
        self.db_manager = DatabaseManager()  # Hard to test!
```

---

## Performance Considerations

### Delegation Overhead

The delegation pattern (ToolAccessor → Service) adds minimal overhead:

- **Extra Method Call:** ~1µs per call (negligible)
- **No Extra Database Queries:** Services use the same DB patterns
- **Memory:** Service instances are lightweight (~1KB each)

### Benchmarking

Performance should be monitored during migration:

```python
import time

async def benchmark_project_creation():
    start = time.time()
    result = await service.create_project(...)
    elapsed = time.time() - start
    print(f"Create project took {elapsed:.3f}s")
```

**Expected Performance:**
- CRUD operations: <100ms
- Complex queries: <500ms
- Batch operations: <2s

---

## Testing Strategy

### Unit Tests

Each service should have comprehensive unit tests:

```python
@pytest.mark.asyncio
async def test_create_project_success():
    """Test successful project creation"""
    # Arrange
    db_manager = Mock()
    tenant_manager = Mock()
    service = ProjectService(db_manager, tenant_manager)

    # Act
    result = await service.create_project(
        name="Test",
        mission="Mission"
    )

    # Assert
    assert result["success"] is True
    assert "project_id" in result
```

### Integration Tests

Test service integration with ToolAccessor:

```python
@pytest.mark.asyncio
async def test_tool_accessor_delegates_to_service():
    """Test ToolAccessor properly delegates to ProjectService"""
    # Arrange
    accessor = ToolAccessor(db_manager, tenant_manager)

    # Act
    result = await accessor.create_project(...)

    # Assert - Should have same behavior as direct service call
    assert result["success"] is True
```

### Regression Tests

Ensure no breaking changes:

```python
@pytest.mark.asyncio
async def test_backward_compatibility():
    """Test that existing API contracts are maintained"""
    # Existing tests should continue to pass
    result = await accessor.create_project(...)

    # All expected fields should be present
    assert "project_id" in result
    assert "tenant_key" in result
    assert "status" in result
```

---

## Monitoring & Observability

### Logging

All services use structured logging:

```python
self._logger.info(f"Created project {project_id}")
self._logger.error(f"Failed to create project: {error}")
self._logger.exception(f"Unexpected error: {e}")
```

### Metrics

Consider adding metrics for:

- Method call counts
- Error rates
- Response times
- Database query counts

### Debugging

Services log at appropriate levels:

- **DEBUG**: Detailed flow information
- **INFO**: Important operations (create, update, delete)
- **WARNING**: Recoverable issues
- **ERROR**: Operation failures
- **CRITICAL**: System-level failures

---

## Appendix

### Related Documents

- **Handover 0121**: ToolAccessor Phase 1 - Extract ProjectService
- **Handover 0123**: ToolAccessor Phase 2 - Extract Remaining Services (planned)
- **TECHNICAL_DEBT_v2.md**: Technical debt tracking
- **REFACTORING_ROADMAP_0120-0129.md**: Overall refactoring plan

### Code References

- **ProjectService**: `src/giljo_mcp/services/project_service.py:719`
- **ToolAccessor Integration**: `src/giljo_mcp/tools/tool_accessor.py:27-97`
- **Unit Tests**: `tests/unit/test_project_service.py`

### Changelog

#### 2025-11-10 - v1.0
- Initial document created
- Documented ProjectService extraction
- Established service layer pattern
- Defined migration strategy

---

**Document Owner:** Engineering Team
**Review Cycle:** Quarterly or after each service extraction
**Next Review:** After Handover 0123 (Phase 2 completion)
