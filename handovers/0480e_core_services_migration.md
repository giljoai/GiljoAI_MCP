# Handover 0480e: Core Services Migration (OrchestrationService, AgentJobManager, TemplateService)

**Date:** 2026-01-26
**From Agent:** Documentation Manager
**To Agent:** Database Expert + TDD Implementor
**Priority:** HIGH
**Estimated Complexity:** 10-12 hours
**Status:** Ready for Implementation
**Series:** 0480 (Exception Handling Architecture Remediation)
**Dependencies:** Handover 0480d (High-value services complete)

---

## Executive Summary

### What
Migrate three core infrastructure services:
1. **OrchestrationService** - Orchestrator coordination (15+ exceptions)
2. **AgentJobManager** - Agent job lifecycle (20+ exceptions)
3. **TemplateService** - Agent template management (10+ exceptions)

These services have complex dependencies and require careful migration.

### Why
- Critical infrastructure (all projects depend on these)
- Complex business logic needs rich exception context
- Current error handling masks root causes
- Foundation for endpoint migration (Handover 0480g)

### Impact
- **Files Changed**: 3 service files, 3 test files, ~8 new domain exceptions
- **Code Reduction**: ~150 lines
- **Risk**: Medium (high usage, but well-tested)

---

## Service 1: OrchestrationService

**Complexity**: HIGH
**Estimated Time**: 5 hours
**Dependencies**: ProjectService, ProductService

### New Domain Exceptions

```python
# ORCHESTRATION EXCEPTIONS
class OrchestratorNotFoundError(NotFoundError):
    def __init__(self, orchestrator_id: str, tenant_key: Optional[str] = None):
        super().__init__(
            message=f"Orchestrator {orchestrator_id} not found",
            metadata={"orchestrator_id": orchestrator_id, "tenant_key": tenant_key}
        )

class ContextBudgetExceededError(ValidationError):
    def __init__(self, context_used: int, context_budget: int):
        super().__init__(
            message=f"Context budget exceeded: {context_used}/{context_budget} tokens",
            metadata={"context_used": context_used, "context_budget": context_budget}
        )

class SuccessionNotRequiredError(ValidationError):
    def __init__(self, orchestrator_id: str, reason: str):
        super().__init__(
            message=f"Succession not required for orchestrator {orchestrator_id}: {reason}",
            metadata={"orchestrator_id": orchestrator_id, "reason": reason}
        )
```

### Methods to Migrate (6 methods)

- [ ] **get_orchestrator_instructions()** - Use `get_or_404()`, handle context prioritization errors
- [ ] **update_project_mission()** - Validate project exists, mission length
- [ ] **update_agent_mission()** - Validate job exists
- [ ] **create_successor_orchestrator()** - Validate context budget, handle succession logic
- [ ] **check_succession_status()** - Validate thresholds
- [ ] **track_context_usage()** - Validate ranges

---

## Service 2: AgentJobManager

**Complexity**: HIGH
**Estimated Time**: 5 hours
**Dependencies**: ProjectService, TemplateService

### New Domain Exceptions

```python
# AGENT JOB EXCEPTIONS
class AgentJobNotFoundError(NotFoundError):  # Already exists
    pass

class InvalidJobStatusTransitionError(ValidationError):
    def __init__(self, job_id: str, current_status: str, attempted_status: str):
        super().__init__(
            message=f"Cannot transition job from '{current_status}' to '{attempted_status}'",
            metadata={"job_id": job_id, "current": current_status, "attempted": attempted_status}
        )

class JobAlreadyAcknowledgedError(ConflictError):
    def __init__(self, job_id: str, acknowledged_by: str):
        super().__init__(
            message=f"Job already acknowledged by agent {acknowledged_by}",
            metadata={"job_id": job_id, "acknowledged_by": acknowledged_by}
        )

class AgentNotAssignedToJobError(AuthorizationError):
    def __init__(self, agent_id: str, job_id: str):
        super().__init__(
            message=f"Agent {agent_id} is not assigned to job {job_id}",
            metadata={"agent_id": agent_id, "job_id": job_id}
        )
```

### Methods to Migrate (9 methods)

- [ ] **get_pending_jobs()** - Tenant filtering, template validation
- [ ] **acknowledge_job()** - Validate job exists, not already acknowledged, agent match
- [ ] **report_progress()** - Validate job exists, status is 'active'
- [ ] **complete_job()** - Validate job exists, final status transition
- [ ] **report_error()** - Validate job exists, pause job
- [ ] **spawn_agent_job()** - Validate project/template exist, generate thin prompt
- [ ] **cancel_job()** - Validate job exists, status allows cancellation
- [ ] **get_workflow_status()** - Validate project exists
- [ ] **handover_job()** - Complex validation, successor creation

---

## Service 3: TemplateService

**Complexity**: MEDIUM
**Estimated Time**: 3 hours
**Dependencies**: None (leaf service)

### New Domain Exceptions

