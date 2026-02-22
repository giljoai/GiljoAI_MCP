# Handover 0419: Long-Polling MCP Tool for Orchestrator Monitoring

**Status**: READY FOR IMPLEMENTATION
**Created**: 2026-01-16
**Complexity**: Medium (8-12 hours)
**Priority**: High (Unblocks multi-terminal orchestration)
**Dependencies**: Handover 0416 (Agent Status State Machine Enhancement)

---

## Pre-Implementation Required Reading

**CRITICAL**: Read these documents before starting implementation:

1. **MCP Tools Architecture**:
   - `docs/api/MCP_TOOLS_MANUAL.md` - MCP tool patterns and registration
   - `src/giljo_mcp/tools/orchestration.py` - Existing orchestration tools

2. **Orchestrator Protocol**:
   - `docs/ORCHESTRATOR.md` - Orchestrator workflow and communication patterns
   - `docs/components/STAGING_WORKFLOW.md` - 7-task staging workflow (Handover 0246a)

3. **State Machine & Events**:
   - `handovers/completed/0416_agent_status_state_machine_enhancement.md` - Status transitions
   - `src/giljo_mcp/agent_job_manager.py` - WebSocket event emission

4. **Testing Standards**:
   - `docs/TESTING.md` - TDD patterns and coverage requirements (>80%)

---

## TDD Protocol Reminder

**Test-Driven Development is MANDATORY**:

1. **Write tests FIRST** (before implementation code)
2. **Run tests** - they should FAIL (red)
3. **Implement minimum code** to make tests pass (green)
4. **Refactor** while keeping tests green
5. **Repeat** for next feature

**Coverage Target**: >80% for all new code (enforced via pytest-cov)

---

## Objective

Implement HTTP long-polling MCP tool to enable orchestrators to monitor agent progress and respond to events in real-time without manual user intervention, solving the "passive orchestrator" problem in multi-terminal mode.

---

## Problem Statement

### Current Behavior (Broken)

After spawning agents in separate terminals, the orchestrator sits idle with no mechanism to know when:
- Agents become blocked (need assistance)
- Agents complete (need acknowledgment/next steps)
- Agents fail (need error handling)
- Messages arrive (need processing)

**User Experience**: Orchestrator terminal shows no activity. User must manually check dashboard or agent terminals, then manually type into orchestrator terminal to trigger checks. This defeats the purpose of autonomous orchestration.

### Why Existing Solutions Don't Work

| Approach | Why It Fails |
|----------|--------------|
| **WebSocket in CLI** | Requires event loop integration, breaks stdio MCP protocol, platform-dependent |
| **Polling with sleep()** | Wastes tokens on empty checks, consumes context with "still waiting..." messages |
| **GUI Integration** | Orchestrator runs in CLI terminal (no Electron), no cross-process communication |
| **Timer/Scheduler** | External dependency, requires daemon process, complicates installation |

---

## Architecture Context

### HTTP MCP Protocol (v3.0+)

GiljoAI uses HTTP-only MCP transport (Handover 0334):
- **Endpoint**: `/mcp` (JSON-RPC over HTTP)
- **Auth**: `X-API-Key` header
- **Transport**: Request/response (synchronous by design)

**Key Constraint**: MCP tools are synchronous functions. We cannot use WebSockets or async notifications within the tool itself.

### Long-Polling Pattern

**Industry Standard** used by AWS SQS, Kubernetes watch API, Slack (pre-WebSocket):

```
┌─────────────┐                           ┌─────────────┐
│ Orchestrator│                           │   Server    │
│   (Client)  │                           │             │
└──────┬──────┘                           └──────┬──────┘
       │                                         │
       │  POST /mcp                              │
       │  wait_for_notifications(timeout=60)     │
       ├────────────────────────────────────────>│
       │                                         │
       │              [Server holds connection]  │
       │              [Monitors for events]      │
       │              [Agent status changes]     │
       │              [Messages arrive]          │
       │                                         │
       │              [Event occurs OR timeout]  │
       │                                         │
       │  Response: {events: [...]}              │
       │<────────────────────────────────────────┤
       │                                         │
       │  [Process events]                       │
       │  [Take actions]                         │
       │                                         │
       │  POST /mcp (call again)                 │
       │  wait_for_notifications(timeout=60)     │
       ├────────────────────────────────────────>│
       │                                         │
```

