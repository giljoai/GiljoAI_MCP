<template>
  <v-card class="compact-card">
    <v-card-title class="text-h6 pb-1">Depth Configuration</v-card-title>
    <v-card-subtitle class="text-caption pt-0">
      Control extraction detail levels for context sources
    </v-card-subtitle>

    <v-card-text class="pt-2">
      <!-- Token Budget Alert -->
      <v-alert
        :type="budgetStatus"
        :icon="budgetIcon"
        class="mb-3 compact-alert"
        density="compact"
      >
        <div class="d-flex justify-space-between align-center flex-wrap">
          <div class="text-body-2">
            <strong>Total:</strong> {{ totalTokens.toLocaleString() }} tokens
          </div>
          <div v-if="userTokenBudget" class="text-caption">
            Budget: {{ userTokenBudget.toLocaleString() }} ({{ budgetPercentage }}%)
          </div>
        </div>
      </v-alert>

      <!-- Locked Project Context Display -->
      <div class="depth-control-row compact-row d-flex justify-space-between align-center py-2">
        <div>
          <div class="d-flex align-center">
            <v-icon size="small" color="primary" class="mr-1">mdi-lock</v-icon>
            <span class="text-subtitle-2 font-weight-medium">Project Context</span>
          </div>
          <div class="text-caption text-medium-emphasis ml-5">
            Always included - project metadata
          </div>
        </div>
        <v-chip size="x-small" color="primary" variant="flat">
          {{ projectContextTokens.toLocaleString() }}
        </v-chip>
      </div>

      <!-- Product Core Toggle -->
      <div class="depth-control-row compact-row d-flex justify-space-between align-center py-2">
        <div class="flex-grow-1">
          <div class="text-subtitle-2 font-weight-medium">Product Core</div>
          <div class="text-caption text-medium-emphasis">Basic product information</div>
        </div>
        <div class="d-flex align-center">
          <v-select
            v-model="depthConfig.product_core_enabled"
            :items="productCoreOptions"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="updateEstimate"
            aria-label="Product Core depth setting"
            class="compact-select mr-2"
          />
          <v-chip size="x-small" color="primary" variant="tonal">
            {{ (tokenEstimates.product_core_enabled || 0).toLocaleString() }}
          </v-chip>
        </div>
      </div>

      <!-- Vision Documents Dropdown -->
      <div class="depth-control-row compact-row d-flex justify-space-between align-center py-2">
        <div class="flex-grow-1">
          <div class="text-subtitle-2 font-weight-medium">Vision Documents</div>
          <div class="text-caption text-medium-emphasis">Chunking level for uploads</div>
        </div>
        <div class="d-flex align-center">
          <v-select
            v-model="depthConfig.vision_chunking"
            :items="visionOptions"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="updateEstimate"
            aria-label="Vision Documents depth setting"
            class="compact-select mr-2"
          />
          <v-chip size="x-small" color="primary" variant="tonal">
            {{ (tokenEstimates.vision_chunking || 0).toLocaleString() }}
          </v-chip>
        </div>
      </div>

      <!-- Tech Stack Checkbox Group -->
      <div class="depth-control-row py-2">
        <FieldCheckboxGroup
          v-model="depthConfig.tech_stack_fields"
          :fields="techStackFields"
          label="Tech Stack"
          subtitle="Programming languages and frameworks"
          @update:model-value="updateEstimate"
        />
      </div>

      <!-- Architecture Checkbox Group -->
      <div class="depth-control-row py-2">
        <FieldCheckboxGroup
          v-model="depthConfig.architecture_fields"
          :fields="architectureFields"
          label="Architecture"
          subtitle="Design patterns and structure"
          @update:model-value="updateEstimate"
        />
      </div>

      <!-- Testing Checkbox Group -->
      <div class="depth-control-row py-2">
        <FieldCheckboxGroup
          v-model="depthConfig.testing_fields"
          :fields="testingFields"
          label="Testing"
          subtitle="Quality standards and frameworks"
          @update:model-value="updateEstimate"
        />
      </div>

      <!-- Agent Templates Dropdown -->
      <div class="depth-control-row compact-row d-flex justify-space-between align-center py-2">
        <div class="flex-grow-1">
          <div class="text-subtitle-2 font-weight-medium">Agent Templates</div>
          <div class="text-caption text-medium-emphasis">Detail level for templates</div>
        </div>
        <div class="d-flex align-center">
          <v-select
            v-model="depthConfig.agent_template_detail"
            :items="agentTemplateOptions"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="updateEstimate"
            aria-label="Agent Templates depth setting"
            class="compact-select mr-2"
          />
          <v-chip size="x-small" color="primary" variant="tonal">
            {{ (tokenEstimates.agent_template_detail || 0).toLocaleString() }}
          </v-chip>
        </div>
      </div>

      <!-- 360 Memory Dropdown -->
      <div class="depth-control-row compact-row d-flex justify-space-between align-center py-2">
        <div class="flex-grow-1">
          <div class="text-subtitle-2 font-weight-medium">360 Memory</div>
          <div class="text-caption text-medium-emphasis">Recent projects to include</div>
        </div>
        <div class="d-flex align-center">
          <v-select
            v-model="depthConfig.memory_last_n_projects"
            :items="memoryOptions"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="updateEstimate"
            aria-label="360 Memory depth setting"
            class="compact-select mr-2"
          />
          <v-chip size="x-small" color="primary" variant="tonal">
            {{ (tokenEstimates.memory_last_n_projects || 0).toLocaleString() }}
          </v-chip>
        </div>
      </div>

      <!-- Git History Dropdown -->
      <div class="depth-control-row compact-row d-flex justify-space-between align-center py-2">
        <div class="flex-grow-1">
          <div class="text-subtitle-2 font-weight-medium">Git History</div>
          <div class="text-caption text-medium-emphasis">Recent commits</div>
        </div>
        <div class="d-flex align-center">
          <v-select
            v-model="depthConfig.git_commits"
            :items="gitOptions"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="updateEstimate"
            aria-label="Git History depth setting"
            class="compact-select mr-2"
          />
          <v-chip size="x-small" color="primary" variant="tonal">
            {{ (tokenEstimates.git_commits || 0).toLocaleString() }}
          </v-chip>
        </div>
      </div>

      <!-- Save Button -->
      <div class="mt-4">
        <v-btn
          color="primary"
          :loading="saving"
          :disabled="saving"
          @click="saveDepthConfig"
        >
          <v-icon start size="small">mdi-content-save</v-icon>
          Save Configuration
        </v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import {
  DepthTokenEstimator,
  type DepthConfig,
  type TechStackFields,
  type ArchitectureFields,
  type TestingFields
} from '@/services/depthTokenEstimator';
import FieldCheckboxGroup from '@/components/settings/FieldCheckboxGroup.vue';
import axios from 'axios';

