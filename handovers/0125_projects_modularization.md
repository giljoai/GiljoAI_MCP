# Handover 0125: Projects Modularization

**Status:** Ready
**Priority:** High
**Estimated Duration:** 1 week
**Depends On:** ✅ Handover 0123 (ToolAccessor Phase 2)
**Blocks:** Handover 0127 (Deprecated Code Removal)

---

## Executive Summary

Modularize the monolithic project endpoints into focused modules that use ProjectService for all operations. **API routes remain IDENTICAL - no breaking changes to frontend.**

### 🚨 CRITICAL REQUIREMENTS

**1. ZERO API Breaking Changes**
- ALL routes stay at `/api/v1/projects/*` (existing routes)
- Same HTTP methods, same request/response formats
- Frontend sees ZERO difference

**2. Aggressive Code Cleanup**
- DELETE `projects_crud.py` after migration (replace with projects/crud.py)
- DELETE `projects_lifecycle.py` after migration (replace with projects/lifecycle.py)
- DELETE `projects_completion.py` after migration (replace with projects/completion.py)
- DELETE all old project-related code and tests
- NO facades, NO "backward compatibility wrappers"

**3. Backend Reorganization Only**
- Split large files into focused modules
- All code uses ProjectService
- Clean module structure for maintainability

### Problem Statement

**Current State:**
- Project endpoints in 3 large files (1,500+ total lines)
- Some endpoints bypass ProjectService (direct DB access)
- Mixed concerns in single files
- Hard to navigate and test

**Example of Current Structure:**
```
api/endpoints/
├── projects_crud.py          (~600 lines) - DELETE after migration
├── projects_lifecycle.py     (~500 lines) - DELETE after migration
├── projects_completion.py    (~400 lines) - DELETE after migration
```

### Desired State

**Reorganized Backend (SAME API routes!):**
```
api/endpoints/projects/
├── __init__.py               # Export all routers
├── crud.py                   (~200 lines) - CRUD operations
├── lifecycle.py              (~200 lines) - Lifecycle management
├── status.py                 (~150 lines) - Status queries
└── completion.py             (~200 lines) - Completion workflow
```

**API Routes (UNCHANGED!):**
```
POST   /api/v1/projects
GET    /api/v1/projects
GET    /api/v1/projects/{project_id}
PUT    /api/v1/projects/{project_id}
PUT    /api/v1/projects/{project_id}/mission
POST   /api/v1/projects/{project_id}/activate
POST   /api/v1/projects/{project_id}/switch
POST   /api/v1/projects/{project_id}/cancel
POST   /api/v1/projects/{project_id}/restore
GET    /api/v1/projects/{project_id}/status
POST   /api/v1/projects/{project_id}/complete
GET    /api/v1/projects/{project_id}/summary
```

**All endpoints use ProjectService** (no direct DB access)

---

## Objectives

### Primary Objectives

✅ **Modularize Project Endpoints** - Split into focused modules by concern
✅ **Use ProjectService** - All endpoints delegate to service layer
✅ **Remove Direct DB Access** - No database operations in endpoint code
✅ **Consistent Patterns** - Same structure as agent_jobs consolidation (0124)
✅ **Reduce File Sizes** - From 600+ lines to 150-250 lines per file
✅ **Comprehensive Tests** - >80% coverage on all modularized endpoints

### Secondary Objectives

✅ **API Documentation** - Complete OpenAPI/Swagger docs
✅ **Error Handling** - Consistent error responses
✅ **Validation** - Pydantic models for all requests/responses
✅ **Performance** - No performance degradation

---

## Current State Analysis

### Existing Project Endpoints

**File:** `api/endpoints/projects_crud.py` (~600 lines)
```python
# CRUD operations
POST   /api/v1/projects                    # create_project
GET    /api/v1/projects                    # list_projects
GET    /api/v1/projects/{project_id}       # get_project
PUT    /api/v1/projects/{project_id}       # update_project
DELETE /api/v1/projects/{project_id}       # delete_project (deprecated)
PUT    /api/v1/projects/{project_id}/mission  # update_mission
```

