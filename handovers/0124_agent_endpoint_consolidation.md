# Handover 0124: Agent Endpoint Consolidation

**Status:** Ready
**Priority:** High
**Estimated Duration:** 1 week
**Depends On:** ✅ Handover 0123 (ToolAccessor Phase 2)
**Blocks:** Handover 0127 (Deprecated Code Removal)

---

## Executive Summary

Consolidate the fragmented agent-related endpoints into a single, well-organized `api/endpoints/agent_jobs/` module that uses the newly extracted OrchestrationService. **API routes remain IDENTICAL - no breaking changes to frontend.**

### 🚨 CRITICAL REQUIREMENTS

**1. ZERO API Breaking Changes**
- ALL routes stay at `/api/v1/agent-jobs/*` (existing routes)
- Same HTTP methods, same request/response formats
- Frontend sees ZERO difference

**2. Aggressive Code Cleanup**
- DELETE `agents.py` completely (legacy, already marked deprecated)
- DELETE `orchestration.py` (merge into agent_jobs/)
- REMOVE spawn_agents from `projects_lifecycle.py`
- DELETE all old agent-related code
- NO facades, NO "backward compatibility wrappers"

**3. Backend Reorganization Only**
- Reorganize large files into focused modules
- All code uses OrchestrationService
- Clean module structure for maintainability

### Problem Statement

**Current State:**
- Agent functionality scattered across 4+ endpoint files
- Mix of legacy Agent model and new MCPAgentJob model
- 1,200+ lines spread across multiple files
- Direct database access in some endpoints
- Duplicated logic across endpoint files

**Example of Current Fragmentation:**
```
api/endpoints/
├── agents.py              # 400 lines - LEGACY, DELETE THIS
├── agent_jobs.py          # 600 lines - Main operations
├── orchestration.py       # 200 lines - DELETE THIS, merge into agent_jobs/
├── projects_lifecycle.py  # Has spawn_agents - REMOVE, belongs in agent_jobs
└── ...
```

### Desired State

**Reorganized Backend (SAME API routes!):**
```
api/endpoints/agent_jobs/
├── __init__.py           # Export all routers
├── spawn.py              # ~150 lines - spawn operations
├── lifecycle.py          # ~200 lines - acknowledge, complete, error
├── status.py             # ~150 lines - get status, list pending, get mission
├── progress.py           # ~100 lines - report progress
└── orchestration.py      # ~200 lines - orchestrate project, workflow status
```

**API Routes (UNCHANGED!):**
```
POST   /api/v1/agent-jobs/spawn
GET    /api/v1/agent-jobs/pending
POST   /api/v1/agent-jobs/{job_id}/acknowledge
POST   /api/v1/agent-jobs/{job_id}/complete
POST   /api/v1/agent-jobs/{job_id}/error
GET    /api/v1/agent-jobs/{job_id}/mission
GET    /api/v1/agent-jobs/{job_id}
POST   /api/v1/agent-jobs/{job_id}/progress
POST   /api/v1/agent-jobs/orchestrate/{project_id}
GET    /api/v1/agent-jobs/workflow/{project_id}
```

**All endpoints use OrchestrationService** (no direct database access)

---

## Objectives

### Primary Objectives

✅ **Consolidate Agent Endpoints** - All agent operations under `/api/v1/agent-jobs/*`
✅ **Use OrchestrationService** - All endpoints delegate to service layer
✅ **Remove Direct DB Access** - No database operations in endpoint code
✅ **Deprecate Legacy Endpoints** - Mark old `/agents/*` endpoints as deprecated
✅ **Consistent Naming** - Uniform naming across all agent endpoints
✅ **Comprehensive Tests** - >80% coverage on all new endpoints

### Secondary Objectives

✅ **API Documentation** - OpenAPI/Swagger docs for all endpoints
✅ **Error Handling** - Consistent error responses
✅ **Validation** - Pydantic models for request/response validation
✅ **Performance** - No performance degradation from consolidation

---

## Current State Analysis

### Existing Agent Endpoints (Fragmented)

**File:** `api/endpoints/agents.py` (LEGACY - deprecated)
```python
# Uses legacy Agent model (4-state)
POST   /api/v1/agents/spawn           # DEPRECATED
GET    /api/v1/agents/list            # DEPRECATED
GET    /api/v1/agents/{agent_id}      # DEPRECATED
PUT    /api/v1/agents/{agent_id}      # DEPRECATED
DELETE /api/v1/agents/{agent_id}      # DEPRECATED
```

**File:** `api/endpoints/agent_jobs.py` (CURRENT)
```python
# Uses MCPAgentJob model (7-state)
POST   /api/v1/agent-jobs/spawn
GET    /api/v1/agent-jobs/pending
POST   /api/v1/agent-jobs/{job_id}/acknowledge
POST   /api/v1/agent-jobs/{job_id}/complete
POST   /api/v1/agent-jobs/{job_id}/error
GET    /api/v1/agent-jobs/{job_id}/mission
```

