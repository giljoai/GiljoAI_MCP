# Handover 0272: Comprehensive Integration Test Suite

**Date**: 2025-11-29
**Status**: Ready for Implementation
**Type**: Quality Assurance
**Priority**: 🟢 High
**Estimated Time**: 6 hours
**Dependencies**: Handovers 0266-0271 (all fixes complete)
**Related**: Handovers 0265 (Investigation), docs/TESTING.md

---

## Executive Summary

**Problem**: Individual handovers (0266-0271) have unit tests, but no comprehensive integration test suite validates the COMPLETE context wiring flow from UI → Backend → Orchestrator.

**Impact**: Individual features may work in isolation but fail when integrated. Edge cases and cross-feature interactions are untested.

**Solution**: Create comprehensive integration test suite covering:
- Complete settings persistence flow (UI → DB → Orchestrator)
- All context types together (not in isolation)
- WebSocket event propagation
- Agent spawning with full context
- Performance and error handling
- Multi-tenant isolation across all features

**Scope**: This handover focuses on INTEGRATION and E2E testing, not unit tests (those were created in 0266-0271).

---

## Prerequisites

### Required Reading

1. **CRITICAL**: `F:\GiljoAI_MCP\docs\TESTING.md` - Testing patterns
2. `F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt` - TDD patterns
3. `F:\GiljoAI_MCP\handovers\0265_orchestrator_context_investigation.md` - Requirements
4. All handovers 0266-0271 - Individual feature tests

### Environment Setup

```bash
# Verify all dependencies installed
pip install -r requirements.txt

# Check test database accessible
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp_test -c "SELECT 1;"

# Verify frontend tests runnable
cd frontend && npm install && npm run test:unit -- --run
```

---

## TDD Approach

**Test-Driven Development for Integration Tests**:
1. Write FAILING integration test showing complete flow
2. Verify individual handovers (0266-0271) make it pass
3. Refactor for edge cases
4. Focus on BEHAVIOR across system boundaries
5. Test complete user journeys, not isolated units

---

## Test Categories

### 1. Complete Context Flow Tests

**Test the ENTIRE pipeline**: UI settings → Database → MCP tool → Orchestrator

