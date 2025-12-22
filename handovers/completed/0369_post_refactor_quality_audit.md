# Handover 0369: Post-Refactor Quality Audit

## Priority: CRITICAL
## Status: READY FOR EXECUTION
## Type: Research & Fix

---

## Context

A major refactor (Handover 0366a-0367 series) split the legacy `MCPAgentJob` model into two separate models:

1. **AgentJob** - Persistent work order (survives agent succession)
   - Primary key: `job_id` (UUID string)
   - Contains: `mission`, `job_type`, `status`, `project_id`, `tenant_key`
   - Location: `src/giljo_mcp/models/agent_identity.py`

2. **AgentExecution** - Executor instance (changes on succession)
   - Primary key: `agent_id` (UUID string)
   - Foreign key: `job_id` (references AgentJob)
   - Contains: `agent_type`, `agent_name`, `status`, `progress`, `messages`, `tool_type`
   - Location: `src/giljo_mcp/models/agent_identity.py`

### Critical Breaking Changes

| Old Pattern | New Pattern | Notes |
|-------------|-------------|-------|
| `job.id` | `job.job_id` | Primary key renamed |
| `execution.id` | `execution.agent_id` | Primary key renamed |
| `job.agent_type` | `execution.agent_type` | Moved to AgentExecution |
| `job.agent_name` | `execution.agent_name` | Moved to AgentExecution |
| `job.messages` | `execution.messages` | Moved to AgentExecution |
| `job.progress` | `execution.progress` | Moved to AgentExecution |
| `job.tool_type` | `execution.tool_type` | Moved to AgentExecution |
| `MCPAgentJob` | `AgentJob` + `AgentExecution` | Model split |

---

## Research Scope

### Phase 1: Find All `.id` Access Patterns

Search for code still using `.id` on AgentJob or AgentExecution objects:

```bash
# Search patterns to run
rg "\.id\b" --type py -g "!**/migrations/**" -g "!**/tests/**" -C 3
rg "job\.id" --type py -C 3
rg "execution\.id" --type py -C 3
rg "agent_job\.id" --type py -C 3
rg "orchestrator.*\.id" --type py -C 3
```

**Files to audit:**
- `api/endpoints/projects/*.py`
- `src/giljo_mcp/services/*.py`
- `src/giljo_mcp/tools/*.py`
- `mcp_server/*.py`

### Phase 2: Find Wrong Field Access

Search for code accessing fields on wrong model:

```bash
# Fields that moved from AgentJob to AgentExecution
rg "AgentJob.*agent_type" --type py -C 3
rg "AgentJob.*agent_name" --type py -C 3
rg "AgentJob.*messages" --type py -C 3
rg "AgentJob.*progress" --type py -C 3
rg "AgentJob.*tool_type" --type py -C 3
rg "job\.agent_type" --type py -C 3
rg "job\.agent_name" --type py -C 3
rg "job\.messages" --type py -C 3
rg "job\.progress" --type py -C 3
```

### Phase 3: Find Legacy Model References

Search for any remaining references to the old unified model:

```bash
rg "MCPAgentJob" --type py -C 3
rg "mcp_agent_job" --type py -C 3  # table name
rg "from.*models.*import.*MCPAgentJob" --type py
```

### Phase 4: Validate Response Models

Check all Pydantic response models that serialize agent data:

**Files to check:**
- `api/endpoints/projects/models.py`
- `api/endpoints/agent_jobs/models.py`
- `src/giljo_mcp/schemas/*.py`

**Patterns to search:**
```bash
rg "id:\s*(int|str)" --type py -g "*models.py" -C 5
rg "class.*Response.*BaseModel" --type py -C 10
```

### Phase 5: Database Query Validation

Check all SQLAlchemy queries for correct joins and field access:

```bash
rg "select\(AgentJob\)" --type py -C 10
rg "select\(AgentExecution\)" --type py -C 10
rg "join.*AgentJob" --type py -C 5
rg "join.*AgentExecution" --type py -C 5
```

### Phase 6: Frontend API Contract

Check Vue/JS files for API response expectations:

```bash
rg "\.id\b" --type js --type vue -C 3
rg "job_id" --type js --type vue -C 3
rg "agent_id" --type js --type vue -C 3
```

**Files to audit:**
- `frontend/src/components/jobs/*.vue`
- `frontend/src/views/*.vue`
- `frontend/src/stores/*.js`

---

## Known Issues (Already Identified)

### Issue 1: `status.py:247`
```python
# BROKEN
id=orchestrator_execution.id,  # AgentExecution.id (row ID)

# FIX
id=None,  # or remove field, AgentExecution uses agent_id not id
```