**File:** `api/endpoints/projects_lifecycle.py` (~500 lines)
```python
# Lifecycle operations
POST   /api/v1/projects/{project_id}/activate
POST   /api/v1/projects/{project_id}/switch
GET    /api/v1/projects/{project_id}/status
POST   /api/v1/projects/{project_id}/cancel
POST   /api/v1/projects/{project_id}/restore
POST   /api/v1/projects/{project_id}/spawn-agents  # Should be in agent_jobs
```

**File:** `api/endpoints/projects_completion.py` (~400 lines)
```python
# Completion workflow
POST   /api/v1/projects/{project_id}/complete
POST   /api/v1/projects/{project_id}/close     # Deprecated alias
GET    /api/v1/projects/{project_id}/summary
```

### Issues with Current Structure

1. **Large Files** - 400-600 lines makes navigation difficult
2. **Mixed Concerns** - CRUD + business logic + validation in same file
3. **Direct DB Access** - Some endpoints bypass ProjectService
4. **Inconsistent Patterns** - Different error handling across files
5. **Poor Modularity** - Hard to test and maintain

---

## Proposed Architecture

### New Endpoint Structure

```
api/endpoints/projects/
├── __init__.py                    # Module exports and router setup
│
├── crud.py                        # CRUD operations (~200 lines)
│   ├── POST   /api/v1/projects
│   ├── GET    /api/v1/projects
│   ├── GET    /api/v1/projects/{project_id}
│   └── PUT    /api/v1/projects/{project_id}/mission
│
├── lifecycle.py                   # Lifecycle operations (~200 lines)
│   ├── POST   /api/v1/projects/{project_id}/activate
│   ├── POST   /api/v1/projects/{project_id}/switch
│   ├── POST   /api/v1/projects/{project_id}/cancel
│   └── POST   /api/v1/projects/{project_id}/restore
│
├── status.py                      # Status queries (~150 lines)
│   ├── GET    /api/v1/projects/{project_id}/status
│   └── GET    /api/v1/projects/{project_id}/metrics
│
└── completion.py                  # Completion workflow (~200 lines)
    ├── POST   /api/v1/projects/{project_id}/complete
    └── GET    /api/v1/projects/{project_id}/summary
```

### Design Principles

1. **Service Layer Only** - All endpoints use ProjectService
2. **Single Responsibility** - Each module handles one concern
3. **Thin Endpoints** - Minimal logic, delegate to service
4. **Consistent Patterns** - Same structure as agent_jobs (0124)
5. **Proper Validation** - Pydantic models throughout

---

## Implementation Plan

### Phase 1: Create Modular Structure (2 days)

**Step 1.1: Create Module Structure**
```bash
mkdir -p api/endpoints/projects
touch api/endpoints/projects/__init__.py
touch api/endpoints/projects/crud.py
touch api/endpoints/projects/lifecycle.py
touch api/endpoints/projects/status.py
touch api/endpoints/projects/completion.py
touch api/endpoints/projects/models.py
```

**Step 1.2: Create Pydantic Models**
```python
# api/endpoints/projects/models.py
from pydantic import BaseModel, Field
from typing import Optional

class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    mission: str = Field(..., min_length=1)
    description: str = Field("", max_length=1000)
    product_id: Optional[str] = None
    status: str = Field("inactive", pattern="^(active|inactive)$")
    context_budget: int = Field(150000, ge=1000, le=1000000)

class CreateProjectResponse(BaseModel):
    success: bool
    project_id: str
    name: str
    status: str
    tenant_key: str

class ListProjectsResponse(BaseModel):
    success: bool
    projects: list[dict]
    count: int

# ... etc for all operations
```

