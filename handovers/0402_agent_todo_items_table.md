# Handover 0402: Agent TODO Items Table

**Date:** 2026-01-02
**From Agent:** Orchestrator Session
**To Agent:** database-expert, tdd-implementor, ux-designer
**Priority:** High
**Estimated Complexity:** 2-3 hours
**Status:** Complete

---

## Task Summary

Create a proper database table for agent TODO items instead of storing them in JSONB. This enables the Plan/TODOs tab in the Message Audit modal to display what agents are actually working on, with real-time updates.

**Why:** Current `job_metadata.todo_steps` only stores counts (completed_steps, total_steps), not the actual TODO items. The Plan/TODOs tab shows `(0)` because no data populates it.

**Expected Outcome:** Agents report their TODO list via `report_progress()`, items are stored in a proper table, and the UI displays them in real-time.

---

## Technical Details

### New Database Table

```sql
CREATE TABLE agent_todo_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES agent_jobs(job_id) ON DELETE CASCADE,
    tenant_key VARCHAR(64) NOT NULL,
    content VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, in_progress, completed
    sequence INT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_status CHECK (status IN ('pending', 'in_progress', 'completed'))
);

-- Indexes for performance
CREATE INDEX idx_todo_items_job ON agent_todo_items(job_id);
CREATE INDEX idx_todo_items_tenant_status ON agent_todo_items(tenant_key, status);
CREATE INDEX idx_todo_items_job_sequence ON agent_todo_items(job_id, sequence);
```

### Files to Modify

| File | Changes |
|------|---------|
| `src/giljo_mcp/models/agent_identity.py` | Add `AgentTodoItem` model |
| `src/giljo_mcp/services/orchestration_service.py` | Update `report_progress()` to store items |
| `api/websocket.py` | Include todo_items in progress events |
| `frontend/src/stores/agentJobsStore.js` | Handle todo_items in progress updates |
| `frontend/src/components/projects/MessageAuditModal.vue` | Display items in Plan/TODOs tab |
| `install.py` | Add migration for new table |

### Backend Changes

**1. Update `report_progress()` in orchestration_service.py:**

Accept new `todo_items` field in progress dict:
```python
progress = {
    "mode": "todo",
    "completed_steps": 3,
    "total_steps": 5,
    "current_step": "Running tests",
    "percent": 60,
    "todo_items": [
        {"content": "Set up database", "status": "completed"},
        {"content": "Create endpoints", "status": "completed"},
        {"content": "Run tests", "status": "in_progress"},
        {"content": "Write docs", "status": "pending"},
        {"content": "Deploy", "status": "pending"}
    ]
}
```

**2. Update agent instructions template:**

Location: `orchestration_service.py` lines 239-261 (CRITICAL: Sync TodoWrite section)

Add `todo_items` to the example call so agents know to include it.

**3. WebSocket event payload:**

Include `todo_items` array in `job:progress_update` event.

### Frontend Changes

**1. agentJobsStore.js - handleProgressUpdate():**

Store `todo_items` on the job object for UI access.

**2. MessageAuditModal.vue - Plan/TODOs tab:**

Replace message filtering with display of `agent.todo_items`:
```vue
<div v-for="item in todoItems" :key="item.id" class="todo-item">
  <v-icon :icon="getStatusIcon(item.status)" :color="getStatusColor(item.status)" />
  <span>{{ item.content }}</span>
</div>
```

Status icons:
- `pending`: `mdi-checkbox-blank-outline` (gray)
- `in_progress`: `mdi-progress-clock` (orange, animated)
- `completed`: `mdi-checkbox-marked` (green)

---

## Implementation Plan

### Phase 1: Database (database-expert)
1. Create SQLAlchemy model `AgentTodoItem`
2. Add migration to `install.py`
3. Add relationship to `AgentJob` model
4. Test migration idempotency

### Phase 2: Backend (tdd-implementor)
1. Write tests for todo_items storage
2. Update `report_progress()` to upsert items
3. Update agent instructions template
4. Include items in WebSocket payload
5. Verify existing step counts still work

### Phase 3: Frontend (ux-designer)
1. Update `handleProgressUpdate()` in store
2. Redesign Plan/TODOs tab to show items
3. Add status icons and animations
4. Real-time updates via WebSocket
5. Empty state when no items

---

## Testing Requirements

### Unit Tests
- `test_report_progress_stores_todo_items`
- `test_report_progress_updates_existing_items`
- `test_report_progress_maintains_step_counts`
- `test_todo_items_cascade_delete_with_job`

### Integration Tests
- Agent calls report_progress with items → DB stores them
- WebSocket broadcasts todo_items to frontend
- UI updates in real-time when items change

### Manual Testing
1. Start an agent job
2. Agent reports progress with todo_items
3. Open Message Audit modal → Plan/TODOs tab
4. Verify items display with correct status icons
5. Agent updates progress → verify real-time update

---

## Success Criteria

- [x] New `agent_todo_items` table created with proper indexes
- [x] `report_progress()` accepts and stores `todo_items`
- [x] Agent instructions include `todo_items` in example
- [x] WebSocket event includes `todo_items`
- [x] Plan/TODOs tab displays items with status icons
- [x] Real-time updates work
- [x] Existing step counts (Steps column) still work
- [x] All tests pass

---

## Token Impact

- Per-call overhead: +70-80 tokens (for 5 items)
- Total per agent: ~400-800 tokens additional
- Overhead percentage: <1% of agent context budget

---

## Related

- Handover 0401b: Message counter fixes (just completed)
- Handover 0297: Steps column tracking
- Handover 0386: Direct WebSocket for progress

---

## Progress Updates

### 2026-01-02 - Initial Creation
**Status:** Complete
**Notes:** Created from discussion about Plan/TODOs tab not being populated. Decision made to use proper table instead of JSONB for SaaS scalability.

### 2026-01-02 - Implementation Complete
**Status:** Complete
**Commit:** `5c09bbab`
**Changes:**
- Phase 1 (Database): Created `AgentTodoItem` model with indexes, constraints, cascade delete
- Phase 2 (Backend): Updated `report_progress()` to store todo_items, include in WebSocket
- Phase 3 (Frontend): Redesigned Plan/TODOs tab with status icons and animations
- Agent template updated with todo_items example in report_progress() call
**Token Impact:** ~70-80 tokens per call (<1% overhead)