**Key Properties**:
- Client makes request, server delays response
- Connection held open (timeout: 60s default)
- When event occurs: immediate response
- No event: response after timeout with empty list
- Client immediately calls again (continuous loop)

**Why This Works**:
- ✅ Pure HTTP (works with existing MCP protocol)
- ✅ No client-side async (MCP tool is synchronous)
- ✅ Push-like semantics (low latency on events)
- ✅ Token-efficient (waiting is FREE, only processing costs tokens)
- ✅ Cross-platform (no timers, no GUI, no external deps)

---

## Solution Design

### MCP Tool Signature

```python
@mcp_tool(
    name="wait_for_notifications",
    description=(
        "Long-polling tool for orchestrators to monitor agent events. "
        "Blocks until events occur or timeout. Call in loop after spawning agents. "
        "Returns immediately if events pending, otherwise waits up to timeout seconds."
    )
)
async def wait_for_notifications(
    orchestrator_id: str,
    tenant_key: str,
    timeout: int = 60,
    event_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Wait for orchestrator-relevant events (agent status changes, messages).

    Args:
        orchestrator_id: Orchestrator's agent_id (identity.agent_id)
        tenant_key: Tenant isolation key
        timeout: Max seconds to wait (default 60, range 10-120)
        event_types: Optional filter (default: all orchestrator events)

    Returns:
        {
            "events": [
                {
                    "event_type": "agent_status_changed",
                    "agent_id": "uuid",
                    "agent_name": "implementor-auth",
                    "old_status": "active",
                    "new_status": "blocked",
                    "timestamp": "2026-01-16T10:30:00Z",
                    "details": {...}
                },
                {
                    "event_type": "message_received",
                    "message_id": "uuid",
                    "from_agent": "uuid",
                    "content": "Need guidance on API design",
                    "priority": "high",
                    "timestamp": "2026-01-16T10:31:00Z"
                }
            ],
            "waited_seconds": 3.2,
            "timeout_occurred": false,
            "next_poll_recommended": true
        }
    """
```

### Event Types

| Event Type | Trigger | Details |
|------------|---------|---------|
| `agent_status_changed` | Agent transitions to blocked/complete/failed | agent_id, old_status, new_status, reason |
| `message_received` | Message sent TO orchestrator | message_id, from_agent, content, priority |
| `project_cancelled` | User cancels project via dashboard | project_id, cancelled_by |
| `succession_requested` | Context limit approaching (90%+) | current_usage, budget, handover_reason |

### Server Implementation Pattern

