# Project Launch Components Index

## Overview

This directory contains all components for the ProjectLaunchView feature (Handover 0062).

**Location**: `F:\GiljoAI_MCP\frontend\src\components\project-launch\`

## Files

### 1. LaunchPanelView.vue

**Purpose**: Tab 1 of ProjectLaunchView - Three-section launch panel

**Sections**:
- **Left (Orchestrator)**: Project description + copyable prompt
- **Center (Mission)**: AI-generated mission display
- **Right (Agents)**: 2x3 agent grid
- **Bottom**: ACCEPT MISSION button

**Key Props**:
```javascript
project: Object        // Project data
mission: String       // AI-generated mission
agents: Array         // Selected agents (up to 6)
loadingMission: Boolean
launching: Boolean
canAccept: Boolean
```

**Key Events**:
```javascript
@save-description(description)   // Save project description
@copy-prompt()                   // Copy orchestrator prompt
@accept-mission()                // Accept mission & create jobs
```

**Features**:
- Gradient card headers
- Loading states
- Empty states
- Orchestrator info dialog
- Responsive 3-column layout

---

### 2. AgentMiniCard.vue

**Purpose**: Compact agent display card (used in 2x3 grid)

**Usage**:
```vue
<v-col v-for="agent in agents" :key="agent.id" cols="6">
  <agent-mini-card :agent="agent" />
