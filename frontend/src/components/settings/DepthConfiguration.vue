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

      <!-- Depth Controls Grid -->
      <v-row v-for="source in depthSources" :key="source.key" class="mb-3 align-center depth-control-row">
        <v-col cols="12" md="4">
          <div class="text-subtitle-1 font-weight-medium">{{ source.label }}</div>
          <div class="text-caption text-grey-darken-1">{{ source.description }}</div>
        </v-col>
        <v-col cols="12" md="5">
          <v-select
            v-model="depthConfig[source.key]"
            :items="source.options"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="updateEstimate"
            :aria-label="`${source.label} depth setting`"
          />
        </v-col>
        <v-col cols="12" md="3" class="text-right">
          <v-chip size="small" color="primary" variant="tonal">
            {{ (tokenEstimates[source.key] || 0).toLocaleString() }} tokens
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
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { DepthTokenEstimator, type DepthConfig } from '@/services/depthTokenEstimator';
import axios from 'axios';

// State
const depthConfig = ref<DepthConfig>({
  vision_chunking: 'moderate',
  memory_last_n_projects: 3,
  git_commits: 25,
  agent_template_detail: 'standard',
  tech_stack_sections: 'all',
  architecture_depth: 'overview',
  product_core_enabled: false,  // Handover 0316: New field
  testing_config_depth: 'none',  // Handover 0316: New field
});

const saving = ref(false);
const userTokenBudget = ref<number>(200000); // Default budget (matches backend)
const tokenEstimates = ref<Record<string, number>>({});
const totalTokens = ref(0);

// Depth sources configuration
// Maps to backend depth settings with user-friendly labels
const depthSources = [
  {
    key: 'vision_chunking' as keyof DepthConfig,
    label: 'Vision Documents',
    description: 'Chunking level for vision uploads',
    options: [
      { title: 'None (0 tokens)', value: 'none' },
      { title: 'Light (~10K tokens)', value: 'light' },
      { title: 'Moderate (~17.5K tokens)', value: 'moderate' },
      { title: 'Heavy (~30K tokens)', value: 'heavy' },
    ],
  },
  {
    key: 'memory_last_n_projects' as keyof DepthConfig,
    label: '360 Memory',
    description: 'Number of recent projects to include',
    options: [
      { title: '1 project (~500 tokens)', value: 1 },
      { title: '3 projects (~1.5K tokens)', value: 3 },
      { title: '5 projects (~2.5K tokens)', value: 5 },
      { title: '10 projects (~5K tokens)', value: 10 },
    ],
  },
  {
    key: 'git_commits' as keyof DepthConfig,
    label: 'Git History',
    description: 'Number of recent commits',
    options: [
      { title: '10 commits (~500 tokens)', value: 10 },
      { title: '25 commits (~1.25K tokens)', value: 25 },
      { title: '50 commits (~2.5K tokens)', value: 50 },
      { title: '100 commits (~5K tokens)', value: 100 },
    ],
  },
  {
    key: 'agent_template_detail' as keyof DepthConfig,
    label: 'Agent Templates',
    description: 'Detail level for templates',
    options: [
      { title: 'Minimal (~400 tokens)', value: 'minimal' },
      { title: 'Standard (~800 tokens)', value: 'standard' },
      { title: 'Full (~2.4K tokens)', value: 'full' },
    ],
  },
  {
    key: 'tech_stack_sections' as keyof DepthConfig,
    label: 'Tech Stack',
    description: 'Sections to include',
    options: [
      { title: 'Required only (~200 tokens)', value: 'required' },
      { title: 'All sections (~400 tokens)', value: 'all' },
    ],
  },
  {
    key: 'architecture_depth' as keyof DepthConfig,
    label: 'Architecture',
    description: 'Documentation depth',
    options: [
      { title: 'Overview (~300 tokens)', value: 'overview' },
      { title: 'Detailed (~1.5K tokens)', value: 'detailed' },
    ],
  },
  // Handover 0316: New context tools
  {
    key: 'product_core_enabled' as keyof DepthConfig,
    label: 'Product Core',
    description: 'Basic product information',
    options: [
      { title: 'Disabled (0 tokens)', value: false },
      { title: 'Enabled (~100 tokens)', value: true },
    ],
  },
  {
    key: 'testing_config_depth' as keyof DepthConfig,
    label: 'Testing Configuration',
    description: 'Quality standards and testing strategy',
    options: [
      { title: 'None (0 tokens)', value: 'none' },
      { title: 'Basic - Strategy + Coverage (~150 tokens)', value: 'basic' },
      { title: 'Full - All fields + Frameworks (~400 tokens)', value: 'full' },
    ],
  },
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
    depthConfig.value = response.data.depth_config;

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