```python
# src/giljo_mcp/tools/orchestration.py

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

class OrchestrationEventMonitor:
    """Manages long-polling event subscriptions for orchestrators."""

    def __init__(self):
        self._pending_events: Dict[str, List[Dict]] = {}  # orchestrator_id -> events
        self._waiters: Dict[str, List[asyncio.Event]] = {}  # orchestrator_id -> wake signals

    def add_event(self, orchestrator_id: str, event: Dict[str, Any]):
        """Called by WebSocket event handlers when events occur."""
        if orchestrator_id not in self._pending_events:
            self._pending_events[orchestrator_id] = []

        self._pending_events[orchestrator_id].append(event)

        # Wake any waiting long-poll requests
        if orchestrator_id in self._waiters:
            for waiter in self._waiters[orchestrator_id]:
                waiter.set()

    async def wait_for_events(
        self,
        orchestrator_id: str,
        tenant_key: str,
        timeout: int,
        event_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Long-polling wait for events."""
        start_time = datetime.now()

        # Check for pending events first (immediate return)
        events = self._get_pending_events(orchestrator_id, tenant_key, event_types)
        if events:
            return {
                "events": events,
                "waited_seconds": 0.0,
                "timeout_occurred": False,
                "next_poll_recommended": True
            }

        # No pending events - wait for new ones
        waiter = asyncio.Event()
        if orchestrator_id not in self._waiters:
            self._waiters[orchestrator_id] = []
        self._waiters[orchestrator_id].append(waiter)

        try:
            # Wait for event or timeout
            await asyncio.wait_for(waiter.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            # Timeout - return empty
            elapsed = (datetime.now() - start_time).total_seconds()
            return {
                "events": [],
                "waited_seconds": elapsed,
                "timeout_occurred": True,
                "next_poll_recommended": True  # Keep polling
            }
        finally:
            # Cleanup
            self._waiters[orchestrator_id].remove(waiter)

        # Event occurred - fetch and return
        elapsed = (datetime.now() - start_time).total_seconds()
        events = self._get_pending_events(orchestrator_id, tenant_key, event_types)

        return {
            "events": events,
            "waited_seconds": elapsed,
            "timeout_occurred": False,
            "next_poll_recommended": True
        }

    def _get_pending_events(
        self,
        orchestrator_id: str,
        tenant_key: str,
        event_types: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Fetch and clear pending events for orchestrator."""
        if orchestrator_id not in self._pending_events:
            return []

        events = self._pending_events[orchestrator_id]
        self._pending_events[orchestrator_id] = []

        # Filter by event type if specified
        if event_types:
            events = [e for e in events if e["event_type"] in event_types]

        return events

# Global singleton
event_monitor = OrchestrationEventMonitor()

@mcp_tool(name="wait_for_notifications")
async def wait_for_notifications(
    orchestrator_id: str,
    tenant_key: str,
    timeout: int = 60,
    event_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Long-polling wait for orchestrator events."""

    # Validate timeout range
    timeout = max(10, min(timeout, 120))

    # Wait for events (blocks HTTP response)
    result = await event_monitor.wait_for_events(
        orchestrator_id=orchestrator_id,
        tenant_key=tenant_key,
        timeout=timeout,
        event_types=event_types
    )

    return result
```

### Integration with Existing Event System

Modify `AgentJobManager` to emit events to long-poll monitor:

```python
# src/giljo_mcp/agent_job_manager.py

from giljo_mcp.tools.orchestration import event_monitor

class AgentJobManager:
    async def update_status(self, job_id: str, new_status: str, ...):
        # ... existing status update logic ...

        # Emit WebSocket event (existing)
        await self._emit_status_event(job, old_status, new_status)

        # NEW: Notify long-poll monitor
        if job.spawned_by:  # Has orchestrator parent
            event_monitor.add_event(
                orchestrator_id=job.spawned_by,
                event={
                    "event_type": "agent_status_changed",
                    "agent_id": job.agent_id,
                    "agent_name": job.agent_name,
                    "old_status": old_status,
                    "new_status": new_status,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "details": {
                        "job_id": job_id,
                        "status_metadata": job.status_metadata
                    }
                }
            )
```

### Orchestrator Protocol Update

Add monitoring guidance to orchestrator instructions (Handover 0246a staging workflow or generic agent template 0246b):

**Option 1: Update Staging Workflow (CH7 - Post-Spawning Monitoring)**

```markdown
## Chapter 7: Monitoring & Coordination

After spawning agents, enter monitoring loop to track progress and respond to events.

### 7.1 Start Monitoring Loop

Call `wait_for_notifications()` repeatedly to receive real-time agent events:

```python
wait_for_notifications(
    orchestrator_id="{orchestrator_id}",
    tenant_key="{tenant_key}",
    timeout=60  # Wait up to 60 seconds for events
)
```

**What Happens**: Server holds connection open until events occur or timeout. This is FREE token-wise - you only pay for processing events.

### 7.2 Process Events

When `wait_for_notifications()` returns, process each event:

**Agent Status Changed**:
- `blocked`: Agent needs guidance → Call `receive_messages()`, provide assistance, send instructions
- `complete`: Agent finished → Acknowledge completion, spawn next agent if needed
- `failed`: Agent encountered error → Review error, decide retry/modify/abandon

**Message Received**:
- High priority: Respond immediately
- Normal priority: Respond when appropriate
- Low priority: Batch with other responses

**Project Cancelled**:
- Stop all work immediately
- Call `complete_job()` with cancellation status

**Succession Requested**:
- Context limit approaching → Call `create_successor_orchestrator()`

### 7.3 Continue Loop

After processing events, call `wait_for_notifications()` again. Continue until:
- All agents complete successfully
- Project cancelled
- Succession triggered
```

