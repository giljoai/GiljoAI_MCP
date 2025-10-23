# Handover 0021: Dashboard Integration for Agent Monitoring

**Handover ID**: 0021
**Creation Date**: 2025-10-14
**Target Date**: 2025-11-11 (1.5 week timeline)
**Priority**: MEDIUM
**Type**: IMPLEMENTATION
**Status**: Not Started
**Dependencies**: Handovers 0019 (Agent Jobs) and 0020 (Orchestrator) should be completed

---

## 1. Context and Background

**Purpose**: Create real-time dashboard components for monitoring and controlling the multi-agent orchestration system, providing visibility into agent activities, message flows, and performance metrics.

**Current State**:
- Basic task dashboard exists
- No agent job visibility
- No message monitoring
- No performance metrics display

**Target State**:
- Real-time agent job monitoring
- Message flow visualization
- Performance metrics dashboard
- Interactive agent controls
- Token usage tracking

---

## 2. Vue Components to Build

### Component 1: Agent Monitor Dashboard

```vue
<!-- components/agents/AgentMonitor.vue -->
<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <h2>Active Agent Jobs</h2>
      </v-col>
    </v-row>

    <v-row>
      <v-col v-for="job in activeJobs" :key="job.job_id" cols="12" md="6" lg="4">
        <agent-job-card
          :job="job"
          @message="sendMessage"
          @terminate="terminateJob"
        />
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <agent-timeline :events="agentEvents" />
      </v-col>
    </v-row>
  </v-container>
</template>
```

### Component 2: Agent Job Card

```vue
<!-- components/agents/AgentJobCard.vue -->
<template>
  <v-card>
    <v-card-title>
      <v-icon :color="statusColor">{{ agentIcon }}</v-icon>
      {{ job.agent_type }}
      <v-spacer />
      <v-chip :color="statusColor" small>
        {{ job.status }}
      </v-chip>
    </v-card-title>

    <v-card-text>
      <div class="mission-text">{{ job.mission }}</div>

      <v-progress-linear
        v-if="job.status === 'active'"
        :value="progress"
        color="primary"
        height="8"
      />

      <div class="metrics">
        <span>Tokens: {{ job.token_usage }}</span>
        <span>Messages: {{ job.messages.length }}</span>
        <span>Duration: {{ duration }}</span>
      </div>
    </v-card-text>

    <v-card-actions>
      <v-btn @click="viewDetails" text>Details</v-btn>
      <v-btn @click="sendMessage" text>Message</v-btn>
      <v-btn @click="terminate" text color="error">Terminate</v-btn>
    </v-card-actions>
  </v-card>
</template>
```

### Component 3: Message Flow Visualizer

```vue
<!-- components/agents/MessageFlow.vue -->
<template>
  <v-card>
    <v-card-title>Agent Communication</v-card-title>

    <v-card-text>
      <div class="message-timeline">
        <v-timeline dense>
          <v-timeline-item
            v-for="message in messages"
            :key="message.id"
            :color="getMessageColor(message)"
            small
          >
            <template v-slot:opposite>
              <span class="text-caption">{{ formatTime(message.timestamp) }}</span>
            </template>

            <v-card class="elevation-2">
              <v-card-subtitle>
                {{ message.from_agent }} → {{ message.to_agent }}
              </v-card-subtitle>
              <v-card-text>
                {{ message.content }}
                <v-chip
                  v-if="message.acknowledged"
                  x-small
                  color="success"
                  class="ml-2"
                >
                  Acknowledged
                </v-chip>
              </v-card-text>
            </v-card>
          </v-timeline-item>
        </v-timeline>
      </div>
    </v-card-text>
  </v-card>
</template>
```

### Component 4: Performance Metrics

```vue
<!-- components/agents/PerformanceMetrics.vue -->
<template>
  <v-card>
    <v-card-title>Performance Metrics</v-card-title>

    <v-card-text>
      <v-row>
        <v-col cols="12" md="3">
          <metric-card
            title="Token Reduction"
            :value="metrics.tokenReduction"
            suffix="%"
            icon="mdi-trending-down"
            color="success"
          />
        </v-col>

        <v-col cols="12" md="3">
          <metric-card
            title="Active Agents"
            :value="metrics.activeAgents"
            icon="mdi-robot"
            color="primary"
          />
        </v-col>

        <v-col cols="12" md="3">
          <metric-card
            title="Messages/Min"
            :value="metrics.messageRate"
            icon="mdi-message-fast"
            color="info"
          />
        </v-col>

        <v-col cols="12" md="3">
          <metric-card
            title="Success Rate"
            :value="metrics.successRate"
            suffix="%"
            icon="mdi-check-circle"
            color="success"
          />
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12">
          <token-usage-chart :data="tokenUsageData" />
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>
```

