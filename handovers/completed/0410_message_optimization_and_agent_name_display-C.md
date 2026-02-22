# Handover 0410: Message Display UX Fix

**Date**: 2026-02-21 (rewritten; original 2026-01-05)
**From Agent**: Research session
**To Agent**: Next Session
**Priority**: HIGH
**Status**: Ready for Implementation
**Estimated Effort**: 2-3 hours
**Depends On**: None (self-contained)

---

## Task Summary

Every message in the Message Audit modal shows recipient as "Broadcast" due to a field name mismatch between backend and frontend. Additionally, recipient names are never resolved to human-readable display names. This handover fixes message display across backend API and frontend components so users see clear "From [Name] / To [Name]" with full UUIDs available in detail views.

## Context and Background

- **Original 0410** (2026-01-05): Proposed `message_check` MCP tool + sender name fix. Sender resolution was completed by handovers 0414/0500. The `message_check` tool is CLOSED as LOW VALUE (0.3% token savings; counter-based messaging 0387e already exists).
- **Current bug**: Backend sends `to_agents` (JSONB array). Frontend reads `to_agent_id` (scalar string). Field never exists -> every message = "Broadcast".
- **Related handovers**: 0387 (broadcast fan-out), 0414 (agent_display_name), 0500 (sender resolution)

---

## Current Code (What You'll Be Modifying)

### Backend: Message Response Builder

**File**: `api/endpoints/agent_jobs/messages.py`

Endpoint signature (line 57):
```python
@router.get("/{job_id}/messages")
async def get_job_messages(job_id, limit, current_user, session):
```

Agent lookup construction (lines 99-112):
```python
agents_stmt = select(AgentExecution).where(AgentExecution.tenant_key == current_user.tenant_key)
agents_result = await session.execute(agents_stmt)
agents = agents_result.scalars().all()
agent_lookup = {}
for agent in agents:
    display_name = agent.agent_display_name.capitalize() if agent.agent_display_name else "Agent"
    agent_lookup[agent.agent_id] = display_name
    if agent.agent_name:
        agent_lookup[agent.agent_name] = display_name
```

Response builder (lines 136-156) - **this is where recipient fields are missing**:
```python
message_list.append({
    "id": str(m.id),
    "from": resolved_from,              # Resolved sender name (WORKS)
    "from_agent": raw_from_agent,        # Raw sender value (WORKS)
    "from_agent_id": raw_from_agent if raw_from_agent in agent_lookup else None,
    "to_agents": m.to_agents,            # Raw UUID array - NO NAME RESOLUTION
    "content": m.content[:500] if m.content else "",
    "status": m.status,
    "created_at": m.created_at.isoformat(),
    "direction": "outbound" if is_outbound else "inbound",
    "message_type": m.message_type,
    # MISSING: "to" (resolved recipient name)
    # MISSING: "to_agent_id" (single recipient UUID)
})
```

Sender resolution function (lines 24-54) - `_resolve_sender_display_name()` already works. Reuse its pattern for recipients.

### Backend: Fan-out in send_message()

**File**: `src/giljo_mcp/services/message_service.py`

Broadcast resolution (lines 178-201) expands `"all"` to individual agent IDs, excluding sender:
```python
for agent_ref in to_agents:
    if agent_ref == "all":
        # ... queries active agents in project ...
        for execution in executions:
            if sender_ref in (execution.agent_display_name, execution.agent_id):
                continue  # Skip sender
            resolved_to_agents.append(execution.agent_id)
```

Message creation (lines 234-258) - `message_type` is passed through as-is:
```python
message = Message(
    to_agents=[recipient_id],
    message_type=message_type,  # <-- LINE 243: NOT overridden to "broadcast" during fan-out
    meta_data={"_from_agent": from_agent or "orchestrator", "job_id": project.id},
)
```

**Problem**: When `send_message(to_agents=["all"], message_type="direct")` is called, fan-out creates individual rows but keeps `message_type="direct"`. Only `broadcast()` (line 571) explicitly passes `message_type="broadcast"`. This means the frontend cannot distinguish fan-out-expanded broadcasts from direct messages.

### Frontend: MessageAuditModal.vue

