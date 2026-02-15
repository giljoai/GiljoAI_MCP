# Handover 0358d: MCPAgentJob Deprecation and Cleanup

**Status**: PENDING
**Date**: 2025-12-20
**Estimate**: 16-24 hours
**Priority**: LOW (after 0366 series completion)
**Dependencies**: 0366a (Schema), 0366b (Services), 0366c (MCP Tools), 0366d (Frontend)

---

## Executive Summary

This handover completes the agent identity refactor by deprecating and eventually removing the legacy MCPAgentJob model. The 0366 series introduced the dual-model architecture (AgentJob + AgentExecution), but the old MCPAgentJob model and mcp_agent_jobs table were preserved for backward compatibility. This handover:

1. Marks MCPAgentJob as deprecated with proper warnings
2. Updates remaining code paths to use new models
3. Migrates test fixtures to use AgentJob/AgentExecution
4. Updates documentation references
5. Provides a timeline for final removal

**Key Metric**: 341 source file occurrences + 1,224 test occurrences across 198 files must be addressed.

---

## Prerequisites

Before starting this handover, verify the following are complete:

### Verification Checklist
- [ ] **0366a Complete**: agent_jobs and agent_executions tables exist in database
- [ ] **0366b Complete**: Service layer uses new models for all new code paths
- [ ] **0366c Complete**: MCP tools use agent_id and job_id semantically
- [ ] **0366d Complete**: Frontend displays agent identity correctly
- [ ] **Migration Applied**: migrations/0366a_split_agent_job.py has been run

### Database Verification
```sql
-- Verify new tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name IN ('agent_jobs', 'agent_executions');

-- Verify old table still exists (for rollback safety)
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'mcp_agent_jobs';

-- Count records in each
SELECT 'mcp_agent_jobs' as table_name, COUNT(*) FROM mcp_agent_jobs
UNION ALL
SELECT 'agent_jobs', COUNT(*) FROM agent_jobs
UNION ALL
SELECT 'agent_executions', COUNT(*) FROM agent_executions;
```

---

## Scope Boundaries

### IN SCOPE
- Mark MCPAgentJob class as deprecated with @deprecated decorator
- Add runtime deprecation warnings when MCPAgentJob is instantiated
- Update test fixtures from MCPAgentJob to AgentJob/AgentExecution
- Update test factories (AgentFactory) to create new model instances
- Update documentation referencing MCPAgentJob
- Create migration plan for final table drop
- Add CI/CD checks for new MCPAgentJob usage

### OUT OF SCOPE
- Dropping mcp_agent_jobs table (deferred to 0358e or v4.0)
- Modifying existing working code unless necessary for deprecation
- Frontend changes (already handled in 0366d)
- API response format changes (maintain backward compatibility)

---

## Remaining MCPAgentJob References (Post-0366)

### Source Files (29 files, 341 occurrences)

#### Core Modules (CRITICAL - Must Update)
| File | Occurrences | Priority | Notes |
|------|-------------|----------|-------|
| src/giljo_mcp/agent_job_manager.py | 20 | HIGH | Central job management |
| src/giljo_mcp/services/project_service.py | 43 | HIGH | Project lifecycle |
| src/giljo_mcp/services/orchestration_service.py | 52 | HIGH | Orchestration core |
| src/giljo_mcp/services/message_service.py | 29 | HIGH | Message routing |
| src/giljo_mcp/tools/tool_accessor.py | 19 | HIGH | MCP tool access |
| src/giljo_mcp/orchestrator.py | 18 | MEDIUM | Orchestrator logic |
| src/giljo_mcp/orchestrator_succession.py | 2 | MEDIUM | Succession handling |
| src/giljo_mcp/thin_prompt_generator.py | 12 | MEDIUM | Prompt generation |

#### Tools (Need Wrapper/Adapter)
| File | Occurrences | Priority |
|------|-------------|----------|
| src/giljo_mcp/tools/orchestration.py | 10 | MEDIUM |
| src/giljo_mcp/tools/agent.py | 35 | MEDIUM |
| src/giljo_mcp/tools/project.py | 1 | LOW |
| src/giljo_mcp/tools/claude_code_integration.py | 4 | LOW |
| src/giljo_mcp/tools/agent_status.py | 1 | LOW |
| src/giljo_mcp/tools/agent_coordination.py | 3 | LOW |

