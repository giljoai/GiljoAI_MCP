# Handover 0480b: Service Migration - Auth & Product (REVISED)

**Date:** 2026-01-27
**From Agent:** Orchestrator
**To Agent:** TDD Implementor
**Priority:** HIGH
**Estimated Complexity:** 8-10 hours
**Status:** Ready for Implementation
**Series:** 0480 (Exception Handling Remediation - REVISED)
**Prerequisite:** 0480a must be complete

---

## Executive Summary

### What
Migrate `auth_service.py` and `product_service.py` from dict returns to raising exceptions.

### Current State
Services return error dicts:
```python
return {"success": False, "error": "Product not found"}
return {"success": False, "error": str(e)}
```

### Target State
Services raise exceptions:
```python
from src.giljo_mcp.exceptions import ResourceNotFoundError

raise ResourceNotFoundError(
    message="Product not found",
    context={"product_id": product_id}
)
```

---

## Tasks

### Task 1: Migrate auth_service.py

**File:** `src/giljo_mcp/services/auth_service.py`

**Pattern to find:** `return {"success": False`

**Mapping:**

| Error Message | Exception to Raise |
|--------------|-------------------|
| "Invalid credentials" | `AuthenticationError` |
| "User not found" | `ResourceNotFoundError` |
| "User account is inactive" | `AuthorizationError` |
| "Username already exists" | `ValidationError` |
| "Email already exists" | `ValidationError` |
| Generic `str(e)` | `BaseGiljoException` |

**Example transformation:**
```python
# BEFORE
if not user:
    return {"success": False, "error": "User not found"}

# AFTER
if not user:
    raise ResourceNotFoundError(
        message="User not found",
        context={"username": username}
    )
```

### Task 2: Migrate product_service.py

**File:** `src/giljo_mcp/services/product_service.py`

**Mapping:**

| Error Message | Exception to Raise |
|--------------|-------------------|
| "Product not found" | `ResourceNotFoundError` |
| "Product already exists" | `ValidationError` |
| Generic `str(e)` | `BaseGiljoException` |

### Task 3: Update Return Types

Change method signatures:
```python
# BEFORE
async def get_product(...) -> dict:

# AFTER
async def get_product(...) -> Product:
```

### Task 4: Write Tests

For each migrated method:
```python
@pytest.mark.asyncio
async def test_get_product_raises_not_found():
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.get_product("nonexistent", "tenant")
    assert "not found" in exc_info.value.message
```

---

## Success Criteria

- [ ] Zero `{"success": False` patterns in auth_service.py
- [ ] Zero `{"success": False` patterns in product_service.py
- [ ] Return types updated to model objects
- [ ] Tests verify exception raising
- [ ] Existing endpoints still work (global handler catches exceptions)

---

## Verification Command

```bash
grep -c "success.*False" src/giljo_mcp/services/auth_service.py
# Should return 0

grep -c "success.*False" src/giljo_mcp/services/product_service.py
# Should return 0
```

---

## Reference

- Exceptions: `src/giljo_mcp/exceptions.py`
- Master handover: `handovers/0480_exception_handling_remediation_REVISED.md`
