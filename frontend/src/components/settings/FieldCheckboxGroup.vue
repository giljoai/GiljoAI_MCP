<template>
  <div class="field-checkbox-group">
    <!-- Group Header with Total -->
    <div class="d-flex justify-space-between align-center mb-1">
      <div class="text-subtitle-2 font-weight-medium">{{ label }}</div>
      <v-chip size="x-small" color="primary" variant="tonal">
        ~{{ totalTokens.toLocaleString() }} tokens
      </v-chip>
    </div>

    <!-- Subtitle -->
    <div class="text-caption grey--text text--darken-1 mb-2">
      {{ subtitle || 'Fields from product profile' }}
    </div>

    <!-- Horizontal Switch List -->
    <div class="switch-container d-flex flex-wrap align-center">
      <div
        v-for="field in fields"
        :key="field.key"
        class="switch-item d-flex align-center mr-4 mb-1"
      >
        <span class="text-body-2 mr-1">{{ field.label }}</span>
        <v-switch
          :model-value="modelValue[field.key]"
          @update:model-value="onSwitchChange(field.key, $event)"
          density="compact"
          hide-details
          color="primary"
          :aria-label="`Toggle ${field.label}`"
          class="compact-switch"
        />
      </div>
    </div>

    <!-- Selected Tokens Footer -->
    <div class="text-right mt-1">
      <span class="text-caption grey--text">
        ~{{ selectedTokens.toLocaleString() }} tokens
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Field {
  key: string;
  label: string;
  tokens: number;
}

interface Props {
  fields: Field[];
  modelValue: Record<string, boolean>;
  label: string;
  subtitle?: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  'update:modelValue': [value: Record<string, boolean>];
}>();

// Computed properties
const totalTokens = computed(() => {
  return props.fields.reduce((sum, field) => sum + field.tokens, 0);
});

const selectedTokens = computed(() => {
  return props.fields.reduce((sum, field) => {
    return sum + (props.modelValue[field.key] ? field.tokens : 0);
  }, 0);
});

const allSelected = computed(() => {
  if (props.fields.length === 0) return false;
  return props.fields.every(field => props.modelValue[field.key]);
});

const someSelected = computed(() => {
  return props.fields.some(field => props.modelValue[field.key]);
});

// Methods
function onSwitchChange(key: string, value: boolean) {
  const newValue = { ...props.modelValue, [key]: value };
  emit('update:modelValue', newValue);
}

function toggleField(key: string) {
  const newValue = { ...props.modelValue, [key]: !props.modelValue[key] };
  emit('update:modelValue', newValue);
}

function selectAll(selected: boolean) {
  const newValue: Record<string, boolean> = {};
  props.fields.forEach(field => {
    newValue[field.key] = selected;
  });
  emit('update:modelValue', newValue);
}

// Expose methods for testing
defineExpose({
  totalTokens,
  selectedTokens,
  allSelected,
  someSelected,
  toggleField,
  selectAll,
});
</script>

<style scoped>
.field-checkbox-group {
  padding: 8px 12px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 4px;
  background-color: rgba(var(--v-theme-surface-variant), 0.03);
}

.switch-container {
  gap: 4px;
}

.switch-item {
  white-space: nowrap;
}

.compact-switch {
  margin: 0;
  padding: 0;
}

.compact-switch :deep(.v-switch__track) {
  height: 14px;
  width: 28px;
}

.compact-switch :deep(.v-switch__thumb) {
  height: 10px;
  width: 10px;
}

.compact-switch :deep(.v-selection-control) {
  min-height: auto;
}

/* Ensure grey text colors work in both light and dark themes */
.grey--text.text--darken-1 {
  color: rgba(var(--v-theme-on-surface), 0.6) !important;
}
</style>
