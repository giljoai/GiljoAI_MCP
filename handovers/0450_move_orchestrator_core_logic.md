# Handover 0450: Move Core Logic from orchestrator.py to OrchestrationService

**Created**: 2026-01-22
**Series**: Orchestrator/ToolAccessor Consolidation (0450-0453)
**Phase**: 1 of 4 (Green - Foundation)
**Risk Level**: MEDIUM

---

## Executive Summary

Move the actively-used methods from `orchestrator.py` into `OrchestrationService`. This handover handles the heaviest migration - the `process_product_vision()` workflow and related methods.

---

## Pre-Requisites

- [ ] Database backup exists: `backups/db_backup_orchestrator_consolidation_*.dump`
- [ ] Working on branch: `_orchestrator_tool_accessor_consolidation`
- [ ] Master branch reference available for rollback

---

## File Impact Index

### SOURCE (orchestrator.py) - Methods to Move

| Method | Lines | Destination |
|--------|-------|-------------|
| `process_product_vision()` | 144 | OrchestrationService |
| `generate_mission_plan()` | ~30 | OrchestrationService |
| `select_agents_for_mission()` | ~40 | OrchestrationService |
| `coordinate_agent_workflow()` | ~50 | OrchestrationService |
| `spawn_agent()` | 177 | OrchestrationService |
| `_get_agent_template()` | ~40 | OrchestrationService |
| `_spawn_claude_code_agent()` | ~60 | OrchestrationService |
| `_spawn_generic_agent()` | ~40 | OrchestrationService |

### IMPORTS to Move

```python
from .workflow_engine import WorkflowEngine      # Only in orchestrator.py
from .agent_selector import AgentSelector        # Only in orchestrator.py
from .mission_planner import MissionPlanner      # Also in tool_accessor
from .context_management.chunker import VisionDocumentChunker
```

### TARGET (orchestration_service.py) - Additions

Estimated additions: ~600 lines (methods + imports + docstrings)

---

## TDD Execution Plan

### Phase 1: RED - Write Failing Tests First

Create test file: `tests/services/test_orchestration_service_consolidation.py`

```python
@pytest.mark.asyncio
async def test_process_product_vision_creates_project(db_session, test_tenant):
    """Test process_product_vision creates project and returns workflow result"""
    # Setup: Create product with vision
    # Act: Call orchestration_service.process_product_vision()
    # Assert: Project created, missions generated, agents selected

@pytest.mark.asyncio
async def test_spawn_agent_routes_by_template_tool(db_session, test_tenant):
    """Test spawn_agent routes to correct spawn method based on template.tool"""
    # Test Claude Code routing
    # Test Codex routing
    # Test Gemini routing

@pytest.mark.asyncio
async def test_coordinate_workflow_executes_agents(db_session, test_tenant):
    """Test coordinate_agent_workflow executes workflow via WorkflowEngine"""
    # Setup: Create agent configs
    # Act: Call coordinate_workflow
    # Assert: WorkflowEngine.execute_workflow called

@pytest.mark.asyncio
async def test_multi_tenant_isolation_enforced(db_session):
    """Test all new methods enforce tenant isolation"""
    # Create products in different tenants
    # Verify cross-tenant access blocked
```

Run tests - MUST FAIL (RED):
```bash
pytest tests/services/test_orchestration_service_consolidation.py -v
```

### Phase 2: GREEN - Implement in OrchestrationService

1. Add imports to `orchestration_service.py`:
```python
from giljo_mcp.workflow_engine import WorkflowEngine
from giljo_mcp.agent_selector import AgentSelector
from giljo_mcp.mission_planner import MissionPlanner
from giljo_mcp.context_management.chunker import VisionDocumentChunker
```

2. Add methods (copy from orchestrator.py, adapt to service pattern):
   - Change `self.db_manager` to `self.session`
   - Add `tenant_key` filtering
   - Return `dict[str, Any]` with success/error structure
   - Add WebSocket events

3. Fix the duplicate project bug:
   - `process_product_vision()` should accept optional `project_id` parameter
   - If `project_id` provided, use existing project instead of creating new

4. Run tests - MUST PASS (GREEN):
```bash
pytest tests/services/test_orchestration_service_consolidation.py -v
```

### Phase 3: REFACTOR - Polish

1. Add structured logging with metadata
2. Add comprehensive docstrings
3. Ensure WebSocket events fire for real-time UI
4. Run linting: `ruff src/giljo_mcp/services/orchestration_service.py`

---

## Update Callers (3 locations)

### 1. orchestration_service.py:orchestrate_project() (self-update)

**BEFORE** (line 482-485):
```python
from giljo_mcp.orchestrator import ProjectOrchestrator
orchestrator = ProjectOrchestrator()
result = await orchestrator.process_product_vision(...)
```

**AFTER**:
```python
# Now call internal method directly
result = await self.process_product_vision(...)
```

### 2. tools/orchestration.py (line 27) - Dead Import

**BEFORE**:
```python
from src.giljo_mcp.orchestrator import ProjectOrchestrator
```

**AFTER**:
```python
# Remove - this import is unused
```

### 3. api/endpoints/orchestration.py (lines 16, 30) - Re-export

**BEFORE**:
```python
from src.giljo_mcp.orchestrator import ProjectOrchestrator
__all__ = ["router", "ProjectOrchestrator"]
```

**AFTER**:
```python
# Remove ProjectOrchestrator from imports and __all__
# It will be deleted in handover 0452
__all__ = ["router"]
```

---

## Success Criteria

- [ ] All new tests pass (GREEN)
- [ ] `process_product_vision` works via OrchestrationService
- [ ] No duplicate project creation bug
- [ ] Workflow coordination works (WorkflowEngine called)
- [ ] Agent spawning routes correctly by template.tool
- [ ] Multi-tenant isolation enforced
- [ ] Existing tests still pass: `pytest tests/services/test_orchestration_service.py -v`

---

## Verification Commands

```bash
# Run new tests
pytest tests/services/test_orchestration_service_consolidation.py -v

# Run existing service tests
pytest tests/services/test_orchestration_service.py -v

# Run full test suite (expect some orchestrator tests to still work via old path)
pytest tests/ -v --tb=short

# Check coverage
pytest tests/services/ --cov=src/giljo_mcp/services/orchestration_service --cov-report=term-missing
```

---

## Rollback Procedure

If this handover fails:
```bash
git checkout master
# Database unchanged - no rollback needed
```

---

## Next Handover

On successful completion, spawn terminal for **Handover 0451** (tool_accessor inline code).

---

## Estimated Effort

- Tests (RED): 1-2 hours
- Implementation (GREEN): 2-3 hours
- Refactor & Polish: 1 hour
- **Total**: 4-6 hours
