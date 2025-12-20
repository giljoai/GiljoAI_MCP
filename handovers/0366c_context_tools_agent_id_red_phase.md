# Handover 0366c - Context Tools agent_id RED Phase

**Status**: RED Phase Complete ✅
**Date**: 2025-12-20
**Phase**: C of Agent Identity Refactor Series

## Objective

Write failing tests for `src/giljo_mcp/tools/context.py` to enforce new semantic parameter naming using `agent_id` (executor-specific context tracking).

## Semantic Principles

### Key Distinction
- **`job_id`** = Work order UUID (the WHAT - persistent across succession)
- **`agent_id`** = Executor UUID (the WHO - specific instance)

### Why agent_id for Context Tools?
Context tools should use `agent_id` because:
1. Each agent EXECUTION has its own context window (`context_used`, `context_budget`)
2. Context tracking is per-executor, not per-job
3. Multiple executions on same job have independent context windows
4. Succession creates NEW executor with fresh context window

## Tests Created

**File**: `tests/tools/test_context_0366c.py`

### Test Coverage (6 tests, all failing as expected)

1. **test_fetch_context_uses_agent_id**
   - Verifies `fetch_context(agent_id=...)` parameter signature
   - Expected failure: `ImportError: cannot import name 'fetch_context'`

2. **test_context_tracking_updates_agent_execution**
   - Verifies context tracking updates `AgentExecution.context_used`
   - Expected failure: `ImportError: cannot import name 'update_context_usage'`

3. **test_multiple_executions_independent_context**
   - Verifies multiple executions on same job have independent context windows
   - Tests succession scenario (executor 1 vs executor 2)
   - Expected failure: `ImportError: cannot import name 'fetch_context'`

4. **test_get_context_history_includes_both_ids**
   - Verifies response includes both `agent_id` (WHO) and `job_id` (WHAT)
   - Expected failure: `ImportError: cannot import name 'get_context_history'`

5. **test_context_multi_tenant_isolation**
   - Verifies multi-tenant security boundary enforcement
   - Expected failure: `ImportError: cannot import name 'fetch_context'`

6. **test_context_succession_tracking**
   - Verifies succession chain tracking with context resets
   - Tests 3-executor succession chain
   - Expected failure: `ImportError: cannot import name 'get_succession_context'`

## Test Execution Results

```bash
$ pytest tests/tools/test_context_0366c.py -v --tb=short

FAILED tests/tools/test_context_0366c.py::test_fetch_context_uses_agent_id
FAILED tests/tools/test_context_0366c.py::test_context_tracking_updates_agent_execution
FAILED tests/tools/test_context_0366c.py::test_multiple_executions_independent_context
FAILED tests/tools/test_context_0366c.py::test_get_context_history_includes_both_ids
FAILED tests/tools/test_context_multi_tenant_isolation
FAILED tests/tools/test_context_0366c.py::test_context_succession_tracking

============================== 6 failed in 7.01s ==============================
```

## Functions to Implement (GREEN Phase)

Phase D will implement these functions in `src/giljo_mcp/tools/context.py`:

1. **`fetch_context(agent_id, tenant_key, categories)`**
   - Fetch context for specific agent execution
   - Returns: `{agent_id, job_id, context_used, context_budget, context}`

2. **`update_context_usage(agent_id, tenant_key, tokens_used)`**
   - Update `AgentExecution.context_used` incrementally
   - Auto-updates `last_progress_at` timestamp
   - Returns: `{agent_id, context_used, context_budget}`

3. **`get_context_history(agent_id, tenant_key)`**
   - Get context usage history for agent execution
   - Returns: `{agent_id, job_id, agent_type, instance_number, context_history}`

4. **`get_succession_context(agent_id, tenant_key)`**
   - Get full succession chain with context windows
   - Returns: `{agent_id, job_id, instance_number, succession_chain[]}`

## Current State Analysis

### context.py Current Implementation
- **Uses**: `tenant_key` and `project_id` for context retrieval
- **No agent_id support**: All tools work at project/product level
- **No execution-specific tracking**: Context not tracked per-executor

### Required Changes (Phase D)
1. Add new functions listed above
2. Query `AgentExecution` table instead of `Project` table
3. Use `agent_id` as primary parameter (not `project_id`)
4. Track context usage in `AgentExecution.context_used` column
5. Support succession chain queries via `spawned_by`/`succeeded_by` links

## Database Schema Alignment

### AgentExecution Columns Used
```python
agent_id              # Primary key (executor UUID)
job_id                # Foreign key to AgentJob (work order UUID)
tenant_key            # Multi-tenant isolation
context_used          # Current context window usage (tokens)
context_budget        # Maximum context window (tokens)
last_progress_at      # Timestamp of last activity
spawned_by            # Parent executor agent_id
succeeded_by          # Successor executor agent_id
instance_number       # Succession instance (1, 2, 3...)
```

## Next Steps (Phase D - GREEN)

1. Read existing context.py implementation patterns
2. Implement 4 new functions following TDD approach
3. Ensure all tests pass
4. Verify multi-tenant isolation
5. Test succession chain tracking

## Files Modified

- **Created**: `tests/tools/test_context_0366c.py` (6 failing tests)
- **Created**: `handovers/0366c_context_tools_agent_id_red_phase.md` (this file)

## Success Criteria

✅ All 6 tests fail with expected ImportError
✅ Tests enforce semantic parameter naming (agent_id not job_id)
✅ Tests verify multi-tenant isolation
✅ Tests verify succession chain tracking
✅ Tests verify independent context windows per executor

## RED Phase Status: COMPLETE

All tests failing as expected. Ready for Phase D (GREEN - implementation).

---

**Handover Chain**: 0366a (Models) → 0366b (Service Layer) → **0366c (Context RED)** → 0366d (Context GREEN)
