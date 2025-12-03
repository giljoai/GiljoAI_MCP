# Handover 0106d: WebSocket Event Catalog (Reference)

**Date**: 2025-11-05
**Status**: 📚 REFERENCE CATALOG PROJECT
**Priority**: Medium (Documentation)
**Estimated Complexity**: 2-3 hours

---

## Purpose

Create comprehensive reference catalog of all WebSocket events used in the GiljoAI MCP system. Centralizes event specifications currently scattered across multiple handovers.

---

## Scope

### Events to Document

**From Handover 0107** (Agent Monitoring):
- `job:progress_update`
- `job:stale_warning`
- `agent:spawned` (dynamic spawning)

**From Existing System**:
- `job:status_changed`
- `job:completed`
- `job:failed`

**From Handover 0105 v1.0** (Removed but may exist):
- `mission_plan:created` (verify if still used)

**From Agent Job System**:
- `job:acknowledged`
- `job:blocked`

**From Projects**:
- `project:activated`
- `project:completed`

**From Orchestration**:
- `orchestrator:spawned`
- `orchestrator:succession`

**To Investigate**:
- Message queue events
- Template update events
- User settings events

---

## Catalog Format

For each event, document:

### **Event Name**: `event:action`

**Trigger**: When does this event fire?

**Payload**:
```json
{
  "event": "event:action",
  "data": {
    "field1": "type and description",
    "field2": "type and description"
  },
  "timestamp": "ISO 8601 format"
}
```

**Emitted By**: Which backend component sends this event?

**Consumed By**: Which frontend components listen for this event?

**Multi-Tenant**: Is tenant_key included for isolation?

**Example**:
```json
{
  "event": "job:progress_update",
  "data": {
    "job_id": "job-xyz789",
    "agent_id": "implementer-abc123",
    "progress": {
      "task": "Implementing authentication endpoints",
      "percent": 45,
      "todos_completed": 3,
      "todos_remaining": 5
    },
    "last_progress_at": "2025-11-05T14:30:00Z"
  },
  "timestamp": "2025-11-05T14:30:00Z"
}
```

**Frontend Handler**:
```javascript
socket.on('job:progress_update', (data) => {
  store.commit('jobs/updateProgress', data)
  // Update UI: agent card progress bar
})
```

---

## Investigation Tasks

### Step 1: Source Code Audit

**Files to Review**:
- `api/websocket.py` - Event emission
- `frontend/src/services/websocket.js` - Event handlers
- `api/endpoints/*.py` - Event triggers
- `frontend/src/store/*.js` - Event consumers

**Method**: Search for all `broadcast_`, `emit_`, `socket.on` patterns

---

### Step 2: Event Mapping

**Create Matrix**:
| Event Name | Backend Source | Frontend Handler | Handover Reference |
|------------|---------------|------------------|-------------------|
| job:progress_update | agent_job_manager.py:123 | websocket.js:45 | 0107 |
| ... | ... | ... | ... |

---

### Step 3: Payload Schemas

**Define TypeScript/JSON Schema** for each event payload:

```typescript
// Example
interface JobProgressUpdateEvent {
  event: "job:progress_update";
  data: {
    job_id: string;
    agent_id: string;
    progress: {
      task: string;
      percent: number;  // 0-100
      todos_completed: number;
      todos_remaining: number;
      context_tokens_estimate?: number;
    };
    last_progress_at: string;  // ISO 8601
  };
  timestamp: string;  // ISO 8601
}
```

---

### Step 4: Testing Guide

**For Each Event**:
- How to trigger manually (for testing)
- Expected UI behavior
- How to verify in browser DevTools
- Common issues and solutions

---

## Output Format

**Primary File**: `docs/reference/WEBSOCKET_EVENT_CATALOG.md`

**Structure**:
```markdown
# WebSocket Event Catalog

## Table of Contents
1. Job Lifecycle Events
2. Agent Coordination Events
3. Project Events
4. Orchestration Events
5. System Events

## Job Lifecycle Events

### job:progress_update
[Full spec here]

### job:status_changed
[Full spec here]

## Agent Coordination Events
...
```

**Secondary**: Quick Reference Card
- One-page summary of all events
- Event name + brief description
- For developers to keep handy

---

## Testing Requirements

### Manual Testing Checklist

For each event:
- [ ] Trigger event from backend
- [ ] Verify payload structure in browser DevTools
- [ ] Confirm frontend handler executes
- [ ] Verify UI updates correctly
- [ ] Test multi-tenant isolation (event only to correct tenant)

---

## Success Criteria

- [ ] All WebSocket events documented
- [ ] Payload schemas defined (JSON/TypeScript)
- [ ] Frontend handlers mapped
- [ ] Backend emission points documented
- [ ] Testing guide included
- [ ] Reference catalog published
- [ ] Quick reference card created

---

## Dependencies

**Related Handovers**:
- 0107 (Agent monitoring events)
- 0105 (Mission workflow events)
- Agent Job Management (Handover 0019)
- Orchestrator Succession (Handover 0080)

---

## Notes

**Version**: 1.0 (Catalog Project)
**Last Updated**: 2025-11-05
**Author**: System Architect
**Status**: Not started - Investigation required

**Estimated Effort**:
- Source code audit: 1 hour
- Event documentation: 1-2 hours
- Schema definition: 30 minutes
- Testing guide: 30 minutes
- **Total: 2-3 hours**

**Priority**: Medium (documentation/reference material, not blocking implementation)
