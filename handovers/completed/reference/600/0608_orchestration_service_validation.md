# Handover 0608: OrchestrationService Validation

**Phase**: 1
**Tool**: CCW (Cloud)
**Agent Type**: tdd-implementor
**Duration**: 1 day
**Parallel Group**: Group A (Services)
**Depends On**: 0602

---

## Context

**Read First**: `handovers/600/AGENT_REFERENCE_GUIDE.md` for universal project context.

**Previous Handovers**: Handover 0602 established test baseline.

**This Handover**: Create comprehensive unit and integration tests for OrchestrationService, achieving 80%+ coverage while validating mission planning (condensed missions), agent selection (capability matching), workflow execution (waterfall/parallel coordination), and AgentJobManager integration for context prioritization and orchestration.

---

## Specific Objectives

- **Objective 1**: Create comprehensive unit tests for all OrchestrationService methods (80%+ coverage)
- **Objective 2**: Create integration tests for MissionPlanner, AgentSelector, WorkflowEngine integration
- **Objective 3**: Validate mission condensation (context prioritization and orchestration from vision docs)
- **Objective 4**: Test agent selection based on capability matching
- **Objective 5**: Verify workflow coordination (waterfall and parallel execution)
- **Objective 6**: Ensure AgentJobManager integration for job lifecycle

---

## Tasks

### Task 1: Read and Analyze OrchestrationService
**What**: Read OrchestrationService implementation
**Files**:
- `src/giljo_mcp/services/orchestration_service.py`
- `src/giljo_mcp/mission_planner.py`
- `src/giljo_mcp/agent_selector.py`
- `src/giljo_mcp/workflow_engine.py`

**Methods to Test**:
- `process_product_vision(product_id, tenant_key)` - Parse vision doc
- `generate_mission_plan(vision_data, tenant_key)` - Create condensed mission
- `select_agents_for_mission(mission_plan, tenant_key)` - Match capabilities
- `coordinate_agent_workflow(mission_plan, selected_agents, tenant_key)` - Execute
- `create_agent_jobs(agents, mission_plan, tenant_key)` - AgentJobManager integration
- `monitor_workflow_progress(workflow_id, tenant_key)` - Track execution
- `handle_agent_failure(agent_job_id, error, tenant_key)` - Error handling

### Task 2: Implement Mission Planning Tests
**What**: Write unit tests for mission planning and condensation
**Files**: `tests/unit/test_orchestration_service.py`

**Test Coverage** (40+ tests):

**Vision Processing Tests** (5 tests):
- `test_process_product_vision_success`
- `test_process_product_vision_markdown_parsing`
- `test_process_product_vision_not_found`
- `test_process_product_vision_empty_vision`
- `test_process_product_vision_wrong_tenant`

**Mission Generation Tests** (8 tests):
- `test_generate_mission_plan_success`
- `test_generate_mission_plan_70_percent_reduction` - Token count validation
- `test_generate_mission_plan_includes_objectives`
- `test_generate_mission_plan_includes_constraints`
- `test_generate_mission_plan_condensed_format`
- `test_generate_mission_plan_preserves_key_info`
- `test_generate_mission_plan_invalid_vision_data`
- `test_generate_mission_plan_too_large_vision`

**Example Test**:
```python
def test_generate_mission_plan_70_percent_reduction(
    self, orchestration_service, sample_vision_data, test_tenant_key
):
    """Test mission plan achieves context prioritization and orchestration"""
    # Arrange: Vision data with known token count (e.g., 10,000 tokens)
    vision_text = sample_vision_data["vision_text"]
    original_tokens = estimate_tokens(vision_text)  # ~10,000 tokens

    # Act: Generate mission plan
    mission_plan = orchestration_service.generate_mission_plan(
        vision_data=sample_vision_data,
        tenant_key=test_tenant_key
    )

    # Assert: Mission plan <= 30% of original (70% reduction)
    mission_tokens = estimate_tokens(mission_plan["condensed_mission"])
    reduction_percentage = (1 - mission_tokens / original_tokens) * 100

    assert reduction_percentage >= 70
    assert mission_tokens <= original_tokens * 0.3
```

### Task 3: Implement Agent Selection Tests
**What**: Write tests for agent selection based on capabilities
**Files**: `tests/unit/test_orchestration_service.py`

**Test Coverage** (9 tests):
- `test_select_agents_for_mission_success`
- `test_select_agents_capability_matching`
- `test_select_agents_priority_ordering`
- `test_select_agents_workload_balancing`
- `test_select_agents_availability_check`
- `test_select_agents_no_match_found`
- `test_select_agents_fallback_to_generalist`
- `test_select_agents_multi_agent_coordination`
- `test_select_agents_wrong_tenant`

**Example Test**:
```python
def test_select_agents_capability_matching(
    self, orchestration_service, mission_plan, test_tenant_key
):
    """Test agent selection matches required capabilities"""
    # Arrange: Mission requires 'python', 'api-design' capabilities
    mission_plan["required_capabilities"] = ["python", "api-design"]

    # Act: Select agents
    selected_agents = orchestration_service.select_agents_for_mission(
        mission_plan=mission_plan,
        tenant_key=test_tenant_key
    )

    # Assert: All selected agents have required capabilities
    assert len(selected_agents) > 0
    for agent in selected_agents:
        agent_capabilities = agent["capabilities"]
        assert "python" in agent_capabilities or "generalist" in agent_capabilities
```

