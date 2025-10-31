<template>
  <v-container fluid class="pa-4">
    <v-row>
      <v-col cols="12">
        <h2 class="text-h4 mb-4">AgentCardEnhanced - Usage Examples</h2>
        <p class="text-body-1 mb-6">
          Production-grade examples showing all modes and states of the AgentCardEnhanced component.
        </p>
      </v-col>
    </v-row>

    <!-- Launch Tab Mode -->
    <v-row>
      <v-col cols="12">
        <h3 class="text-h5 mb-3">Launch Tab Mode</h3>
        <p class="text-body-2 mb-4">
          Displays agent with mission text and "Edit Mission" button.
        </p>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" md="4" lg="3">
        <AgentCardEnhanced
          :agent="launchTabAgent"
          mode="launch"
          @edit-mission="handleEditMission"
        />
      </v-col>
    </v-row>

    <v-divider class="my-6" />

    <!-- Jobs Tab - All States -->
    <v-row>
      <v-col cols="12">
        <h3 class="text-h5 mb-3">Jobs Tab - All Agent States</h3>
        <p class="text-body-2 mb-4">
          Shows cards in all possible states: waiting, working, complete, failed, blocked.
        </p>
      </v-col>
    </v-row>

    <v-row>
      <!-- Waiting State -->
      <v-col cols="12" md="4" lg="3">
        <div class="mb-2">
          <v-chip color="grey" size="small" class="mb-2">Waiting State</v-chip>
        </div>
        <AgentCardEnhanced
          :agent="waitingAgent"
          mode="jobs"
          @launch-agent="handleLaunchAgent"
        />
      </v-col>

      <!-- Working State -->
      <v-col cols="12" md="4" lg="3">
        <div class="mb-2">
          <v-chip color="primary" size="small" class="mb-2">Working State</v-chip>
        </div>
        <AgentCardEnhanced
          :agent="workingAgent"
          mode="jobs"
          @view-details="handleViewDetails"
        />
      </v-col>

      <!-- Complete State -->
      <v-col cols="12" md="4" lg="3">
        <div class="mb-2">
          <v-chip color="yellow-darken-2" size="small" class="mb-2">Complete State</v-chip>
        </div>
        <AgentCardEnhanced
          :agent="completeAgent"
          mode="jobs"
        />
      </v-col>

      <!-- Failed State -->
      <v-col cols="12" md="4" lg="3">
        <div class="mb-2">
          <v-chip color="purple" size="small" class="mb-2">Failed State (Priority)</v-chip>
        </div>
        <AgentCardEnhanced
          :agent="failedAgent"
          mode="jobs"
          @view-error="handleViewError"
        />
      </v-col>

      <!-- Blocked State -->
      <v-col cols="12" md="4" lg="3">
        <div class="mb-2">
          <v-chip color="orange" size="small" class="mb-2">Blocked State (Priority)</v-chip>
        </div>
        <AgentCardEnhanced
          :agent="blockedAgent"
          mode="jobs"
          @view-error="handleViewError"
        />
      </v-col>
    </v-row>

    <v-divider class="my-6" />

    <!-- Message Badges Example -->
    <v-row>
      <v-col cols="12">
        <h3 class="text-h5 mb-3">Message Badges</h3>
        <p class="text-body-2 mb-4">
          Shows three separate message count badges: unread (red), acknowledged (green), sent (grey).
        </p>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" md="4" lg="3">
        <AgentCardEnhanced
          :agent="agentWithMessages"
          mode="jobs"
          @view-details="handleViewDetails"
        />
      </v-col>
    </v-row>

    <v-divider class="my-6" />

    <!-- Multi-Instance Agents -->
    <v-row>
      <v-col cols="12">
        <h3 class="text-h5 mb-3">Multi-Instance Agents</h3>
        <p class="text-body-2 mb-4">
          Multiple instances of the same agent type with instance numbers.
        </p>
      </v-col>
    </v-row>

    <v-row>
      <v-col
        v-for="instance in multiInstanceAgents"
        :key="instance.job_id"
        cols="12"
        md="4"
        lg="3"
      >
        <AgentCardEnhanced
          :agent="instance"
          mode="jobs"
          :instance-number="instance.instanceNumber"
        />
      </v-col>
    </v-row>

    <v-divider class="my-6" />

    <!-- Orchestrator Special Features -->
    <v-row>
      <v-col cols="12">
        <h3 class="text-h5 mb-3">Orchestrator Special Features</h3>
        <p class="text-body-2 mb-4">
          Orchestrator with LaunchPromptIcons and Closeout Project button.
        </p>
      </v-col>
    </v-row>

    <v-row>
      <!-- Orchestrator Working -->
      <v-col cols="12" md="4" lg="3">
        <div class="mb-2">
          <v-chip color="primary" size="small" class="mb-2">Orchestrator Working</v-chip>
        </div>
        <AgentCardEnhanced
          :agent="orchestratorWorking"
          mode="jobs"
          is-orchestrator
          @view-details="handleViewDetails"
        />
      </v-col>

      <!-- Orchestrator Complete with Closeout -->
      <v-col cols="12" md="4" lg="3">
        <div class="mb-2">
          <v-chip color="success" size="small" class="mb-2">Orchestrator Complete (Closeout)</v-chip>
        </div>
        <AgentCardEnhanced
          :agent="orchestratorComplete"
          mode="jobs"
          is-orchestrator
          show-closeout-button
          @closeout-project="handleCloseoutProject"
        />
      </v-col>
    </v-row>

    <v-divider class="my-6" />

    <!-- Event Log -->
    <v-row>
      <v-col cols="12">
        <h3 class="text-h5 mb-3">Event Log</h3>
        <v-card variant="outlined">
          <v-card-text>
            <div v-if="eventLog.length === 0" class="text-body-2 text-grey">
              No events yet. Interact with the cards above to see events.
            </div>
            <div v-else>
              <div
                v-for="(event, index) in eventLog"
                :key="index"
                class="event-log-entry mb-2"
              >
                <v-chip :color="event.color" size="x-small" class="mr-2">
                  {{ event.type }}
                </v-chip>
                <span class="text-body-2">{{ event.message }}</span>
                <span class="text-caption text-grey ml-2">{{ event.timestamp }}</span>
              </div>
            </div>
          </v-card-text>
          <v-card-actions v-if="eventLog.length > 0">
            <v-btn
              variant="text"
              color="error"
              size="small"
              @click="clearEventLog"
            >
              Clear Log
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import AgentCardEnhanced from './AgentCardEnhanced.vue'

