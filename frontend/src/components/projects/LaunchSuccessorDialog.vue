<template>
  <v-dialog v-model="dialog" max-width="800">
    <template #activator="{ props: activatorProps }">
      <slot name="activator" :props="activatorProps">
        <v-btn v-bind="activatorProps" color="primary"> Launch Successor </v-btn>
      </slot>
    </template>

    <v-card>
      <v-card-title>
        Launch Successor Orchestrator
        <v-chip class="ml-2" size="small" color="primary">
          Instance {{ nextInstanceNumber }}
        </v-chip>
      </v-card-title>

      <v-card-text>
        <!-- Warning: Existing waiting successors -->
        <v-alert v-if="waitingSuccessors.length > 0" type="error" variant="tonal" class="mb-4" density="compact">
          <template #prepend>
            <v-icon>mdi-alert-circle</v-icon>
          </template>
          <strong>Warning:</strong> There are already {{ waitingSuccessors.length }} waiting successor(s):
          <span v-for="(s, i) in waitingSuccessors" :key="s.instance_number">
            Instance #{{ s.instance_number }}<span v-if="i < waitingSuccessors.length - 1">, </span>
          </span>.
          Consider launching one of those instead of creating another.
        </v-alert>

        <v-alert type="warning" variant="tonal" class="mb-4" density="compact">
          <template #prepend>
            <v-icon>mdi-alert</v-icon>
          </template>
          Ensure all agents have completed their work before proceeding. Messages sent to
          this orchestrator will be received by the successor.
        </v-alert>

        <v-alert type="info" class="mb-4" variant="tonal">
          <div class="text-subtitle-2 mb-2">Creating New Agent Execution</div>
          <ul class="text-body-2 pl-4">
            <li>✓ Same job_id ({{ currentJob.job_id?.slice(0, 8) }}...)</li>
            <li>✓ New agent_id (fresh execution)</li>
            <li>✓ Instance #{{ nextInstanceNumber }} in succession chain</li>
            <li>✓ Fresh context window (resets to 0 tokens)</li>
          </ul>
        </v-alert>

        <!-- Succession Reason -->
        <v-select
          v-model="successionReason"
          :items="reasonOptions"
          label="Succession Reason"
          variant="outlined"
        />

        <!-- Notes (Optional) -->
        <v-textarea
          v-model="notes"
          label="Notes (optional)"
          placeholder="Why are you triggering succession manually?"
          variant="outlined"
          rows="3"
        />

        <!-- Context Summary -->
        <v-card v-if="currentJob" variant="outlined" class="mb-4">
          <v-card-subtitle>Current Instance Summary</v-card-subtitle>
          <v-card-text>
            <div class="text-body-2">
              <div><strong>Job ID:</strong> <code data-testid="current-job-id">{{ currentJob.job_id }}</code></div>
              <div><strong>Agent ID:</strong> <code data-testid="current-agent-id">{{ currentJob.agent_id }}</code></div>
              <div><strong>Instance:</strong> {{ currentJob.instance_number || 1 }}</div>
              <div><strong>Status:</strong> {{ currentJob.status }}</div>
              <div v-if="currentJob.context_used">
                <strong>Context Usage:</strong>
                {{ formatNumber(currentJob.context_used) }} /
                {{ formatNumber(currentJob.context_budget) }} tokens ({{
                  Math.round(contextPercentage)
                }}%)
              </div>
            </div>

            <v-progress-linear
              v-if="currentJob.context_used"
              :model-value="contextPercentage"
              :color="contextColor"
              class="mt-2"
            />
          </v-card-text>
        </v-card>

        <!-- Generated Launch Prompt -->
        <v-card v-if="launchPrompt" variant="tonal" class="mt-4">
          <v-card-subtitle>
            Thin-Client Launch Prompt
            <v-btn icon="mdi-content-copy" size="small" variant="text" @click="copyPrompt" />
          </v-card-subtitle>
          <v-card-text>
            <pre class="launch-prompt">{{ launchPrompt }}</pre>
          </v-card-text>
        </v-card>

        <v-alert v-if="error" type="error" class="mt-4">
          {{ error }}
        </v-alert>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="dialog = false">Cancel</v-btn>
        <v-btn color="primary" :loading="loading" @click="triggerSuccession">
          Trigger Succession
        </v-btn>
        <v-btn v-if="launchPrompt" color="success" @click="copyAndClose">
          Copy Prompt & Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { useToast } from '@/composables/useToast'
import api from '@/services/api'

/**
 * LaunchSuccessorDialog.vue - Handover 0509
 * Dialog for manually triggering orchestrator succession
 *
 * Props:
 * - jobId: str - Current orchestrator job UUID
 * - currentJob: obj - Current job data with context usage
 *
 * Emits:
 * - succession-triggered: {successor_job_id, instance_number, launch_prompt}
 *
 * Calls api.agentJobs.triggerSuccession(jobId, reason, notes)
 * Displays thin-client launch prompt for copy/paste
 */