```python
# tests/integration/test_complete_context_flow.py

import pytest
from src.giljo_mcp.tools.get_orchestrator_instructions import get_orchestrator_instructions
from src.giljo_mcp.services.product_service import ProductService
from src.giljo_mcp.services.user_service import UserService
from src.giljo_mcp.services.orchestration_service import OrchestrationService


@pytest.mark.asyncio
async def test_complete_settings_to_orchestrator_flow(
    db_session,
    test_user,
    test_product,
    test_project,
    test_tenant
):
    """
    E2E test: User configures settings in UI → Orchestrator receives full context

    This test validates the COMPLETE flow:
    1. User sets field priorities
    2. User enables GitHub integration
    3. User configures testing standards
    4. System closes previous project (creates 360 memory)
    5. User stages new orchestrator
    6. Orchestrator receives ALL context types correctly
    """

    # === PHASE 1: Configure User Settings ===

    user_service = UserService(db_session, tenant_key=test_tenant)

    # Set field priorities (Handover 0266)
    await user_service.update_field_priorities(
        user_id=test_user.id,
        priorities={
            "product_core": 1,      # CRITICAL
            "vision_documents": 2,  # IMPORTANT
            "tech_stack": 1,        # CRITICAL
            "architecture": 2,      # IMPORTANT
            "testing": 2,           # IMPORTANT
            "memory_360": 2,        # IMPORTANT
            "git_history": 2,       # IMPORTANT
            "agent_templates": 1    # CRITICAL
        }
    )

    # === PHASE 2: Configure Product Settings ===

    product_service = ProductService(db_session, tenant_key=test_tenant)

    # Enable GitHub integration (Handover 0269)
    await product_service.update_github_integration(
        product_id=test_product.id,
        enabled=True
    )

    # Configure testing standards (Handover 0271)
    test_product.testing_config = {
        "coverage_target": 80,
        "quality_standards": "TDD required, production-grade code",
        "frameworks": {
            "backend": ["pytest", "pytest-asyncio"],
            "frontend": ["vitest", "vue-test-utils"]
        },
        "strategy": "Unit, integration, E2E testing"
    }
    await db_session.commit()

    # === PHASE 3: Create 360 Memory ===

    # Close a previous project to create memory (Handover 0268)
    from src.giljo_mcp.tools.close_project import close_project_and_update_memory

    old_project_id = "completed-project-uuid"
    await close_project_and_update_memory(
        project_id=old_project_id,
        tenant_key=test_tenant,
        summary="Built authentication system with JWT tokens and password reset",
        key_outcomes=[
            "JWT authentication with 15-min tokens",
            "Password reset via email",
            "Role-based access control"
        ],
        decisions_made=[
            "Use bcrypt for hashing (12 rounds)",
            "15-minute token lifetime for security"
        ]
    )

    # === PHASE 4: Enable Serena MCP ===

    # Simulate Serena enabled in config (Handover 0267)
    # (In real flow, this is config.yaml setting)
    import src.giljo_mcp.config as config_module
    config_module.serena_mcp = {"enabled": True}

    # === PHASE 5: Stage Orchestrator ===

    orch_service = OrchestrationService(db_session, tenant_key=test_tenant)
    job = await orch_service.create_orchestrator_job(
        project_id=test_project.id,
        user_id=test_user.id
    )

    # === PHASE 6: Fetch Orchestrator Instructions ===

    context = await get_orchestrator_instructions(
        orchestrator_id=job.id,
        tenant_key=test_tenant
    )

    # === VERIFICATION: All Context Types Present ===

    mission = context["mission"]

    # Field priorities (0266)
    assert context["field_priorities"] != {}
    assert context["field_priorities"]["product_core"] == 1
    assert context["field_priorities"]["testing"] == 2

    # Product core (always included)
    assert test_product.name in mission
    assert test_product.description in mission

    # Vision documents (priority 2)
    assert "vision" in mission.lower()

    # Tech stack (priority 1)
    assert "tech stack" in mission.lower()

    # Serena MCP instructions (0267)
    assert "serena" in mission.lower()
    assert "find_symbol" in mission
    assert "get_symbols_overview" in mission

    # 360 Memory (0268)
    assert "360 memory" in mission.lower()
    assert "Built authentication system" in mission
    assert "JWT authentication" in mission
    assert "close_project_and_update_memory" in mission

    # GitHub integration (0269)
    assert "git" in mission.lower() or "commit" in mission.lower()

    # MCP Tool catalog (0270)
    assert "mcp tools" in mission.lower() or "available tools" in mission.lower()
    assert "spawn_agent_job" in mission
    assert "fetch_product_context" in mission

    # Testing config (0271)
    assert "testing" in mission.lower()
    assert "80" in mission or "80%" in mission  # Coverage target
    assert "tdd" in mission.lower()
    assert "pytest" in mission

    # === VERIFICATION: Context Budget ===

    assert context["context_budget"] > 0
    assert context["context_used"] >= 0
    assert context["estimated_tokens"] > 0

    # === VERIFICATION: Metadata ===

    assert context["thin_client"] is True
    assert context["serena_enabled"] is True


@pytest.mark.asyncio
async def test_priority_filtering_excludes_contexts():
    """Verify priority 4 (EXCLUDED) contexts don't appear"""

    # Set testing to EXCLUDED
    await user_service.update_field_priorities(
        user_id=test_user.id,
        priorities={
            "product_core": 1,
            "testing": 4  # EXCLUDED
        }
    )

    # Configure testing (should be ignored)
    test_product.testing_config = {
        "coverage_target": 80,
        "frameworks": {"backend": ["pytest"]}
    }
    await db_session.commit()

    # Stage orchestrator
    job = await orch_service.create_orchestrator_job(...)
    context = await get_orchestrator_instructions(job.id, test_tenant)

    # BEHAVIOR: Testing config should NOT appear
    assert "testing" not in context["mission"].lower()
    assert "pytest" not in context["mission"]
    assert "coverage" not in context["mission"].lower()


@pytest.mark.asyncio
async def test_settings_persist_across_sessions():
    """Settings should survive database session boundaries"""

    # Configure settings
    await user_service.update_field_priorities(...)
    await product_service.update_github_integration(...)
    await db_session.commit()

    # Close session
    await db_session.close()

    # New session (simulates page refresh / server restart)
    new_session = get_new_db_session()
    new_user_service = UserService(new_session, tenant_key=test_tenant)
    new_product_service = ProductService(new_session, tenant_key=test_tenant)

    # Fetch settings
    user_refreshed = await new_user_service.get_user(test_user.id)
    product_refreshed = await new_product_service.get_product(test_product.id)

    # BEHAVIOR: Settings persisted
    assert user_refreshed.field_priority_config["priorities"] != {}
    assert product_refreshed.product_memory["git_integration"]["enabled"] is True
```

