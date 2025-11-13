---
**Document Type:** Handover
**Handover ID:** 0504
**Title:** Project Endpoints - Lifecycle Operations
**Version:** 1.0
**Created:** 2025-11-12
**Status:** Ready for Execution
**Duration:** 4 hours
**Scope:** Implement 5 project lifecycle endpoints (activate, deactivate, cancel-staging, summary, launch)
**Priority:** 🔴 P0 CRITICAL
**Tool:** ☁️ CCW
**Parallel Execution:** ✅ Yes (Group 1 - Endpoints)
**Parent Project:** Projectplan_500.md
---

# Handover 0504: Project Endpoints - Lifecycle Operations

## 🎯 Mission Statement
Implement production-grade project lifecycle endpoints using ProjectService methods from Handover 0501. Fix 5 critical HTTP 501/404 errors: activate, deactivate, cancel-staging, summary, and launch URL mismatch.

## 📋 Prerequisites
**Must be complete before starting:**
- ✅ Handover 0501 complete (ProjectService methods implemented)
- ✅ ProjectService has: activate_project(), deactivate_project(), cancel_staging(), get_project_summary(), launch_project()

## ⚠️ Problem Statement

### Issue 1-5: Missing/Stubbed Endpoints
**Evidence**: Projectplan_500.md lines 40-45

| Endpoint | Method | Current State | Impact |
|----------|--------|---------------|---------|
| `/projects/{id}/activate` | POST | HTTP 501 | Cannot activate projects |
| `/projects/{id}/deactivate` | POST | HTTP 404 | Cannot pause projects |
| `/projects/{id}/cancel-staging` | POST | HTTP 501 | Cannot cancel staged projects |
| `/projects/{id}/summary` | GET | HTTP 501 | Dashboard broken |
| `/projects/{id}/launch` | POST | Wrong URL | Launch button broken |

**Root Cause**: Endpoints created during Handover 0127 (Projects Modularization) but never implemented. Service methods now exist from Handover 0501, just need endpoint wiring.

## ✅ Solution Approach

### Endpoint Implementation Pattern
All endpoints follow same pattern:
1. Get ProjectService dependency
2. Call service method
3. Return response with correct schema
4. Handle exceptions with proper HTTP codes

### URL Routing Structure
```
/api/v1/projects/
  ├── / (GET, POST) - CRUD operations
  ├── /{id} (GET, PATCH, DELETE)
  ├── /{id}/activate (POST) - lifecycle
  ├── /{id}/deactivate (POST) - lifecycle
  ├── /{id}/cancel-staging (POST) - lifecycle
  ├── /{id}/launch (POST) - orchestrator launch
  └── /{id}/summary (GET) - metrics
```

## 📝 Implementation Tasks