#### Other Modules
| File | Occurrences | Priority |
|------|-------------|----------|
| src/giljo_mcp/monitoring/agent_health_monitor.py | 23 | MEDIUM |
| src/giljo_mcp/job_monitoring.py | 8 | LOW |
| src/giljo_mcp/staging_rollback.py | 18 | LOW |
| src/giljo_mcp/agent_message_queue.py | 8 | LOW |
| src/giljo_mcp/slash_commands/project.py | 7 | LOW |
| src/giljo_mcp/slash_commands/handover.py | 10 | LOW |

#### Models (Keep for Backward Compat)
| File | Occurrences | Notes |
|------|-------------|-------|
| src/giljo_mcp/models/agents.py | 2 | Model definition |
| src/giljo_mcp/models/__init__.py | 5 | Export for backward compat |
| src/giljo_mcp/models/projects.py | 1 | Relationship definition |
| src/giljo_mcp/models/templates.py | 1 | Template relationship |
| src/giljo_mcp/models/tasks.py | 2 | Task linkage |
| src/giljo_mcp/models/agent_identity.py | 2 | Docstring reference only |

### API Endpoints (9 files)
| File | Notes |
|------|-------|
| api/endpoints/agent_jobs/table_view.py | Table view queries |
| api/endpoints/agent_jobs/operations.py | CRUD operations |
| api/endpoints/agent_jobs/filters.py | Filter logic |
| api/endpoints/agent_jobs/succession.py | Succession endpoints |
| api/endpoints/agent_jobs/orchestration.py | Orchestration endpoints |
| api/endpoints/prompts.py | Prompt generation |
| api/endpoints/templates/crud.py | Template CRUD |
| api/endpoints/projects/status.py | Project status |
| api/endpoints/statistics.py | Stats queries |

### Test Files (169 files, 1,224 occurrences)
See detailed breakdown in Test Suite Cleanup section below.

---

## Database Migration Plan

### Current State
The mcp_agent_jobs table is preserved alongside new agent_jobs and agent_executions tables.

### Schema Comparison

| mcp_agent_jobs (34 columns) | agent_jobs (10) | agent_executions (28) |
|----------------------------|-----------------|----------------------|
| id (INTEGER, PK) | - | - |
| job_id (STRING, UK) | job_id (STRING, PK) | agent_id (STRING, PK) |
| tenant_key | tenant_key | tenant_key |
| project_id | project_id | - |
| agent_type | job_type | agent_type |
| mission | mission | - |
| status | status | status |
| ... | job_metadata | ... (28 total) |

### Foreign Key Dependencies

```sql
-- Current FK from tasks table
ALTER TABLE tasks 
  DROP CONSTRAINT fk_tasks_agent_job;

-- OR update to point to new table
ALTER TABLE tasks 
  ADD CONSTRAINT fk_tasks_agent_job 
  FOREIGN KEY (agent_job_id) 
  REFERENCES agent_jobs(job_id);
```

### Data Preservation
The 0366a migration already copied data to new tables. No data loss occurred.

### Recommended Approach

**Phase 1 (This Handover)**: Soft Deprecation
- Keep mcp_agent_jobs table
- Add deprecation warnings
- New code uses new models
- Old code paths still work

**Phase 2 (0358e - Future)**: Table Retirement
- Verify no production reads from mcp_agent_jobs
- Update tasks FK to point to agent_jobs
- Archive mcp_agent_jobs data
- Drop mcp_agent_jobs table

### Historical Data
- Data was migrated during 0366a
- job_id in mcp_agent_jobs maps to job_id in agent_jobs
- job_id in mcp_agent_jobs maps to agent_id in agent_executions (1:1 for existing data)

---

## Deprecation Steps

### Step 1: Mark Model as Deprecated (2 hours)

```python
# src/giljo_mcp/models/agents.py

import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class MCPAgentJob(Base):
    """
    MCP Agent Job model - tracks agent jobs separately from user tasks.

    .. deprecated:: 3.3.0
        Use :class:`AgentJob` and :class:`AgentExecution` instead.
        See Handover 0366a for migration guide.
        Will be removed in v4.0.
    """

    __tablename__ = "mcp_agent_jobs"
    
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "MCPAgentJob is deprecated. Use AgentJob and AgentExecution instead. "
            "See Handover 0366a for migration guide. Will be removed in v4.0.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(*args, **kwargs)
    
    # ... rest of class unchanged
```

