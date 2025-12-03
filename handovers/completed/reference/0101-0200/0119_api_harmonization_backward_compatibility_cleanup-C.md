---
**Handover ID:** 0119
**Title:** API Harmonization & Backward Compatibility Cleanup
**Status:** Planning → Ready for Implementation
**Priority:** CRITICAL
**Estimated Effort:** 1-2 days
**Risk Level:** MEDIUM (affects frontend-backend integration)
**Created:** 2025-11-10
**Dependencies:** Handover 0116 (Agent Job Migration), Handover 0109 (API Versioning)
**Blocks:** Production release (broken frontend code exists)
---

# Handover 0119: API Harmonization & Backward Compatibility Cleanup

## Executive Summary

**Problem:** The codebase has accumulated backward compatibility bloat from recent major refactors (Handover 0116: Agent → Job migration, Handover 0109: API versioning). This includes:
- **CRITICAL:** Broken frontend code calling deprecated `/api/v1/agents/` endpoints (404 errors)
- Dual route registrations creating confusion (`/api/prompts` + `/api/v1/prompts`)
- Dead code (448 lines of deprecated `agents.py`)
- Inconsistent API versioning across frontend

**Context:** Two agents recently completed foundational work:
1. **SQLAlchemy 2.0 Migration** - 34 old-style queries migrated, 100% async/await compliance
2. **Orchestrator Messaging** - Message loop automation, MCP tool integration

**Solution:** Since we're pre-release and in dev mode, aggressively clean up all backward compatibility cruft. This is the **last chance** to do this before v3.0 ships.

**Impact:** Without this cleanup:
- Frontend will have broken API calls (404 errors on agent operations)
- Confusing dual API routes will persist into production
- Dead code will accumulate maintenance burden
- Inconsistent versioning will complicate future API changes

---

## Table of Contents

