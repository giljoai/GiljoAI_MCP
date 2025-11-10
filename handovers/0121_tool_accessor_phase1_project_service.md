---
**Handover ID:** 0121
**Title:** ToolAccessor Refactoring Phase 1 - Extract ProjectService
**Status:** Planning → Ready for Implementation
**Priority:** HIGH
**Estimated Effort:** 1-2 weeks
**Risk Level:** MEDIUM (affects core infrastructure)
**Created:** 2025-11-10
**Dependencies:** Handover 0120 (Message Queue Consolidation)
**Blocks:** Handover 0123 (ToolAccessor Phase 2)
**Agent Budget:** 200K tokens (main agent + 2-3 sub-agents)
---

# Handover 0121: ToolAccessor Phase 1 - Extract ProjectService

## Executive Summary

**Problem:** ToolAccessor is a **god object** (2,677 lines, 69 methods) handling 10+ business domains. It violates Single Responsibility Principle and is impossible to unit test independently.

**Context:** This is **Phase 1** of breaking down ToolAccessor. We start with **ProjectService** as proof-of-concept for the extraction pattern.

**Solution:** Extract all project-related methods (12 methods, ~350 lines) from ToolAccessor into a focused `ProjectService` class. This establishes the pattern for extracting the remaining 7 services in Phase 2 (Handover 0123).

**Impact:**
- Reduce ToolAccessor from 2,677 → ~2,300 lines
- Create reusable ProjectService (~350 lines)
- Establish service extraction pattern
- Enable independent testing of project logic
- Prove viability for Phase 2 (7 more services)

---

## Table of Contents