/**
 * AgentCardEnhanced Usage Examples
 *
 * This file demonstrates all modes, states, and features of the AgentCardEnhanced component.
 * Use this as a reference for integration into the Launch Jobs dual-tab interface.
 */

// Event log for tracking interactions
const eventLog = ref([])

function addEvent(type, message, color = 'primary') {
  eventLog.value.unshift({
    type,
    message,
    color,
    timestamp: new Date().toLocaleTimeString()
  })
}

function clearEventLog() {
  eventLog.value = []
}

// Launch Tab Agent
const launchTabAgent = {
  job_id: 'launch-001',
  agent_type: 'orchestrator',
  agent_name: 'Orchestrator',
  status: 'waiting',
  mission: 'Coordinate the implementation of the user authentication system. This includes creating the database schema, implementing the API endpoints, and building the frontend login/register forms.',
  messages: []
}

// Waiting State Agent
const waitingAgent = {
  job_id: 'waiting-001',
  agent_type: 'implementor',
  agent_name: 'Implementor',
  status: 'waiting',
  mission: 'Implement user registration API endpoint with email verification',
  messages: []
}

// Working State Agent
const workingAgent = {
  job_id: 'working-001',
  agent_type: 'analyzer',
  agent_name: 'Analyzer',
  status: 'working',
  mission: 'Analyze authentication requirements and design security architecture',
  progress: 65,
  current_task: 'Reviewing OAuth 2.0 implementation patterns',
  messages: []
}

// Complete State Agent
const completeAgent = {
  job_id: 'complete-001',
  agent_type: 'tester',
  agent_name: 'Tester',
  status: 'complete',
  mission: 'Test user authentication flow end-to-end',
  progress: 100,
  messages: []
}

