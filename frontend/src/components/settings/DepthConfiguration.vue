<template>
  <v-card>
    <v-card-title>Depth Configuration</v-card-title>
    <v-card-subtitle>
      Control extraction detail levels for context sources
    </v-card-subtitle>

    <v-card-text>
      <!-- Token Budget Alert -->
      <v-alert
        :type="budgetStatus"
        :icon="budgetIcon"
        class="mb-4"
        prominent
      >
        <div class="d-flex justify-space-between align-center flex-wrap">
          <div>
            <strong>Total Estimated Tokens:</strong>
            {{ totalTokens.toLocaleString() }}
          </div>
          <div v-if="userTokenBudget" class="text-caption">
            Budget: {{ userTokenBudget.toLocaleString() }} tokens
            ({{ budgetPercentage }}% used)
          </div>
        </div>
      </v-alert>

      <!-- Locked Project Context Display -->
      <v-card variant="tonal" color="primary" class="mb-4">
        <v-card-text class="py-3">
          <div class="d-flex justify-space-between align-center">
            <div>
              <div class="d-flex align-center">
                <v-icon start color="primary">mdi-lock</v-icon>
                <span class="text-subtitle-1 font-weight-medium">Project Context</span>
              </div>
              <div class="text-caption text-grey-darken-1 ml-7">
                Always included - project name, alias, mission, status
              </div>
            </div>
            <v-chip size="small" color="primary" variant="flat">
              {{ projectContextTokens.toLocaleString() }} tokens
            </v-chip>
          </div>
        </v-card-text>
      </v-card>

      <!-- Product Core Toggle -->
      <v-row class="mb-3 align-center depth-control-row">
        <v-col cols="12" md="4">
          <div class="text-subtitle-1 font-weight-medium">Product Core</div>
          <div class="text-caption text-grey-darken-1">Basic product information</div>
        </v-col>
        <v-col cols="12" md="5">
          <v-select
            v-model="depthConfig.product_core_enabled"
            :items="productCoreOptions"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="updateEstimate"
            aria-label="Product Core depth setting"
          />
        </v-col>
        <v-col cols="12" md="3" class="text-right">
          <v-chip size="small" color="primary" variant="tonal">
            {{ (tokenEstimates.product_core_enabled || 0).toLocaleString() }} tokens
          </v-chip>
        </v-col>
      </v-row>

      <!-- Vision Documents Dropdown -->
      <v-row class="mb-3 align-center depth-control-row">
        <v-col cols="12" md="4">
          <div class="text-subtitle-1 font-weight-medium">Vision Documents</div>
          <div class="text-caption text-grey-darken-1">Chunking level for vision uploads</div>
        </v-col>
        <v-col cols="12" md="5">
          <v-select
            v-model="depthConfig.vision_chunking"
            :items="visionOptions"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="updateEstimate"
            aria-label="Vision Documents depth setting"
          />
        </v-col>
        <v-col cols="12" md="3" class="text-right">
          <v-chip size="small" color="primary" variant="tonal">
            {{ (tokenEstimates.vision_chunking || 0).toLocaleString() }} tokens
          </v-chip>
        </v-col>
      </v-row>

      <!-- Tech Stack Checkbox Group -->
      <v-row class="mb-3 depth-control-row">
        <v-col cols="12">
          <FieldCheckboxGroup
            v-model="depthConfig.tech_stack_fields"
            :fields="techStackFields"
            label="Tech Stack"
            @update:model-value="updateEstimate"
          />
        </v-col>
      </v-row>

      <!-- Architecture Checkbox Group -->
      <v-row class="mb-3 depth-control-row">
        <v-col cols="12">
          <FieldCheckboxGroup
            v-model="depthConfig.architecture_fields"
            :fields="architectureFields"
            label="Architecture"
            @update:model-value="updateEstimate"
          />
        </v-col>
      </v-row>

      <!-- Testing Checkbox Group -->
      <v-row class="mb-3 depth-control-row">
        <v-col cols="12">
          <FieldCheckboxGroup
            v-model="depthConfig.testing_fields"
            :fields="testingFields"
            label="Testing"
            @update:model-value="updateEstimate"
          />
        </v-col>
      </v-row>

      <!-- Agent Templates Dropdown -->
      <v-row class="mb-3 align-center depth-control-row">
        <v-col cols="12" md="4">
          <div class="text-subtitle-1 font-weight-medium">Agent Templates</div>
          <div class="text-caption text-grey-darken-1">Detail level for templates</div>
        </v-col>
        <v-col cols="12" md="5">
          <v-select
            v-model="depthConfig.agent_template_detail"
            :items="agentTemplateOptions"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="updateEstimate"
            aria-label="Agent Templates depth setting"
          />
        </v-col>
        <v-col cols="12" md="3" class="text-right">
          <v-chip size="small" color="primary" variant="tonal">
            {{ (tokenEstimates.agent_template_detail || 0).toLocaleString() }} tokens
          </v-chip>
        </v-col>
      </v-row>

      <!-- 360 Memory Dropdown -->
      <v-row class="mb-3 align-center depth-control-row">
        <v-col cols="12" md="4">
          <div class="text-subtitle-1 font-weight-medium">360 Memory</div>
          <div class="text-caption text-grey-darken-1">Number of recent projects to include</div>
        </v-col>
        <v-col cols="12" md="5">
          <v-select
            v-model="depthConfig.memory_last_n_projects"
            :items="memoryOptions"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="updateEstimate"
            aria-label="360 Memory depth setting"
          />
        </v-col>
        <v-col cols="12" md="3" class="text-right">
          <v-chip size="small" color="primary" variant="tonal">
            {{ (tokenEstimates.memory_last_n_projects || 0).toLocaleString() }} tokens
          </v-chip>
        </v-col>
      </v-row>

      <!-- Git History Dropdown -->
      <v-row class="mb-3 align-center depth-control-row">
        <v-col cols="12" md="4">
          <div class="text-subtitle-1 font-weight-medium">Git History</div>
          <div class="text-caption text-grey-darken-1">Number of recent commits</div>
        </v-col>
        <v-col cols="12" md="5">
          <v-select
            v-model="depthConfig.git_commits"
            :items="gitOptions"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="updateEstimate"
            aria-label="Git History depth setting"
          />
        </v-col>
        <v-col cols="12" md="3" class="text-right">
          <v-chip size="small" color="primary" variant="tonal">
            {{ (tokenEstimates.git_commits || 0).toLocaleString() }} tokens
          </v-chip>
        </v-col>
      </v-row>

      <!-- Save Button -->
      <v-row class="mt-6">
        <v-col>
          <v-btn
            color="primary"
            :loading="saving"
            :disabled="saving"
            @click="saveDepthConfig"
            size="large"
          >
            <v-icon start>mdi-content-save</v-icon>
            Save Configuration
          </v-btn>
        </v-col>
      </v-row>
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

