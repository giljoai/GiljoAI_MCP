<template>
  <v-container>
    <!-- Page Header -->
    <h1 class="text-h4 mb-2">My Settings</h1>
    <p class="text-subtitle-1 mb-4">Manage your personal preferences</p>

    <!-- Settings Tabs -->
    <v-tabs v-model="activeTab" class="mb-6">
      <v-tab value="general">
        <v-icon start>mdi-cog</v-icon>
        General
      </v-tab>
      <v-tab value="appearance">
        <v-icon start>mdi-palette</v-icon>
        Appearance
      </v-tab>
      <v-tab value="notifications">
        <v-icon start>mdi-bell</v-icon>
        Notifications
      </v-tab>
      <v-tab value="templates">
        <template #prepend>
          <v-img :src="theme.global.current.value.dark ? '/giljo_YW_Face.svg' : '/icons/Giljo_BY_Face.svg'" width="20" height="20" style="margin-right: 3px;" />
        </template>
        Agent Templates
      </v-tab>
      <v-tab value="api">
        <v-icon start>mdi-api</v-icon>
        API and Integrations
      </v-tab>
    </v-tabs>

    <!-- Tab Content -->
    <v-window v-model="activeTab">
      <!-- General Settings -->
      <v-window-item value="general">
        <v-card data-test="general-settings">
          <v-card-title>General Settings</v-card-title>
          <v-card-text>
            <v-form ref="generalForm">
              <v-text-field
                v-model="settings.general.projectName"
                label="Project Name"
                variant="outlined"
                hint="The name of your orchestrator project"
                persistent-hint
                data-test="project-name-field"
              />
            </v-form>

            <v-divider class="my-6"></v-divider>

            <div class="text-h6 mb-4">
              <v-icon start>mdi-priority-high</v-icon>
              Field Priority for AI Agents
            </div>

            <v-alert type="info" variant="tonal" density="compact" class="mb-4">
              Controls which product configuration fields are prioritized when generating
              AI agent missions. Fields are included top-to-bottom until token budget ({{ tokenBudget }}) is reached.
            </v-alert>

            <!-- Priority 1 Card -->
            <v-card variant="outlined" class="mb-4">
              <v-card-title class="d-flex align-center">
                <v-icon color="error" start>mdi-numeric-1-circle</v-icon>
                Priority 1 - Always Included
              </v-card-title>
              <v-card-text>
                <draggable
                  v-model="priority1Fields"
                  group="fields"
                  item-key="id"
                  handle=".drag-handle"
                  @change="onPriorityChange"
                  class="d-flex flex-wrap"
                >
                  <template #item="{ element }">
                    <v-chip
                      class="ma-1 drag-handle"
                      closable
                      @click:close="removeField(element, 'priority_1')"
                      style="cursor: move;"
                      color="error"
                      variant="outlined"
                    >
                      <v-icon start size="small">mdi-drag-vertical</v-icon>
                      {{ getFieldLabel(element) }}
                    </v-chip>
                  </template>
                </draggable>
                <div v-if="priority1Fields.length === 0" class="text-caption text-medium-emphasis">
                  No fields assigned to Priority 1
                </div>
              </v-card-text>
            </v-card>

            <!-- Priority 2 Card -->
            <v-card variant="outlined" class="mb-4">
              <v-card-title class="d-flex align-center">
                <v-icon color="warning" start>mdi-numeric-2-circle</v-icon>
                Priority 2 - High Priority
              </v-card-title>
              <v-card-text>
                <draggable
                  v-model="priority2Fields"
                  group="fields"
                  item-key="id"
                  handle=".drag-handle"
                  @change="onPriorityChange"
                  class="d-flex flex-wrap"
                >
                  <template #item="{ element }">
                    <v-chip
                      class="ma-1 drag-handle"
                      closable
                      @click:close="removeField(element, 'priority_2')"
                      style="cursor: move;"
                      color="warning"
                      variant="outlined"
                    >
                      <v-icon start size="small">mdi-drag-vertical</v-icon>
                      {{ getFieldLabel(element) }}
                    </v-chip>
                  </template>
                </draggable>
                <div v-if="priority2Fields.length === 0" class="text-caption text-medium-emphasis">
                  No fields assigned to Priority 2
                </div>
              </v-card-text>
            </v-card>

            <!-- Priority 3 Card -->
            <v-card variant="outlined" class="mb-4">
              <v-card-title class="d-flex align-center">
                <v-icon color="info" start>mdi-numeric-3-circle</v-icon>
                Priority 3 - Medium Priority
              </v-card-title>
              <v-card-text>
                <draggable
                  v-model="priority3Fields"
                  group="fields"
                  item-key="id"
                  handle=".drag-handle"
                  @change="onPriorityChange"
                  class="d-flex flex-wrap"
                >
                  <template #item="{ element }">
                    <v-chip
                      class="ma-1 drag-handle"
                      closable
                      @click:close="removeField(element, 'priority_3')"
                      style="cursor: move;"
                      color="info"
                      variant="outlined"
                    >
                      <v-icon start size="small">mdi-drag-vertical</v-icon>
                      {{ getFieldLabel(element) }}
                    </v-chip>
                  </template>
                </draggable>
                <div v-if="priority3Fields.length === 0" class="text-caption text-medium-emphasis">
                  No fields assigned to Priority 3
                </div>
              </v-card-text>
            </v-card>

            <!-- Token Budget Indicator -->
            <v-card v-if="activeProductTokens" variant="tonal" :color="tokenIndicatorColor" class="mb-4">
              <v-card-text>
                <div class="d-flex align-center justify-space-between">
                  <div>
                    <div class="text-caption">Estimated Context Size for: {{ activeProductName }}</div>
                    <div class="text-h6">{{ estimatedTokens }} / {{ tokenBudget }} tokens</div>
                  </div>
                  <v-progress-circular
                    :model-value="tokenPercentage"
                    :color="tokenIndicatorColor"
                    size="64"
                  >
                    {{ tokenPercentage }}%
                  </v-progress-circular>
                </div>
              </v-card-text>
            </v-card>

            <!-- No Active Product Message -->
            <v-alert v-else type="info" variant="tonal" class="mb-4">
              <v-icon start>mdi-information</v-icon>
              No active product / Token estimation unavailable
            </v-alert>

            <!-- Action Buttons -->
            <div class="d-flex gap-2 mb-4">
              <v-btn
                color="primary"
                variant="flat"
                @click="saveFieldPriority"
                :loading="savingFieldPriority"
                :disabled="!fieldPriorityHasChanges"
              >
                <v-icon start>mdi-content-save</v-icon>
                Save Field Priority
              </v-btn>

              <v-btn
                variant="outlined"
                @click="resetFieldPriorityToDefaults"
                :disabled="savingFieldPriority"
              >
                <v-icon start>mdi-restore</v-icon>
                Reset to Defaults
              </v-btn>
            </div>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="resetGeneralSettings" data-test="reset-general-btn">Reset</v-btn>
            <v-btn color="primary" variant="flat" @click="saveGeneralSettings" data-test="save-general-btn">Save Changes</v-btn>
          </v-card-actions>
        </v-card>
      </v-window-item>

      <!-- Appearance Settings -->
      <v-window-item value="appearance">
        <v-card data-test="appearance-settings">
          <v-card-title>Appearance Settings</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="6">
                <h3 class="text-h6 mb-4">Theme</h3>
                <v-radio-group v-model="settings.appearance.theme" data-test="theme-selector">
                  <v-radio label="Dark Theme" value="dark" />
                  <v-radio label="Light Theme" value="light" />
                  <v-radio label="System Default" value="system" />
                </v-radio-group>
              </v-col>

              <v-col cols="12" md="6">
                <h3 class="text-h6 mb-4">Mascot Preferences</h3>
                <v-switch
                  v-model="settings.appearance.showMascot"
                  label="Show mascot animations"
                  color="primary"
                  data-test="mascot-toggle"
                />
                <v-switch
                  v-model="settings.appearance.useBlueVariant"
                  label="Use blue mascot variant"
                  color="primary"
                />
              </v-col>
            </v-row>

            <v-divider class="my-6" />

            <h3 class="text-h6 mb-4">Display Options</h3>
            <v-row>
              <v-col cols="12" md="6">
                <v-switch
                  v-model="settings.appearance.compactMode"
                  label="Compact mode"
                  color="primary"
                />
                <v-switch
                  v-model="settings.appearance.showAnimations"
                  label="Enable animations"
                  color="primary"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-switch
                  v-model="settings.appearance.showTooltips"
                  label="Show tooltips"
                  color="primary"
                />
                <v-switch
                  v-model="settings.appearance.highContrast"
                  label="High contrast mode"
                  color="primary"
                />
              </v-col>
            </v-row>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="resetAppearanceSettings" data-test="reset-appearance-btn">Reset</v-btn>
            <v-btn color="primary" variant="flat" @click="saveAppearanceSettings" data-test="save-appearance-btn"
              >Save Changes</v-btn
            >
          </v-card-actions>
        </v-card>
      </v-window-item>

      <!-- Notification Settings -->
      <v-window-item value="notifications">
        <v-card data-test="notification-settings">
          <v-card-title>Notification Settings</v-card-title>
          <v-card-text>
            <h3 class="text-h6 mb-4">Message Notifications</h3>
            <v-switch
              v-model="settings.notifications.newMessages"
              label="New message alerts"
              color="primary"
              data-test="new-messages-toggle"
            />
            <v-switch
              v-model="settings.notifications.urgentOnly"
              label="Urgent messages only"
              color="primary"
              :disabled="!settings.notifications.newMessages"
            />

            <v-divider class="my-6" />

            <h3 class="text-h6 mb-4">Agent Notifications</h3>
            <v-switch
              v-model="settings.notifications.agentStatus"
              label="Agent status changes"
              color="primary"
            />
            <v-switch
              v-model="settings.notifications.agentErrors"
              label="Agent errors"
              color="primary"
            />

            <v-divider class="my-6" />

            <h3 class="text-h6 mb-4">Task Notifications</h3>
            <v-switch
              v-model="settings.notifications.taskComplete"
              label="Task completions"
              color="primary"
            />
            <v-switch
              v-model="settings.notifications.taskOverdue"
              label="Overdue task alerts"
              color="primary"
            />

            <v-divider class="my-6" />

            <h3 class="text-h6 mb-4">Notification Display</h3>
            <v-select
              v-model="settings.notifications.position"
              :items="[
                'top-left',
                'top-center',
                'top-right',
                'bottom-left',
                'bottom-center',
                'bottom-right',
              ]"
              label="Notification position"
              variant="outlined"
              data-test="notification-position-select"
            />
            <v-slider
              v-model="settings.notifications.duration"
              :min="2"
              :max="10"
              :step="1"
              label="Display duration (seconds)"
              thumb-label
              class="mt-4"
            />
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="resetNotificationSettings" data-test="reset-notification-btn">Reset</v-btn>
            <v-btn color="primary" variant="flat" @click="saveNotificationSettings" data-test="save-notification-btn"
              >Save Changes</v-btn
            >
          </v-card-actions>
        </v-card>
      </v-window-item>

      <!-- Templates -->
      <v-window-item value="templates">
        <TemplateManager />
      </v-window-item>

      <!-- API Configuration -->
      <v-window-item value="api">
        <v-card>
          <v-card-title>API and Integrations</v-card-title>
          <v-card-subtitle>Configure API settings and MCP tool integrations</v-card-subtitle>
          <v-card-text>
            <v-tabs
              v-model="apiSubTab"
              class="api-subtabs"
              selected-class="bg-primary"
              show-arrows
              hide-slider
            >
              <v-tab value="api-keys"><v-icon start>mdi-key-variant</v-icon>API Keys</v-tab>
              <v-tab value="mcp-config">
                <template #prepend>
                  <v-img :src="theme.global.current.value.dark ? '/Giljo_gray_Face.svg' : '/icons/Giljo_BY_Face.svg'" width="20" height="20" style="margin-right: 3px;" />
                </template>
                MCP Configuration
              </v-tab>
              <v-tab value="integrations"><v-icon start>mdi-puzzle</v-icon>Integrations</v-tab>
            </v-tabs>
            <v-divider class="mb-4" thickness="3" style="border-color: #FFFFFF !important; opacity: 1 !important;"></v-divider>

            <v-window v-model="apiSubTab" :theme="theme.global.name.value">
              <!-- API Keys Tab -->
              <v-window-item value="api-keys">
                <ApiKeyManager />
              </v-window-item>

              <!-- MCP Configuration Tab -->
              <v-window-item value="mcp-config">
                <div class="mb-2">
                  <div class="d-flex align-center" style="padding-left: 10px;">
                    <v-img :src="theme.global.current.value.dark ? '/giljo_YW_Face.svg' : '/icons/Giljo_BY_Face.svg'" width="28" height="28" class="mr-2" cover style="flex: 0 0 28px;" />
                    <h3 class="text-h6 mb-0">AI Tool Self-Configuration</h3>
                  </div>
                </div>
                <p class="text-body-2 text-medium-emphasis mb-4" style="padding-left: 10px;">
                  Use the wizard to generate a tool-specific prompt that configures your AI tool automatically.
                  For tools without wizard support, use manual configuration.
                </p>

                <v-card variant="outlined" class="mb-4 pa-4">
                  <AiToolConfigWizard />
                </v-card>

                <!-- Manual Configuration (fallback) -->
                <v-card variant="outlined" class="mb-6">
                  <v-card-text>
                    <div class="d-flex align-center mb-2">
                      <v-icon color="secondary" size="large" class="mr-2">mdi-cog</v-icon>
                      <h4 class="text-h6 mb-0">Manual AI Tool Configuration</h4>
                    </div>
                    <p class="text-body-2 text-medium-emphasis mb-0">
                      Manual configuration for AI tools that don't support automatic setup.
                      Generate and copy configuration snippets.
                    </p>
                    <v-btn
                      color="primary"
                      size="large"
                      block
                      @click="openManualConfig"
                      aria-label="Open manual AI tool configuration dialog"
                      class="mt-3"
                    >
                      Open Manual Configuration
                    </v-btn>
                  </v-card-text>
                </v-card>
              </v-window-item>

              <!-- Integrations Tab -->
              <v-window-item value="integrations">
                <h3 class="text-h6 mb-4">MCP Integrations</h3>
                <v-card variant="outlined" class="mb-4">
                  <v-list>
                    <v-list-item>
                      <template #prepend>
                        <v-avatar size="40" rounded="0">
                          <v-img src="/Serena.png" alt="Serena MCP" />
                        </v-avatar>
                      </template>

                      <v-list-item-title class="text-h6 mb-1">Serena MCP</v-list-item-title>
                      <v-list-item-subtitle>
                        Enabling adds Serena tool instructions to agent prompts. Disabling removes them
                        from agent tool startup. (Currently only Claude Code)
                      </v-list-item-subtitle>

                      <template #append>
                        <v-switch
                          v-model="serenaEnabled"
                          @update:model-value="toggleSerena"
                          color="primary"
                          :loading="toggling"
                          hide-details
                          inset
                          class="serena-toggle"
                        />
                      </template>
                    </v-list-item>
                  </v-list>
                </v-card>

                <v-alert type="info" variant="tonal" class="mb-4">
                  Serena MCP must be installed separately and configured in your coding tool (e.g.,
                  Claude Code). This toggle only controls whether Serena instructions are included in
                  agent prompts.
                </v-alert>

                <!-- Claude Code Agent Export -->
                <h3 class="text-h6 mb-4 mt-6">Claude Code Agent Export</h3>
                <ClaudeCodeExport />
              </v-window-item>
            </v-window>
          </v-card-text>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- Manual Configuration Dialog -->
    <v-dialog v-model="showManualConfigDialog" max-width="900" scrollable>
      <McpConfigComponent @close="showManualConfigDialog = false" />
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { useTheme } from 'vuetify'
import { useRouter } from 'vue-router'
import TemplateManager from '@/components/TemplateManager.vue'
import ApiKeyManager from '@/components/ApiKeyManager.vue'
import McpConfigComponent from '@/components/McpConfigComponent.vue'
import AiToolConfigWizard from '@/components/AiToolConfigWizard.vue'
import ClaudeCodeExport from '@/components/ClaudeCodeExport.vue'
import draggable from 'vuedraggable'
import setupService from '@/services/setupService'
import api from '@/services/api'

