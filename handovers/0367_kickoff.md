# 0367 Kickoff: MCPAgentJob Cleanup Migration

**Living Document** - Each agent team updates this after completing their phase.

**Last Updated**: 2025-12-21
**Current Phase**: 0367b COMPLETE - Ready for 0367c
**Overall Progress**: 2/4 phases complete

---

## Quick Start for Agent Teams

1. Read this ENTIRE document first
2. Read your specific handover (e.g., `0367a_service_layer_cleanup.md`)
3. Check the "Handover Notes" section below for updates from previous phases
4. Complete your phase
5. **UPDATE THIS DOCUMENT** with your handover notes before finishing

---

## The Problem

After the 0366 Agent Identity Refactor, the codebase has a **dual-model architecture** that was never completed:

| Model | Table | Purpose | Status |
|-------|-------|---------|--------|
| `MCPAgentJob` | `mcp_agent_jobs` | OLD monolithic model | DEPRECATED but still used |
| `AgentJob` | `agent_jobs` | NEW work order (persistent) | Partially adopted |
| `AgentExecution` | `agent_executions` | NEW executor instance | Partially adopted |

**Result**:
- READ paths query `AgentExecution` (new)
- WRITE paths still create `MCPAgentJob` in some places
- Fallback/bridge code throughout codebase
- "Orchestrator execution not found" errors

**Goal**: Remove ALL MCPAgentJob usage from production code. ONE system only.

---

## Scope

| Category | Files | References | This Series |
|----------|-------|------------|-------------|
| Production code | 35 | 367 | YES - 0367a-d |
| Test files | 169 | 1,291 | NO - future 0368 |

---

## Critical Field Mapping

When migrating code, use this mapping:

| MCPAgentJob Field | New Location | Notes |
|-------------------|--------------|-------|
| `job_id` | `AgentJob.job_id` | **SEMANTIC CHANGE**: Now means WORK ORDER, not executor |
| `job_id` (for executor) | `AgentExecution.agent_id` | Use this when you need executor identity |
| `tenant_key` | BOTH tables | Must filter on BOTH in joins |
| `project_id` | `AgentJob.project_id` | Job-level only |
| `agent_type` | Split: `AgentJob.job_type` + `AgentExecution.agent_type` | WHAT vs WHO |
| `mission` | `AgentJob.mission` | Stored ONCE, not duplicated |
| `status` | `AgentJob.status` (3 values) OR `AgentExecution.status` (7 values) | Different enums! |
| `progress` | `AgentExecution.progress` | Execution-level |
| `instance_number` | `AgentExecution.instance_number` | Execution-level |
| `spawned_by` | `AgentExecution.spawned_by` | **NOW agent_id, not job_id!** |
| `handover_to` | `AgentExecution.succeeded_by` | **RENAMED + NOW agent_id!** |
| `messages` | `AgentExecution.messages` | Execution-level JSONB |
| `job_metadata` | `AgentJob.job_metadata` | Job-level JSONB |

**Full reference**: `handovers/Reference_docs/0358_model_mapping_reference.md`

---

## Code Patterns

### Pattern 1: Query for Agent Data (READ)

**OLD (MCPAgentJob):**
```python
from src.giljo_mcp.models import MCPAgentJob

stmt = select(MCPAgentJob).where(
    MCPAgentJob.job_id == job_id,
    MCPAgentJob.tenant_key == tenant_key,
)
result = await session.execute(stmt)
job = result.scalar_one_or_none()
```

**NEW (AgentExecution with Job):**
```python
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from sqlalchemy.orm import joinedload

stmt = (
    select(AgentExecution)
    .options(joinedload(AgentExecution.job))
    .where(
        AgentExecution.job_id == job_id,  # or agent_id if you have that
        AgentExecution.tenant_key == tenant_key,
    )
)
result = await session.execute(stmt)
execution = result.scalar_one_or_none()

# Access job data via relationship
mission = execution.job.mission
project_id = execution.job.project_id
```

### Pattern 2: Create New Agent (WRITE)

**OLD (MCPAgentJob):**
```python
orchestrator = MCPAgentJob(
    job_id=str(uuid4()),
    tenant_key=tenant_key,
    project_id=project_id,
    agent_type="orchestrator",
    mission=mission,
    status="waiting",
    instance_number=1,
)
session.add(orchestrator)
```

**NEW (Two-step creation):**
```python
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution

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
    job_id=job_id,
    tenant_key=tenant_key,
    agent_type="orchestrator",
    agent_name="Orchestrator #1",
    instance_number=1,
    status="waiting",
    progress=0,
    messages=[],
)
session.add(agent_execution)
await session.commit()
```

### Pattern 3: Succession (New Executor, Same Job)