**Option 2: Add to Generic Agent Template (if orchestrators also use generic template)**

---

## Implementation Plan

### Phase 1: Core Long-Polling Infrastructure (TDD)

**Tests First**:

```python
# tests/tools/test_orchestration_longpoll.py

import pytest
import asyncio
from datetime import datetime
from giljo_mcp.tools.orchestration import (
    event_monitor,
    wait_for_notifications
)

@pytest.mark.asyncio
async def test_immediate_return_when_events_pending():
    """Should return immediately if events already queued."""
    orch_id = "orch-123"
    tenant = "tenant-abc"

    # Pre-queue event
    event_monitor.add_event(orch_id, {
        "event_type": "agent_status_changed",
        "agent_id": "agent-456",
        "new_status": "blocked",
        "timestamp": datetime.now().isoformat()
    })

    # Call should return immediately (not wait 60s)
    start = datetime.now()
    result = await wait_for_notifications(orch_id, tenant, timeout=60)
    elapsed = (datetime.now() - start).total_seconds()

    assert elapsed < 1.0  # Should be instant
    assert len(result["events"]) == 1
    assert result["events"][0]["event_type"] == "agent_status_changed"
    assert result["timeout_occurred"] is False

@pytest.mark.asyncio
async def test_timeout_when_no_events():
    """Should timeout and return empty list after specified seconds."""
    orch_id = "orch-789"
    tenant = "tenant-xyz"

    start = datetime.now()
    result = await wait_for_notifications(orch_id, tenant, timeout=2)
    elapsed = (datetime.now() - start).total_seconds()

    assert 1.8 <= elapsed <= 2.5  # Should wait ~2 seconds
    assert len(result["events"]) == 0
    assert result["timeout_occurred"] is True
    assert result["waited_seconds"] >= 1.8

@pytest.mark.asyncio
async def test_wake_on_event_arrival():
    """Should wake immediately when event added during wait."""
    orch_id = "orch-999"
    tenant = "tenant-test"

    async def add_event_after_delay():
        await asyncio.sleep(0.5)  # Wait 500ms
        event_monitor.add_event(orch_id, {
            "event_type": "message_received",
            "message_id": "msg-123",
            "content": "Help needed",
            "timestamp": datetime.now().isoformat()
        })

    # Start both concurrently
    task1 = asyncio.create_task(wait_for_notifications(orch_id, tenant, timeout=10))
    task2 = asyncio.create_task(add_event_after_delay())

    start = datetime.now()
    result, _ = await asyncio.gather(task1, task2)
    elapsed = (datetime.now() - start).total_seconds()

    assert 0.4 <= elapsed <= 1.0  # Should wake at ~500ms (not wait 10s)
    assert len(result["events"]) == 1
    assert result["events"][0]["event_type"] == "message_received"

@pytest.mark.asyncio
async def test_event_type_filtering():
    """Should filter events by type when specified."""
    orch_id = "orch-filter"
    tenant = "tenant-abc"

    # Add multiple event types
    event_monitor.add_event(orch_id, {"event_type": "agent_status_changed"})
    event_monitor.add_event(orch_id, {"event_type": "message_received"})
    event_monitor.add_event(orch_id, {"event_type": "project_cancelled"})

    # Filter for only message_received
    result = await wait_for_notifications(
        orch_id, tenant, timeout=1, event_types=["message_received"]
    )

    assert len(result["events"]) == 1
    assert result["events"][0]["event_type"] == "message_received"

@pytest.mark.asyncio
async def test_multiple_orchestrators_isolated():
    """Events should not leak between orchestrators."""
    orch1 = "orch-aaa"
    orch2 = "orch-bbb"
    tenant = "tenant-test"

    # Add event for orch1
    event_monitor.add_event(orch1, {"event_type": "agent_status_changed"})

    # orch2 should not see orch1's events
    result = await wait_for_notifications(orch2, tenant, timeout=1)

    assert len(result["events"]) == 0
    assert result["timeout_occurred"] is True
```

