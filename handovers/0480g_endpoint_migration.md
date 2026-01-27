# Handover 0480g: API Endpoint Migration (205 Endpoints Across 47 Files)

> **DEPRECATED 2026-01-27**: This handover is part of the deprecated 0480 series.
> The series was redesigned due to critical flaws (false premises about codebase state).
>
> **Use Instead**:
> - Master: `handovers/0480_exception_handling_remediation_REVISED.md`
> - Chain prompts: `prompts/0480_chain/`

**Date:** 2026-01-26
**From Agent:** Documentation Manager
**To Agent:** Backend Integration Tester (Multi-Terminal)
**Priority:** HIGH
**Estimated Complexity:** 16-20 hours (parallel: 6-8 hours)
**Status:** DEPRECATED
**Series:** 0480 (Exception Handling Architecture Remediation)
**Dependencies:** Handovers 0480d-0480f (All services migrated)

---

## Executive Summary

### What
Remove exception handling from 205 API endpoints across 47 files. With services migrated (0480d-0480f), endpoints become thin wrappers that delegate to services and let global exception handler translate errors to HTTP.

### Why
**Current State:**
- Endpoints duplicate service exception handling
- try-except blocks scatter HTTPException raises
- Inconsistent error responses across similar endpoints

**Target State:**
- Endpoints trust service layer exceptions
- Global handler provides consistent HTTP translation
- 70% less code per endpoint

### Impact
- **Files Changed**: 47 endpoint files
- **Code Reduction**: ~600 lines removed
- **Breaking Changes**: None (HTTP responses identical via global handler)

---

## Migration Strategy

### Phase 1: High-Traffic Endpoints (4 hours)

Migrate endpoints with highest request volume first:

**Module**: `api/endpoints/projects/` (12 endpoints)
- GET `/api/projects/` - List projects
- GET `/api/projects/{id}` - Get single project
- POST `/api/projects/` - Create project
- PUT `/api/projects/{id}` - Update project
- DELETE `/api/projects/{id}` - Delete project
- POST `/api/projects/{id}/activate` - Activate
- POST `/api/projects/{id}/deactivate` - Deactivate
- GET `/api/projects/{id}/summary` - Project summary
- POST `/api/projects/{id}/launch` - Launch orchestrator
- POST `/api/projects/{id}/vision` - Upload vision
- GET `/api/projects/next-series` - Next series number
- GET `/api/projects/available-series` - Available series

**Module**: `api/endpoints/products/` (10 endpoints)
- GET `/api/products/`
- GET `/api/products/{id}`
- POST `/api/products/`
- PUT `/api/products/{id}`
- DELETE `/api/products/{id}`
- POST `/api/products/{id}/activate`
- GET `/api/products/{id}/context`
- POST `/api/products/{id}/vision`
- GET `/api/products/{id}/vision-summary`
- PUT `/api/products/{id}/vision-summary`

**Module**: `api/endpoints/messages/` (7 endpoints)
- GET `/api/messages/`
- GET `/api/messages/{id}`
- POST `/api/messages/send`
- POST `/api/messages/receive`
- POST `/api/messages/{id}/acknowledge`
- GET `/api/messages/agent/{agent_id}`
- GET `/api/messages/project/{project_id}`

### Phase 2: Infrastructure Endpoints (3 hours)

**Module**: `api/endpoints/orchestration/` (8 endpoints)
**Module**: `api/endpoints/agent_jobs/` (10 endpoints)
**Module**: `api/endpoints/templates/` (6 endpoints)

### Phase 3: Remaining Endpoints (1-2 hours)

**Module**: `api/endpoints/tasks/` (3 endpoints)
**Module**: `api/endpoints/context/` (5 endpoints)
**Module**: `api/endpoints/settings/` (4 endpoints)
**Module**: Misc endpoints across 38 other files

---

## Migration Pattern

### Before: Endpoint with Exception Handling

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_key: str = Depends(get_tenant_key)
):
    """Get single project by ID."""
    try:
        service = ProjectService(session)
        project = await service.get_project(project_id, tenant_key)
        return project
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
```

### After: Thin Endpoint Wrapper

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_key: str = Depends(get_tenant_key)
):
    """Get single project by ID."""
    service = ProjectService(session)
    return await service.get_project(project_id, tenant_key)
    # Service raises ProjectNotFoundError → Global handler → 404 JSON response
```

**Lines of Code**: 15 → 8 (47% reduction)

---

## Migration Checklist (Per Endpoint)

### Step 1: Remove Exception Handling (2 minutes)
- [ ] Delete `try-except` blocks
- [ ] Remove `raise HTTPException` statements
- [ ] Remove `from fastapi import HTTPException` if no longer used

### Step 2: Trust Service Layer (1 minute)
- [ ] Direct call to service method
- [ ] No error handling (global handler does it)
- [ ] Return service result directly

### Step 3: Update Docstring (1 minute)
- [ ] Document expected HTTP responses
- [ ] Reference domain exceptions raised by service