**File**: `frontend/src/components/projects/MessageAuditModal.vue`

`formatRecipient()` (lines 328-345) - **the broken function**:
```javascript
function formatRecipient(message) {
  const toBroadcast = message.to_agents?.includes('all') ||
                      message.message_type === 'broadcast' ||
                      !message.to_agent_id  // <-- ALWAYS true (field never sent by backend)
  if (toBroadcast) return 'Broadcast'  // <-- ALWAYS returns here
  const toAgentId = message.to_agent_id  // Dead code below
  if (toAgentId) { return `${toAgentId.slice(0, 8)}...` }
  return 'Unknown'
}
```

`formatMessageMeta()` (lines 358-372) - **dead code, never called**. DELETE.

Stale filter (line 229):
```javascript
const sentMessages = computed(() =>
  messages.value.filter((m) => m.from === 'developer' || m.direction === 'outbound')
)
```
`m.from === 'developer'` is stale - backend sends `"User"`, not `"developer"`. Works only because `direction === 'outbound'` saves it. Clean up.

Message row template (lines 107-148) shows: `To: {{ formatRecipient(message) }}` - always "Broadcast".

### Frontend: MessageDetailView.vue

**File**: `frontend/src/components/projects/MessageDetailView.vue` (lines 10-21)

```html
<div class="meta-row">
  <strong>From:</strong>
  <span>{{ message.from || 'unknown' }}</span>          <!-- WORKS -->
</div>
<div class="meta-row">
  <strong>From Agent ID:</strong>
  <code>{{ message.from_agent_id || 'User' }}</code>    <!-- Shows UUID or "User" -->
</div>
<div class="meta-row">
  <strong>To Agent ID:</strong>
  <code>{{ message.to_agent_id || 'Broadcast' }}</code> <!-- BROKEN: field never sent -->
</div>
```

### Database: Message Model

**File**: `src/giljo_mcp/models/tasks.py` (lines 118-163)

```python
class Message(Base):
    __tablename__ = "messages"
    to_agents = Column(JSONB, default=list)           # Line 129 - stores [single_agent_id] after fan-out
    message_type = Column(String(50), default="direct") # Line 130 - "direct" or "broadcast"
    meta_data = Column(JSONB, default=dict)            # Line 141 - {"_from_agent": "...", "job_id": "..."}
```

No schema changes needed - all fixes are in the API layer and frontend.

---

## Implementation Plan

### Phase 1: Quick Fixes (15 min)

1. **DELETE** `formatMessageMeta()` in `MessageAuditModal.vue` (lines 358-372) - dead code
2. **FIX** stale `m.from === 'developer'` check in `MessageAuditModal.vue` (line 229) - remove it, `direction === 'outbound'` is sufficient

### Phase 2: Backend - Broadcast Signal + Recipient Resolution (45 min)

**File**: `src/giljo_mcp/services/message_service.py`

1. At line 243 in the fan-out loop, override `message_type` when the original `to_agents` contained `"all"`:
```python
# Add a flag before the fan-out loop (around line 177):
is_broadcast_fanout = "all" in to_agents

# Then at line 243:
message_type="broadcast" if is_broadcast_fanout else message_type,
```

**File**: `api/endpoints/agent_jobs/messages.py`

2. In the response builder (lines 136-156), add recipient resolution using the existing `agent_lookup`:
```python
# After resolved_from, add:
to_agent_id = m.to_agents[0] if m.to_agents else None
if m.message_type == "broadcast":
    resolved_to = "All Agents"
elif to_agent_id and to_agent_id in agent_lookup:
    resolved_to = agent_lookup[to_agent_id]
else:
    resolved_to = to_agent_id or "Unknown"

# Add to response dict:
"to": resolved_to,
"to_agent_id": to_agent_id,
```

### Phase 3: Frontend - Display Fix (45 min)

**File**: `frontend/src/components/projects/MessageAuditModal.vue`

1. Rewrite `formatRecipient()`:
```javascript
function formatRecipient(message) {
  return message.to || 'Unknown'
}
```

2. Message row (line 119): `To: {{ formatRecipient(message) }}` - now shows resolved name