**Implementation**:
1. Create `OrchestrationEventMonitor` class in `src/giljo_mcp/tools/orchestration.py`
2. Implement `wait_for_notifications()` MCP tool
3. Run tests (should pass)

**Acceptance**: All Phase 1 tests pass, coverage >80%

---

### Phase 2: Integration with Event Emission (TDD)

**Tests First**:

```python
# tests/integration/test_longpoll_integration.py

import pytest
from giljo_mcp.agent_job_manager import AgentJobManager
from giljo_mcp.tools.orchestration import event_monitor, wait_for_notifications

@pytest.mark.asyncio
async def test_status_change_triggers_notification(db_session, sample_orchestrator, sample_agent):
    """Changing agent status should trigger orchestrator notification."""
    manager = AgentJobManager(db_session)

    # Start long-poll in background
    poll_task = asyncio.create_task(
        wait_for_notifications(
            orchestrator_id=sample_orchestrator.agent_id,
            tenant_key=sample_orchestrator.tenant_key,
            timeout=10
        )
    )

    # Give poll time to start waiting
    await asyncio.sleep(0.1)

    # Change agent status (should wake poll)
    await manager.update_status(
        job_id=sample_agent.id,
        new_status="blocked",
        status_metadata={"reason": "Needs guidance"}
    )

    # Poll should wake immediately
    result = await poll_task

    assert len(result["events"]) == 1
    assert result["events"][0]["event_type"] == "agent_status_changed"
    assert result["events"][0]["new_status"] == "blocked"
    assert result["timeout_occurred"] is False

@pytest.mark.asyncio
async def test_message_triggers_notification(db_session, sample_orchestrator):
    """Sending message to orchestrator should trigger notification."""
    from giljo_mcp.tools.messaging import send_message

    # Start long-poll
    poll_task = asyncio.create_task(
        wait_for_notifications(
            orchestrator_id=sample_orchestrator.agent_id,
            tenant_key=sample_orchestrator.tenant_key,
            timeout=10
        )
    )

    await asyncio.sleep(0.1)

    # Send message to orchestrator
    await send_message(
        to_agents=[sample_orchestrator.agent_id],
        content="Need help with architecture",
        from_agent="agent-123",
        tenant_key=sample_orchestrator.tenant_key,
        project_id=sample_orchestrator.project_id
    )

    result = await poll_task

    assert len(result["events"]) == 1
    assert result["events"][0]["event_type"] == "message_received"
    assert "architecture" in result["events"][0]["content"]
```

**Implementation**:
1. Modify `AgentJobManager.update_status()` to call `event_monitor.add_event()`
2. Modify `send_message()` to call `event_monitor.add_event()` for orchestrator recipients
3. Add project cancellation event emission
4. Run integration tests (should pass)

**Acceptance**: All Phase 2 tests pass, events flow from domain logic to long-poll

---

### Phase 3: Orchestrator Protocol Documentation

**Tasks**:
1. Update `docs/ORCHESTRATOR.md` with monitoring loop guidance
2. Update `docs/components/STAGING_WORKFLOW.md` (add CH7 or update existing chapters)
3. Update `docs/api/MCP_TOOLS_MANUAL.md` with `wait_for_notifications()` reference
4. Add code examples for orchestrator monitoring patterns

**Acceptance**: Documentation complete, reviewed, committed

---

### Phase 4: E2E Validation

**Manual Test Scenario**:

1. Create project via dashboard
2. Activate project (spawns orchestrator in Terminal 1)
3. Orchestrator spawns 2 agents (Terminal 2, Terminal 3)
4. Orchestrator calls `wait_for_notifications()` (Terminal 1 should show "Waiting for events...")
5. Agent 1 completes work, updates status to "complete" (Terminal 2)
6. **Expected**: Terminal 1 wakes immediately (not after 60s timeout), displays event, processes completion
7. Agent 2 reports blocked (Terminal 3)
8. **Expected**: Terminal 1 receives blocked event, orchestrator responds with guidance
9. Agent 2 completes (Terminal 3)
10. **Expected**: Terminal 1 receives complete event, orchestrator finalizes project

**Acceptance**: Full orchestration loop works autonomously with real-time event response

---

## Files to Modify