// Stores and Theme
const settingsStore = useSettingsStore()
const theme = useTheme()
const router = useRouter()

// State
const activeTab = ref('general')
const apiSubTab = ref('api-keys')
const generalForm = ref(null)
const serenaEnabled = ref(false)
const toggling = ref(false)
const showManualConfigDialog = ref(false)

// Field Priority Configuration state (Handover 0048)
const priority1Fields = ref([])
const priority2Fields = ref([])
const priority3Fields = ref([])
const tokenBudget = ref(2000)
const savingFieldPriority = ref(false)
const fieldPriorityHasChanges = ref(false)

// Real-time token calculation state (Handover 0049)
const activeProductTokens = ref(null)
const loadingTokenEstimate = ref(false)

// Field labels mapping for display
const fieldLabels = {
  'tech_stack.languages': 'Programming Languages',
  'tech_stack.backend': 'Backend Stack',
  'tech_stack.frontend': 'Frontend Stack',
  'tech_stack.database': 'Databases',
  'tech_stack.infrastructure': 'Infrastructure',
  'architecture.pattern': 'Architecture Pattern',
  'architecture.api_style': 'API Style',
  'architecture.design_patterns': 'Design Patterns',
  'architecture.notes': 'Architecture Notes',
  'features.core': 'Core Features',
  'test_config.strategy': 'Testing Strategy',
  'test_config.frameworks': 'Testing Frameworks',
  'test_config.coverage_target': 'Coverage Target',
}

