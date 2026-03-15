<template>
  <div class="status-badge-wrapper">
    <!-- Status Badge with Dropdown Menu -->
    <v-menu
      v-model="menuOpen"
      :close-on-content-click="false"
      location="bottom"
      offset="4"
      :disabled="loading"
    >
      <template v-slot:activator="{ props: menuProps }">
        <v-chip
          v-bind="menuProps"
          :color="statusColor"
          :prepend-icon="statusIcon"
          variant="flat"
          size="small"
          class="status-badge-chip"
          :class="{ 'status-badge-loading': loading }"
          :disabled="loading"
          :aria-label="`Project status: ${status}. Click to change status.`"
          role="button"
          tabindex="0"
          @keydown.enter="menuOpen = !menuOpen"
          @keydown.space.prevent="menuOpen = !menuOpen"
        >
          <span class="text-caption font-weight-medium">{{ statusLabel }}</span>
          <v-icon v-if="loading" end size="small" class="ml-1 status-spinner"> mdi-loading </v-icon>
          <v-icon v-else end size="small" class="ml-1"> mdi-chevron-down </v-icon>
        </v-chip>
      </template>

      <!-- Action Menu -->
      <v-list density="compact" class="status-menu-list">
        <v-list-item
          v-for="action in availableActions"
          :key="action.value"
          :value="action.value"
          :prepend-icon="action.icon"
          :class="{ 'text-error': action.destructive }"
          :aria-label="action.label"
          role="menuitem"
          tabindex="0"
          @click="handleActionClick(action)"
        >
          <v-list-item-title>{{ action.label }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>

    <!-- Confirmation Dialog for Destructive Actions -->
    <v-dialog
      v-model="showConfirmDialog"
      max-width="500"
      persistent
      :aria-labelledby="confirmDialogTitle"
      role="alertdialog"
    >
      <v-card v-draggable>
        <v-card-title class="d-flex align-center">
          <v-icon start :color="pendingAction?.destructive ? 'error' : 'warning'">
            {{ pendingAction?.destructive ? 'mdi-alert-circle' : 'mdi-help-circle' }}
          </v-icon>
          <span :id="confirmDialogTitle">{{ confirmDialogTitle }}</span>
        </v-card-title>

        <v-divider></v-divider>

        <v-card-text>
          <div class="text-body-1">
            {{ confirmMessage }}
          </div>
          <v-alert
            v-if="pendingAction?.destructive"
            type="warning"
            variant="tonal"
            density="compact"
            class="mt-4"
          >
            This action cannot be undone.
          </v-alert>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            variant="text"
            :disabled="loading"
            aria-label="Cancel action"
            @click="cancelConfirmation"
          >
            Cancel
          </v-btn>
          <v-btn
            :color="pendingAction?.destructive ? 'error' : 'primary'"
            variant="flat"
            :loading="loading"
            :aria-label="`Confirm ${pendingAction?.label}`"
            @click="confirmAction"
          >
            {{ pendingAction?.label }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

// Props
const props = defineProps({
  status: {
    type: String,
    required: true,
    validator: (value) =>
      ['inactive', 'active', 'completed', 'cancelled', 'terminated', 'deleted'].includes(value),
  },
  projectId: {
    type: String,
    required: true,
  },
  projectName: {
    type: String,
    default: 'this project',
  },
})

// Emits
const emit = defineEmits(['action', 'loading', 'error'])

// State
const menuOpen = ref(false)
const showConfirmDialog = ref(false)
const pendingAction = ref(null)
const loading = ref(false)

// Status Configuration
const statusConfig = {
  active: {
    label: 'Active',
    color: 'success',
    icon: 'mdi-play-circle',
  },
  inactive: {
    label: 'Inactive',
    color: 'grey',
    icon: 'mdi-stop-circle-outline',
  },
  completed: {
    label: 'Completed',
    color: 'info',
    icon: 'mdi-check-circle',
  },
  cancelled: {
    label: 'Cancelled',
    color: 'warning',
    icon: 'mdi-cancel',
  },
  terminated: {
    label: 'Terminated',
    color: 'error',
    icon: 'mdi-stop-circle',
  },
  deleted: {
    label: 'Deleted',
    color: 'error',
    icon: 'mdi-delete',
  },
}

// Action Definitions
const actionDefinitions = {
  activate: {
    value: 'activate',
    label: 'Activate',
    icon: 'mdi-play',
    newStatus: 'active',
    destructive: false,
    requiresConfirm: false,
  },
  deactivate: {
    value: 'deactivate',
    label: 'Deactivate',
    icon: 'mdi-pause-circle-outline',
    newStatus: 'inactive',
    destructive: false,
    requiresConfirm: true,
  },
  complete: {
    value: 'complete',
    label: 'Complete',
    icon: 'mdi-check-circle',
    newStatus: 'completed',
    destructive: false,
    requiresConfirm: true,
  },
  cancel: {
    value: 'cancel',
    label: 'Cancel',
    icon: 'mdi-cancel',
    newStatus: 'cancelled',
    destructive: true,
    requiresConfirm: true,
  },
  reopen: {
    value: 'reopen',
    label: 'Reopen',
    icon: 'mdi-restore',
    newStatus: 'inactive',
    destructive: false,
    requiresConfirm: false,
  },
  review: {
    value: 'review',
    label: 'Review',
    icon: 'mdi-eye',
    newStatus: null,
    destructive: false,
    requiresConfirm: false,
  },
  delete: {
    value: 'delete',
    label: 'Delete',
    icon: 'mdi-delete',
    newStatus: null,
    destructive: true,
    requiresConfirm: true,
  },
}

// Context-Aware Action Mapping
const actionsByStatus = {
  inactive: ['activate', 'complete', 'cancel'],
  active: ['deactivate', 'complete', 'cancel'],
  completed: ['review'],
  cancelled: ['reopen'],
  terminated: ['review'],
}

// Computed
const statusLabel = computed(() => statusConfig[props.status]?.label || props.status)
const statusColor = computed(() => statusConfig[props.status]?.color || 'grey')
const statusIcon = computed(() => statusConfig[props.status]?.icon || 'mdi-circle')

const availableActions = computed(() => {
  const actions = actionsByStatus[props.status] || []
  return actions.map((actionKey) => actionDefinitions[actionKey]).filter(Boolean)
})

const confirmDialogTitle = computed(() => {
  if (!pendingAction.value) return ''
  if (pendingAction.value.value === 'delete') {
    return 'Delete Project?'
  }
  return `${pendingAction.value.label} Project?`
})

const confirmMessage = computed(() => {
  if (!pendingAction.value) return ''

  const actionLabel = pendingAction.value.label.toLowerCase()
  const projectName = props.projectName

  if (pendingAction.value.value === 'delete') {
    return `Are you sure you want to permanently delete "${projectName}"? This action cannot be undone and will remove all associated data.`
  }

  if (pendingAction.value.value === 'cancel') {
    return `Are you sure you want to cancel "${projectName}"? This will mark the project as cancelled and may affect associated tasks.`
  }

  if (pendingAction.value.value === 'complete') {
    return `Mark "${projectName}" as completed? This will close the project and update its status.`
  }

  if (pendingAction.value.value === 'deactivate') {
    return `This will free up the active project slot. The project can be reactivated later.`
  }

  return `Are you sure you want to ${actionLabel} "${projectName}"?`
})

// Methods
const handleActionClick = (action) => {
  menuOpen.value = false

  if (action.requiresConfirm) {
    pendingAction.value = action
    showConfirmDialog.value = true
  } else {
    executeAction(action)
  }
}

const confirmAction = () => {
  if (pendingAction.value) {
    executeAction(pendingAction.value)
    showConfirmDialog.value = false
  }
}

const cancelConfirmation = () => {
  showConfirmDialog.value = false
  pendingAction.value = null
}

const executeAction = (action) => {
  loading.value = true
  emit('loading', { loading: true })

  emit('action', {
    action: action.value,
    newStatus: action.newStatus,
    projectId: props.projectId,
  })

  // Parent component is responsible for handling the action
  // and calling the API. We'll reset loading state when the
  // parent updates the status prop or we can expose a method
  // to reset loading state.

  // For now, reset loading after a short delay to prevent UI freeze
  setTimeout(() => {
    loading.value = false
    emit('loading', { loading: false })
  }, 500)
}

// Watch for status changes to close dialogs
watch(
  () => props.status,
  () => {
    menuOpen.value = false
    showConfirmDialog.value = false
    pendingAction.value = null
    loading.value = false
  },
)

// Expose method to reset loading state (optional, for parent control)
defineExpose({
  resetLoading: () => {
    loading.value = false
  },
})
</script>

<style scoped>
.status-badge-wrapper {
  display: inline-block;
}

.status-badge-chip {
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.status-badge-chip:not(.status-badge-loading):hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.status-badge-chip:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

.status-badge-loading {
  opacity: 0.7;
  cursor: not-allowed;
}

.status-spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.status-menu-list {
  min-width: 160px;
}

.status-menu-list .v-list-item {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.status-menu-list .v-list-item:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}

.status-menu-list .v-list-item:focus-visible {
  outline: 2px solid rgba(var(--v-theme-primary), 0.5);
  outline-offset: -2px;
}

.status-menu-list .v-list-item.text-error:hover {
  background-color: rgba(var(--v-theme-error), 0.08);
}
</style>