// Failed State Agent
const failedAgent = {
  job_id: 'failed-001',
  agent_type: 'implementor',
  agent_name: 'Backend Implementor',
  status: 'failed',
  mission: 'Implement password reset functionality',
  block_reason: 'Database connection timeout after 30 seconds. Cannot access users table.',
  messages: []
}

// Blocked State Agent
const blockedAgent = {
  job_id: 'blocked-001',
  agent_type: 'reviewer',
  agent_name: 'Code Reviewer',
  status: 'blocked',
  mission: 'Review authentication API implementation',
  block_reason: 'Waiting for developer approval on security architecture design document.',
  messages: []
}

// Agent with Messages
const agentWithMessages = {
  job_id: 'messages-001',
  agent_type: 'implementor',
  agent_name: 'Frontend Implementor',
  status: 'working',
  mission: 'Build user registration form with Vuetify components',
  progress: 75,
  current_task: 'Adding form validation and error handling',
  messages: [
    { id: 1, status: 'pending', from: 'agent', content: 'Need clarification on password requirements' },
    { id: 2, status: 'pending', from: 'agent', content: 'Should we support social login?' },
    { id: 3, status: 'acknowledged', from: 'agent', content: 'Form layout approved' },
    { id: 4, status: 'acknowledged', from: 'agent', content: 'Validation rules implemented' },
    { id: 5, status: 'acknowledged', from: 'agent', content: 'Email verification added' },
    { id: 6, from: 'developer', content: 'Use minimum 8 characters for password' },
    { id: 7, from: 'developer', content: 'Social login not required in v1' }
  ]
}

// Multi-Instance Agents
const multiInstanceAgents = [
  {
    job_id: 'multi-001',
    agent_type: 'implementor',
    agent_name: 'Implementor #1',
    status: 'complete',
    mission: 'Implement user login functionality',
    progress: 100,
    instanceNumber: 1,
    messages: []
  },
  {
    job_id: 'multi-002',
    agent_type: 'implementor',
    agent_name: 'Implementor #2',
    status: 'complete',
    mission: 'Implement user registration functionality',
    progress: 100,
    instanceNumber: 2,
    messages: []
  },
  {
    job_id: 'multi-003',
    agent_type: 'implementor',
    agent_name: 'Implementor #3',
    status: 'working',
    mission: 'Implement password reset functionality',
    progress: 40,
    current_task: 'Creating email template for reset link',
    instanceNumber: 3,
    messages: []
  }
]

// Orchestrator Working
const orchestratorWorking = {
  job_id: 'orch-001',
  agent_type: 'orchestrator',
  agent_name: 'Project Orchestrator',
  status: 'working',
  mission: 'Coordinate all agents to complete authentication system implementation',
  progress: 80,
  current_task: 'Monitoring agent progress and coordinating handoffs',
  messages: []
}

// Orchestrator Complete
const orchestratorComplete = {
  job_id: 'orch-002',
  agent_type: 'orchestrator',
  agent_name: 'Project Orchestrator',
  status: 'complete',
  mission: 'Coordinate all agents to complete authentication system implementation',
  progress: 100,
  messages: []
}

// Event Handlers
function handleEditMission(agent) {
  addEvent('edit-mission', `Edit mission requested for ${agent.agent_name}`, 'primary')
  console.log('[Edit Mission]', agent)
}

function handleLaunchAgent(agent) {
  addEvent('launch-agent', `Launch requested for ${agent.agent_name}`, 'yellow-darken-2')
  console.log('[Launch Agent]', agent)
}

function handleViewDetails(agent) {
  addEvent('view-details', `Details requested for ${agent.agent_name}`, 'blue')
  console.log('[View Details]', agent)
}

function handleViewError(agent) {
  addEvent('view-error', `Error details requested for ${agent.agent_name}`, 'error')
  console.log('[View Error]', agent)
}

function handleCloseoutProject() {
  addEvent('closeout-project', 'Closeout project requested', 'success')
  console.log('[Closeout Project]')
}
</script>

<style scoped>
.event-log-entry {
  display: flex;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.event-log-entry:last-child {
  border-bottom: none;
}
</style>
