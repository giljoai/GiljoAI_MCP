# Handover 0451: Move tool_accessor.py Inline Code to Services

**Created**: 2026-01-22
**Series**: Orchestrator/ToolAccessor Consolidation (0450-0453)
**Phase**: 2 of 4 (Blue - Backend)
**Risk Level**: MEDIUM

---

## Executive Summary

Move the 4 inline implementations from `tool_accessor.py` to `OrchestrationService`. After this handover, tool_accessor.py becomes a pure delegation layer (~250 lines).

---

## Pre-Requisites

- [ ] Handover 0450 completed successfully
- [ ] All 0450 tests passing
- [ ] `process_product_vision` working via OrchestrationService

---

## File Impact Index

### SOURCE (tool_accessor.py) - Inline Methods to Move

| Method | Lines | Current State | Destination |
|--------|-------|---------------|-------------|
| `get_orchestrator_instructions` | ~270 | Inline DB logic | OrchestrationService |
| `create_successor_orchestrator` | ~100 | Inline DB logic | OrchestrationService |
| `check_succession_status` | ~50 | Inline DB logic | OrchestrationService |
| `update_agent_mission` | ~70 | Inline DB logic | OrchestrationService |

### TARGET STATE (tool_accessor.py)

After refactor, each method becomes 1-3 line delegation:

```python
async def get_orchestrator_instructions(self, job_id: str, tenant_key: str):
    return await self.orchestration_service.get_orchestrator_instructions(job_id, tenant_key)

async def create_successor_orchestrator(self, current_job_id: str, tenant_key: str, reason: str):
    return await self.orchestration_service.create_successor_orchestrator(current_job_id, tenant_key, reason)

async def check_succession_status(self, job_id: str, tenant_key: str):
    return await self.orchestration_service.check_succession_status(job_id, tenant_key)

async def update_agent_mission(self, job_id: str, tenant_key: str, mission: str):
    return await self.orchestration_service.update_agent_mission(job_id, tenant_key, mission)
```

---

## TDD Execution Plan

### Phase 1: RED - Write Failing Tests First

Create test file: `tests/services/test_orchestration_service_instructions.py`

```python
@pytest.mark.asyncio
async def test_get_orchestrator_instructions_returns_context(db_session, test_tenant):
    """Test get_orchestrator_instructions returns orchestrator context"""
    # Setup: Create orchestrator job
    # Act: Call service.get_orchestrator_instructions()
    # Assert: Returns instructions with product context

@pytest.mark.asyncio
async def test_create_successor_orchestrator_creates_job(db_session, test_tenant):
    """Test create_successor_orchestrator creates new orchestrator job"""
    # Setup: Create active orchestrator
    # Act: Call service.create_successor_orchestrator()
    # Assert: New job created, old job marked for succession

@pytest.mark.asyncio
async def test_check_succession_status_returns_threshold(db_session, test_tenant):
    """Test check_succession_status returns context usage vs threshold"""
    # Setup: Create orchestrator with context tracking
    # Act: Call service.check_succession_status()
    # Assert: Returns succession_needed flag and metrics

@pytest.mark.asyncio
async def test_update_agent_mission_updates_job(db_session, test_tenant):
    """Test update_agent_mission updates job mission field"""
    # Setup: Create agent job
    # Act: Call service.update_agent_mission()
    # Assert: Job.mission updated, WebSocket event fired
```

Run tests - MUST FAIL (RED):
```bash
pytest tests/services/test_orchestration_service_instructions.py -v
```

### Phase 2: GREEN - Implement in OrchestrationService

1. Copy logic from tool_accessor.py inline methods
2. Adapt to service pattern:
   - Use `self.session` instead of creating new sessions
   - Add `tenant_key` validation
   - Return `dict[str, Any]` with success/error structure
3. Add WebSocket events for real-time updates

Run tests - MUST PASS (GREEN):
```bash
pytest tests/services/test_orchestration_service_instructions.py -v
```

### Phase 3: Update tool_accessor.py to Delegate

Replace inline implementations with delegation calls:

```python
async def get_orchestrator_instructions(self, job_id: str, tenant_key: str):
    """Delegate to OrchestrationService"""
    return await self.orchestration_service.get_orchestrator_instructions(job_id, tenant_key)
```

### Phase 4: REFACTOR - Polish

1. Remove dead code from tool_accessor.py
2. Update docstrings to reflect delegation pattern
3. Run linting: `ruff src/giljo_mcp/tools/tool_accessor.py`

---

## Success Criteria

- [ ] All new tests pass (GREEN)
- [ ] `get_orchestrator_instructions` works via service delegation
- [ ] `create_successor_orchestrator` works via service delegation
- [ ] `check_succession_status` works via service delegation
- [ ] `update_agent_mission` works via service delegation
- [ ] tool_accessor.py reduced by ~490 lines
- [ ] MCP tools still work (test via curl or MCP client)

---

## Verification Commands

```bash
# Run new tests
pytest tests/services/test_orchestration_service_instructions.py -v

# Run tool_accessor tests (should still pass via delegation)
pytest tests/tools/test_tool_accessor*.py -v

# Verify MCP tools work end-to-end
pytest tests/integration/test_mcp_http.py -v

# Line count verification
wc -l src/giljo_mcp/tools/tool_accessor.py
# Should be ~1,100 lines (down from 1,580)
```

---

## Rollback Procedure

If this handover fails:
```bash
git checkout HEAD~1  # Undo this handover's commits
# Re-run 0450 verification to ensure still working
pytest tests/services/test_orchestration_service_consolidation.py -v
```

---

## Next Handover

On successful completion, spawn terminal for **Handover 0452** (delete orchestrator.py).

---

## Estimated Effort

- Tests (RED): 1 hour
- Implementation (GREEN): 1-2 hours
- Delegation update: 30 minutes
- **Total**: 2.5-3.5 hours
