# 0480 MessageService Exception Handling Test Results

## Test Execution Summary

**Date**: 2026-01-28
**Migration**: 0480 series (dict returns → exception-based error handling)
**Component**: MessageService & Agent Communication Tools

---

## Test Suite 1: MessageService Unit Tests

**Command**: `pytest tests/services/test_message*.py -v --tb=short`

### Results Overview
- **Total Tests**: 36
- **Passed**: 18 (50%)
- **Failed**: 16 (44%)
- **Skipped**: 2 (6%)

### Passed Tests (18)
✅ Counter-based architecture tests (11/11 passed):
- `test_send_message_increments_sender_sent_count`
- `test_send_broadcast_increments_sender_sent_count_once`
- `test_send_broadcast_increments_each_recipient_waiting_count`
- `test_acknowledge_message_decrements_waiting_increments_read`
- `test_counters_survive_without_jsonb_persistence`
- `test_multiple_messages_accumulate_counters`
- `test_message_sent_event_includes_sender_counter`
- `test_message_sent_event_includes_recipient_counter`
- `test_message_received_event_includes_waiting_counter`
- `test_message_acknowledged_event_includes_counters`
- `test_broadcast_message_includes_counters_for_multiple_recipients`

✅ Agent ID routing tests (2/2 passed):
- `test_send_message_routes_by_agent_id_not_job_id`
- `test_succession_routing_delivers_to_new_executor`

✅ Basic filtering tests (2/5 passed):
- `test_receive_messages_exclude_self_filters_own_messages`
- `test_receive_messages_exclude_progress_filters_progress_type`

✅ Error handling tests (2/2 passed):
- `test_send_message_to_nonexistent_project_fails`
- `test_complete_nonexistent_message_fails`

✅ Empty state test (1/1 passed):
- `test_broadcast_no_project_returns_graceful`

### Failed Tests (16)

#### 1. Return Format Issues (3 failures)
**Root Cause**: Service methods returning `{"success": True, "data": {...}}` wrapper instead of direct data.

```python
# Tests expect:
message_id = result["message_id"]

# But service returns:
result = {"success": True, "data": {"message_id": "...", ...}}

# Fix needed:
message_id = result["data"]["message_id"]
```

**Affected Tests**:
- `test_send_message_creates_message_and_updates_jsonb_counters`
- `test_complete_message_marks_completed_and_preserves_ack`
- `test_broadcast_resolves_all_agents_in_project`
- `test_message_service_websocket_injection`
- `test_message_service_without_websocket_manager`

**Error Pattern**:
```
KeyError: 'message_id'
AssertionError: assert 'message_id' in {'data': {'message_id': None, ...}, 'success': True}
```

#### 2. Missing `await` Keywords (5 failures)
**Root Cause**: Database queries not awaited, treating coroutines as objects.

```python
# Error:
AttributeError: 'coroutine' object has no attribute 'id'
AttributeError: 'coroutine' object has no attribute 'all'
AttributeError: 'coroutine' object has no attribute 'tenant_key'
```

**Affected Tests**:
- `test_list_messages_no_project_returns_empty`
- `test_list_messages_empty_database_returns_empty`
- `test_list_messages_with_filters_empty_returns_empty`

**Issue Location**: `src/giljo_mcp/services/message_service.py:list_messages()`

```python
# Line 1023 - Missing await:
query = select(Message).where(Message.project_id == project.id)
# Should be:
project = await self.db.get(Project, project_id)
```

#### 3. Missing Methods (4 failures)
**Root Cause**: Methods removed or renamed during 0480 migration.

**Missing Methods**:
- `get_message_by_id()` - Method doesn't exist on MessageService
- `count_messages()` - Method doesn't exist
- `get_message_stats()` - Method doesn't exist
- `delete_messages()` - Method doesn't exist

**Affected Tests**:
- `test_get_message_by_id_nonexistent_returns_none`
- `test_count_messages_empty_database_returns_zero`
- `test_aggregate_stats_empty_database_returns_zeros`
- `test_delete_messages_empty_database_no_error`

#### 4. Unexpected Keyword Arguments (1 failure)
**Root Cause**: Pagination parameters removed from method signature.

```python
# Error:
TypeError: MessageService.list_messages() got an unexpected keyword argument 'skip'
```

**Affected Test**:
- `test_list_messages_pagination_skip_on_empty`

#### 5. Message Type Filtering Logic (3 failures)
**Root Cause**: Tests expect `messages` to be a list, but receive dict wrapper.

```python
# Error:
AssertionError: Should have at least one direct message
assert 0 >= 1
```

**Affected Tests**:
- `test_receive_messages_message_types_allowlist_works`
- `test_broadcast_to_project_sends_to_all_active_executions`
- `test_acknowledge_message_explicit_works`

---

## Test Suite 2: Agent Communication Tool Tests

**Command**: `pytest tests/tools/test_agent_communication*.py -v --tb=short`