// Dropdown options
const productCoreOptions = [
  { title: 'Disabled (0 tokens)', value: false },
  { title: 'Enabled (~100 tokens)', value: true },
];

const visionOptions = [
  { title: 'None (0 tokens)', value: 'none' },
  { title: 'Light (~10K tokens)', value: 'light' },
  { title: 'Moderate (~17.5K tokens)', value: 'moderate' },
  { title: 'Heavy (~30K tokens)', value: 'heavy' },
];

const agentTemplateOptions = [
  { title: 'Type Only (~400 tokens)', value: 'type_only' },
  { title: 'Full (~2.4K tokens)', value: 'full' },
];

const memoryOptions = [
  { title: '1 project (~500 tokens)', value: 1 },
  { title: '3 projects (~1.5K tokens)', value: 3 },
  { title: '5 projects (~2.5K tokens)', value: 5 },
  { title: '10 projects (~5K tokens)', value: 10 },
];

const gitOptions = [
  { title: 'None (0 tokens)', value: 0 },
  { title: '5 commits (~250 tokens)', value: 5 },
  { title: '15 commits (~750 tokens)', value: 15 },
  { title: '25 commits (~1.25K tokens)', value: 25 },
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
.depth-control-row {
  padding-top: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}

.depth-control-row:last-of-type {
  border-bottom: none;
}

/* Mobile responsive adjustments */
@media (max-width: 600px) {
  .depth-control-row .text-right {
    text-align: left !important;
  }
}
</style>
