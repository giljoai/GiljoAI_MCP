<template>
  <div class="kanban-column">
    <!-- Column Header -->
    <v-card class="column-header mb-4" elevation="1">
      <v-card-title class="d-flex align-center justify-space-between pa-4">
        <v-icon :color="iconColor" size="28">{{ icon }}</v-icon>
        <div class="flex-grow-1 text-center">
          <p class="text-h6 font-weight-bold mb-0">{{ title }}</p>
          <p class="text-caption text-grey mb-0">{{ description }}</p>
        </div>
        <v-chip
          :color="iconColor"
          text-color="white"
          size="large"
          label
        >
          {{ jobs.length }}
        </v-chip>
      </v-card-title>
    </v-card>

    <!-- Jobs Column Content -->
    <div class="column-content">
      <!-- Job Cards -->
      <job-card
        v-for="job in jobs"
        :key="job.job_id"
        :job="job"
        :column-status="status"
        @view-details="$emit('view-job-details', job)"
        @open-messages="$emit('open-messages', job)"
        class="mb-3"
      />

      <!-- Empty State -->
      <v-card
        v-if="jobs.length === 0"
        variant="outlined"
        class="d-flex align-center justify-center pa-8"
        style="min-height: 200px"
      >
        <div class="text-center">
          <v-icon
            :color="iconColor"
            opacity="0.3"
            size="48"
            class="mb-3 d-block"
          >
            {{ emptyIcon }}
          </v-icon>
          <p class="text-body-2 text-grey">
            No {{ title.toLowerCase() }} jobs
          </p>
        </div>
      </v-card>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import JobCard from './JobCard.vue'

/**
 * KanbanColumn Component
 *
 * Displays a display-only column of agent jobs with a specific status.
 * NO drag-drop functionality - agents navigate themselves via MCP tools.
 *
 * Features:
 * - Job card display with agent info, mission, and message counts
 * - Empty state when no jobs in column
 * - Column header with status icon and job count
 * - Responsive design for mobile/tablet/desktop
 *
 * Props:
 * - status: 'pending' | 'active' | 'completed' | 'blocked'
 * - jobs: Array of agent job objects
 * - title: Display title for column
 * - description: Subtitle explaining column purpose
 */

const props = defineProps({
  status: {
    type: String,
    required: true,
    validator: (value) => ['pending', 'active', 'completed', 'blocked'].includes(value),
  },
  jobs: {
    type: Array,
    default: () => [],
  },
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    default: '',
  },
})

defineEmits(['view-job-details', 'open-messages'])

/**
 * Determine icon and color based on column status
 */
const iconConfig = computed(() => {
  const configs = {
    pending: {
      icon: 'mdi-clock-outline',
      iconColor: 'grey',
      emptyIcon: 'mdi-clock-outline',
    },
    active: {
      icon: 'mdi-play-circle',
      iconColor: 'primary',
      emptyIcon: 'mdi-play-circle-outline',
    },
    completed: {
      icon: 'mdi-check-circle',
      iconColor: 'success',
      emptyIcon: 'mdi-check-circle-outline',
    },
    blocked: {
      icon: 'mdi-alert-circle',
      iconColor: 'error',
      emptyIcon: 'mdi-alert-circle-outline',
    },
  }

  return configs[props.status] || configs.pending
})

const icon = computed(() => iconConfig.value.icon)
const iconColor = computed(() => iconConfig.value.iconColor)
const emptyIcon = computed(() => iconConfig.value.emptyIcon)
</script>

<style scoped>
.kanban-column {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
}

.column-header {
  flex-shrink: 0;
  background: linear-gradient(135deg, rgba(0, 0, 0, 0.02) 0%, rgba(0, 0, 0, 0.03) 100%);
}

.column-content {
  flex: 1;
  overflow-y: auto;
  padding-right: 0.5rem;
}

/* Custom scrollbar styling */
.column-content::-webkit-scrollbar {
  width: 6px;
}

.column-content::-webkit-scrollbar-track {
  background: transparent;
}

.column-content::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 3px;
}

.column-content::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}

/* Firefox scrollbar */
.column-content {
  scrollbar-color: rgba(0, 0, 0, 0.1) transparent;
  scrollbar-width: thin;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .kanban-column {
    min-height: 300px;
  }
}
</style>
