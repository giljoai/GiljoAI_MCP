<template>
  <v-card
    variant="outlined"
    class="agent-mini-card h-100"
    :color="cardColor"
  >
    <v-card-text class="pa-3 d-flex flex-column align-center text-center h-100">
      <!-- Agent Avatar -->
      <v-avatar
        :color="agentColor"
        size="48"
        class="mb-3"
        :aria-label="`${agent.name} avatar`"
      >
        <v-icon color="white" size="28">{{ agentIcon }}</v-icon>
      </v-avatar>

      <!-- Agent Name -->
      <p class="text-subtitle-2 font-weight-bold mb-1 text-truncate w-100">
        {{ agent.name }}
      </p>

      <!-- Agent Type Badge -->
      <v-chip
        size="x-small"
        density="compact"
        :color="agentColor"
        text-color="white"
        class="mb-2"
      >
        {{ agent.type }}
      </v-chip>

      <!-- Agent Status (if available) -->
      <p v-if="agent.status" class="text-caption text-grey mt-auto">
        Status: <strong>{{ agent.status }}</strong>
      </p>

      <!-- Mission Summary (if available) -->
      <p v-if="agent.mission" class="text-caption text-grey mt-1" style="line-height: 1.4">
        <strong>Mission:</strong>
        <br />
        {{ truncateText(agent.mission, 50) }}
      </p>
    </v-card-text>

    <!-- Hover Action (Optional) -->
    <template v-if="showDetails">
      <v-divider />
      <v-card-actions class="pa-2 justify-center">
        <v-btn
          size="x-small"
          variant="text"
          color="primary"
          @click="showDetailsDialog = true"
        >
          <v-icon start size="small">mdi-information</v-icon>
          Details
        </v-btn>
      </v-card-actions>
    </template>

    <!-- Agent Details Dialog -->
    <v-dialog v-if="showDetails" v-model="showDetailsDialog" max-width="400">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-avatar :color="agentColor" size="36" class="mr-2">
            <v-icon color="white" size="20">{{ agentIcon }}</v-icon>
          </v-avatar>
          {{ agent.name }}
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-4">
          <!-- Type -->
          <div class="mb-3">
            <p class="text-caption text-grey mb-1">Agent Type</p>
            <v-chip size="small" :color="agentColor" text-color="white">
              {{ agent.type }}
            </v-chip>
          </div>

          <!-- Status -->
          <div v-if="agent.status" class="mb-3">
            <p class="text-caption text-grey mb-1">Status</p>
            <p class="text-body-2">{{ agent.status }}</p>
          </div>

          <!-- Mission -->
          <div v-if="agent.mission" class="mb-3">
            <p class="text-caption text-grey mb-1">Mission</p>
            <p class="text-body-2">{{ agent.mission }}</p>
          </div>

          <!-- Capabilities (if available) -->
          <div v-if="agent.capabilities && agent.capabilities.length > 0" class="mb-3">
            <p class="text-caption text-grey mb-1">Capabilities</p>
            <div class="d-flex flex-wrap gap-2">
              <v-chip
                v-for="capability in agent.capabilities"
                :key="capability"
                size="small"
                variant="outlined"
              >
                {{ capability }}
              </v-chip>
            </div>
          </div>

          <!-- Created At -->
          <div v-if="agent.created_at" class="mb-3">
            <p class="text-caption text-grey mb-1">Created</p>
            <p class="text-body-2">{{ formatDate(agent.created_at) }}</p>
          </div>

          <!-- Additional Info -->
          <v-alert
            type="info"
            variant="tonal"
            density="compact"
            class="mb-0"
          >
            <v-icon start size="small">mdi-information</v-icon>
            Agent will be ready for job assignment after mission acceptance.
          </v-alert>
        </v-card-text>

        <v-divider />

        <v-card-actions>
          <v-spacer />
          <v-btn @click="showDetailsDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { ref, computed } from 'vue'

/**
 * AgentMiniCard Component
 *
 * Compact card displaying agent information within the launch panel.
 * Shows agent name, type, status, and optional mission summary.
 * Optional details dialog for full agent information.
 */

const props = defineProps({
  agent: {
    type: Object,
    required: true,
    validator: (val) => {
      return val && val.id && val.name && val.type
    },
  },
  showDetails: {
    type: Boolean,
    default: true,
  },
  cardColor: {
    type: String,
    default: '',
  },
})

const showDetailsDialog = ref(false)

/**
 * Get agent color based on type
 */
const agentColor = computed(() => {
  const colors = {
    orchestrator: '#7c3aed', // Purple
    lead: '#3b82f6', // Blue
    backend: '#059669', // Green
    frontend: '#06b6d4', // Cyan
    tester: '#f97316', // Orange
    analyzer: '#ec4899', // Pink
    architect: '#8b5cf6', // Violet
    devops: '#6366f1', // Indigo
    security: '#dc2626', // Red
    ux_designer: '#f472b6', // Rose
    database: '#14b8a6', // Teal
    ai_specialist: '#a855f7', // Fuchsia
  }

  return colors[props.agent.type?.toLowerCase().replace(/\s+/g, '_')] || '#6b7280'
})

/**
 * Get agent icon based on type
 */
const agentIcon = computed(() => {
  const icons = {
    orchestrator: 'mdi-brain',
    lead: 'mdi-account-tie',
    backend: 'mdi-database',
    frontend: 'mdi-palette',
    tester: 'mdi-test-tube',
    analyzer: 'mdi-magnify',
    architect: 'mdi-blueprint',
    devops: 'mdi-server',
    security: 'mdi-shield-lock',
    ux_designer: 'mdi-palette-advanced',
    database: 'mdi-database-multiple',
    ai_specialist: 'mdi-robot',
  }

  return icons[props.agent.type?.toLowerCase().replace(/\s+/g, '_')] || 'mdi-robot'
})

/**
 * Truncate text to specified length
 */
function truncateText(text, maxLength = 50) {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

/**
 * Format date string for display
 */
function formatDate(dateString) {
  if (!dateString) return 'Unknown'

  try {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(date)
  } catch {
    return dateString
  }
}
</script>

<style scoped>
.agent-mini-card {
  transition: all 0.3s ease;
  border: 2px solid transparent;
  cursor: pointer;
}

.agent-mini-card:hover {
  border-color: currentColor;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

/* Card text truncation */
.text-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Avatar styling */
:deep(.v-avatar) {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

/* Chip styling */
:deep(.v-chip) {
  text-transform: capitalize;
  font-weight: 500;
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .agent-mini-card {
    border-width: 1px;
  }
}

/* Gap utility for flex layouts */
.gap-2 {
  gap: 0.5rem;
}

/* Accessibility */
:focus-visible {
  outline: 2px solid #2196f3;
  outline-offset: 2px;
}
</style>
