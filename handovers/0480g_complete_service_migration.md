# Handover 0480g: Complete Service Migration (CRITICAL FIX)

**Date:** 2026-01-27
**From Agent:** Orchestrator
**To Agent:** TDD Implementor + Backend Tester
**Priority:** CRITICAL - Application broken
**Estimated Complexity:** 8-12 hours
**Status:** Ready for Implementation
**Series:** 0480 (Exception Handling Remediation - REVISED)

---

## CRITICAL: Application Broken

The partial 0480 migration broke the service-endpoint contract. Projects and tasks are not displaying in the UI because:

1. Services partially migrated - some return data directly, some still return `{"success": True, ...}`
2. Endpoints still check `result.get("success")` which fails when key missing
3. Result: Empty data returned to frontend

**This handover MUST be completed before any other work.**

---

## Scope

Complete the service migration that 0480c/0480d failed to finish:

| Service | Dict Returns | Status | Priority |
|---------|-------------|--------|----------|
| orchestration_service.py | 61 | ❌ 18% done | **P1 - CRITICAL** |
| project_service.py | 16 | ⚠️ 68% done | **P1 - CRITICAL** |
| message_service.py | 8 | ⚠️ 58% done | P2 |
| template_service.py | 4 | ⚠️ 64% done | P2 |
| context_service.py | 4 | ❌ 0% (stub) | P3 - Skip for now |

---

## Task 1: Fix project_service.py (CRITICAL)

**File:** `src/giljo_mcp/services/project_service.py`

**Find all remaining dict returns:**
```bash
grep -n "success.*True\|success.*False" src/giljo_mcp/services/project_service.py
```

**Pattern to fix - Success returns:**
```python
# BEFORE (broken contract)
return {"success": True, "project": project_data}

# AFTER (consistent pattern)
# Option A: Return data directly (update endpoint to match)
return project_data

# Option B: Keep dict but ensure ALL methods use it (check endpoint expects it)
return {"success": True, "project": project_data}
```

**IMPORTANT:** Check what the endpoint expects BEFORE changing the service. The contract must match.

**Pattern to fix - Error returns:**
```python
# BEFORE
return {"success": False, "error": "Project not found"}

# AFTER
raise ResourceNotFoundError(
    message="Project not found",
    context={"project_id": project_id}
)
```

---

## Task 2: Fix orchestration_service.py (CRITICAL)

**File:** `src/giljo_mcp/services/orchestration_service.py`

This service has 61 dict returns - the most of any service.

**Find all dict returns:**
```bash
grep -n "success.*True\|success.*False\|\"error\":" src/giljo_mcp/services/orchestration_service.py
```

**Common patterns to fix:**

```python
# Pattern 1: Error dict
# BEFORE
return {"error": "NOT_FOUND", "message": "Job not found"}

# AFTER
raise ResourceNotFoundError(message="Job not found", context={"job_id": job_id})
```

```python
# Pattern 2: Status error dict
# BEFORE
return {"status": "error", "error": "Failed to spawn", "jobs": [], "count": 0}

# AFTER
raise OrchestrationError(message="Failed to spawn", context={...})
```

```python
# Pattern 3: Success dict
# BEFORE
return {"status": "success", "jobs": formatted_jobs, "count": len(formatted_jobs)}

# AFTER - Check endpoint first!
return {"jobs": formatted_jobs, "count": len(formatted_jobs)}
# OR if endpoint needs status key:
return {"status": "success", "jobs": formatted_jobs, "count": len(formatted_jobs)}
```

---

## Task 3: Update Endpoints to Match

**Files to check:**
- `api/endpoints/projects/lifecycle.py`
- `api/endpoints/agent_jobs/lifecycle.py`
- `api/endpoints/agent_jobs/progress.py`
- `api/endpoints/agent_jobs/succession.py`

**Pattern to fix:**
```python
# BEFORE (checking dict)
result = await service.get_project(...)
if not result.get("success"):
    raise HTTPException(status_code=404, detail=result.get("error"))
return result["data"]

# AFTER (service raises exception on error)
return await service.get_project(...)
# Exception bubbles to global handler automatically
```

---

## Task 4: Fix message_service.py and template_service.py

Lower priority but should be done for consistency.

Same patterns as above.

---

## Verification

After each service fix, verify:

```bash
# 1. No dict error returns
grep -c "success.*False" src/giljo_mcp/services/{service_name}.py
# Should return 0

# 2. Run tests
pytest tests/services/test_{service_name}.py -v

# 3. Manual UI test
# - List projects
# - List tasks
# - Create/edit operations
```

---

## Success Criteria

- [ ] Projects display in UI
- [ ] Tasks display in UI
- [ ] Zero `{"success": False}` returns in migrated services
- [ ] Endpoints updated to not check dict pattern
- [ ] All existing tests pass
- [ ] Manual UI verification complete

---

## Reference

- Audit results: See conversation history
- Exception classes: `src/giljo_mcp/exceptions.py`
- Global handler: `api/exception_handlers.py`