**File:** `api/endpoints/orchestration.py`
```python
POST   /api/v1/orchestration/projects/{project_id}/orchestrate
GET    /api/v1/orchestration/projects/{project_id}/workflow-status
```

**File:** `api/endpoints/projects_lifecycle.py`
```python
# Contains spawn_agents method - should be in agent_jobs
POST   /api/v1/projects/{project_id}/spawn-agents
```

### Issues with Current Structure

1. **Fragmentation** - Agent logic in 4+ different files
2. **Inconsistent Naming** - `/agents/` vs `/agent-jobs/` vs `/orchestration/`
3. **Direct DB Access** - Some endpoints bypass service layer
4. **Legacy Code** - Old Agent model still in use
5. **Poor Discoverability** - Hard to find all agent-related endpoints

---

## Proposed Architecture

### New Endpoint Structure

```
api/endpoints/agent_jobs/
├── __init__.py                    # Module exports
├── lifecycle.py                   # Job lifecycle operations
│   ├── POST   /api/v1/agent-jobs/spawn
│   ├── POST   /api/v1/agent-jobs/{job_id}/acknowledge
│   ├── POST   /api/v1/agent-jobs/{job_id}/complete
│   └── POST   /api/v1/agent-jobs/{job_id}/error
│
├── status.py                      # Status and querying
│   ├── GET    /api/v1/agent-jobs/pending
│   ├── GET    /api/v1/agent-jobs/{job_id}
│   └── GET    /api/v1/agent-jobs/{job_id}/mission
│
├── progress.py                    # Progress reporting
│   └── POST   /api/v1/agent-jobs/{job_id}/progress
│
└── orchestration.py               # Project orchestration
    ├── POST   /api/v1/agent-jobs/orchestrate/{project_id}
    └── GET    /api/v1/agent-jobs/workflow/{project_id}
```

### Design Principles

1. **Service Layer Only** - All endpoints use OrchestrationService
2. **No Business Logic** - Endpoints are thin wrappers
3. **Consistent Patterns** - Same structure across all files
4. **Proper Validation** - Pydantic models for all requests/responses
5. **Error Handling** - Standard error format across endpoints

---

## Implementation Plan

### Phase 1: Create New Consolidated Structure (2 days)

**Step 1.1: Create Module Structure**
```bash
mkdir -p api/endpoints/agent_jobs
touch api/endpoints/agent_jobs/__init__.py
touch api/endpoints/agent_jobs/lifecycle.py
touch api/endpoints/agent_jobs/status.py
touch api/endpoints/agent_jobs/progress.py
touch api/endpoints/agent_jobs/orchestration.py
```

**Step 1.2: Create Pydantic Models**
```python
# api/endpoints/agent_jobs/models.py
from pydantic import BaseModel, Field
from typing import Optional

class SpawnAgentRequest(BaseModel):
    agent_type: str = Field(..., description="Type of agent (e.g., 'implementer')")
    agent_name: str = Field(..., description="Unique agent name")
    mission: str = Field(..., description="Agent mission description")
    project_id: str = Field(..., description="Project UUID")
    parent_job_id: Optional[str] = Field(None, description="Parent job UUID")

class SpawnAgentResponse(BaseModel):
    success: bool
    agent_job_id: str
    agent_prompt: str
    mission_stored: bool
    thin_client: bool
    # ... etc
```

**Step 1.3: Implement lifecycle.py**
```python
# api/endpoints/agent_jobs/lifecycle.py
from fastapi import APIRouter, Depends, HTTPException
from giljo_mcp.services.orchestration_service import OrchestrationService
from .models import SpawnAgentRequest, SpawnAgentResponse

router = APIRouter(prefix="/api/v1/agent-jobs", tags=["agent-jobs"])

@router.post("/spawn", response_model=SpawnAgentResponse)
async def spawn_agent_job(
    request: SpawnAgentRequest,
    orchestration_service: OrchestrationService = Depends(get_orchestration_service)
):
    """Spawn a new agent job."""
    result = await orchestration_service.spawn_agent_job(
        agent_type=request.agent_type,
        agent_name=request.agent_name,
        mission=request.mission,
        project_id=request.project_id,
        tenant_key=get_tenant_key(),  # From auth context
        parent_job_id=request.parent_job_id
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result)

    return result

# ... acknowledge, complete, error endpoints
```

**Step 1.4: Implement status.py, progress.py, orchestration.py**
- Follow same pattern as lifecycle.py
- All endpoints delegate to OrchestrationService
- Consistent error handling and validation

### Phase 2: Migrate and DELETE Old Files (1 day)

**Step 2.1: Update Main Router**
```python
# api/main.py or api/router.py
# BEFORE:
from api.endpoints import agent_jobs, agents, orchestration

# AFTER (only agent_jobs module):
from api.endpoints.agent_jobs import spawn, lifecycle, status, progress, orchestration

app.include_router(spawn.router)
app.include_router(lifecycle.router)
app.include_router(status.router)
app.include_router(progress.router)
app.include_router(orchestration.router)
```

