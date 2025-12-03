# Handover 0066 - Critical Updates & Clarifications

**Date**: 2025-10-28
**Status**: ADDENDUM to main handover

---

## Critical Changes to Original Spec

### 1. **4 Columns (NOT 5, NOT drag-drop)**

**Original**: 5 columns with drag-drop
**Updated**: 4 columns with agent self-navigation

**Columns**:
1. **Pending** - Jobs created, waiting for agent to start
2. **Active** - Jobs in progress (agent working)
3. **Completed** - Jobs finished successfully
4. **BLOCKED** - Jobs failed OR waiting for feedback (combined status)

### 2. **NO Drag-Drop Functionality**

**REMOVE** all vuedraggable code and drag-drop references.

**Why**: Agents move themselves between columns using MCP tools. Developers cannot manually move cards.

**Agent Self-Navigation**:
- **Codex/Gemini**: Job assignment includes MCP instructions to update status
- **Claude Code**: Agent templates have strict MCP instructions to report progress
- Agents call MCP tool: `update_job_status(job_id, new_status)`

### 3. **Three Separate Message Counts**

**Original**: Single message count
**Updated**: Three badges per job card

```vue
<!-- Job Card Message Counts -->
<div class="message-counts">
  <v-chip size="x-small" color="error" v-if="unreadCount > 0">
    <v-icon start size="x-small">mdi-message-badge</v-icon>
    {{ unreadCount }} Unread
  </v-chip>

  <v-chip size="x-small" color="success">
    <v-icon start size="x-small">mdi-check-all</v-icon>
    {{ acknowledgedCount }} Read
  </v-chip>

  <v-chip size="x-small" color="grey">
    <v-icon start size="x-small">mdi-send</v-icon>
    {{ sentCount }} Sent
  </v-chip>
</div>
```

**Calculation**:
```javascript
// From MCPAgentJob.messages JSONB array
const unreadCount = job.messages.filter(m => m.status === 'pending').length
const acknowledgedCount = job.messages.filter(m => m.status === 'acknowledged').length
const sentCount = job.messages.filter(m => m.from === 'developer').length
```

### 4. **Developer Messaging to Agents**

**New Feature**: Developers can send messages to individual agents OR broadcast to all

```vue
<!-- Message Composition -->
<v-card>
  <v-card-title>Send Message to Agents</v-card-title>
  <v-card-text>
    <v-select
      v-model="messageTarget"
      :items="messageTargets"
      label="Send to"
    >
      <v-list-item value="all">Broadcast to All Agents</v-list-item>
      <v-list-item
        v-for="agent in activeAgents"
        :key="agent.id"
        :value="agent.id"
      >
        {{ agent.name }} ({{ agent.type }})
      </v-list-item>
    </v-select>

    <v-textarea
      v-model="messageContent"
      label="Message"
      rows="4"
    />

    <!-- Warning for paused agents -->
    <v-alert
      v-if="hasPausedAgents"
      type="warning"
      variant="tonal"
    >
      Some agents are paused. They must be reactivated to read new messages.
    </v-alert>

    <v-btn color="primary" @click="sendMessage">
      Send Message
    </v-btn>
  </v-card-text>
</v-card>
```

### 5. **Navigation Label**

**Original**: "Messages" or "Agent Dashboard"
**Updated**: "**Jobs**" in sidebar navigation

### 6. **Integration with Project Launch Panel**

**Original**: Standalone replacement for Messages page
**Updated**: **Tab 2** of Project Launch Panel (from Handover 0062)

```vue
<!-- Project Launch Panel Tabs -->
<v-tabs v-model="activeTab">
  <v-tab value="launch">Launch Panel</v-tab>
  <v-tab value="jobs">Active Jobs</v-tab> <!-- Kanban board here -->
</v-tabs>
```

### 7. **BLOCKED Column Behavior**

**Triggers for BLOCKED status**:
- Agent reports failure (error, exception, unable to proceed)
- Agent requests human input (`request_feedback` MCP tool)
- Job timeout (optional future enhancement)

**Developer Actions**:
- Review blocked job details
- Send clarifying message to agent
- Manually mark as "active" to retry
- OR mark as "completed" if acceptable state

---

## Updated Backend Endpoint

### Remove Drag-Drop Status Update

**DELETE** the `PATCH /{job_id}/status` endpoint (lines 361-420 in original spec)

**REPLACE WITH** MCP Tool for Agents:

```python
# src/giljo_mcp/tools/update_job_status.py

@mcp.tool()
async def update_job_status(
    job_id: str,
    new_status: str,
    reason: Optional[str] = None
) -> dict:
    """
    Update job status (for agent self-navigation).

    Args:
        job_id: Job identifier
        new_status: One of: pending, active, completed, blocked
        reason: Optional reason for status change

    Returns:
        Updated job details

    Used by agents to move themselves between Kanban columns.
    """
    # Validate status
    valid_statuses = ["pending", "active", "completed", "blocked"]
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

    # Update job in database
    async with get_db_session() as db:
        job = await get_job_by_id(db, job_id)

        if not job:
            raise ValueError(f"Job {job_id} not found")

        old_status = job.status
        job.status = new_status

        # Update timestamps
        if new_status == "active" and not job.started_at:
            job.started_at = datetime.utcnow()
        elif new_status in ["completed", "blocked"]:
            job.completed_at = datetime.utcnow()

        # Log reason
        if reason:
            job.status_reason = reason

        await db.commit()

        # Broadcast WebSocket event
        await broadcast_job_update(job_id, old_status, new_status)

    return {
        "success": True,
        "job_id": job_id,
        "old_status": old_status,
        "new_status": new_status
    }
```