| File | Changes | Estimated Lines |
|------|---------|----------------|
| `src/giljo_mcp/tools/orchestration.py` | Add `OrchestrationEventMonitor` class, `wait_for_notifications()` tool | +200 |
| `src/giljo_mcp/agent_job_manager.py` | Integrate event emission on status changes | +15 |
| `src/giljo_mcp/tools/messaging.py` | Integrate event emission for orchestrator messages | +10 |
| `tests/tools/test_orchestration_longpoll.py` | **NEW** - Unit tests for long-polling | +250 |
| `tests/integration/test_longpoll_integration.py` | **NEW** - Integration tests | +150 |
| `docs/ORCHESTRATOR.md` | Add monitoring loop documentation | +50 |
| `docs/components/STAGING_WORKFLOW.md` | Add CH7 or update existing chapters | +80 |
| `docs/api/MCP_TOOLS_MANUAL.md` | Document `wait_for_notifications()` | +40 |

**Total Estimated**: ~795 lines

---

## Testing Requirements

### Unit Tests (>80% coverage)

- `OrchestrationEventMonitor` class methods
- `wait_for_notifications()` tool all code paths
- Event filtering logic
- Timeout behavior
- Multi-orchestrator isolation

### Integration Tests

- Status change → notification flow
- Message send → notification flow
- Project cancellation → notification flow
- Succession request → notification flow

### E2E Validation

- Full orchestration loop with 2+ agents
- Real-time event response (no manual intervention)
- Timeout behavior (no events for 60+ seconds)

**Coverage Command**:
```bash
pytest tests/tools/test_orchestration_longpoll.py \
       tests/integration/test_longpoll_integration.py \
       --cov=src/giljo_mcp/tools/orchestration \
       --cov-report=html \
       --cov-fail-under=80
```

---

## Success Criteria

### Functional Requirements

- ✅ `wait_for_notifications()` MCP tool implemented and registered
- ✅ Returns immediately if events pending (<1 second)
- ✅ Waits up to timeout if no events (default 60s)
- ✅ Wakes immediately when event occurs during wait (<1 second latency)
- ✅ Filters events by type when specified
- ✅ Isolates events between orchestrators (no cross-tenant leakage)

### Integration Requirements

- ✅ Agent status changes trigger orchestrator notifications
- ✅ Messages to orchestrator trigger notifications
- ✅ Project cancellation triggers notifications
- ✅ Succession requests trigger notifications

### Quality Requirements

- ✅ Test coverage >80% for all new code
- ✅ No breaking changes to existing MCP tools
- ✅ No external dependencies added
- ✅ Cross-platform compatible (Windows/Linux/macOS)

### Documentation Requirements

- ✅ MCP tool documented in `MCP_TOOLS_MANUAL.md`
- ✅ Orchestrator monitoring loop documented in `ORCHESTRATOR.md`
- ✅ Staging workflow updated with monitoring guidance
- ✅ Code examples provided for common patterns

### User Experience Requirements

- ✅ Orchestrator responds to events within 1 second of occurrence
- ✅ No manual intervention required after spawning agents
- ✅ Token-efficient (waiting is free, only processing costs tokens)
- ✅ Works in multi-terminal mode (orchestrator + N agents in separate shells)

---

## Non-Goals (Out of Scope)

- ❌ WebSocket integration for GUI dashboard (use existing WebSocket infrastructure)
- ❌ Event persistence (events are transient, not stored in database)
- ❌ Event replay/history (orchestrators process events once)
- ❌ Priority queue for events (events processed in order received)
- ❌ Event acknowledgment protocol (simple fire-and-forget)

---

## Security Considerations

### Tenant Isolation

- **CRITICAL**: Events MUST be filtered by tenant_key
- Orchestrators cannot see events from other tenants
- Test cross-tenant isolation thoroughly

### Timeout Limits

- Minimum: 10 seconds (prevent abuse)
- Maximum: 120 seconds (prevent connection starvation)
- Default: 60 seconds (safe for proxies/firewalls)

### DoS Prevention

- Limit concurrent long-poll connections per tenant (future enhancement)
- Monitor memory usage of pending events (future enhancement)

---

## Performance Considerations

