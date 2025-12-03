# Handover 0607: ContextService Validation

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

**This Handover**: Create comprehensive unit and integration tests for ContextService, achieving 80%+ coverage while validating context usage tracking, succession monitoring (90%+ budget triggers), handover summary generation, and orchestrator lineage tracking.

---

## Specific Objectives

- **Objective 1**: Create comprehensive unit tests for all ContextService methods (80%+ coverage)
- **Objective 2**: Create integration tests for succession workflow
- **Objective 3**: Validate context budget tracking and 90%+ threshold detection
- **Objective 4**: Test handover summary generation (<10K tokens)
- **Objective 5**: Verify orchestrator lineage tracking (spawned_by chain)
- **Objective 6**: Ensure succession reason logging

---

## Tasks

### Task 1: Read and Analyze ContextService
**What**: Read ContextService implementation
**Files**: `src/giljo_mcp/services/context_service.py`

**Methods to Test**:
- `track_context_usage(agent_job_id, context_used, context_budget)`
- `get_context_usage(agent_job_id, tenant_key)`
- `calculate_context_percentage(agent_job_id, tenant_key)`
- `check_succession_threshold(agent_job_id, tenant_key, threshold=0.9)`
- `create_handover_summary(agent_job_id, tenant_key, max_tokens=10000)`
- `get_orchestrator_lineage(agent_job_id, tenant_key)` - Get spawned_by chain
- `log_succession_trigger(agent_job_id, reason, tenant_key)`

### Task 2: Implement Context Tracking Tests
**What**: Write unit tests for context usage tracking
**Files**: `tests/unit/test_context_service.py`

**Test Coverage** (35+ tests):

**Tracking Tests** (7 tests):
- `test_track_context_usage_success`
- `test_track_context_usage_updates_existing`
- `test_track_context_usage_calculates_percentage`
- `test_track_context_usage_invalid_budget`
- `test_track_context_usage_zero_budget`
- `test_track_context_usage_wrong_tenant`
- `test_track_context_usage_timestamp_recorded`

**Retrieval Tests** (4 tests):
- `test_get_context_usage_success`
- `test_get_context_usage_not_found`
- `test_get_context_usage_wrong_tenant`
- `test_calculate_context_percentage`

### Task 3: Implement Succession Threshold Tests
**What**: Write tests for 90%+ threshold detection
**Files**: `tests/unit/test_context_service.py`

**Test Coverage** (8 tests):
- `test_check_succession_threshold_below_90` - Returns False
- `test_check_succession_threshold_at_90` - Returns True
- `test_check_succession_threshold_above_90` - Returns True
- `test_check_succession_threshold_custom_threshold` - 85% threshold
- `test_check_succession_threshold_100_percent` - Edge case
- `test_check_succession_threshold_no_usage_data` - Returns False
- `test_log_succession_trigger_success`
- `test_log_succession_trigger_with_reason`

**Example Test**:
```python
def test_check_succession_threshold_at_90(self, context_service, test_agent_job, test_tenant_key):
    """Test succession threshold detection at exactly 90%"""
    # Arrange: Track context at 90%
    context_service.track_context_usage(
        agent_job_id=test_agent_job.id,
        context_used=90000,
        context_budget=100000
    )

    # Act: Check threshold
    should_succeed = context_service.check_succession_threshold(
        agent_job_id=test_agent_job.id,
        tenant_key=test_tenant_key,
        threshold=0.9
    )

    # Assert: Succession should trigger
    assert should_succeed is True
```

### Task 4: Implement Handover Summary Tests
**What**: Write tests for handover summary generation
**Files**: `tests/unit/test_context_service.py`

**Test Coverage** (6 tests):
- `test_create_handover_summary_success`
- `test_create_handover_summary_token_limit` - Max 10K tokens
- `test_create_handover_summary_includes_context_refs`
- `test_create_handover_summary_includes_key_decisions`
- `test_create_handover_summary_condensed_format`
- `test_create_handover_summary_not_found`

