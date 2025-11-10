---
**Handover ID:** 0123
**Title:** ToolAccessor Phase 2 - Extract Remaining 7 Services
**Status:** Ready for Implementation
**Priority:** CRITICAL
**Estimated Effort:** 2-3 weeks
**Risk Level:** MEDIUM (affects core infrastructure)
**Created:** 2025-11-10
**Dependencies:** Handover 0121 (ProjectService extraction - COMPLETE ✅)
**Blocks:** Handovers 0124, 0125, 0126 (all depend on service layer)
**Agent Budget:** 200K tokens × 7 agents (parallel execution)
---

# Handover 0123: ToolAccessor Phase 2 - Extract Remaining Services

## Executive Summary

**Problem:** ToolAccessor is still a **god object** (2,324 lines, 59 methods) handling 7+ business domains after Phase 1. It remains difficult to test, maintain, and extend.

**Context:** **Phase 1 (Handover 0121) successfully extracted ProjectService** and established the service layer pattern. We reduced ToolAccessor by 353 lines and created a 719-line focused service with >80% test coverage.

**Solution:** Extract the remaining **7 services** from ToolAccessor using the proven delegation pattern from Phase 1. Execute extractions in parallel using 7 specialized agents.

**Impact:**
- Remove ~1,950 more lines from ToolAccessor (reducing it to ~370 lines, an 86% reduction from original)
- Create 7 focused, testable services
- Complete the god object refactoring
- Enable handovers 0124, 0125, 0126 to proceed
- Establish production-ready service layer architecture

---

## Table of Contents