### 2. WebSocket Event Tests

```python
# tests/integration/test_websocket_events.py

@pytest.mark.asyncio
async def test_settings_changes_emit_websocket_events(websocket_mock):
    """All settings updates should emit WebSocket events for real-time UI"""

    with websocket_mock.capture_events(test_tenant):

        # Field priorities update
        await user_service.update_field_priorities(...)
        assert "settings:context_priorities_updated" in websocket_mock.events

        # GitHub integration toggle
        await product_service.update_github_integration(...)
        assert "settings:github_integration_updated" in websocket_mock.events

        # Project closure (360 memory update)
        await close_project_and_update_memory(...)
        assert "project:closed" in websocket_mock.events
        assert "product:memory_updated" in websocket_mock.events


@pytest.mark.asyncio
async def test_websocket_events_tenant_isolated(websocket_mock):
    """WebSocket events should only broadcast to correct tenant"""

    # Update settings for tenant_a
    service_a = UserService(db_session, tenant_key="tenant_a")
    await service_a.update_field_priorities(...)

    # BEHAVIOR: Only tenant_a receives event
    assert websocket_mock.tenant_received_event("tenant_a", "settings:context_priorities_updated")
    assert not websocket_mock.tenant_received_event("tenant_b", "settings:context_priorities_updated")
```

### 3. Agent Spawning Integration Tests

```python
# tests/integration/test_agent_spawning_with_context.py

@pytest.mark.asyncio
async def test_spawned_agent_receives_relevant_context():
    """Spawned agents should receive context relevant to their role"""

    # Configure full context
    await configure_all_settings(...)

    # Spawn implementer agent
    from src.giljo_mcp.tools.spawn_agent import spawn_agent_job

    impl_job = await spawn_agent_job(
        agent_type="implementer",
        agent_name="Feature Builder",
        mission="Implement authentication feature",
        project_id=test_project.id,
        tenant_key=test_tenant
    )

    # Get agent mission
    from src.giljo_mcp.tools.get_agent_mission import get_agent_mission
    agent_mission = await get_agent_mission(impl_job.id, test_tenant)

    # BEHAVIOR: Agent receives relevant context
    assert "Implement authentication feature" in agent_mission  # Original mission
    assert "serena" in agent_mission.lower()  # Serena tools
    assert "send_message" in agent_mission  # Communication tools
    assert "testing" in agent_mission.lower()  # Testing config

    # BEHAVIOR: Agent does NOT receive orchestration tools
    assert "spawn_agent_job" not in agent_mission
    assert "create_successor_orchestrator" not in agent_mission


@pytest.mark.asyncio
async def test_tester_agent_receives_full_testing_config():
    """Tester agents should get complete testing configuration"""

    # Configure testing standards
    test_product.testing_config = {
        "coverage_target": 90,  # Higher for testers
        "frameworks": {"backend": ["pytest", "coverage"]}
    }

    # Spawn tester agent
    tester_job = await spawn_agent_job(
        agent_type="tester",
        agent_name="Quality Enforcer",
        mission="Test authentication feature"
    )

    tester_mission = await get_agent_mission(tester_job.id, test_tenant)

    # BEHAVIOR: Full testing config for tester
    assert "90" in tester_mission or "90%" in tester_mission
    assert "coverage" in tester_mission.lower()
    assert "tdd" in tester_mission.lower()
```

### 4. Multi-Tenant Isolation Tests

```python
# tests/integration/test_multi_tenant_isolation.py

@pytest.mark.asyncio
async def test_complete_tenant_isolation_across_all_features():
    """All features must enforce tenant isolation"""

    # Create two tenants with different settings

    # Tenant A: Full context enabled
    service_a = UserService(db_session, tenant_key="tenant_a")
    product_a = await create_test_product("tenant_a", name="Product A")
    await service_a.update_field_priorities(user_a.id, {
        "priorities": {"testing": 1}  # Testing enabled
    })

    # Tenant B: Testing excluded
    service_b = UserService(db_session, tenant_key="tenant_b")
    product_b = await create_test_product("tenant_b", name="Product B")
    await service_b.update_field_priorities(user_b.id, {
        "priorities": {"testing": 4}  # Testing EXCLUDED
    })

    # Stage orchestrators for both tenants
    job_a = await orch_service_a.create_orchestrator_job(...)
    job_b = await orch_service_b.create_orchestrator_job(...)

    context_a = await get_orchestrator_instructions(job_a.id, "tenant_a")
    context_b = await get_orchestrator_instructions(job_b.id, "tenant_b")

    # BEHAVIOR: Tenant A has testing config
    assert "testing" in context_a["mission"].lower()

    # BEHAVIOR: Tenant B does NOT have testing config
    assert "testing" not in context_b["mission"].lower()

    # BEHAVIOR: Product names are tenant-isolated
    assert "Product A" in context_a["mission"]
    assert "Product B" not in context_a["mission"]

    assert "Product B" in context_b["mission"]
    assert "Product A" not in context_b["mission"]


@pytest.mark.asyncio
async def test_cross_tenant_data_access_blocked():
    """Tenant A cannot access Tenant B's data"""

    # Tenant A service tries to access Tenant B's product
    service_a = ProductService(db_session, tenant_key="tenant_a")

    result = await service_a.get_product(product_b.id)

    # BEHAVIOR: Access denied (product not found for this tenant)
    assert result["success"] is False
    assert "not found" in result["error"].lower()
```

