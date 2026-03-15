<template>
  <v-dialog
    :model-value="show"
    :fullscreen="isMobile"
    :max-width="isMobile ? undefined : '1000'"
    persistent
    role="dialog"
    aria-labelledby="review-modal-title"
    data-testid="review-modal"
    @keydown.esc="$emit('close')"
  >
    <v-card>
      <!-- Header -->
      <v-card-title id="review-modal-title" class="bg-primary text-white pa-4">
        <div class="d-flex align-center justify-space-between">
          <div class="d-flex align-center">
            <v-icon icon="mdi-eye" size="large" class="mr-2" />
            <span class="text-h6">Project Review: {{ projectData?.name }}</span>
          </div>
          <v-btn icon variant="text" color="white" aria-label="Close modal" @click="$emit('close')">
            <v-icon icon="mdi-close" />
          </v-btn>
        </div>
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-4" style="max-height: 70vh; overflow-y: auto;">
        <v-progress-linear v-if="loading" indeterminate color="primary" />
        <v-alert v-if="error" type="error" class="mb-4">{{ error }}</v-alert>

        <template v-if="projectData && !loading">
          <!-- Section 1: Project Overview -->
          <div class="mb-6">
            <h3 class="text-h6 mb-2">Overview</h3>
            <v-chip :color="statusColor" variant="flat" size="small" class="mr-2">{{ projectData.status }}</v-chip>
            <span class="text-caption text-medium-emphasis">
              Created {{ formatDate(projectData.created_at) }}
              <template v-if="projectData.completed_at"> | Completed {{ formatDate(projectData.completed_at) }}</template>
            </span>
            <p class="mt-2">{{ projectData.description || 'No description provided.' }}</p>
          </div>

          <!-- Section 2: Mission -->
          <div v-if="projectData.mission" class="mb-6">
            <h3 class="text-h6 mb-2">Mission</h3>
            <v-card variant="outlined" class="pa-3">
              <pre class="text-body-2" style="white-space: pre-wrap;">{{ missionText }}</pre>
            </v-card>
          </div>

          <!-- Section 3: Agent Roster -->
          <div v-if="agents.length" class="mb-6">
            <h3 class="text-h6 mb-2">Agents ({{ agents.length }})</h3>
            <v-table density="compact">
              <thead>
                <tr>
                  <th>Agent</th>
                  <th>Role</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="agent in agents" :key="agent.id">
                  <td>{{ agent.agent_display_name }}</td>
                  <td>{{ agent.agent_role || '-' }}</td>
                  <td><v-chip :color="agentStatusColor(agent.status)" size="x-small" variant="flat">{{ agent.status }}</v-chip></td>
                </tr>
              </tbody>
            </v-table>
          </div>

          <!-- Section 4: Agent Details (expandable, lazy-loaded messages) -->
          <div v-if="agents.length" class="mb-6">
            <h3 class="text-h6 mb-2">Agent Details</h3>
            <v-expansion-panels variant="accordion">
              <v-expansion-panel
                v-for="agent in agents"
                :key="agent.id"
                @group:selected="loadAgentMessages(agent)"
              >
                <v-expansion-panel-title>
                  {{ agent.agent_display_name }} - {{ agent.status }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-progress-linear v-if="agentMessages[agent.id]?.loading" indeterminate />
                  <div v-else-if="agentMessages[agent.id]?.messages?.length">
                    <div v-for="msg in agentMessages[agent.id].messages" :key="msg.id" class="mb-2 pa-2 rounded" style="background: rgba(0,0,0,0.03);">
                      <div class="d-flex justify-space-between">
                        <span class="text-caption font-weight-bold">{{ msg.from }}</span>
                        <span class="text-caption text-medium-emphasis">{{ formatDate(msg.created_at) }}</span>
                      </div>
                      <v-chip v-if="msg.direction" size="x-small" :color="msg.direction === 'outbound' ? 'primary' : 'default'" class="mr-1">{{ msg.direction }}</v-chip>
                      <p class="text-body-2 mt-1">{{ truncate(msg.content, 300) }}</p>
                    </div>
                  </div>
                  <p v-else class="text-caption text-medium-emphasis">No messages recorded.</p>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>

          <!-- Section 5: 360 Memory -->
          <div v-if="memoryEntries.length" class="mb-6">
            <h3 class="text-h6 mb-2">360 Memory ({{ memoryEntries.length }} entries)</h3>
            <v-expansion-panels variant="accordion">
              <v-expansion-panel v-for="(entry, i) in memoryEntries" :key="i">
                <v-expansion-panel-title>
                  #{{ entry.sequence ?? i + 1 }} - {{ entry.summary || 'Memory Entry' }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <pre class="text-body-2" style="white-space: pre-wrap;">{{ entry.summary || JSON.stringify(entry, null, 2) }}</pre>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>
        </template>
      </v-card-text>

      <v-divider />

      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn variant="elevated" color="primary" aria-label="Close review modal" @click="$emit('close')" data-testid="review-close-btn">
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useDisplay } from 'vuetify'
import api from '@/services/api'

