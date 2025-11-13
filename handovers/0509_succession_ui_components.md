---
**Document Type:** Handover
**Handover ID:** 0509
**Title:** Succession UI Components - Timeline & Launch Dialog
**Version:** 1.0
**Created:** 2025-11-12
**Status:** Ready for Execution
**Duration:** 4-6 hours
**Scope:** Create SuccessionTimeline.vue and LaunchSuccessorDialog.vue components
**Priority:** 🔴 P0 CRITICAL
**Tool:** ☁️ CCW
**Parallel Execution:** ✅ Yes (Group 2 - Frontend)
**Parent Project:** Projectplan_500.md
---

# Handover 0509: Succession UI Components - Timeline & Launch Dialog

## 🎯 Mission Statement
Create production-grade Vue components for orchestrator succession: SuccessionTimeline.vue for lineage visualization and LaunchSuccessorDialog.vue for launching successor instances with thin-client prompts.

## 📋 Prerequisites
- ✅ Handover 0505 complete (succession endpoint works)
- ✅ Handover 0507 complete (API client updated)
- ✅ CLAUDE.md lines 304-306 describe required components

## ⚠️ Problem Statement

### Issue 1: SuccessionTimeline.vue MISSING
**Evidence**: Projectplan_500.md line 55, CLAUDE.md line 304
- Component referenced but doesn't exist
- Should show instance chain (1 → 2 → 3)
- **Impact**: Users can't visualize succession lineage

### Issue 2: LaunchSuccessorDialog.vue MISSING
**Evidence**: Projectplan_500.md line 56, CLAUDE.md line 305
- Component referenced but doesn't exist
- Should generate thin-client launch prompt
- **Impact**: Manual succession trigger has no UI

## ✅ Solution Approach

### Component Architecture
```
Projects Page
  └── AgentCardEnhanced.vue
        ├── "Hand Over" button → LaunchSuccessorDialog
        └── SuccessionTimeline (shows instance chain)
```

### Design Pattern
Follow existing Vue 3 + Vuetify patterns from AgentCardEnhanced.vue

## 📝 Implementation Tasks

### Task 1: Create SuccessionTimeline.vue (2-3 hours)
**File**: `frontend/src/components/projects/SuccessionTimeline.vue` (NEW)

```vue
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
            <div class="text-caption">
              Instance {{ instance.instance_number }}
            </div>
          </template>

          <v-card variant="outlined">
            <v-card-title class="text-subtitle-2">
              <v-chip
                :color="getStatusColor(instance)"
                size="small"
                class="mr-2"
              >
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
                  <template #default="{ value }">
                    {{ Math.round(value) }}%
                  </template>
                </v-progress-linear>
                <div class="text-caption mt-1">
                  {{ formatNumber(instance.context_used) }} / {{ formatNumber(instance.context_budget) }} tokens
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
                    <v-expansion-panel-title>
                      Handover Summary
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <pre class="text-caption">{{ instance.handover_summary }}</pre>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </div>
            </v-card-text>

            <v-card-actions v-if="instance.handover_to">
              <v-btn
                size="small"
                variant="text"
                @click="scrollToInstance(instance.handover_to)"
              >
                View Successor
                <v-icon end>mdi-arrow-right</v-icon>
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-timeline-item>
      </v-timeline>

      <v-alert v-if="instances.length === 0" type="info">
        No succession history yet.
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { format } from 'date-fns'
import api from '@/services/api'

export default {
  name: 'SuccessionTimeline',

  props: {
    projectId: {
      type: String,
      required: true
    }
  },

  setup(props) {
    const instances = ref([])
    const loading = ref(false)

    const fetchSuccessionHistory = async () => {
      loading.value = true
      try {
        const response = await api.agentJobs.list({
          project_id: props.projectId,
          agent_type: 'orchestrator'
        })

        // Sort by instance_number
        instances.value = response.data.sort((a, b) =>
          (a.instance_number || 1) - (b.instance_number || 1)
        )
      } catch (error) {
        console.error('Failed to load succession history:', error)
      } finally {
        loading.value = false
      }
    }

    const getStatusColor = (instance) => {
      const statusColors = {
        pending: 'grey',
        active: 'success',
        working: 'primary',
        completed: 'success',
        failed: 'error'
      }
      return statusColors[instance.status] || 'grey'
    }

    const getContextPercentage = (instance) => {
      if (!instance.context_budget || !instance.context_used) return 0
      return (instance.context_used / instance.context_budget) * 100
    }

    const getContextColor = (instance) => {
      const pct = getContextPercentage(instance)
      if (pct >= 90) return 'error'
      if (pct >= 70) return 'warning'
      return 'success'
    }

    const formatDate = (dateString) => {
      return format(new Date(dateString), 'MMM d, yyyy HH:mm')
    }

    const formatNumber = (num) => {
      return num ? num.toLocaleString() : 0
    }

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
      scrollToInstance
    }
  }
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
```

### Task 2: Create LaunchSuccessorDialog.vue (2-3 hours)
**File**: `frontend/src/components/projects/LaunchSuccessorDialog.vue` (NEW)

