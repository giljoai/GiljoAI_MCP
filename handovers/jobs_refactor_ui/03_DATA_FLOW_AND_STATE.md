# Data Flow and State Management

**Document ID**: jobs_refactor_ui/03
**Created**: 2025-11-21

---

## Table of Contents

1. [State Management Architecture](#state-management-architecture)
2. [Pinia Store Structure](#pinia-store-structure)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [WebSocket Integration](#websocket-integration)
5. [API Integration Patterns](#api-integration-patterns)
6. [Caching Strategy](#caching-strategy)

---

## State Management Architecture

### Overview

The jobs page refactor uses **Pinia** for centralized state management with three primary stores:

1. **projectJobsStore** - Project-level data (description, mission, staging status)
2. **agentStore** - Agent data, statuses, message queue
3. **uiStore** - UI state (active tab, modals, notifications)

---

## Pinia Store Structure

### 1. projectJobsStore

**File**: `frontend/stores/projectJobs.ts`

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useProjectJobsStore = defineStore('projectJobs', () => {
  // State
  const currentProjectId = ref<string | null>(null)
  const projectDescription = ref<string>('')
  const orchestratorMission = ref<string>('')
  const stagingStatus = ref<'Waiting' | 'Working' | 'Completed!'>('Waiting')
  const isLaunching = ref(false)
  const launchComplete = ref(false)

  // Getters
  const isStagingDisabled = computed(() => stagingStatus.value !== 'Waiting')
  const isLaunchEnabled = computed(() => stagingStatus.value === 'Completed!')

  // Actions
  async function loadProject(projectId: string) {
    currentProjectId.value = projectId
    try {
      const response = await api.get(`/api/projects/${projectId}`)
      projectDescription.value = response.data.project_description
      orchestratorMission.value = response.data.orchestrator_mission || ''
      stagingStatus.value = response.data.staging_status || 'Waiting'
      launchComplete.value = response.data.jobs_launched || false
    } catch (error) {
      console.error('Failed to load project:', error)
      throw error
    }
  }

  async function updateProjectDescription(description: string) {
    projectDescription.value = description
    try {
      await api.patch(`/api/projects/${currentProjectId.value}`, {
        project_description: description
      })
    } catch (error) {
      console.error('Failed to update description:', error)
      throw error
    }
  }

  async function stageProject() {
    stagingStatus.value = 'Working'
    try {
      // Get staging prompt
      const response = await api.post(
        `/api/projects/${currentProjectId.value}/stage/prompt`
      )
      const prompt = response.data.prompt

      // Copy to clipboard
      await navigator.clipboard.writeText(prompt)

      // Show notification
      showToast('Staging prompt copied! Paste in CLI tool.')

      // API call to initialize staging (orchestrator will fill mission via WebSocket)
      await api.post(`/api/projects/${currentProjectId.value}/stage`)

      // Status will update to 'Completed!' via WebSocket when done
    } catch (error) {
      console.error('Failed to stage project:', error)
      stagingStatus.value = 'Waiting'
      throw error
    }
  }

  function updateStagingStatus(status: 'Waiting' | 'Working' | 'Completed!') {
    stagingStatus.value = status
  }

  function appendMissionText(text: string) {
    orchestratorMission.value += text
  }

  function setMission(text: string) {
    orchestratorMission.value = text
  }

  async function launchJobs() {
    isLaunching.value = true
    try {
      await api.post(`/api/projects/${currentProjectId.value}/launch-jobs`)
      launchComplete.value = true
    } catch (error) {
      console.error('Failed to launch jobs:', error)
      throw error
    } finally {
      isLaunching.value = false
    }
  }

  function reset() {
    currentProjectId.value = null
    projectDescription.value = ''
    orchestratorMission.value = ''
    stagingStatus.value = 'Waiting'
    isLaunching.value = false
    launchComplete.value = false
  }

  return {
    // State
    currentProjectId,
    projectDescription,
    orchestratorMission,
    stagingStatus,
    isLaunching,
    launchComplete,

    // Getters
    isStagingDisabled,
    isLaunchEnabled,

    // Actions
    loadProject,
    updateProjectDescription,
    stageProject,
    updateStagingStatus,
    appendMissionText,
    setMission,
    launchJobs,
    reset
  }
})
```

---

### 2. agentStore

**File**: `frontend/stores/agents.ts`

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Agent {
  id: string
  agent_type: 'orchestrator' | 'analyzer' | 'implementor' | 'tester'
  mission: string
  status: 'Waiting' | 'Working' | 'Working...' | 'Completed!'
  job_read: boolean
  job_acknowledged: boolean
  messages_sent: number
  messages_waiting: number
  messages_read: number
  cli_mode: 'claude-code' | 'general'
}

export interface AgentMessage {
  id: string
  from_agent_id: string
  to_agent_id: string | null  // null = broadcast
  message_type: 'direct' | 'broadcast'
  content: string
  read: boolean
  created_at: string
  read_at: string | null
}

export const useAgentStore = defineStore('agents', () => {
  // State
  const agents = ref<Agent[]>([])
  const messages = ref<AgentMessage[]>([])
  const cliMode = ref<boolean>(true)  // true = Claude Code CLI
  const promptsCopied = ref<Set<string>>(new Set())

  // Getters
  const orchestrator = computed(() => {
    return agents.value.find(a => a.agent_type === 'orchestrator')
  })

  const subagents = computed(() => {
    return agents.value.filter(a => a.agent_type !== 'orchestrator')
  })

  const agentById = computed(() => {
    return (id: string) => agents.value.find(a => a.id === id)
  })

  const messagesByAgent = computed(() => {
    return (agentId: string) => {
      return messages.value.filter(
        m => m.to_agent_id === agentId || m.from_agent_id === agentId || m.to_agent_id === null
      )
    }
  })

  // Actions
  async function loadAgents(projectId: string) {
    try {
      const response = await api.get(`/api/projects/${projectId}/agents`)
      agents.value = response.data.agents
    } catch (error) {
      console.error('Failed to load agents:', error)
      throw error
    }
  }

  async function loadMessages(projectId: string) {
    try {
      const response = await api.get(`/api/projects/${projectId}/messages`)
      messages.value = response.data.messages
    } catch (error) {
      console.error('Failed to load messages:', error)
      throw error
    }
  }

  function updateAgent(agentId: string, updates: Partial<Agent>) {
    const index = agents.value.findIndex(a => a.id === agentId)
    if (index !== -1) {
      agents.value[index] = { ...agents.value[index], ...updates }
    }
  }

  function updateAgentStatus(agentId: string, status: Agent['status']) {
    updateAgent(agentId, { status })
  }

  function setJobRead(agentId: string, read: boolean) {
    updateAgent(agentId, { job_read: read })
  }

  function setJobAcknowledged(agentId: string, acknowledged: boolean) {
    updateAgent(agentId, { job_acknowledged: acknowledged })
  }

  function incrementMessagesSent(agentId: string) {
    const agent = agentById.value(agentId)
    if (agent) {
      updateAgent(agentId, { messages_sent: agent.messages_sent + 1 })
    }
  }

  function incrementMessagesWaiting(agentId: string) {
    const agent = agentById.value(agentId)
    if (agent) {
      updateAgent(agentId, { messages_waiting: agent.messages_waiting + 1 })
    }
  }

  function incrementMessagesRead(agentId: string) {
    const agent = agentById.value(agentId)
    if (agent) {
      updateAgent(agentId, {
        messages_read: agent.messages_read + 1,
        messages_waiting: Math.max(0, agent.messages_waiting - 1)
      })
    }
  }

  function addMessage(message: AgentMessage) {
    messages.value.push(message)

    // Update counters
    if (message.from_agent_id) {
      incrementMessagesSent(message.from_agent_id)
    }
    if (message.to_agent_id) {
      incrementMessagesWaiting(message.to_agent_id)
    } else {
      // Broadcast - increment all agents
      agents.value.forEach(agent => {
        if (agent.id !== message.from_agent_id) {
          incrementMessagesWaiting(agent.id)
        }
      })
    }
  }

  function markMessageRead(messageId: string) {
    const message = messages.value.find(m => m.id === messageId)
    if (message && !message.read) {
      message.read = true
      message.read_at = new Date().toISOString()

      // Update counter
      if (message.to_agent_id) {
        incrementMessagesRead(message.to_agent_id)
      }
    }
  }

  async function copyPrompt(agentId: string) {
    try {
      const response = await api.get(
        `/api/agents/${agentId}/prompt`,
        { params: { cli_mode: cliMode.value ? 'claude-code' : 'general' } }
      )
      const prompt = response.data.prompt

      await navigator.clipboard.writeText(prompt)
      promptsCopied.value.add(agentId)

      showToast(`Prompt copied for ${agentById.value(agentId)?.agent_type}!`)

      // Reset after 2 seconds
      setTimeout(() => {
        promptsCopied.value.delete(agentId)
      }, 2000)

      return prompt
    } catch (error) {
      console.error('Failed to copy prompt:', error)
      throw error
    }
  }

  async function sendMessage(toAgentId: string, content: string, fromAgentId?: string) {
    try {
      const response = await api.post('/api/agents/messages', {
        from_agent_id: fromAgentId || null,
        to_agent_id: toAgentId,
        message_type: 'direct',
        content
      })

      addMessage(response.data.message)
      showToast('Message sent!')
    } catch (error) {
      console.error('Failed to send message:', error)
      throw error
    }
  }

  async function sendBroadcast(content: string, fromAgentId?: string) {
    try {
      const response = await api.post('/api/agents/broadcast', {
        from_agent_id: fromAgentId || null,
        content
      })

      addMessage(response.data.message)
      showToast('Broadcast sent to all agents!')
    } catch (error) {
      console.error('Failed to send broadcast:', error)
      throw error
    }
  }

  function toggleCLIMode() {
    cliMode.value = !cliMode.value
  }

  function reset() {
    agents.value = []
    messages.value = []
    cliMode.value = true
    promptsCopied.value.clear()
  }

  return {
    // State
    agents,
    messages,
    cliMode,
    promptsCopied,

    // Getters
    orchestrator,
    subagents,
    agentById,
    messagesByAgent,

    // Actions
    loadAgents,
    loadMessages,
    updateAgent,
    updateAgentStatus,
    setJobRead,
    setJobAcknowledged,
    incrementMessagesSent,
    incrementMessagesWaiting,
    incrementMessagesRead,
    addMessage,
    markMessageRead,
    copyPrompt,
    sendMessage,
    sendBroadcast,
    toggleCLIMode,
    reset
  }
})
```

---

### 3. uiStore

**File**: `frontend/stores/ui.ts`

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUIStore = defineStore('ui', () => {
  // State
  const activeTab = ref<'launch' | 'implementation'>('launch')
  const showAgentTemplateModal = ref(false)
  const selectedAgentForTemplate = ref<string | null>(null)
  const showMessageHistoryModal = ref(false)
  const selectedAgentForMessages = ref<string | null>(null)
  const toasts = ref<Array<{ id: string; message: string; type: string }>>([])

  // Actions
  function switchTab(tab: 'launch' | 'implementation') {
    activeTab.value = tab
  }

  function openAgentTemplateModal(agentId: string) {
    selectedAgentForTemplate.value = agentId
    showAgentTemplateModal.value = true
  }

  function closeAgentTemplateModal() {
    showAgentTemplateModal.value = false
    selectedAgentForTemplate.value = null
  }

  function openMessageHistoryModal(agentId: string) {
    selectedAgentForMessages.value = agentId
    showMessageHistoryModal.value = true
  }

  function closeMessageHistoryModal() {
    showMessageHistoryModal.value = false
    selectedAgentForMessages.value = null
  }

  function showToast(message: string, type = 'success') {
    const id = Math.random().toString(36).substr(2, 9)
    toasts.value.push({ id, message, type })

    // Auto-dismiss after 3 seconds
    setTimeout(() => {
      dismissToast(id)
    }, 3000)
  }

  function dismissToast(id: string) {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }

  function reset() {
    activeTab.value = 'launch'
    showAgentTemplateModal.value = false
    selectedAgentForTemplate.value = null
    showMessageHistoryModal.value = false
    selectedAgentForMessages.value = null
    toasts.value = []
  }

  return {
    // State
    activeTab,
    showAgentTemplateModal,
    selectedAgentForTemplate,
    showMessageHistoryModal,
    selectedAgentForMessages,
    toasts,

    // Actions
    switchTab,
    openAgentTemplateModal,
    closeAgentTemplateModal,
    openMessageHistoryModal,
    closeMessageHistoryModal,
    showToast,
    dismissToast,
    reset
  }
})
```

---

## Data Flow Diagrams

### 1. Stage Project Flow

```
USER                     COMPONENT                  STORE                   API                    WEBSOCKET
│                       │                          │                       │                       │
│ Click "Stage          │                          │                       │                       │
│ Project"              │                          │                       │                       │
├──────────────────────>│                          │                       │                       │
│                       │ call stageProject()      │                       │                       │
│                       ├─────────────────────────>│                       │                       │
│                       │                          │ POST /stage/prompt    │                       │
│                       │                          ├──────────────────────>│                       │
│                       │                          │<──────────────────────┤                       │
│                       │                          │ {prompt: "..."}       │                       │
│                       │                          │                       │                       │
│                       │<─────────────────────────┤                       │                       │
│                       │ copy to clipboard        │                       │                       │
│                       │                          │                       │                       │
│<──────────────────────┤                          │                       │                       │
│ "Prompt copied!"      │                          │                       │                       │
│                       │                          │ POST /stage           │                       │
│                       │                          ├──────────────────────>│                       │
│                       │                          │                       │ Orchestrator starts   │
│                       │                          │                       │                       │
│                       │                          │ stagingStatus='Working'                       │
│                       │                          │                       │                       │
│                       │ re-render                │                       │                       │
│<──────────────────────┤                          │                       │                       │
│ Status: "Working"     │                          │                       │                       │
│                       │                          │                       │ project:stage_started │
│                       │                          │<──────────────────────┼───────────────────────┤
│                       │                          │                       │                       │
│                       │                          │                       │ mission:text_chunk    │
│                       │                          │<──────────────────────┼───────────────────────┤
│                       │                          │ appendMissionText()   │                       │
│                       │ re-render (streaming)    │                       │                       │
│<──────────────────────┤                          │                       │                       │
│ Mission text appears  │                          │                       │                       │
│                       │                          │                       │ agents:created        │
│                       │                          │<──────────────────────┼───────────────────────┤
│                       │                          │ agentStore.loadAgents()                       │
│                       │ re-render                │                       │                       │
│<──────────────────────┤                          │                       │                       │
│ Agent Team populated  │                          │                       │                       │
│                       │                          │                       │ project:stage_complete│
│                       │                          │<──────────────────────┼───────────────────────┤
│                       │                          │ stagingStatus='Completed!'                   │
│                       │ re-render                │                       │                       │
│<──────────────────────┤                          │                       │                       │
│ Status: "Completed!"  │                          │                       │                       │
│ Launch Jobs active    │                          │                       │                       │
```

---

### 2. Launch Jobs Flow

```
USER                     COMPONENT                  STORE                   API                    WEBSOCKET
│                       │                          │                       │                       │
│ Click "Launch         │                          │                       │                       │
│ Jobs"                 │                          │                       │                       │
├──────────────────────>│                          │                       │                       │
│                       │ call launchJobs()        │                       │                       │
│                       ├─────────────────────────>│                       │                       │
│                       │                          │ POST /launch-jobs     │                       │
│                       │                          ├──────────────────────>│                       │
│                       │                          │                       │ Initialize message    │
│                       │                          │                       │ queue for all agents  │
│                       │                          │<──────────────────────┤                       │
│                       │                          │                       │                       │
│                       │<─────────────────────────┤                       │                       │
│                       │ uiStore.switchTab('implementation')              │                       │
│                       │                          │                       │                       │
│<──────────────────────┤                          │                       │                       │
│ Implementation tab    │                          │                       │                       │
│ loads                 │                          │                       │                       │
│                       │                          │                       │                       │
│                       │ agentStore.loadAgents()  │                       │                       │
│                       ├─────────────────────────>│                       │                       │
│                       │                          │ GET /agents           │                       │
│                       │                          ├──────────────────────>│                       │
│                       │                          │<──────────────────────┤                       │
│                       │<─────────────────────────┤                       │                       │
│                       │ re-render                │                       │                       │
│<──────────────────────┤                          │                       │                       │
│ Status Board visible  │                          │                       │                       │
│ All agents: Waiting   │                          │                       │                       │
│ Messages waiting: 1   │                          │                       │                       │
```

---

### 3. Copy Prompt and Agent Execution Flow (Claude Code CLI Mode)

```
USER                     COMPONENT                  STORE                   API                    WEBSOCKET
│                       │                          │                       │                       │
│ Click ▶ on            │                          │                       │                       │
│ Orchestrator          │                          │                       │                       │
├──────────────────────>│                          │                       │                       │
│                       │ call copyPrompt(agentId) │                       │                       │
│                       ├─────────────────────────>│                       │                       │
│                       │                          │ GET /agents/:id/prompt│                       │
│                       │                          │ ?cli_mode=claude-code │                       │
│                       │                          ├──────────────────────>│                       │
│                       │                          │<──────────────────────┤                       │
│                       │                          │ {prompt: "..."}       │                       │
│                       │<─────────────────────────┤                       │                       │
│                       │ copy to clipboard        │                       │                       │
│<──────────────────────┤                          │                       │                       │
│ "Prompt copied!"      │                          │                       │                       │
│                       │                          │                       │                       │
│ Paste in Claude Code  │                          │                       │                       │
│ CLI                   │                          │                       │                       │
│                       │                          │                       │                       │
│ Orchestrator reads    │                          │                       │ agent:job_read        │
│ job                   │                          │<──────────────────────┼───────────────────────┤
│                       │                          │ setJobRead(agentId, true)                     │
│                       │ re-render                │                       │                       │
│<──────────────────────┤                          │                       │                       │
│ Job Read: ✓           │                          │                       │                       │
│                       │                          │                       │ agent:job_acknowledged│
│                       │                          │<──────────────────────┼───────────────────────┤
│                       │                          │ setJobAcknowledged(agentId, true)             │
│                       │ re-render                │                       │                       │
│<──────────────────────┤                          │                       │                       │
│ Job Ack: ✓            │                          │                       │                       │
│                       │                          │                       │ agent:status_changed  │
│                       │                          │<──────────────────────┼───────────────────────┤
│                       │                          │ updateAgentStatus(agentId, 'Working')         │
│                       │ re-render                │                       │                       │
│<──────────────────────┤                          │                       │                       │
│ Status: Working       │                          │                       │                       │
│                       │                          │                       │                       │
│ Subagents auto-       │                          │                       │ agent:status_changed  │
│ triggered by Claude   │                          │<──────────────────────┼───────────────────────┤
│ Code                  │                          │ updateAgentStatus(subagentId, 'Working')      │
│                       │ re-render                │                       │                       │
│<──────────────────────┤                          │                       │                       │
│ All agents: Working   │                          │                       │                       │
│                       │                          │                       │                       │
│ Messages exchanged    │                          │                       │ agent:message_sent    │
│                       │                          │<──────────────────────┼───────────────────────┤
│                       │                          │ addMessage()          │                       │
│                       │                          │ incrementMessagesSent()                       │
│                       │                          │ incrementMessagesWaiting()                    │
│                       │ re-render                │                       │                       │
│<──────────────────────┤                          │                       │                       │
│ Message counts update │                          │                       │                       │
│                       │                          │                       │ agent:status_changed  │
│                       │                          │<──────────────────────┼───────────────────────┤
│                       │                          │ updateAgentStatus(agentId, 'Completed!')      │
│                       │ re-render                │                       │                       │
│<──────────────────────┤                          │                       │                       │
│ Status: Completed!    │                          │                       │                       │
```

---

### 4. Send Message Flow

```
USER                     COMPONENT                  STORE                   API                    WEBSOCKET
│                       │                          │                       │                       │
│ Select "Message       │                          │                       │                       │
│ Orchestrator"         │                          │                       │                       │
├──────────────────────>│                          │                       │                       │
│                       │ selectedRecipient set    │                       │                       │
│                       │                          │                       │                       │
│ Type "Hello"          │                          │                       │                       │
├──────────────────────>│                          │                       │                       │
│                       │ messageText updated      │                       │                       │
│                       │                          │                       │                       │
│ Click Send            │                          │                       │                       │
├──────────────────────>│                          │                       │                       │
│                       │ call sendMessage()       │                       │                       │
│                       ├─────────────────────────>│                       │                       │
│                       │                          │ POST /agents/messages │                       │
│                       │                          ├──────────────────────>│                       │
│                       │                          │                       │ Store message in DB   │
│                       │                          │<──────────────────────┤                       │
│                       │                          │ {message: {...}}      │                       │
│                       │                          │ addMessage()          │                       │
│                       │<─────────────────────────┤                       │                       │
│                       │ clear input              │                       │                       │
│<──────────────────────┤                          │                       │                       │
│ "Message sent!"       │                          │                       │                       │
│ Input cleared         │                          │                       │                       │
│                       │                          │                       │ agent:message_received│
│                       │                          │<──────────────────────┼───────────────────────┤
│                       │                          │ (broadcast to all clients)                    │
│                       │ re-render                │                       │                       │
│<──────────────────────┤                          │                       │                       │
│ Messages Waiting: +1  │                          │                       │                       │
```

---

## WebSocket Integration

### WebSocket Event Handler

**File**: `frontend/services/websocket.ts`

```typescript
import { useProjectJobsStore } from '@/stores/projectJobs'
import { useAgentStore } from '@/stores/agents'
import { useUIStore } from '@/stores/ui'

export class JobsWebSocketHandler {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5

  connect(projectId: string, token: string) {
    const wsUrl = `ws://localhost:7272/ws/projects/${projectId}?token=${token}`
    this.ws = new WebSocket(wsUrl)

    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
    }

    this.ws.onmessage = (event) => {
      this.handleMessage(JSON.parse(event.data))
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    this.ws.onclose = () => {
      console.log('WebSocket closed')
      this.attemptReconnect(projectId, token)
    }
  }

  private handleMessage(data: any) {
    const projectStore = useProjectJobsStore()
    const agentStore = useAgentStore()
    const uiStore = useUIStore()

    switch (data.event) {
      case 'project:stage_started':
        projectStore.updateStagingStatus('Working')
        break

      case 'project:mission_chunk':
        projectStore.appendMissionText(data.text)
        break

      case 'project:stage_completed':
        projectStore.updateStagingStatus('Completed!')
        projectStore.setMission(data.mission)
        uiStore.showToast('Staging completed!')
        break

      case 'project:jobs_launched':
        agentStore.loadAgents(data.project_id)
        uiStore.showToast('Jobs launched!')
        break

      case 'agent:status_changed':
        agentStore.updateAgentStatus(data.agent_id, data.status)
        break

      case 'agent:job_read':
        agentStore.setJobRead(data.agent_id, true)
        break

      case 'agent:job_acknowledged':
        agentStore.setJobAcknowledged(data.agent_id, true)
        break

      case 'agent:message_sent':
        agentStore.addMessage(data.message)
        break

      case 'agent:message_read':
        agentStore.markMessageRead(data.message_id)
        break

      case 'agents:created':
        agentStore.loadAgents(data.project_id)
        break

      default:
        console.warn('Unknown WebSocket event:', data.event)
    }
  }

  private attemptReconnect(projectId: string, token: string) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000)
      console.log(`Reconnecting in ${delay}ms...`)
      setTimeout(() => this.connect(projectId, token), delay)
    } else {
      console.error('Max reconnection attempts reached')
      const uiStore = useUIStore()
      uiStore.showToast('Connection lost. Please refresh the page.', 'error')
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}
```

---

## API Integration Patterns

### API Service

**File**: `frontend/services/api.ts`

```typescript
import axios from 'axios'

const apiClient = axios.create({
  baseURL: 'http://localhost:7272',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add auth token to requests
apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle errors
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient
```

---

## Caching Strategy

### 1. API Response Caching

```typescript
// Cache GET requests for 30 seconds
const cache = new Map<string, { data: any; timestamp: number }>()
const CACHE_DURATION = 30000 // 30 seconds

apiClient.interceptors.request.use(config => {
  if (config.method === 'get') {
    const cacheKey = `${config.url}?${JSON.stringify(config.params)}`
    const cached = cache.get(cacheKey)

    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
      // Return cached response
      return Promise.resolve({ ...config, data: cached.data })
    }
  }
  return config
})

apiClient.interceptors.response.use(response => {
  if (response.config.method === 'get') {
    const cacheKey = `${response.config.url}?${JSON.stringify(response.config.params)}`
    cache.set(cacheKey, {
      data: response.data,
      timestamp: Date.now()
    })
  }
  return response
})
```

### 2. Store Persistence

```typescript
// Persist stores to localStorage
export const persistStorePlugin = ({ store }) => {
  const key = `pinia_${store.$id}`

  // Load from localStorage on init
  const saved = localStorage.getItem(key)
  if (saved) {
    try {
      store.$patch(JSON.parse(saved))
    } catch (error) {
      console.error('Failed to load store from localStorage:', error)
    }
  }

  // Save to localStorage on changes
  store.$subscribe((mutation, state) => {
    localStorage.setItem(key, JSON.stringify(state))
  })
}
```

---

## Performance Optimization

### 1. Debouncing

```typescript
// Debounce project description updates
import { debounce } from 'lodash-es'

const debouncedUpdateDescription = debounce((description: string) => {
  projectStore.updateProjectDescription(description)
}, 500)
```

### 2. Virtual Scrolling

For large agent lists (future enhancement):

```vue
<template>
  <v-virtual-scroll
    :items="agents"
    item-height="60"
    height="400"
  >
    <template #default="{ item }">
      <AgentRow :agent="item" />
    </template>
  </v-virtual-scroll>
</template>
```

---

## Next Document

[04_API_SPECIFICATIONS.md](./04_API_SPECIFICATIONS.md) - Backend API endpoints and database schema

---

**Document Version**: 1.0
**Last Updated**: 2025-11-21
