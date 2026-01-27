# Handover 0480d: High-Value Service Migration (MessageService, ProjectService, ProductService)

**Date:** 2026-01-26
**From Agent:** Documentation Manager
**To Agent:** Database Expert + TDD Implementor (Multi-Terminal)
**Priority:** CRITICAL
**Estimated Complexity:** 12-16 hours (parallel execution: 5-6 hours)
**Status:** Ready for Implementation
**Series:** 0480 (Exception Handling Architecture Remediation)
**Dependencies:** Handovers 0480a (framework), 0480b (pattern), 0480c (test infrastructure)

---

## Executive Summary

### What
Migrate three high-value service classes to use the exception framework:
1. **MessageService** - Agent communication (20+ HTTPException raises)
2. **ProjectService** - Project lifecycle (30+ HTTPException raises)
3. **ProductService** - Product management (25+ HTTPException raises)

These three services account for **~40% of total HTTPException usage** across the codebase.

### Why
**High Impact:**
- Most frequently called services (thousands of requests per project)
- Current error handling causes frontend confusion ("500 Server Error" for user mistakes)
- Complex business logic needs rich exception context
- Foundation for remaining services (patterns proven here)

**Parallel Execution:**
- Three separate services can be migrated simultaneously
- Each agent works in separate terminal
- Coordination only needed for shared domain exceptions

### Impact
- **Files Changed**: 3 service files, 3 test files, ~10 new domain exceptions
- **Code Reduction**: ~200 lines removed (error handling duplication)
- **Breaking Changes**: None (HTTP responses identical)
- **Multi-Terminal**: 3 agents in parallel = 3x faster completion

---

## Parallel Execution Strategy

### Terminal 1: MessageService Migration

**Agent**: TDD Implementor #1
**Focus**: Agent communication exceptions
**Estimated Time**: 5 hours

**Domain Exceptions to Create:**
- `MessageNotFoundError` (404)
- `InvalidMessageStatusError` (400)
- `MessageAlreadyAcknowledgedError` (409)
- `AgentNotFoundError` (404)

**Methods to Migrate** (7 methods):
- `send_message()` - Validate sender/recipients exist
- `receive_messages()` - Handle agent not found
- `acknowledge_message()` - Handle already acknowledged
- `list_messages()` - Tenant filtering
- `get_message()` - Single message fetch
- `update_message_status()` - Status validation
- `delete_message()` - Soft delete

**Test Coverage:**
- 14 unit tests (2 per method: happy path + exception path)
- 7 integration tests (API endpoint responses)

---

### Terminal 2: ProjectService Migration

**Agent**: TDD Implementor #2
**Focus**: Project lifecycle exceptions
**Estimated Time**: 6 hours

**Domain Exceptions to Create:**
- `ProjectNotFoundError` (404) - Already exists in 0480a
- `ProjectAlreadyExistsError` (409) - Already exists in 0480a
- `InvalidProjectStatusError` (400) - Already exists in 0480a
- `ProjectHasActiveJobsError` (409) - NEW
- `WorkspacePathInvalidError` (400) - NEW
- `VisionDocumentTooLargeError` (413) - NEW

**Methods to Migrate** (10 methods):
- `get_project()` - Not found handling
- `create_project()` - Duplicate alias, workspace validation
- `update_project()` - Not found, status transitions
- `delete_project()` - Active jobs check
- `activate_project()` - Status validation
- `deactivate_project()` - Status validation
- `list_projects()` - Tenant filtering
- `upload_vision_document()` - Size validation
- `get_project_summary()` - Not found
- `launch_orchestrator()` - Multiple validations

**Test Coverage:**
- 20 unit tests (2 per method)
- 10 integration tests (API endpoints)

---

### Terminal 3: ProductService Migration

**Agent**: TDD Implementor #3
**Focus**: Product management exceptions
**Estimated Time**: 5 hours

**Domain Exceptions to Create:**
- `ProductNotFoundError` (404) - Already exists in 0480a
- `ProductAlreadyExistsError` (409) - NEW
- `ProductHasActiveProjectsError` (409) - NEW
- `InvalidProductConfigError` (400) - NEW
- `VisionChunkTooLargeError` (413) - NEW

**Methods to Migrate** (8 methods):
- `get_product()` - Not found handling
- `create_product()` - Duplicate name check
- `update_product()` - Not found, validation
- `delete_product()` - Active projects check
- `activate_product()` - Status validation
- `list_products()` - Tenant filtering
- `upload_vision_document()` - Chunking validation
- `get_product_context()` - Not found, invalid config

**Test Coverage:**
- 16 unit tests (2 per method)
- 8 integration tests (API endpoints)

---

## Implementation Steps (Per Service)

### Step 1: Create Domain Exceptions (30 minutes)

Add exceptions to `src/giljo_mcp/exceptions/domain.py`:

```python
# MESSAGE SERVICE EXCEPTIONS
class MessageNotFoundError(NotFoundError):
    def __init__(self, message_id: str, tenant_key: Optional[str] = None):
        super().__init__(
            message=f"Message {message_id} not found",
            metadata={"message_id": message_id, "tenant_key": tenant_key}
        )

class InvalidMessageStatusError(ValidationError):
    def __init__(self, message_id: str, current_status: str, attempted_status: str):
        super().__init__(
            message=f"Cannot transition message from '{current_status}' to '{attempted_status}'",
            metadata={"message_id": message_id, "current": current_status, "attempted": attempted_status}
        )

# PROJECT SERVICE EXCEPTIONS
class ProjectHasActiveJobsError(ConflictError):
    def __init__(self, project_id: str, active_job_count: int):
        super().__init__(
            message=f"Cannot delete project with {active_job_count} active job(s)",
            metadata={"project_id": project_id, "active_jobs": active_job_count}
        )

class WorkspacePathInvalidError(ValidationError):
    def __init__(self, path: str, reason: str):
        super().__init__(
            message=f"Workspace path '{path}' is invalid: {reason}",
            metadata={"path": path, "reason": reason}
        )

# PRODUCT SERVICE EXCEPTIONS
class ProductHasActiveProjectsError(ConflictError):
    def __init__(self, product_id: str, active_project_count: int):
        super().__init__(
            message=f"Cannot delete product with {active_project_count} active project(s)",
            metadata={"product_id": product_id, "active_projects": active_project_count}
        )
```

### Step 2: Update Service Class (2-3 hours per service)

**Make service inherit from BaseService:**
```python
from src.giljo_mcp.services.base_service import BaseService
from src.giljo_mcp.exceptions.domain import (
    ProjectNotFoundError,
    ProjectAlreadyExistsError,
    # ... other exceptions
)

class ProjectService(BaseService):
    """Project lifecycle management service."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)  # Call base class __init__
```

**Migrate each method** using patterns from Handover 0480b:

```python
# BEFORE
async def get_project(self, project_id: str, tenant_key: str):
    stmt = select(Project).where(...)
    result = await self.session.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

# AFTER
async def get_project(self, project_id: str, tenant_key: str):
    return await self.get_or_404(
        Project,
        project_id,
        tenant_key,
        ProjectNotFoundError
    )
```

### Step 3: Write Tests (2-3 hours per service)

Use test infrastructure from Handover 0480c:

```python
from tests.utils.exception_helpers import assert_raises_with_metadata

@pytest.mark.asyncio
async def test_get_project_not_found(db_session):
    """get_project raises ProjectNotFoundError when not found."""
    service = ProjectService(db_session)

    await assert_raises_with_metadata(
        ProjectNotFoundError,
        {"project_id": "nonexistent", "tenant_key": "tenant_abc"},
        service.get_project,
        "nonexistent",
        "tenant_abc"
    )
```

### Step 4: Run Tests & Verify (30 minutes per service)

```bash
# Unit tests
pytest tests/services/test_project_service.py -v

# Integration tests
pytest tests/integration/test_projects_api.py -v

# Coverage check
pytest tests/services/test_project_service.py --cov=src.giljo_mcp.services.project_service
```

---

## Coordination Requirements

### Shared Domain Exceptions

Some exceptions used by multiple services:

| Exception | Terminal 1 | Terminal 2 | Terminal 3 |
|-----------|------------|------------|------------|
| `AgentNotFoundError` | Creates | Uses | - |
| `ProductNotFoundError` | - | Uses | Creates |
| `ProjectNotFoundError` | Uses | Creates | Uses |

**Coordination Protocol:**
1. Terminal 2 creates `ProjectNotFoundError` first (15 minutes)
2. Terminal 3 creates `ProductNotFoundError` first (15 minutes)
3. Terminal 1 creates `AgentNotFoundError` first (15 minutes)
4. All terminals wait for shared exceptions before continuing
5. Git commit shared exceptions: `git add src/giljo_mcp/exceptions/domain.py && git commit -m "Add shared domain exceptions for 0480d"`

### Git Workflow

Each terminal works on separate branch:

```bash
# Terminal 1
git checkout -b handover-0480d-message-service

# Terminal 2
git checkout -b handover-0480d-project-service

# Terminal 3
git checkout -b handover-0480d-product-service
```

