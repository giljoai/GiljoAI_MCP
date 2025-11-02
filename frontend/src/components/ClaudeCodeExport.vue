<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-text>
      <div class="d-flex align-center mb-3">
        <v-icon color="primary" size="large" class="mr-2">mdi-download</v-icon>
        <h3 class="text-h6 mb-0">Claude Code Agent Export</h3>
      </div>

      <!-- Info Alert -->
      <v-alert type="info" variant="tonal" class="mb-4">
        <div class="text-body-2">
          Export your agent templates as Claude Code agent definition files. Use the copy commands below to export directly from your Claude Code terminal for seamless path resolution.
        </div>
      </v-alert>

      <!-- Export Commands Section -->
      <div class="export-commands mb-4">
        <h4 class="text-subtitle-1 font-weight-medium mb-3">Export Commands</h4>

        <!-- Product Agents Command -->
        <v-card variant="outlined" class="mb-3">
          <v-card-text class="d-flex align-center justify-between">
            <div class="flex-grow-1">
              <div class="text-subtitle-2 font-weight-medium">Product Agents</div>
              <div class="text-body-2 text-medium-emphasis mb-2">
                Install agents in your product's .claude/agents folder
              </div>
              <div v-if="!selectedProduct?.project_path" class="text-caption text-error">
                <v-icon size="small" class="mr-1">mdi-alert-circle-outline</v-icon>
                Product path not configured. Set up your product path first.
              </div>
            </div>
            <v-btn
              color="primary"
              variant="outlined"
              :disabled="!selectedProduct?.project_path"
              @click="copyProductCommand"
              prepend-icon="mdi-content-copy"
            >
              Copy Command
            </v-btn>
          </v-card-text>
        </v-card>

        <!-- Personal Agents Command -->
        <v-card variant="outlined" class="mb-3">
          <v-card-text class="d-flex align-center justify-between">
            <div class="flex-grow-1">
              <div class="text-subtitle-2 font-weight-medium">Personal Agents</div>
              <div class="text-body-2 text-medium-emphasis">
                Install agents in your user profile (~/.claude/agents)
              </div>
            </div>
            <v-btn
              color="primary"
              variant="outlined"
              @click="copyPersonalCommand"
              prepend-icon="mdi-content-copy"
            >
              Copy Command
            </v-btn>
          </v-card-text>
        </v-card>
      </div>

      <!-- Product Selection (if multiple products) -->
      <div v-if="availableProducts.length > 1" class="mb-4">
        <h4 class="text-subtitle-1 font-weight-medium mb-2">Select Product</h4>
        <v-select
          v-model="selectedProduct"
          :items="availableProducts"
          item-title="name"
          item-value="id"
          label="Product"
          return-object
          variant="outlined"
          :disabled="loading"
        >
          <template #item="{ props, item }">
            <v-list-item v-bind="props">
              <template #append>
                <v-icon
                  v-if="!item.raw.project_path"
                  color="warning"
                  size="small"
                >
                  mdi-alert-circle-outline
                </v-icon>
              </template>
            </v-list-item>
          </template>
        </v-select>
      </div>

      <!-- Template Summary -->
      <div v-if="activeTemplates.length > 0" class="mb-4">
        <h4 class="text-subtitle-1 font-weight-medium mb-2">
          Active Templates ({{ activeTemplates.length }})
        </h4>
        <v-chip-group column>
          <v-chip
            v-for="template in activeTemplates"
            :key="template.id"
            size="small"
            label
            :prepend-icon="getTemplateIcon(template.role)"
          >
            {{ template.name }}
          </v-chip>
        </v-chip-group>
      </div>

      <!-- No Templates Message -->
      <v-alert v-else type="warning" variant="tonal" class="mb-4">
        No active templates available for export. Please activate at least one template in the
        Agent Templates tab.
      </v-alert>

      <!-- Context Budget Warning -->
      <v-alert type="warning" variant="tonal" density="compact" class="mb-4" icon="mdi-alert-circle-outline">
        <div class="text-body-2">
          <strong>Context Budget Recommendation:</strong> Export no more than 8 agents maximum.
          Each agent description consumes context budget, reducing available tokens for your
          project. Claude Code recommends 6-8 agents for optimal performance.
        </div>
      </v-alert>

      <!-- Usage Instructions -->
      <v-alert type="info" variant="tonal" class="mb-4" icon="mdi-information-outline">
        <div class="text-body-2">
          <strong>How to use:</strong>
          <ol class="ml-4 mt-2">
            <li>Click "Copy Command" above</li>
            <li>Paste the command in your Claude Code terminal</li>
            <li>Agents will be exported to the appropriate directory</li>
          </ol>
        </div>
      </v-alert>

      <!-- Copy Feedback -->
      <v-snackbar v-model="showCopyFeedback" timeout="3000" color="success">
        <v-icon class="mr-2">mdi-check-circle</v-icon>
        {{ copyFeedbackMessage }}
      </v-snackbar>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '@/services/api'