// Settings object
const settings = ref({
  general: {
    projectName: 'GiljoAI MCP Orchestrator',
  },
  appearance: {
    theme: 'dark',
    showMascot: true,
    useBlueVariant: false,
    compactMode: false,
    showAnimations: true,
    showTooltips: true,
    highContrast: false,
  },
  notifications: {
    newMessages: true,
    urgentOnly: false,
    agentStatus: true,
    agentErrors: true,
    taskComplete: true,
    taskOverdue: true,
    position: 'bottom-right',
    duration: 5,
  },
})

// Methods
async function saveGeneralSettings() {
  try {
    await settingsStore.updateSettings({ general: settings.value.general })
    console.log('General settings saved')
  } catch (error) {
    console.error('Failed to save general settings:', error)
  }
}

async function saveAppearanceSettings() {
  try {
    // Apply theme immediately
    if (settings.value.appearance.theme !== 'system') {
      theme.global.name.value = settings.value.appearance.theme  // TODO: Upgrade to theme.change() after Vuetify 3.7+
      document.documentElement.setAttribute('data-theme', settings.value.appearance.theme)
      localStorage.setItem('theme-preference', settings.value.appearance.theme)
    }

    await settingsStore.updateSettings({ appearance: settings.value.appearance })
    console.log('Appearance settings saved')
  } catch (error) {
    console.error('Failed to save appearance settings:', error)
  }
}