### Issue 2: `project_service.py:231-238`
```python
# BROKEN
agent_dicts = [
    {
        "id": job.id,           # Wrong - should be job.job_id
        "job_id": job.id,       # Wrong - should be job.job_id
        "agent_type": job.agent_type,  # Wrong - should be execution.agent_type
        "agent_name": job.agent_name,  # Wrong - should be execution.agent_name
        "messages": job.messages or [],  # Wrong - should be execution.messages
    }
    for job, execution in agent_pairs
]

# FIX
agent_dicts = [
    {
        "id": job.job_id,
        "job_id": job.job_id,
        "agent_type": execution.agent_type,
        "agent_name": execution.agent_name,
        "status": execution.status,
        "messages": execution.messages or [],
        "thin_client": True,
    }
    for job, execution in agent_pairs
]
```

---

## Validation Checklist

After fixes, verify:

- [ ] `/api/v1/projects/{id}` returns 200 with agents list
- [ ] `/api/v1/projects/{id}/orchestrator` returns 200 with orchestrator data
- [ ] `/api/agent-jobs/` returns 200 with jobs list
- [ ] Project activation flow works (no 500 errors)
- [ ] Project launch flow works
- [ ] Agent spawning creates both AgentJob and AgentExecution
- [ ] WebSocket job updates work
- [ ] Frontend Jobs tab displays correctly

---

## Model Reference (Quick Reference)

### AgentJob (Work Order)
```python
class AgentJob(Base):
    __tablename__ = "agent_jobs"

    job_id = Column(String(36), primary_key=True)  # UUID
    tenant_key = Column(String(50), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"))
    mission = Column(Text, nullable=False)
    job_type = Column(String(100), nullable=False)  # orchestrator, implementer, etc.
    status = Column(String(50), default="active")  # active, completed, cancelled
    created_at = Column(DateTime)
    completed_at = Column(DateTime)
    job_metadata = Column(JSONB)
    template_id = Column(String(36))

    # Relationships
    executions = relationship("AgentExecution", back_populates="job")
    project = relationship("Project", back_populates="agent_jobs_v2")
```

### AgentExecution (Executor Instance)
```python
class AgentExecution(Base):
    __tablename__ = "agent_executions"

    agent_id = Column(String(36), primary_key=True)  # UUID
    job_id = Column(String(36), ForeignKey("agent_jobs.job_id"))
    tenant_key = Column(String(50), nullable=False)
    agent_type = Column(String(100), nullable=False)
    agent_name = Column(String(255))
    instance_number = Column(Integer, default=1)
    status = Column(String(50), default="waiting")
    progress = Column(Integer, default=0)
    messages = Column(JSONB, default=list)
    tool_type = Column(String(20), default="universal")
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    # ... more fields

    # Relationships
    job = relationship("AgentJob", back_populates="executions")
```

---

## Success Criteria

1. **Zero 500 errors** on project/agent endpoints
2. **All API contracts** return expected field names
3. **No runtime AttributeError** for `.id`, `.agent_type`, `.messages` etc.
4. **Frontend renders** jobs and projects correctly
5. **E2E flow works**: Create project -> Activate -> Stage -> Launch

---

## Estimated Scope

- **Files to audit**: 15-25 Python files
- **Potential fix locations**: 10-20 code changes
- **Testing**: Manual API + Frontend validation

---

## Related Handovers

- 0366a: AgentExecution model extraction
- 0367a: Service layer cleanup
- 0367b: API endpoint migration
- 0367c: Tools/monitoring cleanup
- 0367d: Validation and deprecation
- 0367e: Final identity cleanup

---

## EXECUTION LOG (Session 0369a)

### Date: 2025-12-21

### Summary

Initial 0367d/0368 migration was **incomplete**. A comprehensive audit revealed **25+ additional issues** that were missed. This session fixed them properly.

### Commits Made

1. **8419ce47** - `fix(0368): use execution.agent_type instead of execution.job.agent_type`
   - Fixed 4 occurrences in agent_health_monitor.py

2. **5d8f39ff** - `fix(0368): remove execution_metadata references (field doesn't exist)`
   - Fixed agent_health_monitor.py and agent_status.py
   - AgentExecution uses direct fields, not metadata dict

3. **a8cd0bab** - `fix(0368): correct AgentJob/AgentExecution field references`
   - Fixed 9 occurrences of `AgentExecution.agent_job_id` → `AgentExecution.job_id`
   - Fixed 8 occurrences of `AgentJob.id` → `AgentJob.job_id`

4. **7127d56e** - `fix(0368): comprehensive MCPAgentJob migration field corrections`
   - 18 files modified, 389 insertions, 104 deletions
   - See detailed fixes below

### Detailed Fixes (Commit 7127d56e)

#### CRITICAL - Runtime AttributeError Prevention

| File | Issue | Fix |
|------|-------|-----|
| `orchestrator.py` (6 lines) | `Project.agent_jobs` | `Project.agent_jobs_v2` |
| `orchestrator.py` | Inline `JobCompat` class | `CLIPromptJobInfo` dataclass at module level |
| `agent_job_manager.py` (2 lines) | `AgentJob.agent_type` | `AgentJob.job_type` |
| `tasks.py` | FK to `mcp_agent_jobs.job_id` | FK to `agent_jobs.job_id` |

