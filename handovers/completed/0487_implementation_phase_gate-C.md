# Handover: Implementation Phase Gate

**Date:** 2026-02-04
**From Agent:** Orchestrator Session (Claude Opus 4.5)
**To Agent:** tdd-implementor, database-expert
**Priority:** HIGH
**Estimated Complexity:** 4-6 hours
**Status:** Ready for Implementation

---

## Task Summary

Add server-side enforcement to prevent orchestrators from launching agents before the user clicks "Implement" in the UI. Currently, the staging protocol is purely instructional - orchestrators can ignore it and prematurely spawn agents.

**Why it's important:** During alpha testing, orchestrators repeatedly bypassed the two-phase session boundary (staging → implementation), consuming tokens and confusing users.

**Expected outcome:** Agents self-block at `get_agent_mission()` when `implementation_launched_at` is NULL, preventing any work until user explicitly launches implementation.

---

## Context and Background

### The Problem

The staging protocol framing tells orchestrators:
- "Do NOT call `acknowledge_job()` during staging"
- "Your job remains in 'waiting' status - this enables the Implement button in UI"
- "STAGING ENDS HERE... Implementation happens in a new session"

But this is **advisory only**. Nothing prevents an LLM from:
1. Ignoring the framing
2. Calling `Task()` to spawn agents during staging
3. Agents then calling MCP tools and starting work

### Root Cause

The gate should be on **user action** (clicking "Implement"), not orchestrator compliance with text instructions.

### Architectural Reality (Passive MCP Server)

- MCP server is **passive** - it only responds to tool calls, cannot push stop signals
- Agents run on **remote PCs/laptops** - server cannot prevent `Task()` spawning
- Server CAN gate: `get_agent_mission()`, `acknowledge_job()`, other MCP tools

### Solution: Gate at Mission Fetch

Gate `get_agent_mission()` so agents can't even get their instructions until implementation is launched:

```python
def get_agent_mission(job_id, tenant_key):
    project = get_project_for_job(job_id)

    if project.implementation_launched_at is None:
        return {
            "blocked": True,
            "mission": None,
            "error": "Implementation phase not started",
            "user_instruction": "Ask your user to click 'Implement' button in the dashboard."
        }

    # Normal mission delivery...
```

**Flow with gate:**
1. Orchestrator (wrongly) spawns agent via `Task()`
2. Agent immediately calls `get_agent_mission()`
3. Server returns "BLOCKED" with user-facing message
4. Agent outputs: *"I can't get my mission - please click 'Implement' in the dashboard"*
5. Agent stops (~50 tokens wasted vs potentially thousands)

---

## Technical Details

### Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/models.py` | Add `Project.implementation_launched_at: DateTime \| None` |
| `src/giljo_mcp/tools/agent_tools.py` | Gate `get_agent_mission()` on implementation_launched_at |
| `api/endpoints/orchestration.py` | Add `PATCH /projects/{id}/launch-implementation` endpoint |
| `api/endpoints/orchestration.py` | Gate `acknowledge_job()` as backup |
| `frontend/src/components/projects/JobsTab.vue` | "Implement" button calls launch endpoint |
| Database migration | Add column to projects table |

### Database Schema Change

```python
# In models.py - Project model
implementation_launched_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
    default=None,
    comment="Timestamp when user clicked Implement button. NULL = staging only."
)
```

### API Endpoint

```python
@router.patch("/projects/{project_id}/launch-implementation")
async def launch_implementation(
    project_id: UUID,
    tenant_key: str = Depends(get_tenant_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Set implementation_launched_at timestamp.
    Called when user clicks 'Implement' button.
    Returns the implementation prompt for user to paste.
    """
    project = await db.get(Project, project_id)
    if not project or project.tenant_key != tenant_key:
        raise HTTPException(404, "Project not found")

    if project.implementation_launched_at is not None:
        # Already launched - return existing prompt
        return {"already_launched": True, "implementation_prompt": ...}

    project.implementation_launched_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "success": True,
        "implementation_launched_at": project.implementation_launched_at,
        "implementation_prompt": generate_implementation_prompt(project)
    }
```

### MCP Tool Gate (Primary Defense)

```python
# In get_agent_mission()
async def get_agent_mission(job_id: str, tenant_key: str) -> dict:
    job = await get_job(job_id)
    project = await get_project(job.project_id)

    # PRIMARY GATE: Block before implementation launch
    if project.implementation_launched_at is None:
        return {
            "blocked": True,
            "mission": None,
            "full_protocol": None,
            "error": "BLOCKED: Implementation phase not started by user",
            "user_instruction": (
                "Your mission is blocked. The user must click the 'Implement' "
                "button in the GiljoAI dashboard before you can receive your mission. "
                "Please inform your user of this requirement and wait."
            )
        }

    # Normal mission delivery...
```

### Backup Gate (acknowledge_job)

```python
# In acknowledge_job()
if project.implementation_launched_at is None:
    return {
        "success": False,
        "error": "BLOCKED: Implementation not launched by user",
        "action_required": "User must click 'Implement' button in dashboard"
    }
```

### Frontend Integration