async function saveNotificationSettings() {
  try {
    await settingsStore.updateSettings({ notifications: settings.value.notifications })
    console.log('Notification settings saved')
  } catch (error) {
    console.error('Failed to save notification settings:', error)
  }
}

function resetGeneralSettings() {
  settings.value.general = {
    projectName: 'GiljoAI MCP Orchestrator',
  }
}

function resetAppearanceSettings() {
  settings.value.appearance = {
    theme: 'dark',
    showMascot: true,
    useBlueVariant: false,
    compactMode: false,
    showAnimations: true,
    showTooltips: true,
    highContrast: false,
  }
}

function resetNotificationSettings() {
  settings.value.notifications = {
    newMessages: true,
    urgentOnly: false,
    agentStatus: true,
    agentErrors: true,
    taskComplete: true,
    taskOverdue: true,
    position: 'bottom-right',
    duration: 5,
  }
}

// AI Tool Configuration Methods

function openManualConfig() {
  // Show the manual config dialog
  showManualConfigDialog.value = true
  console.log('[USER SETTINGS] Opening manual configuration dialog')
}

// Serena MCP Methods
async function checkSerenaStatus() {
  try {
    const status = await setupService.getSerenaStatus()
    serenaEnabled.value = status.enabled || false
    console.log('[USER SETTINGS] Serena prompt injection status:', serenaEnabled.value)
  } catch (error) {
    console.error('[USER SETTINGS] Failed to check Serena status:', error)
    serenaEnabled.value = false
  }
}