### Step 2: Add Import Warning (1 hour)

```python
# src/giljo_mcp/models/__init__.py

import warnings

# At module level, add deprecation note
_DEPRECATED_MODELS = {"MCPAgentJob"}

def __getattr__(name):
    if name in _DEPRECATED_MODELS:
        warnings.warn(
            f"{name} is deprecated. Use AgentJob and AgentExecution instead. "
            "Will be removed in v4.0.",
            DeprecationWarning,
            stacklevel=2
        )
    return globals()[name]
```

### Step 3: Update Model Docstrings (1 hour)

Add clear deprecation notices to:
- MCPAgentJob class docstring
- MCPAgentJob column comments
- models/__init__.py import guidance

### Step 4: Add Ruff/Lint Rule (2 hours)

Create custom ruff rule or pre-commit hook to flag new MCPAgentJob usage:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: no-deprecated-models
        name: Check for deprecated model usage
        entry: python scripts/check_deprecated_models.py
        language: python
        files: \.py$
        exclude: ^(tests/|migrations/|handovers/)
```

---

## Test Suite Cleanup

### Test Fixtures to Update

#### Priority 1: Base Fixtures
```python
# tests/fixtures/base_fixtures.py

# BEFORE
from src.giljo_mcp.models import MCPAgentJob

# AFTER
from src.giljo_mcp.models import AgentJob, AgentExecution

# Update TestData.generate_agent_job_data()
@staticmethod
def generate_agent_job_data(project_id: str, tenant_key: str, agent_type: Optional[str] = None) -> tuple[dict, dict]:
    """Generate test AgentJob and AgentExecution data"""
    job_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())
    
    job_data = {
        "job_id": job_id,
        "tenant_key": tenant_key,
        "project_id": project_id,
        "job_type": agent_type or "worker",
        "mission": f"Test mission for {agent_type or 'worker'} agent",
        "status": "active",
        "created_at": datetime.now(timezone.utc),
    }
    
    execution_data = {
        "agent_id": agent_id,
        "job_id": job_id,
        "tenant_key": tenant_key,
        "agent_type": agent_type or "worker",
        "status": "waiting",
        "instance_number": 1,
    }
    
    return job_data, execution_data
```

#### Priority 2: Test Factories
```python
# tests/helpers/test_factories.py

class AgentFactory:
    """Factory for creating AgentJob and AgentExecution instances."""

    @staticmethod
    def build_job(project_id: str, tenant_key: str, **kwargs) -> AgentJob:
        """Build an AgentJob instance"""
        defaults = {
            "job_id": str(uuid.uuid4()),
            "tenant_key": tenant_key,
            "project_id": project_id,
            "job_type": "worker",
            "mission": "Test mission",
            "status": "active",
        }
        defaults.update(kwargs)
        return AgentJob(**defaults)

    @staticmethod
    def build_execution(job: AgentJob, **kwargs) -> AgentExecution:
        """Build an AgentExecution instance linked to a job"""
        defaults = {
            "agent_id": str(uuid.uuid4()),
            "job_id": job.job_id,
            "tenant_key": job.tenant_key,
            "agent_type": job.job_type,
            "status": "waiting",
            "instance_number": 1,
        }
        defaults.update(kwargs)
        return AgentExecution(**defaults)
    
    @staticmethod
    def build(project_id: str, tenant_key: str, **kwargs) -> tuple[AgentJob, AgentExecution]:
        """Build both job and execution (convenience method)"""
        job = AgentFactory.build_job(project_id, tenant_key, **kwargs)
        execution = AgentFactory.build_execution(job)
        return job, execution