// State
const selectedProduct = ref(null)
const availableProducts = ref([])
const activeTemplates = ref([])
const loading = ref(false)
const showCopyFeedback = ref(false)
const copyFeedbackMessage = ref('')

// Template role icon mapping
const roleIcons = {
  orchestrator: 'mdi-connection',
  analyzer: 'mdi-magnify',
  implementor: 'mdi-code-braces',
  tester: 'mdi-test-tube',
  documenter: 'mdi-file-document-edit',
  reviewer: 'mdi-eye-check',
  default: 'mdi-robot',
}

// Methods
function getTemplateIcon(role) {
  return roleIcons[role?.toLowerCase()] || roleIcons.default
}

function generateProductCommand() {
  if (!selectedProduct.value?.project_path) {
    return 'export_agents # Error: No product path configured'
  }
  return `export_agents --product-path "${selectedProduct.value.project_path}/.claude/agents"`
}

function generatePersonalCommand() {
  return 'export_agents --personal'
}

async function copyProductCommand() {
  const command = generateProductCommand()
  try {
    await navigator.clipboard.writeText(command)
    showCopyFeedback.value = true
    copyFeedbackMessage.value = 'Product command copied to clipboard!'
  } catch (error) {
    console.error('Failed to copy command:', error)
    showCopyFeedback.value = true
    copyFeedbackMessage.value = 'Failed to copy command'
  }
}

async function copyPersonalCommand() {
  const command = generatePersonalCommand()
  try {
    await navigator.clipboard.writeText(command)
    showCopyFeedback.value = true
    copyFeedbackMessage.value = 'Personal command copied to clipboard!'
  } catch (error) {
    console.error('Failed to copy command:', error)
    showCopyFeedback.value = true
    copyFeedbackMessage.value = 'Failed to copy command'
  }
}

async function loadActiveTemplates() {
  try {
    loading.value = true
    const response = await api.templates.list({ is_active: true })
    activeTemplates.value = response.data || []
    console.log('[CLAUDE EXPORT] Loaded active templates:', activeTemplates.value.length)
  } catch (error) {
    console.error('[CLAUDE EXPORT] Failed to load templates:', error)
    activeTemplates.value = []
  } finally {
    loading.value = false
  }
}

async function loadProducts() {
  try {
    loading.value = true
    const response = await api.products.list()
    availableProducts.value = response.data || []

    // Auto-select first product or active product
    if (availableProducts.value.length > 0) {
      const activeProduct = availableProducts.value.find(p => p.is_active)
      selectedProduct.value = activeProduct || availableProducts.value[0]
    }

    console.log('[CLAUDE EXPORT] Loaded products:', availableProducts.value.length)
  } catch (error) {
    console.error('[CLAUDE EXPORT] Failed to load products:', error)
    availableProducts.value = []
  } finally {
    loading.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadActiveTemplates()
  loadProducts()
})
</script>

<style scoped>
code {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.875em;
}

.export-commands {
  border-radius: 8px;
}

ol {
  padding-left: 20px;
}

