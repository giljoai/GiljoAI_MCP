<template>
  <v-dialog
    v-model="isOpen"
    :max-width="maxWidth"
    :persistent="persistent"
    z-index="2500"
    @update:model-value="handleDialogChange"
  >
    <v-card v-draggable class="base-dialog-card" elevation="24">
      <!-- Title Bar -->
      <v-card-title :class="titleClasses">
        <v-icon v-if="showIcon" :class="iconClasses">{{ iconName }}</v-icon>
        <span>{{ title }}</span>
        <v-spacer v-if="$slots.titleAppend" />
        <slot name="titleAppend" />
      </v-card-title>

      <v-divider />

      <!-- Content -->
      <v-card-text :class="contentClasses">
        <!-- Default alert for simple messages -->
        <v-alert
          v-if="message && !$slots.default"
          :type="type"
          variant="tonal"
          density="compact"
          class="mb-4"
        >
          {{ message }}
        </v-alert>

        <!-- Custom content slot -->
        <slot />

        <!-- Text confirmation input -->
        <v-text-field
          v-if="confirmText"
          v-model="confirmInput"
          :label="`Type ${confirmText} to confirm`"
          variant="outlined"
          :hint="`Type the word ${confirmText} to enable the confirm button`"
          persistent-hint
          :placeholder="confirmText"
          class="mt-4"
        />

        <!-- Checkbox confirmation -->
        <v-checkbox
          v-if="confirmCheckbox"
          v-model="checkboxConfirmed"
          density="compact"
          hide-details
          class="mt-4"
        >
          <template #label>
            <span>{{ confirmCheckboxLabel }}</span>
          </template>
        </v-checkbox>
      </v-card-text>

      <v-divider />

      <!-- Actions -->
      <v-card-actions>
        <v-spacer />
        <slot name="actions" :can-confirm="canConfirm" :loading="loading">
          <v-btn
            variant="text"
            :disabled="loading"
            @click="handleCancel"
          >
            {{ cancelText }}
          </v-btn>
          <v-btn
            :color="confirmButtonColor"
            :variant="confirmButtonVariant"
            :loading="loading"
            :disabled="!canConfirm"
            @click="handleConfirm"
          >
            {{ confirmLabel }}
          </v-btn>
        </slot>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
/**
 * BaseDialog.vue - Standardized Dialog Component
 *
 * Provides consistent styling and behavior for all application dialogs.
 *
 * Types:
 * - info: Blue header, informational content
 * - warning: Amber header, caution/reversible actions
 * - danger: Red header, destructive/irreversible actions
 * - success: Green header, positive confirmations
 *
 * Confirmation Patterns:
 * - None: Simple confirm/cancel
 * - confirmText: Requires typing specific text (e.g., "DELETE")
 * - confirmCheckbox: Requires checking acknowledgment box
 *
 * @example Basic usage
 * <BaseDialog
 *   v-model="showDialog"
 *   type="warning"
 *   title="Switch Product?"
 *   message="This will change the active context."
 *   @confirm="handleSwitch"
 * />
 *
 * @example With text confirmation
 * <BaseDialog
 *   v-model="showDialog"
 *   type="danger"
 *   title="Delete Item?"
 *   confirm-text="DELETE"
 *   @confirm="handleDelete"
 * >
 *   <p>This action cannot be undone.</p>
 * </BaseDialog>
 */

import { ref, computed, watch } from 'vue'

