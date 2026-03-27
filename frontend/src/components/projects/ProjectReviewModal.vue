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
          <div>
            <div class="d-flex align-center">
              <v-icon icon="mdi-eye" size="large" class="mr-2" />
              <span class="text-h6">Project Review: {{ projectData?.name }}</span>
            </div>
            <div class="d-flex align-center mt-1 ml-9">
              <v-tooltip location="bottom">
                <template #activator="{ props: tp }">
                  <code
                    v-bind="tp"
                    class="review-project-id"
                    role="button"
                    tabindex="0"
                    @click="copyProjectId"
                    @keydown.enter="copyProjectId"
                  >{{ projectId }}</code>
                </template>
                <span>{{ copied ? 'Copied!' : 'Click to copy project ID' }}</span>
              </v-tooltip>
            </div>
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
          <div class="mb-6">
            <h3 class="text-h6 mb-2">Mission</h3>
            <v-card variant="outlined" class="pa-3">
              <pre v-if="missionText" class="text-body-2" style="white-space: pre-wrap;">{{ missionText }}</pre>
              <p v-else class="text-caption text-medium-emphasis">No data</p>
            </v-card>
          </div>

          <!-- Section 3: Agent Roster -->
          <div class="mb-6">
            <h3 class="text-h6 mb-2">Agents ({{ agents.length }})</h3>
            <p v-if="!agents.length" class="text-caption text-medium-emphasis">No data</p>
            <v-table v-else density="compact">
              <thead>
                <tr>
                  <th>Agent</th>
                  <th>Type</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="agent in agents" :key="agent.id">
                  <td>{{ agent.agent_display_name }}</td>
                  <td>{{ agent.agent_name || '-' }}</td>
                  <td><v-chip :color="agentStatusColor(agent.status)" size="x-small" variant="flat">{{ agent.status }}</v-chip></td>
                </tr>
              </tbody>
            </v-table>
          </div>

          <!-- Section 4: Agent Details (expandable, lazy-loaded messages) -->
          <div v-if="agents.length" class="mb-6">

            <h3 class="text-h6 mb-2">Agent Details</h3>
            <v-expansion-panels v-model="expandedAgentPanels" variant="accordion">
              <v-expansion-panel
                v-for="(agent, idx) in agents"
                :key="agent.id"
                :value="idx"
              >
                <v-expansion-panel-title>
                  <div class="d-flex align-center w-100">
                    <span class="font-weight-medium">{{ agent.agent_display_name }}</span>
                    <v-spacer />
                    <v-chip :color="agentStatusColor(agent.status)" size="x-small" variant="flat" class="mr-2">{{ agent.status }}</v-chip>
                  </div>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-progress-linear v-if="agentMessages[agent.id]?.loading" indeterminate />
                  <v-alert v-else-if="agentMessages[agent.id]?.error" type="warning" density="compact" variant="tonal" class="mb-2">
                    Failed to load messages
                  </v-alert>
                  <div v-else-if="agentMessages[agent.id]?.messages?.length">
                    <div v-for="msg in agentMessages[agent.id].messages" :key="msg.id" class="mb-2 pa-2 rounded" style="background: rgba(var(--v-theme-on-surface), 0.03);">
                      <div class="d-flex justify-space-between align-center">
                        <div class="d-flex align-center">
                          <span class="text-caption font-weight-bold">{{ msg.from }}</span>
                          <v-chip v-if="msg.direction" size="x-small" :color="msg.direction === 'outbound' ? 'primary' : 'default'" class="ml-2">{{ msg.direction }}</v-chip>
                        </div>
                        <span class="text-caption text-medium-emphasis">{{ formatDate(msg.created_at) }}</span>
                      </div>
                      <p class="text-body-2 mt-1">{{ truncate(msg.content, 300) }}</p>
                    </div>
                  </div>
                  <p v-else class="text-caption text-medium-emphasis">No messages recorded.</p>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>

          <!-- Section 5: 360 Memory -->
          <div class="mb-6">
            <h3 class="text-h6 mb-2">360 Memory ({{ memoryEntries.length }} entries)</h3>
            <p v-if="!memoryEntries.length" class="text-caption text-medium-emphasis">No data</p>
            <v-expansion-panels v-else variant="accordion">
              <v-expansion-panel v-for="(entry, i) in memoryEntries" :key="i" :value="i">
                <v-expansion-panel-title>
                  <div class="d-flex align-center w-100">
                    <v-icon icon="mdi-book-open-page-variant" class="mr-2" size="small" />
                    <span class="font-weight-medium">
                      #{{ entry.sequence ?? i + 1 }} - {{ entry.project_name || 'Memory Entry' }}
                    </span>
                    <v-spacer />
                    <span v-if="entry.timestamp" class="text-caption text-medium-emphasis">{{ formatDate(entry.timestamp) }}</span>
                  </div>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <div v-if="entry.summary" class="mb-3">
                    <h4 class="text-subtitle-2 font-weight-bold mb-1">Summary</h4>
                    <div class="text-body-2">{{ entry.summary }}</div>
                  </div>
                  <div v-if="entry.key_outcomes && entry.key_outcomes.length" class="mb-3">
                    <h4 class="text-subtitle-2 font-weight-bold mb-1">Key Outcomes</h4>
                    <v-list density="compact">
                      <v-list-item v-for="(outcome, oi) in entry.key_outcomes" :key="oi" class="px-0">
                        <template #prepend>
                          <v-icon icon="mdi-check-circle" color="success" size="small" class="mr-2" />
                        </template>
                        <v-list-item-title class="text-body-2">{{ outcome }}</v-list-item-title>
                      </v-list-item>
                    </v-list>
                  </div>
                  <div v-if="entry.decisions_made && entry.decisions_made.length" class="mb-3">
                    <h4 class="text-subtitle-2 font-weight-bold mb-1">Decisions Made</h4>
                    <v-list density="compact">
                      <v-list-item v-for="(decision, di) in entry.decisions_made" :key="di" class="px-0">
                        <template #prepend>
                          <v-icon icon="mdi-lightbulb" color="warning" size="small" class="mr-2" />
                        </template>
                        <v-list-item-title class="text-body-2">{{ decision }}</v-list-item-title>
                      </v-list-item>
                    </v-list>
                  </div>
                  <div v-if="!entry.summary && !entry.key_outcomes?.length && !entry.decisions_made?.length">
                    <p class="text-caption text-medium-emphasis">No detailed content available.</p>
                  </div>
                  <div v-if="entry.entry_type" class="mt-3 pt-2" style="border-top: 1px solid rgba(var(--v-theme-on-surface), 0.12);">
                    <span class="text-caption text-medium-emphasis">
                      <strong>Type:</strong> {{ entry.entry_type }}
                      <template v-if="entry.source"> | <strong>Source:</strong> {{ entry.source }}</template>
                    </span>
                  </div>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>
        </template>
      </v-card-text>

      <v-divider />

      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn variant="elevated" color="primary" aria-label="Close review modal" data-testid="review-close-btn" @click="$emit('close')">
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useDisplay } from 'vuetify'
import { useClipboard } from '@/composables/useClipboard'
import api from '@/services/api'

