# Handover 0480f: Low-Priority Services Migration (TaskService, ContextService, SettingsService)

**Date:** 2026-01-26
**From Agent:** Documentation Manager
**To Agent:** TDD Implementor
**Priority:** MEDIUM
**Estimated Complexity:** 4-6 hours
**Status:** Ready for Implementation
**Series:** 0480 (Exception Handling Architecture Remediation)
**Dependencies:** Handover 0480e (Core services complete)

---

## Executive Summary

### What
Migrate three low-priority service classes:
1. **TaskService** - Task management (5+ exceptions)
2. **ContextService** - Context field management (8+ exceptions)
3. **SettingsService** - System settings (5+ exceptions)

These services have low complexity and minimal dependencies.

### Why
- Complete service layer migration (100% coverage)
- Simple patterns (fewer edge cases than core services)
- Low risk (limited usage compared to core services)

### Impact
- **Files Changed**: 3 service files, 3 test files, ~5 new domain exceptions
- **Code Reduction**: ~80 lines
- **Risk**: Low (simple CRUD operations)

---

## Service 1: TaskService

**Complexity**: LOW
**Estimated Time**: 2 hours
**Dependencies**: None

### New Domain Exceptions

```python
class TaskNotFoundError(NotFoundError):
    def __init__(self, task_id: str, tenant_key: Optional[str] = None):
        super().__init__(
            message=f"Task {task_id} not found",
            metadata={"task_id": task_id, "tenant_key": tenant_key}
        )
```

### Methods to Migrate (3 methods)

- [ ] **get_task()** - Use `get_or_404()`
- [ ] **create_task()** - Use `safe_commit()`
- [ ] **update_task()** - Use `get_or_404()` + `safe_commit()`

### Tests (6 tests)
- Unit: `test_get_task_not_found`
- Unit: `test_create_task_success`
- Unit: `test_update_task_not_found`
- Integration: `test_task_api_404`
- Integration: `test_task_api_create_200`
- Integration: `test_task_api_update_404`

---

## Service 2: ContextService

**Complexity**: MEDIUM
**Estimated Time**: 3 hours
**Dependencies**: ProductService

### New Domain Exceptions

```python
class ContextFieldNotFoundError(NotFoundError):
    def __init__(self, field_name: str, tenant_key: Optional[str] = None):
        super().__init__(
            message=f"Context field '{field_name}' not found",
            metadata={"field_name": field_name, "tenant_key": tenant_key}
        )

class InvalidContextPriorityError(ValidationError):
    def __init__(self, priority: int, allowed_range: tuple):
        super().__init__(
            message=f"Priority {priority} outside allowed range {allowed_range}",
            metadata={"priority": priority, "min": allowed_range[0], "max": allowed_range[1]}
        )

class InvalidDepthConfigError(ValidationError):
    def __init__(self, category: str, depth: str, allowed_values: list):
        super().__init__(
            message=f"Invalid depth '{depth}' for category '{category}'. Allowed: {allowed_values}",
            metadata={"category": category, "depth": depth, "allowed": allowed_values}
        )
```

### Methods to Migrate (5 methods)

- [ ] **get_context_field()** - Validate field exists, priority in range
- [ ] **update_context_priority()** - Validate field exists, priority valid (1-4)
- [ ] **update_depth_config()** - Validate category, depth options
- [ ] **fetch_context()** - Validate product exists, depth config valid
- [ ] **list_context_fields()** - Use `list_by_tenant()`

### Tests (10 tests)
- Unit: `test_get_context_field_not_found`
- Unit: `test_update_priority_invalid_range`
- Unit: `test_update_depth_invalid_option`
- Unit: `test_fetch_context_product_not_found`
- Unit: `test_fetch_context_invalid_depth`
- Integration: `test_context_api_404_field_not_found`
- Integration: `test_context_api_400_invalid_priority`
- Integration: `test_context_api_400_invalid_depth`
- Integration: `test_fetch_context_424_product_not_found`
- Integration: `test_list_fields_tenant_isolated`

---

## Service 3: SettingsService

**Complexity**: LOW
**Estimated Time**: 1.5 hours
**Dependencies**: None

### New Domain Exceptions