const props = defineProps({
  // v-model binding
  modelValue: {
    type: Boolean,
    required: true,
  },

  // Dialog type determines colors and icon
  type: {
    type: String,
    default: 'info',
    validator: (val) => ['info', 'warning', 'danger', 'success'].includes(val),
  },

  // Title text
  title: {
    type: String,
    required: true,
  },

  // Simple message (alternative to slot content)
  message: {
    type: String,
    default: '',
  },

  // Confirm button text
  confirmLabel: {
    type: String,
    default: 'Confirm',
  },

  // Cancel button text
  cancelText: {
    type: String,
    default: 'Cancel',
  },

  // Dialog width: 'sm' (400), 'md' (500), 'lg' (650), 'xl' (800), or number
  size: {
    type: [String, Number],
    default: 'md',
  },

  // Prevent closing by clicking outside
  persistent: {
    type: Boolean,
    default: true,
  },

  // Loading state for confirm button
  loading: {
    type: Boolean,
    default: false,
  },

  // Text confirmation (user must type this to confirm)
  confirmText: {
    type: String,
    default: '',
  },

  // Checkbox confirmation
  confirmCheckbox: {
    type: Boolean,
    default: false,
  },

  // Checkbox label
  confirmCheckboxLabel: {
    type: String,
    default: 'I understand and want to proceed',
  },

  // Hide the icon in title
  hideIcon: {
    type: Boolean,
    default: false,
  },

  // Custom icon (overrides type default)
  icon: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

// Local state
const confirmInput = ref('')
const checkboxConfirmed = ref(false)

// Computed: dialog open state
const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

// Computed: size to max-width mapping
const maxWidth = computed(() => {
  const sizeMap = {
    sm: 400,
    md: 500,
    lg: 650,
    xl: 800,
  }
  return typeof props.size === 'number' ? props.size : sizeMap[props.size] || 500
})

// Computed: type-based configuration
const typeConfig = computed(() => {
  const configs = {
    info: {
      color: 'info',
      icon: 'mdi-information',
      bgClass: 'bg-info',
    },
    warning: {
      color: 'warning',
      icon: 'mdi-alert',
      bgClass: 'bg-warning',
    },
    danger: {
      color: 'error',
      icon: 'mdi-alert-circle',
      bgClass: 'bg-error',
    },
    success: {
      color: 'success',
      icon: 'mdi-check-circle',
      bgClass: 'bg-success',
    },
  }
  return configs[props.type] || configs.info
})

// Computed: title bar classes
const titleClasses = computed(() => [
  'd-flex',
  'align-center',
  typeConfig.value.bgClass,
])

// Computed: icon classes
const iconClasses = computed(() => ['mr-2'])

// Computed: whether to show icon
const showIcon = computed(() => !props.hideIcon)

// Computed: icon name
const iconName = computed(() => props.icon || typeConfig.value.icon)

// Computed: content area classes
const contentClasses = computed(() => ['pt-4'])

// Computed: confirm button color
const confirmButtonColor = computed(() => typeConfig.value.color)

// Computed: confirm button variant
const confirmButtonVariant = computed(() => 'flat')

// Computed: can confirm (validation passed)
const canConfirm = computed(() => {
  // Text confirmation required
  if (props.confirmText) {
    return confirmInput.value === props.confirmText
  }

  // Checkbox confirmation required
  if (props.confirmCheckbox) {
    return checkboxConfirmed.value
  }

  // No confirmation required
  return true
})

// Methods
function handleConfirm() {
  if (canConfirm.value) {
    emit('confirm')
  }
}

function handleCancel() {
  if (!props.loading) {
    emit('cancel')
    isOpen.value = false
  }
}

function handleDialogChange(val) {
  if (!val && !props.loading) {
    emit('cancel')
  }
}

// Reset confirmation state when dialog opens/closes
watch(() => props.modelValue, (newVal) => {
  if (!newVal) {
    confirmInput.value = ''
    checkboxConfirmed.value = false
  }
})
</script>

<style scoped>
/* Ensure dialog card is fully opaque and elevated */
.base-dialog-card {
  background-color: rgb(var(--v-theme-surface));
  opacity: 1;
}

/* Title bar background colors with proper contrast */
.bg-info {
  background-color: rgb(var(--v-theme-info));
  color: white;
}

.bg-warning {
  background-color: rgb(var(--v-theme-warning));
  color: rgba(0, 0, 0, 0.87);
}

.bg-error {
  background-color: rgb(var(--v-theme-error));
  color: white;
}

.bg-success {
  background-color: rgb(var(--v-theme-success));
  color: white;
}

/* Icon sizing in title */
.v-card-title .v-icon {
  font-size: 1.5rem;
}
</style>