### 5. Performance Tests

```python
# tests/integration/test_performance.py

@pytest.mark.asyncio
async def test_orchestrator_context_generation_performance():
    """Context generation should complete within reasonable time"""

    import time

    # Configure maximum context (all priorities set to 1)
    await configure_maximum_context(...)

    # Measure context generation time
    start = time.time()

    job = await orch_service.create_orchestrator_job(...)
    context = await get_orchestrator_instructions(job.id, test_tenant)

    elapsed = time.time() - start

    # BEHAVIOR: Context generation < 2 seconds
    assert elapsed < 2.0, f"Context generation took {elapsed:.2f}s (target: <2s)"

    # BEHAVIOR: Reasonable token count
    assert context["estimated_tokens"] < 20000, "Estimated tokens too high"


@pytest.mark.asyncio
async def test_settings_persistence_performance():
    """Settings updates should be fast"""

    import time

    start = time.time()

    await user_service.update_field_priorities(...)
    await product_service.update_github_integration(...)

    elapsed = time.time() - start

    # BEHAVIOR: Settings save < 500ms
    assert elapsed < 0.5, f"Settings persistence took {elapsed:.2f}s (target: <0.5s)"


@pytest.mark.asyncio
async def test_no_memory_leaks_in_long_session():
    """Repeated operations should not leak memory"""

    import psutil
    import os

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Perform 100 orchestrator creations
    for i in range(100):
        job = await orch_service.create_orchestrator_job(...)
        context = await get_orchestrator_instructions(job.id, test_tenant)
        # Simulate cleanup
        await db_session.rollback()

    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    # BEHAVIOR: Memory increase < 50MB for 100 operations
    assert memory_increase < 50, f"Memory leak detected: {memory_increase:.2f}MB increase"
```

### 6. Error Handling Tests

```python
# tests/integration/test_error_handling.py

@pytest.mark.asyncio
async def test_graceful_handling_of_missing_product():
    """System should handle missing product gracefully"""

    # Try to stage orchestrator for non-existent product
    result = await orch_service.create_orchestrator_job(
        project_id="non-existent-project-id",
        user_id=test_user.id
    )

    # BEHAVIOR: Returns error, doesn't crash
    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_partial_context_when_some_missing():
    """System should include available context even if some parts missing"""

    # Product with no testing config, no 360 memory, GitHub disabled
    minimal_product = await create_minimal_product()

    # Stage orchestrator
    job = await orch_service.create_orchestrator_job(...)
    context = await get_orchestrator_instructions(job.id, test_tenant)

    # BEHAVIOR: Partial context still works
    assert context["mission"]  # Not empty
    assert "product" in context["mission"].lower()  # Has product context

    # Missing parts gracefully omitted
    assert "360 memory" not in context["mission"].lower()


@pytest.mark.asyncio
async def test_invalid_field_priorities_rejected():
    """Invalid priority values should be rejected"""

    result = await user_service.update_field_priorities(
        user_id=test_user.id,
        priorities={
            "product_core": 5,  # Invalid (must be 1-4)
            "testing": 0        # Invalid (must be 1-4)
        }
    )

    # BEHAVIOR: Validation error
    assert result["success"] is False
    assert "priority" in result["error"].lower()
```

---

## Test Execution Plan

### Phase 1: Unit Tests (Already Created in 0266-0271)
```bash
pytest tests/services/ -v --cov=src/giljo_mcp/services
pytest tests/unit/ -v
```