---

## Updated Frontend Components

### Remove vuedraggable

**package.json**: Remove `vuedraggable` dependency

### KanbanColumn Component - NO Draggable

```vue
<template>
  <div class="kanban-column">
    <v-card class="column-header">
      <v-card-title>
        <v-icon :color="color">{{ icon }}</v-icon>
        {{ title }}
        <v-chip size="small" :color="color">{{ jobs.length }}</v-chip>
      </v-card-title>
    </v-card>

    <!-- Simple list (NO draggable) -->
    <div class="column-content">
      <job-card
        v-for="job in jobs"
        :key="job.job_id"
        :job="job"
        :color="color"
        @view-details="$emit('view-job', job)"
        @view-messages="$emit('view-messages', job.job_id)"
      />

      <!-- Empty state -->
      <v-card v-if="jobs.length === 0" variant="outlined">
        <v-card-text class="text-center text-grey">
          No {{ title.toLowerCase() }} jobs
        </v-card-text>
      </v-card>
    </div>
  </div>
</template>

<script setup>
// NO import of draggable
// NO drag event handlers
// Cards are read-only for developers
</script>
```

### JobCard - Three Message Counts

```vue
<template>
  <v-card class="job-card">
    <!-- Existing content -->

    <!-- THREE message count badges -->
    <v-card-text>
      <div class="message-counts d-flex gap-1">
        <!-- Unread (red badge) -->
        <v-chip
          v-if="job.unread_messages > 0"
          size="x-small"
          color="error"
          @click.stop="$emit('view-messages')"
        >
          <v-icon start size="x-small">mdi-message-badge</v-icon>
          {{ job.unread_messages }}
        </v-chip>

        <!-- Acknowledged (green checkmark) -->
        <v-chip
          v-if="job.acknowledged_messages > 0"
          size="x-small"
          color="success"
        >
          <v-icon start size="x-small">mdi-check-all</v-icon>
          {{ job.acknowledged_messages }}
        </v-chip>

        <!-- Sent (grey) -->
        <v-chip
          v-if="job.sent_messages > 0"
          size="x-small"
          color="grey"
        >
          <v-icon start size="x-small">mdi-send</v-icon>
          {{ job.sent_messages }}
        </v-chip>
      </div>
    </v-card-text>
  </v-card>
</template>
```

---

## Agent Template Instructions

### For Claude Code (via Agent Templates)

Add to agent templates (Handover 0041):

```markdown
## MCP Status Reporting

You MUST report your progress using MCP tools:

1. **When starting work**: Call `update_job_status(job_id, "active")`
2. **When blocked**: Call `update_job_status(job_id, "blocked", reason="Describe issue")`
3. **When complete**: Call `update_job_status(job_id, "completed")`

Example:
```python
# At start of work
mcp.call_tool("update_job_status", {
    "job_id": "your-job-id",
    "new_status": "active"
})

# If blocked
mcp.call_tool("update_job_status", {
    "job_id": "your-job-id",
    "new_status": "blocked",
    "reason": "Need database schema clarification"
})
```
```

### For Codex/Gemini (in Job Assignment)

Job assignment payload includes instructions:

```json
{
  "job_id": "uuid",
  "mission": "Implement user authentication...",
  "mcp_instructions": {
    "status_reporting": {
      "on_start": "update_job_status(job_id='uuid', new_status='active')",
      "on_blocked": "update_job_status(job_id='uuid', new_status='blocked', reason='...')",
      "on_complete": "update_job_status(job_id='uuid', new_status='completed')"
    },
    "communication": {
      "broadcast": "Send messages to all agents via send_agent_message()",
      "request_help": "Message specific agent or request human feedback"
    }
  }
}
```

---

## Summary of Key Changes

| Aspect | Original 0066 | Updated 0066 |
|--------|--------------|--------------|
| Columns | 5 (Pending, Active, Completed, Failed, Feedback) | 4 (Pending, Active, Completed, BLOCKED) |
| Status Update | Drag-drop by user | MCP tools by agents |
| Message Count | Single count | Three counts (unread, ack, sent) |
| Developer Actions | Drag cards | Send messages only |
| Navigation | "Agent Dashboard" | "Jobs" |
| Integration | Standalone page | Tab 2 of Project Launch Panel |
| Dependencies | vuedraggable library | NO drag libraries |
| Complexity | HIGH (drag-drop + WebSocket) | MEDIUM (display + messaging) |
| Duration | 16-20 hours | 12-16 hours |

---

## Implementation Priority

**Sequence**:
1. ✅ Complete Handover 0062 (Project Launch Panel + DB migration)
2. ⏭️ Implement Handover 0066 (Kanban as Tab 2)
3. ⏭️ Update agent templates with MCP instructions
4. ⏭️ Test agent self-navigation workflow

**No Handover 0067 Needed**: Scope is manageable at 12-16 hours

---

**This addendum supersedes conflicting instructions in the main 0066 handover.**

**End of Updates Document**
