# Handover 0464: Empty State API Resilience

## Problem Statement

On a fresh installation with no products, projects, or data, certain API endpoints return 500 errors instead of gracefully handling empty states. This creates a poor user experience and unnecessary error noise in logs.

**Observed Error:**
```
GET /api/v1/messages/ HTTP/1.1" 500 Internal Server Error
HTTP exception: 500 - 400: Project not found
```

**Root Cause:** The system treats "no data exists" as an error condition rather than a valid empty state.

---

## Audit Findings

### Category 1: Endpoints That FAIL on Empty State

| Endpoint | Service Method | Current Behavior | Impact |
|----------|---------------|------------------|--------|
| `GET /api/v1/messages/` | `MessageService.list_messages()` | Returns error when no project exists | 500 error on fresh install |
| `POST /api/v1/messages/broadcast` | `MessageService.broadcast()` | Returns error when no project found | 400 error |

**Additional Bug Found:**
- `api/endpoints/messages.py` lines 219-220: Exception handler catches `HTTPException` and re-wraps it as 500
  ```python
  # BUG: This catches HTTPException(400) and re-raises as HTTPException(500)
  except Exception as e:
      raise HTTPException(status_code=500, detail=str(e))
  ```

### Category 2: Endpoints That CORRECTLY Handle Empty State

| Endpoint | Service Method | Correct Behavior |
|----------|---------------|------------------|
| `GET /api/v1/tasks/` | `TaskService.list_tasks()` | Returns `{"success": True, "tasks": [], "count": 0}` |
| `GET /api/agent-jobs/` | `OrchestrationService.list_jobs()` | Returns `{"jobs": [], "total": 0}` |
| `GET /api/v1/stats/projects` | Direct query | Returns `[]` |

---

## Design Principle

**Empty is not an error.** Collection queries should return empty results, not failures.

### Decision Matrix

| Scenario | Correct Response | Status Code |
|----------|-----------------|-------------|
| List resources, none exist | `[]` or `{"items": [], "count": 0}` | 200 |
| List resources with filter, none match | `[]` | 200 |
| Get specific resource by ID, not found | Error | 404 |
| Create resource, missing required dependency | Error | 400/422 |
| Query requires context (project), none active | `[]` (graceful) | 200 |

---

## Proposed Fix

### Fix 1: MessageService.list_messages() - Return Empty on No Project

**File:** `src/giljo_mcp/services/message_service.py`
**Lines:** 972-985

**Current (incorrect):**
```python
if not project:
    return {
        "success": False,
        "error": "Project not found"
    }
```

**Proposed (correct):**
```python
if not project:
    # No project = no messages - return empty list, not error
    return {
        "success": True,
        "messages": [],
        "count": 0
    }
```

**Rationale:** If there's no project, there can be no messages. This is a valid empty state, not an error condition.

---

### Fix 2: Messages Endpoint Exception Handler

**File:** `api/endpoints/messages.py`
**Lines:** 219-220

**Current (buggy):**
```python
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

**Proposed (correct):**
```python
except HTTPException:
    # Re-raise HTTP exceptions with their original status codes
    raise
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

**Rationale:** HTTPException should preserve its original status code. Only unexpected exceptions should become 500s.

---

### Fix 3: MessageService.broadcast() - Graceful Handling

**File:** `src/giljo_mcp/services/message_service.py`
**Lines:** 156-160

**Current:**
```python
if not project:
    return {
        "success": False,
        "error": "Project not found or access denied"
    }
```

**Proposed:**
```python
if not project:
    # No project = no agents to broadcast to - return success with empty recipients
    return {
        "success": True,
        "message_id": None,
        "to_agents": [],
        "recipients_count": 0,
        "note": "No active project - broadcast skipped"
    }
```

**Rationale:** Broadcast to zero agents is a no-op, not a failure.

---

## Implementation Checklist

- [ ] **Fix 1:** Update `MessageService.list_messages()` to return empty list when no project
- [ ] **Fix 2:** Add `except HTTPException: raise` to `list_messages` endpoint
- [ ] **Fix 3:** Update `MessageService.broadcast()` to return empty recipients gracefully
- [ ] **Test:** Verify fresh install shows no errors in logs
- [ ] **Test:** Verify dashboard loads without 500 errors when empty

---

## Testing Strategy

### Unit Tests

```python
# test_message_service.py

async def test_list_messages_no_project_returns_empty():
    """Listing messages with no project should return empty list, not error."""
    result = await message_service.list_messages(tenant_key="new_tenant")
    assert result["success"] is True
    assert result["messages"] == []
    assert result["count"] == 0

async def test_broadcast_no_project_returns_graceful():
    """Broadcasting with no project should succeed with zero recipients."""
    result = await message_service.broadcast(
        content="test",
        project_id=None,
        tenant_key="new_tenant"
    )
    assert result["success"] is True
    assert result["to_agents"] == []
```

### Integration Tests

```python
# test_empty_state_api.py

async def test_fresh_install_endpoints_return_200():
    """All list endpoints should return 200 with empty data on fresh install."""
    endpoints = [
        "/api/v1/messages/",
        "/api/v1/tasks/",
        "/api/agent-jobs/",
        "/api/v1/stats/projects",
    ]
    for endpoint in endpoints:
        response = await client.get(endpoint, headers=auth_headers)
        assert response.status_code == 200, f"{endpoint} failed with {response.status_code}"
```

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `src/giljo_mcp/services/message_service.py` | Modify | Return empty list on no project (2 locations) |
| `api/endpoints/messages.py` | Modify | Add HTTPException re-raise in exception handler |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Breaking existing API consumers | Low | Medium | Returning empty is more compatible than errors |
| Masking real errors | Low | Medium | Only "not found" becomes empty; exceptions still 500 |

---

## Success Criteria

1. Fresh install with no data: Dashboard loads without 500 errors
2. `GET /api/v1/messages/` returns `[]` with status 200 when no projects
3. Server logs show no ERROR or WARNING for empty state queries
4. All existing tests pass

---

## Estimated Effort

- **Lines Changed:** ~20
- **Files Changed:** 2
- **Test Coverage:** 4 new tests
- **Complexity:** Low - Pattern already established in TaskService

---

## References

- **Correct Pattern Example:** `TaskService.list_tasks()` lines 318-319
- **REST Best Practices:** Empty collections return 200 with `[]`, not 404 or 500
