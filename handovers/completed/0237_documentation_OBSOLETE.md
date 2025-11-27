# Handover 0237: Documentation

**⚠️ STATUS: OBSOLETE - SUPERSEDED by 0243 GUI Redesign**

**Original Status**: ~~Ready for Implementation~~ OBSOLETE
**Original Priority**: ~~Medium~~ N/A
**Original Estimated Effort**: ~~4 hours~~ Not needed
**Dependencies**: Handovers 0225-0236 (all complete)
**Part of**: Visual Refactor Series (0225-0237)

---

## Why This Is Obsolete

This handover was created to document the StatusBoard table components from the Visual Refactor Series (0225-0236). However:

1. **GUI Completely Redesigned**: The 0243 Nicepage series completely redesigned the GUI
2. **Components Superseded**: The StatusBoard components this would document have been replaced
3. **No Value in Documentation**: Writing docs for superseded components would be wasteful
4. **Series Complete**: The Visual Refactor Series is 100% complete and archived

## Historical Context

This was the final handover (0237) in the Visual Refactor Series, intended to document:
- StatusBoardTable component from 0234-0235
- User guide updates with table view screenshots
- API documentation for table endpoints
- Migration guide from cards to table

All of this work became irrelevant when the GUI was redesigned in the 0243 Nicepage series.

---

## Archive Note

This handover should be moved to `handovers/completed/` and marked as obsolete. The Visual Refactor Series (0225-0237) is complete, with this documentation task being unnecessary due to subsequent redesigns.

---

## Before You Begin

**REQUIRED READING** (Critical for TDD discipline and architectural alignment):

