# Handover 0453: TDD Test Rewrite

**Created**: 2026-01-22
**Series**: Orchestrator/ToolAccessor Consolidation (0450-0453)
**Phase**: 4 of 4 (Orange - Testing)
**Risk Level**: LOW

---

## Executive Summary

Write comprehensive TDD tests for the consolidated OrchestrationService. This handover ensures the new architecture has proper test coverage and documents the new patterns for future development.

---

## Pre-Requisites

- [ ] Handover 0450-0452 completed successfully
- [ ] `orchestrator.py` deleted
- [ ] All service methods working
- [ ] Basic tests passing

---

## Test Strategy

### Files to Create/Update

| File | Purpose | Coverage Target |
|------|---------|-----------------|
| `tests/services/test_orchestration_service_full.py` | Complete service coverage | 90%+ |
| `tests/integration/test_orchestration_e2e.py` | End-to-end workflows | Critical paths |
| `tests/tools/test_tool_accessor_delegation.py` | Verify delegation pattern | All delegated methods |

### Test Categories

1. **Unit Tests** - Individual method behavior
2. **Integration Tests** - Service interactions
3. **E2E Tests** - Full workflow from MCP tool to database
4. **Multi-Tenant Tests** - Isolation verification
5. **Error Handling Tests** - Failure scenarios

---

## TDD Test Specifications

### 1. Process Product Vision Tests

```python
@pytest.mark.asyncio
async def test_process_product_vision_full_workflow(db_session, test_tenant, test_product):
    """Complete workflow: vision -> project -> missions -> agents"""
    service = OrchestrationService(db_session, test_tenant)

    result = await service.process_product_vision(
        tenant_key=test_tenant,
        product_id=test_product.id,
        project_requirements="Build user authentication"
    )

    assert result["success"] is True
    assert "project_id" in result["data"]
    assert "mission_plan" in result["data"]
    assert "selected_agents" in result["data"]
    assert len(result["data"]["selected_agents"]) > 0

@pytest.mark.asyncio
async def test_process_product_vision_uses_existing_project(db_session, test_tenant, test_project):
    """When project_id provided, don't create duplicate"""
    service = OrchestrationService(db_session, test_tenant)

    result = await service.process_product_vision(
        tenant_key=test_tenant,
        product_id=test_project.product_id,
        project_requirements="Build feature X",
        project_id=test_project.id  # Use existing
    )

    assert result["success"] is True
    assert result["data"]["project_id"] == str(test_project.id)
    # Verify no new project was created
    projects = await db_session.execute(
        select(Project).where(Project.product_id == test_project.product_id)
    )
    assert len(projects.scalars().all()) == 1  # Still just one

@pytest.mark.asyncio
async def test_process_product_vision_chunks_large_vision(db_session, test_tenant):
    """Vision documents >25K tokens should be chunked"""
    # Create product with 50K token vision
    large_vision = "x" * 60000
    product = await create_test_product(db_session, test_tenant, vision_content=large_vision)

    service = OrchestrationService(db_session, test_tenant)
    result = await service.process_product_vision(...)

    # Verify chunking occurred
    assert product.vision_chunked is True
```

### 2. Agent Spawning Tests

```python
@pytest.mark.asyncio
async def test_spawn_agent_routes_claude_code(db_session, test_tenant, test_project):
    """Agents with tool='claude_code' route to Claude Code spawn"""
    template = await create_test_template(db_session, test_tenant, tool="claude_code")
    service = OrchestrationService(db_session, test_tenant)

    result = await service.spawn_agent(
        project_id=test_project.id,
        role=AgentRole.IMPLEMENTER,
        template=template
    )

    assert result["success"] is True
    assert result["data"]["execution_mode"] == "claude_code"

@pytest.mark.asyncio
async def test_spawn_agent_routes_codex(db_session, test_tenant, test_project):
    """Agents with tool='codex' route to Codex spawn"""
    template = await create_test_template(db_session, test_tenant, tool="codex")
    service = OrchestrationService(db_session, test_tenant)

    result = await service.spawn_agent(...)

    assert result["data"]["execution_mode"] == "codex"

@pytest.mark.asyncio
async def test_spawn_agents_parallel(db_session, test_tenant, test_project):
    """Multiple agents can be spawned in parallel"""
    service = OrchestrationService(db_session, test_tenant)

    agents = [
        {"role": AgentRole.IMPLEMENTER, "mission": "Implement feature"},
        {"role": AgentRole.TESTER, "mission": "Write tests"},
    ]

    result = await service.spawn_agents_parallel(test_project.id, agents)

    assert result["success"] is True
    assert len(result["data"]["jobs"]) == 2
```

### 3. Succession Tests