Merge order:
1. Merge shared exceptions first (from Terminal 2's branch)
2. Merge MessageService (Terminal 1)
3. Merge ProjectService (Terminal 2)
4. Merge ProductService (Terminal 3)

---

## Detailed Method Migration Checklists

### MessageService (Terminal 1)

- [ ] **send_message()**
  - [ ] Validate sender exists (raise `AgentNotFoundError`)
  - [ ] Validate recipients exist (raise `AgentNotFoundError`)
  - [ ] Handle integrity errors (raise `ConflictError`)
  - [ ] Test: Happy path
  - [ ] Test: Sender not found
  - [ ] Test: Recipient not found

- [ ] **receive_messages()**
  - [ ] Validate agent exists (raise `AgentNotFoundError`)
  - [ ] Filter by tenant (use `list_by_tenant()`)
  - [ ] Test: Happy path
  - [ ] Test: Agent not found

- [ ] **acknowledge_message()**
  - [ ] Fetch message (use `get_or_404()`)
  - [ ] Check already acknowledged (raise `MessageAlreadyAcknowledgedError`)
  - [ ] Test: Happy path
  - [ ] Test: Already acknowledged

- [ ] **list_messages()** - Simple tenant filtering
- [ ] **get_message()** - Use `get_or_404()`
- [ ] **update_message_status()** - Validate transitions
- [ ] **delete_message()** - Soft delete

### ProjectService (Terminal 2)

- [ ] **get_project()** - Use `get_or_404()`
- [ ] **create_project()**
  - [ ] Check duplicate alias (use `exists()`)
  - [ ] Validate workspace path (raise `WorkspacePathInvalidError`)
  - [ ] Handle integrity errors
  - [ ] Test: Happy path
  - [ ] Test: Duplicate alias
  - [ ] Test: Invalid workspace

- [ ] **update_project()**
  - [ ] Fetch project (use `get_or_404()`)
  - [ ] Validate status transitions (raise `InvalidProjectStatusError`)
  - [ ] Use `safe_commit()`

- [ ] **delete_project()**
  - [ ] Check active jobs (raise `ProjectHasActiveJobsError`)
  - [ ] Use `safe_delete()`

- [ ] **activate_project()** - Status validation
- [ ] **deactivate_project()** - Status validation
- [ ] **list_projects()** - Use `list_by_tenant()`
- [ ] **upload_vision_document()** - Size validation
- [ ] **get_project_summary()** - Use `get_or_404()`
- [ ] **launch_orchestrator()** - Multi-step validation

### ProductService (Terminal 3)

- [ ] **get_product()** - Use `get_or_404()`
- [ ] **create_product()**
  - [ ] Check duplicate name (use `exists()`)
  - [ ] Handle integrity errors
  - [ ] Test: Happy path
  - [ ] Test: Duplicate name

- [ ] **update_product()**
  - [ ] Fetch product (use `get_or_404()`)
  - [ ] Validate config (raise `InvalidProductConfigError`)

- [ ] **delete_product()**
  - [ ] Check active projects (raise `ProductHasActiveProjectsError`)
  - [ ] Use `safe_delete()`

- [ ] **activate_product()** - Status validation
- [ ] **list_products()** - Use `list_by_tenant()`
- [ ] **upload_vision_document()** - Chunk size validation
- [ ] **get_product_context()** - Config validation

---

## Testing Requirements

### Coverage Targets
- **Unit Tests**: 100% of exception paths
- **Integration Tests**: All API endpoints return correct status codes
- **Line Coverage**: >90% for each service file

### Test Commands

```bash
# Terminal 1 - MessageService
pytest tests/services/test_message_service.py -v --cov=src.giljo_mcp.services.message_service
pytest tests/integration/test_messages_api.py -v

# Terminal 2 - ProjectService
pytest tests/services/test_project_service.py -v --cov=src.giljo_mcp.services.project_service
pytest tests/integration/test_projects_api.py -v

# Terminal 3 - ProductService
pytest tests/services/test_product_service.py -v --cov=src.giljo_mcp.services.product_service
pytest tests/integration/test_products_api.py -v

# All three (final verification)
pytest tests/services/test_message_service.py tests/services/test_project_service.py tests/services/test_product_service.py -v
```

---

## Success Criteria

- [ ] All 3 services inherit from `BaseService`
- [ ] Zero `from fastapi import HTTPException` in service files
- [ ] All domain exceptions defined and tested
- [ ] Unit test coverage >90% for each service
- [ ] Integration tests pass (HTTP responses unchanged)
- [ ] Code reduction: ~200 lines removed across 3 services
- [ ] Parallel execution completed in 5-6 hours (vs 16 hours sequential)

---

## Rollback Plan

Each service can be rolled back independently:

```bash
# Rollback MessageService
git revert <commit_hash_message_service>

# Rollback ProjectService
git revert <commit_hash_project_service>

# Rollback ProductService
git revert <commit_hash_product_service>

# Rollback shared exceptions
git revert <commit_hash_shared_exceptions>
```

Tests must pass after each rollback.

---

**Document Version**: 1.0
**Created**: 2026-01-26
**Author**: Claude (Sonnet 4.5)
**Status**: Ready for Implementation
**Execution Mode**: Multi-Terminal (3 agents in parallel)
