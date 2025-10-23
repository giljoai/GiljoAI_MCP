# Agent Flow Visualization - Quick Start Guide

## Installation

Dependencies already installed via npm:
```bash
@vue-flow/core ^1.0.0
@vue-flow/background ^1.0.0
@vue-flow/controls ^1.0.0
@vue-flow/minimap ^1.0.0
gsap ^3.12.0
```

## Quick Import

```javascript
// Import main component
import { FlowCanvas } from '@/components/agent-flow'

// Or import all components
import {
  FlowCanvas,
  AgentNode,
  ThreadView,
  MissionDashboard,
  ArtifactTimeline,
  NodeDetailPanel,
  EdgeDetailPanel
} from '@/components/agent-flow'

// Import store
import { useAgentFlowStore } from '@/stores/agentFlow'

// Import service
import flowWebSocketService from '@/services/flowWebSocket'
```

## Minimal Example

```vue
<template>
  <FlowCanvas :project-id="projectId" :auto-initialize="true" />
</template>

<script setup>
const projectId = 'my-project-123'
</script>
```

## Full Dashboard Example

```vue
<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12" md="8">
        <!-- Main flow canvas -->
        <FlowCanvas
          :project-id="projectId"
          @node-selected="selectedNode = $event"
        />
      </v-col>
      <v-col cols="12" md="4">
        <!-- Mission dashboard -->
        <MissionDashboard />
        
        <!-- Artifact timeline -->
        <ArtifactTimeline />
      </v-col>
    </v-row>

    <!-- Message thread for selected agent -->
    <v-row v-if="selectedNode">
      <v-col cols="12">
        <ThreadView
          :node-id="selectedNode.id"
          :agent-name="selectedNode.data.label"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import {
  FlowCanvas,
  MissionDashboard,
  ArtifactTimeline,
  ThreadView
} from '@/components/agent-flow'

const projectId = 'my-project-123'
const selectedNode = ref(null)
</script>
```

## WebSocket Event Examples

Send these events from your backend:

### Agent Status Update
```javascript
{
  type: 'agent_communication:status_update',
  data: {
    agent_name: 'designer',
    agent_id: 'agent-1',
    status: 'active',
    health: 95,
    context_used: 45,
    active_jobs: 2
  }
}
```

### Message Sent
```javascript
{
  type: 'agent_communication:message_sent',
  data: {
    message_id: 'msg-1',
    from_agent: 'orchestrator',
    to_agents: ['designer', 'developer'],
    content: 'Design the UI',
    created_at: '2024-10-22T10:30:00Z'
  }
}
```

### Artifact Created
```javascript
{
  type: 'agent_communication:artifact_created',
  data: {
    filename: 'component.vue',
    filepath: '/src/components/component.vue',
    agent_name: 'designer',
    agent_id: 'agent-1',
    content_type: 'text/vue',
    filesize: 2048,
    description: 'Vue component'
  }
}
```

### Mission Started
```javascript
{
  type: 'mission:started',
  data: {
    mission_id: 'mission-1',
    title: 'Build Dashboard',
    description: 'Create a new admin dashboard',
    agents: ['orchestrator', 'designer', 'developer'],
    goals: [
      'Design UI',
      'Implement backend',
      'Test functionality'
    ]
  }
}
```

## Store Actions

```javascript
import { useAgentFlowStore } from '@/stores/agentFlow'

const flowStore = useAgentFlowStore()

// Initialize from agents
await flowStore.initializeFromAgents()

// Update node status
flowStore.updateNodeStatus('agent-1', 'active')

// Update metrics
flowStore.updateNodeMetrics('agent-1', {
  health: 95,
  contextUsed: 45,
  activeJobs: 2
})

// Add message to node
flowStore.addMessageToNode('agent-1', {
  id: 'msg-1',
  from: 'agent-1',
  content: 'Message content',
  status: 'sent',
  createdAt: new Date().toISOString()
})

// Set mission data
flowStore.setMissionData({
  title: 'My Mission',
  description: 'Description',
  agents: ['agent-1', 'agent-2'],
  goals: ['Goal 1', 'Goal 2']
})

// Add artifact
flowStore.addArtifact({
  type: 'file',
  name: 'myfile.vue',
  path: '/src/components/myfile.vue',
  size: 2048,
  agentName: 'designer'
})
```

## Styling Customization

```scss
// Override colors
:root {
  --color-primary: #315074;
  --color-success: #67bd6d;
  --color-warning: #ffc300;
  --color-error: #c6298c;
}

// Customize node appearance
.agent-node {
  --node-color: #67bd6d;
  background: linear-gradient(135deg, #1e3147 0%, #182739 100%);
}
```

## Testing

```bash
# Run all tests
npm run test

# Watch mode
npm run test

# Coverage report
npm run test:coverage

# Interactive UI
npm run test:ui
```

## Troubleshooting

**Q: Nodes not updating in real-time**  
A: Check WebSocket connection is active and events are being broadcast with correct format

**Q: Agents not appearing**  
A: Set `auto-initialize="true"` or call `flowStore.initializeFromAgents()` manually

**Q: Poor performance with many agents**  
A: Reduce animation speed or disable minimap/controls with `:show-minimap="false"`

**Q: Styling looks wrong**  
A: Ensure Vuetify dark theme is configured in `config/theme.js`

## Full Documentation

See `frontend/AGENT_FLOW_VISUALIZATION_INTEGRATION.md` for:
- Complete API reference
- All event types and formats
- Performance optimization guide
- Advanced customization options
- Troubleshooting guide

## Component Overview

| Component | Purpose | Usage |
|-----------|---------|-------|
| FlowCanvas | Main visualization | Wrap your entire visualization |
| AgentNode | Single agent display | Used automatically in FlowCanvas |
| ThreadView | Message conversations | Show messages for selected agent |
| MissionDashboard | Mission overview | Display mission progress |
| ArtifactTimeline | File tracking | Show created artifacts |

## Key Features

✅ Real-time agent monitoring  
✅ Message flow visualization  
✅ Professional dark theme  
✅ Smooth 60 FPS animations  
✅ Search and filter capabilities  
✅ Responsive design  
✅ Mobile friendly  
✅ Accessible (a11y)  

---

**For more details, see the full integration guide.**