**File**: `frontend/src/components/projects/MessageDetailView.vue`

3. Replace lines 10-21 with:
```html
<div class="meta-row">
  <strong>From:</strong>
  <span>{{ message.from || 'unknown' }}</span>
</div>
<div class="meta-row">
  <strong>From Agent ID:</strong>
  <code class="text-mono">{{ message.from_agent_id || 'N/A' }}</code>
</div>
<div class="meta-row">
  <strong>To:</strong>
  <span>{{ message.to || 'Unknown' }}</span>
</div>
<div class="meta-row">
  <strong>To Agent ID:</strong>
  <code class="text-mono">{{ message.to_agent_id || 'N/A' }}</code>
</div>
```

### Phase 4: Tests (30 min)

Write TDD tests before implementing Phase 2-3. Test files:
- `tests/test_0410_message_display.py` (new)

| Test | Assertion |
|------|-----------|
| Direct message response includes `to` with resolved name | `response["to"] == "Implementer"` |
| Direct message response includes `to_agent_id` as UUID | UUID format validation |
| Broadcast message response shows `to` as "All Agents" | `response["to"] == "All Agents"` |
| Broadcast fan-out preserves `message_type="broadcast"` | `msg.message_type == "broadcast"` |
| Sender resolution still works | `response["from"] == "Orchestrator"` |
| Tenant isolation respected | Standard tenant_key filtering |
| Empty `to_agents` handled gracefully | `response["to"] == "Unknown"` |

---

## Entity Hierarchy Cascading Analysis

```
Organization -> User -> Product -> Project -> Job -> Agent
                                      |
                                      +-> Message (belongs to project)
```

**Downstream impact**: None. Messages are read-only display. No changes to how messages are created, stored, or acknowledged.

**Upstream impact**: None. The Message model is unchanged. The `to_agents` JSONB column and `message_type` column are unmodified in schema.

**Sibling impact**: The `message_type` value change (fan-out now stores `"broadcast"` instead of `"direct"`) affects only the display layer. The `receive_messages()` MCP tool queries by `to_agents` containment, not by `message_type`, so agent message retrieval is unaffected.

## Installation Flow Impact

**None.** No database schema changes. No new columns, no migrations. All changes are in the API response builder and frontend display logic.

## Dependencies and Blockers

None. All required infrastructure exists:
- `agent_lookup` dict already built in `messages.py`
- `_resolve_sender_display_name()` pattern available for reuse
- Fan-out already works correctly for message delivery

## Rollback Plan

All changes are in 4 files with no schema impact. Git revert of the commit(s) fully rolls back. No data migration needed.

## Files to Modify (Complete List)

| File | Phase | Change |
|------|-------|--------|
| `src/giljo_mcp/services/message_service.py` | 2 | Override `message_type="broadcast"` during fan-out (line 243) |
| `api/endpoints/agent_jobs/messages.py` | 2 | Add `to`, `to_agent_id` fields with name resolution (lines 136-156) |
| `frontend/src/components/projects/MessageAuditModal.vue` | 1,3 | Delete dead code, fix `formatRecipient()`, fix stale filter |
| `frontend/src/components/projects/MessageDetailView.vue` | 3 | Show resolved To name + full UUIDs |
| `tests/test_0410_message_display.py` | 4 | New TDD test file |

## Success Criteria

1. Received messages show "From [Agent Name]" - never raw UUID, never "User" for agents
2. Sent direct messages show "To [Agent Name]"
3. Sent broadcasts show "To All Agents"
4. Detail view shows both resolved name AND full UUID for sender and recipient
5. No regressions to `send_message` / `receive_messages` MCP tools
6. Broadcast fan-out still excludes sender, still creates per-recipient rows
7. All new tests pass, zero regressions

---

## History

### Original 0410 (2026-01-05)
- Fix 1 (message_check MCP tool): CLOSED as LOW VALUE (0.3% token savings; counter-based messaging exists)
- Fix 2 (sender name display): Sender resolution implemented by 0414/0500

### Rewrite (2026-02-21)
- Refocused on recipient display bug: field mismatch + missing name resolution + broadcast signal lost in fan-out
- Added full code references with line numbers for self-contained implementation