// State
const depthConfig = ref<DepthConfig>({
  vision_chunking: 'moderate',
  memory_last_n_projects: 3,
  git_commits: 15,
  agent_template_detail: 'type_only',
  product_core_enabled: true,
  // v3.0: Field-based selection
  tech_stack_fields: {
    languages: true,
    frameworks: true,
    databases: true,
    dependencies: false,
  },
  architecture_fields: {
    primary_pattern: true,
    api_style: true,
    design_patterns: true,
    architecture_notes: false,
    security_considerations: false,
    scalability_notes: false,
  },
  testing_fields: {
    quality_standards: true,
    testing_strategy: true,
    testing_frameworks: false,
  },
});

const saving = ref(false);
const userTokenBudget = ref<number>(200000);
const tokenEstimates = ref<Record<string, number>>({});
const totalTokens = ref(0);
const projectContextTokens = ref(200); // Locked value

// Field definitions from estimator
const techStackFields = DepthTokenEstimator.getTechStackFieldDefinitions();
const architectureFields = DepthTokenEstimator.getArchitectureFieldDefinitions();
const testingFields = DepthTokenEstimator.getTestingFieldDefinitions();

// Dropdown options - shortened titles for compact display
const productCoreOptions = [
  { title: 'Disabled', value: false },
  { title: 'Enabled (~100)', value: true },
];

const visionOptions = [
  { title: 'None', value: 'none' },
  { title: 'Light (~10K)', value: 'light' },
  { title: 'Moderate (~17.5K)', value: 'moderate' },
  { title: 'Heavy (~30K)', value: 'heavy' },
];

const agentTemplateOptions = [
  { title: 'Type Only (~400)', value: 'type_only' },
  { title: 'Full (~2.4K)', value: 'full' },
];

const memoryOptions = [
  { title: '1 project (~500)', value: 1 },
  { title: '3 projects (~1.5K)', value: 3 },
  { title: '5 projects (~2.5K)', value: 5 },
  { title: '10 projects (~5K)', value: 10 },
];

