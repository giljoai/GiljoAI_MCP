<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-2">Choose Deployment Mode</h2>
    <p class="text-body-1 mb-6">How will you use GiljoAI MCP?</p>

    <v-radio-group v-model="selectedMode" class="mb-6">
      <!-- Localhost -->
      <v-card
        variant="outlined"
        class="mb-4 mode-card"
        :class="{ selected: selectedMode === 'localhost' }"
        @click="selectedMode = 'localhost'"
        role="button"
        tabindex="0"
        aria-label="Select localhost mode for single user"
      >
        <v-card-text>
          <v-radio value="localhost">
            <template #label>
              <div class="ml-4">
                <div class="text-h6 d-flex align-center">
                  <v-icon class="mr-2">mdi-laptop</v-icon>
                  Localhost
                </div>
                <div class="text-caption text-medium-emphasis">
                  Single user on this computer only
                </div>
              </div>
            </template>
          </v-radio>

          <v-list density="compact" class="mt-4 bg-transparent">
            <v-list-item
              prepend-icon="mdi-check"
              title="No network access required"
              class="text-caption"
            />
            <v-list-item
              prepend-icon="mdi-check"
              title="No authentication needed"
              class="text-caption"
            />
            <v-list-item
              prepend-icon="mdi-check"
              title="Fastest performance"
              class="text-caption"
            />
            <v-list-item
              prepend-icon="mdi-check"
              title="Recommended for personal use"
              class="text-caption"
            />
          </v-list>
        </v-card-text>
      </v-card>

      <!-- LAN -->
      <v-card
        variant="outlined"
        class="mb-4 mode-card"
        :class="{ selected: selectedMode === 'lan' }"
        @click="selectedMode = 'lan'"
        role="button"
        tabindex="0"
        aria-label="Select LAN mode for local network team access"
      >
        <v-card-text>
          <v-radio value="lan">
            <template #label>
              <div class="ml-4">
                <div class="text-h6 d-flex align-center">
                  <v-icon class="mr-2">mdi-network</v-icon>
                  LAN (Local Area Network)
                </div>
                <div class="text-caption text-medium-emphasis">
                  Team access on your local network
                </div>
              </div>
            </template>
          </v-radio>

          <v-list density="compact" class="mt-4 bg-transparent">
            <v-list-item
              prepend-icon="mdi-check"
              title="Multiple users can connect"
              class="text-caption"
            />
            <v-list-item
              prepend-icon="mdi-check"
              title="Requires admin account setup"
              class="text-caption"
            />
            <v-list-item
              prepend-icon="mdi-check"
              title="Firewall configuration needed"
              class="text-caption"
            />
            <v-list-item
              prepend-icon="mdi-check"
              title="Recommended for teams (2-10 users)"
              class="text-caption"
            />
          </v-list>
        </v-card-text>
      </v-card>

      <!-- WAN (disabled) -->
      <v-card variant="outlined" class="mb-4 mode-card disabled" disabled aria-disabled="true">
        <v-card-text>
          <v-radio value="wan" disabled>
            <template #label>
              <div class="ml-4">
                <div class="text-h6 d-flex align-center text-disabled">
                  <v-icon class="mr-2" color="disabled">mdi-earth</v-icon>
                  WAN (Wide Area Network)
                  <v-chip size="small" color="info" class="ml-2">Coming Soon</v-chip>
                </div>
                <div class="text-caption text-disabled">Internet access for remote teams</div>
              </div>
            </template>
          </v-radio>

          <v-list density="compact" class="mt-4 bg-transparent">
            <v-list-item
              prepend-icon="mdi-close"
              title="Coming in Phase 1"
              class="text-caption text-disabled"
            />
            <v-list-item
              prepend-icon="mdi-close"
              title="Requires SSL/TLS certificates"
              class="text-caption text-disabled"
            />
            <v-list-item
              prepend-icon="mdi-close"
              title="Advanced security features"
              class="text-caption text-disabled"
            />
          </v-list>
        </v-card-text>
      </v-card>
    </v-radio-group>

    <!-- Info -->
    <v-alert type="info" variant="tonal" class="mb-6">
      <v-icon start>mdi-information</v-icon>
      You can change this setting later in Settings &gt; General
    </v-alert>

    <!-- Progress -->
    <v-card variant="outlined" class="mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 3 of 7</span>
          <span class="text-caption">43%</span>
        </div>
        <v-progress-linear :model-value="43" color="primary" />
      </v-card-text>
    </v-card>

    <!-- Navigation -->
    <div class="d-flex justify-space-between">
      <v-btn variant="outlined" @click="$emit('back')" aria-label="Go back to database">
        <v-icon start>mdi-arrow-left</v-icon>
        Back
      </v-btn>
      <v-btn
        color="primary"
        :disabled="!selectedMode"
        @click="handleNext"
        aria-label="Continue to next step"
      >
        Continue
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </div>
  </v-card-text>
</template>

<script setup>
import { ref, watch } from 'vue'

/**
 * DeploymentModeStep - Deployment mode selection step
 *
 * Allows user to choose between localhost, LAN, or WAN deployment modes
 */

const props = defineProps({
  modelValue: {
    type: String,
    required: true,
    validator: (value) => ['localhost', 'lan', 'wan'].includes(value),
  },
})

const emit = defineEmits(['update:modelValue', 'next', 'back'])

const selectedMode = ref(props.modelValue)

watch(selectedMode, (newVal) => {
  emit('update:modelValue', newVal)
})

const handleNext = () => {
  emit('next')
}
</script>

<style scoped>
h2 {
  color: rgb(var(--v-theme-primary));
}

.mode-card {
  cursor: pointer;
  transition: all 0.2s ease;
}

.mode-card:hover:not(.disabled) {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
}

.mode-card.selected {
  border-color: rgb(var(--v-theme-primary));
  border-width: 2px;
  background-color: rgba(var(--v-theme-primary), 0.05);
}

.mode-card.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mode-card.disabled:hover {
  background-color: transparent;
}
</style>
