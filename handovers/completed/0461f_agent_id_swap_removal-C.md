# Handover 0461f: Agent ID Swap Code Removal (Remediation)

**Series**: Handover Simplification Series (0461)
**Color**: Cyan (#00BCD4)
**Estimated Effort**: 3-4 hours
**Subagents**: `tdd-implementor`, `backend-tester`
**Dependencies**: 0461e complete (remediation of incomplete work)

---

## Mission Statement

**Quality verification found critical issues**: Agent ID Swap code was NOT fully removed in the 0461 series. This handover completes the removal.

**Goal**: Remove all Agent ID Swap implementation code and update the MCP tool to use simple 360 Memory-based handover.

---

## Background

### What Was Found

The backend quality check revealed:

1. **orchestrator_succession.py:84-178** - `create_successor()` method still implements Agent ID Swap:
   - Creates new AgentExecution rows
   - Swaps agent IDs (old gets decomm-xxx)
   - Tracks instance_number

2. **orchestration_service.py:3339-3419** - `create_successor_orchestrator()` uses old pattern:
   - Exposed as MCP tool (agents can call it)
   - Creates NEW agent_id for successor
   - Sets status to "decommissioned"

3. **tool_accessor.py:676-680** - Exposes old MCP tool
4. **mcp_http.py:492,706** - Registers old MCP tool

### What Should Happen

Per Handover 0461 goals:
- NO new AgentExecution rows on handover
- NO agent ID swapping
- Write session context to 360 Memory
- Reset context_used to 0
- Return continuation prompt

---

## Tasks

### Task 1: Remove `create_successor()` from OrchestratorSuccessionManager

**File**: `src/giljo_mcp/orchestrator_succession.py`

**Action**: Delete the entire `create_successor()` method (lines 84-178, ~94 lines)

The method signature to delete:
```python
async def create_successor(
    self,
    current_execution: AgentExecution,
    reason: str,
) -> AgentExecution:
```

Also remove any docstring references to this method in the class docstring.

**Keep**: `generate_handover_summary()` and `complete_handover()` - these may still be useful for 360 Memory content generation.

### Task 2: Rewrite `create_successor_orchestrator()` in OrchestrationService

**File**: `src/giljo_mcp/services/orchestration_service.py`

**Current location**: Lines 3339-3419

**Action**: Rewrite to use simple 360 Memory pattern (NOT Agent ID Swap)

**New implementation**:
```python
async def create_successor_orchestrator(
    self, current_job_id: str, tenant_key: str, reason: str = "manual"
) -> dict[str, Any]:
    """
    Create successor orchestrator context via 360 Memory (Handover 0461f).

    SIMPLIFIED: No longer creates new AgentExecution rows or swaps IDs.
    Instead, writes session context to 360 Memory and resets context_used.

    Args:
        current_job_id: Current orchestrator job_id or agent_id
        tenant_key: Tenant key for isolation
        reason: Handover reason (default: "manual")

    Returns:
        Dict with success status, continuation instructions, and memory entry info
    """
    async with self._get_session() as session:
        # Find current execution
        query = select(AgentExecution).where(
            AgentExecution.agent_id == current_job_id,
            AgentExecution.tenant_key == tenant_key
        ).order_by(AgentExecution.instance_number.desc()).limit(1)

        result = await session.execute(query)
        execution = result.scalar_one_or_none()

        # Fallback to job_id
        if not execution:
            query = select(AgentExecution).where(
                AgentExecution.job_id == current_job_id,
                AgentExecution.tenant_key == tenant_key
            ).order_by(AgentExecution.instance_number.desc()).limit(1)
            result = await session.execute(query)
            execution = result.scalar_one_or_none()

        if not execution:
            raise ValueError(f"Execution not found for {current_job_id}")

        if execution.agent_display_name != "orchestrator":
            raise ValueError("Only orchestrators can use succession")

        # Get project_id from job
        job_query = select(AgentJob).where(AgentJob.job_id == execution.job_id)
        job_result = await session.execute(job_query)
        job = job_result.scalar_one_or_none()

        if not job:
            raise ValueError("Job not found")

        # Build session context
        session_context = {
            "context_used": execution.context_used,
            "context_budget": execution.context_budget,
            "progress": execution.progress,
            "current_task": execution.current_task,
            "agent_id": execution.agent_id,
            "job_id": execution.job_id,
            "reason": reason,
        }

        # Write to 360 Memory
        from src.giljo_mcp.tools.write_360_memory import write_360_memory

        memory_result = await write_360_memory(
            project_id=str(job.project_id),
            summary=f"Session handover ({reason}) at {execution.context_used}/{execution.context_budget} tokens.",
            key_outcomes=[f"Progress: {execution.progress}%", f"Task: {execution.current_task or 'N/A'}"],
            decisions_made=[f"Handover triggered: {reason}"],
            entry_type="session_handover",
            author_job_id=execution.job_id,
            tenant_key=tenant_key,
            metrics={"session_context": session_context}
        )

        # Reset context_used (same agent, fresh context)
        old_context = execution.context_used
        execution.context_used = 0
        await session.commit()

        self._logger.info(
            f"Simple succession: {execution.agent_id} context reset "
            f"({old_context} -> 0), reason: {reason}, memory_entry: {memory_result.get('entry_id')}"
        )

        # Return simplified response
        return {
            "success": True,
            "job_id": execution.job_id,
            "agent_id": execution.agent_id,  # SAME agent_id (no swap)
            "context_reset": True,
            "old_context_used": old_context,
            "new_context_used": 0,
            "memory_entry_id": memory_result.get("entry_id"),
            "reason": reason,
            "message": "Session context written to 360 Memory. Use fetch_context(categories=['memory_360']) in new session to retrieve.",
        }
```

### Task 3: Update tool_accessor.py

**File**: `src/giljo_mcp/tools/tool_accessor.py`

**Location**: Lines 676-680

**Action**: Update docstring to reflect new behavior:

```python
async def create_successor_orchestrator(
    self, current_job_id: str, tenant_key: str, reason: str = "manual"
) -> dict[str, Any]:
    """
    Create successor orchestrator context via 360 Memory (Handover 0461f).

    SIMPLIFIED: Writes session context to 360 Memory and resets context_used.
    No new AgentExecution rows created. Same agent_id continues.

    Use fetch_context(categories=['memory_360']) in new session to retrieve context.
    """
    return await self._orchestration_service.create_successor_orchestrator(
        current_job_id, tenant_key, reason
    )
```

### Task 4: Update MCP tool schema in mcp_http.py

**File**: `api/endpoints/mcp_http.py`

**Location**: Line 492 (tool definition)

**Action**: Update the tool description:

```python
{
    "name": "create_successor_orchestrator",
    "description": "Write session context to 360 Memory and reset context for continuation. Use in new session: fetch_context(categories=['memory_360']) to retrieve handover context.",
    "inputSchema": {
        # ... keep existing schema
    }
}
```

### Task 5: Fix Minor Issues in simple_handover.py

**File**: `api/endpoints/agent_jobs/simple_handover.py`

1. **Line 175**: Remove duplicate import of `api.app`
2. **Line 234**: Replace hardcoded URL with config:
   ```python
   # Before:
   mcp_url = "http://localhost:7272/mcp"

   # After:
   from src.giljo_mcp.config import get_config
   config = get_config()
   mcp_url = f"http://{config.get('host', 'localhost')}:{config.get('port', 7272)}/mcp"
   ```

### Task 6: Update 360_MEMORY_MANAGEMENT.md Schema

**File**: `docs/360_MEMORY_MANAGEMENT.md`

**Location**: Line 34 (schema definition)

**Action**: Add missing `metrics` column:
```python
metrics = Column(JSONB, nullable=True)  # For session_handover context
```

### Task 7: Remove OrchestratorSuccessionManager.create_successor References

Search and update any remaining references:

```bash
grep -r "succession_manager.create_successor\|OrchestratorSuccessionManager" src/ api/
```

Update or remove as needed. The class can remain but `create_successor()` must be deleted.

### Task 8: Write Integration Tests

**File**: `tests/api/test_create_successor_orchestrator.py` (NEW or update existing)

Add tests for the rewritten MCP tool:

```python
async def test_create_successor_orchestrator_writes_360_memory():
    """Verify MCP tool writes to 360 Memory instead of creating new execution."""
    # Call tool
    result = await tool_accessor.create_successor_orchestrator(job_id, tenant_key)

    # Verify NO new AgentExecution created
    executions = await get_executions_for_job(job_id)
    assert len(executions) == 1  # Still just one

    # Verify 360 Memory entry created
    entries = await get_memory_entries(project_id, entry_type="session_handover")
    assert len(entries) == 1

    # Verify context reset
    assert executions[0].context_used == 0

async def test_create_successor_orchestrator_same_agent_id():
    """Verify agent_id stays the same (no swap)."""
    original_agent_id = execution.agent_id

    result = await tool_accessor.create_successor_orchestrator(job_id, tenant_key)

    assert result["agent_id"] == original_agent_id  # SAME, not new
```

---

## Verification

After all tasks complete:

```bash
# 1. Verify create_successor deleted
grep -r "def create_successor\(" src/giljo_mcp/orchestrator_succession.py
# Should return nothing

# 2. Verify no Agent ID Swap references in active code
grep -r "Agent ID Swap\|decomm-\|decommissioned" src/giljo_mcp/services/orchestration_service.py
# Should only find comments/deprecation notes

# 3. Run tests
pytest tests/ -v -k "successor or handover"

# 4. Syntax check
python -m py_compile src/giljo_mcp/orchestrator_succession.py
python -m py_compile src/giljo_mcp/services/orchestration_service.py
python -m py_compile api/endpoints/agent_jobs/simple_handover.py
```

---

## Files Modified Summary

| File | Action | Lines Changed |
|------|--------|---------------|
| `src/giljo_mcp/orchestrator_succession.py` | DELETE method | -94 lines |
| `src/giljo_mcp/services/orchestration_service.py` | REWRITE method | ~80 lines |
| `src/giljo_mcp/tools/tool_accessor.py` | UPDATE docstring | ~10 lines |
| `api/endpoints/mcp_http.py` | UPDATE description | ~5 lines |
| `api/endpoints/agent_jobs/simple_handover.py` | FIX minor issues | ~10 lines |
| `docs/360_MEMORY_MANAGEMENT.md` | ADD column | ~5 lines |
| `tests/api/test_create_successor_orchestrator.py` | ADD tests | ~50 lines |

**Total**: ~7 files, ~160 lines net change

---

## Success Criteria

- [ ] `create_successor()` method DELETED from orchestrator_succession.py
- [ ] `create_successor_orchestrator()` rewritten to use 360 Memory
- [ ] MCP tool returns same agent_id (no swap)
- [ ] No new AgentExecution rows created on handover
- [ ] 360 Memory entry created with session_handover type
- [ ] context_used reset to 0
- [ ] Minor issues fixed (duplicate import, hardcoded URL, docs)
- [ ] Integration tests pass
- [ ] All syntax checks pass

---

## Rollback

If issues arise:
```bash
git checkout HEAD -- src/giljo_mcp/orchestrator_succession.py
git checkout HEAD -- src/giljo_mcp/services/orchestration_service.py
```

---

## Chain Log Update Required

Update `prompts/0461_chain/chain_log.json`:
- Add new session entry for 0461f
- Update chain_summary when complete