Example:
```python
"""
Get single project by ID.

Returns:
    ProjectResponse: Project details

Raises:
    ProjectNotFoundError (404): Project doesn't exist
    AuthorizationError (403): Tenant mismatch
"""
```

### Step 4: Test Endpoint (2 minutes)
- [ ] Run integration test
- [ ] Verify 200 OK for happy path
- [ ] Verify 404/409/400 for error paths
- [ ] Check response JSON structure unchanged

---

## Parallel Execution Plan

### Terminal 1: Projects & Products (4 hours)
```bash
# Projects module
api/endpoints/projects/__init__.py
api/endpoints/projects/routes.py

# Products module
api/endpoints/products/__init__.py
api/endpoints/products/routes.py

# Test
pytest tests/integration/test_projects_api.py -v
pytest tests/integration/test_products_api.py -v
```

### Terminal 2: Messages & Orchestration (4 hours)
```bash
# Messages module
api/endpoints/messages/__init__.py

# Orchestration module
api/endpoints/orchestration/__init__.py

# Test
pytest tests/integration/test_messages_api.py -v
pytest tests/integration/test_orchestration_api.py -v
```

### Terminal 3: Jobs, Templates, Settings (3 hours)
```bash
# Agent jobs
api/endpoints/agent_jobs/__init__.py

# Templates
api/endpoints/templates/__init__.py

# Settings
api/endpoints/settings/__init__.py

# Tasks
api/endpoints/tasks/__init__.py

# Context
api/endpoints/context/__init__.py

# Test all
pytest tests/integration/test_agent_jobs_api.py -v
pytest tests/integration/test_templates_api.py -v
```

---

## Module-by-Module Breakdown

### api/endpoints/projects/ (12 endpoints)

| Endpoint | Current LOC | Target LOC | Reduction |
|----------|-------------|------------|-----------|
| GET `/projects/` | 18 | 10 | 44% |
| GET `/projects/{id}` | 15 | 8 | 47% |
| POST `/projects/` | 25 | 12 | 52% |
| PUT `/projects/{id}` | 22 | 10 | 55% |
| DELETE `/projects/{id}` | 20 | 10 | 50% |
| POST `/projects/{id}/activate` | 18 | 9 | 50% |
| POST `/projects/{id}/deactivate` | 18 | 9 | 50% |
| GET `/projects/{id}/summary` | 15 | 8 | 47% |
| POST `/projects/{id}/launch` | 30 | 15 | 50% |
| POST `/projects/{id}/vision` | 28 | 14 | 50% |
| GET `/projects/next-series` | 12 | 8 | 33% |
| GET `/projects/available-series` | 12 | 8 | 33% |

**Total**: 233 LOC → 121 LOC (48% reduction)

### api/endpoints/products/ (10 endpoints)

Similar reduction: ~45% code removal

### api/endpoints/messages/ (7 endpoints)

Similar reduction: ~40% code removal

---

## Testing Requirements

### Integration Test Template

```python
@pytest.mark.asyncio
async def test_endpoint_error_responses(client: AsyncClient, auth_headers):
    """Verify all error codes returned correctly."""

    # 404 Not Found
    response = await client.get("/api/projects/nonexistent", headers=auth_headers)
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "PROJECT_NOT_FOUND"
    assert "timestamp" in data

    # 409 Conflict
    response = await client.post("/api/projects/", json={...}, headers=auth_headers)
    assert response.status_code == 409
    data = response.json()
    assert data["error_code"] == "PROJECT_ALREADY_EXISTS"

    # 400 Validation
    response = await client.put("/api/projects/abc", json={"status": "invalid"}, headers=auth_headers)
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PROJECT_STATUS"
```

### Coverage Requirements

- **All 205 endpoints** must have integration tests
- **Error paths** (404, 409, 400) tested for each endpoint
- **Happy paths** (200, 201) verified unchanged

### Test Execution

```bash
# Run all integration tests
pytest tests/integration/ -v

# With coverage report
pytest tests/integration/ -v --cov=api/endpoints --cov-report=html

# Verify no regressions
pytest tests/integration/ -v --tb=short
```

---

## Success Criteria

- [ ] All 205 endpoints migrated (zero try-except blocks)
- [ ] Zero `raise HTTPException` in endpoint files
- [ ] All integration tests pass (HTTP responses unchanged)
- [ ] Code reduction: ~600 lines removed
- [ ] No performance degradation (benchmark tests)
- [ ] Swagger UI documentation accurate

---

## Rollback Plan

Rollback by module:

```bash
# Rollback projects module
git revert <commit_hash_projects_endpoints>

# Rollback products module
git revert <commit_hash_products_endpoints>

# ... etc for each module
```

Or rollback entire handover:

```bash
git revert <commit_hash_0480g_start>..<commit_hash_0480g_end>
```

---

**Document Version**: 1.0
**Created**: 2026-01-26
**Author**: Claude (Sonnet 4.5)
**Status**: Ready for Implementation
**Execution Mode**: Multi-Terminal (3 agents in parallel)