**Step 2.2: DELETE agents.py**
```bash
rm api/endpoints/agents.py
rm tests/unit/test_agents_endpoint.py  # Delete old tests too
rm tests/integration/test_agents.py     # Delete integration tests
```

**Step 2.3: DELETE orchestration.py**
```bash
rm api/endpoints/orchestration.py
rm tests/unit/test_orchestration_endpoint.py
```

**Step 2.4: REMOVE spawn_agents from projects_lifecycle.py**
```python
# api/endpoints/projects_lifecycle.py
# DELETE this entire function:
# async def spawn_agents(...):
#     ...  DELETE ALL OF THIS

# If other functions used spawn_agents, update them to call agent_jobs endpoints instead
```

**Step 2.5: Clean Up Imports**
- Remove all imports of deleted files
- Update any code that referenced old agent endpoints
- Verify no references remain using grep

### Phase 3: Comprehensive Cleanup (1 day)

**Step 3.1: Delete Test Files**
```bash
# Find and delete ALL test files related to old structure
find tests/ -name "*agents*" -type f -delete
find tests/ -name "*old_orchestration*" -type f -delete
```

**Step 3.2: Update API Documentation**
- Remove all references to deleted endpoints
- Update OpenAPI schema (auto-generated from remaining routes)
- Verify documentation reflects NEW structure only

**Step 3.3: Search for Zombie References**
```bash
# Search for any references to deleted files
grep -r "from.*endpoints.agents" .
grep -r "from.*endpoints.orchestration" .
grep -r "spawn_agents" api/

# Delete or update ANY files that reference old code
```

### Phase 4: Testing & Validation (2 days)

**Step 4.1: Unit Tests**
- Test each endpoint in isolation
- Mock OrchestrationService
- Validate request/response models
- Test error handling

**Step 4.2: Integration Tests**
- Test full agent job lifecycle
- Test orchestration workflow
- Test tenant isolation
- Test error scenarios

**Step 4.3: Performance Testing**
- Validate no performance degradation
- Check endpoint response times
- Monitor database query counts

### Phase 5: Documentation & Cleanup (1 day)

**Step 5.1: Update Documentation**
- API reference documentation
- Migration guide for API consumers
- Updated architecture diagrams

**Step 5.2: Code Cleanup**
- Remove commented code
- Update imports
- Verify linting passes

---

## Technical Specifications

### Endpoint Patterns

**Pattern 1: Service Delegation**
```python
@router.post("/agent-jobs/spawn")
async def spawn_agent_job(request: SpawnRequest, service: OrchestrationService = Depends(...)):
    result = await service.spawn_agent_job(...)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result
```

**Pattern 2: Tenant Isolation**
```python
def get_tenant_key(token: str = Depends(oauth2_scheme)) -> str:
    # Extract tenant from JWT/session
    return tenant_key
```

**Pattern 3: Error Handling**
```python
try:
    result = await service.method(...)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

### Request/Response Models

**All requests/responses use Pydantic models:**
- Type validation
- OpenAPI documentation
- Clear API contracts

### Testing Strategy

**Test Coverage:**
- Unit tests: >80% coverage on endpoint code
- Integration tests: Full workflow coverage
- Performance tests: Response time validation

---

## Success Criteria

### Functional Requirements

✅ All agent operations accessible via `/api/v1/agent-jobs/*`
✅ All endpoints use OrchestrationService (no direct DB access)
✅ Legacy endpoints marked as deprecated
✅ Backward compatibility maintained
✅ All endpoints properly validated with Pydantic

### Quality Requirements

✅ >80% test coverage on new endpoint code
✅ All tests passing (unit + integration)
✅ API documentation complete and accurate
✅ No performance degradation (< 5% response time increase)
✅ Linting passes (ruff, mypy)

### Documentation Requirements

✅ API reference updated
✅ Migration guide created
✅ Architecture diagram updated
✅ Completion document written

---

## Dependencies

### Required Before Start

✅ **Handover 0123 Complete** - OrchestrationService available
✅ **Testing Infrastructure** - FastAPI test client setup
✅ **Auth Mechanism** - Tenant extraction from requests

### Concurrent Work

⚠️ **None** - Should complete before starting 0125/0126

---

## Risk Assessment

### Risks & Mitigations

**Risk 1: Breaking Changes**
- **Impact:** High
- **Mitigation:** Maintain backward compatibility, deprecate gradually

**Risk 2: Performance Degradation**
- **Impact:** Medium
- **Mitigation:** Performance testing, optimize queries

**Risk 3: Incomplete Migration**
- **Impact:** High
- **Mitigation:** Comprehensive testing, code review

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

1. **Handover 0125**: Projects Modularization (uses ProjectService)
2. **Handover 0126**: Templates & Products Modularization (uses TemplateService)
3. **Handover 0127**: Deprecated Code Removal (remove legacy agent endpoints)

---

**Created:** 2025-11-10
**Author:** Claude (Sonnet 4.5)
**Ready to Execute:** Yes (depends on 0123 ✅)