```python
class SettingNotFoundError(NotFoundError):
    def __init__(self, setting_key: str, tenant_key: Optional[str] = None):
        super().__init__(
            message=f"Setting '{setting_key}' not found",
            metadata={"setting_key": setting_key, "tenant_key": tenant_key}
        )

class InvalidSettingValueError(ValidationError):
    def __init__(self, setting_key: str, value: Any, constraint: str):
        super().__init__(
            message=f"Invalid value for setting '{setting_key}': {constraint}",
            metadata={"setting_key": setting_key, "value": str(value), "constraint": constraint}
        )
```

### Methods to Migrate (3 methods)

- [ ] **get_setting()** - Use `get_or_404()`
- [ ] **update_setting()** - Validate value constraints
- [ ] **list_settings()** - Use `list_by_tenant()`

### Tests (6 tests)
- Unit: `test_get_setting_not_found`
- Unit: `test_update_setting_invalid_value`
- Unit: `test_list_settings_success`
- Integration: `test_settings_api_404`
- Integration: `test_settings_api_400_invalid_value`
- Integration: `test_settings_api_list_200`

---

## Migration Checklist (Per Service)

### Step 1: Inherit from BaseService (5 minutes)
```python
from src.giljo_mcp.services.base_service import BaseService

class TaskService(BaseService):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
```

### Step 2: Add Domain Exception Imports (5 minutes)
```python
from src.giljo_mcp.exceptions.domain import (
    TaskNotFoundError,
    # ... other exceptions
)
```

### Step 3: Remove HTTPException (2 minutes)
```python
# DELETE THIS LINE
from fastapi import HTTPException
```

### Step 4: Migrate Methods (30-60 minutes per service)
- Replace manual queries with base service helpers
- Replace `HTTPException` with domain exceptions
- Use `safe_commit()` instead of try-except blocks

### Step 5: Write Tests (30-60 minutes per service)
- Use test infrastructure from Handover 0480c
- 2 tests per method (happy path + exception)
- Verify HTTP status codes in integration tests

### Step 6: Run Tests (10 minutes per service)
```bash
pytest tests/services/test_task_service.py -v --cov
pytest tests/services/test_context_service.py -v --cov
pytest tests/services/test_settings_service.py -v --cov
```

---

## Code Examples

### TaskService - Before & After

**BEFORE:**
```python
async def get_task(self, task_id: str, tenant_key: str):
    stmt = select(Task).where(Task.id == task_id, Task.tenant_key == tenant_key)
    result = await self.session.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
```

**AFTER:**
```python
async def get_task(self, task_id: str, tenant_key: str):
    return await self.get_or_404(Task, task_id, tenant_key, TaskNotFoundError)
```

### ContextService - Validation Example

**BEFORE:**
```python
async def update_context_priority(self, field_name: str, priority: int, tenant_key: str):
    if priority < 1 or priority > 4:
        raise HTTPException(status_code=400, detail="Priority must be 1-4")
    # ... rest of method
```

**AFTER:**
```python
async def update_context_priority(self, field_name: str, priority: int, tenant_key: str):
    if priority < 1 or priority > 4:
        raise InvalidContextPriorityError(priority, (1, 4))
    # ... rest of method
```

---

## Testing Strategy

### Coverage Requirements
- **Unit Tests**: 100% of exception paths
- **Integration Tests**: All API endpoints
- **Line Coverage**: >85% (simpler code than core services)

### Test Execution Order
1. TaskService (simplest) - 30 minutes
2. SettingsService (simple) - 30 minutes
3. ContextService (medium complexity) - 60 minutes

Total testing time: ~2 hours

---

## Success Criteria

- [ ] All 3 services inherit from `BaseService`
- [ ] Zero `HTTPException` in service files
- [ ] 22 total tests written (6 + 10 + 6)
- [ ] Unit test coverage >85% for each service
- [ ] Integration tests pass (HTTP responses unchanged)
- [ ] Service layer migration 100% complete

---

## Rollback Plan

```bash
# Rollback individual services
git revert <commit_hash_task_service>
git revert <commit_hash_context_service>
git revert <commit_hash_settings_service>

# Or rollback all three
git revert <commit_hash_0480f_start>..<commit_hash_0480f_end>
```

---

**Document Version**: 1.0
**Created**: 2026-01-26
**Author**: Claude (Sonnet 4.5)
**Status**: Ready for Implementation