li {
  margin-bottom: 4px;
}
</style><template>
  <v-card variant="outlined" class="mb-4">
    <v-card-text>
      <div class="d-flex align-center mb-3">
        <v-icon color="primary" size="large" class="mr-2">mdi-download</v-icon>
        <h3 class="text-h6 mb-0">Claude Code Agent Export</h3>
      </div>

      <!-- Info Alert -->
      <v-alert type="info" variant="tonal" class="mb-4">
        <div class="text-body-2">
          Export your agent templates as Claude Code agent definition files. Use the copy commands below to export directly from your Claude Code terminal for seamless path resolution.
        </div>
      </v-alert>

      <!-- Export Commands Section -->
      <div class="export-commands mb-4">
        <h4 class="text-subtitle-1 font-weight-medium mb-3">Export Commands</h4>

        <!-- Product Agents Command -->
        <v-card variant="outlined" class="mb-3">
          <v-card-text class="d-flex align-center justify-between">
            <div class="flex-grow-1">
              <div class="text-subtitle-2 font-weight-medium">Product Agents</div>
              <div class="text-body-2 text-medium-emphasis mb-2">
                Install agents in your product's .claude/agents folder
              </div>
              <div v-if="!selectedProduct?.project_path" class="text-caption text-error">
                <v-icon size="small" class="mr-1">mdi-alert-circle-outline</v-icon>
                Product path not configured. Set up your product path first.
              </div>
            </div>
            <v-btn
              color="primary"
              variant="outlined"
              :disabled="!selectedProduct?.project_path"
              @click="copyProductCommand"
              prepend-icon="mdi-content-copy"
            >
              Copy Command
            </v-btn>
          </v-card-text>
        </v-card>

        <!-- Personal Agents Command -->
        <v-card variant="outlined" class="mb-3">
          <v-card-text class="d-flex align-center justify-between">
            <div class="flex-grow-1">
              <div class="text-subtitle-2 font-weight-medium">Personal Agents</div>
              <div class="text-body-2 text-medium-emphasis">
                Install agents in your user profile (~/.claude/agents)
              </div>
            </div>
            <v-btn
              color="primary"
              variant="outlined"
              @click="copyPersonalCommand"
              prepend-icon="mdi-content-copy"
            >
              Copy Command
            </v-btn>
          </v-card-text>
        </v-card>
      </div>

      <!-- Product Selection (if multiple products) -->
      <div v-if="availableProducts.length > 1" class="mb-4">
        <h4 class="text-subtitle-1 font-weight-medium mb-2">Select Product</h4>
        <v-select
          v-model="selectedProduct"
          :items="availableProducts"
          item-title="name"
          item-value="id"
          label="Product"
          return-object
          variant="outlined"
          :disabled="loading"
        >
          <template #item="{ props, item }">
            <v-list-item v-bind="props">
              <template #append>
                <v-icon
                  v-if="!item.raw.project_path"
                  color="warning"
                  size="small"
                >
                  mdi-alert-circle-outline
                </v-icon>
              </template>
            </v-list-item>
          </template>
        </v-select>
      </div>

      <!-- Template Summary -->
      <div v-if="activeTemplates.length > 0" class="mb-4">
        <h4 class="text-subtitle-1 font-weight-medium mb-2">
          Active Templates ({{ activeTemplates.length }})
        </h4>
        <v-chip-group column>
          <v-chip
            v-for="template in activeTemplates"
            :key="template.id"
            size="small"
            label
            :prepend-icon="getTemplateIcon(template.role)"
          >
            {{ template.name }}
          </v-chip>
        </v-chip-group>
      </div>

      <!-- No Templates Message -->
      <v-alert v-else type="warning" variant="tonal" class="mb-4">
        No active templates available for export. Please activate at least one template in the
        Agent Templates tab.
      </v-alert>

      <!-- Context Budget Warning -->
      <v-alert type="warning" variant="tonal" density="compact" class="mb-4" icon="mdi-alert-circle-outline">
        <div class="text-body-2">
          <strong>Context Budget Recommendation:</strong> Export no more than 8 agents maximum.
          Each agent description consumes context budget, reducing available tokens for your
          project. Claude Code recommends 6-8 agents for optimal performance.
        </div>
      </v-alert>

      <!-- Usage Instructions -->
      <v-alert type="info" variant="tonal" class="mb-4" icon="mdi-information-outline">
        <div class="text-body-2">
          <strong>How to use:</strong>
          <ol class="ml-4 mt-2">
            <li>Click "Copy Command" above</li>
            <li>Paste the command in your Claude Code terminal</li>
            <li>Agents will be exported to the appropriate directory</li>
          </ol>
        </div>
      </v-alert>

      <!-- Copy Feedback -->
      <v-snackbar v-model="showCopyFeedback" timeout="3000" color="success">
        <v-icon class="mr-2">mdi-check-circle</v-icon>
        {{ copyFeedbackMessage }}
      </v-snackbar>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '@/services/api'