**OLD**: Created entirely new MCPAgentJob

**NEW**:
```python
# Same job_id, new agent_id
successor_agent_id = str(uuid4())
successor = AgentExecution(
    agent_id=successor_agent_id,
    job_id=existing_job_id,  # SAME job
    tenant_key=tenant_key,
    agent_type="orchestrator",
    instance_number=previous_instance + 1,
    spawned_by=previous_agent_id,  # Link to predecessor
    status="waiting",
)
session.add(successor)

# Update predecessor
predecessor.succeeded_by = successor_agent_id
predecessor.status = "decommissioned"
```

---

## Phases Overview

| Phase | Handover | Focus | Est. Time | Status |
|-------|----------|-------|-----------|--------|
| **0367a** | `0367a_service_layer_cleanup.md` | Services (206 refs) | 8-12 hrs | ✅ COMPLETE |
| **0367b** | `0367b_api_endpoint_migration.md` | API endpoints (103 refs) | 6-8 hrs | ✅ COMPLETE |
| **0367c-1** | `0367c-1_monitoring_orchestrator_cleanup.md` | Monitoring + Orchestrator (46 refs) | 2-3 hrs | PENDING |
| **0367c-2** | `0367c-2_tools_prompt_cleanup.md` | Tools + Prompts (49 refs) | 2-3 hrs | PENDING |
| **0367d** | `0367d_validation_and_deprecation.md` | Validation & cleanup | 2-4 hrs | PENDING |

**Dependency**: 0367a ✅ → 0367b ✅ → 0367c-1 → 0367c-2 → 0367d (sequential for safety).

---

## Files by Phase

### 0367a: Service Layer (CRITICAL PATH)
| File | Refs | Priority |
|------|------|----------|
| `src/giljo_mcp/services/project_service.py` | 44 | P0 |
| `src/giljo_mcp/services/message_service.py` | 29 | P0 |
| `src/giljo_mcp/agent_job_manager.py` | 20 | P0 |
| `src/giljo_mcp/services/orchestration_service.py` | 20 | P0 |
| `src/giljo_mcp/agent_message_queue.py` | 8 | P1 |
| `src/giljo_mcp/job_monitoring.py` | 8 | P1 |

### 0367b: API Endpoints
| File | Refs | Priority |
|------|------|----------|
| `api/endpoints/prompts.py` | 28 | P0 |
| `api/endpoints/statistics.py` | 21 | P0 |
| `api/endpoints/agent_jobs/filters.py` | 13 | P1 |
| `api/endpoints/agent_jobs/table_view.py` | 12 | P1 |
| `api/endpoints/agent_jobs/succession.py` | 11 | P1 |
| `api/endpoints/projects/status.py` | 11 | P1 |
| `api/endpoints/agent_jobs/operations.py` | 7 | P2 |

### 0367c-1: Monitoring & Orchestrator
| File | Refs | Priority |
|------|------|----------|
| `src/giljo_mcp/monitoring/agent_health_monitor.py` | 23 | P0 |
| `src/giljo_mcp/orchestrator.py` | 21 | P0 |
| `src/giljo_mcp/orchestrator_succession.py` | 2 | P1 |

### 0367c-2: Tools & Prompt Generation
| File | Refs | Priority |
|------|------|----------|
| `src/giljo_mcp/staging_rollback.py` | 18 | P0 |
| `src/giljo_mcp/thin_prompt_generator.py` | 17 | P0 |
| `src/giljo_mcp/tools/orchestration.py` | 4 | P1 |
| `src/giljo_mcp/tools/agent_coordination.py` | 3 | P1 |
| `src/giljo_mcp/tools/__init__.py` | 2 | P1 |
| `src/giljo_mcp/tools/tool_accessor.py` | 2 | P1 |
| `src/giljo_mcp/tools/agent_status.py` | 1 | P2 |
| `src/giljo_mcp/tools/optimization.py` | 1 | P2 |
| `src/giljo_mcp/tools/project.py` | 1 | P2 |

### 0367d: Validation
- Verify zero MCPAgentJob refs in production
- Full test suite pass
- Mark model deprecated
- Document table deprecation plan

---

## Known Bridge Code Locations

**MUST REMOVE** - These are the fallback/dual-system patterns:

| File | Lines | Description |
|------|-------|-------------|
| `orchestration_service.py` | 1372-1398 | Legacy fallback query |
| `orchestration_service.py` | 1815-1879 | Legacy succession path |
| `thin_prompt_generator.py` | 202-221 | MCPAgentJob fallback check |
| `agent_job_manager.py` | 19 | `Job = MCPAgentJob` alias |
| `project_service.py` | 1777, 1796-1803 | Dual query patterns |