```

### Test Files by Category

#### High Priority (Core Functionality)
| File | MCPAgentJob Count | Action |
|------|-------------------|--------|
| tests/unit/test_orchestration_service.py | 11 | Migrate to new models |
| tests/unit/test_staging_rollback.py | 43 | Migrate to new models |
| tests/thin_prompt/test_orchestrator_reuse.py | 33 | Migrate to new models |
| tests/integration/test_succession_multi_tenant.py | 32 | Migrate to new models |
| tests/test_orchestrator_succession.py | 39 | Migrate to new models |

#### Medium Priority (Integration Tests)
| File | MCPAgentJob Count | Action |
|------|-------------------|--------|
| tests/integration/test_orchestrator_instruction_compilation.py | 27 | Migrate |
| tests/integration/test_e2e_project_lifecycle.py | 23 | Migrate |
| tests/integration/test_orchestrator_status_filtering.py | 22 | Migrate |
| tests/security/test_succession_security.py | 22 | Migrate |
| tests/performance/test_succession_performance.py | 21 | Migrate |

#### Low Priority (Can Remain During Deprecation Period)
- Tests that only use MCPAgentJob for backward compatibility assertions
- Tests explicitly verifying deprecation warnings work
- Performance benchmark comparisons between old and new models

---

## Documentation Updates

### Files to Update (31 docs reference MCPAgentJob)

#### Architecture Docs (Priority 1)
| File | Action |
|------|--------|
| docs/SERVER_ARCHITECTURE_TECH_STACK.md | Update model references |
| docs/SERVICES.md | Update service layer docs |
| docs/ORCHESTRATOR.md | Update orchestrator docs |
| docs/architecture/ADR-0108-unified-agent-state-architecture.md | Mark as superseded by 0366 |

#### Developer Guides (Priority 2)
| File | Action |
|------|--------|
| docs/developer_guides/orchestrator_succession_developer_guide.md | Update examples |
| docs/developer_guides/agent_monitoring_developer_guide.md | Update examples |
| docs/guides/thin_client_migration_guide.md | Update examples |
| docs/guides/staging_rollback_integration_guide.md | Update examples |

#### Component Docs (Priority 3)
| File | Action |
|------|--------|
| docs/components/STAGING_WORKFLOW.md | Update workflow docs |
| docs/architecture/messaging_contract.md | Update contract |
| docs/testing/ORCHESTRATOR_SIMULATOR.md | Update test docs |

### Documentation Pattern

Add migration note block to relevant documentation:

```markdown
## Agent Models

> **Migration Note (Handover 0366a)**
> 
> The MCPAgentJob model is **deprecated** as of v3.3.0.
> Use AgentJob (work order) and AgentExecution (executor instance) instead.
> 
> **Key Changes:**
> - job_id = The work to be done (persists across succession)
> - agent_id = The executor doing the work (changes on succession)
> 
> See Agent Identity Refactor (handovers/completed/0366_agent_identity_refactor_roadmap-C.md) for details.
```

---

## Rollback Strategy

### If Deprecation Causes Issues

**Immediate Rollback (< 1 hour)**:
1. Revert deprecation warning additions
2. Keep MCPAgentJob fully functional
3. Document issues encountered

**Partial Rollback (2-4 hours)**:
1. Remove __getattr__ import warning (too aggressive)
2. Keep class-level deprecation docstring
3. Maintain new code using new models

### If Table Drop is Needed Before v4.0

**Emergency Preservation**:
```sql
-- Archive old data
CREATE TABLE mcp_agent_jobs_archive AS SELECT * FROM mcp_agent_jobs;

-- Add metadata
ALTER TABLE mcp_agent_jobs_archive ADD COLUMN archived_at TIMESTAMP DEFAULT NOW();
COMMENT ON TABLE mcp_agent_jobs_archive IS 'Archived MCPAgentJob data from pre-0366 era';
```

### Re-enabling MCPAgentJob

If we need to un-deprecate:
1. Remove deprecation warnings from __init__
2. Remove __getattr__ hook
3. Update docstrings to remove deprecation notice
4. Re-enable any disabled tests

---

## Success Criteria

### Phase 1: Soft Deprecation (This Handover)

- [ ] MCPAgentJob has deprecation warning in __init__
- [ ] MCPAgentJob has deprecation notice in docstring
- [ ] Import warning fires on from models import MCPAgentJob
- [ ] Pre-commit hook flags new MCPAgentJob usage in src/
- [ ] All new code uses AgentJob/AgentExecution
- [ ] 5+ documentation files updated with migration note
- [ ] Test fixtures remain functional (no breaking changes)

### Phase 2: Test Migration (Future - 0358e)

- [ ] All test fixtures use new models
- [ ] Test factories create AgentJob/AgentExecution
- [ ] No MCPAgentJob usage in new tests
- [ ] Deprecation warning tests added

### Phase 3: Final Removal (v4.0)

- [ ] MCPAgentJob class removed from models
- [ ] mcp_agent_jobs table dropped (with archive)
- [ ] tasks FK updated to agent_jobs
- [ ] All documentation references removed
- [ ] Zero MCPAgentJob occurrences in codebase

---

## Commit Message Template

```
deprecate(0358d): mark MCPAgentJob as deprecated in favor of AgentJob/AgentExecution

