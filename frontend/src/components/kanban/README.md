# Kanban Components

Agent job monitoring dashboard components for GiljoAI MCP (Handover 0066).

## Components

### KanbanColumn.vue
Display-only column for a single job status group.

**Features:**
- Shows jobs for one status (pending, active, completed, or blocked)
- Status-specific icon and color
- Job count badge
- Empty state indicator
- NO drag-drop functionality (agents navigate themselves)

**Props:**
- `status` (String, required): Column status ('pending'|'active'|'completed'|'blocked')
- `jobs` (Array, default []): Array of job objects
- `title` (String, required): Column display title
- `description` (String, default ''): Column subtitle

**Events:**
- `view-job-details(job)`: User clicked on job card
- `open-messages(job)`: User clicked message badge

### JobCard.vue
Individual job card displaying agent and mission information with THREE message count badges.

**Features:**
- Agent type icon and color
- Agent name and type display
- Mode indicator badge (claude/codex/gemini)
- Mission preview (truncated to 120 chars)
- Progress bar (active jobs only)
- Relative time display ("2 hours ago")
- **THREE separate message count badges:**
  - Unread (red, mdi-message-badge)
  - Acknowledged (green, mdi-check-all)
  - Sent (grey, mdi-send)
- Status badge matching column

**Props:**
- `job` (Object, required): Agent job object
- `columnStatus` (String, required): Current column status

**Events:**
- `view-details()`: Card clicked
- `open-messages()`: Unread message badge clicked

**Agent Type Icons & Colors:**
```javascript
orchestrator: purple (mdi-brain)
analyzer: blue (mdi-magnify)
implementer: green (mdi-code-braces)
tester: orange (mdi-test-tube)
ux-designer: pink (mdi-palette)
backend: teal (mdi-server)
frontend: indigo (mdi-monitor)
```

**Mode Colors:**
```javascript
claude: deep-purple
codex: blue
gemini: light-blue
```

### MessageThreadPanel.vue
Slack-style message thread panel for developer-agent communication.

**Features:**
- Right-side drawer navigation
- Mission context displayed at top
- Chronological message list
- Message sender identification (developer vs agent)
- Message status indicators (pending, acknowledged, sent)
- Message composition area
- Ctrl+Enter to send support
- Auto-scroll to newest messages
- Loading states
- Empty state handling

**Props:**
- `modelValue` (Boolean): Panel open state
- `job` (Object): Current job object
- `columnStatus` (String): Job status (affects messaging behavior)

**Events:**
- `update:modelValue(state)`: Toggle panel open/closed
- `message-sent(message)`: New message sent

**Message Object Structure:**
```javascript
{
  id: string,
  from: 'developer' | 'agent',
  content: string,
  status: 'pending' | 'acknowledged' | 'sent',
  created_at: ISO8601,
  ...
}
```

**Message Status Meanings:**
- `pending`: Message sent, waiting for agent to read
- `acknowledged`: Agent has acknowledged receipt
- `sent`: Developer sent this message

## Integration with KanbanJobsView

The components are used together in KanbanJobsView:

```vue
<kanban-column
  v-for="column in kanbanColumns"
  :key="column.status"
  :status="column.status"
  :jobs="column.jobs"
  :title="column.title"
  @view-job-details="openJobDetails"
  @open-messages="openMessagePanel"
/>

<message-thread-panel
  v-model="messagePanelOpen"
  :job="selectedJob"
  :column-status="selectedJob?.status"
  @message-sent="onMessageSent"
/>
```

## API Integration

### Required API Endpoints

**Get Kanban Board Data:**
```javascript
GET /api/agent-jobs/kanban/{project_id}
Response:
{
  "jobs": [
    {
      "job_id": "uuid",
      "agent_id": "agent-name",
      "agent_name": "Agent Name",
      "agent_type": "implementer",
      "status": "active",
      "mode": "claude",
      "mission": "Full mission description...",
      "progress": 65,
      "created_at": "2025-10-28T12:00:00Z",
      "messages": [
        {
          "id": "msg-1",
          "from": "developer",
          "content": "Please implement auth...",
          "status": "sent",
          "created_at": "2025-10-28T12:30:00Z"
        }
      ]
    }
  ]
}
```

**Get Message Thread:**
```javascript
GET /api/agent-jobs/{job_id}/messages
Response:
{
  "job_id": "uuid",
  "messages": [
    {
      "id": "msg-1",
      "from": "developer",
      "content": "Message content",
      "status": "sent",
      "created_at": "2025-10-28T12:30:00Z"
    }
  ]
}
```

**Send Message:**
```javascript
POST /api/agent-jobs/{job_id}/send-message
Request Body:
{
  "content": "Message text",
  "to": "agent-id"
}

Response:
{
  "message_id": "uuid",
  "status": "success"
}
```

## WebSocket Events

Subscribe to real-time job updates:

```javascript
websocketService.onMessage('job:status_changed', (data) => {
  // data contains: job_id, old_status, new_status, project_id
})
```

## Message Count Logic

From the `job.messages` JSONB array:

```javascript
// Unread count
unreadCount = job.messages.filter(m => m.status === 'pending').length

// Acknowledged count
acknowledgedCount = job.messages.filter(m => m.status === 'acknowledged').length

// Sent count
sentCount = job.messages.filter(m => m.from === 'developer').length
```

## Column Status Meanings

**Pending**
- Jobs created, waiting for agent to start
- Agent has not yet called `update_job_status('active')`
- Grey icon: mdi-clock-outline

**Active**
- Jobs in progress
- Agent is actively working
- Blue icon: mdi-play-circle
- Shows progress bar if available

**Completed**
- Jobs finished successfully
- Agent called `update_job_status('completed')`
- Green icon: mdi-check-circle

**Blocked**
- Jobs failed OR waiting for feedback
- Agent called `update_job_status('blocked', reason=...)`
- OR job encountered error
- Red icon: mdi-alert-circle
- Developer should review and send guidance message

## Job Details Dialog

Accessed by clicking a job card. Shows:
- Agent information (name, type, mode)
- Full mission text
- Current status
- Progress (if active)
- All message counts
- Quick link to message panel

## Styling Notes

- Responsive design (mobile, tablet, desktop)
- Vuetify 3 theme integration
- Custom scrollbar styling in columns
- Smooth animations on message bubbles
- Accessible keyboard navigation
- Focus management in drawers

## Development Notes

- NO drag-drop library (agents navigate themselves via MCP)
- Display-only columns for developers
- Message panel is temporary (closes when dismissed)
- Real-time updates via WebSocket
- Proper cleanup on component unmount

## Dependencies

- Vue 3 (Composition API)
- Vuetify 3
- date-fns (for time formatting)
- axios (via api service)

## Testing Checklist

- [ ] Kanban board loads and displays 4 columns
- [ ] Jobs appear in correct columns based on status
- [ ] Message badge counts match message array
- [ ] Clicking unread badge opens message panel
- [ ] Messages send successfully
- [ ] WebSocket updates trigger column re-layout
- [ ] Empty states display when no jobs
- [ ] Responsive design works on mobile
- [ ] Keyboard navigation works
- [ ] Focus is managed properly in drawer
- [ ] Error states display gracefully