1. **F:\GiljoAI_MCP\handovers\QUICK_LAUNCH.txt**
   - TDD discipline (Red → Green → Refactor)
   - Write tests FIRST (behavior, not implementation)
   - No zombie code policy (delete, don't comment)

2. **F:\GiljoAI_MCP\handovers\013A_code_review_architecture_status.md**
   - Service layer patterns
   - Multi-tenant isolation
   - Component reuse principles

3. **F:\GiljoAI_MCP\handovers\code_review_nov18.md**
   - Past mistakes to avoid (ProductsView 2,582 lines)
   - Success patterns to follow (ProjectsView componentization)

**Execute in order**: Red (failing tests) → Green (minimal implementation) → Refactor (cleanup)

---

## Objective

Update all documentation to reflect the new status board table interface, including component usage guides, user documentation with updated screenshots, API reference documentation, and developer guides for extending the status board functionality.

---

## Current State Analysis

### Existing Documentation Structure

**Location**: `docs/`

**Current Documentation**:
- `docs/README_FIRST.md` - Project navigation hub
- `docs/GILJOAI_MCP_PURPOSE.md` - System overview
- `docs/SERVER_ARCHITECTURE_TECH_STACK.md` - Architecture documentation
- `docs/INSTALLATION_FLOW_PROCESS.md` - Installation guide
- `docs/USER_GUIDE.md` - User documentation
- `docs/API_REFERENCE.md` - API documentation
- `docs/DEVELOPER_GUIDE.md` - Developer documentation
- `docs/vision/` - Vision documents

**Documentation Gaps**:
- No component-specific documentation
- Screenshots show old card-based interface
- Missing table view endpoint documentation
- No WebSocket event reference for status board

---

## Implementation Plan

### 1. Component Documentation

**File**: `docs/components/StatusBoardTable.md` (NEW)

Create comprehensive component documentation:

```markdown
# StatusBoardTable Component

## Overview

The StatusBoardTable component displays agent jobs in a table format with real-time updates, advanced filtering, sorting, and action controls.

## Location

`frontend/src/components/StatusBoard/StatusBoardTable.vue`

## Features

- **Table View**: Displays agent jobs in a structured table layout
- **Real-Time Updates**: WebSocket integration for live status changes
- **Message Indicators**: Visual badges showing unread/acknowledged message counts
- **Health Monitoring**: Health indicators with pulse animations for critical states
- **Staleness Detection**: Automatic warnings for inactive agents (>10 minutes)
- **Action Controls**: Launch, copy, message, cancel, and hand over actions
- **Filtering**: Filter by status, health, unread messages, agent type
- **Sorting**: Sort by last activity, creation time, status, agent type
- **Pagination**: Server-side pagination for large datasets

## Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| projectId | String | Yes | - | Current project ID to display jobs for |
| claudeCodeCliMode | Boolean | No | false | Enable Claude Code CLI mode (affects launch buttons) |
| autoRefreshInterval | Number | No | 30000 | Auto-refresh interval in milliseconds (0 = disabled) |

## Events

| Event | Payload | Description |
|-------|---------|-------------|
| job-launched | { jobId: string } | Emitted when agent job is launched |
| job-cancelled | { jobId: string } | Emitted when agent job is cancelled |
| message-sent | { jobId: string, messageId: string } | Emitted when message is sent to agent |
| hand-over-triggered | { jobId: string } | Emitted when orchestrator handover is triggered |

## Usage

### Basic Usage

\`\`\`vue
<template>
  <StatusBoardTable
    :project-id="currentProject.project_id"
    :claude-code-cli-mode="settings.claudeCodeCliMode"
    @job-launched="handleJobLaunched"
    @job-cancelled="handleJobCancelled"
  />
</template>

<script>
import { ref } from 'vue';
import StatusBoardTable from '@/components/StatusBoard/StatusBoardTable.vue';

export default {
  components: {
    StatusBoardTable
  },

  setup() {
    const currentProject = ref({ project_id: 'test-project-123' });
    const settings = ref({ claudeCodeCliMode: false });

    const handleJobLaunched = (data) => {
      console.log('Job launched:', data.jobId);
    };

    const handleJobCancelled = (data) => {
      console.log('Job cancelled:', data.jobId);
    };

    return {
      currentProject,
      settings,
      handleJobLaunched,
      handleJobCancelled
    };
  }
};
</script>
\`\`\`

### With Custom Refresh Interval

\`\`\`vue
<StatusBoardTable
  :project-id="currentProject.project_id"
  :auto-refresh-interval="60000"
/>
\`\`\`

## Subcomponents

### StatusChip

Displays agent status with icon, color coding, and health indicators.

**Location**: `frontend/src/components/StatusBoard/StatusChip.vue`

**Props**:
- `status` (String): Agent status (waiting, working, blocked, etc.)
- `healthStatus` (String): Health status (healthy, warning, critical, timeout)
- `lastProgressAt` (String): ISO timestamp of last activity
- `healthFailureCount` (Number): Consecutive health check failures
- `minutesSinceProgress` (Number): Minutes since last activity

### JobMessageBadge

Displays message counts with colored badges.

**Location**: `frontend/src/components/StatusBoard/JobMessageBadge.vue`

**Props**:
- `unreadCount` (Number): Count of unread messages
- `acknowledgedCount` (Number): Count of acknowledged messages
- `totalMessages` (Number): Total message count

**Events**:
- `click-badge`: Emitted when badge is clicked (opens message modal)

### ActionIcons

Displays action buttons with confirmation dialogs.

**Location**: `frontend/src/components/StatusBoard/ActionIcons.vue`

**Props**:
- `job` (Object): Agent job data
- `claudeCodeCliMode` (Boolean): CLI mode toggle state

**Events**:
- `launch`: Launch agent job
- `copy-prompt`: Copy agent prompt to clipboard
- `view-messages`: Open message transcript modal
- `cancel`: Cancel agent job
- `hand-over`: Trigger orchestrator succession

## Data Flow

\`\`\`
┌─────────────────────────────────────────┐
│  StatusBoardTable                       │
│  ┌─────────────────────────────────┐   │
│  │ 1. Fetch table data on mount    │   │
│  │    GET /api/agent-jobs/table-view │   │
│  └─────────────────────────────────┘   │
│                                          │
│  ┌─────────────────────────────────┐   │
│  │ 2. Connect WebSocket             │   │
│  │    ws://host/ws                  │   │
│  └─────────────────────────────────┘   │
│                                          │
│  ┌─────────────────────────────────┐   │
│  │ 3. Listen for events:            │   │
│  │    - message:new                 │   │
│  │    - job:table_update            │   │
│  │    - message:status_change       │   │
│  └─────────────────────────────────┘   │
│                                          │
│  ┌─────────────────────────────────┐   │
│  │ 4. Update table data              │   │
│  │    (reactive updates)            │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
\`\`\`

## Styling

The component uses Vuetify's v-data-table with custom styling:

- **Row Height**: 64px
- **Icon Size**: 20px (actions), 24px (status)
- **Badge Colors**: Red (unread), Green (acknowledged), Grey (no messages)
- **Chip Colors**: Varies by status (see STATUS_CONFIG in utils/statusConfig.js)

## Performance Considerations

- **Server-Side Pagination**: Only loads visible rows (default 50)
- **WebSocket Updates**: Incremental updates, not full table refresh
- **Debounced Filtering**: 300ms debounce on filter changes
- **Virtual Scrolling**: Optional for very large datasets (>500 rows)

## Accessibility

- **ARIA Labels**: All action buttons have aria-label attributes
- **Keyboard Navigation**: Tab through actions, Enter to activate
- **Screen Reader Support**: Status changes announced via aria-live regions
- **Focus Management**: Modal traps focus when open

## Browser Support

- Chrome 90+
- Firefox 88+
- Edge 90+
- Safari 14+

## Related Documentation

- [MessageTranscriptModal](./MessageTranscriptModal.md)
- [MessageComposer](./MessageComposer.md)
- [API Reference - Table View Endpoint](../API_REFERENCE.md#agent-jobs-table-view)
- [Developer Guide - Extending Status Board](../DEVELOPER_GUIDE.md#extending-status-board)
```

### 2. Message Transcript Modal Documentation

**File**: `docs/components/MessageTranscriptModal.md` (NEW)

```markdown
# MessageTranscriptModal Component

## Overview

Modal dialog displaying agent message history with bidirectional communication via the built-in message composer.

## Location

`frontend/src/components/MessageTranscriptModal.vue`

## Features

- **Message History**: Chronological display of all messages
- **Status Indicators**: Pending (unread) vs. Acknowledged (read)
- **Message Composer**: Send messages directly from modal
- **Auto-Scroll**: Automatically scrolls to latest message
- **Real-Time Updates**: WebSocket integration for new messages
- **Character Counter**: Shows remaining characters (10,000 max)

## Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| dialog | Boolean | Yes | - | Controls modal visibility (v-model) |
| jobId | String | Yes | - | Agent job ID to display messages for |
| agentName | String | Yes | - | Agent name for modal title |
| messages | Array | No | [] | Initial message array |

## Events

| Event | Payload | Description |
|-------|---------|-------------|
| update:dialog | Boolean | Emitted when modal is closed |
| message-sent | { messageId, content, timestamp } | Emitted when message is sent |

## Usage

\`\`\`vue
<template>
  <MessageTranscriptModal
    v-model:dialog="showModal"
    :job-id="selectedJob.job_id"
    :agent-name="selectedJob.agent_name"
    :messages="selectedJob.messages"
    @message-sent="handleMessageSent"
  />
</template>

<script>
import { ref } from 'vue';
import MessageTranscriptModal from '@/components/MessageTranscriptModal.vue';

export default {
  components: {
    MessageTranscriptModal
  },

  setup() {
    const showModal = ref(false);
    const selectedJob = ref(null);

    const handleMessageSent = (data) => {
      console.log('Message sent:', data);
    };

    return {
      showModal,
      selectedJob,
      handleMessageSent
    };
  }
};
</script>
\`\`\`

## Message Format

Messages are displayed in chronological order with:
- **Timestamp**: ISO format (localized)
- **Sender**: Job ID or "user"
- **Status Badge**: Pending (orange) or Acknowledged (green)
- **Content**: Message text with markdown support

## Keyboard Shortcuts

- **Ctrl+Enter / Cmd+Enter**: Send message
- **Esc**: Close modal

## Related Documentation

- [MessageComposer](./MessageComposer.md)
- [API Reference - Send Message Endpoint](../API_REFERENCE.md#send-message)
```

### 3. User Guide Updates

**File**: `docs/USER_GUIDE.md`

Update user guide with new screenshots and instructions:

```markdown
# User Guide

## Status Board (Table View)

### Overview

The Status Board displays all agent jobs for the current project in a structured table format with real-time updates.

![Status Board Table](./images/status-board-table.png)

### Table Columns

| Column | Description |
|--------|-------------|
| **Agent Type** | Type of agent (orchestrator, analyzer, implementer, etc.) |
| **Agent ID** | Unique job identifier |
| **Agent Status** | Current status with icon (waiting, working, blocked, complete, failed, cancelled) |
| **Job Read** | Message indicators showing unread (red) and acknowledged (green) counts |
| **Messages Sent** | Number of messages sent by agent |
| **Messages Waiting** | Number of messages waiting to be sent |
| **Messages Read** | Number of messages read by agent |
| **Actions** | Quick action buttons (launch, copy, message, cancel, hand over) |

### Status Indicators

#### Status Chips

Each agent displays a colored status chip with icon:

- 🕐 **Waiting** (Grey): Agent is waiting to start
- ⚙️ **Working** (Blue): Agent is actively working
- ⚠️ **Blocked** (Orange): Agent is blocked waiting for input
- ✅ **Complete** (Green): Agent has completed successfully
- ❌ **Failed** (Red): Agent has failed
- 🚫 **Cancelled** (Grey): Agent was cancelled
- 📦 **Decommissioned** (Grey): Agent has been archived

#### Health Indicators

A small colored dot appears on the status chip when health issues are detected:

- 🟡 **Yellow Dot**: Warning - Minor health issue
- 🔴 **Red Pulsing Dot**: Critical - Severe health issue (requires attention)
- ⚪ **Grey Dot**: Timeout - Agent is not responding

#### Staleness Warning

When an agent has been inactive for more than 10 minutes (and is not in a terminal state), a clock-alert icon (🕐⚠️) appears on the status chip.

### Message Indicators

The "Job Read" column shows message status at a glance:

- **Red Badge** (🔴 3): 3 unread messages
- **Green Badge** (🟢 5): 5 acknowledged messages
- **Grey Chip** (📭): No messages

Click any badge to open the message transcript modal.

### Actions

#### Launch Agent

**Icon**: 🚀 Rocket

Copies the agent's launch prompt to your clipboard and prepares the agent for execution.

**Availability**:
- **Claude Code CLI Mode ON**: Only available for orchestrator
- **Claude Code CLI Mode OFF**: Available for all agents in "waiting" status

#### Copy Prompt

**Icon**: 📋 Copy

Copies the agent's prompt to your clipboard without launching.

**Availability**: Always available

#### View Messages

**Icon**: 💬 Message

Opens the message transcript modal showing full conversation history. You can send messages directly from this modal.

**Availability**: Always available
**Badge**: Shows unread message count

#### Cancel Job

**Icon**: 🚫 Cancel

Cancels the agent job. This action requires confirmation and cannot be undone.

**Availability**: Only for jobs in "working", "waiting", or "blocked" status

#### Hand Over (Orchestrator Only)

**Icon**: 👋 Hand

Triggers orchestrator succession, creating a new orchestrator instance and transferring context.

**Availability**: Only for orchestrator agents at 90%+ context usage

### Filtering

Click the filter icon at the top of the table to access filtering options:

- **Filter by Status**: Show only jobs with specific statuses
- **Filter by Health**: Show only jobs with specific health states
- **Filter by Unread Messages**: Show only jobs with unread messages
- **Filter by Agent Type**: Show only specific agent types

### Sorting

Click any column header to sort the table:

- **Last Activity**: Sort by most recent activity (default: descending)
- **Creation Time**: Sort by when job was created
- **Status**: Sort alphabetically by status
- **Agent Type**: Sort alphabetically by agent type

### Claude Code CLI Mode Toggle

**Location**: Top-left of status board

This toggle controls launch button availability:

- **ON** (Red): Claude Code CLI mode - Only orchestrator gets a launch button (all other agents run as sub-agents)
- **OFF** (Grey): General CLI mode - All agents get individual launch buttons for separate terminals

### Message Transcript Modal

![Message Transcript Modal](./images/message-transcript-modal.png)

#### Features

- **Chronological View**: Messages displayed oldest-to-newest
- **Status Badges**: Pending (orange) vs. Acknowledged (green)
- **Auto-Scroll**: Automatically scrolls to latest message
- **Message Composer**: Send messages without closing modal
- **Character Counter**: Shows remaining characters (10,000 max)
- **Keyboard Shortcuts**: Ctrl+Enter to send, Esc to close

#### Sending Messages

1. Type your message in the text area
2. Watch the character counter (turns orange at 500 remaining, red at 100)
3. Press **Ctrl+Enter** or click the **Send** button
4. Message appears immediately with "pending" status
5. Status changes to "acknowledged" when agent reads it

### Real-Time Updates

The status board updates automatically via WebSocket connection:

- **Status Changes**: Agent status updates appear instantly
- **New Messages**: Message badges update in real-time
- **Health Changes**: Health indicators update as agents report health
- **Staleness Warnings**: Warnings appear automatically for inactive agents

No manual refresh needed!

### Troubleshooting

#### Table Not Loading

- Verify project is selected in top navigation
- Check network connection
- Refresh page (F5)

#### WebSocket Not Connecting

- Check that backend server is running on correct port
- Verify firewall settings (port 7272 default)
- Check browser console for connection errors

#### Messages Not Sending

- Verify message length is under 10,000 characters
- Check that job is not in terminal state (complete, failed, cancelled)
- Refresh page and try again

---

**See Also**:
- [Installation Guide](./INSTALLATION_FLOW_PROCESS.md)
- [API Reference](./API_REFERENCE.md)
- [Developer Guide](./DEVELOPER_GUIDE.md)
```

### 4. API Reference Updates

**File**: `docs/API_REFERENCE.md`

Add new endpoint documentation:

```markdown
# API Reference

## Agent Jobs Endpoints

### GET /api/agent-jobs/table-view

Get optimized table view data for status board.

**Authentication**: Required (Bearer token)

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| project_id | string | Yes | - | Project ID to fetch jobs for |
| status | array[string] | No | - | Filter by status (can specify multiple) |
| health_status | array[string] | No | - | Filter by health status |
| has_unread | boolean | No | - | Filter jobs with unread messages |
| agent_type | array[string] | No | - | Filter by agent type |
| sort_by | string | No | "last_progress" | Sort column (last_progress, created_at, status, agent_type) |
| sort_order | string | No | "desc" | Sort direction (asc, desc) |
| limit | integer | No | 50 | Number of rows to return (1-500) |
| offset | integer | No | 0 | Pagination offset |

**Response**: 200 OK

\`\`\`json
{
  "rows": [
    {
      "job_id": "uuid",
      "agent_type": "orchestrator",
      "agent_name": "Main Orchestrator",
      "tool_type": "claude-code",
      "status": "working",
      "progress": 45,
      "current_task": "Analyzing requirements",
      "unread_count": 3,
      "acknowledged_count": 12,
      "total_messages": 15,
      "health_status": "healthy",
      "last_progress_at": "2025-11-21T10:30:00Z",
      "minutes_since_progress": 2,
      "is_stale": false,
      "created_at": "2025-11-21T10:00:00Z",
      "started_at": "2025-11-21T10:05:00Z",
      "completed_at": null,
      "instance_number": 1,
      "is_orchestrator": true
    }
  ],
  "total": 8,
  "limit": 50,
  "offset": 0,
  "project_id": "uuid",
  "filters_applied": {
    "status": ["working", "waiting"]
  }
}
\`\`\`

**Errors**:
- 400 Bad Request: Invalid query parameters
- 401 Unauthorized: Missing or invalid authentication token
- 404 Not Found: Project not found or not accessible

**Performance**:
- Response time: <100ms for 50 jobs with indexes
- Payload size: ~300-500 bytes per row

**Related Endpoints**:
- [GET /api/agent-jobs/](#get-apiagenT-jobs) - Full job list
- [GET /api/agent-jobs/{job_id}](#get-apiagent-jobsjobid) - Single job details

---

### GET /api/agent-jobs/filter-options

Get available filter options for current project.

**Authentication**: Required (Bearer token)

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| project_id | string | Yes | Project ID |

**Response**: 200 OK

\`\`\`json
{
  "statuses": ["blocked", "complete", "failed", "waiting", "working"],
  "agent_types": ["analyzer", "implementer", "orchestrator", "tester"],
  "health_statuses": ["critical", "healthy", "warning"],
  "tool_types": ["claude-code", "codex", "gemini"],
  "has_unread_jobs": true
}
\`\`\`

## WebSocket Events

### Connection

**URL**: `ws://localhost:7272/ws`

**Authentication**: JWT token in connection URL or initial message

### Events

#### job:table_update

Batch update event for multiple job changes.

**Payload**:
\`\`\`json
{
  "event": "job:table_update",
  "project_id": "uuid",
  "event_type": "status_change",
  "timestamp": "2025-11-21T10:35:00Z",
  "updates": [
    {
      "job_id": "uuid",
      "status": "complete",
      "updated_at": "2025-11-21T10:35:00Z"
    }
  ]
}
\`\`\`

#### message:new

New message added to job queue.

**Payload**:
\`\`\`json
{
  "event": "message:new",
  "job_id": "uuid",
  "message_id": "uuid",
  "status": "pending",
  "timestamp": "2025-11-21T10:00:00Z"
}
\`\`\`

#### message:status_change

Message status changed (pending → acknowledged).

**Payload**:
\`\`\`json
{
  "event": "message:status_change",
  "job_id": "uuid",
  "message_id": "uuid",
  "old_status": "pending",
  "new_status": "acknowledged",
  "timestamp": "2025-11-21T10:01:00Z"
}
\`\`\`
```

### 5. Developer Guide Updates

**File**: `docs/DEVELOPER_GUIDE.md`

Add section on extending status board:

```markdown
# Developer Guide

## Extending the Status Board

### Adding a New Column

1. **Update TableRowData schema** (`api/endpoints/agent_jobs/table_view.py`):

\`\`\`python
class TableRowData(BaseModel):
    # ... existing fields ...
    new_field: str | None  # Add new field
\`\`\`

2. **Update backend endpoint** to populate new field:

\`\`\`python
rows.append(
    TableRowData(
        # ... existing fields ...
        new_field=job.new_field  # Populate new field
    )
)
\`\`\`

3. **Update frontend table headers**:

\`\`\`javascript
const tableHeaders = ref([
  // ... existing headers ...
  { text: 'New Column', value: 'new_field', sortable: true }
]);
\`\`\`

4. **Add table cell template** (if custom rendering needed):

\`\`\`vue
<template #item.new_field="{ item }">
  <span>{{ item.new_field }}</span>
</template>
\`\`\`

### Adding a New Action

1. **Update ACTION_CONFIG** (`frontend/src/utils/actionConfig.js`):

\`\`\`javascript
export const ACTION_CONFIG = {
  // ... existing actions ...

  newAction: {
    icon: 'mdi-new-icon',
    color: 'primary',
    label: 'New Action',
    tooltip: 'Perform new action',
    confirmation: true,  // Show confirmation dialog
    confirmationTitle: 'Confirm New Action?',
    confirmationMessage: 'Are you sure?',
    requiresStatus: ['working'],  // Only show for working jobs
    excludeTerminalStates: true
  }
};
\`\`\`

2. **Update ActionIcons component** to add button:

\`\`\`vue
<v-btn
  v-if="action === 'newAction'"
  icon
  small
  :color="getActionColor('newAction')"
  :loading="loadingStates.newAction"
  @click="handleNewAction"
  class="mx-1"
>
  <v-icon small>mdi-new-icon</v-icon>
</v-btn>
\`\`\`

3. **Implement handler**:

\`\`\`javascript
const handleNewAction = async () => {
  const config = getActionConfig('newAction');
  if (config.confirmation) {
    showConfirmation('newAction', config);
  } else {
    await executeNewAction();
  }
};

const executeNewAction = async () => {
  loadingStates.value.newAction = true;
  try {
    emit('new-action', props.job);
  } finally {
    loadingStates.value.newAction = false;
  }
};
\`\`\`

4. **Handle event in parent component**:

\`\`\`vue
<ActionIcons
  :job="item"
  @new-action="handleNewAction"
/>
\`\`\`

### Adding a New WebSocket Event

1. **Backend**: Emit event from appropriate location:

\`\`\`python
from api.websocket import broadcast_to_tenant

await broadcast_to_tenant(
    tenant_key=tenant_key,
    event_data={
        "event": "custom:event",
        "job_id": job.job_id,
        "data": {"key": "value"}
    }
)
\`\`\`

2. **Frontend**: Add event handler in StatusBoardTable:

\`\`\`javascript
ws.value.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.event === 'custom:event') {
    handleCustomEvent(data);
  }
};

const handleCustomEvent = (data) => {
  // Update table data based on event
  const jobIndex = tableRows.value.findIndex(r => r.job_id === data.job_id);
  if (jobIndex !== -1) {
    tableRows.value[jobIndex].customField = data.data.value;
    tableRows.value = [...tableRows.value];  // Trigger reactivity
  }
};
\`\`\`

### Performance Optimization Tips

- **Use server-side pagination** for large datasets
- **Debounce filter changes** to avoid excessive API calls
- **Use WebSocket incremental updates** instead of full table refresh
- **Implement virtual scrolling** for tables with >500 rows
- **Cache filter options** to reduce API calls

### Testing New Features

1. **Unit Tests**: Test component logic in isolation
2. **Integration Tests**: Test component interactions
3. **E2E Tests**: Test complete user workflows
4. **Performance Tests**: Measure render time and API response time

### Troubleshooting

#### Table Not Updating After WebSocket Event

- Verify event payload matches expected format
- Check that job_id exists in table
- Ensure reactive update: `tableRows.value = [...tableRows.value]`
- Check browser console for errors

#### New Column Not Sorting

- Verify `sortable: true` in header definition
- Check that backend endpoint supports sort_by parameter for new field
- Add database index if sorting is slow

---

**See Also**:
- [Component Documentation](./components/)
- [API Reference](./API_REFERENCE.md)
- [Testing Guide](./TESTING.md)
```

---

## Cleanup Checklist

**Old Code Removed**:
- [ ] No commented-out blocks remaining
- [ ] No orphaned imports (check with linter)
- [ ] No unused functions or variables
- [ ] No `// TODO` or `// FIXME` comments without tickets

**Integration Verified**:
- [ ] Existing components reused where possible
- [ ] No duplicate functionality created
- [ ] Shared logic extracted to composables (if applicable)
- [ ] No zombie code (per QUICK_LAUNCH.txt line 28)

**Testing**:
- [ ] All imports resolved correctly
- [ ] No linting errors (eslint/ruff)
- [ ] Coverage maintained (>80%)

---

## Success Criteria

- ✅ Component documentation created for StatusBoardTable, MessageTranscriptModal, MessageComposer
- ✅ User guide updated with new screenshots (table view replaces card view)
- ✅ All feature explanations current (toggle, filters, actions, badges)
- ✅ API reference updated with table view endpoint and filter options endpoint
- ✅ WebSocket events documented (job:table_update, message:new, message:status_change)
- ✅ Developer guide includes extension patterns (new columns, actions, events)
- ✅ All screenshots replaced with new table interface
- ✅ Code examples tested and accurate
- ✅ Cross-references updated between documentation files
- ✅ Documentation structure remains consistent with existing style

---

## Next Steps

This completes the Visual Refactor Series (0225-0237). All documentation is now current and reflects the new status board table interface.

**Future Enhancements** (Not in Scope):
- Video tutorials for new interface
- Interactive documentation with live examples
- API playground for testing endpoints
- Component storybook for design system

---

## References

- **Vision Document**: All slides (1-27) showing complete new interface
- **Existing Documentation**: `docs/` directory structure
- **Component Implementation**: Handovers 0232-0235
- **API Implementation**: Handover 0226
- **Testing Implementation**: Handover 0236
- **Screenshot Tool**: Use browser DevTools or screenshot utility to capture new interface