- Add DeprecationWarning to MCPAgentJob.__init__()
- Add deprecation notice to MCPAgentJob docstring
- Add import-time deprecation warning via __getattr__
- Add pre-commit hook to flag new MCPAgentJob usage
- Update 5 architecture docs with migration notes
- Document timeline for final removal in v4.0

Part of Agent Identity Refactor (0366 series)
See: handovers/completed/0366_agent_identity_refactor_roadmap-C.md


```

---

## Research Findings Summary

### Codebase Analysis (2025-12-20)

**Source Files**:
- 29 files with 341 occurrences
- Heavy usage in: agent_job_manager (20), project_service (43), orchestration_service (52), message_service (29)
- Tool files have moderate usage (10-35 occurrences each)

**Test Files**:
- 169 files with 1,224 occurrences
- Core test areas: unit tests (100+), integration tests (300+), fixtures (50+)

**Documentation**:
- 31 docs reference MCPAgentJob
- 24 docs reference mcp_agent_jobs table
- CLAUDE.md has no MCPAgentJob references (good)

**Database**:
- mcp_agent_jobs table preserved during 0366a migration
- Foreign key from tasks.agent_job_id to mcp_agent_jobs.job_id
- Data duplicated to new tables (no data loss)

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing code | LOW | HIGH | Keep model functional, only add warnings |
| Test failures | MEDIUM | MEDIUM | Migrate fixtures carefully, one at a time |
| Documentation drift | MEDIUM | LOW | Batch update docs with migration note |
| Developer confusion | MEDIUM | MEDIUM | Clear deprecation messages, migration guide |

---

## Related Handovers

- **0366**: Agent Identity Refactor Master Roadmap (completed)
- **0366a**: Schema and Models - Split MCPAgentJob into AgentJob + AgentExecution
- **0366b**: Service Layer Updates - Services use new dual-model architecture
- **0366c**: MCP Tool Standardization - Tools use job_id and agent_id semantically
- **0366d**: Frontend Integration - UI displays agent identity correctly
- **0358**: WebSocket and UI State Overhaul (separate track)

---

## Appendix: File Reference Index

### Source Files with MCPAgentJob (29 files)

```
src/giljo_mcp/agent_job_manager.py (20)
src/giljo_mcp/agent_message_queue.py (8)
src/giljo_mcp/job_monitoring.py (8)
src/giljo_mcp/models/__init__.py (5)
src/giljo_mcp/models/agent_identity.py (2)
src/giljo_mcp/models/agents.py (2)
src/giljo_mcp/models/projects.py (1)
src/giljo_mcp/models/tasks.py (2)
src/giljo_mcp/models/templates.py (1)
src/giljo_mcp/monitoring/agent_health_monitor.py (23)
src/giljo_mcp/orchestrator.py (18)
src/giljo_mcp/orchestrator_succession.py (2)
src/giljo_mcp/services/message_service.py (29)
src/giljo_mcp/services/orchestration_service.py (52)
src/giljo_mcp/services/project_service.py (43)
src/giljo_mcp/slash_commands/handover.py (10)
src/giljo_mcp/slash_commands/project.py (7)
src/giljo_mcp/staging_rollback.py (18)
src/giljo_mcp/templates/generic_agent_template.py (2)
src/giljo_mcp/thin_prompt_generator.py (12)
src/giljo_mcp/tools/__init__.py (2)
src/giljo_mcp/tools/agent.py (35)
src/giljo_mcp/tools/agent_coordination.py (3)
src/giljo_mcp/tools/agent_status.py (1)
src/giljo_mcp/tools/claude_code_integration.py (4)
src/giljo_mcp/tools/optimization.py (1)
src/giljo_mcp/tools/orchestration.py (10)
src/giljo_mcp/tools/project.py (1)
src/giljo_mcp/tools/tool_accessor.py (19)
```

---

**Prepared by**: Deep Researcher Agent
**Date**: 2025-12-20
**Research Time**: ~45 minutes
**Review Required**: System Architect, Database Expert, TDD Implementor
