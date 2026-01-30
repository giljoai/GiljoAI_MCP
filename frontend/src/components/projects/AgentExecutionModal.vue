<template>
  <v-dialog v-model="isOpen" max-width="700" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-robot-outline</v-icon>
        <span>Agent Execution Details</span>
        <v-spacer></v-spacer>
        <v-btn icon variant="text" @click="close" aria-label="Close">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-divider></v-divider>
      <v-card-text v-if="execution">
        <!-- Agent Info Section -->
        <div class="agent-info-section mb-4">
          <h4 class="text-subtitle-1 font-weight-bold mb-2">Execution Info</h4>
          <v-row dense>
            <v-col cols="6">
              <div class="info-item">
                <span class="info-label">Agent ID:</span>
                <code class="info-value" data-testid="modal-agent-id">{{ execution.agent_id }}</code>
              </div>
            </v-col>
            <v-col cols="6">
              <div class="info-item">
                <span class="info-label">Job ID:</span>
                <code class="info-value" data-testid="modal-job-id">{{ execution.job_id }}</code>
              </div>
            </v-col>
            <v-col cols="6">
              <div class="info-item">
                <span class="info-label">Instance Number:</span>
                <v-chip size="small" color="blue-grey" label data-testid="modal-instance">
                  #{{ execution.instance_number || 1 }}
                </v-chip>
              </div>
            </v-col>
            <v-col cols="6">
              <div class="info-item">
                <span class="info-label">Status:</span>
                <span data-testid="modal-status">{{ execution.status }}</span>
              </div>
            </v-col>
          </v-row>
        </div>

        <!-- Mission Section (from job, not execution) -->
        <div class="mission-section" v-if="job">
          <h4 class="text-subtitle-1 font-weight-bold mb-2">Mission</h4>
          <v-card variant="outlined" class="pa-3">
            <pre class="mission-text" data-testid="modal-mission">{{ job.mission || 'No mission assigned.' }}</pre>
          </v-card>
        </div>

        <!-- Progress Section -->
        <div class="progress-section mt-4" v-if="execution.progress">
          <h4 class="text-subtitle-1 font-weight-bold mb-2">Progress</h4>
          <v-card variant="outlined" class="pa-3">
            <pre class="progress-text">{{ execution.progress }}</pre>
          </v-card>
        </div>
      </v-card-text>
      <v-card-text v-else class="text-center py-4 text-medium-emphasis">
        No execution selected
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn color="primary" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
// Handover 0396: Fixed import - api is default export, not named export
import api from '@/services/api'

/**
 * AgentExecutionModal Component - Handover 0366d-1
 *
 * Displays agent execution details including:
 * - agent_id (execution instance UUID)
 * - job_id (foreign key to AgentJob)
 * - instance_number (human-readable instance tracking)
 * - status
 * - mission (fetched from job)
 * - progress (if available)
 */

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  execution: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue'])

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const job = ref(null)

// Fetch job details when execution changes
watch(() => props.execution, async (newExecution) => {
  if (newExecution?.job_id) {
    try {
      // Handover 0396: Use structured api.agentJobs.get() method
      const response = await api.agentJobs.get(newExecution.job_id)
      job.value = response.data
    } catch (error) {
      console.error('[AgentExecutionModal] Failed to fetch job:', error)
      job.value = null
    }
  } else {
    job.value = null
  }
}, { immediate: true })

function close() {
  isOpen.value = false
}
</script>

<style scoped>
.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.6);
  font-weight: 500;
}

.info-value {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  background: rgba(255, 255, 255, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
  word-break: break-all;
}

.mission-text,
.progress-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Roboto Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.9);
  margin: 0;
  max-height: 300px;
  overflow-y: auto;
}
</style>