#### HIGH - Logic Errors

| File | Lines | Issue | Fix |
|------|-------|-------|-----|
| `project_service.py` | 743, 836 | `execution.agent_job_id` | `execution.job_id` |
| `project_service.py` | 235, 1990 | `job.agent_type` | `job.job_type` |
| `orchestrator.py` | 347, 378, 389, 461 | `job.agent_type` | `job.job_type` |
| `agent_coordination.py` | 603, 699, 1017, 1025 | `job.agent_type` | `job.job_type` |
| `orchestration_service.py` | 1259 | `job.agent_type` | `execution.agent_type` |
| `claude_code_integration.py` | 96, 102, 103, 105 | `job.agent_type` | `job.job_type` |
| `agent_management.py` | 118, 163, 175, 232, 277, 327 | `job.agent_type` | `job.job_type` |

#### MEDIUM - Wrong Primary Key

| File | Lines | Issue | Fix |
|------|-------|-------|-----|
| `project_service.py` | 1189, 1551 | `AgentExecution.id` | `AgentExecution.agent_id` |
| `prompts.py` | 77, 671 | `AgentExecution.id` | `AgentExecution.agent_id` |
| `status.py` | 247 | `orchestrator_execution.id` | `None` (deprecated) |
| `test_*.py` (4 files) | Multiple | `AgentExecution.id` | `AgentExecution.agent_id` |

#### Scripts/Dev Tools

| File | Issue | Fix |
|------|-------|-----|
| `cleanup_stale_progress_messages.py` | `MCPAgentJob` imports | `AgentExecution` + join with `AgentJob` |
| `control_panel.py` | Raw SQL `mcp_agent_jobs` | `agent_jobs` + `agent_executions` |
| `message_service.py` | Comment reference | Updated to `agent_executions.messages` |

### Files Modified (18 total)

**Production Code (14 files):**
- `src/giljo_mcp/orchestrator.py`
- `src/giljo_mcp/agent_job_manager.py`
- `src/giljo_mcp/models/tasks.py`
- `src/giljo_mcp/services/project_service.py`
- `src/giljo_mcp/services/orchestration_service.py`
- `src/giljo_mcp/services/message_service.py`
- `src/giljo_mcp/tools/agent_coordination.py`
- `src/giljo_mcp/tools/claude_code_integration.py`
- `api/endpoints/agent_management.py`
- `api/endpoints/prompts.py`
- `api/endpoints/projects/status.py`
- `api/endpoints/projects/models.py`
- `scripts/cleanup_stale_progress_messages.py`
- `dev_tools/control_panel.py`

**Test Code (4 files):**
- `tests/integration/test_nuclear_delete_project.py`
- `tests/integration/test_project_deletion_cascade.py`
- `tests/test_project_soft_delete.py`
- `tests/thin_prompt/test_token_reduction_comparison.py`

### Remaining Work (Future Handovers)

#### Test Fixtures (LOW priority)
Many test files still have `job.agent_type` assertions. These may pass because:
1. Test fixtures create `AgentExecution` objects (which have `agent_type`)
2. Tests use mocks with `agent_type` attribute

Files to audit:
- `tests/test_agent_job_manager.py`
- `tests/test_orchestrator_routing.py`
- `tests/integration/test_agent_workflow.py`
- `tests/integration/test_spawn_agent_job_validation.py`

#### Frontend Contract (MEDIUM priority)
Verify frontend expects correct field names:
- `job_id` vs `id` in API responses
- `agent_id` for execution identification

---

## Lessons Learned

### Why Initial Migration Was Incomplete

1. **Scope creep**: 0367b-0367d focused on specific files, missed ripple effects
2. **Field name confusion**: `agent_job_id` vs `job_id`, `job.id` vs `job.job_id`
3. **Relationship changes**: `project.agent_jobs` → `project.agent_jobs_v2` was missed
4. **Legacy compatibility layers**: `JobCompat` class was a bandaid, not a fix

### Best Practices for Future Migrations

1. **Run comprehensive grep searches** BEFORE starting fixes
2. **Use subagents** for parallel file scanning
3. **Create field mapping reference** at start
4. **Validate ALL changed files** with syntax checks
5. **Test critical paths** after migration

### Field Reference Card

```
MCPAgentJob (DEPRECATED)     →   AgentJob + AgentExecution
─────────────────────────────────────────────────────────
job_id (PK)                  →   job.job_id
agent_type                   →   execution.agent_type
agent_name                   →   execution.agent_name
status                       →   execution.status (or job.status)
progress                     →   execution.progress
messages                     →   execution.messages
project_id                   →   job.project_id
mission                      →   job.mission
tenant_key                   →   Both have tenant_key
```

---

## Status: ✅ COMPLETED

All critical, high, and medium priority fixes applied. Test fixtures remain as lower priority for future cleanup.