### Phase 2: Integration Tests (This Handover)
```bash
pytest tests/integration/test_complete_context_flow.py -v
pytest tests/integration/test_websocket_events.py -v
pytest tests/integration/test_agent_spawning_with_context.py -v
pytest tests/integration/test_multi_tenant_isolation.py -v
pytest tests/integration/test_performance.py -v
pytest tests/integration/test_error_handling.py -v
```

### Phase 3: Coverage Report
```bash
pytest tests/ --cov=src/giljo_mcp --cov-report=html --cov-report=term
# Target: >90% coverage for modified code
```

### Phase 4: E2E Manual Testing
```bash
# 1. Start server
python startup.py --dev

# 2. Login to UI
# 3. Configure all settings (priorities, GitHub, testing)
# 4. Close a project (create 360 memory)
# 5. Stage new orchestrator
# 6. Verify context in Claude Code
```

---

## Success Criteria

**This handover is complete when**:

### Functional Requirements
- ✅ Complete context flow test passing (all 6 handovers integrated)
- ✅ Settings persistence verified across sessions
- ✅ WebSocket events emit and broadcast correctly
- ✅ Spawned agents receive role-appropriate context
- ✅ Multi-tenant isolation enforced across all features
- ✅ Priority filtering works (1-4 levels)

### Quality Requirements
- ✅ >90% code coverage for context wiring code
- ✅ All integration tests passing (40+ tests)
- ✅ Performance targets met (<2s context generation, <500ms settings)
- ✅ No memory leaks detected
- ✅ Error handling comprehensive

### Documentation Requirements
- ✅ Test suite documented
- ✅ Coverage report generated
- ✅ Integration test patterns documented

---

## Test File Structure

```
tests/
├── conftest.py                           # Shared fixtures
├── unit/                                 # Unit tests (0266-0271)
│   ├── test_serena_instruction_generator.py
│   ├── test_memory_instruction_generator.py
│   ├── test_mcp_tool_catalog.py
│   └── test_testing_config_generator.py
├── services/                             # Service tests (0266-0271)
│   ├── test_user_service.py
│   ├── test_product_service.py
│   └── test_git_service.py
└── integration/                          # Integration tests (THIS HANDOVER)
    ├── test_complete_context_flow.py     # Full E2E flow
    ├── test_websocket_events.py          # Real-time updates
    ├── test_agent_spawning_with_context.py
    ├── test_multi_tenant_isolation.py
    ├── test_performance.py
    └── test_error_handling.py
```

---

## Common Issues & Troubleshooting

### Issue 1: Test Database Not Clean

```bash
# Drop and recreate test database
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp_test;"
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "CREATE DATABASE giljo_mcp_test;"

# Run migrations
python install.py --test-db
```

### Issue 2: Integration Tests Failing

**Debug Strategy**:
1. Run failing test in isolation: `pytest tests/integration/test_x.py::test_y -v`
2. Add debugging: `pytest tests/integration/test_x.py::test_y -v -s`  # See print output
3. Check database state after test
4. Verify WebSocket mock working

### Issue 3: Performance Tests Failing

**Common Causes**:
- Database not indexed properly
- Too much test data
- Caching not working
- Network latency

**Solutions**:
- Run: `pytest tests/integration/test_performance.py -v --benchmark`
- Profile slow tests: `pytest --profile`
- Check query performance: `EXPLAIN ANALYZE` in psql

---

## Git Commit Message

```
test: Add comprehensive integration test suite (Handover 0272)

Complete integration testing for context wiring system (Handovers 0266-0271).

Test Coverage:
- Complete context flow (UI → DB → Orchestrator)
- Settings persistence across sessions
- WebSocket event propagation
- Agent spawning with role-appropriate context
- Multi-tenant isolation across all features
- Performance benchmarks
- Error handling and edge cases

Test Metrics:
- 45 integration tests added
- 92% code coverage for context wiring
- All performance targets met:
  - Context generation: <2s
  - Settings persistence: <500ms
  - No memory leaks in 100-iteration test

Test Categories:
1. Complete context flow (6 tests)
2. WebSocket events (4 tests)
3. Agent spawning (8 tests)
4. Multi-tenant isolation (6 tests)
5. Performance (5 tests)
6. Error handling (8 tests)

Closes: #272

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Next Steps After Completion

1. **Code Review**: Review all 7 handovers (0266-0272) as a series
2. **Documentation**: Update docs/ORCHESTRATOR.md with complete flow diagram
3. **Performance Optimization**: Profile and optimize any slow paths
4. **Monitoring**: Add production monitoring for context generation time
5. **User Training**: Create user guide for context configuration UI

---

**End of Handover 0272 - Comprehensive Integration Test Suite**
