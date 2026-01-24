# Handover 0452: Delete orchestrator.py

**Created**: 2026-01-22
**Series**: Orchestrator/ToolAccessor Consolidation (0450-0453)
**Phase**: 3 of 4 (Purple - Cleanup)
**Risk Level**: HIGH

---

## Executive Summary

Delete `src/giljo_mcp/orchestrator.py` entirely. All functionality has been moved to OrchestrationService in handovers 0450-0451.

---

## Pre-Requisites

- [ ] Handover 0450 completed successfully (core logic moved)
- [ ] Handover 0451 completed successfully (inline code moved)
- [ ] All service tests passing
- [ ] MCP tools working via delegation

---

## File Impact Index

### FILE TO DELETE

`src/giljo_mcp/orchestrator.py` - 1,675 lines

### FILES TO UPDATE (Remove Dead Imports)

| File | Line | Action |
|------|------|--------|
| `src/giljo_mcp/tools/orchestration.py` | 27 | Remove unused import |
| `api/endpoints/orchestration.py` | 16, 30 | Remove import and `__all__` export |

### MODULES THAT BECOME ORPHANED

These modules are now imported by OrchestrationService (moved in 0450):
- `workflow_engine.py` - Now imported by OrchestrationService
- `agent_selector.py` - Now imported by OrchestrationService

Verify they're still reachable after deletion.

---

## Execution Plan

### Phase 1: Pre-Deletion Verification

Confirm all functionality works via new paths:

```bash
# Service layer tests
pytest tests/services/test_orchestration_service.py -v
pytest tests/services/test_orchestration_service_consolidation.py -v
pytest tests/services/test_orchestration_service_instructions.py -v

# MCP tool tests
pytest tests/tools/test_tool_accessor*.py -v

# Integration tests
pytest tests/integration/test_mcp_http.py -v
```

All must pass before proceeding.

### Phase 2: Delete orchestrator.py

```bash
rm src/giljo_mcp/orchestrator.py
```

### Phase 3: Fix Cascading Imports

**File 1: `src/giljo_mcp/tools/orchestration.py`**

```python
# REMOVE this line (line 27):
from src.giljo_mcp.orchestrator import ProjectOrchestrator
```

**File 2: `api/endpoints/orchestration.py`**

```python
# REMOVE this import (line 16):
from src.giljo_mcp.orchestrator import ProjectOrchestrator

# UPDATE __all__ (line 30):
# BEFORE: __all__ = ["router", "ProjectOrchestrator"]
# AFTER:
__all__ = ["router"]
```

### Phase 4: Run Tests - Expect Failures

```bash
pytest tests/ -v --tb=short > test_failures.txt 2>&1
```

**Expected Failures** (tests that directly import/use ProjectOrchestrator):

| Test File | Expected Failures | Fix Strategy |
|-----------|-------------------|--------------|
| `tests/unit/test_orchestrator.py` | ALL | DELETE file |
| `tests/unit/test_orchestrator_enhancement.py` | ALL | DELETE file |
| `tests/unit/test_phase5_orchestrator_product_validation.py` | ALL | DELETE file |
| `tests/test_orchestrator_*.py` (root) | ALL | DELETE files |
| `tests/integration/test_orchestration_workflow.py` | SOME | UPDATE to use service |
| `tests/performance/test_concurrent_agents.py` | SOME | UPDATE to use service |

### Phase 5: Delete Orphaned Test Files

```bash
# Delete tests for deleted module
rm tests/unit/test_orchestrator.py
rm tests/unit/test_orchestrator_enhancement.py
rm tests/unit/test_phase5_orchestrator_product_validation.py
rm tests/test_orchestrator_comprehensive.py
rm tests/test_orchestrator_final.py
rm tests/test_orchestrator_mission_integration.py
rm tests/test_orchestrator_routing.py
rm tests/test_real_integration.py
# ... (list all orchestrator test files)
```

### Phase 6: Update Remaining Tests

For tests that used ProjectOrchestrator but test integration behavior:

**BEFORE**:
```python
from src.giljo_mcp.orchestrator import ProjectOrchestrator
orchestrator = ProjectOrchestrator()
result = await orchestrator.process_product_vision(...)
```

**AFTER**:
```python
from src.giljo_mcp.services.orchestration_service import OrchestrationService
service = OrchestrationService(session, tenant_key)
result = await service.process_product_vision(...)
```

### Phase 7: Final Verification

```bash
# All tests should pass now
pytest tests/ -v

# Verify no orphaned references
grep -r "ProjectOrchestrator" src/ api/ tests/
# Should return NO MATCHES

grep -r "from.*orchestrator import" src/ api/ tests/
# Should return NO MATCHES (except this handover doc)
```

---

## Success Criteria

- [ ] `orchestrator.py` deleted
- [ ] No orphaned imports in codebase
- [ ] All remaining tests pass
- [ ] MCP tools work end-to-end
- [ ] `grep -r "ProjectOrchestrator"` returns no code matches
- [ ] workflow_engine.py and agent_selector.py still reachable

---

## Verification Commands

```bash
# Final test suite
pytest tests/ -v --tb=short

# Coverage check
pytest tests/ --cov=src/giljo_mcp --cov-report=term-missing

# Orphan check
grep -r "ProjectOrchestrator" src/ api/
grep -r "from.*orchestrator import" src/ api/

# Module reachability check
python -c "from giljo_mcp.services.orchestration_service import OrchestrationService; print('OK')"
python -c "from giljo_mcp.workflow_engine import WorkflowEngine; print('OK')"
python -c "from giljo_mcp.agent_selector import AgentSelector; print('OK')"
```

---

## Rollback Procedure

If this handover fails:
```bash
git checkout HEAD~1  # Restore orchestrator.py
git checkout HEAD~1 -- src/giljo_mcp/tools/orchestration.py
git checkout HEAD~1 -- api/endpoints/orchestration.py
```

---

## Next Handover

On successful completion, spawn terminal for **Handover 0453** (TDD test rewrite).

---

## Estimated Effort

- Pre-deletion verification: 30 minutes
- Deletion + import fixes: 30 minutes
- Test file deletion: 30 minutes
- Test updates: 1-2 hours
- Final verification: 30 minutes
- **Total**: 3-4 hours