**Step 1.3: Implement crud.py**
```python
# api/endpoints/projects/crud.py
from fastapi import APIRouter, Depends, HTTPException
from giljo_mcp.services.project_service import ProjectService
from .models import CreateProjectRequest, CreateProjectResponse

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

@router.post("", response_model=CreateProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    project_service: ProjectService = Depends(get_project_service),
    tenant_key: str = Depends(get_tenant_key)
):
    """Create a new project."""
    result = await project_service.create_project(
        name=request.name,
        mission=request.mission,
        description=request.description,
        product_id=request.product_id,
        tenant_key=tenant_key,
        status=request.status,
        context_budget=request.context_budget
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result

@router.get("", response_model=ListProjectsResponse)
async def list_projects(
    status: Optional[str] = None,
    project_service: ProjectService = Depends(get_project_service),
    tenant_key: str = Depends(get_tenant_key)
):
    """List all projects with optional status filter."""
    result = await project_service.list_projects(
        status=status,
        tenant_key=tenant_key
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result

# ... get_project, update_mission endpoints
```

**Step 1.4: Implement lifecycle.py**
```python
# api/endpoints/projects/lifecycle.py
from fastapi import APIRouter, Depends, HTTPException
from giljo_mcp.services.project_service import ProjectService
from .models import LifecycleResponse

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

@router.post("/{project_id}/switch", response_model=LifecycleResponse)
async def switch_project(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service)
):
    """Switch to a different project."""
    result = await project_service.switch_project(project_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result

@router.post("/{project_id}/cancel", response_model=LifecycleResponse)
async def cancel_project(
    project_id: str,
    reason: Optional[str] = None,
    project_service: ProjectService = Depends(get_project_service)
):
    """Cancel a project."""
    result = await project_service.cancel_project(project_id, reason)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result

# ... restore, activate endpoints
```

**Step 1.5: Implement status.py and completion.py**
- Follow same pattern as above
- All delegate to ProjectService
- Consistent error handling

### Phase 2: Migrate and DELETE Old Files (1 day)

**Step 2.1: Update Main Router**
```python
# api/main.py or api/router.py
# BEFORE:
from api.endpoints import projects_crud, projects_lifecycle, projects_completion

# AFTER (only projects module):
from api.endpoints.projects import crud, lifecycle, status, completion

app.include_router(crud.router)
app.include_router(lifecycle.router)
app.include_router(status.router)
app.include_router(completion.router)
```

**Step 2.2: DELETE projects_crud.py**
```bash
rm api/endpoints/projects_crud.py
rm tests/unit/test_projects_crud.py
rm tests/integration/test_projects_crud.py
```

**Step 2.3: DELETE projects_lifecycle.py**
```bash
rm api/endpoints/projects_lifecycle.py
rm tests/unit/test_projects_lifecycle.py
```

**Step 2.4: DELETE projects_completion.py**
```bash
rm api/endpoints/projects_completion.py
rm tests/unit/test_projects_completion.py
```

**Step 2.5: Clean Up Imports**
- Remove all imports of deleted files
- Update any code that referenced old project endpoints
- Verify no references remain using grep

### Phase 3: Comprehensive Cleanup (1 day)

**Step 3.1: Remove Direct DB Access**
- Audit all endpoints for database imports
- Ensure all use ProjectService
- Remove unused database session dependencies

**Step 3.2: Standardize Error Handling**
```python
# Common error handler
def handle_service_result(result: dict) -> dict:
    if not result.get("success"):
        error = result.get("error", "Unknown error")
        raise HTTPException(status_code=400, detail=error)
    return result
```

**Step 3.3: Optimize Imports**
- Remove unused imports
- Organize imports consistently
- Update __init__.py exports

### Phase 4: Testing & Validation (2 days)

**Step 4.1: Unit Tests**
```python
# tests/unit/api/endpoints/projects/test_crud.py
@pytest.mark.asyncio
async def test_create_project_success():
    # Mock ProjectService
    mock_service = Mock(spec=ProjectService)
    mock_service.create_project = AsyncMock(return_value={
        "success": True,
        "project_id": "test-id",
        "name": "Test Project",
        "status": "active",
        "tenant_key": "test-tenant"
    })

    # Test endpoint
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "Test Project",
            "mission": "Test mission"
        },
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["project_id"] == "test-id"
```

**Step 4.2: Integration Tests**
- Test full project lifecycle
- Test error scenarios
- Test tenant isolation