```python
@pytest.mark.asyncio
async def test_create_successor_orchestrator_creates_job(db_session, test_tenant):
    """Successor creation creates new orchestrator job"""
    # Create active orchestrator
    current = await create_test_orchestrator_job(db_session, test_tenant)

    service = OrchestrationService(db_session, test_tenant)
    result = await service.create_successor_orchestrator(
        current_job_id=current.id,
        tenant_key=test_tenant,
        reason="context_limit"
    )

    assert result["success"] is True
    assert result["data"]["successor_job_id"] != str(current.id)

    # Verify current job marked for succession
    await db_session.refresh(current)
    assert current.succession_triggered is True

@pytest.mark.asyncio
async def test_check_succession_status_at_threshold(db_session, test_tenant):
    """Succession check returns true at 90% context usage"""
    job = await create_test_orchestrator_job(
        db_session, test_tenant,
        context_used=135000,  # 90% of 150000 default budget
        context_budget=150000
    )

    service = OrchestrationService(db_session, test_tenant)
    result = await service.check_succession_status(job.id, test_tenant)

    assert result["success"] is True
    assert result["data"]["succession_needed"] is True
    assert result["data"]["context_percent"] >= 90
```

### 4. Multi-Tenant Isolation Tests

```python
@pytest.mark.asyncio
async def test_tenant_isolation_process_product_vision(db_session):
    """Cannot process vision for product in different tenant"""
    # Create product in tenant A
    product = await create_test_product(db_session, "tenant_a")

    # Try to access from tenant B
    service = OrchestrationService(db_session, "tenant_b")
    result = await service.process_product_vision(
        tenant_key="tenant_b",
        product_id=product.id,
        project_requirements="..."
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()

@pytest.mark.asyncio
async def test_tenant_isolation_spawn_agent(db_session):
    """Cannot spawn agent for project in different tenant"""
    project = await create_test_project(db_session, "tenant_a")

    service = OrchestrationService(db_session, "tenant_b")
    result = await service.spawn_agent(
        project_id=project.id,
        role=AgentRole.IMPLEMENTER
    )

    assert result["success"] is False

@pytest.mark.asyncio
async def test_tenant_isolation_succession(db_session):
    """Cannot create successor for job in different tenant"""
    job = await create_test_orchestrator_job(db_session, "tenant_a")

    service = OrchestrationService(db_session, "tenant_b")
    result = await service.create_successor_orchestrator(job.id, "tenant_b", "manual")

    assert result["success"] is False
```

### 5. Error Handling Tests

```python
@pytest.mark.asyncio
async def test_process_product_vision_invalid_product(db_session, test_tenant):
    """Returns error for non-existent product"""
    service = OrchestrationService(db_session, test_tenant)
    result = await service.process_product_vision(
        tenant_key=test_tenant,
        product_id="00000000-0000-0000-0000-000000000000",
        project_requirements="..."
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()

@pytest.mark.asyncio
async def test_spawn_agent_invalid_role(db_session, test_tenant, test_project):
    """Returns error for invalid agent role"""
    service = OrchestrationService(db_session, test_tenant)
    result = await service.spawn_agent(
        project_id=test_project.id,
        role="invalid_role"
    )

    assert result["success"] is False
```

---

## Success Criteria

- [ ] 90%+ coverage on OrchestrationService
- [ ] All critical paths tested
- [ ] Multi-tenant isolation verified
- [ ] Error handling tested
- [ ] No regressions in existing functionality
- [ ] Test file organization follows project conventions

---

## Verification Commands

```bash
# Run all new tests
pytest tests/services/test_orchestration_service_full.py -v
pytest tests/integration/test_orchestration_e2e.py -v
pytest tests/tools/test_tool_accessor_delegation.py -v

# Coverage report
pytest tests/ --cov=src/giljo_mcp/services/orchestration_service --cov-report=html

# Full test suite
pytest tests/ -v

# View coverage
# Open: htmlcov/index.html
```

---

## Documentation Updates

After tests pass, update:

1. `docs/SERVICES.md` - Add OrchestrationService consolidated methods
2. `docs/TESTING.md` - Add new test patterns
3. `CLAUDE.md` - Update orchestrator references

---

## Completion Checklist

- [ ] All tests written and passing
- [ ] Coverage >90% for OrchestrationService
- [ ] Documentation updated
- [ ] Git commit with test results
- [ ] Merge to master (if all green)

---

## Final Commands (On Completion)

```bash
# Final test run
pytest tests/ -v --tb=short

# Commit
git add .
git commit -m "feat: Complete orchestrator/tool_accessor consolidation (0450-0453)

- Moved process_product_vision to OrchestrationService
- Moved 4 inline methods from tool_accessor to service
- Deleted orchestrator.py (1,675 lines removed)
- Added comprehensive TDD tests (90%+ coverage)

Net code reduction: ~1,500 lines
Tests: X passed, 0 failed
Coverage: 90%+"

# Merge to master
git checkout master
git merge _orchestrator_tool_accessor_consolidation
git push origin master
```

---

## Estimated Effort

- Test writing: 2-3 hours
- Documentation updates: 30 minutes
- Final verification: 30 minutes
- **Total**: 3-4 hours

---

## CHAIN COMPLETE

This is the final handover in the consolidation series. No next terminal to spawn.

After completion:
1. Delete the `_orchestrator_tool_accessor_consolidation` branch (merged)
2. Archive handovers 0450-0453 to `handovers/completed/`
3. Update CLAUDE.md with new architecture
