# Handover 0482: Agent Jobs API Exception Handling

**Status**: Ready for Execution
**Priority**: High
**Depends On**: 0480 (Exception Handling Refactor)
**Branch**: `0480-exception-handling-remediation`

---

## Problem Statement

Handover 0480 changed services to raise domain-specific exceptions instead of returning error dicts. The Agent Jobs API endpoints were not updated to handle these exceptions correctly.

**Current Behavior**: Endpoints catch generic `Exception` and return HTTP 500 for all errors
**Expected Behavior**: Return appropriate status codes (404, 422, 403) based on exception type

---

## Evidence from Tests

```
tests/api/test_agent_jobs_api.py:
- assert 500 == 200 (acknowledge endpoint)
- assert 500 in [400, 404] (missing job)

tests/api/test_agent_jobs_mission.py:
- Multiple 500 errors where 404 expected
```

---

## Files to Modify

Search for agent jobs endpoints:
```bash
find api/endpoints -name "*agent*" -o -name "*job*"
```

Likely files:
- `api/endpoints/agent_jobs/lifecycle.py`
- `api/endpoints/agent_jobs/status.py`
- `api/endpoints/agent_jobs/operations.py`
- `api/endpoints/agent_jobs/progress.py`
- `api/endpoints/agent_jobs/orchestration.py`

---

## Fix Pattern

### Add Imports
```python
from src.giljo_mcp.exceptions import (
    ResourceNotFoundError,
    ValidationError,
    AuthorizationError,
)
```

### Replace Exception Handling

**BEFORE** (broken):
```python
try:
    result = await service.some_operation(...)
    return result
except HTTPException:
    raise
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

**AFTER** (fixed):
```python
try:
    result = await service.some_operation(...)
    return result
except ResourceNotFoundError as e:
    raise HTTPException(status_code=404, detail=str(e))
except ValidationError as e:
    raise HTTPException(status_code=422, detail=str(e))
except AuthorizationError as e:
    raise HTTPException(status_code=403, detail=str(e))
except HTTPException:
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

---

## Reference Implementation

See the already-fixed Products API endpoints:
- `api/endpoints/products/crud.py` (commit 96296f16)
- `api/endpoints/products/lifecycle.py`
- `api/endpoints/products/vision.py`

---

## Verification

After applying fixes, run:
```bash
python -m pytest tests/api/test_agent_jobs_api.py tests/api/test_agent_jobs_mission.py -v --no-cov --tb=short
```

**Target**: Significant reduction in 500 errors, proper 404/422/403 responses

---

## Commit Message Template

```
fix(api): Add proper exception handling to Agent Jobs API endpoints

- Import domain exceptions (ResourceNotFoundError, ValidationError, AuthorizationError)
- Return 404 for ResourceNotFoundError
- Return 422 for ValidationError
- Return 403 for AuthorizationError
- Keep 500 only for unexpected errors

Part of Handover 0480 remediation series.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## Safety Notes

1. **DO NOT** modify service layer - exceptions are correct there
2. **DO NOT** modify test files - they expect correct status codes
3. **DO NOT** touch the database
4. Only modify endpoint files in `api/endpoints/`
5. Commit frequently for recovery

---

## Success Criteria

- [ ] All agent jobs endpoint files have proper exception imports
- [ ] All try/except blocks follow the new pattern
- [ ] Tests show proper 404/422/403 instead of 500
- [ ] No regressions in previously passing tests
- [ ] Changes committed with descriptive message
