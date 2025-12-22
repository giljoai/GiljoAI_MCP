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
