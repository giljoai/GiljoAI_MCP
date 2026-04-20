# Test Report: Message Routing WebSocket Emissions (Handover 0289 - RED Phase)

**Date**: 2025-12-03
**Phase**: TDD RED Phase (Failing Tests)
**Purpose**: Validate that tests fail appropriately before implementation

---

## Executive Summary

✅ **RED Phase Complete**: All 5 tests fail as expected
⏭️ **Next Step**: GREEN Phase - Implement WebSocket emissions in MessageService

---

## Test Results

### Test File: `tests/integration/test_message_routing_0289.py`

| # | Test Name | Status | Reason for Failure |
|---|-----------|--------|-------------------|
| 1 | `test_direct_message_emits_websocket_event` | ❌ **FAIL** | `MessageService` does not have `_websocket_manager` attribute |
| 2 | `test_broadcast_message_emits_websocket_event` | ❌ **FAIL** | `MessageService` does not have `_websocket_manager` attribute |
| 3 | `test_message_acknowledgment_emits_websocket_event` | ❌ **FAIL** | `MessageService` does not have `_websocket_manager` attribute |
| 4 | `test_multi_tenant_message_isolation` | ❌ **FAIL** | `MessageService` does not have `_websocket_manager` attribute |
| 5 | `test_message_completion_emits_websocket_event` | ❌ **FAIL** | `MessageService` does not have `_websocket_manager` attribute |

---

## Test Coverage

### Test 1: Direct Message WebSocket Emission

**Purpose**: Verify direct messages emit `message:sent` WebSocket event

**Expected Behavior**:
1. Message created in database ✅ (works)
2. WebSocket manager's `broadcast_message_sent()` called ❌ (not implemented)
3. Event contains correct metadata ❌ (not implemented)

**Failure Point**:
```python
assert hasattr(message_service, '_websocket_manager'), \
    "MessageService should have _websocket_manager attribute"
```

**Current State**: `MessageService` does not have WebSocket integration

---

### Test 2: Broadcast Message WebSocket Emission

**Purpose**: Verify broadcast messages emit `message:new` WebSocket events to all agents

**Expected Behavior**:
1. Message broadcast to all agents in project ✅ (database layer works)
2. WebSocket `broadcast_job_message()` called for each recipient ❌ (not implemented)
3. Sender does NOT receive echo ❌ (not implemented)

**Failure Point**: Same as Test 1 - missing `_websocket_manager` attribute

**Current State**: Broadcast works at database level but no real-time notifications

---

### Test 3: Message Acknowledgment WebSocket Emission

**Purpose**: Verify message acknowledgments emit `message:acknowledged` WebSocket event

**Expected Behavior**:
1. Message acknowledged in database ✅ (works)
2. WebSocket `broadcast_message_acknowledged()` called ❌ (not implemented)
3. Event contains acknowledgment metadata ❌ (not implemented)

**Failure Point**: Same as Test 1 - missing `_websocket_manager` attribute

**Current State**: Acknowledgments work but no real-time notification to orchestrator

---

### Test 4: Multi-Tenant Message Isolation

**Purpose**: Verify WebSocket events respect tenant boundaries

**Expected Behavior**:
1. Messages isolated at database level ✅ (works)
2. WebSocket events only broadcast to correct tenant ❌ (not implemented)
3. No cross-tenant leakage ❌ (cannot verify without WebSocket)

**Failure Point**: Same as Test 1 - missing `_websocket_manager` attribute

**Current State**: Database isolation works but real-time isolation untested

---

### Test 5: Message Completion WebSocket Emission

**Purpose**: Verify message completion emits appropriate WebSocket events

**Expected Behavior**:
1. Message completed in database ✅ (works)
2. WebSocket event emitted for completion ❌ (not implemented)

**Failure Point**: Same as Test 1 - missing `_websocket_manager` attribute

**Current State**: Completion tracking works but no real-time notification

---

## Architecture Findings

### Current MessageService Implementation

**Location**: `src/giljo_mcp/services/message_service.py`

**Current Constructor**:
```python
def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
    self.db_manager = db_manager
    self.tenant_manager = tenant_manager
    self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
```

**Missing**:
- `_websocket_manager` parameter
- WebSocket emissions in:
  - `send_message()` method
  - `broadcast()` method
  - `acknowledge_message()` method
  - `complete_message()` method

---

## WebSocket Manager Reference

**Location**: `api/websocket.py`