### Task 1: Implement activate_project Endpoint (30 min)
**File**: `api/endpoints/projects/lifecycle.py` (create if doesn't exist)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.models.schemas.project_schemas import ProjectResponse
from api.dependencies.auth import get_current_active_user
from api.dependencies.database import get_db
from src.giljo_mcp.models import User

router = APIRouter()

@router.post(
    "/{project_id}/activate",
    response_model=ProjectResponse,
    summary="Activate project",
    description="Activate staged or paused project (enforces Single Active Project constraint)"
)
async def activate_project(
    project_id: str,
    force: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> ProjectResponse:
    """
    Activate project.

    State transitions:
    - staging → active (initial launch)
    - paused → active (resume)

    Automatically deactivates other active projects in same product.
    """
    service = ProjectService(db, current_user.tenant_key)
    try:
        project = await service.activate_project(project_id, force=force)
        return project
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Task 2: Implement deactivate_project Endpoint (20 min)
**File**: `api/endpoints/projects/lifecycle.py`

```python
@router.post(
    "/{project_id}/deactivate",
    response_model=ProjectResponse,
    summary="Deactivate project",
    description="Pause active project (active → paused)"
)
async def deactivate_project(
    project_id: str,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> ProjectResponse:
    """Deactivate (pause) active project."""
    service = ProjectService(db, current_user.tenant_key)
    try:
        project = await service.deactivate_project(project_id, reason=reason)
        return project
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Task 3: Implement cancel_staging Endpoint (20 min)
**File**: `api/endpoints/projects/lifecycle.py`

```python
@router.post(
    "/{project_id}/cancel-staging",
    response_model=ProjectResponse,
    summary="Cancel staging project",
    description="Cancel project in staging state (staging → cancelled)"
)
async def cancel_staging(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> ProjectResponse:
    """Cancel project in staging state."""
    service = ProjectService(db, current_user.tenant_key)
    try:
        project = await service.cancel_staging(project_id)
        return project
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Task 4: Implement get_project_summary Endpoint (30 min)
**File**: `api/endpoints/projects/metrics.py` (create new file for metrics)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.models.schemas.project_schemas import ProjectSummaryResponse
from api.dependencies.auth import get_current_active_user
from api.dependencies.database import get_db
from src.giljo_mcp.models import User

router = APIRouter()

@router.get(
    "/{project_id}/summary",
    response_model=ProjectSummaryResponse,
    summary="Get project summary",
    description="Get project summary with job metrics and progress"
)
async def get_project_summary(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> ProjectSummaryResponse:
    """Get project summary with metrics."""
    service = ProjectService(db, current_user.tenant_key)
    try:
        summary = await service.get_project_summary(project_id)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Task 5: Implement launch_project Endpoint (30 min)
**File**: `api/endpoints/projects/orchestration.py` (create new file)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any

from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.models.schemas.project_schemas import ProjectLaunchResponse
from api.dependencies.auth import get_current_active_user
from api.dependencies.database import get_db
from src.giljo_mcp.models import User

router = APIRouter()

@router.post(
    "/{project_id}/launch",
    response_model=ProjectLaunchResponse,
    summary="Launch project orchestrator",
    description="Create orchestrator job and generate launch prompt"
)
async def launch_project(
    project_id: str,
    launch_config: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> ProjectLaunchResponse:
    """Launch project orchestrator with thin-client prompt."""
    service = ProjectService(db, current_user.tenant_key)
    try:
        launch_response = await service.launch_project(
            project_id,
            launch_config=launch_config
        )
        return launch_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Task 6: Fix PATCH Endpoint (15 min)
**File**: `api/endpoints/projects/crud.py`

**Find current PATCH implementation**:
```bash
grep -n "@router.patch" api/endpoints/projects/crud.py
```

**Update to support all fields** (not just mission):
```python
from pydantic import BaseModel

class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    mission: Optional[str] = None
    config_data: Optional[Dict[str, Any]] = None

@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project"
)
async def update_project(
    project_id: str,
    updates: ProjectUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    service: ProjectService = Depends(get_project_service)
) -> ProjectResponse:
    """Update project fields."""
    update_dict = updates.dict(exclude_unset=True)
    project = await service.update_project(project_id, update_dict)
    return project
```

### Task 7: Update Router Registration (15 min)
**File**: `api/endpoints/projects/__init__.py`

```python
from fastapi import APIRouter
from .crud import router as crud_router
from .lifecycle import router as lifecycle_router  # Add
from .metrics import router as metrics_router      # Add
from .orchestration import router as orch_router   # Add

router = APIRouter()
router.include_router(crud_router, tags=["projects"])
router.include_router(lifecycle_router, tags=["projects", "lifecycle"])
router.include_router(metrics_router, tags=["projects", "metrics"])
router.include_router(orch_router, tags=["projects", "orchestration"])
```

### Task 8: Add Response Schemas (30 min)
**File**: `src/giljo_mcp/models/schemas/project_schemas.py`

**Add if missing**:
```python
class ProjectSummaryResponse(BaseModel):
    id: str
    name: str
    status: str
    mission: Optional[str]

    # Metrics
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    active_jobs: int = 0
    pending_jobs: int = 0

    # Progress
    completion_percentage: float = 0.0

    # Timestamps
    created_at: datetime
    activated_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None

    # Product context
    product_id: str
    product_name: str

    class Config:
        from_attributes = True

class ProjectLaunchResponse(BaseModel):
    project_id: str
    orchestrator_job_id: str
    launch_prompt: str
    status: str = "active"

    class Config:
        from_attributes = True
```

### Task 9: Frontend API Client Update (30 min)
**File**: `frontend/src/services/api.js`

**Add/update project lifecycle methods**:
```javascript
// In api.projects object
projects: {
  // ... existing methods ...

  activate: (projectId, force = false) =>
    apiClient.post(`/api/v1/projects/${projectId}/activate`, { force }),

  deactivate: (projectId, reason = null) =>
    apiClient.post(`/api/v1/projects/${projectId}/deactivate`, { reason }),

  cancelStaging: (projectId) =>
    apiClient.post(`/api/v1/projects/${projectId}/cancel-staging`),

  getSummary: (projectId) =>
    apiClient.get(`/api/v1/projects/${projectId}/summary`),

  launch: (projectId, config = null) =>
    apiClient.post(`/api/v1/projects/${projectId}/launch`, config),
}
```

## 🧪 Testing Strategy

### Manual Testing with Postman
```bash
# 1. Activate project
curl -X POST http://localhost:7274/api/v1/projects/{id}/activate \
  -H "Authorization: Bearer {token}"
# Expected: 200 OK, ProjectResponse with status='active'

# 2. Deactivate project
curl -X POST http://localhost:7274/api/v1/projects/{id}/deactivate \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Testing"}'
# Expected: 200 OK, ProjectResponse with status='paused'

# 3. Cancel staging
curl -X POST http://localhost:7274/api/v1/projects/{id}/cancel-staging \
  -H "Authorization: Bearer {token}"
# Expected: 200 OK, ProjectResponse with status='cancelled'

# 4. Get summary
curl -X GET http://localhost:7274/api/v1/projects/{id}/summary \
  -H "Authorization: Bearer {token}"
# Expected: 200 OK, ProjectSummaryResponse with metrics

# 5. Launch project
curl -X POST http://localhost:7274/api/v1/projects/{id}/launch \
  -H "Authorization: Bearer {token}"
# Expected: 200 OK, ProjectLaunchResponse with orchestrator_job_id

# 6. Update project
curl -X PATCH http://localhost:7274/api/v1/projects/{id} \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Name", "description": "New Desc"}'
# Expected: 200 OK, updated project
```

### Frontend Integration Testing
- [ ] Projects page loads without errors
- [ ] Activate button works (staging → active)
- [ ] Pause button works (active → paused)
- [ ] Resume button works (paused → active)
- [ ] Cancel button works (staging → cancelled)
- [ ] Summary metrics display correctly
- [ ] Launch button creates orchestrator job

## ✅ Success Criteria
- [ ] Zero HTTP 501 errors for project endpoints
- [ ] Zero HTTP 404 errors for deactivate
- [ ] All 5 lifecycle endpoints return 200
- [ ] Project summary includes accurate job metrics
- [ ] Launch endpoint creates orchestrator job
- [ ] Launch response includes thin-client prompt
- [ ] PATCH endpoint updates all fields
- [ ] Frontend API client methods work
- [ ] Single Active Project constraint enforced
- [ ] WebSocket events emitted for state changes

## 🔄 Rollback Plan
1. Revert lifecycle.py: `git rm api/endpoints/projects/lifecycle.py` (if new)
2. Revert metrics.py: `git rm api/endpoints/projects/metrics.py` (if new)
3. Revert orchestration.py: `git rm api/endpoints/projects/orchestration.py` (if new)
4. Revert crud.py: `git checkout HEAD~1 -- api/endpoints/projects/crud.py`
5. Revert schemas: `git checkout HEAD~1 -- src/giljo_mcp/models/schemas/project_schemas.py`
6. Revert frontend: `git checkout HEAD~1 -- frontend/src/services/api.js`

## 📚 Related Handovers
**Depends on**:
- 0501 (ProjectService Implementation) - service methods

**Parallel with** (Group 1):
- 0503 (Product Endpoints)
- 0505 (Orchestrator Succession Endpoint)
- 0506 (Settings Endpoints)

**Blocks**:
- 0509 (Succession UI Components) - needs launch endpoint

## 🛠️ Tool Justification
**Why CCW (Cloud)**:
- Pure API endpoint changes
- No service layer changes (already done in 0501)
- No database changes
- Can run in parallel with other endpoint work
- Fast iteration for HTTP routing

## 📊 Parallel Execution
**✅ CAN RUN IN PARALLEL** (Group 1 - Endpoints)

Execute simultaneously with: 0503, 0505, 0506

---
**Status:** Ready for Execution
**Estimated Effort:** 4 hours
**Archive Location:** `handovers/completed/0504_project_endpoints-COMPLETE.md`

---

## 🎉 COMPLETION SUMMARY

**Status:** ✅ COMPLETE
**Completed:** 2025-11-13
**Actual Effort:** ~2 hours
**Commit:** 4d26375

### Implementation Summary

Successfully implemented all 5 project lifecycle endpoints plus fixed PATCH endpoint:

1. **POST /projects/{id}/activate** - Activate staged/paused projects (lifecycle.py:30-97)
2. **POST /projects/{id}/deactivate** - Deactivate active projects (lifecycle.py:100-163)
3. **POST /projects/{id}/cancel-staging** - Cancel staging state (lifecycle.py:289-350)
4. **GET /projects/{id}/summary** - Get comprehensive metrics (status.py:67-108)
5. **POST /projects/{id}/launch** - Launch orchestrator (lifecycle.py:357-403)
6. **PATCH /projects/{id}** - Fixed to handle all fields (crud.py:329-400)

### Key Achievements

✅ Zero HTTP 501 errors - All TODOs replaced with production implementations
✅ Zero HTTP 404 errors - deactivate endpoint added successfully
✅ All endpoints return appropriate 200/400/404 status codes
✅ Project summary includes job metrics (total/completed/failed/active/pending)
✅ Launch endpoint creates orchestrator job via ProjectService
✅ Launch response includes thin-client prompt
✅ PATCH endpoint now supports name, description, mission, status updates
✅ Frontend API client already had all required methods
✅ Single Active Project constraint enforced
✅ WebSocket events emitted by ProjectService

### Files Modified

- `api/endpoints/projects/lifecycle.py` (+254 lines, 4 endpoints)
- `api/endpoints/projects/status.py` (+42 lines, fixed summary)
- `api/endpoints/projects/crud.py` (+45 lines, fixed PATCH)

### Tests Created

- `tests/api/test_project_lifecycle_endpoints_handover_0504.py` (1,011 lines, 31 tests)
- `tests/api/TEST_COVERAGE_HANDOVER_0504.md` (coverage documentation)

**Test Coverage:** >80% target met with comprehensive success/error case coverage

### Implementation Approach

Followed existing codebase patterns:
- Used ProjectService for all business logic (no direct DB access in endpoints)
- Imported centralized schemas from `src/giljo_mcp/models/schemas.py`
- Consistent error handling (404 for not found, 400 for business logic errors)
- Proper logging with user context
- Token-efficient inline documentation

### Deviations from Handover Plan

1. **File Structure:** Used existing `lifecycle.py` and `status.py` instead of creating separate `metrics.py` and `orchestration.py` files (followed established patterns)
2. **Schema Location:** Used schemas from `src/giljo_mcp/models/schemas.py` (already existed from Handover 0501)
3. **Frontend:** No changes needed - API client already had all methods

### Lessons Learned

1. ✅ **Existing patterns save time** - Following codebase structure was faster than creating new files
2. ✅ **Service layer completeness** - Handover 0501 did excellent groundwork
3. ✅ **Centralized schemas** - Single source of truth prevented duplication
4. ✅ **Test-driven validation** - 31 comprehensive tests ensure robustness

### Next Steps

Ready for:
- **Handover 0507** (API Client URL Fixes) - Can now proceed
- **Handover 0509** (Succession UI Components) - Depends on 0505 still
- **Integration Testing** - Manual curl testing in local environment

---

**Handover 0504 successfully completed and committed.**
**Branch:** `claude/project-0504-011CV5QgUdruFiK7nA4s3UsR`
**Commit:** `4d26375`