const props = defineProps({
  show: { type: Boolean, required: true },
  projectId: { type: String, default: null },
  productId: { type: String, default: null },
})

defineEmits(['close'])

const { mobile } = useDisplay()
const isMobile = computed(() => mobile.value)
const { copy: clipboardCopy, copied } = useClipboard()

const loading = ref(false)
const error = ref(null)
const projectData = ref(null)
const agents = ref([])
const memoryEntries = ref([])
const agentMessages = reactive({})
const expandedAgentPanels = ref([])

function copyProjectId() {
  if (props.projectId) clipboardCopy(props.projectId)
}

watch(() => props.show, (open) => {
  if (open && props.projectId) {
    loadReviewData()
  } else {
    resetState()
  }
})

// Lazy-load agent messages when expansion panel opens
watch(expandedAgentPanels, (expanded) => {
  if (expanded == null) return
  const indices = Array.isArray(expanded) ? expanded : [expanded]
  for (const idx of indices) {
    const agent = agents.value[idx]
    if (agent) loadAgentMessages(agent)
  }
})

async function loadReviewData() {
  loading.value = true
  error.value = null
  try {
    // Fetch project, jobs, and memory in parallel
    const [projectRes, jobsRes, memoryRes] = await Promise.all([
      api.projects.get(props.projectId),
      api.agentJobs.list(props.projectId),
      props.productId
        ? api.products.getMemoryEntries(props.productId, { project_id: props.projectId, limit: 20 })
        : Promise.resolve({ data: { entries: [] } }),
    ])
    projectData.value = projectRes.data
    agents.value = jobsRes.data?.jobs || []
    memoryEntries.value = memoryRes.data?.entries || []
  } catch (err) {
    console.error('[ProjectReviewModal] Failed to load:', err)
    error.value = err.response?.data?.message || err.message || 'Failed to load project data'
  } finally {
    loading.value = false
  }
}

async function loadAgentMessages(agent) {
  const key = agent.id
  if (agentMessages[key]) return
  if (!agent.job_id) {
    agentMessages[key] = { loading: false, messages: [], error: true }
    return
  }
  agentMessages[key] = { loading: true, messages: [], error: false }
  try {
    const res = await api.agentJobs.messages(agent.job_id)
    agentMessages[key] = { loading: false, messages: (res.data?.messages || []).slice(0, 20), error: false }
  } catch (err) {
    console.error(`[ProjectReviewModal] Failed to load messages for job ${agent.job_id}:`, err)
    agentMessages[key] = { loading: false, messages: [], error: true }
  }
}

function resetState() {
  projectData.value = null
  agents.value = []
  memoryEntries.value = []
  Object.keys(agentMessages).forEach((k) => delete agentMessages[k])
  expandedAgentPanels.value = []
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
  return text.length > maxLen ? `${text.slice(0, maxLen)}...` : text
}
</script>

<style scoped>
.review-project-id {
  font-family: monospace;
  font-size: 0.75rem;
  opacity: 0.7;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.15);
  user-select: all;
  transition: opacity 0.15s ease;
}
.review-project-id:hover,
.review-project-id:focus-visible {
  opacity: 1;
  background: rgba(255, 255, 255, 0.25);
}
</style>
