# Kickoff Prompt: Complete 0358d - MCPAgentJob Write Path Migration

## Mission

Complete the Agent Identity Refactor by migrating all **WRITE paths** from `MCPAgentJob` to `AgentJob` + `AgentExecution`. The 0366 series updated READ paths but left WRITE paths incomplete, causing a production bug where orchestrators fail with "Orchestrator execution for job {job_id} not found".

## Problem Statement

**Current Bug**: When user clicks "Stage Project", the orchestrator staging prompt fails:
```
get_orchestrator_instructions(job_id='538c7003-...', tenant_key='tk_9DRp...')
→ Error: "Orchestrator execution for job 538c7003-... not found"
```

**Root Cause**: Half-completed migration
- 0366 series updated **READS** → queries `AgentExecution` table
- 0358d (PENDING) was supposed to update **WRITES** → still creates `MCPAgentJob`
- Result: Writes go to `mcp_agent_jobs`, reads look in `agent_executions` → NOT FOUND

## Context: Model Architecture

### Old Model (DEPRECATED)
```python
MCPAgentJob  # Table: mcp_agent_jobs
- job_id: Both work order AND executor identity (conflated)
- 44 fields, monolithic
```

### New Model (0366 series)
```python
AgentJob     # Table: agent_jobs - The WORK (persists across succession)
- job_id (PK): Work order identity
- mission, job_type, status

AgentExecution  # Table: agent_executions - The WORKER (changes on succession)
- agent_id (PK): Executor identity
- job_id (FK): Links to AgentJob
- agent_type, status, progress, instance_number
```

**Key Semantic Change**:
- OLD: `job_id` changes on succession (new orchestrator = new job_id)
- NEW: `job_id` persists, `agent_id` changes on succession

## Reference Documents

**MUST READ** before starting:
1. `handovers/Reference_docs/0358_model_mapping_reference.md` - Complete field mapping
2. `handovers/completed/0358d_mcpagentjob_deprecation-C.md` - Full scope and file list
3. `handovers/completed/0366a_schema_and_models-C.md` - Schema definitions

**Working Example** (already migrated correctly):
- `src/giljo_mcp/tools/tool_accessor.py:1477-1510` - `gil_activate()` creates BOTH models

## Files to Migrate (Priority Order)

### CRITICAL - Fixes the Bug
| File | Line | Method | Action |
|------|------|--------|--------|
| `src/giljo_mcp/thin_prompt_generator.py` | 256 | `generate()` | Create AgentJob + AgentExecution instead of MCPAgentJob |

### HIGH - Production Code
| File | Lines | Method | Action |
|------|-------|--------|--------|
| `src/giljo_mcp/orchestrator.py` | 267, 529, 1083 | Multiple | Update all MCPAgentJob creations |
| `src/giljo_mcp/services/orchestration_service.py` | 1821 | Succession | Update successor creation |
| `src/giljo_mcp/slash_commands/project.py` | 49 | Slash command | Update orchestrator creation |
| `api/endpoints/projects/status.py` | 179 | API endpoint | Update orchestrator creation |

### MEDIUM - Supporting Code
| File | Notes |
|------|-------|
| `src/giljo_mcp/agent_job_manager.py` | 20 occurrences |
| `src/giljo_mcp/services/project_service.py` | 43 occurrences |
| `src/giljo_mcp/services/message_service.py` | 29 occurrences |

## Migration Pattern

### Before (OLD - Creates MCPAgentJob)
```python
from src.giljo_mcp.models import MCPAgentJob

orchestrator = MCPAgentJob(
    tenant_key=tenant_key,
    project_id=project_id,
    job_id=str(uuid4()),
    agent_type="orchestrator",
    mission=mission,
    status="waiting",
    instance_number=1,
    # ... other fields
)
session.add(orchestrator)
```

### After (NEW - Creates Both Models)
```python
from src.giljo_mcp.models import AgentJob, AgentExecution

# Step 1: Create work order
job_id = str(uuid4())
agent_job = AgentJob(
    job_id=job_id,
    tenant_key=tenant_key,
    project_id=project_id,
    mission=mission,
    job_type="orchestrator",
    status="active",
)
session.add(agent_job)

# Step 2: Create executor instance
agent_id = str(uuid4())
agent_execution = AgentExecution(
    agent_id=agent_id,
    job_id=job_id,  # FK to AgentJob
    tenant_key=tenant_key,
    agent_type="orchestrator",
    agent_name="Orchestrator",
    instance_number=1,
    status="waiting",
    progress=0,
    tool_type="universal",
    messages=[],
)
session.add(agent_execution)
await session.commit()
```

## Field Mapping Quick Reference

| MCPAgentJob Field | AgentJob | AgentExecution |
|-------------------|----------|----------------|
| job_id | job_id (PK) | job_id (FK) |
| - | - | agent_id (PK) - NEW |
| tenant_key | tenant_key | tenant_key |
| project_id | project_id | - |
| agent_type | job_type | agent_type |
| mission | mission | - |
| status | status (3 values) | status (7 values) |
| progress | - | progress |
| instance_number | - | instance_number |
| spawned_by | - | spawned_by (NOW agent_id!) |
| handover_to | - | succeeded_by (NOW agent_id!) |

## Success Criteria

### Functional
- [ ] "Stage Project" button creates orchestrator successfully
- [ ] `get_orchestrator_instructions()` finds the orchestrator
- [ ] Orchestrator can call MCP tools and proceed with staging workflow
- [ ] Succession creates new AgentExecution, SAME AgentJob

### Code Quality
- [ ] No new MCPAgentJob creations in production code
- [ ] All migrations use the two-step pattern (job + execution)
- [ ] Tenant isolation maintained (tenant_key on BOTH tables)

### Testing
- [ ] Run existing tests - should pass (queries already migrated)
- [ ] Manual test: Stage a project end-to-end
- [ ] Verify database has records in BOTH new tables

## Verification Commands

```bash
# Check database state after staging a project
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "
SELECT 'agent_jobs' as tbl, COUNT(*) FROM agent_jobs
UNION ALL
SELECT 'agent_executions', COUNT(*) FROM agent_executions
UNION ALL
SELECT 'mcp_agent_jobs', COUNT(*) FROM mcp_agent_jobs;
"

# Run tests
pytest tests/integration/test_mcp_get_orchestrator_instructions.py -v
pytest tests/thin_prompt/ -v
```

## Do NOT

- Do NOT modify query/read paths (already migrated in 0366)
- Do NOT drop MCPAgentJob model or mcp_agent_jobs table (future work)
- Do NOT change API response formats (maintain backward compat)
- Do NOT migrate test files yet (separate effort)

## Commit Message Template

```
fix(0358d): migrate orchestrator creation to AgentJob + AgentExecution

- Update ThinClientPromptGenerator.generate() to create both models
- Update orchestrator.py creation paths
- Update orchestration_service.py succession creation
- Update slash_commands/project.py orchestrator creation
- Update api/endpoints/projects/status.py orchestrator creation

Fixes: Orchestrator execution not found error after 0366 series
Root cause: WRITE paths still used MCPAgentJob while READ paths queried AgentExecution

Part of Agent Identity Refactor (0366 series completion)
See: handovers/completed/0358d_mcpagentjob_deprecation-C.md
```

## Start Here

1. Read `tool_accessor.py:1477-1510` for working example
2. Fix `thin_prompt_generator.py:256` first (unblocks the bug)
3. Test manually: Stage a project
4. Proceed with remaining files

Good luck!
