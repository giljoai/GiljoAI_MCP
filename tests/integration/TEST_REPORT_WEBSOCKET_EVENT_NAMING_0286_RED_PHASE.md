# WebSocket Event Naming Tests - RED Phase Report

**Handover**: 0286 - Jobs Dashboard WebSocket Wiring
**Date**: 2025-12-02
**Phase**: TDD RED (Tests written, expected to FAIL)
**Test File**: `F:\GiljoAI_MCP\tests\integration\test_websocket_event_naming_0286.py`

## Test Results Summary

**Total Tests**: 10
**Failed**: 9 ✅ (Expected - these define the target behavior)
**Passed**: 1 ✅ (Multi-tenant isolation already working correctly)

## Purpose

These tests verify that backend WebSocket events match frontend expectations. They are **behavioral tests** that define the contract between backend and frontend, NOT implementation tests.

## Test Failures (Expected)

### 1. Event Type Mismatches ❌

| Test | Frontend Expects | Backend Currently Emits | Status |
|------|-----------------|------------------------|--------|
| `test_status_change_emits_agent_status_changed_event` | `agent:status_changed` | `agent_job:status_update` | **FAIL** ✅ |
| `test_message_sent_emits_message_sent_event` | `message:sent` | `agent_communication:message_sent` | **FAIL** ✅ |
| `test_message_acknowledged_emits_message_acknowledged_event` | `message:acknowledged` | `agent_communication:message_acknowledged` | **FAIL** ✅ |
| `test_new_message_emits_message_new_event` | `message:new` | `agent_job:message` | **FAIL** ✅ |

**Reference**: Frontend handlers in `JobsTab.vue` lines 874-877:
```javascript
on('agent:status_changed', handleStatusUpdate)
on('message:sent', handleMessageSent)
on('message:acknowledged', handleMessageAcknowledged)
on('message:new', handleNewMessage)
```

### 2. Payload Field Mismatches ❌

| Test | Frontend Expects | Backend Currently Provides | Status |
|------|-----------------|---------------------------|--------|
| `test_status_payload_includes_status_field_not_new_status` | `data.status` | `data.new_status` | **FAIL** ✅ |
| `test_message_payload_includes_message_field_not_content_preview` | `data.message` | `data.content_preview` | **FAIL** ✅ |
| `test_all_events_include_tenant_key_in_payload` | `data.tenant_key` | Not included | **FAIL** ✅ |

**Reference**: Frontend handlers in `JobsTab.vue`:
- Line 864: `agent.status = data.status`
- Line 785: `text: data.message`
- Line 768: `if (data.tenant_key !== currentTenantKey.value)`

### 3. Complete Event Structure Tests ❌

| Test | Issue | Status |
|------|-------|--------|
| `test_status_change_event_complete_structure` | Event type mismatch | **FAIL** ✅ |
| `test_message_sent_event_complete_structure` | Event type mismatch | **FAIL** ✅ |

### 4. Multi-Tenant Isolation Test ✅

| Test | Status | Notes |
|------|--------|-------|
| `test_events_only_broadcast_to_matching_tenant` | **PASS** ✅ | Already working correctly |

## Failure Examples

### Test: `test_status_change_emits_agent_status_changed_event`
```
AssertionError: Expected event type 'agent:status_changed', got 'agent_job:status_update'.
Frontend handler: on('agent:status_changed', handleStatusUpdate)
```

### Test: `test_status_payload_includes_status_field_not_new_status`
```
AssertionError: Payload must include 'status' field for frontend compatibility.
Frontend expects: data.status
```

### Test: `test_all_events_include_tenant_key_in_payload`
```
AssertionError: Status update payload must include tenant_key.
Frontend checks: if (data.tenant_key !== currentTenantKey.value)
```

## Backend Methods Tested

From `F:\GiljoAI_MCP\api\websocket.py`:

1. **`broadcast_job_status_update()`** - Lines 784-850
   - Currently emits: `agent_job:status_update`, `agent_job:acknowledged`, `agent_job:completed`, `agent_job:failed`
   - Should emit: `agent:status_changed`
   - Payload issues: Uses `new_status` instead of `status`, missing `tenant_key`

2. **`broadcast_message_sent()`** - Lines 957-1014
   - Currently emits: `agent_communication:message_sent`
   - Should emit: `message:sent`
   - Payload issues: Uses `content_preview` instead of `message`, missing `tenant_key`

3. **`broadcast_message_acknowledged()`** - Lines 1016-1068
   - Currently emits: `agent_communication:message_acknowledged`
   - Should emit: `message:acknowledged`
   - Payload issues: Missing `tenant_key`

4. **`broadcast_job_message()`** - Lines 852-906
   - Currently emits: `agent_job:message`
   - Should emit: `message:new`
   - Payload issues: Uses `content_preview` instead of `message`, missing `tenant_key`

## Next Steps (GREEN Phase)

The implementation agent should now fix the backend code to make these tests pass:

1. **Update Event Types** in `api/websocket.py`:
   - Change `agent_job:status_update` → `agent:status_changed`
   - Change `agent_communication:message_sent` → `message:sent`
   - Change `agent_communication:message_acknowledged` → `message:acknowledged`
   - Change `agent_job:message` → `message:new`

2. **Update Payload Fields**:
   - Add `data.status` field (copy value from `new_status`)
   - Add `data.message` field (copy value from `content_preview`)
   - Add `data.tenant_key` to all event payloads

3. **Run Tests Again**:
   ```bash
   pytest tests/integration/test_websocket_event_naming_0286.py -v
   ```

## Test Coverage

These tests cover:
- ✅ Event type naming (4 tests)
- ✅ Payload field naming (3 tests)
- ✅ Complete event structure (2 tests)
- ✅ Multi-tenant isolation (1 test)
- ✅ Total: 10 comprehensive integration tests

## Architecture Notes

- **Behavioral Testing**: Tests verify the API contract (event names, field names), not implementation details
- **No Database Coupling**: Message fixtures use dictionaries instead of ORM models
- **Multi-Tenant Safety**: All tests verify tenant_key filtering
- **Frontend-Driven**: Test assertions match exact frontend expectations from `JobsTab.vue`

## Fixed Issues

During test development, fixed:
1. ✅ Syntax error in `project_service.py` line 1824 (missing except block)
2. ✅ Invalid status values (changed `pending`/`active` → `waiting`/`working`)
3. ✅ Message model coupling (simplified to use dictionaries)

## References

- **Frontend Handler**: `F:\GiljoAI_MCP\frontend\src\components\projects\JobsTab.vue`
- **Backend WebSocket**: `F:\GiljoAI_MCP\api\websocket.py`
- **Handover Document**: `handovers/0286_jobs_dashboard_websocket_wiring.md`

---

**Status**: ✅ RED Phase Complete
**Ready For**: GREEN Phase (Implementation to make tests pass)
