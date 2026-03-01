# Handover 0497b: Persist Agent Completion Results + Auto-Message to Orchestrator

**Date:** 2026-02-25
**From Agent:** Research/Architecture Session
**To Agent:** database-expert + tdd-implementor
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** COMPLETE (2026-02-25)
**Chain:** 0497a → **0497b** → 0497c → 0497d → 0497e (Multi-Terminal Production Parity)
**Depends On:** None (independent DB + service change)

## Task Summary

When an agent calls `complete_job(job_id, result={"summary": "...", "artifacts": [...]})`, the `result` dict is validated but **never stored** — it's thrown away. This means there's no record of what an agent accomplished, which breaks recovery flows (spawning a successor to fix issues found by a tester). Fix this by: (1) persisting the result dict, and (2) auto-generating a completion message from the agent to the orchestrator on the backend, eliminating redundant token usage.

## Context and Background

### Current State
In `orchestration_service.py:2327-2569`, the `complete_job()` method:
- Validates `result` is a non-empty dict (line ~2357)
- Transitions `AgentExecution.status` to "complete"
- Sets `completed_at` and `progress = 100`
- Broadcasts WebSocket event
- **NEVER stores the `result` dict anywhere**

The docstring literally says: `result: Job result data dict (for backwards compatibility, not currently used)`

### Why This Matters
In multi-terminal mode:
- The orchestrator needs to know what each agent accomplished
- If a tester finds problems, a fresh successor agent needs to read what the original implementer did
- Currently the only traces are git commits (if git is enabled) and TodoWrite items
- There's no structured summary of agent work