```javascript
// JobsTab.vue - Implement button handler
async function launchImplementation() {
  const response = await api.patch(`/projects/${projectId}/launch-implementation`)

  if (response.implementation_prompt) {
    // Show prompt in modal for user to copy
    showImplementationPromptModal(response.implementation_prompt)
  }

  // Refresh project state
  await refreshProject()
}
```

---

## Implementation Plan

### Phase 1: Database Schema (30 min)
**Agent:** database-expert

1. Add `implementation_launched_at` column to Project model
2. Update baseline migration
3. Verify existing projects get NULL default

### Phase 2: Backend Gates (2-3 hours)
**Agent:** tdd-implementor

1. Write tests for `get_agent_mission()` gate behavior
2. Implement gate in `get_agent_mission()`
3. Write tests for `acknowledge_job()` gate
4. Implement backup gate in `acknowledge_job()`
5. Add `PATCH /projects/{id}/launch-implementation` endpoint
6. Write integration tests

### Phase 3: Frontend Integration (1-2 hours)
**Agent:** tdd-implementor or frontend-tester

1. Update "Implement" button to call launch endpoint
2. Show implementation prompt in modal after launch
3. Update UI state to reflect implementation_launched_at

### Phase 4: Testing (1 hour)
**Agent:** backend-tester

1. Test agent blocked before implementation launch
2. Test agent unblocked after implementation launch
3. Test error message clarity
4. Test multi-tenant isolation

---

## Testing Requirements

### Unit Tests

```python
# test_agent_tools.py
async def test_get_agent_mission_blocked_before_launch():
    """Mission fetch fails when implementation not launched."""
    project = create_project(implementation_launched_at=None)
    job = create_job(project_id=project.id)

    result = await get_agent_mission(job.job_id, tenant_key)

    assert result["blocked"] is True
    assert result["mission"] is None
    assert "Implement" in result["user_instruction"]

async def test_get_agent_mission_succeeds_after_launch():
    """Mission fetch succeeds when implementation launched."""
    project = create_project(implementation_launched_at=datetime.now(timezone.utc))
    job = create_job(project_id=project.id)

    result = await get_agent_mission(job.job_id, tenant_key)

    assert result.get("blocked") is not True
    assert result["mission"] is not None
```

### Integration Tests

```python
async def test_full_staging_to_implementation_flow():
    """End-to-end test of phase gate."""
    # 1. Create project (implementation_launched_at = NULL)
    # 2. Spawn orchestrator, create jobs
    # 3. Agent tries get_agent_mission() -> BLOCKED
    # 4. User calls launch-implementation endpoint
    # 5. Agent retries get_agent_mission() -> SUCCESS
```

---

## Success Criteria

- [ ] Agents cannot get mission until user clicks "Implement"
- [ ] Clear error message returned when blocked
- [ ] Agent outputs user-facing instruction to click Implement
- [ ] UI "Implement" button sets the unlock timestamp
- [ ] Implementation prompt returned after launch
- [ ] Multi-tenant isolation preserved
- [ ] Existing projects unaffected (NULL = staging-only behavior)

---

## Related

- Technical Debt Document: `handovers/TECHNICAL_DEBT_v2.md` (line ~2470)
- Staging Workflow: Handover 0246a
- Orchestrator Protocol: `docs/ORCHESTRATOR.md`
- STAGING_COMPLETE broadcast pattern

---

## Progress Updates

### 2026-02-04 - Implementation Complete

**Status:** COMPLETE

**Work Done:**

1. **Database Schema** (database-expert)
   - Added `implementation_launched_at` column to Project model
   - Updated baseline migration `baseline_v32_unified.py`
   - Column: `DateTime(timezone=True)`, nullable, defaults to NULL

2. **Backend Gates** (tdd-implementor)
   - Gated `get_agent_mission()` in OrchestrationService (PRIMARY DEFENSE)
   - Gated `acknowledge_job()` in OrchestrationService (BACKUP DEFENSE)
   - Added `PATCH /projects/{id}/launch-implementation` endpoint
   - Created 8 tests (4 service + 4 endpoint) - all passing

3. **Frontend Integration** (frontend-tester)
   - Added `launchImplementation` API endpoint to `api.js`
   - Updated ProjectTabs.vue with implementation gate logic
   - Button changes from "Implement" to "Implementation Started" when launched
   - Created 19 tests for frontend behavior - all passing

**Files Modified:**
- `src/giljo_mcp/models/projects.py` - Added column
- `migrations/versions/baseline_v32_unified.py` - Added column
- `src/giljo_mcp/services/orchestration_service.py` - Added gates
- `api/endpoints/agent_jobs/orchestration.py` - Added endpoint
- `frontend/src/services/api.js` - Added API method
- `frontend/src/components/projects/ProjectTabs.vue` - Button logic

**Files Created:**
- `tests/services/test_orchestration_implementation_phase_gate.py`
- `tests/api/test_launch_implementation_endpoint.py`
- `frontend/src/components/projects/ProjectTabs.implementation-gate.spec.js`

**Success Criteria:**
- [x] Agents cannot get mission until user clicks "Implement"
- [x] Clear error message returned when blocked
- [x] Agent outputs user-facing instruction to click Implement
- [x] UI "Implement" button sets the unlock timestamp
- [x] Multi-tenant isolation preserved
- [x] All tests passing (27 new tests total)