```vue
<template>
  <v-dialog v-model="dialog" max-width="800">
    <template #activator="{ props }">
      <slot name="activator" :props="props">
        <v-btn v-bind="props" color="primary">
          Launch Successor
        </v-btn>
      </slot>
    </template>

    <v-card>
      <v-card-title>
        Launch Successor Orchestrator
        <v-chip class="ml-2" size="small">
          Instance {{ nextInstanceNumber }}
        </v-chip>
      </v-card-title>

      <v-card-text>
        <v-alert type="info" class="mb-4">
          This will create a new orchestrator instance ({{ nextInstanceNumber }}) to continue the mission with a fresh context window.
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
              <div><strong>Instance:</strong> {{ currentJob.instance_number || 1 }}</div>
              <div><strong>Status:</strong> {{ currentJob.status }}</div>
              <div v-if="currentJob.context_used">
                <strong>Context Usage:</strong>
                {{ formatNumber(currentJob.context_used) }} / {{ formatNumber(currentJob.context_budget) }} tokens
                ({{ Math.round(contextPercentage) }}%)
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
            <v-btn
              icon="mdi-content-copy"
              size="small"
              variant="text"
              @click="copyPrompt"
            />
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
        <v-btn
          color="primary"
          :loading="loading"
          @click="triggerSuccession"
        >
          Trigger Succession
        </v-btn>
        <v-btn
          v-if="launchPrompt"
          color="success"
          @click="copyAndClose"
        >
          Copy Prompt & Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, computed } from 'vue'
import { useToast } from '@/composables/useToast'
import api from '@/services/api'

export default {
  name: 'LaunchSuccessorDialog',

  props: {
    jobId: {
      type: String,
      required: true
    },
    currentJob: {
      type: Object,
      required: true
    }
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

    const reasonOptions = [
      { title: 'Manual Handover', value: 'manual' },
      { title: 'Context Limit Approaching', value: 'context_limit' },
      { title: 'Phase Transition', value: 'phase_transition' }
    ]

    const nextInstanceNumber = computed(() => {
      return (props.currentJob.instance_number || 1) + 1
    })

    const contextPercentage = computed(() => {
      if (!props.currentJob.context_budget || !props.currentJob.context_used) return 0
      return (props.currentJob.context_used / props.currentJob.context_budget) * 100
    })

    const contextColor = computed(() => {
      const pct = contextPercentage.value
      if (pct >= 90) return 'error'
      if (pct >= 70) return 'warning'
      return 'success'
    })

    const formatNumber = (num) => num ? num.toLocaleString() : 0

    const triggerSuccession = async () => {
      loading.value = true
      error.value = null

      try {
        const response = await api.agentJobs.triggerSuccession(
          props.jobId,
          successionReason.value,
          notes.value
        )

        launchPrompt.value = response.data.launch_prompt

        toast.success(`Successor instance ${response.data.instance_number} created`)
        emit('succession-triggered', response.data)

      } catch (err) {
        console.error('Succession trigger failed:', err)
        error.value = err.response?.data?.detail || 'Failed to trigger succession'
        toast.error(error.value)
      } finally {
        loading.value = false
      }
    }

    const copyPrompt = async () => {
      try {
        await navigator.clipboard.writeText(launchPrompt.value)
        toast.success('Launch prompt copied to clipboard')
      } catch (err) {
        toast.error('Failed to copy prompt')
      }
    }

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
      contextPercentage,
      contextColor,
      formatNumber,
      triggerSuccession,
      copyPrompt,
      copyAndClose
    }
  }
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
</style>
```

### Task 3: Integrate into AgentCardEnhanced.vue (30 min)
**File**: `frontend/src/components/projects/AgentCardEnhanced.vue`

```vue
<template>
  <v-card>
    <!-- Existing card content -->

    <!-- Add Succession Timeline -->
    <succession-timeline
      v-if="job.agent_type === 'orchestrator'"
      :project-id="job.project_id"
      class="mt-4"
    />

    <!-- Hand Over Button -->
    <v-card-actions v-if="job.agent_type === 'orchestrator' && job.status === 'working'">
      <launch-successor-dialog
        :job-id="job.id"
        :current-job="job"
        @succession-triggered="onSuccessionTriggered"
      >
        <template #activator="{ props }">
          <v-btn v-bind="props" color="warning" variant="outlined">
            <v-icon start>mdi-handshake</v-icon>
            Hand Over
          </v-btn>
        </template>
      </launch-successor-dialog>
    </v-card-actions>
  </v-card>
</template>

<script>
import SuccessionTimeline from './SuccessionTimeline.vue'
import LaunchSuccessorDialog from './LaunchSuccessorDialog.vue'

export default {
  components: {
    SuccessionTimeline,
    LaunchSuccessorDialog
  },

  methods: {
    onSuccessionTriggered(successorData) {
      console.log('Successor created:', successorData)
      // Refresh job list or navigate to successor
      this.$emit('refresh-jobs')
    }
  }
}
</script>
```

## ✅ Success Criteria
- [ ] SuccessionTimeline.vue displays instance chain
- [ ] Timeline shows context usage bars
- [ ] Timeline shows succession reasons
- [ ] LaunchSuccessorDialog opens from "Hand Over" button
- [ ] Dialog shows current context usage
- [ ] Dialog allows selecting succession reason
- [ ] Succession trigger creates successor job
- [ ] Launch prompt generated and copyable
- [ ] Toast notifications on success/failure
- [ ] Components integrate with AgentCardEnhanced

## 🔄 Rollback Plan
1. `git rm frontend/src/components/projects/SuccessionTimeline.vue`
2. `git rm frontend/src/components/projects/LaunchSuccessorDialog.vue`
3. `git checkout HEAD~1 -- frontend/src/components/projects/AgentCardEnhanced.vue`

## 📚 Related Handovers
**Depends on**: 0505 (Succession Endpoint), 0507 (API Client)
**Parallel with**: 0507, 0508

## 🛠️ Tool Justification
**Why CCW**: Pure Vue component development, no backend changes

## 📊 Parallel Execution
**✅ CAN RUN IN PARALLEL** (Group 2 - Frontend)

---
**Status:** Ready for Execution
**Estimated Effort:** 4-6 hours
**Archive Location:** `handovers/completed/0509_succession_ui_components-COMPLETE.md`