---

## Verification Commands

```bash
# Count MCPAgentJob references (should decrease to ~10 after cleanup)
grep -r "MCPAgentJob" src/ api/ --include="*.py" | wc -l

# Check specific file
grep -n "MCPAgentJob" src/giljo_mcp/services/project_service.py

# Run tests
pytest tests/services/ -v
pytest tests/integration/ -v

# Check database state
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "
SELECT 'agent_jobs' as tbl, COUNT(*) FROM agent_jobs
UNION ALL SELECT 'agent_executions', COUNT(*) FROM agent_executions
UNION ALL SELECT 'mcp_agent_jobs', COUNT(*) FROM mcp_agent_jobs;
"
```

---

## Handover Notes

**IMPORTANT**: Each agent team MUST update this section after completing their phase.

### Phase 0367a Handover Notes
**Status**: ✅ COMPLETE
**Completed By**: Claude Opus 4.5 (TDD with 5 parallel subagents)
**Date**: 2025-12-21
**Duration**: ~2 hours (parallelized via subagents)

**What was done**:
- [x] Created TDD test file: `tests/services/test_0367a_mcpagentjob_removal.py`
- [x] Removed MCPAgentJob imports from all 6 service layer files
- [x] Replaced MCPAgentJob queries with AgentJob + AgentExecution patterns
- [x] Removed legacy fallback/bridge code in orchestration_service.py
- [x] Removed `Job = MCPAgentJob` alias in agent_job_manager.py
- [x] All 10 TDD tests pass (GREEN phase verified)

**Files modified**:
- `src/giljo_mcp/services/orchestration_service.py` - Removed import, removed fallback blocks (lines 1372-1398, 1815-1879)
- `src/giljo_mcp/services/project_service.py` - Removed 3 imports, replaced ~10 query patterns
- `src/giljo_mcp/services/message_service.py` - Removed import, updated 9 query locations
- `src/giljo_mcp/agent_job_manager.py` - Removed Job alias, replaced all Job refs with AgentJob
- `src/giljo_mcp/agent_message_queue.py` - Removed import, updated queries
- `src/giljo_mcp/job_monitoring.py` - Removed import, updated monitoring queries

**Breaking changes**:
- None for callers - service interfaces unchanged
- Internal implementation now uses AgentJob + AgentExecution exclusively

**Issues encountered**:
- Test fixture signatures required careful reading of actual method APIs
- AgentJobManager uses synchronous patterns - larger refactor deferred
- Some docstring comments still mention MCPAgentJob for historical context (intentional)

**Notes for next phase**:
- Remaining MCPAgentJob refs in `src/giljo_mcp/` are in: tools/, monitoring/agent_health_monitor.py, models/
- 0367b (API endpoints) and 0367c (tools/monitoring) can now proceed in parallel
- Deprecation warnings still fire from test fixtures - expected until 0368 (test cleanup)

**MCPAgentJob Reference Counts (post-0367a)**:
| Layer | Refs | Phase |
|-------|------|-------|
| Services | **0** ✅ | 0367a DONE |
| API Endpoints | **10** ✅ | 0367b DONE (7 files migrated, 10 refs remain in orchestration.py + templates/crud.py) |
| Monitoring | 23 | 0367c |
| Tools | 14 | 0367c |
| Other src/ | 58 | 0367c |

**Verification command**: `grep -r "MCPAgentJob" src/giljo_mcp/ api/ --include="*.py" | grep -v models | grep -v __pycache__ | wc -l`

---

### Phase 0367b Handover Notes
**Status**: ✅ COMPLETE
**Completed By**: Claude Opus 4.5 (TDD with 4 parallel subagents)
**Date**: 2025-12-21
**Duration**: ~1 hour (parallelized via subagents)

**What was done**:
- [x] Created TDD test file: `tests/api/test_0367b_mcpagentjob_removal.py` (18 tests)
- [x] Migrated all 7 target API endpoint files from MCPAgentJob to AgentJob + AgentExecution
- [x] Replaced 103 MCPAgentJob references with new dual-model queries
- [x] All 18 TDD tests pass (GREEN phase verified)

**Files modified**:
- `api/endpoints/prompts.py` - Removed import, replaced 28 query patterns with AgentExecution + joinedload
- `api/endpoints/statistics.py` - Removed 3 local imports, replaced 21 count/aggregation queries
- `api/endpoints/agent_jobs/filters.py` - Removed import, updated 13 filter queries
- `api/endpoints/agent_jobs/table_view.py` - Removed import, updated 12 table data queries
- `api/endpoints/agent_jobs/succession.py` - Removed import & fallback code, updated 11 succession queries
- `api/endpoints/agent_jobs/operations.py` - Removed import, updated 10 CRUD operations
- `api/endpoints/projects/status.py` - Removed import & backward compat shim, updated 8 orchestrator queries