1. [Context & Background](#context--background)
2. [Current State Analysis](#current-state-analysis)
3. [Phase 1: Fix Broken Frontend (CRITICAL)](#phase-1-fix-broken-frontend-critical)
4. [Phase 2: Remove Dual Routes (HIGH)](#phase-2-remove-dual-routes-high)
5. [Phase 3: Delete Dead Code (MEDIUM)](#phase-3-delete-dead-code-medium)
6. [Phase 4: Clean Frontend Config (LOW)](#phase-4-clean-frontend-config-low)
7. [Testing & Validation](#testing--validation)
8. [Success Criteria](#success-criteria)
9. [Risk Mitigation](#risk-mitigation)

---

## Context & Background

### Recent Major Refactors

**Handover 0116 (Agent → Job Migration):**
- Removed `Agent` model from database
- Created `MCPAgentJob` model as replacement
- Disabled `/api/v1/agents/` endpoint in backend
- **Problem:** Frontend was never updated to match

**Handover 0109 (API Versioning):**
- Added `/api/v1/` prefix to all endpoints
- Kept legacy routes for backward compatibility
- **Problem:** Dual registration became permanent, frontend inconsistent

**SQLAlchemy 2.0 Migration (Recent):**
- 34 queries migrated to async/await
- All repositories now use `AsyncSession` and `select()`
- Backend API server compiles and runs cleanly
- **Impact:** Database layer is now solid foundation for cleanup

**Orchestrator Messaging (Recent):**
- Message loop automation implemented
- MCP tools integrated (`send_welcome`, `broadcast_status`, `coordinate_messages`)
- Messaging infrastructure complete
- **Impact:** Core orchestration features ready, need clean API layer

### Why Now?

**Dev Mode Opportunity:**
- No production users to break
- Can make breaking changes freely
- Last chance before v3.0 release
- Clean slate for future development

**Technical Debt Prevention:**
- Dead code accumulates quickly
- Dual routes cause confusion
- Broken frontend code hides in unused components
- Better to fix now than debug later

---

## Current State Analysis

### 🔴 CRITICAL ISSUES (Breaking)

#### Issue 1: Broken Frontend Code - Deprecated Agent Endpoint

**Problem:** Backend disabled `/api/v1/agents/` in Handover 0116, but frontend still calls it.

**Location:** `frontend/src/services/api.js:189-197`

**Broken Code:**
```javascript
agents: {
  list: (projectId) => apiClient.get('/api/v1/agents/', { params: { project_id: projectId } }),
  get: (id) => apiClient.get(`/api/v1/agents/${id}/`),
  create: (data) => apiClient.post('/api/v1/agents/', data),
  health: (id) => apiClient.get(`/api/v1/agents/${id}/health/`),
  decommission: (id, reason) => apiClient.post(`/api/v1/agents/${id}/decommission/`, { reason }),
  tree: (projectId) => apiClient.get('/api/v1/agents/tree', { params: { project_id: projectId } }),
  metrics: (projectId, hours = 24) => apiClient.get('/api/v1/agents/metrics', { params: { project_id: projectId, hours } }),
}
```

**Backend Status:** `api/app.py:762` - Commented out
```python
# DEPRECATED (Handover 0116): Legacy Agent endpoint superseded by agent_jobs.py
# app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
```

**Impact:** Any frontend component using these APIs will fail with 404.

**Frontend Components Affected:**
- `frontend/src/views/AgentsView.vue` (if it calls agent list)
- `frontend/src/components/agents/AgentCard.vue` (if it calls agent health)
- `frontend/src/components/agents/AgentFormDialog.vue` (if it calls agent create)
- Any dashboard component querying agent metrics

**Fix Required:** Migrate to `/api/agent-jobs` endpoints from `agent_jobs.py`

---

#### Issue 2: Frontend Using Legacy /api/prompts Route

**Problem:** Frontend uses `/api/prompts` instead of `/api/v1/prompts`

**Locations:**
1. `frontend/src/services/api.js:402-408`
2. `frontend/src/stores/orchestration.js:65`
3. `frontend/src/components/orchestration/OrchestratorCard.vue:186`
4. `frontend/src/components/orchestration/AgentCard.vue:279`

**Backend:** Both routes work (dual registration), but inconsistent versioning.

**Impact:** Technical debt, confusing API versioning, harder to deprecate legacy routes later.

---

### 🟡 MEDIUM ISSUES (Cleanup Needed)

#### Issue 3: Dual Route Registrations

**Problem:** Two endpoint groups registered twice with different prefixes

**File:** `api/app.py:770-773`

```python
# Orchestration - BOTH routes active
app.include_router(orchestration.router, prefix="/api/orchestrator", tags=["orchestration"])
app.include_router(orchestration.router, prefix="/api/v1/orchestration", tags=["orchestration"])  # Handover 0109

# Prompts - BOTH routes active
app.include_router(prompts.router, prefix="/api/prompts", tags=["prompts"])
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])  # Handover 0109
```

**Impact:**
- Confusion about which route to use
- Maintenance burden (changes must work on both routes)
- Inconsistent API versioning strategy
- Harder to deprecate legacy routes

---

#### Issue 4: Dead Code - Deprecated agents.py File

**Problem:** File exists but is never imported/used

**File:** `api/endpoints/agents.py` (448 lines)

**Status:**
- Not imported in `app.py`
- Superseded by `agent_jobs.py`
- `Agent` model removed from database in migration 0116
- Contains 448 lines of obsolete code

**Impact:**
- Confuses developers (looks active but isn't)
- Adds maintenance burden (must be updated during refactors)
- Takes up codebase space
- Could be accidentally re-enabled

---

### 🟢 LOW PRIORITY (Cosmetic)

#### Issue 5: Frontend Config Cruft

**Problem:** Old agent endpoint config still in frontend config files

**File:** `frontend/src/config/api.js:95-97`

```javascript
// OBSOLETE - Backend disabled these endpoints
agents: '/api/v1/agents/',
agent: '/api/v1/agents/:id',
agentHealth: '/api/v1/agents/:id/health',
```

**Impact:** Minimal - just cleanup for consistency

---

## Phase 1: Fix Broken Frontend (CRITICAL)

**Duration:** 4-6 hours
**Priority:** P0 - Blocking issue
**Risk:** HIGH - Breaking changes to frontend

### 1.1 Map Old Agent API to New Job API

**Reference:** `handovers/completed/0116_0113_COMPLETION_SUMMARY-C.md` for field mappings

**Old → New API Mapping:**

| Old Agent Endpoint | New Job Endpoint | Notes |
|-------------------|------------------|-------|
| `GET /api/v1/agents/` | `GET /api/agent-jobs/` | Returns jobs instead of agents |
| `GET /api/v1/agents/{id}` | `GET /api/agent-jobs/{job_id}` | Job ID instead of agent ID |
| `POST /api/v1/agents/` | `POST /api/agent-jobs/spawn` | Different payload structure |
| `GET /api/v1/agents/{id}/health` | `GET /api/agent-jobs/{job_id}/status` | Status instead of health |
| `POST /api/v1/agents/{id}/decommission` | `POST /api/agent-jobs/{job_id}/terminate` | Terminate instead of decommission |
| `GET /api/v1/agents/tree` | `GET /api/agent-jobs/hierarchy` | Hierarchy instead of tree |
| `GET /api/v1/agents/metrics` | `GET /api/agent-jobs/metrics` | Same concept, different base path |

**Field Mappings (Agent → Job):**

```javascript
// OLD (Agent)
{
  id: "agent-123",
  name: "Backend Implementer",
  status: "active",
  project_id: "proj-456",
  created_at: "2025-11-10T...",
}

// NEW (MCPAgentJob)
{
  job_id: "job-789",
  agent_type: "implementer",
  status: "spawned", // or "acknowledged", "in_progress", "completed", "failed"
  project_id: "proj-456",
  spawned_at: "2025-11-10T...",
  tenant_key: "tenant-123",
  mission: "...",
}
```

### 1.2 Update frontend/src/services/api.js

**File:** `frontend/src/services/api.js`

**Current Code (lines 189-197):**
```javascript
agents: {
  list: (projectId) => apiClient.get('/api/v1/agents/', { params: { project_id: projectId } }),
  get: (id) => apiClient.get(`/api/v1/agents/${id}/`),
  create: (data) => apiClient.post('/api/v1/agents/', data),
  health: (id) => apiClient.get(`/api/v1/agents/${id}/health/`),
  decommission: (id, reason) => apiClient.post(`/api/v1/agents/${id}/decommission/`, { reason }),
  tree: (projectId) => apiClient.get('/api/v1/agents/tree', { params: { project_id: projectId } }),
  metrics: (projectId, hours = 24) => apiClient.get('/api/v1/agents/metrics', { params: { project_id: projectId, hours } }),
}
```

**New Code:**
```javascript
// MIGRATION: Agent endpoints replaced with agent-jobs (Handover 0119)
// Reference: Handover 0116 for Agent → Job migration details
agentJobs: {
  list: (projectId) => apiClient.get('/api/agent-jobs/', { params: { project_id: projectId } }),
  get: (jobId) => apiClient.get(`/api/agent-jobs/${jobId}`),
  spawn: (data) => apiClient.post('/api/agent-jobs/spawn', data),
  status: (jobId) => apiClient.get(`/api/agent-jobs/${jobId}/status`),
  terminate: (jobId, reason) => apiClient.post(`/api/agent-jobs/${jobId}/terminate`, { reason }),
  hierarchy: (projectId) => apiClient.get('/api/agent-jobs/hierarchy', { params: { project_id: projectId } }),
  metrics: (projectId, hours = 24) => apiClient.get('/api/agent-jobs/metrics', { params: { project_id: projectId, hours } }),

  // Additional job-specific endpoints
  acknowledge: (jobId) => apiClient.post(`/api/agent-jobs/${jobId}/acknowledge`),
  reportProgress: (jobId, data) => apiClient.post(`/api/agent-jobs/${jobId}/progress`, data),
  complete: (jobId, data) => apiClient.post(`/api/agent-jobs/${jobId}/complete`, data),
  messages: (jobId) => apiClient.get(`/api/agent-jobs/${jobId}/messages`),
}
```

**Deprecation Strategy:**
```javascript
// DEPRECATED: Legacy agent endpoints removed in Handover 0116
// Use agentJobs.* methods instead
agents: {
  list: () => {
    console.warn('DEPRECATED: Use agentJobs.list() instead');
    return Promise.reject(new Error('Agent API removed in v3.0. Use agentJobs API.'));
  },
  // ... other deprecated methods with same warning pattern
}
```

### 1.3 Update Frontend Components

**Components to Update:**

1. **AgentsView.vue** - Replace `api.agents.list()` with `api.agentJobs.list()`
2. **AgentCard.vue** - Replace `api.agents.get()` and `api.agents.health()` with job equivalents
3. **AgentFormDialog.vue** - Replace `api.agents.create()` with `api.agentJobs.spawn()`
4. **Dashboard components** - Replace `api.agents.metrics()` with `api.agentJobs.metrics()`

**Example Change (AgentsView.vue):**

**Before:**
```javascript
async fetchAgents() {
  try {
    const response = await api.agents.list(this.currentProjectId);
    this.agents = response.data;
  } catch (error) {
    console.error('Failed to fetch agents:', error);
  }
}
```

**After:**
```javascript
async fetchAgentJobs() {
  try {
    const response = await api.agentJobs.list(this.currentProjectId);
    this.agentJobs = response.data;
    // Map to display format if needed
    this.agents = this.agentJobs.map(job => ({
      id: job.job_id,
      name: job.agent_type,
      status: job.status,
      // ... other mappings
    }));
  } catch (error) {
    console.error('Failed to fetch agent jobs:', error);
  }
}
```

### 1.4 Standardize Prompts Route to /api/v1/prompts

**Files to Update:**

1. `frontend/src/services/api.js:402-408`
2. `frontend/src/stores/orchestration.js:65`
3. `frontend/src/components/orchestration/OrchestratorCard.vue:186`
4. `frontend/src/components/orchestration/AgentCard.vue:279`

**Find and Replace:**
- **Find:** `/api/prompts`
- **Replace:** `/api/v1/prompts`

**Example (api.js):**

**Before:**
```javascript
prompts: {
  getOrchestrator: (projectId) => apiClient.get(`/api/prompts/orchestrator/${projectId}`),
  getAgent: (jobId) => apiClient.get(`/api/prompts/agent/${jobId}`),
}
```

**After:**
```javascript
prompts: {
  getOrchestrator: (projectId) => apiClient.get(`/api/v1/prompts/orchestrator/${projectId}`),
  getAgent: (jobId) => apiClient.get(`/api/v1/prompts/agent/${jobId}`),
}
```

### 1.5 Verification Steps

**After changes:**

1. **Build frontend:** `npm run build`
2. **Check for broken imports:** Look for errors referencing `api.agents.*`
3. **Test agent operations:**
   - List agent jobs in AgentsView
   - View job details in AgentCard
   - Spawn new agent job
   - Check agent metrics in Dashboard
4. **Test prompts:**
   - Generate orchestrator prompt
   - Generate agent prompt
   - Verify prompts display correctly

---

## Phase 2: Remove Dual Routes (HIGH)

**Duration:** 1-2 hours
**Priority:** P1 - High priority cleanup
**Risk:** LOW (frontend standardized in Phase 1)

### 2.1 Remove Legacy Orchestration Route

**File:** `api/app.py:770`

**Delete this line:**
```python
app.include_router(orchestration.router, prefix="/api/orchestrator", tags=["orchestration"])
```

**Keep this line:**
```python
app.include_router(orchestration.router, prefix="/api/v1/orchestration", tags=["orchestration"])  # Handover 0109
```

**Verification:**
- Frontend should use `/api/v1/orchestration/*` (updated in Phase 1)
- Legacy `/api/orchestrator/*` will return 404 (expected)

### 2.2 Remove Legacy Prompts Route

**File:** `api/app.py:772`

**Delete this line:**
```python
app.include_router(prompts.router, prefix="/api/prompts", tags=["prompts"])
```

**Keep this line:**
```python
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])  # Handover 0109
```

**Verification:**
- Frontend should use `/api/v1/prompts/*` (updated in Phase 1)
- Legacy `/api/prompts/*` will return 404 (expected)

### 2.3 Update API Documentation

**If OpenAPI/Swagger docs exist:**

1. Verify only `/api/v1/*` routes appear in docs
2. Remove any legacy route references
3. Update route descriptions to indicate versioning strategy

---

## Phase 3: Delete Dead Code (MEDIUM)

**Duration:** 30 minutes
**Priority:** P2 - Cleanup
**Risk:** NONE (code already disabled)

### 3.1 Delete api/endpoints/agents.py

**File to Delete:** `api/endpoints/agents.py` (448 lines)

**Verification Before Deletion:**
1. Confirm not imported in `api/app.py` ✓ (already verified - line 762 commented out)
2. Search codebase for `from api.endpoints import agents` → Should find 0 results
3. Search codebase for `agents.router` → Should find only commented-out line in app.py

**Command:**
```bash
rm api/endpoints/agents.py
```

**Git Commit Message:**
```
Delete deprecated agents.py endpoint (Handover 0119)

- File superseded by agent_jobs.py in Handover 0116
- Agent model removed from database
- Endpoint disabled since Handover 0116
- 448 lines of dead code removed
```

### 3.2 Remove Commented-Out Agent Import

**File:** `api/app.py:762`

**Delete this line:**
```python
# DEPRECATED (Handover 0116): Legacy Agent endpoint superseded by agent_jobs.py
# app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
```

**Reason:** Since we're deleting the file, the comment is meaningless.

---

## Phase 4: Clean Frontend Config (LOW)

**Duration:** 15 minutes
**Priority:** P3 - Cosmetic
**Risk:** NONE

### 4.1 Remove Agent Endpoints from Frontend Config

**File:** `frontend/src/config/api.js:95-97`

**Delete these lines:**
```javascript
agents: '/api/v1/agents/',
agent: '/api/v1/agents/:id',
agentHealth: '/api/v1/agents/:id/health',
```

**Optionally Add (if config-driven):**
```javascript
agentJobs: '/api/agent-jobs/',
agentJob: '/api/agent-jobs/:id',
agentJobStatus: '/api/agent-jobs/:id/status',
```

**Verification:**
- Frontend should continue working (uses direct URLs in `api.js`)
- Config file should only contain active endpoints

---

## Testing & Validation

### Manual Testing Checklist

**Backend API Tests:**
- [ ] `GET /api/agent-jobs/` returns list of jobs
- [ ] `POST /api/agent-jobs/spawn` creates new job
- [ ] `GET /api/agent-jobs/{job_id}` returns job details
- [ ] `GET /api/agent-jobs/{job_id}/status` returns job status
- [ ] `POST /api/agent-jobs/{job_id}/terminate` terminates job
- [ ] `GET /api/v1/prompts/orchestrator/{project_id}` returns orchestrator prompt
- [ ] `GET /api/v1/prompts/agent/{job_id}` returns agent prompt
- [ ] `GET /api/v1/orchestration/*` endpoints work
- [ ] Legacy routes return 404:
  - [ ] `GET /api/v1/agents/` → 404
  - [ ] `GET /api/prompts/*` → 404
  - [ ] `GET /api/orchestrator/*` → 404

**Frontend Tests:**
- [ ] AgentsView loads and displays agent jobs
- [ ] AgentCard shows job details correctly
- [ ] Spawning new agent job works (AgentFormDialog)
- [ ] Agent metrics display in Dashboard
- [ ] Orchestrator prompt generation works
- [ ] Agent prompt generation works
- [ ] No console errors related to API calls
- [ ] No 404 errors in network tab

**Integration Tests:**
- [ ] Full orchestration workflow (spawn → acknowledge → progress → complete)
- [ ] Message sending/receiving between agents
- [ ] User message handling
- [ ] Job termination and cleanup

### Automated Testing

**Backend Tests:**
```bash
# Run agent job API tests
pytest tests/api/test_agent_jobs.py -v

# Run prompts API tests
pytest tests/api/test_prompts.py -v

# Run orchestration API tests
pytest tests/api/test_orchestration.py -v
```

**Frontend Tests:**
```bash
# Run component tests
npm run test:unit

# Run E2E tests (if available)
npm run test:e2e
```

### Regression Testing

**Critical Workflows to Verify:**
1. **Project Creation** → Agent spawning → Job execution → Completion
2. **Message Hub** → Agent communication → User messages
3. **Dashboard** → Metrics display → Job monitoring
4. **Orchestrator** → Prompt generation → Agent coordination

---

## Success Criteria

### Must Have (P0)

- [ ] **No broken API calls** - All frontend components use active endpoints
- [ ] **No 404 errors** - Frontend makes no calls to deprecated routes
- [ ] **Consistent versioning** - All API calls use `/api/v1/*` prefix
- [ ] **Dead code removed** - `agents.py` deleted, commented-out imports removed
- [ ] **Dual routes removed** - Only `/api/v1/*` routes registered

### Should Have (P1)

- [ ] **Frontend config cleaned** - No references to deprecated endpoints
- [ ] **API documentation updated** - Only active routes documented
- [ ] **Migration notes** - Document what changed for future developers

### Nice to Have (P2)

- [ ] **Automated tests updated** - No tests reference old endpoints
- [ ] **Error messages helpful** - If user hits old endpoint, clear error message
- [ ] **Logging cleanup** - Remove logging for deprecated routes

### Metrics for Success

**Code Reduction:**
- Remove 448 lines (agents.py)
- Remove 2 dual route registrations
- Remove frontend config cruft (~10 lines)
- **Total:** ~460 lines of dead code removed

**API Consistency:**
- 100% of frontend API calls use `/api/v1/*` or `/api/*` (no version)
- 0 dual route registrations
- 0 deprecated endpoints in codebase

**Functionality:**
- All critical workflows work (project → orchestration → agents → messages)
- 0 regression bugs introduced
- 0 broken frontend components

---

## Risk Mitigation

### Risk #1: Breaking Frontend in Production

**Risk:** Frontend API changes break existing functionality

**Mitigation:**
- Thorough manual testing of all frontend components
- Automated E2E tests for critical workflows
- Gradual rollout (dev → staging → production)
- Keep deprecated methods with error messages for 1 sprint

**Contingency:**
- Revert to dual routes temporarily
- Add compatibility layer if needed
- Hot-patch specific breaking changes

### Risk #2: Missing API Calls

**Risk:** Some frontend component uses deprecated API but isn't caught in testing

**Mitigation:**
- Search entire frontend codebase for `/api/v1/agents/`
- Search for `api.agents.` method calls
- Monitor browser console for 404 errors during testing
- Add error tracking (Sentry, etc.) to catch missed calls

**Contingency:**
- Re-enable specific deprecated routes temporarily
- Fix component and redeploy
- Add test coverage for that component

### Risk #3: Database Migration Issues

**Risk:** Removing agent code affects database migrations

**Mitigation:**
- Agent model already removed in Handover 0116
- Migration 0116 already ran successfully
- No database changes in this handover
- Keep migration files intact (only remove endpoint code)

**Contingency:**
- Migrations are idempotent (can re-run)
- Database rollback available if needed

### Risk #4: Confusing Developers

**Risk:** Developers look for agent endpoints and can't find them

**Mitigation:**
- Document migration in CHANGELOG
- Update README with API changes
- Add comment in `api/app.py` explaining agent → job migration
- Update API documentation

**Example Comment:**
```python
# NOTE (Handover 0119): Agent endpoints removed in favor of agent-jobs
# - Old: /api/v1/agents/ → New: /api/agent-jobs/
# - Old: Agent model → New: MCPAgentJob model
# - Reference: handovers/0116_0113_COMPLETION_SUMMARY-C.md
```

---

## Implementation Plan

### Day 1: Frontend Migration (6-8 hours)

**Morning (4 hours):**
1. Update `frontend/src/services/api.js`
   - Replace `agents.*` with `agentJobs.*` methods
   - Standardize prompts routes to `/api/v1/prompts`
   - Add deprecated method warnings
2. Update AgentsView.vue
   - Replace `api.agents.list()` with `api.agentJobs.list()`
   - Update data mapping (agent → job fields)
3. Update AgentCard.vue
   - Replace health checks with status checks
   - Update job display logic

**Afternoon (4 hours):**
4. Update AgentFormDialog.vue
   - Replace `api.agents.create()` with `api.agentJobs.spawn()`
   - Update payload structure
5. Update Dashboard components
   - Replace metrics API calls
6. Search for remaining `/api/prompts` references
   - Replace with `/api/v1/prompts`
7. Build frontend and test for errors
8. Manual testing of all updated components
9. Commit: "Migrate frontend from agents API to agent-jobs API (Handover 0119)"

### Day 2: Backend Cleanup & Testing (4-6 hours)

**Morning (2 hours):**
1. Remove dual routes from `api/app.py`
   - Delete `/api/orchestrator` route
   - Delete `/api/prompts` route
2. Delete `api/endpoints/agents.py`
3. Remove commented-out agent import
4. Clean frontend config (`frontend/src/config/api.js`)
5. Commit: "Remove deprecated routes and dead code (Handover 0119)"

**Afternoon (4 hours):**
6. Run backend API tests
7. Run frontend unit tests
8. Manual testing of full workflows:
   - Project creation → orchestration → agent jobs
   - Message hub communication
   - Dashboard metrics
9. Verify no 404 errors in browser console
10. Regression testing
11. Document changes in CHANGELOG
12. Final commit: "Complete API harmonization cleanup (Handover 0119)"

---

## Related Handovers

**Dependencies (must be complete):**
- **Handover 0116:** Agent → Job migration (database model removed)
- **Handover 0109:** API versioning strategy (dual routes created)

**Related:**
- **SQLAlchemy 2.0 Migration:** Backend database layer now clean
- **Orchestrator Messaging:** Message loop and MCP tools integrated
- **TECHNICAL_DEBT_v2.md:** Pre-release cleanup recommendations

**Enables:**
- Production release (removes broken code)
- Future API changes (consistent versioning)
- Developer onboarding (clean, understandable codebase)

---

## Acceptance Criteria

This handover is considered **COMPLETE** when:

1. **No broken API calls** - All frontend components use active endpoints
2. **Frontend builds without errors** - `npm run build` succeeds
3. **Backend tests pass** - `pytest` passes all API tests
4. **Manual testing complete** - All critical workflows verified
5. **Dead code deleted** - `agents.py` removed, no commented-out imports
6. **Dual routes removed** - Only `/api/v1/*` routes registered
7. **Documentation updated** - CHANGELOG, README, API docs reflect changes
8. **Zero regressions** - Existing functionality still works
9. **Code review approved** - Senior developer approves changes
10. **Deployment successful** - Changes deployed to dev environment without issues

---

## Post-Completion Actions

1. **Update CHANGELOG:**
   ```markdown
   ## [v3.0.0-beta] - 2025-11-10

   ### Breaking Changes
   - Removed deprecated `/api/v1/agents/` endpoints (use `/api/agent-jobs/` instead)
   - Removed legacy `/api/prompts` route (use `/api/v1/prompts` instead)
   - Removed legacy `/api/orchestrator` route (use `/api/v1/orchestration` instead)

   ### Removed
   - Deleted `api/endpoints/agents.py` (superseded by agent_jobs.py)
   - Removed dual route registrations
   - Cleaned up deprecated frontend code
   ```

2. **Update README/Documentation:**
   - Add migration guide for developers
   - Update API endpoint list
   - Document agent → job migration

3. **Monitor Production:**
   - Watch for 404 errors in logs
   - Monitor error tracking (Sentry, etc.)
   - Check user reports for broken functionality

4. **Archive Handover:**
   ```bash
   mv handovers/0119_api_harmonization_backward_compatibility_cleanup.md \
      handovers/completed/0119_api_harmonization_backward_compatibility_cleanup-C.md
   ```

---

## Summary Table

| Issue | Type | Priority | Effort | Files Changed |
|-------|------|----------|--------|---------------|
| Broken /api/v1/agents calls | CRITICAL | P0 | 4-6h | Frontend (8+ files) |
| Legacy /api/prompts usage | HIGH | P0 | 1-2h | Frontend (6 files) |
| Dual route orchestration | HIGH | P1 | 15min | app.py |
| Dual route prompts | HIGH | P1 | 15min | app.py |
| Dead agents.py file | MEDIUM | P2 | 5min | Delete 1 file |
| Commented-out import | LOW | P3 | 2min | app.py |
| Frontend config cruft | LOW | P3 | 5min | config/api.js |

**Total Effort:** 1-2 days (8-16 hours)
**Total Files:** ~15-20 files modified/deleted
**Total Lines Removed:** ~460 lines of dead code

---

**Document Version:** 1.0
**Last Updated:** 2025-11-10
**Author:** System Analysis (based on backward compatibility audit)
**Status:** Ready for Implementation
**Estimated Completion:** 2025-11-12 (2 days from start)