// State
const selectedProduct = ref(null)
const availableProducts = ref([])
const activeTemplates = ref([])
const loading = ref(false)
const showCopyFeedback = ref(false)
const copyFeedbackMessage = ref('')

// Template role icon mapping
const roleIcons = {
  orchestrator: 'mdi-connection',
  analyzer: 'mdi-magnify',
  implementor: 'mdi-code-braces',
  tester: 'mdi-test-tube',
  documenter: 'mdi-file-document-edit',
  reviewer: 'mdi-eye-check',
  default: 'mdi-robot',
}

// Methods
function getTemplateIcon(role) {
  return roleIcons[role?.toLowerCase()] || roleIcons.default
}

function generateProductCommand() {
  if (!selectedProduct.value?.project_path) {
    return 'export_agents # Error: No product path configured'
  }
  return `export_agents --product-path "${selectedProduct.value.project_path}/.claude/agents"`
}

function generatePersonalCommand() {
  return 'export_agents --personal'
}

async function copyProductCommand() {
  const command = generateProductCommand()
  try {
    await navigator.clipboard.writeText(command)
    showCopyFeedback.value = true
    copyFeedbackMessage.value = 'Product command copied to clipboard!'
  } catch (error) {
    console.error('Failed to copy command:', error)
    showCopyFeedback.value = true
    copyFeedbackMessage.value = 'Failed to copy command'
  }
}

async function copyPersonalCommand() {
  const command = generatePersonalCommand()
  try {
    await navigator.clipboard.writeText(command)
    showCopyFeedback.value = true
    copyFeedbackMessage.value = 'Personal command copied to clipboard!'
  } catch (error) {
    console.error('Failed to copy command:', error)
    showCopyFeedback.value = true
    copyFeedbackMessage.value = 'Failed to copy command'
  }
}

async function loadActiveTemplates() {
  try {
    loading.value = true
    const response = await api.templates.list({ is_active: true })
    activeTemplates.value = response.data || []
    console.log('[CLAUDE EXPORT] Loaded active templates:', activeTemplates.value.length)
  } catch (error) {
    console.error('[CLAUDE EXPORT] Failed to load templates:', error)
    activeTemplates.value = []
  } finally {
    loading.value = false
  }
}

async function loadProducts() {
  try {
    loading.value = true
    const response = await api.products.list()
    availableProducts.value = response.data || []

    // Auto-select first product or active product
    if (availableProducts.value.length > 0) {
      const activeProduct = availableProducts.value.find(p => p.is_active)
      selectedProduct.value = activeProduct || availableProducts.value[0]
    }

    console.log('[CLAUDE EXPORT] Loaded products:', availableProducts.value.length)
  } catch (error) {
    console.error('[CLAUDE EXPORT] Failed to load products:', error)
    availableProducts.value = []
  } finally {
    loading.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadActiveTemplates()
  loadProducts()
})
</script>

<style scoped>
code {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.875em;
}

.export-commands {
  border-radius: 8px;
}

ol {
  padding-left: 20px;
}

li {
  margin-bottom: 4px;
}
</style>