### The Design
1. Add a `result` JSON column to `AgentExecution` (not AgentJob — results are per-execution, not per-work-order)
2. Store the result dict in `complete_job()`
3. After storing, auto-generate a backend message from the completing agent to the orchestrator containing the result summary — this eliminates double-token-spend (agent doesn't need to call both `complete_job()` AND `send_message()` with the same data)
4. Add an MCP tool or extend existing tool to read completion results

### Git References
- `complete_job()`: `orchestration_service.py:2327-2569`
- AgentExecution model: `src/giljo_mcp/models/agent_identity.py:135-298`
- Message model: `src/giljo_mcp/models/tasks.py:117-163` — **NOTE: no `from_agent` column; sender stored in `meta_data["_from_agent"]` JSONB**
- WebSocket broadcast pattern: See `complete_job()` existing broadcast at end of method

## Technical Details

### Files to Modify

**`src/giljo_mcp/models/agent_identity.py`** — Add column to AgentExecution:
```python
# After messages_read_count (line ~258)
result = Column(
    JSON,
    nullable=True,
    comment="Structured completion result from agent (summary, artifacts, commits)",
)
```

**`migrations/versions/`** — Create new Alembic migration:
- The project uses Alembic exclusively (NOT raw ALTER TABLE in install.py)
- Follow the existing idempotent pattern from `f2a3b4c5d678_0411a_add_phase_to_agent_jobs.py`:
```python
def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :col"
    ), {"table": table_name, "col": column_name})
    return result.fetchone() is not None

def upgrade() -> None:
    conn = op.get_bind()
    if not _column_exists(conn, "agent_executions", "result"):
        op.add_column("agent_executions", sa.Column("result", sa.JSON(), nullable=True,
            comment="Structured completion result from agent (summary, artifacts, commits)"))
```

**`src/giljo_mcp/services/orchestration_service.py`** — `complete_job()` method:
1. After status transition (around line 2480), store the result:
   ```python
   execution.result = result
   ```
2. Auto-create completion message to orchestrator. **IMPORTANT implementation notes:**

   **The Message model has NO `from_agent` column.** The sender is stored in `meta_data["_from_agent"]` (JSONB). See `message_service.py:264` for the pattern.

   **Two approaches for message creation:**
   - **Option A (Recommended):** Use `self._message_service.send_message()` which handles counter updates (`messages_waiting_count` on recipient, `messages_sent_count` on sender) and WebSocket broadcasts automatically. The `OrchestrationService` already has `self._message_service` (line 996).
   - **Option B:** Direct `session.add(Message(...))` but you MUST manually update `messages_waiting_count` on the orchestrator's AgentExecution and `messages_sent_count` on the completing agent. Missing these counters = silent messages (no UI badge update).

   **Note:** `report_progress()` at line 2276 has a comment "DO NOT use MessageService.send_message()" — that warning is specific to progress reports, NOT completion reports. For `complete_job()`, creating a message IS the desired behavior.

   ```python
   # Auto-generate completion message to orchestrator
   # Must happen INSIDE the async with self._get_session() block, before session closes
   if job.project_id:
       orchestrator_exec = await self._find_orchestrator_execution(session, job.project_id, tenant_key)
       if orchestrator_exec and orchestrator_exec.agent_id != execution.agent_id:
           summary = result.get("summary", "Work completed")
           auto_message = Message(
               tenant_key=tenant_key,
               project_id=str(job.project_id),
               meta_data={"_from_agent": str(execution.agent_id), "job_id": str(job.project_id)},
               to_agents=[orchestrator_exec.agent_id],
               content=f"COMPLETION REPORT from {execution.agent_display_name}: {summary}",
               message_type="completion_report",
               status="pending",
           )
           session.add(auto_message)
           # Update counters manually if using direct session.add
           orchestrator_exec.messages_waiting_count = (orchestrator_exec.messages_waiting_count or 0) + 1
           execution.messages_sent_count = (execution.messages_sent_count or 0) + 1
           await session.commit()
   ```

   **Session lifecycle note:** This message creation MUST happen inside the existing `async with self._get_session()` block. The session closes when the context manager exits, so you cannot create the message "after commit" — do it before the final commit, or commit twice within the same session block.

3. Add helper method `_find_orchestrator_execution()` to find the active orchestrator for a project. Use the existing pattern: orchestrators are identified by `agent_display_name == "orchestrator"` (see line 2494 in `complete_job()`).

**`src/giljo_mcp/services/orchestration_service.py`** — Add `get_agent_result()` method:
```python
async def get_agent_result(self, job_id: str, tenant_key: str) -> Optional[dict]:
    """Fetch the completion result for a given job's latest execution."""
```
This allows successor agents to read what their predecessor accomplished.

**MCP Tool exposure** — Check if `get_workflow_status()` already returns per-agent data. If so, include `result` in its response. If not, expose `get_agent_result()` as a new MCP tool via `tool_accessor.py`.

### Response Model Updates

**`src/giljo_mcp/schemas/service_responses.py`** — Update `CompleteJobResult`:
- Add `result_stored: bool = True` field to confirm storage

### WebSocket Event Enhancement
The existing `agent:status_changed` broadcast for completion should include a `has_result: true` flag so the frontend knows a result summary is available.

## Implementation Plan

### Phase 1: Database Migration (database-expert)
1. Add `result` JSON column to AgentExecution model
2. Create new Alembic migration in `migrations/versions/` using the idempotent `_column_exists()` pattern
3. Test migration on fresh DB and existing DB (run `alembic upgrade head`)

### Phase 2: Write Tests (TDD)
1. Test `complete_job()` stores result dict in execution
2. Test auto-message created to orchestrator on completion
3. Test no auto-message when agent IS the orchestrator
4. Test `get_agent_result()` returns stored result
5. Test `get_agent_result()` returns None for incomplete jobs
6. Test tenant isolation on result reads

### Phase 3: Implement Storage + Auto-Message
1. Store `execution.result = result` in `complete_job()`
2. Implement `_find_orchestrator_execution()` helper
3. Create auto-message after commit
4. Add `get_agent_result()` service method

### Phase 4: MCP Tool Exposure
1. Check if `get_workflow_status()` can include results
2. If needed, add `get_agent_result` to tool_accessor.py
3. Register in MCP tool registry

**Recommended Sub-Agents:** database-expert (Phase 1), tdd-implementor (Phases 2-4)

## Testing Requirements

### Unit Tests
- `tests/services/test_complete_job_result.py` (new)
- Storage correctness, auto-message generation, tenant isolation, orchestrator exclusion

### Integration Tests
- Complete agent → verify result in DB
- Complete agent → verify message to orchestrator created
- Successor agent calls `get_agent_result()` → reads predecessor's work

## Dependencies and Blockers
- **None** — independent of 0497a (can be implemented in parallel)
- Migration must run before service changes

## Success Criteria
- `complete_job()` persists the `result` dict to `AgentExecution.result`
- Auto-message created to orchestrator on agent completion (not for orchestrator self-completion)
- `get_agent_result()` retrieves stored results with tenant isolation
- Alembic migration is idempotent (safe for fresh + upgrade installs)
- Zero lint issues, all tests pass

## Rollback Plan
- Column addition is additive — no data loss on rollback
- `git revert` removes service logic; column remains harmless (nullable JSON)

## Cascading Analysis
- **Downstream**: AgentExecution gets a new nullable column — no breaking changes
- **Upstream**: No impact on AgentJob, Project, or Product
- **Sibling**: Message auto-creation follows existing Message model patterns. New `message_type="completion_report"` is safe — `message_type` is String(50) with no CheckConstraint, and `receive_messages` does not filter by type.
- **Installation**: Alembic migration required (idempotent ADD COLUMN in `migrations/versions/`)

---

## Completion Summary

### 2026-02-25 - Reconciliation Closeout
**Status:** COMPLETE

**Implementation commit:** `15aad66a` feat(0497a+0497b): Thin agent prompt + completion result storage (combined with 0497a)

**What was built:**
- `result` JSON column added to AgentExecution model
- `complete_job()` persists the result dict
- Auto-generated completion message from agent to orchestrator on job completion
- `get_agent_result()` MCP tool for reading stored results with tenant isolation
- Alembic migration for the new column