---

## 3. Implementation Requirements

### API Integration

```typescript
// stores/agents.ts
import { defineStore } from 'pinia'

export const useAgentStore = defineStore('agents', {
  state: () => ({
    activeJobs: [],
    messages: [],
    metrics: {},
    agentEvents: []
  }),

  actions: {
    async fetchActiveJobs() {
      const response = await api.get('/agent-jobs/active')
      this.activeJobs = response.data
    },

    async sendAgentMessage(fromAgent: string, toAgent: string, content: string) {
      await api.post('/agent-messages', {
        from_agent: fromAgent,
        to_agent: toAgent,
        content
      })
    },

    async acknowledgeMessage(messageId: string, agentId: string) {
      await api.post(`/agent-messages/${messageId}/ack`, {
        agent_id: agentId
      })
    }
  }
})
```

### WebSocket Integration

```typescript
// composables/useAgentWebSocket.ts
export function useAgentWebSocket() {
  const agentStore = useAgentStore()
  const { socket } = useWebSocket()

  // Listen for agent events
  socket.on('agent_job_created', (job) => {
    agentStore.activeJobs.push(job)
  })

  socket.on('agent_job_status_changed', (update) => {
    const index = agentStore.activeJobs.findIndex(j => j.job_id === update.job_id)
    if (index !== -1) {
      agentStore.activeJobs[index] = { ...agentStore.activeJobs[index], ...update }
    }
  })

  socket.on('agent_message_received', (message) => {
    agentStore.messages.unshift(message)
  })

  socket.on('performance_metrics_update', (metrics) => {
    agentStore.metrics = metrics
  })

  return { socket }
}
```

### Visualization Components

1. **Agent Network Graph** - D3.js visualization of agent relationships
2. **Token Usage Chart** - Chart.js for token metrics over time
3. **Message Heatmap** - Show communication patterns
4. **Progress Indicators** - Real-time job progress

---

## 4. Testing Requirements

### Component Tests
```typescript
// tests/components/AgentMonitor.spec.ts
describe('AgentMonitor', () => {
  it('displays active agent jobs')
  it('updates in real-time via WebSocket')
  it('handles agent termination')
  it('shows correct status indicators')
})
```

### Integration Tests
- WebSocket event handling
- API endpoint integration
- Store state management
- Real-time updates

### E2E Tests
- Complete agent monitoring flow
- Message sending and acknowledgment
- Performance metrics display
- Interactive controls

---

## 5. Success Criteria

- [ ] Real-time agent job display
- [ ] Message flow visualization
- [ ] Performance metrics accurate
- [ ] WebSocket updates working
- [ ] Interactive controls functional
- [ ] Responsive design implemented
- [ ] Dark mode support
- [ ] Accessibility compliant

---

## 6. Deliverables

1. **Agent monitoring components** (5 Vue components)
2. **Pinia store** for agent state management
3. **WebSocket integration** for real-time updates
4. **API integration layer**
5. **Visualization components** (charts/graphs)
6. **Component tests** with coverage
7. **User documentation** for dashboard

---

## 7. UI/UX Requirements

### Design Consistency
- Follow existing Vuetify theme
- Use color themes from `/docs/color_themes.md`
- Maintain consistent spacing and typography

### Responsive Design
- Mobile-friendly layouts
- Tablet optimization
- Desktop full-feature view

### Accessibility
- WCAG 2.1 AA compliance
- Keyboard navigation
- Screen reader support
- High contrast mode

---

## 8. Getting Started

1. Review existing dashboard components
2. Set up development environment
3. Create agent store with Pinia
4. Build AgentMonitor component first
5. Add WebSocket listeners
6. Implement visualization components
7. Test real-time updates
8. Add interactive controls

---

**Handover Status**: Ready for implementation (after 0019 & 0020)
**Estimated Effort**: 60 hours (1.5 weeks)
**Impact**: Provides visibility and control over agent orchestration