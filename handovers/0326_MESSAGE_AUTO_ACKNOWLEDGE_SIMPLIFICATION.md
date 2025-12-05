# Handover: Message Auto-Acknowledge Simplification

**Date:** 2025-12-05
**From Agent:** Orchestrator (Claude Opus 4.5)
**To Agent:** TDD-Implementor, Analyzer, Tester subagents
**Priority:** High
**Estimated Complexity:** 2-3 hours
**Status:** In Progress

---

## Task Summary

Simplify the messaging system by merging "read" and "acknowledge" into a single operation. When an agent calls `receive_messages`, messages are automatically marked as acknowledged/read. Remove the separate `acknowledge_message` MCP tool entirely.

**Why:** User feedback indicates the separate acknowledge step over-complicates the workflow. Agents run in visible terminal windows - users can see when messages are received. If an agent misses something, the user can simply ask it to re-read messages.

**Expected Outcome:** Cleaner API surface, fewer MCP tools, simpler agent workflow.

---

## Context and Background

### Architecture Reference
- Slide 2: Developer PC with visible CLI/Terminal running agents
- Slide 3: Multi-user architecture - each dev sees their agents in terminals
- Slide 4: "MCP message center for working Agents, with Developer visualization"

### Current State
- `receive_messages` - Returns messages, does NOT mark as read
- `acknowledge_message` - Separate call to mark message as acknowledged
- Dashboard shows "acknowledged" status in Messages column

### Target State
- `receive_messages` - Returns messages AND marks them as acknowledged
- `acknowledge_message` - REMOVED entirely
- Dashboard shows "read" status (same field, cleaner semantics)

---

## Technical Details

### Files to Modify

| File | Action | Changes |
|------|--------|---------|
| `src/giljo_mcp/services/message_service.py` | Modify | Add auto-ack to `receive_messages`, remove `acknowledge_message` method |
| `src/giljo_mcp/tools/agent_communication.py` | Modify | Remove `acknowledge_message` tool registration |
| `src/giljo_mcp/tools/tool_accessor.py` | Modify | Remove `acknowledge_message` method |
| `src/giljo_mcp/agent_message_queue.py` | Modify | Remove `acknowledge_message` method |
| `api/endpoints/messages.py` | Modify | Remove `acknowledge_message` endpoint |
| `scripts/continuous_ui_monitor.py` | Modify | Remove `acknowledge_message` calls |
| `scripts/ui_analyzer_monitor.py` | Modify | Remove `acknowledge_message` calls |
| `scripts/ui_analyzer_monitor_mcp.py` | Modify | Remove `acknowledge_message` calls |
| `dev_tools/simulator/api_client.py` | Modify | Remove `acknowledge_message` method |
| `tests/unit/test_tools_message.py` | Modify | Update tests, remove ack-specific tests |
| `frontend/src/components/projects/JobsTab.vue` | Modify | Wire up read status display |

### Key Code Locations

**MessageService.receive_messages** (`message_service.py:442-558`):
- Add bulk update to mark messages as acknowledged after retrieval
- Use single transaction for read + acknowledge

**MessageService.acknowledge_message** (`message_service.py:738-850`):
- Remove entirely

**MCP Tool Registration** (`agent_communication.py:120-189`):
- Remove `acknowledge_message` tool from `register_agent_communication_tools`

---

## Implementation Plan

### Phase 1: Analysis (Analyzer subagent)
- Map all `acknowledge_message` usages
- Identify any edge cases or dependencies
- Confirm removal is safe

### Phase 2: TDD Implementation (TDD-Implementor subagent)
1. Write test: `test_receive_messages_auto_acknowledges`
2. Modify `receive_messages` to auto-acknowledge
3. Write test: `test_acknowledge_message_removed`
4. Remove `acknowledge_message` from all layers
5. Update existing tests

### Phase 3: Frontend Update (TDD-Implementor subagent)
- Update JobsTab.vue to display read status correctly
- Ensure WebSocket updates work with new flow

### Phase 4: Testing (Tester subagent)
- Unit tests pass
- Integration tests pass
- Manual verification via dashboard

---

## Testing Requirements

### Unit Tests
- `test_receive_messages_auto_acknowledges` - Messages marked read on retrieval
- `test_receive_messages_only_marks_returned_messages` - Limit respected
- Remove: `test_acknowledge_message_*` tests

### Integration Tests
- MCP tool list no longer includes `acknowledge_message`
- Dashboard shows read status after agent receives messages

### Manual Testing
1. Send message to agent via dashboard
2. Agent calls `receive_messages`
3. Dashboard shows message as "read"
4. No `acknowledge_message` tool available in MCP

---

## Success Criteria

- [ ] `receive_messages` auto-acknowledges retrieved messages
- [ ] `acknowledge_message` completely removed from codebase
- [ ] No orphan code or dead references
- [ ] All tests pass
- [ ] Dashboard correctly shows read/unread status
- [ ] MCP tool list does not include `acknowledge_message`

---

## Rollback Plan

If issues arise:
1. Revert commits for this handover
2. `acknowledge_message` was separate - no data migration needed
3. Messages table schema unchanged (still has `acknowledged` field)

---

## Additional Resources

- Architecture slides: `handovers/Reference_docs/Workflow PPT to JPG/`
- Message service: `src/giljo_mcp/services/message_service.py`
- MCP tools: `src/giljo_mcp/tools/agent_communication.py`