async function toggleSerena(enabled) {
  toggling.value = true
  try {
    const result = await setupService.toggleSerena(enabled)
    if (result.success) {
      serenaEnabled.value = result.enabled
      console.log('[USER SETTINGS] Serena prompt injection toggled:', result.enabled)
    } else {
      // Revert on failure
      serenaEnabled.value = !enabled
      console.error('[USER SETTINGS] Failed to toggle Serena:', result.message)
    }
  } catch (error) {
    console.error('[USER SETTINGS] Error toggling Serena:', error)
    // Revert on error
    serenaEnabled.value = !enabled
  } finally {
    toggling.value = false
  }
}

// Real-time token calculation computed properties (Handover 0049)
const activeProductName = computed(() => {
  return activeProductTokens.value?.name || 'No Active Product'
})

// Field Priority Configuration computed properties (Handover 0048)
const estimatedTokens = computed(() => {
  // Use real-time data from active product if available (Handover 0049)
  if (activeProductTokens.value?.total_tokens) {
    return activeProductTokens.value.total_tokens
  }

  // Fallback to generic calculation
  const p1 = priority1Fields.value.length * 50
  const p2 = priority2Fields.value.length * 30
  const p3 = priority3Fields.value.length * 20
  return p1 + p2 + p3 + 500
})

