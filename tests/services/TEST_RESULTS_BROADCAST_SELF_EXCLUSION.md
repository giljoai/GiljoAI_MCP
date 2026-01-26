# Broadcast Self-Exclusion Test Results

## Test Summary

**Test File**: `tests/services/test_broadcast_self_exclusion.py`
**Date**: 2026-01-25
**Status**: ✅ ALL TESTS PASSED
**Total Tests**: 5
**Passed**: 5
**Failed**: 0
**Execution Time**: 0.81 seconds

---

## Test Cases

### 1. ✅ test_broadcast_excludes_sender
**Purpose**: Verify that when Agent A sends a broadcast to `['all']`, Agent A does NOT receive the message.

**Scenario**:
- Agent A sends broadcast message to `['all']`
- Agent A's `messages_sent_count` increments by 1
- Agent A's `messages_waiting_count` remains 0 (self-exclusion)
- Agents B and C each have `messages_waiting_count` = 1

**Result**: PASSED

**Key Log Output**:
```
[FANOUT] Expanded broadcast to agent_id '76027b57-c6ee-49ff-baa6-c13f6a57b1ff'
[FANOUT] Expanded broadcast to agent_id '2f5f9da9-a46c-4301-a8ef-0b6edc9cce4c'
[COUNTER] Incremented sent_count for agent-a
[COUNTER] Updated counters: sender +1 sent, 2 recipients +1 waiting each
[WEBSOCKET DEBUG] Broadcast to all: 2 recipients (excluded sender: agent-a)
```

**Assertions Verified**:
- ✅ Agent A's `messages_sent_count` = 1
- ✅ Agent A's `messages_waiting_count` = 0 (NOT receiving own message)
- ✅ Agent B's `messages_waiting_count` = 1
- ✅ Agent C's `messages_waiting_count` = 1
- ✅ Only 2 messages created in database (not 3)
- ✅ Agent A's agent_id not in recipient list

---

### 2. ✅ test_broadcast_excludes_sender_by_agent_id
**Purpose**: Verify self-exclusion works when sender is identified by `agent_id` (UUID) instead of `agent_display_name`.

**Scenario**:
- Agent A sends broadcast using `from_agent=agent_a.agent_id` (UUID)
- System excludes sender by matching both `agent_display_name` and `agent_id`

**Result**: PASSED

**Code Coverage**: Tests alternate code path at `message_service.py:176-177`:
```python
if (execution.agent_display_name == sender_ref or
        execution.agent_id == sender_ref):
    continue
```

**Assertions Verified**:
- ✅ Agent A excluded when identified by agent_id
- ✅ Agents B and C receive the message

---

### 3. ✅ test_broadcast_with_multiple_messages_accumulates_correctly
**Purpose**: Verify that sending multiple broadcasts accumulates counters correctly.

**Scenario**:
- Agent A sends 3 broadcast messages
- Agent A's `messages_sent_count` = 3
- Agent A's `messages_waiting_count` = 0 (never receives own broadcasts)
- Agents B and C each have `messages_waiting_count` = 3

**Result**: PASSED

**Assertions Verified**:
- ✅ Agent A's `messages_sent_count` = 3 (accumulated)
- ✅ Agent A's `messages_waiting_count` = 0 (self-exclusion persists)
- ✅ Agent B's `messages_waiting_count` = 3
- ✅ Agent C's `messages_waiting_count` = 3

---

### 4. ✅ test_broadcast_from_different_agents
**Purpose**: Verify that each agent is excluded from their own broadcasts.

**Scenario**:
- Agent A broadcasts → Agents B and C receive, Agent A does not
- Agent B broadcasts → Agents A and C receive, Agent B does not
- Agent C broadcasts → Agents A and B receive, Agent C does not

**Result**: PASSED

**Assertions Verified**:
- ✅ Each agent sent 1 message (`messages_sent_count` = 1)
- ✅ Each agent received 2 messages (`messages_waiting_count` = 2)
- ✅ Each agent excluded from their own broadcast

**Cross-Agent Verification**:
- Agent A: sent=1, waiting=2 (received from B and C)
- Agent B: sent=1, waiting=2 (received from A and C)
- Agent C: sent=1, waiting=2 (received from A and B)

---

### 5. ✅ test_broadcast_to_empty_project_no_crash
**Purpose**: Verify that broadcasting to a project with no agents doesn't crash.

**Edge Case**: `['all']` expansion results in empty recipient list.

**Result**: PASSED

**Assertions Verified**:
- ✅ `send_message()` returns `success=True`
- ✅ `message_id` is `None` (no messages created)
- ✅ No messages created in database
- ✅ No crash or exception

---

## Implementation Details

### Code Under Test
**File**: `src/giljo_mcp/services/message_service.py`
**Method**: `MessageService.send_message()`
**Lines**: 171-179 (broadcast fan-out logic)

**Self-Exclusion Logic**:
```python
# Expand to individual recipients (excluding sender)
sender_ref = from_agent or "orchestrator"
for execution in executions:
    # Skip sender - compare both agent_display_name and agent_id
    if (execution.agent_display_name == sender_ref or
            execution.agent_id == sender_ref):
        continue
    resolved_to_agents.append(execution.agent_id)
    self._logger.info(f"[FANOUT] Expanded broadcast to agent_id '{execution.agent_id}'")
```

### Counter Update Logic
- **Sender**: `messages_sent_count` +1 (once per broadcast, not per recipient)
- **Recipients**: `messages_waiting_count` +1 (each recipient individually)
- **Self-Exclusion**: Sender's `messages_waiting_count` NEVER incremented

---

## Test Infrastructure

### Fixtures Used
- `test_tenant_key` - Unique tenant for test isolation
- `test_product` - Test product for project creation
- `test_project_with_three_agents` - Project with Agent A, B, C
- `message_service` - MessageService with mocked WebSocket manager
- `mock_websocket_manager` - Mocked WebSocket for event verification

### Database Verification
Tests verify both:
1. **Counter columns** on `AgentExecution` table
2. **Message records** in `Message` table

---

## Conclusion

✅ **All tests passed successfully**

The broadcast self-exclusion feature is working correctly:
- Senders are excluded from receiving their own broadcast messages
- Exclusion works for both `agent_display_name` and `agent_id` identification
- Counter updates are accurate (sender +1 sent, recipients +1 waiting each)
- Self-exclusion persists across multiple broadcasts
- Edge cases (empty projects) are handled gracefully

**Test Coverage**: Comprehensive integration testing covering happy path, edge cases, and multiple agent interactions.

**Confidence Level**: HIGH - All critical assertions passed, including database verification and counter accuracy.
