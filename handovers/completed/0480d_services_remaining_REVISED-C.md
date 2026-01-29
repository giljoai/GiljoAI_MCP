# Handover 0480d: Service Migration - Remaining Services (REVISED)

**Date:** 2026-01-27
**From Agent:** Orchestrator
**To Agent:** TDD Implementor
**Priority:** HIGH
**Estimated Complexity:** 4-8 hours
**Status:** Ready for Implementation
**Series:** 0480 (Exception Handling Remediation - REVISED)
**Prerequisite:** 0480b and 0480c must be complete

---

## Executive Summary

### What
Migrate any remaining services from dict returns to raising exceptions.

### Current State
Services return error dicts:
```python
return {"success": False, "error": "Message not found"}
return {"success": False, "error": str(e)}
```

### Target State
Services raise exceptions:
```python
from src.giljo_mcp.exceptions import ResourceNotFoundError, ValidationError

raise ResourceNotFoundError(
    message="Message not found",
    context={"message_id": message_id}
)
```

---

## Tasks

### Task 1: Survey Remaining Services

**Location:** `src/giljo_mcp/services/`

Run this command to find services with dict returns:
```bash
grep -l "success.*False" src/giljo_mcp/services/*.py
```

Check specifically:
- `message_service.py`
- `context_service.py`
- `settings_service.py`
- `agent_job_manager.py`
- Any other services not covered by 0480b/0480c

### Task 2: Migrate message_service.py (if applicable)

**File:** `src/giljo_mcp/services/message_service.py`

**Mapping:**

| Error Message | Exception to Raise |
|--------------|-------------------|
| "Message not found" | `ResourceNotFoundError` |
| "Invalid message format" | `ValidationError` |
| "Delivery failed" | `MessageDeliveryError` |
| Generic `str(e)` | `BaseGiljoException` |

**Example transformation:**
```python
# BEFORE
if not message:
    return {"success": False, "error": "Message not found"}

# AFTER
if not message:
    raise ResourceNotFoundError(
        message="Message not found",
        context={"message_id": message_id}
    )
```

### Task 3: Migrate context_service.py (if applicable)

**File:** `src/giljo_mcp/services/context_service.py`

**Mapping:**

| Error Message | Exception to Raise |
|--------------|-------------------|
| "Context not found" | `ResourceNotFoundError` |
| "Context limit exceeded" | `ContextLimitError` |
| Generic `str(e)` | `BaseGiljoException` |

### Task 4: Migrate settings_service.py (if applicable)

**File:** `src/giljo_mcp/services/settings_service.py`

**Mapping:**

| Error Message | Exception to Raise |
|--------------|-------------------|
| "Settings not found" | `ResourceNotFoundError` |
| "Invalid setting value" | `ValidationError` |
| Generic `str(e)` | `BaseGiljoException` |

### Task 5: Apply Same Migration Pattern to Any Other Services

For each service with dict returns:
1. Find `return {"success": False, ...}` patterns
2. Map error messages to appropriate exceptions
3. Replace dict returns with exception raises
4. Update return types
5. Write tests

### Task 6: Final Verification

```bash
# This MUST return 0 matches after all migrations complete
grep -r "success.*False" src/giljo_mcp/services/ --include="*.py"
```

---

## Success Criteria

- [ ] Zero dict return patterns in ANY service file
- [ ] All services raise exceptions for errors
- [ ] Return types updated to model objects
- [ ] Tests verify exception raising
- [ ] Final grep verification returns 0 matches

---

## Verification Commands

```bash
# Count remaining dict returns per service
for f in src/giljo_mcp/services/*.py; do
    count=$(grep -c "success.*False" "$f" 2>/dev/null || echo 0)
    if [ "$count" -gt 0 ]; then
        echo "$f: $count"
    fi
done
# Should output nothing (all counts are 0)

# Final check - must return empty
grep -r "success.*False" src/giljo_mcp/services/ --include="*.py"
```

---

## Files Changed

| File | Action |
|------|--------|
| `src/giljo_mcp/services/message_service.py` | MODIFY - if dict returns exist |
| `src/giljo_mcp/services/context_service.py` | MODIFY - if dict returns exist |
| `src/giljo_mcp/services/settings_service.py` | MODIFY - if dict returns exist |
| `src/giljo_mcp/services/agent_job_manager.py` | MODIFY - if dict returns exist |
| `tests/services/test_*.py` | MODIFY - add exception tests |

---

## Reference

- Exceptions: `src/giljo_mcp/exceptions.py`
- Master handover: `handovers/0480_exception_handling_remediation_REVISED.md`