const tokenPercentage = computed(() => {
  return Math.min(Math.round((estimatedTokens.value / tokenBudget.value) * 100), 100)
})

const tokenIndicatorColor = computed(() => {
  if (tokenPercentage.value > 90) return 'error'
  if (tokenPercentage.value > 70) return 'warning'
  return 'success'
})

// Field Priority Configuration Methods (Handover 0048)
function getFieldLabel(fieldPath) {
  return fieldLabels[fieldPath] || fieldPath
}

function onPriorityChange() {
  fieldPriorityHasChanges.value = true
}

function removeField(field, priority) {
  if (priority === 'priority_1') {
    const index = priority1Fields.value.indexOf(field)
    if (index > -1) priority1Fields.value.splice(index, 1)
  } else if (priority === 'priority_2') {
    const index = priority2Fields.value.indexOf(field)
    if (index > -1) priority2Fields.value.splice(index, 1)
  } else if (priority === 'priority_3') {
    const index = priority3Fields.value.indexOf(field)
    if (index > -1) priority3Fields.value.splice(index, 1)
  }
  fieldPriorityHasChanges.value = true
}

async function saveFieldPriority() {
  savingFieldPriority.value = true
  try {
    // Convert frontend arrays to backend format
    const fieldsConfig = {}
    priority1Fields.value.forEach(field => {
      fieldsConfig[field] = 1
    })
    priority2Fields.value.forEach(field => {
      fieldsConfig[field] = 2
    })
    priority3Fields.value.forEach(field => {
      fieldsConfig[field] = 3
    })

    const config = {
      version: '1.0',
      token_budget: tokenBudget.value,
      fields: fieldsConfig
    }

    await settingsStore.updateFieldPriorityConfig(config)
    fieldPriorityHasChanges.value = false
    console.log('[USER SETTINGS] Field priority config saved successfully')
  } catch (error) {
    console.error('[USER SETTINGS] Failed to save field priority config:', error)
  } finally {
    savingFieldPriority.value = false
  }
}

async function resetFieldPriorityToDefaults() {
  savingFieldPriority.value = true
  try {
    await settingsStore.resetFieldPriorityConfig()
    await loadFieldPriorityConfig()
    fieldPriorityHasChanges.value = false
    console.log('[USER SETTINGS] Field priority config reset to defaults')
  } catch (error) {
    console.error('[USER SETTINGS] Failed to reset field priority config:', error)
  } finally {
    savingFieldPriority.value = false
  }
}