**Breaking changes**:
- Response DTOs now use `agent_id` (UUID str) instead of `job_id` (int) as primary identifier
- Frontend StatusBoard components already expect `agent_id: str` from 0358 migration
- `spawned_by` field now references `agent_id` (not `job_id`)

**Issues encountered**:
- None significant - 0367a service layer migration provided clean foundation
- Some files had local imports inside functions (statistics.py) - all migrated
- backward compat shim in projects/status.py removed (was creating legacy MCPAgentJob objects)

**Notes for next phase**:
- Remaining MCPAgentJob refs in api/endpoints/: orchestration.py (4), templates/crud.py (5)
- orchestration.py is part of 0367c scope (tools/monitoring cleanup)
- templates/crud.py handles template deletion with historical data - may need special consideration
- 0367c can now proceed (no dependencies on 0367b files)

**MCPAgentJob Reference Counts (post-0367b)**:
| Layer | Refs | Phase |
|-------|------|-------|
| Services | **0** ✅ | 0367a DONE |
| API Endpoints (in-scope) | **0** ✅ | 0367b DONE |
| API Endpoints (out-of-scope) | 9 | orchestration.py + templates/crud.py → 0367c/0367d |
| Monitoring | 23 | 0367c |
| Tools | 14 | 0367c |
| Other src/ | 58 | 0367c |

**Verification command**: `grep -rn "MCPAgentJob" api/endpoints/ --include="*.py" | grep -v __pycache__ | wc -l`

---

### Phase 0367c-1 Handover Notes
**Status**: NOT STARTED
**Completed By**: [Agent ID]
**Date**: [Date]
**Duration**: [Hours]

**Scope**: Monitoring + Orchestrator (46 refs across 3 files)
- `agent_health_monitor.py` (23 refs)
- `orchestrator.py` (21 refs)
- `orchestrator_succession.py` (2 refs)

**What was done**:
- [ ] TBD

**Files modified**:
- TBD

**Notes for next phase**:
- TBD

---

### Phase 0367c-2 Handover Notes
**Status**: NOT STARTED
**Completed By**: [Agent ID]
**Date**: [Date]
**Duration**: [Hours]

**Scope**: Tools + Prompt Generation (49 refs across 9 files)
- `staging_rollback.py` (18 refs)
- `thin_prompt_generator.py` (17 refs)
- `tools/*.py` (14 refs across 7 files)

**What was done**:
- [ ] TBD

**Files modified**:
- TBD

**Notes for next phase**:
- TBD

---

### Phase 0367d Handover Notes
**Status**: NOT STARTED
**Completed By**: [Agent ID]
**Date**: [Date]
**Duration**: [Hours]

**What was done**:
- [ ] TBD

**Final MCPAgentJob count**:
- Production: TBD (target: 0)
- Tests: TBD (deferred)

**Verification results**:
- TBD

---

## Success Criteria (Overall)

- [ ] Zero MCPAgentJob references in production code (excluding model definition)
- [ ] All bridge/fallback code removed
- [ ] Full test suite passes
- [ ] Manual staging test works end-to-end
- [ ] Database has records in new tables only
- [ ] No "execution not found" errors

---

## Emergency Rollback

If migration causes production issues:

```bash
# Revert to last working commit
git log --oneline -5  # Find last good commit
git revert <commit>   # Or git reset --hard <commit> if safe

# Restore MCPAgentJob imports if needed
# The model still exists in src/giljo_mcp/models/agents.py
```

---

## Reference Documents

- `handovers/Reference_docs/0358_model_mapping_reference.md` - Complete field mapping
- `handovers/completed/0366a_schema_and_models-C.md` - Schema definitions
- `handovers/completed/0358d_mcpagentjob_deprecation-C.md` - Deprecation approach
- `handovers/0367a_service_layer_cleanup.md` - Phase A details ✅ COMPLETE
- `handovers/0367b_api_endpoint_migration.md` - Phase B details ✅ COMPLETE
- `handovers/0367c-1_monitoring_orchestrator_cleanup.md` - Phase C-1 details (Monitoring + Orchestrator)
- `handovers/0367c-2_tools_prompt_cleanup.md` - Phase C-2 details (Tools + Prompts)
- `handovers/0367d_validation_and_deprecation.md` - Phase D details

---

## Contact / Context

**Project**: GiljoAI MCP Server
**Issue**: Dual-model tech debt from incomplete 0366 migration
**Priority**: HIGH - Blocking staging workflow
**Owner**: Patrik

---

*This document is updated by each agent team after completing their phase.*