1. [Context & Background](#context--background)
2. [Current State Analysis](#current-state-analysis)
3. [ProjectService Design](#projectservice-design)
4. [Implementation Plan](#implementation-plan)
5. [Testing & Validation](#testing--validation)
6. [Success Criteria](#success-criteria)
7. [Risk Mitigation](#risk-mitigation)
8. [Agent Execution Strategy](#agent-execution-strategy)

---

## Context & Background

### The ToolAccessor Problem

**File:** `src/giljo_mcp/tools/tool_accessor.py` (2,677 lines, 69 methods)

**Business Domains Mixed Together:**
1. **Projects** (12 methods) ← **This handover**
2. Agents (8 methods)
3. Messages (7 methods)
4. Tasks (5 methods)
5. Context/Vision (8 methods)
6. Templates (4 methods)
7. Orchestration (10+ methods)
8. Job Management (8 methods)
9. Other (7 methods)

**Why This is a Problem:**
- **Testing:** Can't unit test project logic without mocking 8 other domains
- **Maintainability:** Changes to projects risk breaking agents, messages, etc.
- **Complexity:** 2,677 lines is too much for any developer to hold in their head
- **Coupling:** High coupling between unrelated domains
- **Team Velocity:** Multiple developers can't work on ToolAccessor simultaneously

**Why Projects First:**
- Well-defined domain boundary
- 12 methods with clear responsibilities
- Good size for proof-of-concept (~350 lines)
- Critical for orchestration system
- Success here validates pattern for other services

---

## Current State Analysis

### Project-Related Methods in ToolAccessor

**File:** `src/giljo_mcp/tools/tool_accessor.py`

**12 Project Methods** (~350 lines total):

1. **CRUD Operations:**
   - `create_project(name, description, config)` - Create new project
   - `get_project(project_id)` - Get project by ID
   - `update_project(project_id, updates)` - Update project
   - `delete_project(project_id)` - Delete project
   - `list_projects(tenant_key)` - List all projects for tenant

2. **Lifecycle Management:**
   - `start_project(project_id)` - Start project execution
   - `pause_project(project_id)` - Pause project
   - `resume_project(project_id)` - Resume paused project
   - `complete_project(project_id, outcome)` - Mark project complete

3. **State & Metadata:**
   - `get_project_state(project_id)` - Get current project state
   - `update_project_state(project_id, state)` - Update state
   - `get_project_metrics(project_id)` - Get project metrics (agents, tasks, completion %)

**Dependencies:**
- Database: `AsyncSession` for queries
- Models: `Project`, `MCPAgentJob`, `Task`
- Utils: Validation, error handling

**Consumers:**
- `orchestrator.py` - Uses all project methods
- `api/endpoints/projects.py` - Uses CRUD methods
- `tools/orchestration.py` - Uses lifecycle methods
- MCP tools - `tools/project.py`

---

### Code Sample (Current ToolAccessor)

```python
class ToolAccessor:
    def __init__(self, db: AsyncSession, tenant_key: str):
        self.db = db
        self.tenant_key = tenant_key
        # ... 10+ other domain concerns

    # PROJECT METHODS (to be extracted)
    async def create_project(self, name: str, description: str, config: dict):
        """Create new project"""
        project = Project(
            name=name,
            description=description,
            config=config,
            tenant_key=self.tenant_key,
            status="planning"
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def get_project(self, project_id: str):
        """Get project by ID"""
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.tenant_key == self.tenant_key
            )
        )
        return result.scalar_one_or_none()

    # ... 10 more project methods

    # AGENT METHODS (not extracted in this handover)
    async def spawn_agent(self, agent_type: str, mission: str):
        # ... agent logic

    # MESSAGE METHODS (not extracted in this handover)
    async def send_message(self, job_id: str, content: dict):
        # ... message logic

    # ... 50 more methods from other domains
```

**Problem:** Project logic mixed with agent, message, task, context logic in one giant class.

---

## ProjectService Design

### New Service Architecture

**File:** `src/giljo_mcp/services/project_service.py` (new file, ~350 lines)

**Design Principles:**
1. **Single Responsibility:** Only project domain logic
2. **Dependency Injection:** Accept `AsyncSession` and `tenant_key` in constructor
3. **Async/Await:** All methods async for SQLAlchemy 2.0 compatibility
4. **Error Handling:** Consistent exception handling
5. **Testable:** Can unit test without ToolAccessor

**Class Structure:**
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict
from giljo_mcp.models import Project, MCPAgentJob, Task


class ProjectService:
    """Service for managing projects (CRUD + lifecycle + metrics)"""

    def __init__(self, db: AsyncSession, tenant_key: str):
        self.db = db
        self.tenant_key = tenant_key

    # CRUD Operations
    async def create_project(self, name: str, description: str, config: dict) -> Project:
        """Create new project"""
        pass

    async def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID"""
        pass

    async def update_project(self, project_id: str, updates: dict) -> Project:
        """Update project"""
        pass

    async def delete_project(self, project_id: str) -> bool:
        """Delete project (soft delete)"""
        pass

    async def list_projects(self, filters: Optional[dict] = None) -> List[Project]:
        """List all projects for tenant"""
        pass

    # Lifecycle Management
    async def start_project(self, project_id: str) -> Project:
        """Start project execution"""
        pass

    async def pause_project(self, project_id: str) -> Project:
        """Pause project"""
        pass

    async def resume_project(self, project_id: str) -> Project:
        """Resume paused project"""
        pass

    async def complete_project(self, project_id: str, outcome: dict) -> Project:
        """Mark project complete"""
        pass

    # State & Metrics
    async def get_project_state(self, project_id: str) -> dict:
        """Get current project state"""
        pass

    async def update_project_state(self, project_id: str, state: dict) -> Project:
        """Update project state"""
        pass

    async def get_project_metrics(self, project_id: str) -> dict:
        """Get project metrics (agents, tasks, completion %)"""
        pass
```

---

### ToolAccessor Integration Pattern

**Updated ToolAccessor** (after extraction):

```python
from giljo_mcp.services.project_service import ProjectService

class ToolAccessor:
    def __init__(self, db: AsyncSession, tenant_key: str):
        self.db = db
        self.tenant_key = tenant_key

        # Initialize services
        self._project_service = ProjectService(db, tenant_key)

        # ... other domain concerns remain (agents, messages, tasks, etc.)

    # DELEGATING PROJECT METHODS
    # These now delegate to ProjectService

    async def create_project(self, name: str, description: str, config: dict):
        """Create new project (delegates to ProjectService)"""
        return await self._project_service.create_project(name, description, config)

    async def get_project(self, project_id: str):
        """Get project by ID (delegates to ProjectService)"""
        return await self._project_service.get_project(project_id)

    # ... 10 more delegating methods

    # NON-PROJECT METHODS (remain in ToolAccessor for now)
    async def spawn_agent(self, agent_type: str, mission: str):
        # Still in ToolAccessor (extracted in Phase 2)

    async def send_message(self, job_id: str, content: dict):
        # Still in ToolAccessor (extracted in Phase 2)
```

**Key Pattern:**
1. ToolAccessor creates ProjectService instance in `__init__`
2. All project methods delegate to `_project_service`
3. External consumers continue using ToolAccessor (no API changes!)
4. Gradual migration path: callers can switch to ProjectService directly over time

---

## Implementation Plan

### Phase 1: Create ProjectService (2-3 days)

**Agent:** Implementer (1 agent, ~60K tokens)

**Tasks:**
1. ✅ Create `/src/giljo_mcp/services/` directory
2. ✅ Create `project_service.py` with class skeleton
3. ✅ Copy 12 project methods from ToolAccessor
4. ✅ Adapt methods for standalone service (no ToolAccessor dependencies)
5. ✅ Add docstrings and type hints
6. ✅ Implement error handling
7. ✅ Write unit tests

**Files created:**
- `src/giljo_mcp/services/__init__.py`
- `src/giljo_mcp/services/project_service.py` (~350 lines)
- `tests/services/test_project_service.py` (~400 lines)

**Deliverable:** Standalone ProjectService passing all tests

---

### Phase 2: Integrate into ToolAccessor (1-2 days)

**Agent:** Implementer (1 agent, ~40K tokens)

**Tasks:**
1. ✅ Import ProjectService in ToolAccessor
2. ✅ Initialize `_project_service` in `__init__`
3. ✅ Replace 12 project method bodies with delegation calls
4. ✅ Remove original project code from ToolAccessor
5. ✅ Test ToolAccessor still works correctly

**Files modified:**
- `src/giljo_mcp/tools/tool_accessor.py` (- ~300 lines, + ~50 lines delegation)

**Result:** ToolAccessor now ~2,300 lines (down from 2,677)

---

### Phase 3: Update Direct Consumers (2-3 days)

**Agent:** Implementer (1 agent, ~60K tokens)

**Files to update:**

1. **orchestrator.py**
   - Currently: Uses `tool_accessor.create_project()`
   - Option A: Keep using ToolAccessor (no changes)
   - Option B: Inject ProjectService directly (cleaner but more changes)
   - **Recommendation:** Keep using ToolAccessor for now (gradual migration)

2. **api/endpoints/projects.py**
   - Currently: Uses ToolAccessor for CRUD
   - **Recommendation:** Keep using ToolAccessor (API changes in Handover 0125)

3. **tools/project.py** (MCP tools)
   - Currently: Uses ToolAccessor
   - **Recommendation:** Keep using ToolAccessor

**Decision:** **No consumer updates in Phase 1** - maintain backward compatibility

**Advantage:**
- Lower risk (no API changes)
- Easier to roll back if issues
- Consumers can migrate gradually later

---

### Phase 4: Documentation & Testing (1-2 days)

**Agent:** Documenter + Tester (2 agents, 30K + 50K tokens)

**Tasks:**

1. **Documentation:**
   - Update TECHNICAL_DEBT_ANALYSIS.md (mark ProjectService extraction complete)
   - Create SERVICES_ARCHITECTURE.md (document service layer pattern)
   - Update developer onboarding docs

2. **Testing:**
   - Run full test suite
   - Integration tests for project workflows
   - Re-run EVALUATION_FIRST_TEST (verify no regressions)
   - Performance benchmarks (ensure no slowdown)

3. **Code Review:**
   - Review ProjectService code quality
   - Review ToolAccessor delegation pattern
   - Verify test coverage (>80%)

**Deliverable:** Documented, tested, production-ready ProjectService

---

## Testing & Validation

### Unit Tests (ProjectService)

**Test File:** `tests/services/test_project_service.py`

**Test Coverage:**

1. **CRUD Tests:**
   - [ ] Create project - success
   - [ ] Create project - invalid data (should raise exception)
   - [ ] Get project - exists
   - [ ] Get project - not found
   - [ ] Update project - success
   - [ ] Update project - not found
   - [ ] Delete project - success
   - [ ] List projects - empty
   - [ ] List projects - multiple projects
   - [ ] List projects - filters work correctly

2. **Lifecycle Tests:**
   - [ ] Start project - transitions to "in_progress"
   - [ ] Pause project - transitions to "paused"
   - [ ] Resume project - transitions back to "in_progress"
   - [ ] Complete project - transitions to "completed"
   - [ ] Invalid state transitions raise exceptions

3. **Metrics Tests:**
   - [ ] Get project metrics - calculates correctly
   - [ ] Get project state - returns accurate state
   - [ ] Update project state - persists correctly

**Test Pattern:**
```python
import pytest
from giljo_mcp.services.project_service import ProjectService
from giljo_mcp.models import Project

@pytest.mark.asyncio
async def test_create_project(db_session, tenant_key):
    service = ProjectService(db_session, tenant_key)

    project = await service.create_project(
        name="Test Project",
        description="Test description",
        config={"key": "value"}
    )

    assert project.id is not None
    assert project.name == "Test Project"
    assert project.status == "planning"
    assert project.tenant_key == tenant_key
```

**Target Coverage:** >80% line coverage

---

### Integration Tests (ToolAccessor)

**Test File:** `tests/tools/test_tool_accessor.py` (update existing)

**Test Coverage:**
- [ ] ToolAccessor project methods still work (delegation works)
- [ ] No regressions in existing tests
- [ ] ToolAccessor can still be instantiated
- [ ] ProjectService properly injected

**Example:**
```python
@pytest.mark.asyncio
async def test_tool_accessor_create_project(db_session, tenant_key):
    accessor = ToolAccessor(db_session, tenant_key)

    # Should delegate to ProjectService internally
    project = await accessor.create_project(
        name="Test",
        description="Desc",
        config={}
    )

    assert project.id is not None
```

---

### Regression Tests

**Critical Workflows:**
1. **Project Creation → Orchestration → Completion**
   - Create project via ToolAccessor
   - Start orchestration
   - Spawn agents
   - Complete project
   - Verify all steps work

2. **EVALUATION_FIRST_TEST Replay**
   - Run the successful first test again
   - 3 agents spawn
   - Project progresses correctly
   - All MCP tools work
   - Zero regressions

---

## Success Criteria

### Must Have (P0)

- [ ] **ProjectService created** - Standalone service with 12 methods
- [ ] **ToolAccessor reduced** - Down from 2,677 → ~2,300 lines
- [ ] **All tests pass** - Unit + integration + regression
- [ ] **Zero regressions** - EVALUATION_FIRST_TEST still passes
- [ ] **>80% test coverage** - ProjectService well-tested

### Should Have (P1)

- [ ] **Documentation complete** - SERVICES_ARCHITECTURE.md created
- [ ] **Code review approved** - Senior developer approves pattern
- [ ] **Performance maintained** - No slowdown from delegation

### Nice to Have (P2)

- [ ] **Some consumers migrate** - api/endpoints/projects.py uses ProjectService directly
- [ ] **Monitoring added** - Metrics for ProjectService usage
- [ ] **Error handling improved** - Better exception messages

---

## Risk Mitigation

### Risk #1: Breaking Existing Functionality

**Risk:** Delegation pattern breaks project operations

**Mitigation:**
- Extensive unit tests for ProjectService
- Integration tests for ToolAccessor delegation
- Re-run EVALUATION_FIRST_TEST
- Gradual rollout (no consumer changes in Phase 1)

**Contingency:**
- Revert ToolAccessor changes
- Fix ProjectService bugs
- Re-test before merging

---

### Risk #2: Performance Degradation

**Risk:** Extra indirection (ToolAccessor → ProjectService) slows down operations

**Mitigation:**
- Benchmark before/after
- Delegation is single method call (minimal overhead)
- ProjectService uses same database patterns

**Contingency:**
- Profile slow operations
- Optimize ProjectService if needed
- Consider removing delegation layer (consumers use ProjectService directly)

---

### Risk #3: Pattern Doesn't Scale

**Risk:** Extraction pattern doesn't work for other services (Agent, Message, etc.)

**Mitigation:**
- ProjectService is proof-of-concept
- Validate pattern works before Phase 2
- Document lessons learned
- Adjust pattern if needed

**Contingency:**
- Try different extraction approach for next service
- Keep ProjectService working
- Don't proceed with Phase 2 until pattern proven

---

## Agent Execution Strategy

### Recommended Approach: 2-3 Sequential Agents

**Agent 1: Implementer** (Day 1-3, ~60K tokens)
- Create ProjectService
- Copy & adapt 12 methods
- Write unit tests
- **Deliverable:** Standalone ProjectService

**Agent 2: Integrator** (Day 4-5, ~40K tokens)
- Integrate ProjectService into ToolAccessor
- Add delegation methods
- Test ToolAccessor still works
- **Deliverable:** ToolAccessor using ProjectService

**Agent 3: Tester + Documenter** (Day 6-7, ~80K tokens)
- Write integration tests
- Run regression tests
- Create documentation
- Code review
- **Deliverable:** Tested, documented, production-ready

**Total tokens:** ~180K across 3 agents (within budget)

---

### Parallel Execution Opportunities

**Phases that can run in parallel:**

1. **Agent 1 + Agent 3 (partial):**
   - While Agent 1 writes ProjectService, Agent 3 can prepare test infrastructure
   - Agent 3 can write test skeletons based on method signatures

2. **Agent 2 + Agent 3 (partial):**
   - While Agent 2 integrates, Agent 3 can start documentation

**Sequential dependencies:**
1. ProjectService **MUST** be created before ToolAccessor integration
2. ToolAccessor integration **MUST** complete before regression testing
3. Regression testing **MUST** pass before marking handover complete

---

## Acceptance Criteria

This handover is considered **COMPLETE** when:

1. ✅ **ProjectService exists** - `src/giljo_mcp/services/project_service.py` created
2. ✅ **ToolAccessor delegates** - All 12 project methods delegate to ProjectService
3. ✅ **ToolAccessor reduced** - Down from 2,677 → ~2,300 lines
4. ✅ **Tests pass** - Unit + integration + regression all green
5. ✅ **EVALUATION_FIRST_TEST passes** - Zero regressions
6. ✅ **Documentation complete** - SERVICES_ARCHITECTURE.md created
7. ✅ **Code review approved** - Pattern validated for Phase 2
8. ✅ **Test coverage >80%** - ProjectService well-tested

---

## Post-Completion Actions

1. **Archive handover:**
   ```bash
   mv handovers/0121_tool_accessor_phase1_project_service.md \
      handovers/completed/0121_tool_accessor_phase1_project_service-C.md
   ```

2. **Update CHANGELOG:**
   ```markdown
   ## [v3.0.0-beta] - 2025-11-XX

   ### Refactoring
   - Extracted ProjectService from ToolAccessor (Phase 1 of god object refactoring)
   - Reduced ToolAccessor from 2,677 → 2,300 lines
   - Established service layer architecture pattern
   - 80%+ test coverage on ProjectService
   ```

3. **Update technical debt document:**
   - Mark "ToolAccessor Phase 1" as COMPLETE
   - Prepare for Phase 2 (7 remaining services)

4. **Document lessons learned:**
   - What went well in extraction process
   - What could be improved for Phase 2
   - Pattern adjustments needed

5. **Prepare for Handover 0123:**
   - With ProjectService proven, extract remaining 7 services
   - Can now execute in parallel (7 agents, one per service)

---

## Related Handovers

**Dependencies (must be complete):**
- **Handover 0120:** Message Queue Consolidation (messaging layer clean)

**Enables:**
- **Handover 0123:** ToolAccessor Phase 2 (extract remaining 7 services)
- **Handover 0124:** Agent Endpoint Consolidation (cleaner service layer)
- **Handover 0125:** Projects Endpoint Modularization (can use ProjectService directly)

**Related:**
- **TECHNICAL_DEBT_ANALYSIS.md:** Phase 1 critical refactoring
- **EVALUATION_FIRST_TEST.md:** Regression test baseline

---

## Next Phase Preview: Handover 0123

After ProjectService extraction proves successful, **Handover 0123** will extract the remaining 7 services from ToolAccessor:

1. AgentService (8 methods, ~300 lines)
2. MessageService (7 methods, ~250 lines)
3. TaskService (5 methods, ~200 lines)
4. ContextService (8 methods, ~350 lines)
5. TemplateService (4 methods, ~150 lines)
6. OrchestrationService (10+ methods, ~400 lines)
7. JobService (8 methods, ~300 lines)

**Estimated effort:** 2-3 weeks (can run 7 agents in parallel!)

---

## Summary

**What:** Extract ProjectService from ToolAccessor as proof-of-concept
**Why:** Reduce god object, enable testing, establish service layer pattern
**How:** Create standalone service, delegate from ToolAccessor, maintain backward compatibility
**When:** After Handover 0120, before Handover 0123
**Effort:** 1-2 weeks
**Impact:** -377 lines from ToolAccessor, +350 lines ProjectService, cleaner architecture

**Success Metric:** If this works smoothly, we can confidently proceed with Phase 2 (7 more services in parallel).

---

**Document Version:** 1.0
**Last Updated:** 2025-11-10
**Status:** Ready for Implementation
**Estimated Completion:** 2025-11-24 (1-2 weeks from start)