async function loadFieldPriorityConfig() {
  try {
    await settingsStore.fetchFieldPriorityConfig()
    const config = settingsStore.fieldPriorityConfig

    if (config) {
      tokenBudget.value = config.token_budget || 2000

      // Convert backend format to frontend arrays
      priority1Fields.value = []
      priority2Fields.value = []
      priority3Fields.value = []

      Object.entries(config.fields || {}).forEach(([field, priority]) => {
        if (priority === 1) {
          priority1Fields.value.push(field)
        } else if (priority === 2) {
          priority2Fields.value.push(field)
        } else if (priority === 3) {
          priority3Fields.value.push(field)
        }
      })

      fieldPriorityHasChanges.value = false
      console.log('[USER SETTINGS] Field priority config loaded successfully')
    }
  } catch (error) {
    console.error('[USER SETTINGS] Failed to load field priority config:', error)
  }
}

// Real-time token calculation method (Handover 0049)
async function fetchActiveProductTokenEstimate() {
  loadingTokenEstimate.value = true
  try {
    const response = await api.products.getActiveProductTokenEstimate()
    if (response.data) {
      activeProductTokens.value = response.data
      console.log('[USER SETTINGS] Active product token estimate loaded:', activeProductTokens.value)
    }
  } catch (error) {
    console.warn('[USER SETTINGS] Failed to fetch active product token estimate:', error.response?.status || error.message)
    // Graceful fallback: use generic calculation (already implemented in computed property)
    activeProductTokens.value = null
    console.log('[USER SETTINGS] Using fallback generic token calculation')
  } finally {
    loadingTokenEstimate.value = false
  }
}

// Lifecycle
onMounted(async () => {
  // Check for tab parameter in query string
  const route = router.currentRoute.value

  if (route.query.tab) {

    activeTab.value = route.query.tab
  }

  // Check Serena MCP status
  await checkSerenaStatus()

  // Load settings from store
  const storedSettings = await settingsStore.loadSettings()
  if (storedSettings) {
    Object.assign(settings.value, storedSettings)
  }

  // Initialize theme from current Vuetify theme AFTER loading stored settings
  // This ensures UI reflects actual current theme (restored in main.js from localStorage)
  settings.value.appearance.theme = theme.global.name.value

  // Load field priority configuration (Handover 0048)
  await loadFieldPriorityConfig()

  // Fetch real-time token estimate from active product (Handover 0049)
  await fetchActiveProductTokenEstimate()
})

// Watch priority fields for changes and recalculate tokens with debounce (Handover 0049)
let tokenCalculationTimeout
watch(
  () => [priority1Fields.value, priority2Fields.value, priority3Fields.value],
  () => {
    // Clear previous timeout to implement debounce
    if (tokenCalculationTimeout) {
      clearTimeout(tokenCalculationTimeout)
    }

    // Debounce token recalculation (500ms)
    tokenCalculationTimeout = setTimeout(() => {
      // Token recalculation happens automatically via computed property
      console.log('[USER SETTINGS] Token estimate recalculated (debounced)')
    }, 500)
  },
  { deep: true }
)
</script>

<style scoped>
/* Make Serena toggle more visible */
.serena-toggle :deep(.v-switch__track) {
  border: 2px solid rgba(var(--v-theme-primary), 0.5);
}

.serena-toggle :deep(.v-switch__thumb) {
  border: 2px solid rgba(var(--v-theme-primary), 0.8);
}

/* Field Priority drag-and-drop styling (Handover 0048) */
.drag-handle {
  touch-action: none;
  user-select: none;
  min-height: 48px; /* WCAG touch target size */
}

.drag-handle:hover {
  opacity: 0.9;
}

.drag-handle:focus {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

/* Mobile responsive adjustments */
@media (max-width: 600px) {
  .drag-handle {
    min-height: 56px; /* Larger touch targets on mobile */
    font-size: 14px;
  }
}
</style>