```python
# TEMPLATE EXCEPTIONS
class TemplateNotFoundError(NotFoundError):  # Already exists
    pass

class TemplateAlreadyExistsError(ConflictError):
    def __init__(self, agent_name: str, tenant_key: str):
        super().__init__(
            message=f"Template '{agent_name}' already exists",
            metadata={"agent_name": agent_name, "tenant_key": tenant_key}
        )

class InvalidTemplateContentError(ValidationError):
    def __init__(self, agent_name: str, validation_errors: list):
        super().__init__(
            message=f"Template '{agent_name}' has validation errors",
            metadata={"agent_name": agent_name, "errors": validation_errors}
        )
```

### Methods to Migrate (5 methods)

- [ ] **get_template()** - Use `get_or_404()`
- [ ] **list_templates()** - Use `list_by_tenant()`, filter by active
- [ ] **create_template()** - Validate name unique, content valid
- [ ] **update_template()** - Validate exists, content valid
- [ ] **delete_template()** - Soft delete, check for active jobs

---

## Migration Strategy

### Phase 1: TemplateService First (Day 1, 3 hours)
**Why**: Leaf service with no dependencies on other services.

1. Create domain exceptions
2. Migrate methods (simplest patterns)
3. Write tests
4. Verify integration tests pass

### Phase 2: AgentJobManager (Day 1-2, 5 hours)
**Why**: Depends on TemplateService (now migrated).

1. Create domain exceptions
2. Migrate methods (complex state machine logic)
3. Write tests (many edge cases)
4. Verify integration tests pass

### Phase 3: OrchestrationService (Day 2, 5 hours)
**Why**: Depends on AgentJobManager and high-value services.

1. Create domain exceptions
2. Migrate methods (context tracking complexity)
3. Write tests
4. Verify integration tests pass

---

## Testing Requirements

### TemplateService Tests (10 tests)
- [ ] `test_get_template_not_found`
- [ ] `test_create_template_duplicate`
- [ ] `test_create_template_invalid_content`
- [ ] `test_update_template_not_found`
- [ ] `test_delete_template_with_active_jobs`
- [ ] Integration: `test_template_api_404`
- [ ] Integration: `test_template_api_409`
- [ ] Integration: `test_template_api_400_validation`
- [ ] Integration: `test_list_templates_tenant_isolated`
- [ ] Integration: `test_delete_template_409_active_jobs`

### AgentJobManager Tests (18 tests)
- [ ] `test_get_pending_jobs_template_not_found`
- [ ] `test_acknowledge_job_not_found`
- [ ] `test_acknowledge_job_already_acknowledged`
- [ ] `test_acknowledge_job_wrong_agent`
- [ ] `test_report_progress_job_not_active`
- [ ] `test_complete_job_invalid_transition`
- [ ] `test_cancel_job_not_found`
- [ ] `test_spawn_job_project_not_found`
- [ ] `test_spawn_job_template_not_found`
- [ ] Integration: `test_job_lifecycle_404_errors`
- [ ] Integration: `test_job_lifecycle_409_conflicts`
- [ ] Integration: `test_job_lifecycle_403_authorization`
- [ ] ... (6 more integration tests)

### OrchestrationService Tests (12 tests)
- [ ] `test_get_instructions_orchestrator_not_found`
- [ ] `test_update_mission_project_not_found`
- [ ] `test_context_budget_exceeded`
- [ ] `test_succession_not_required`
- [ ] `test_create_successor_context_under_threshold`
- [ ] Integration: `test_orchestration_api_404`
- [ ] Integration: `test_orchestration_api_400_validation`
- [ ] ... (5 more integration tests)

---

## Dependency Notes

### OrchestrationService Dependencies
- **ProjectService**: For fetching project context
- **ProductService**: For fetching product context
- **AgentJobManager**: For spawning agent jobs
- **ContextService**: For fetching context fields

**Risk Mitigation**: Ensure 0480d complete before starting OrchestrationService.

### AgentJobManager Dependencies
- **TemplateService**: For validating agent templates exist
- **ProjectService**: For validating project exists

**Risk Mitigation**: Migrate TemplateService first.

---

## Rollback Plan

Services can be rolled back in reverse order:

```bash
# Rollback Phase 3 (OrchestrationService)
git revert <commit_hash_orchestration>

# Rollback Phase 2 (AgentJobManager)
git revert <commit_hash_agent_job_manager>

# Rollback Phase 1 (TemplateService)
git revert <commit_hash_template_service>
```

All tests must pass after each rollback.

---

## Success Criteria

- [ ] All 3 services inherit from `BaseService`
- [ ] Zero `HTTPException` in service files
- [ ] 40 total tests written (10 + 18 + 12)
- [ ] Unit test coverage >90% for each service
- [ ] Integration tests verify HTTP status codes unchanged
- [ ] No breaking changes to API contracts

---

**Document Version**: 1.0
**Created**: 2026-01-26
**Author**: Claude (Sonnet 4.5)
**Status**: Ready for Implementation
