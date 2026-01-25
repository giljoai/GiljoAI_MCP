<!--
  DEPRECATED (Handover 0461d): This component is no longer used.
  Simple handover uses direct API call instead of timeline visualization.
  Will be removed in v4.0.
-->
<template>
  <v-card class="succession-timeline" data-testid="succession-timeline">
    <v-card-title>Orchestrator Succession Timeline</v-card-title>

    <v-card-text>
      <!-- Job ID Display (shared across all executions) -->
      <div v-if="instances.length > 0" class="mb-4">
        <v-chip size="small" variant="outlined" prepend-icon="mdi-briefcase">
          Job: <code class="ml-1" data-testid="job-id">{{ instances[0].job_id }}</code>
        </v-chip>
      </div>

      <v-timeline side="end">
        <v-timeline-item
          v-for="(instance, index) in instances"
          :key="instance.agent_id"
          data-testid="execution-node"
          :data-agent-id="instance.agent_id"
          :data-job-id="instance.job_id"
          :dot-color="getStatusColor(instance)"
          :icon="index === instances.length - 1 ? 'mdi-account-circle' : 'mdi-check'"
          size="small"
        >
          <template #opposite>
            <div class="text-caption">Instance {{ instance.instance_number }}</div>
          </template>

          <v-card variant="outlined">
            <v-card-title class="text-subtitle-2">
              <v-chip :color="getStatusColor(instance)" size="small" class="mr-2">
                {{ instance.status }}
              </v-chip>
              {{ instance.agent_display_name || 'Agent' }}
              <div class="text-caption text-medium-emphasis mt-1">
                Agent ID: <code data-testid="agent-id">{{ instance.agent_id }}</code>
              </div>
            </v-card-title>

            <v-card-text>
              <div class="text-body-2">
                <strong>Created:</strong> {{ formatDate(instance.created_at) }}
              </div>

              <div v-if="instance.context_used" class="mt-2">
                <div class="text-caption">Context Usage</div>
                <v-progress-linear
                  :model-value="getContextPercentage(instance)"
                  :color="getContextColor(instance)"
                  height="20"
                  class="mt-1"
                >
                  <template #default="{ value }"> {{ Math.round(value) }}% </template>
                </v-progress-linear>
                <div class="text-caption mt-1">
                  {{ formatNumber(instance.context_used) }} /
                  {{ formatNumber(instance.context_budget) }} tokens
                </div>
              </div>

              <div v-if="instance.succession_reason" class="mt-2">
                <v-chip size="small" variant="tonal">
                  Succession: {{ instance.succession_reason }}
                </v-chip>
              </div>

              <div v-if="instance.handover_summary" class="mt-2">
                <v-expansion-panels variant="accordion">
                  <v-expansion-panel>
                    <v-expansion-panel-title> Handover Summary </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <pre class="text-caption">{{ instance.handover_summary }}</pre>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </div>
            </v-card-text>

            <v-card-actions v-if="instance.handover_to">
              <v-btn size="small" variant="text" @click="scrollToInstance(instance.handover_to)">
                View Successor
                <v-icon end>mdi-arrow-right</v-icon>
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-timeline-item>
      </v-timeline>

      <v-alert v-if="instances.length === 0" type="info"> No succession history yet. </v-alert>
    </v-card-text>
  </v-card>
</template>

<script>
import { ref, onMounted } from 'vue'
import { format } from 'date-fns'
import api from '@/services/api'

/**
 * SuccessionTimeline.vue - Handover 0366d-3 (updated from 0509)
 * Displays agent execution chain for a single job.
 *
 * Props:
 * - jobId: str (REQUIRED) - Job UUID to fetch execution history
 *
 * Fetches all executions for job via api.agentExecutions.list(jobId)
 * Each execution shows: agent_id, instance_number, status, context usage, handover reason
 */
export default {
  name: 'SuccessionTimeline',

  props: {
    jobId: {
      type: String,
      required: true,
      validator: (val) => /^[a-f0-9-]{36}$/.test(val), // UUID format
    },
  },

  setup(props) {
    const instances = ref([])
    const loading = ref(false)

    // fetchSuccessionHistory() - Loads agent executions from agentExecutions.list API
    // Fetches all executions for a single job, sorts by instance_number ascending
    // Returns: void (updates instances ref)
    const fetchSuccessionHistory = async () => {
      loading.value = true
      try {
        const response = await api.agentExecutions.list(props.jobId)

        // Sort by instance_number ascending
        instances.value = response.data
          .sort((a, b) => (a.instance_number || 1) - (b.instance_number || 1))
      } catch (error) {
        console.error('Failed to load succession history:', error)
      } finally {
        loading.value = false
      }
    }

    // getStatusColor(instance) - Maps job status to Vuetify color
    // Returns: str - Vuetify color name
    const getStatusColor = (instance) => {
      const statusColors = {
        pending: 'grey',
        waiting: 'grey',
        active: 'success',
        working: 'primary',
        completed: 'success',
        complete: 'success',
        failed: 'error',
      }
      return statusColors[instance.status] || 'grey'
    }

    // getContextPercentage(instance) - Calculates context usage %
    // Args: instance with context_used, context_budget
    // Returns: num - Percentage (0-100)
    const getContextPercentage = (instance) => {
      if (!instance.context_budget || !instance.context_used) return 0
      return (instance.context_used / instance.context_budget) * 100
    }

    // getContextColor(instance) - Color codes context usage (green/warning/error)
    // Returns: str - Vuetify color based on thresholds (90%+ red, 70%+ warning)
    const getContextColor = (instance) => {
      const pct = getContextPercentage(instance)
      if (pct >= 90) return 'error'
      if (pct >= 70) return 'warning'
      return 'success'
    }

    // formatDate(dateString) - Formats ISO timestamp for display
    // Returns: str - "MMM d, yyyy HH:mm" format
    const formatDate = (dateString) => {
      return format(new Date(dateString), 'MMM d, yyyy HH:mm')
    }

    // formatNumber(num) - Adds thousands separators to token counts
    // Returns: str - Localized number format
    const formatNumber = (num) => {
      return num ? num.toLocaleString() : 0
    }

    // scrollToInstance(instanceId) - Scrolls to successor instance in timeline
    // Args: instanceId - UUID of target instance
    // Returns: void (triggers smooth scroll)
    const scrollToInstance = (instanceId) => {
      const element = document.querySelector(`[data-instance-id="${instanceId}"]`)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' })
      }
    }

    onMounted(() => {
      fetchSuccessionHistory()
    })

    return {
      instances,
      loading,
      getStatusColor,
      getContextPercentage,
      getContextColor,
      formatDate,
      formatNumber,
      scrollToInstance,
    }
  },
}
</script>

<style scoped>
.succession-timeline {
  max-height: 600px;
  overflow-y: auto;
}

pre {
  white-space: pre-wrap;
  word-wrap: break-word;
}

code {
  font-family: 'Roboto Mono', monospace;
  font-size: 0.85rem;
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 4px;
  border-radius: 2px;
}
</style>