const gitOptions = [
  { title: 'None', value: 0 },
  { title: '5 commits (~250)', value: 5 },
  { title: '15 commits (~750)', value: 15 },
  { title: '25 commits (~1.25K)', value: 25 },
];

// Computed properties
const budgetPercentage = computed(() => {
  if (!userTokenBudget.value) return 0;
  return Math.round((totalTokens.value / userTokenBudget.value) * 100);
});

const budgetStatus = computed(() => {
  const pct = budgetPercentage.value;
  if (pct > 100) return 'error';
  if (pct > 90) return 'warning';
  return 'success';
});

const budgetIcon = computed(() => {
  if (budgetStatus.value === 'error') return 'mdi-alert-circle';
  if (budgetStatus.value === 'warning') return 'mdi-alert';
  return 'mdi-check-circle';
});

// Methods
function updateEstimate() {
  const estimate = DepthTokenEstimator.estimate(depthConfig.value);
  tokenEstimates.value = estimate.per_source;
  totalTokens.value = estimate.total;
  console.log('[DEPTH CONFIG] Token estimate updated:', estimate);
}

async function fetchDepthConfig() {
  try {
    const response = await axios.get('/api/v1/users/me/context/depth');
    const serverConfig = response.data.depth_config;

    // Merge server config with defaults to handle missing v3.0 fields
    depthConfig.value = {
      ...depthConfig.value,
      ...serverConfig,
    };

    // Ensure field objects exist
    if (!depthConfig.value.tech_stack_fields) {
      depthConfig.value.tech_stack_fields = {
        languages: true,
        frameworks: true,
        databases: true,
        dependencies: false,
      };
    }
    if (!depthConfig.value.architecture_fields) {
      depthConfig.value.architecture_fields = {
        primary_pattern: true,
        api_style: true,
        design_patterns: true,
        architecture_notes: false,
        security_considerations: false,
        scalability_notes: false,
      };
    }
    if (!depthConfig.value.testing_fields) {
      depthConfig.value.testing_fields = {
        quality_standards: true,
        testing_strategy: true,
        testing_frameworks: false,
      };
    }

    if (response.data.token_estimate) {
      tokenEstimates.value = response.data.token_estimate.per_source;
      totalTokens.value = response.data.token_estimate.total;
    } else {
      updateEstimate();
    }
    console.log('[DEPTH CONFIG] Configuration loaded from server:', depthConfig.value);
  } catch (error) {
    console.error('[DEPTH CONFIG] Failed to fetch depth config:', error);
    // Use local estimation as fallback
    updateEstimate();
  }
}

async function saveDepthConfig() {
  saving.value = true;
  try {
    const response = await axios.put('/api/v1/users/me/context/depth', {
      depth_config: depthConfig.value,
    });

    // Update from server response
    if (response.data.token_estimate) {
      tokenEstimates.value = response.data.token_estimate.per_source;
      totalTokens.value = response.data.token_estimate.total;
    }

    console.log('[DEPTH CONFIG] Configuration saved successfully');
  } catch (error) {
    console.error('[DEPTH CONFIG] Failed to save depth config:', error);
  } finally {
    saving.value = false;
  }
}

// Lifecycle
onMounted(() => {
  fetchDepthConfig();
});
</script>

<style scoped>
.compact-card {
  padding: 8px;
}

.compact-card :deep(.v-card-title) {
  padding: 8px 12px 4px;
}

.compact-card :deep(.v-card-subtitle) {
  padding: 0 12px 8px;
}

.compact-card :deep(.v-card-text) {
  padding: 8px 12px;
}

.compact-alert {
  padding: 8px 12px;
}

.depth-control-row {
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

.depth-control-row:last-of-type {
  border-bottom: none;
}

.compact-row {
  min-height: 48px;
}

.compact-select {
  max-width: 160px;
  min-width: 140px;
}

.compact-select :deep(.v-field__input) {
  font-size: 0.75rem;
  padding-top: 4px;
  padding-bottom: 4px;
}

.compact-select :deep(.v-field) {
  min-height: 32px;
}

/* Ensure medium emphasis text works in both themes */
.text-medium-emphasis {
  color: rgba(var(--v-theme-on-surface), 0.6);
}

/* Mobile responsive adjustments */
@media (max-width: 600px) {
  .compact-row {
    flex-direction: column;
    align-items: flex-start !important;
  }

  .compact-row > div:last-child {
    width: 100%;
    justify-content: space-between;
    margin-top: 8px;
  }

  .compact-select {
    flex-grow: 1;
  }
}
</style>