</v-col>
```

**Key Props**:
```javascript
agent: {
  id: String,
  name: String,
  type: String,
  status?: String,
  mission?: String,
  capabilities?: Array,
  created_at?: String
}
showDetails: Boolean  // Show details dialog
cardColor?: String    // Optional background
```

**Features**:
- Color-coded by agent type
- Icon mapping by agent type
- Expandable details dialog
- Hover animations
- Agent type badge

**Agent Type Colors**:
```
orchestrator    → Purple (#7c3aed)
lead            → Blue (#3b82f6)
backend         → Green (#059669)
frontend        → Cyan (#06b6d4)
tester          → Orange (#f97316)
analyzer        → Pink (#ec4899)
architect       → Violet (#8b5cf6)
devops          → Indigo (#6366f1)
security        → Red (#dc2626)
ux_designer     → Rose (#f472b6)
database        → Teal (#14b8a6)
ai_specialist   → Fuchsia (#a855f7)
```

---

### 3. KanbanJobsView.vue

**Purpose**: Tab 2 of ProjectLaunchView - Job monitoring (stub for Handover 0066)

**Current Features**:
- Job statistics (Total, Pending, Running, Completed)
- Data table of jobs with headers
- Job details dialog
- Refresh button with loading state
- Empty state with Handover 0066 reference

**Future Features** (Handover 0066):
- Interactive Kanban board
- Drag-and-drop job management
- Real-time status indicators
- Job message threading

**Key Props**:
```javascript
projectId: String  // Required
jobs: Array        // Initial jobs array
```

**Features**:
- WebSocket integration
- Real-time job updates
- Job filtering by status
- Expandable job details

---

## Usage Example

### Basic Import

```javascript
import LaunchPanelView from '@/components/project-launch/LaunchPanelView.vue'
import AgentMiniCard from '@/components/project-launch/AgentMiniCard.vue'
import KanbanJobsView from '@/components/project-launch/KanbanJobsView.vue'
```

### In ProjectLaunchView

```vue
<template>
  <!-- Tab 1: Launch Panel -->
  <launch-panel-view
    :project="project"
    :mission="mission"
    :agents="selectedAgents"
    :loading-mission="loadingMission"
    :launching="launching"
    :can-accept="canAcceptMission"
    @save-description="handleSaveDescription"
    @copy-prompt="handleCopyPrompt"
    @accept-mission="handleAcceptMission"
  />

  <!-- Tab 2: Active Jobs -->
  <kanban-jobs-view
    v-if="jobsLaunched"
    :project-id="projectId"
    :jobs="projectJobs"
  />
</template>
```

---

## Component Relationships

```
ProjectLaunchView (F:\...\views\ProjectLaunchView.vue)
│
├── LaunchPanelView
│   │
│   └── AgentMiniCard (rendered in 2x3 grid)
│       │
│       └── Agent Details Dialog
│
└── KanbanJobsView
    │
    ├── Job Statistics Cards
    ├── Job Data Table
    └── Job Details Dialog
```

---

## State Management

### ProjectLaunchView (Parent)

```javascript
const project = ref(null)
const mission = ref('')
const selectedAgents = ref([])
const projectJobs = ref([])
const activeTab = ref('launch')
const jobsLaunched = ref(false)
const loading = ref(true)
const error = ref(null)
const showToast = ref(false)
const toastMessage = ref('')
const toastColor = ref('success')
```

### Data Flow

```
API Fetch → ProjectLaunchView
            ↓
        [project data]
            ↓
        LaunchPanelView → (reads project, mission, agents)
                         → AgentMiniCard (each agent)
            ↓
        WebSocket Updates → ProjectLaunchView
                         → LaunchPanelView (mission, agents)
                         → KanbanJobsView (job updates)
```

---

## WebSocket Events

### Subscribed in ProjectLaunchView

**Event**: `orchestrator:progress`
```javascript
{
  project_id: String,
  stage: String,           // 'mission_generated', 'agents_selected'
  mission: String,         // Generated mission
  agents: Array,          // Selected agents
  error?: String
}
```

**Event**: `orchestrator:mission`
```javascript
{
  project_id: String,
  mission: String,
  agents: Array
}
```

**Event**: `job:status_changed`
```javascript
{
  project_id: String,
  job_id: String,
  status: String,
  progress: Number
}
```

---

## Styling

### Colors

**Card Headers**:
```css
.bg-gradient-purple: linear-gradient(135deg, #667eea 0%, #764ba2 100%)
.bg-gradient-blue: linear-gradient(135deg, #2196f3 0%, #1976d2 100%)
.bg-gradient-green: linear-gradient(135deg, #66bb6a 0%, #43a047 100%)
```

**Agent Type Colors**: See AgentMiniCard.vue for complete mapping

### Responsive Breakpoints

- **Desktop** (1264px+): 3-column layout (md-4 each)
- **Tablet** (768px-1263px): 2-column layout with wrapping
- **Mobile** (<768px): Full-width stacked layout

---

## API Integration

### Endpoints Used

**Projects**:
```
GET  /api/v1/projects/{projectId}
PUT  /api/v1/projects/{projectId}
POST /api/v1/projects/{projectId}/activate
```

**Orchestration**:
```
POST /api/v1/orchestration/launch-project
GET  /api/v1/orchestration/workflow-status/{projectId}
GET  /api/v1/orchestration/metrics/{projectId}
```

### Service Methods

```javascript
api.projects.get(projectId)
api.projects.update(projectId, data)
api.orchestrator.launchProject(data)
api.orchestrator.getWorkflowStatus(projectId)
```

---

## Error Handling

### Error Types

1. **Network Errors**: No server response
2. **API Errors**: 4xx, 5xx responses
3. **Validation Errors**: Invalid input
4. **WebSocket Errors**: Connection loss

### Recovery Strategies

```javascript
// Fetch with error handling
try {
  const response = await api.projects.get(projectId)
  project.value = response.data
} catch (err) {
  error.value = err.response?.data?.detail || err.message
  showNotification('Error message', 'error', 'mdi-alert-circle')
}
```

### User Notifications

- **Success**: Green toast (3s timeout)
- **Error**: Red alert (dismissible)
- **Info**: Blue alert (dismissible)

---

## Accessibility

### ARIA Labels

```vue
<v-btn aria-label="Go back">
<v-btn aria-label="Launch orchestrator">
<v-card aria-label="Project launch interface">
```

### Keyboard Navigation

- Tab: Move between interactive elements
- Enter: Activate buttons, submit forms
- Escape: Close dialogs
- Arrow Keys: Navigate lists (if implemented)

### Color Accessibility

- Not color-alone for state indication
- Sufficient contrast ratios (4.5:1 minimum)
- Icons paired with text labels

---

## Performance Tips

### Optimization Techniques

1. **Lazy Loading**:
   ```javascript
   LaunchPanelView: () => import('./LaunchPanelView.vue')
   ```

2. **Computed Properties**:
   ```javascript
   const canAcceptMission = computed(() =>
     mission.value && selectedAgents.value.length > 0
   )
   ```

3. **WebSocket Cleanup**:
   ```javascript
   onUnmounted(() => {
     if (unsubscribeProgress) unsubscribeProgress()
   })
   ```

4. **Virtual Scrolling** (for large lists):
   ```javascript
   // Implement in KanbanJobsView for many jobs
   <v-virtual-scroll :items="jobs">
   ```

---

## Testing Examples

### Unit Test

```javascript
import { mount } from '@vue/test-utils'
import LaunchPanelView from '@/components/project-launch/LaunchPanelView.vue'

describe('LaunchPanelView', () => {
  it('emits copy-prompt when button clicked', async () => {
    const wrapper = mount(LaunchPanelView, {
      props: {
        project: { id: '1', name: 'Test' },
        mission: 'Test mission',
        agents: [],
        canAccept: false,
        loadingMission: false,
        launching: false
      }
    })

    await wrapper.find('.copy-button').trigger('click')
    expect(wrapper.emitted('copy-prompt')).toBeTruthy()
  })
})
```

### Integration Test

```javascript
describe('ProjectLaunchView Workflow', () => {
  it('completes full launch workflow', async () => {
    // 1. Mount component
    const wrapper = mount(ProjectLaunchView, {
      global: { plugins: [router, pinia] }
    })

    // 2. Wait for project fetch
    await wrapper.vm.$nextTick()

    // 3. Accept mission
    await wrapper.find('.accept-mission-btn').trigger('click')

    // 4. Verify job creation
    expect(wrapper.vm.jobsLaunched).toBe(true)
  })
})
```

---

## Troubleshooting

### Common Issues

**Issue**: Mission not loading
- **Cause**: Orchestrator not running or WebSocket disconnected
- **Fix**: Check console logs, verify WebSocket connection

**Issue**: Copy button not working
- **Cause**: Clipboard API not available or HTTPS required
- **Fix**: Use HTTPS in production, fallback to manual copy

**Issue**: Agent colors not showing
- **Cause**: Agent type not in color mapping
- **Fix**: Add new agent type to colors object in AgentMiniCard.vue

**Issue**: Jobs not updating
- **Cause**: WebSocket event name mismatch
- **Fix**: Check event name in websocketService.onMessage()

---

## Future Enhancements

### Handover 0066

- [ ] Replace KanbanJobsView stub with full board
- [ ] Implement drag-and-drop functionality
- [ ] Add real-time job status animations
- [ ] Create job message threading UI
- [ ] Display performance metrics

### Beyond 0066

- [ ] Mission preview/approval dialog
- [ ] Agent capability filtering
- [ ] Workflow template selection
- [ ] Job chaining with dependencies
- [ ] Advanced analytics dashboard

---

## Quick Reference

### Component Exports

```javascript
// All three components are standalone
// Import by relative path:
import LaunchPanelView from '@/components/project-launch/LaunchPanelView.vue'
import AgentMiniCard from '@/components/project-launch/AgentMiniCard.vue'
import KanbanJobsView from '@/components/project-launch/KanbanJobsView.vue'
```

### Key Functions

```javascript
// ProjectLaunchView
fetchProjectDetails()
handleSaveDescription()
handleCopyPrompt()
handleAcceptMission()
showNotification()
goBack()
getStatusColor()

// LaunchPanelView
$emit('save-description')
$emit('copy-prompt')
$emit('accept-mission')

// AgentMiniCard
truncateText()
formatDate()

// KanbanJobsView
fetchJobs()
refreshJobs()
getStatusColor()
showJobDetails()
formatDate()
```

### Key Props

```javascript
// LaunchPanelView
project, mission, agents, loadingMission, launching, canAccept

// AgentMiniCard
agent, showDetails, cardColor

// KanbanJobsView
projectId, jobs
```

---

**Version**: 1.0.0
**Status**: Production Ready
**Last Updated**: 2025-10-28
**Handover**: 0062