**Example Test**:
```python
def test_create_handover_summary_token_limit(self, context_service, test_agent_job, test_tenant_key):
    """Test handover summary respects 10K token limit"""
    # Act: Create summary
    summary = context_service.create_handover_summary(
        agent_job_id=test_agent_job.id,
        tenant_key=test_tenant_key,
        max_tokens=10000
    )

    # Assert: Token count <= 10K
    # Rough estimation: ~4 chars per token
    estimated_tokens = len(summary) / 4
    assert estimated_tokens <= 10000
    assert len(summary) > 0  # Not empty
```

### Task 5: Implement Lineage Tracking Tests
**What**: Write tests for orchestrator lineage (spawned_by chain)
**Files**: `tests/unit/test_context_service.py`

**Test Coverage** (5 tests):
- `test_get_orchestrator_lineage_single_instance`
- `test_get_orchestrator_lineage_two_generations`
- `test_get_orchestrator_lineage_multiple_generations`
- `test_get_orchestrator_lineage_circular_detection`
- `test_get_orchestrator_lineage_empty_chain`

**Example Test**:
```python
def test_get_orchestrator_lineage_multiple_generations(
    self, context_service, db_session, test_tenant_key
):
    """Test lineage tracking across 3 orchestrator instances"""
    # Arrange: Create 3-generation lineage
    # Orchestrator 1 (instance 1)
    orch1 = create_agent_job(db_session, instance_number=1, spawned_by=None)

    # Orchestrator 2 (instance 2, spawned by orch1)
    orch2 = create_agent_job(db_session, instance_number=2, spawned_by=orch1.id)

    # Orchestrator 3 (instance 3, spawned by orch2)
    orch3 = create_agent_job(db_session, instance_number=3, spawned_by=orch2.id)

    # Act: Get lineage for orch3
    lineage = context_service.get_orchestrator_lineage(
        agent_job_id=orch3.id,
        tenant_key=test_tenant_key
    )

    # Assert: Full lineage returned
    assert len(lineage) == 3
    assert lineage[0].id == orch1.id
    assert lineage[1].id == orch2.id
    assert lineage[2].id == orch3.id
```

### Task 6: Create Integration Tests
**What**: Create integration tests for succession workflow
**Files**: `tests/integration/test_context_service.py`

**Test Coverage** (10 tests):

**Multi-Tenant Isolation** (2 tests):
- `test_tenant_isolation_context_tracking`
- `test_tenant_isolation_lineage`

**Succession Workflow** (5 tests):
- `test_full_succession_workflow`
- `test_succession_at_90_percent_creates_successor`
- `test_succession_handover_summary_generation`
- `test_succession_lineage_preserved`
- `test_succession_reason_logged`

**Performance** (3 tests):
- `test_context_tracking_performance`
- `test_handover_summary_generation_time`
- `test_lineage_query_performance`

### Task 7: Run Tests and Verify Coverage
**Commands**:
```bash
pytest tests/unit/test_context_service.py -v \
  --cov=src/giljo_mcp/services/context_service.py \
  --cov-report=term-missing

pytest tests/integration/test_context_service.py -v
```

---

## Success Criteria

- [ ] **Unit Tests**: 35+ unit tests created
- [ ] **Integration Tests**: 10+ integration tests
- [ ] **Coverage**: ≥ 80% coverage on ContextService
- [ ] **Succession Tested**: 90%+ threshold detection working
- [ ] **All Tests Pass**: 100% pass rate
- [ ] **PR Created**: Branch `0607-context-service-tests`

---

## Deliverables

### Code
- **Created**:
  - `tests/unit/test_context_service.py` (35+ tests)
  - `tests/integration/test_context_service.py` (10+ tests)

### Git Commit
- **Message**: `test: Add comprehensive ContextService tests (Handover 0607)`
- **Branch**: `0607-context-service-tests`

---

## Dependencies

### Requires
- **Handover 0602**: Test baseline established
- **Files**: `src/giljo_mcp/services/context_service.py`

### Blocks
- **Handover 0620**: Orchestration workflows testing

---

## Notes for Agent

### CCW (Cloud) Execution
- Create branch: `0607-context-service-tests`
- Focus on succession workflow testing
- Test lineage chain construction

---

**Document Control**:
- **Handover**: 0607
- **Created**: 2025-11-14
- **Status**: Ready for execution
