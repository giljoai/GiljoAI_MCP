# Handover 0410: Message Optimization and Agent Name Display

**Status**: Ready for Implementation
**Priority**: HIGH (message_check) / MEDIUM (agent name display)
**Estimated Effort**: 45 minutes total
**Created**: 2026-01-05

---

## Executive Summary

Two fixes identified from alpha project analysis (TinyContacts folder structure setup):

1. **message_check MCP Tool** - Lightweight y/n check before full message retrieval
2. **Dashboard Agent Name Display** - Resolve agent UUID to name instead of showing "User"

### Alpha Project Metrics

| Metric | Actual | Optimal | Waste |
|--------|--------|---------|-------|
| Time | 32 min | 8-10 min | ~22 min |
| Tokens | 145K | 40-50K | ~100K |
| MCP Calls | ~227 | ~160 | ~67 calls |

Primary overhead source: **~25 empty receive_messages() calls** (count: 0 returns).

---

## FIX 1: Add Lightweight message_check MCP Tool

### Problem

Agents call `receive_messages()` after every TodoWrite item completion (~6-7 times per agent). The current protocol mandates this per Phase 2 EXECUTION:

```
**MESSAGE CHECK**: Call receive_messages() after completing each TodoWrite task
```

Evidence from alpha project log:

```
Line 179-192:
  giljo-mcp - receive_messages (MCP)(agent_id: "6eac2882-2162-41a3-b4c8-dff4c22fa6fd", ...)
  {
    "success": true,
    "data": {
      "messages": [],
      "count": 0    ← EMPTY - wasted call
    }
  }
```

Per-agent pattern observed:
- Analyzer: 6 receive_messages calls, 5 returned empty
- Implementer: 7 receive_messages calls, 6 returned empty
- Documenter: 7 receive_messages calls, 6 returned empty
- Reviewer: 6 receive_messages calls, 5 returned empty

**Total: ~25 unnecessary MCP calls per project** (each costs tokens + latency)

### Solution

Add a lightweight `message_check` MCP tool that returns a simple y/n flag. Agents only call full `receive_messages()` when messages actually exist.

### New MCP Tool Schema

```python
@mcp_tool(name="message_check")
async def message_check(
    agent_id: str,
    tenant_key: str,
    session: AsyncSession = Depends(get_session)
) -> dict:
    """
    Lightweight check for pending messages.

    Does NOT:
    - Auto-acknowledge messages
    - Return message content
    - Perform any writes

    Agent calls receive_messages() only if pending == "y".

    Args:
        agent_id: Executor UUID (from get_agent_mission response)
        tenant_key: Tenant isolation key

    Returns:
        {"pending": "y"} if messages waiting
        {"pending": "n"} if queue empty
    """
    from sqlalchemy import select, func
    from src.giljo_mcp.models import Message

    count = await session.scalar(
        select(func.count(Message.id)).where(
            Message.to_agent == agent_id,
            Message.acknowledged == False,
            Message.tenant_key == tenant_key
        )
    )

    return {"pending": "y" if count > 0 else "n"}
```

### Protocol Update

**Current** (in full_protocol):
```
### Phase 2: EXECUTION
Execute your assigned tasks (TodoWrite created in Phase 1):
- **MESSAGE CHECK**: Call receive_messages() after completing each TodoWrite task
  - Full call: mcp__giljo-mcp__receive_messages(agent_id="...", tenant_key="...")
  - If queue not empty: Process messages BEFORE continuing
  - If queue empty: Safe to proceed
```

**Updated**:
```
### Phase 2: EXECUTION
Execute your assigned tasks (TodoWrite created in Phase 1):
- **MESSAGE CHECK**: After completing each TodoWrite task:
  1. Call mcp__giljo-mcp__message_check(agent_id="...", tenant_key="...")
  2. IF pending == "y": Call mcp__giljo-mcp__receive_messages(agent_id="...", tenant_key="...")
  3. IF pending == "n": Continue to next task (skip full retrieval)
```

### Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/tools/messaging/message_check.py` | New file - implement tool |
| `src/giljo_mcp/tools/__init__.py` | Register message_check in tool exports |
| `src/giljo_mcp/services/orchestration_service.py` | Update full_protocol template (~line 760) |
| `tests/tools/test_message_check.py` | New file - unit tests |

### Expected Savings

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| receive_messages calls | ~25/project | ~5/project | ~20 calls |
| Tokens per empty call | ~150 | ~30 (message_check) | ~80% |
| Total token savings | - | - | ~2,400/project |

---

## FIX 2: Dashboard Agent Name Display

### Problem

Messages from agents display "From Agent ID: User" instead of the actual agent name.

Evidence from alpha project:

