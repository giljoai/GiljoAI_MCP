<template>
  <v-card class="succession-timeline">
    <v-card-title>Orchestrator Succession Timeline</v-card-title>

    <v-card-text>
      <v-timeline side="end">
        <v-timeline-item
          v-for="(instance, index) in instances"
          :key="instance.id"
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
              {{ instance.agent_name }}
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
 * SuccessionTimeline.vue - Handover 0509
 * Displays orchestrator instance chain with context usage and handover summaries
 *
 * Props:
 * - projectId: str - Project UUID to fetch succession history
 *
 * Fetches all orchestrator instances for project, sorted by instance_number
 */
export default {
  name: 'SuccessionTimeline',

  props: {
    projectId: {
      type: String,
      required: true,
    },
  },

  setup(props) {
    const instances = ref([])
    const loading = ref(false)

    // fetchSuccessionHistory() - Loads orchestrator instances from agentJobs.list API
    // Filters for agent_type=orchestrator, sorts by instance_number ascending
    // Returns: void (updates instances ref)
    const fetchSuccessionHistory = async () => {
      loading.value = true
      try {
        const response = await api.agentJobs.list(props.projectId)

        // Filter orchestrators and sort by instance_number
        instances.value = response.data
          .filter((job) => job.agent_type === 'orchestrator')
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
</style>
