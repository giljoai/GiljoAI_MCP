# Handover 0480c: Service Migration - Core Services (REVISED)

**Date:** 2026-01-27
**From Agent:** Orchestrator
**To Agent:** TDD Implementor
**Priority:** HIGH
**Estimated Complexity:** 8-10 hours
**Status:** Ready for Implementation
**Series:** 0480 (Exception Handling Remediation - REVISED)
**Prerequisite:** 0480a must be complete (can run parallel with 0480b)

---

## Executive Summary

### What
Migrate `project_service.py`, `orchestration_service.py`, and `template_service.py` from dict returns to raising exceptions.

### Current State
Services return error dicts:
```python
return {"success": False, "error": "Project not found"}
return {"success": False, "error": str(e)}
```

### Target State
Services raise exceptions:
```python
from src.giljo_mcp.exceptions import ResourceNotFoundError, ProjectStateError

raise ResourceNotFoundError(
    message="Project not found",
    context={"project_id": project_id}
)
```

---

## Tasks

### Task 1: Migrate project_service.py

**File:** `src/giljo_mcp/services/project_service.py`

**Pattern to find:** `return {"success": False`

**Mapping:**

| Error Message | Exception to Raise |
|--------------|-------------------|
| "Project not found" | `ResourceNotFoundError` |
| "Project already exists" | `ValidationError` |
| "Invalid status transition" | `ProjectStateError` |
| "Product not found" | `ResourceNotFoundError` |
| Generic `str(e)` | `BaseGiljoException` |

**Example transformation:**
```python
# BEFORE
if not project:
    return {"success": False, "error": "Project not found"}

# AFTER
if not project:
    raise ResourceNotFoundError(
        message="Project not found",
        context={"project_id": project_id, "tenant_key": tenant_key}
    )
```

### Task 2: Migrate orchestration_service.py

**File:** `src/giljo_mcp/services/orchestration_service.py`

**Mapping:**

| Error Message | Exception to Raise |
|--------------|-------------------|
| "Agent creation failed" | `AgentCreationError` |
| "Handoff failed" | `HandoffError` |
| "Invalid project state" | `ProjectStateError` |
| "Orchestration error" | `OrchestrationError` |
| Generic `str(e)` | `BaseGiljoException` |

**Example transformation:**
```python
# BEFORE
if not agent_job:
    return {"success": False, "error": "Agent creation failed"}

# AFTER
if not agent_job:
    raise AgentCreationError(
        message="Agent creation failed",
        context={"agent_name": agent_name, "project_id": project_id}
    )
```

### Task 3: Migrate template_service.py

**File:** `src/giljo_mcp/services/template_service.py`

**Mapping:**

| Error Message | Exception to Raise |
|--------------|-------------------|
| "Template not found" | `TemplateNotFoundError` |
| "Template validation failed" | `TemplateValidationError` |
| "Template render error" | `TemplateRenderError` |
| Generic `str(e)` | `BaseGiljoException` |

**Example transformation:**
```python
# BEFORE
if not template:
    return {"success": False, "error": f"Template '{name}' not found"}

# AFTER
if not template:
    raise TemplateNotFoundError(
        message=f"Template '{name}' not found",
        context={"template_name": name, "tenant_key": tenant_key}
    )
```

### Task 4: Update Return Types

Change method signatures:
```python
# BEFORE
async def get_project(...) -> dict:

# AFTER
async def get_project(...) -> Project:
```

### Task 5: Write Tests

For each migrated method:
```python
@pytest.mark.asyncio
async def test_get_project_raises_not_found():
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.get_project("nonexistent", "tenant")
    assert "not found" in exc_info.value.message
    assert exc_info.value.context["project_id"] == "nonexistent"
```

---

## Success Criteria

- [ ] Zero `{"success": False` patterns in project_service.py
- [ ] Zero `{"success": False` patterns in orchestration_service.py
- [ ] Zero `{"success": False` patterns in template_service.py
- [ ] Return types updated to model objects
- [ ] Tests verify exception raising
- [ ] Existing endpoints still work (global handler catches exceptions)

---

## Verification Commands

```bash
grep -c "success.*False" src/giljo_mcp/services/project_service.py
# Should return 0

grep -c "success.*False" src/giljo_mcp/services/orchestration_service.py
# Should return 0

grep -c "success.*False" src/giljo_mcp/services/template_service.py
# Should return 0
```

---

## Files Changed

| File | Action |
|------|--------|
| `src/giljo_mcp/services/project_service.py` | MODIFY - replace dict returns |
| `src/giljo_mcp/services/orchestration_service.py` | MODIFY - replace dict returns |
| `src/giljo_mcp/services/template_service.py` | MODIFY - replace dict returns |
| `tests/services/test_project_service.py` | MODIFY - add exception tests |
| `tests/services/test_orchestration_service.py` | MODIFY - add exception tests |
| `tests/services/test_template_service.py` | MODIFY - add exception tests |

---

## Reference

- Exceptions: `src/giljo_mcp/exceptions.py`
- Master handover: `handovers/0480_exception_handling_remediation_REVISED.md`