### Task 4: Implement Workflow Coordination Tests
**What**: Write tests for waterfall and parallel workflow execution
**Files**: `tests/unit/test_orchestration_service.py`

**Test Coverage** (10 tests):

**Waterfall Execution** (4 tests):
- `test_coordinate_workflow_waterfall_sequential`
- `test_coordinate_workflow_waterfall_dependency_order`
- `test_coordinate_workflow_waterfall_error_propagation`
- `test_coordinate_workflow_waterfall_completion`

**Parallel Execution** (3 tests):
- `test_coordinate_workflow_parallel_independent_tasks`
- `test_coordinate_workflow_parallel_max_concurrency`
- `test_coordinate_workflow_parallel_error_handling`

**Mixed Execution** (3 tests):
- `test_coordinate_workflow_mixed_waterfall_parallel`
- `test_coordinate_workflow_dependency_graph_resolution`
- `test_coordinate_workflow_progress_tracking`

### Task 5: Implement AgentJobManager Integration Tests
**What**: Write tests for agent job creation and lifecycle
**Files**: `tests/unit/test_orchestration_service.py`

**Test Coverage** (6 tests):
- `test_create_agent_jobs_success`
- `test_create_agent_jobs_with_mission_plan`
- `test_create_agent_jobs_status_pending`
- `test_monitor_workflow_progress_success`
- `test_handle_agent_failure_retry_logic`
- `test_handle_agent_failure_escalation`

### Task 6: Create Integration Tests
**What**: Create integration tests for full orchestration workflow
**Files**: `tests/integration/test_orchestration_service.py`

**Test Coverage** (12 tests):

**Multi-Tenant Isolation** (2 tests):
- `test_tenant_isolation_orchestration`
- `test_tenant_isolation_agent_jobs`

**End-to-End Orchestration** (5 tests):
- `test_full_orchestration_workflow`
- `test_orchestration_with_product_vision`
- `test_orchestration_agent_selection`
- `test_orchestration_job_creation`
- `test_orchestration_workflow_execution`

**MissionPlanner Integration** (2 tests):
- `test_mission_planner_condensation`
- `test_mission_planner_token_reduction_verified`

**AgentSelector Integration** (2 tests):
- `test_agent_selector_capability_matching`
- `test_agent_selector_availability_check`

**WorkflowEngine Integration** (1 test):
- `test_workflow_engine_coordination`

### Task 7: Run Tests and Verify Coverage
**Commands**:
```bash
pytest tests/unit/test_orchestration_service.py -v \
  --cov=src/giljo_mcp/services/orchestration_service.py \
  --cov=src/giljo_mcp/mission_planner.py \
  --cov=src/giljo_mcp/agent_selector.py \
  --cov=src/giljo_mcp/workflow_engine.py \
  --cov-report=term-missing

pytest tests/integration/test_orchestration_service.py -v
```

---

## Success Criteria

- [ ] **Unit Tests**: 40+ unit tests created
- [ ] **Integration Tests**: 12+ integration tests
- [ ] **Coverage**: ≥ 80% coverage on OrchestrationService + helpers
- [ ] **70% Token Reduction**: Mission condensation verified
- [ ] **Agent Selection**: Capability matching tested
- [ ] **Workflow Coordination**: Waterfall and parallel execution tested
- [ ] **All Tests Pass**: 100% pass rate
- [ ] **PR Created**: Branch `0608-orchestration-service-tests`

---

## Deliverables

### Code
- **Created**:
  - `tests/unit/test_orchestration_service.py` (40+ tests)
  - `tests/integration/test_orchestration_service.py` (12+ tests)

### Git Commit
- **Message**: `test: Add comprehensive OrchestrationService tests (Handover 0608)`
- **Branch**: `0608-orchestration-service-tests`

---

## Dependencies

### Requires
- **Handover 0602**: Test baseline established
- **Files**:
  - `src/giljo_mcp/services/orchestration_service.py`
  - `src/giljo_mcp/mission_planner.py`
  - `src/giljo_mcp/agent_selector.py`
  - `src/giljo_mcp/workflow_engine.py`

### Blocks
- **Handover 0613**: Agent Jobs API validation
- **Handover 0620**: Orchestration workflows E2E testing

---

## Notes for Agent

### CCW (Cloud) Execution
- Create branch: `0608-orchestration-service-tests`
- Test context prioritization and orchestration (critical feature)
- Test both waterfall and parallel workflows
- Verify AgentJobManager integration

### Quality Checklist
- [ ] Mission condensation achieves 70% reduction
- [ ] Agent selection capability matching verified
- [ ] Workflow coordination tested (waterfall + parallel)
- [ ] All tests pass (100% pass rate)
- [ ] Coverage ≥ 80%

---

**Document Control**:
- **Handover**: 0608
- **Created**: 2025-11-14
- **Status**: Ready for execution