1. [Context & Background](#context--background)
2. [Current State Analysis](#current-state-analysis)
3. [Service Extraction Plan](#service-extraction-plan)
4. [Implementation Strategy](#implementation-strategy)
5. [Testing & Validation](#testing--validation)
6. [Success Criteria](#success-criteria)
7. [Agent Execution Strategy](#agent-execution-strategy)

---

## Context & Background

### Phase 1 Success Metrics

**Handover 0121 Results:**
- ✅ ToolAccessor: 2,677 → 2,324 lines (-353 lines, -13.2%)
- ✅ ProjectService: 719 lines, 10 methods
- ✅ Tests: 21+ unit tests, >80% coverage
- ✅ Pattern: Delegation works perfectly
- ✅ Documentation: SERVICES_ARCHITECTURE.md created
- ✅ Compatibility: 100% backward compatible

**Key Learnings:**
1. Delegation pattern works flawlessly
2. Service extraction doesn't break existing code
3. Unit testing is much easier with isolated services
4. Documentation is critical for pattern adoption
5. Parallel execution is feasible for independent services

### Why Phase 2 Now?

1. **Pattern Proven:** Phase 1 demonstrated the extraction works
2. **Unblocks Future Work:** 0124, 0125, 0126 need service layer
3. **High ROI:** Remove 1,950 more lines in one effort
4. **Team Velocity:** Services enable parallel development
5. **Code Quality:** Better testability, maintainability, reusability

---

## Current State Analysis

### ToolAccessor After Phase 1

**File:** `src/giljo_mcp/tools/tool_accessor.py`
**Current Size:** 2,324 lines, 59 methods

**Remaining Business Domains:**

1. **Agents** (8 methods, ~300 lines) ← AgentService
2. **Messages** (7 methods, ~250 lines) ← MessageService
3. **Tasks** (5 methods, ~200 lines) ← TaskService
4. **Context/Vision** (8 methods, ~350 lines) ← ContextService
5. **Templates** (4 methods, ~150 lines) ← TemplateService
6. **Orchestration** (10+ methods, ~400 lines) ← OrchestrationService
7. **Jobs** (8 methods, ~300 lines) ← JobService

**Total Extractable:** ~1,950 lines

**What Remains After Extraction:**
- Initialization logic (~50 lines)
- Service initialization (~100 lines)
- Delegating methods (~220 lines, one-liners to services)

**Target ToolAccessor Size:** ~370 lines (86% reduction from original 2,677 lines!)

---

## Service Extraction Plan

### Service 1: AgentService

**File:** `src/giljo_mcp/services/agent_service.py`
**Estimated Size:** ~300 lines
**Methods to Extract:** 8

#### Methods

1. `spawn_agent_job(agent_type, agent_name, mission, project_id, tenant_key)`
2. `get_agent_job(job_id)`
3. `update_agent_status(job_id, status)`
4. `decommission_agent(agent_name, project_id, reason)`
5. `list_agent_jobs(project_id, status)`
6. `get_agent_metrics(project_id)`
7. `assign_agent_task(job_id, task_id)`
8. `get_agent_conversation_history(job_id)`

#### Dependencies

- Database: `MCPAgentJob` model
- Services: None (independent)
- External: AgentJobManager, JobCoordinator

#### Responsibilities

- Agent job CRUD operations
- Agent lifecycle management
- Status tracking
- Metrics and reporting

---

### Service 2: MessageService

**File:** `src/giljo_mcp/services/message_service.py`
**Estimated Size:** ~250 lines
**Methods to Extract:** 7

#### Methods

1. `send_message(job_id, content, priority)`
2. `get_messages(agent_name, project_id, status)`
3. `acknowledge_message(message_id)`
4. `broadcast_message(content, project_id, priority)`
5. `get_pending_messages(agent_name)`
6. `mark_message_delivered(message_id)`
7. `get_message_history(project_id)`

#### Dependencies

- Database: `Message` model
- Services: None (independent)
- External: AgentCommunicationQueue (from 0120)

#### Responsibilities

- Message CRUD operations
- Message delivery and acknowledgment
- Priority handling
- Message queue integration

---

### Service 3: TaskService

**File:** `src/giljo_mcp/services/task_service.py`
**Estimated Size:** ~200 lines
**Methods to Extract:** 5

#### Methods

1. `create_task(name, description, project_id, agent_id)`
2. `get_task(task_id)`
3. `update_task_status(task_id, status, outcome)`
4. `assign_task_to_agent(task_id, agent_id)`
5. `list_tasks(project_id, status)`

#### Dependencies

- Database: `Task` model
- Services: AgentService (for task assignment)
- External: None

#### Responsibilities

- Task CRUD operations
- Task-agent assignment
- Task status tracking
- Task completion handling

---

### Service 4: ContextService

**File:** `src/giljo_mcp/services/context_service.py`
**Estimated Size:** ~350 lines
**Methods to Extract:** 8

#### Methods

1. `add_context_document(project_id, document_type, content)`
2. `get_context_summary(project_id)`
3. `update_context_usage(project_id, tokens_used)`
4. `get_context_budget(project_id)`
5. `chunk_vision_document(project_id, file_path)`
6. `get_vision_chunks(project_id)`
7. `prioritize_context(project_id, prioritization_strategy)`
8. `get_context_metrics(project_id)`

#### Dependencies

- Database: `VisionDocument`, `VisionChunk` models
- Services: ProjectService (for budget checks)
- External: VisionDocumentRepository, ChunkingSystem

#### Responsibilities

- Context document management
- Vision document chunking
- Context budget tracking
- Context prioritization

---

### Service 5: TemplateService

**File:** `src/giljo_mcp/services/template_service.py`
**Estimated Size:** ~150 lines
**Methods to Extract:** 4

#### Methods

1. `create_template(name, template_type, content)`
2. `get_template(template_id)`
3. `list_templates(template_type, tenant_key)`
4. `render_template(template_id, variables)`

#### Dependencies

- Database: `AgentTemplate` model
- Services: None (independent)
- External: TemplateManager

#### Responsibilities

- Template CRUD operations
- Template rendering
- Template caching
- Template validation

---

### Service 6: OrchestrationService

**File:** `src/giljo_mcp/services/orchestration_service.py`
**Estimated Size:** ~400 lines
**Methods to Extract:** 10+

#### Methods

1. `orchestrate_project(project_id, tenant_key)`
2. `analyze_mission(mission_text)`
3. `spawn_project_agents(project_id, mission_breakdown)`
4. `get_workflow_status(project_id)`
5. `advance_workflow(project_id, event)`
6. `handle_agent_completion(job_id)`
7. `check_project_completion(project_id)`
8. `coordinate_agents(project_id)`
9. `handle_orchestration_error(project_id, error)`
10. `get_orchestration_metrics(project_id)`

#### Dependencies

- Database: Multiple models (Project, MCPAgentJob, Message, Task)
- Services: ProjectService, AgentService, MessageService, TaskService
- External: ProjectOrchestrator, MissionPlanner, WorkflowEngine

#### Responsibilities

- Project orchestration workflow
- Mission analysis and decomposition
- Agent spawning and coordination
- Workflow state management
- Completion detection

---

### Service 7: JobService

**File:** `src/giljo_mcp/services/job_service.py`
**Estimated Size:** ~300 lines
**Methods to Extract:** 8

#### Methods

1. `create_job(job_type, parameters, project_id)`
2. `get_job(job_id)`
3. `update_job_progress(job_id, progress, status)`
4. `cancel_job(job_id, reason)`
5. `list_jobs(project_id, job_type, status)`
6. `get_job_metrics(project_id)`
7. `cleanup_completed_jobs(project_id)`
8. `retry_failed_job(job_id)`

#### Dependencies

- Database: `MCPAgentJob` model
- Services: AgentService (overlaps, may need consolidation)
- External: AgentJobManager, JobCoordinator

#### Responsibilities

- Generic job management
- Job progress tracking
- Job cleanup
- Retry logic

---

## Implementation Strategy

### Execution Model: 7 Parallel Agents

Each service extraction is **independent** and can be executed in parallel:

**Agent 1:** Extract AgentService (Day 1-3, ~28K tokens)
**Agent 2:** Extract MessageService (Day 1-3, ~28K tokens)
**Agent 3:** Extract TaskService (Day 1-3, ~28K tokens)
**Agent 4:** Extract ContextService (Day 1-3, ~28K tokens)
**Agent 5:** Extract TemplateService (Day 1-3, ~28K tokens)
**Agent 6:** Extract OrchestrationService (Day 1-3, ~28K tokens)
**Agent 7:** Extract JobService (Day 1-3, ~28K tokens)

**Total Duration:** 2-3 weeks (parallel execution)
**Total Token Budget:** ~200K tokens (7 agents × ~28K each)

---

### Per-Service Implementation Template

Each agent follows the same pattern from Phase 1:

#### Step 1: Create Service (0.5 day)

1. Create `src/giljo_mcp/services/{service_name}_service.py`
2. Copy methods from ToolAccessor
3. Adapt for standalone service (no ToolAccessor dependencies)
4. Add comprehensive docstrings and type hints
5. Implement error handling
6. Add logging

#### Step 2: Write Unit Tests (1 day)

1. Create `tests/unit/test_{service_name}_service.py`
2. Test all methods (CRUD, lifecycle, edge cases)
3. Mock database and dependencies
4. Achieve >80% code coverage
5. Validate syntax

#### Step 3: Integrate with ToolAccessor (0.5 day)

1. Import service in ToolAccessor
2. Initialize service in `__init__`
3. Replace method bodies with delegation
4. Maintain backward compatibility
5. Update `__init__.py` exports

#### Step 4: Validate (0.5 day)

1. Run unit tests
2. Check syntax
3. Verify backward compatibility
4. Document in completion summary

---

### Service Integration Pattern

**From Phase 1 (ProjectService):**

```python
# src/giljo_mcp/tools/tool_accessor.py

class ToolAccessor:
    def __init__(self, db_manager, tenant_manager):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager

        # Initialize all services
        self._project_service = ProjectService(db_manager, tenant_manager)
        self._agent_service = AgentService(db_manager, tenant_manager)
        self._message_service = MessageService(db_manager, tenant_manager)
        self._task_service = TaskService(db_manager, tenant_manager)
        self._context_service = ContextService(db_manager, tenant_manager)
        self._template_service = TemplateService(db_manager, tenant_manager)
        self._orchestration_service = OrchestrationService(db_manager, tenant_manager)
        self._job_service = JobService(db_manager, tenant_manager)

    # Delegating methods (one-liners)
    async def spawn_agent_job(self, *args, **kwargs):
        return await self._agent_service.spawn_agent_job(*args, **kwargs)

    async def send_message(self, *args, **kwargs):
        return await self._message_service.send_message(*args, **kwargs)

    # ... etc for all methods
```

---

## Testing & Validation

### Unit Tests Per Service

Each service gets comprehensive unit tests (pattern from Phase 1):

**Test Classes:**
1. `Test{Service}CRUD` - Create, Read, Update, Delete operations
2. `Test{Service}Lifecycle` - Lifecycle management methods
3. `Test{Service}Integration` - Integration with other services
4. `Test{Service}EdgeCases` - Error handling, edge cases

**Coverage Target:** >80% line coverage per service

**Example (AgentService):**
```python
# tests/unit/test_agent_service.py

class TestAgentServiceCRUD:
    @pytest.mark.asyncio
    async def test_spawn_agent_job_success(self):
        # Test successful agent job creation
        ...

    @pytest.mark.asyncio
    async def test_get_agent_job_not_found(self):
        # Test error handling
        ...

class TestAgentServiceLifecycle:
    @pytest.mark.asyncio
    async def test_decommission_agent_success(self):
        # Test agent decommissioning
        ...
```

---

### Integration Testing

**After all services extracted:**

1. **ToolAccessor Integration Tests**
   - Verify delegation works
   - All methods still accessible
   - Return values unchanged

2. **Service Interaction Tests**
   - OrchestrationService uses ProjectService, AgentService, etc.
   - TaskService interacts with AgentService
   - No circular dependencies

3. **Regression Tests**
   - Run EVALUATION_FIRST_TEST
   - All existing tests pass
   - No breaking changes

---

### Validation Checklist

- [ ] **7 services created** - All in `src/giljo_mcp/services/`
- [ ] **7 test files created** - All in `tests/unit/`
- [ ] **ToolAccessor reduced** - From 2,324 → ~370 lines
- [ ] **All syntax valid** - No compilation errors
- [ ] **>80% test coverage** - Per service
- [ ] **Backward compatible** - All existing APIs work
- [ ] **Documentation updated** - SERVICES_ARCHITECTURE.md
- [ ] **Services exported** - In `__init__.py`

---

## Success Criteria

### Must Have (P0)

- [ ] **All 7 services extracted** - AgentService, MessageService, TaskService, ContextService, TemplateService, OrchestrationService, JobService
- [ ] **ToolAccessor reduced to ~370 lines** - 86% reduction from original 2,677 lines
- [ ] **>80% test coverage** - Each service independently tested
- [ ] **Zero regressions** - EVALUATION_FIRST_TEST passes
- [ ] **Documentation complete** - SERVICES_ARCHITECTURE.md updated

### Should Have (P1)

- [ ] **Service interaction patterns documented** - How services call each other
- [ ] **Performance benchmarks** - Before/after comparison
- [ ] **Migration guide updated** - How to use services directly
- [ ] **Code review approved** - Senior developer sign-off

### Nice to Have (P2)

- [ ] **Some API endpoints migrated** - Using services directly
- [ ] **Service composition examples** - Best practices
- [ ] **Monitoring added** - Metrics for service usage

---

## Agent Execution Strategy

### Recommended Approach: 7 Parallel Agents

**Rationale:**
- Each service extraction is independent
- No dependencies between services (at extraction time)
- Proven pattern from Phase 1
- Maximum efficiency

**Agent Assignment:**

| Agent | Service | Lines | Methods | Complexity | Tokens |
|-------|---------|-------|---------|------------|--------|
| 1 | AgentService | ~300 | 8 | Medium | ~28K |
| 2 | MessageService | ~250 | 7 | Low | ~28K |
| 3 | TaskService | ~200 | 5 | Low | ~28K |
| 4 | ContextService | ~350 | 8 | High | ~28K |
| 5 | TemplateService | ~150 | 4 | Low | ~28K |
| 6 | OrchestrationService | ~400 | 10+ | High | ~28K |
| 7 | JobService | ~300 | 8 | Medium | ~28K |

**Total:** ~196K tokens (within 200K budget per agent)

---

### Execution Timeline

**Week 1: Service Extraction**
- Day 1: Agents 1-7 start in parallel
- Day 2: Services created, tests written
- Day 3: Integration with ToolAccessor
- Day 4: Validation and syntax checks
- Day 5: Buffer for issues

**Week 2: Integration & Testing**
- Day 1-2: Service interaction testing
- Day 3: Regression testing
- Day 4: Documentation updates
- Day 5: Code review and polish

**Week 3: Finalization (if needed)**
- Day 1-2: Address review feedback
- Day 3: Final validation
- Day 4: Merge preparation
- Day 5: Handover completion

---

### Dependencies Between Services

**Low Dependency:**
- MessageService (independent)
- TemplateService (independent)
- TaskService (independent)

**Medium Dependency:**
- AgentService (may need JobService)
- JobService (may need AgentService)
- ContextService (needs ProjectService from Phase 1)

**High Dependency:**
- OrchestrationService (needs ProjectService, AgentService, MessageService, TaskService)

**Strategy:**
- Extract low-dependency services first (Day 1-2)
- Extract medium-dependency services next (Day 2-3)
- Extract OrchestrationService last (Day 3-4) after dependencies exist

---

## Risk Mitigation

### Risk #1: Service Interaction Complexity

**Risk:** OrchestrationService depends on other services not yet extracted

**Mitigation:**
- Extract in order: MessageService, TaskService, AgentService, then OrchestrationService
- Use ToolAccessor temporarily if needed
- Refactor interactions after all services exist

**Contingency:**
- OrchestrationService can delegate to ToolAccessor for other domains initially
- Refactor to use services in Week 2

---

### Risk #2: Circular Dependencies

**Risk:** Services depend on each other circularly (e.g., AgentService ↔ JobService)

**Mitigation:**
- Analyze dependencies before extraction
- Use interfaces if needed
- Pass services as parameters, not in constructor
- Document dependencies in SERVICES_ARCHITECTURE.md

**Contingency:**
- Merge circular services (e.g., AgentService + JobService = one service)
- Use event-driven communication
- Introduce service mediator pattern

---

### Risk #3: Breaking Changes

**Risk:** Extraction breaks existing functionality

**Mitigation:**
- Maintain 100% backward compatibility
- ToolAccessor continues to expose same API
- Extensive regression testing
- Run EVALUATION_FIRST_TEST continuously

**Contingency:**
- Revert individual service extraction
- Fix service implementation
- Re-test before proceeding

---

### Risk #4: Test Coverage Gaps

**Risk:** Services aren't adequately tested

**Mitigation:**
- Require >80% coverage per service
- Copy test patterns from Phase 1 (ProjectService)
- Mock all dependencies
- Test edge cases and error handling

**Contingency:**
- Add missing tests in Week 2
- Use mutation testing to find gaps
- Peer review test coverage

---

## Acceptance Criteria

This handover is considered **COMPLETE** when:

1. ✅ **7 services created** - All in `src/giljo_mcp/services/`
2. ✅ **ToolAccessor reduced** - From 2,324 → ~370 lines (86% reduction total)
3. ✅ **Tests comprehensive** - >80% coverage per service, 50+ total tests
4. ✅ **Backward compatible** - All existing APIs work unchanged
5. ✅ **EVALUATION_FIRST_TEST passes** - Zero regressions
6. ✅ **Documentation updated** - SERVICES_ARCHITECTURE.md reflects all services
7. ✅ **Code review approved** - Team validates implementation
8. ✅ **Services exported** - All in `__init__.py` for easy import

---

## Post-Completion Actions

1. **Archive handover:**
   ```bash
   mv handovers/0123_tool_accessor_phase2_extract_services.md \
      handovers/completed/0123_tool_accessor_phase2_extract_services-COMPLETE.md
   ```

2. **Update CHANGELOG:**
   ```markdown
   ## [v3.0.0-beta] - 2025-11-XX

   ### Refactoring
   - Completed ToolAccessor god object refactoring (Phase 2 of 2)
   - Extracted 7 additional services: AgentService, MessageService, TaskService,
     ContextService, TemplateService, OrchestrationService, JobService
   - Reduced ToolAccessor from 2,677 → 370 lines (86% reduction)
   - Created complete service layer architecture
   - 80%+ test coverage on all services
   ```

3. **Update REFACTORING_ROADMAP:**
   - Mark Handover 0123 as COMPLETE
   - Unblock Handovers 0124, 0125, 0126
   - Update architecture vision with actual results

4. **Update SERVICES_ARCHITECTURE.md:**
   - Add all 7 new services
   - Document service interactions
   - Update migration guide
   - Add service composition examples

5. **Enable next handovers:**
   - 0124 can now consolidate agent endpoints using AgentService
   - 0125 can modularize projects endpoints using ProjectService
   - 0126 can modularize templates/products using TemplateService

---

## Related Handovers

**Dependencies (must be complete):**
- **Handover 0120:** ✅ Message Queue Consolidation
- **Handover 0121:** ✅ ToolAccessor Phase 1 (ProjectService extraction)

**Enables:**
- **Handover 0124:** Agent Endpoint Consolidation (uses AgentService)
- **Handover 0125:** Projects Endpoint Modularization (uses ProjectService)
- **Handover 0126:** Templates & Products Modularization (uses TemplateService, others)

**Related:**
- **Handover 0122:** Orchestration Documentation (clarifies OrchestrationService scope)
- **SERVICES_ARCHITECTURE.md:** Service layer pattern documentation
- **REFACTORING_ROADMAP_0120-0129.md:** Overall refactoring plan

---

## Summary

**What:** Extract 7 remaining services from ToolAccessor
**Why:** Complete god object refactoring, enable service-based architecture
**How:** 7 parallel agents using proven Phase 1 pattern
**When:** After Handover 0121, enables 0124-0126
**Effort:** 2-3 weeks (7 parallel agents)
**Impact:** -1,950 lines from ToolAccessor, +2,100 lines of focused services, complete refactoring

**Success Metric:** If ToolAccessor is reduced to ~370 lines with all business logic in focused, testable services, this handover succeeded. The god object problem will be fully resolved.

---

**Document Version:** 1.0
**Last Updated:** 2025-11-10
**Status:** Ready for Implementation
**Estimated Completion:** 2025-12-01 (2-3 weeks from start)
