<template>
  <div class="field-checkbox-group">
    <!-- Group Header with Total -->
    <div class="d-flex justify-space-between align-center mb-2">
      <div class="text-subtitle-1 font-weight-medium">{{ label }}</div>
      <v-chip size="small" color="primary" variant="tonal">
        {{ totalTokens.toLocaleString() }} tokens
      </v-chip>
    </div>

    <!-- Select All / None Actions -->
    <div class="d-flex gap-2 mb-2">
      <v-btn
        size="x-small"
        variant="text"
        density="compact"
        @click="selectAll(true)"
        :disabled="allSelected"
      >
        Select All
      </v-btn>
      <v-btn
        size="x-small"
        variant="text"
        density="compact"
        @click="selectAll(false)"
        :disabled="!someSelected"
      >
        Clear All
      </v-btn>
    </div>

    <!-- Checkbox List -->
    <div class="checkbox-container">
      <div
        v-for="field in fields"
        :key="field.key"
        class="checkbox-item d-flex justify-space-between align-center"
      >
        <v-checkbox
          :model-value="modelValue[field.key]"
          @update:model-value="onCheckboxChange(field.key, $event)"
          :label="field.label"
          density="compact"
          hide-details
          class="flex-grow-1"
        />
        <v-chip
          size="x-small"
          variant="outlined"
          :color="modelValue[field.key] ? 'primary' : 'grey'"
          class="token-chip"
        >
          {{ field.tokens }}
        </v-chip>
      </div>
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
}

const props = defineProps<Props>();
const emit = defineEmits<{
  'update:modelValue': [value: Record<string, boolean>];
}>();

// Computed properties
const totalTokens = computed(() => {
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
function onCheckboxChange(key: string, value: boolean) {
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
  allSelected,
  someSelected,
  toggleField,
  selectAll,
});
</script>

<style scoped>
.field-checkbox-group {
  padding: 12px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 4px;
  background-color: rgba(var(--v-theme-surface-variant), 0.05);
}

.checkbox-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.checkbox-item {
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.checkbox-item:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.04);
}

.token-chip {
  min-width: 40px;
  text-align: center;
}
</style>