**Step 4.3: Performance Testing**
- Validate response times
- Check database query counts
- Monitor memory usage

### Phase 5: Documentation (1 day)

**Step 5.1: API Documentation**
- Update OpenAPI schema
- Add endpoint descriptions
- Document request/response models

**Step 5.2: Migration Guide**
- Document endpoint moves
- Provide examples
- List any breaking changes (none expected)

---

## Technical Specifications

### Endpoint Patterns

**Pattern 1: Service Delegation**
```python
@router.post("/{project_id}/complete")
async def complete_project(
    project_id: str,
    summary: Optional[str] = None,
    service: ProjectService = Depends(get_project_service)
):
    result = await service.complete_project(project_id, summary)
    return handle_service_result(result)
```

**Pattern 2: Tenant Isolation**
```python
async def get_tenant_key(token: str = Depends(oauth2_scheme)) -> str:
    # Extract from JWT or session
    return tenant_key

# Use in endpoint
@router.get("")
async def list_projects(
    tenant_key: str = Depends(get_tenant_key),
    service: ProjectService = Depends(get_project_service)
):
    return await service.list_projects(tenant_key=tenant_key)
```

**Pattern 3: Validation**
```python
# All requests validated with Pydantic
class UpdateMissionRequest(BaseModel):
    mission: str = Field(..., min_length=10, max_length=10000)

@router.put("/{project_id}/mission")
async def update_mission(
    project_id: str,
    request: UpdateMissionRequest,  # Auto-validated
    service: ProjectService = Depends(get_project_service)
):
    result = await service.update_project_mission(project_id, request.mission)
    return handle_service_result(result)
```

### Testing Strategy

**Coverage Targets:**
- Unit tests: >80% endpoint code coverage
- Integration tests: Full workflow coverage
- Performance tests: < 5% degradation

---

## Success Criteria

### Functional Requirements

✅ All project operations accessible via `/api/v1/projects/*`
✅ All endpoints use ProjectService (no direct DB access)
✅ File sizes reduced to 150-250 lines per module
✅ Backward compatibility maintained
✅ All endpoints validated with Pydantic

### Quality Requirements

✅ >80% test coverage on endpoint code
✅ All tests passing (unit + integration)
✅ API documentation complete
✅ No performance degradation (< 5% increase)
✅ Code linting passes

### Documentation Requirements

✅ API reference updated
✅ Migration guide created (if needed)
✅ Architecture diagram updated
✅ Completion document written

---

## Dependencies

### Required Before Start

✅ **Handover 0121 Complete** - ProjectService available (already done)
✅ **Handover 0123 Complete** - Service pattern established (already done)
✅ **Testing Infrastructure** - FastAPI test client

### Concurrent Work

✅ **Can run parallel to 0124** - Different endpoint families
⚠️ **Should coordinate with 0126** - May share patterns

---

## Risk Assessment

### Risks & Mitigations

**Risk 1: API Changes**
- **Impact:** High
- **Mitigation:** Maintain backward compatibility, no route changes

**Risk 2: Service Layer Gaps**
- **Impact:** Medium
- **Mitigation:** ProjectService already complete from 0121

**Risk 3: File Organization Confusion**
- **Impact:** Low
- **Mitigation:** Clear documentation, import aliases

---

## Rollback Plan

**Full backup exists before refactoring begins.**

If critical issues arise that cannot be fixed within 1 day:
1. **Revert entire commit** - Use git to rollback all changes
2. **Restore from backup** - Project is fully backed up before starting
3. **Fix issues offline** - Debug in separate branch
4. **Re-attempt refactoring** - Once issues understood

**No partial rollbacks** - Either commit works completely or revert everything.

No data loss risk - only code organization changes, database untouched.

---

## Next Steps After Completion

1. **Handover 0126**: Templates & Products Modularization (uses TemplateService)
2. **Handover 0127**: Deprecated Code Removal
3. **Handover 0129**: Integration Testing

---

**Created:** 2025-11-10
**Author:** Claude (Sonnet 4.5)
**Ready to Execute:** Yes (depends on 0123 ✅)