### Memory

- Pending events stored in-memory (not database)
- Events cleared after delivery (no accumulation)
- Waiter cleanup on timeout/cancellation

### Scalability

- Single-server deployment (no distributed coordination needed)
- Event monitor is singleton (shared across all requests)
- Asyncio-based (efficient for I/O-bound workload)

### Connection Limits

- Default HTTP client timeout: 70 seconds (allows 60s long-poll + overhead)
- Proxy/firewall considerations: 60s is safe for most environments
- Future: Make timeout configurable per deployment

---

## Migration Path

### Backwards Compatibility

- **No breaking changes**: Existing MCP tools unchanged
- **Opt-in**: Orchestrators can ignore `wait_for_notifications()` (existing behavior preserved)
- **Graceful degradation**: If server doesn't support tool, orchestrators fall back to manual checking

### Rollout Plan

1. **Phase 1**: Deploy tool, update docs (orchestrators still use manual checking)
2. **Phase 2**: Update orchestrator instructions to include monitoring loop
3. **Phase 3**: Monitor production usage, tune timeout defaults
4. **Phase 4**: Mark manual checking as deprecated (future handover)

---

## Future Enhancements (Not in 0419)

### Priority Queue

- High-priority events jump queue
- Low-priority events batch together
- Configurable priority thresholds

### Event Persistence

- Store events in database for replay
- Orchestrator crash recovery
- Event history API for debugging

### Advanced Filtering

- Filter by agent_name pattern
- Filter by priority level
- Filter by time range

### Metrics & Monitoring

- Average wait time per orchestrator
- Event throughput (events/second)
- Connection pool utilization

---

## References

### Handovers

- **0416**: Agent Status State Machine Enhancement (status transitions)
- **0246a**: Orchestrator Staging Workflow (7-task protocol)
- **0246b**: Generic Agent Template (6-phase protocol)
- **0334**: HTTP-only MCP transport (removed stdio)

### Documentation

- `docs/ORCHESTRATOR.md` - Orchestrator architecture and protocol
- `docs/components/STAGING_WORKFLOW.md` - 7-task staging workflow
- `docs/api/MCP_TOOLS_MANUAL.md` - MCP tools reference
- `docs/TESTING.md` - Testing standards and patterns

### Code References

- `src/giljo_mcp/tools/orchestration.py` - Orchestration tools
- `src/giljo_mcp/agent_job_manager.py` - Agent lifecycle and events
- `src/giljo_mcp/tools/messaging.py` - Inter-agent messaging

### External Patterns

- **AWS SQS Long Polling**: https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-short-and-long-polling.html
- **Kubernetes Watch API**: https://kubernetes.io/docs/reference/using-api/api-concepts/#efficient-detection-of-changes
- **HTTP Long Polling (MDN)**: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events#long_polling

---

## Checklist for Implementation Agent

Before starting implementation:

- [ ] Read all referenced handovers (0416, 0246a, 0246b, 0334)
- [ ] Read `docs/ORCHESTRATOR.md` and `docs/TESTING.md`
- [ ] Review `src/giljo_mcp/tools/orchestration.py` structure
- [ ] Review `src/giljo_mcp/agent_job_manager.py` event emission
- [ ] Understand TDD protocol (tests first, then implementation)

During implementation:

- [ ] Write unit tests FIRST (Phase 1)
- [ ] Implement `OrchestrationEventMonitor` class
- [ ] Implement `wait_for_notifications()` MCP tool
- [ ] Run tests (should pass), verify coverage >80%
- [ ] Write integration tests FIRST (Phase 2)
- [ ] Integrate event emission in `AgentJobManager`
- [ ] Integrate event emission in `send_message()`
- [ ] Run integration tests (should pass)
- [ ] Update documentation (Phase 3)
- [ ] Run E2E validation (Phase 4)

Before marking complete:

- [ ] All tests pass (unit + integration)
- [ ] Coverage >80% for new code
- [ ] Documentation updated and reviewed
- [ ] E2E scenario validated manually
- [ ] No breaking changes to existing tools
- [ ] Cross-platform compatibility verified (Windows + one other OS if possible)

---

**END OF HANDOVER 0419**