```
Message Details
From: 4d3f0841-428e-4fa9-85ef-0f2d70d32290
From Agent ID: User              ← WRONG! Should be "implementer"
To Agent ID: Broadcast
Direction: outbound
Status: sent
Timestamp: 1/5/2026, 10:40:56 PM
Content: COMPLETE: Folder structure implementation finished...
```

The UUID `4d3f0841-428e-4fa9-85ef-0f2d70d32290` IS the implementer agent (confirmed in log line 1246-1249). Dashboard isn't resolving UUID → agent_name.

### Root Cause

Dashboard shows `from_agent` UUID but falls back to "User" when no resolution logic exists.

### Solution Options

**Option A: Backend Resolution (Recommended)**

Add agent name to message API response:

```python
# In api/endpoints/messages/list.py or similar
async def list_messages(...):
    messages = await session.execute(
        select(Message).where(...)
    )

    result = []
    for msg in messages:
        # Resolve agent_id to agent_name
        agent = await session.scalar(
            select(AgentExecution).where(
                AgentExecution.agent_id == msg.from_agent
            )
        )

        result.append({
            **msg.dict(),
            "from_agent_name": agent.agent_name if agent else "User",
            "from_agent_type": agent.agent_type if agent else None
        })

    return result
```

**Option B: Frontend Resolution**

If agents list is available in context:

```javascript
// frontend/src/components/projects/MessageAuditModal.vue or similar
const getAgentDisplayName = (agentId, agentsList) => {
    if (!agentId) return "User"
    const agent = agentsList.find(a => a.agent_id === agentId)
    return agent?.agent_name || agent?.agent_type || agentId.slice(0, 8)
}

// Usage
<span>From: {{ getAgentDisplayName(message.from_agent, agents) }}</span>
```

### Files to Modify (Option A - Backend)

| File | Change |
|------|--------|
| `api/endpoints/messages/models.py` | Add `from_agent_name`, `from_agent_type` to response model |
| `api/endpoints/messages/list.py` | Join AgentExecution table for name resolution |
| `tests/endpoints/test_messages.py` | Update tests for new fields |

### Files to Modify (Option B - Frontend)

| File | Change |
|------|--------|
| `frontend/src/components/projects/MessageAuditModal.vue` | Add resolution function |
| `frontend/src/stores/agentJobsStore.js` | Ensure agent data available |

### Recommendation

Use **Option A (Backend)** because:
1. Single source of truth for agent name resolution
2. Works for all frontend components without duplication
3. Supports historical messages where agents may no longer be in current session

---

## Summary Table

| Fix | Priority | Effort | Impact |
|-----|----------|--------|--------|
| message_check tool | HIGH | 30 min | Eliminates ~20 wasted MCP calls per project |
| Dashboard agent name | MEDIUM | 15 min | UX clarity - shows who sent message |

---

## Testing Checklist

### message_check Tool
- [ ] Returns `{"pending": "y"}` when messages exist
- [ ] Returns `{"pending": "n"}` when queue empty
- [ ] Does NOT acknowledge messages (read-only)
- [ ] Respects tenant_key isolation
- [ ] Performance: < 10ms response time

### Agent Name Display
- [ ] Messages from agents show agent_name (not "User")
- [ ] Messages from actual users still show "User"
- [ ] Broadcast messages show correct sender
- [ ] Works with historical messages

---

## Related Context

### Alpha Project Stats (for reference)

| Agent | Tool Uses | Tokens | Time | Empty receive_messages |
|-------|-----------|--------|------|------------------------|
| Analyzer | 26 | 44.8K | 4m 19s | 5 |
| Implementer | 70 | 52.7K | 6m 13s | 6 |
| Documenter | 56 | 65.1K | 11m 28s | 6 |
| Reviewer | ~50 | ~30K | ~7m | 5 |
| **Total** | ~227 | ~145K | ~32m | **~22** |

### MCP Server Rating from Orchestrator

> "5/5 - Everything worked flawlessly. The thin-client architecture is solid.
> With message_check optimization, there'd be nothing to complain about."

---

## Implementation Notes

1. **message_check is a COUNT query** - very fast, no data transfer
2. **Keep receive_messages unchanged** - message_check is additive, not replacement
3. **Protocol update is template change** - no runtime code changes needed for protocol
4. **Agent name resolution should use LEFT JOIN** - messages from deleted agents should still display

---

## References

- Alpha project log: `F:\agent work.txt` (6,404 lines)
- Discussion notes: `F:\report and discussion after alpha p.txt`
- Message model: `src/giljo_mcp/models/messaging.py`
- Full protocol generator: `src/giljo_mcp/services/orchestration_service.py`
