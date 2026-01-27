# Handover 0480e: Endpoint Cleanup (REVISED)

**Date:** 2026-01-27
**From Agent:** Orchestrator
**To Agent:** Backend Tester
**Priority:** HIGH
**Estimated Complexity:** 8-12 hours
**Status:** Ready for Implementation
**Series:** 0480 (Exception Handling Remediation - REVISED)
**Prerequisite:** 0480b, 0480c, 0480d must be complete

---

## Executive Summary

### What
Remove redundant try/except blocks from all endpoints. Let exceptions bubble to global handler.

### Current State
Endpoints catch service results and re-raise HTTPException:
```python
@router.get("/{product_id}")
async def get_product(product_id: str, ...):
    try:
        result = await service.get_product(product_id, tenant_key)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result["data"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Target State
Clean endpoints that let exceptions bubble up:
```python
@router.get("/{product_id}")
async def get_product(product_id: str, ...):
    return await service.get_product(product_id, tenant_key)
```

---

## Tasks

### Task 1: Survey All Endpoint Files

**Location:** `api/endpoints/`

```bash
grep -r "except.*HTTPException" api/endpoints/ --include="*.py" -l
```

### Task 2: Remove Redundant Exception Handling

For each endpoint:
1. Remove try/except blocks that translate exceptions
2. Remove `if not result.get("success")` checks
3. Return service result directly
4. Keep only necessary input validation

### Task 3: Keep Legitimate Try/Except

Some try/except is valid - DO NOT remove:
- External API calls with custom handling
- Background tasks with retry logic
- WebSocket connection handling

### Task 4: Update Imports

Remove unused `HTTPException` imports where possible.

### Task 5: Test Each Endpoint

Verify exceptions translate to correct HTTP status codes.

---

## Success Criteria

- [ ] Redundant try/except blocks removed
- [ ] Endpoints return service results directly
- [ ] All endpoints tested
- [ ] No regressions

---

## Reference

- Master handover: `handovers/0480_exception_handling_remediation_REVISED.md`
