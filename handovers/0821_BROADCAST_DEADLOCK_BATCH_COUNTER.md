# 0821: Broadcast Deadlock Fix -- Batch Counter UPDATE

**Edition Scope:** CE
**Date:** 2026-03-15
**Status:** COMPLETE

## Problem

Alpha agent testing exposed a PostgreSQL deadlock (SQLSTATE 40P01) during concurrent broadcast messages. Two broadcasts locking `agent_executions` counter rows in different orders cause a circular wait. The system self-recovered via retry (~27s delay) but this is a latent production risk flagged in 360 memory entries #28/#29.

**Root cause:** In `_handle_send_message_side_effects()`, the sender's `sent_count` was updated FIRST (locking the sender row), then each recipient's `waiting_count` was updated one-by-one in sorted order. When one broadcast's sender is another broadcast's recipient, the lock ordering breaks and a circular wait occurs.

## Solution

Replace N+1 per-row UPDATEs with a single SQL UPDATE statement using CASE expressions. One statement = PostgreSQL handles all lock acquisition internally = no cross-statement deadlock.

## Changes

### 1. `src/giljo_mcp/repositories/message_repository.py`
- Added `batch_update_counters()` method using `sqlalchemy.case()` to batch both `sent_count` and `waiting_count` updates into one UPDATE statement
- Added `case` to sqlalchemy imports

### 2. `src/giljo_mcp/services/message_service.py`
- Refactored `_handle_send_message_side_effects()`: replaced individual `increment_sent_count` + N x `increment_waiting_count` calls with a single `batch_update_counters()` call
- Builds `sent_increments` and `waiting_increments` dicts, passes to batch method

### 3. `src/giljo_mcp/services/orchestration_service.py`
- Refactored `complete_job()` auto-completion message counters: replaced two separate `session.execute(update(...))` statements with `MessageRepository.batch_update_counters()`
- Removed unused `update` import from sqlalchemy

### 4. `src/giljo_mcp/repositories/agent_job_repository.py`
- Removed rogue `session.commit()` from `decrement_waiting_increment_read()` -- repositories should not commit, that's the caller's responsibility

### 5. `tests/unit/test_broadcast_deadlock_retry.py`
- Added `TestBatchUpdateCounters` class (6 tests): single sent+waiting, empty dicts, overlapping agent IDs, multiple recipients, waiting-only, sent-only
- Added `TestSendPathBatchIntegration` class (1 test): verifies `_handle_send_message_side_effects` calls `batch_update_counters` with correct args
- All 20 tests pass

## Verification

```
pytest tests/unit/test_broadcast_deadlock_retry.py -v           # 20 passed
pytest tests/services/test_message_counter_atomic_self_healing.py -v  # 9 passed
pytest tests/services/test_broadcast_self_exclusion.py -v       # 5 passed
pytest tests/services/test_message_service_contract.py -v       # 5 passed
ruff check src/ api/                                            # All checks passed
```