**Available Methods** (that MessageService should call):
```python
# For message sending
async def broadcast_message_sent(
    self,
    message_id: str,
    job_id: str,
    tenant_key: str,
    from_agent: str,
    to_agent: Optional[str],
    message_type: str,
    content_preview: str,
    priority: int,
    timestamp: Optional[datetime] = None,
)

# For message acknowledgment
async def broadcast_message_acknowledged(
    self,
    message_id: str,
    job_id: str,
    tenant_key: str,
    agent_id: str,
    response_data: Optional[dict] = None,
    timestamp: Optional[datetime] = None,
)

# For broadcast messages
async def broadcast_job_message(
    self,
    job_id: str,
    message_id: str,
    from_agent: str,
    tenant_key: str,
    to_agent: Optional[str] = None,
    message_type: str = "status",
    content_preview: Optional[str] = None,
    timestamp: Optional[datetime] = None,
)
```

---

## Implementation Requirements (GREEN Phase)

### 1. Update MessageService Constructor

```python
def __init__(
    self,
    db_manager: DatabaseManager,
    tenant_manager: TenantManager,
    websocket_manager=None  # Optional for tests
):
    self.db_manager = db_manager
    self.tenant_manager = tenant_manager
    self._websocket_manager = websocket_manager
    self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
```

### 2. Add WebSocket Emissions to send_message()

After successfully creating message in database:
```python
if self._websocket_manager:
    await self._websocket_manager.broadcast_message_sent(
        message_id=message_id,
        job_id=None,  # Or derive from message
        tenant_key=project.tenant_key,
        from_agent=from_agent or "orchestrator",
        to_agent=to_agents[0] if len(to_agents) == 1 else None,
        message_type=message_type,
        content_preview=content[:200],
        priority=priority_value,  # Convert string to int
        timestamp=datetime.now(timezone.utc),
    )
```

### 3. Add WebSocket Emissions to broadcast()

After successfully broadcasting message:
```python
if self._websocket_manager:
    for agent_type in agent_types:
        if agent_type != from_agent:  # Don't echo to sender
            await self._websocket_manager.broadcast_job_message(
                job_id=job_id,  # From agent_jobs query
                message_id=message_id,
                from_agent=from_agent,
                tenant_key=tenant_key,
                to_agent=agent_type,
                message_type="broadcast",
                content_preview=content[:200],
                timestamp=datetime.now(timezone.utc),
            )
```

### 4. Add WebSocket Emissions to acknowledge_message()

After successfully acknowledging message:
```python
if self._websocket_manager:
    await self._websocket_manager.broadcast_message_acknowledged(
        message_id=message_id,
        job_id=None,  # Or derive from message
        tenant_key=message.tenant_key,
        agent_id=agent_name,
        timestamp=datetime.now(timezone.utc),
    )
```

### 5. Add WebSocket Emissions to complete_message()

Similar pattern to acknowledgment - emit event after successful completion.

---

## Test Execution Commands

```bash
# Run all message routing tests
python -m pytest tests/integration/test_message_routing_0289.py -v

# Run specific test
python -m pytest tests/integration/test_message_routing_0289.py::test_direct_message_emits_websocket_event -v

# Run with detailed output
python -m pytest tests/integration/test_message_routing_0289.py -v --tb=short
```

---

## Success Criteria for GREEN Phase

1. ✅ All 5 tests pass
2. ✅ WebSocket events emitted for all message operations
3. ✅ Multi-tenant isolation maintained
4. ✅ No performance degradation
5. ✅ Backward compatibility maintained (websocket_manager is optional)

---

## Files Created

- `tests/integration/test_message_routing_0289.py` - Comprehensive failing tests (5 tests, 465 lines)

---

## Next Steps

1. **GREEN Phase**: Implement WebSocket emissions in MessageService
   - Add `websocket_manager` parameter to constructor
   - Add emissions to `send_message()`
   - Add emissions to `broadcast()`
   - Add emissions to `acknowledge_message()`
   - Add emissions to `complete_message()`

2. **Verify**: Run tests and ensure all pass

3. **Refactor**: Clean up any code duplication

4. **Document**: Update MessageService docstrings

---

## Conclusion

✅ **RED Phase Successful**: All tests fail for the correct reason
📋 **Implementation Path Clear**: Requirements well-defined
🎯 **Ready for GREEN Phase**: Proceed with MessageService WebSocket integration

**Handover 0289 Status**: RED Phase Complete