export default {
  name: 'LaunchSuccessorDialog',

  props: {
    jobId: {
      type: String,
      required: true,
    },
    currentJob: {
      type: Object,
      required: true,
    },
  },

  emits: ['succession-triggered'],

  setup(props, { emit }) {
    const toast = useToast()
    const dialog = ref(false)
    const loading = ref(false)
    const successionReason = ref('manual')
    const notes = ref('')
    const launchPrompt = ref('')
    const error = ref(null)
    const allExecutions = ref([])  // All executions for this job

    const reasonOptions = [
      { title: 'Manual Handover', value: 'manual' },
      { title: 'Context Limit Approaching', value: 'context_limit' },
      { title: 'Phase Transition', value: 'phase_transition' },
    ]

    // Fetch all executions when dialog opens
    watch(dialog, async (isOpen) => {
      if (isOpen && props.currentJob?.job_id) {
        try {
          const response = await api.agentJobs.getExecutions(props.currentJob.job_id)
          allExecutions.value = response.data || []
        } catch (err) {
          console.warn('Could not fetch executions:', err)
          allExecutions.value = []
        }
      }
    })

    // waitingSuccessors - Executions in "waiting" status (excluding current)
    const waitingSuccessors = computed(() => {
      return allExecutions.value
        .filter(e => e.status === 'waiting' && e.instance_number !== props.currentJob.instance_number)
        .sort((a, b) => a.instance_number - b.instance_number)
    })

    // maxInstanceNumber - Highest instance number across all executions
    const maxInstanceNumber = computed(() => {
      if (allExecutions.value.length === 0) {
        return props.currentJob.instance_number || 1
      }
      return Math.max(...allExecutions.value.map(e => e.instance_number || 1))
    })

    // nextInstanceNumber - Computed next instance number (max + 1)
    const nextInstanceNumber = computed(() => {
      return maxInstanceNumber.value + 1
    })

    // contextPercentage - Calculates current context usage %
    // Returns: num - Percentage (0-100)
    const contextPercentage = computed(() => {
      if (!props.currentJob.context_budget || !props.currentJob.context_used) return 0
      return (props.currentJob.context_used / props.currentJob.context_budget) * 100
    })

    // contextColor - Color codes context usage
    // Returns: str - Vuetify color (success/warning/error)
    const contextColor = computed(() => {
      const pct = contextPercentage.value
      if (pct >= 90) return 'error'
      if (pct >= 70) return 'warning'
      return 'success'
    })

    // formatNumber(num) - Formats numbers with thousands separators
    // Returns: str - Localized number
    const formatNumber = (num) => (num ? num.toLocaleString() : 0)

    // triggerSuccession() - Calls backend API to create successor instance
    // Updates launchPrompt ref with generated thin-client prompt
    // Emits: succession-triggered event with successor data
    // Raises: HTTPException 400/500 from backend
    const triggerSuccession = async () => {
      loading.value = true
      error.value = null

      try {
        const response = await api.agentJobs.triggerSuccession(
          props.jobId,
          successionReason.value,
          notes.value,
        )

        launchPrompt.value = response.data.launch_prompt

        toast.showToast({
          type: 'success',
          message: `Successor instance ${response.data.instance_number} created`,
        })
        emit('succession-triggered', response.data)
      } catch (err) {
        console.error('Succession trigger failed:', err)
        error.value = err.response?.data?.detail || 'Failed to trigger succession'
        toast.showToast({
          type: 'error',
          message: error.value,
        })
      } finally {
        loading.value = false
      }
    }

    // copyPrompt() - Copies launch prompt to clipboard using Navigator API
    // Shows toast notification on success/failure
    const copyPrompt = async () => {
      try {
        await navigator.clipboard.writeText(launchPrompt.value)
        toast.showToast({
          type: 'success',
          message: 'Launch prompt copied to clipboard',
        })
      } catch (err) {
        toast.showToast({
          type: 'error',
          message: 'Failed to copy prompt',
        })
      }
    }

    // copyAndClose() - Copies prompt and closes dialog
    const copyAndClose = async () => {
      await copyPrompt()
      dialog.value = false
    }

    return {
      dialog,
      loading,
      successionReason,
      notes,
      launchPrompt,
      error,
      reasonOptions,
      nextInstanceNumber,
      waitingSuccessors,  // For warning about existing waiting instances
      contextPercentage,
      contextColor,
      formatNumber,
      triggerSuccession,
      copyPrompt,
      copyAndClose,
    }
  },
}
</script>

<style scoped>
.launch-prompt {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 300px;
  overflow-y: auto;
  background: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
}

code {
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  word-break: break-all;
}

.text-body-2 ul {
  list-style: none;
  margin: 0;
}

.text-body-2 ul li {
  margin-bottom: 4px;
}
</style>