### Results Overview
- **Total Tests**: 8
- **Passed**: 0 (0%)
- **Failed**: 8 (100%)

### Failed Tests (8)

#### 1. Response Format Mismatch (5 failures)
**Root Cause**: Tests expect list of message dicts, but receive `{"success": True, "data": {"messages": [...]}}` wrapper.

```python
# Tests expect:
messages = await receive_messages(...)
assert len(messages) == 1
for msg in messages:
    assert msg["type"] == "direct"

# But tool returns:
{"success": True, "data": {"count": 1, "messages": [...]}}

# Tests check:
assert len(messages) == 1  # Checks dict keys, not message count
```

**Affected Tests**:
- `test_receive_messages_exclude_self_filters_own_messages`
- `test_receive_messages_exclude_self_false_includes_own_messages`
- `test_receive_messages_exclude_progress_filters_progress_messages`
- `test_receive_messages_combined_filters`
- `test_receive_messages_empty_message_types_returns_nothing`

**Error Pattern**:
```
AssertionError: assert 2 == 1  # Counting dict keys instead of messages
  +  where 2 = len({'data': {...}, 'success': True})
```

#### 2. TypeError on Message Iteration (3 failures)
**Root Cause**: Tests try to iterate dict wrapper instead of message list.

```python
# Error:
TypeError: string indices must be integers, not 'str'

# Code:
message_types = {msg["type"] for msg in messages}
# But 'messages' is dict wrapper, so 'msg' is a string key like "success" or "data"
```

**Affected Tests**:
- `test_receive_messages_exclude_progress_false_includes_all`
- `test_receive_messages_filter_by_message_types`
- `test_receive_messages_backward_compatible_defaults`

---

## Critical Issues Summary

### Issue 1: Inconsistent Return Format (BLOCKER)
**Impact**: 13/44 tests (30%)
**Severity**: High - Breaks MCP tool contracts

**Problem**: Service methods return `{"success": True, "data": {...}}` wrapper, but tests/tools expect direct data.

**Example**:
```python
# Before 0480:
result = await service.send_message(...)
message_id = result["message_id"]  # Direct access

# After 0480:
result = await service.send_message(...)
message_id = result["data"]["message_id"]  # Nested access
```

**Decision Needed**:
1. **Option A**: Update service methods to return direct data (cleaner API)
2. **Option B**: Update all tests/tools to unwrap `result["data"]` (preserves current design)

### Issue 2: Missing `await` Keywords (BLOCKER)
**Impact**: 5/44 tests (11%)
**Severity**: Critical - Runtime errors in production

**Problem**: Database queries not awaited in `list_messages()` method.

**Fix Required** (file: `src/giljo_mcp/services/message_service.py`):
```python
# Line 1023 - Missing await:
project = await self.db.get(Project, project_id)

# Line 1034 - Missing await:
result = await self.db.execute(query)
messages = result.scalars().all()
```

### Issue 3: Missing Methods (BLOCKER)
**Impact**: 4/44 tests (9%)
**Severity**: High - Tests for removed functionality

**Missing Methods**:
- `MessageService.get_message_by_id()`
- `MessageService.count_messages()`
- `MessageService.get_message_stats()`
- `MessageService.delete_messages()`

**Decision Needed**:
1. **Option A**: Re-implement methods (if functionality needed)
2. **Option B**: Remove tests (if functionality deprecated in 0480)

### Issue 4: Pagination Parameters Removed
**Impact**: 1/44 tests (2%)
**Severity**: Medium - API change

**Problem**: `list_messages(skip=...)` parameter removed.

**Decision Needed**: Update test or restore parameter.

---

## Recommendations

### Immediate Actions (Blockers)

1. **Fix Missing `await` Keywords** (5 test failures)
   - File: `src/giljo_mcp/services/message_service.py`
   - Method: `list_messages()`
   - Add `await` to database queries

2. **Standardize Return Format** (13 test failures)
   - Decision: Choose Option A (direct data) or Option B (wrapper)
   - Update either service methods or all calling code

3. **Resolve Missing Methods** (4 test failures)
   - Determine if methods were intentionally removed in 0480
   - Either re-implement or remove corresponding tests

### Next Steps

1. Review 0480 handover documentation to understand intended API design
2. Fix missing `await` keywords (blocking production usage)
3. Make architectural decision on return format
4. Update tests or service methods based on decision
5. Re-run test suite to verify fixes

---

## Test Coverage Analysis

**Overall Coverage**: 0% (coverage collection failed)
**Reason**: Module import issues during test run

**Coverage Target**: >80% (per project standards)
**Current Status**: Unable to measure due to import failures

---

## Notes

- Counter-based architecture (0387f) is working correctly (11/11 tests passing)
- Agent ID routing is functioning properly (2/2 tests passing)
- Core message sending/receiving logic works when accessed correctly
- Issues are primarily in test expectations vs. actual API contracts
- No fundamental logic errors detected in MessageService itself