const props = defineProps({
  show: { type: Boolean, required: true },
  projectId: { type: String, default: null },
  productId: { type: String, default: null },
})

defineEmits(['close'])

const { mobile } = useDisplay()
const isMobile = computed(() => mobile.value)

const loading = ref(false)
const error = ref(null)
const projectData = ref(null)
const agents = ref([])
const memoryEntries = ref([])
const agentMessages = reactive({})

watch(() => props.show, (open) => {
  if (open && props.projectId) {
    loadReviewData()
  } else {
    resetState()
  }
})

async function loadReviewData() {
  loading.value = true
  error.value = null
  try {
    // Fetch project, jobs, and memory in parallel
    const [projectRes, jobsRes, memoryRes] = await Promise.all([
      api.projects.get(props.projectId),
      // GET /api/agent-jobs/?project_id=projectId
      api.agentJobs.list(props.projectId),
      // GET /api/v1/products/{productId}/memory-entries?project_id=projectId&limit=20
      props.productId
        ? api.products.getMemoryEntries(props.productId, { project_id: props.projectId, limit: 20 })
        : Promise.resolve({ data: { entries: [] } }),
    ])
    projectData.value = projectRes.data
    // JobListResponse shape: { jobs: [...], total, limit, offset }
    agents.value = jobsRes.data?.jobs || []
    // MemoryEntriesResponse shape: { success, entries: [...], total_count, filtered_count }
    memoryEntries.value = memoryRes.data?.entries || []
  } catch (err) {
    console.error('[ProjectReviewModal] Failed to load:', err)
    error.value = err.response?.data?.message || err.message || 'Failed to load project data'
  } finally {
    loading.value = false
  }
}

async function loadAgentMessages(agent) {
  const jobId = agent.id
  if (agentMessages[jobId]) return
  agentMessages[jobId] = { loading: true, messages: [] }
  try {
    // GET /api/agent-jobs/{jobId}/messages
    // Response shape: { job_id, agent_id, messages: [...] }
    // Each message: { id, from, content, created_at, direction, message_type, ... }
    const res = await api.agentJobs.messages(jobId)
    agentMessages[jobId] = { loading: false, messages: (res.data?.messages || []).slice(0, 20) }
  } catch {
    agentMessages[jobId] = { loading: false, messages: [] }
  }
}

function resetState() {
  projectData.value = null
  agents.value = []
  memoryEntries.value = []
  Object.keys(agentMessages).forEach((k) => delete agentMessages[k])
  error.value = null
}

const missionText = computed(() => {
  const m = projectData.value?.mission
  if (!m) return ''
  if (typeof m === 'string') return m
  return m.mission_statement || m.objective || JSON.stringify(m, null, 2)
})

const statusColor = computed(() => {
  const s = projectData.value?.status
  if (s === 'completed') return 'success'
  if (s === 'terminated') return 'warning'
  if (s === 'cancelled') return 'grey'
  return 'primary'
})

function agentStatusColor(status) {
  if (status === 'complete' || status === 'completed') return 'success'
  if (status === 'decommissioned') return 'grey'
  if (status === 'working') return 'primary'
  if (status === 'waiting') return 'info'
  return 'default'
}

function formatDate(ts) {
  if (!ts) return 'Unknown'
  try {
    return new Date(ts).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch { return ts }
}

function truncate(text, maxLen) {
  if (!text) return ''
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
}
</script>
