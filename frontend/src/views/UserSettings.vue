<template>
  <v-container>
    <!-- Page Header -->
    <h1 class="text-h4 mb-2">My Settings</h1>
    <p class="text-subtitle-1 mb-4">Manage your personal preferences</p>

    <!-- Settings Tabs -->
    <v-tabs v-model="activeTab" class="mb-6">
      <v-tab value="general">
        <v-icon start>mdi-cog</v-icon>
        Setup
      </v-tab>
      <v-tab value="appearance">
        <v-icon start>mdi-palette</v-icon>
        Appearance
      </v-tab>
      <v-tab value="notifications">
        <v-icon start>mdi-bell</v-icon>
        Notifications
      </v-tab>
      <v-tab value="agents">
        <template #prepend>
          <v-img :src="theme.global.current.value.dark ? '/icons/Giljo_White_Face.svg' : '/icons/Giljo_Dark_Face.svg'" width="20" height="20" style="margin-right: 3px;" />
        </template>
        Agents
      </v-tab>
      <v-tab value="context">
        <v-icon start>mdi-layers-triple</v-icon>
        Context
      </v-tab>
      <v-tab value="api-keys">
        <v-icon start>mdi-key-variant</v-icon>
        API Keys
      </v-tab>
      <v-tab value="integrations">
        <v-icon start>mdi-puzzle</v-icon>
        Integrations
      </v-tab>
    </v-tabs>

    <!-- Tab Content -->
    <v-window v-model="activeTab" :touch="false" :reverse="false">
      <!-- Context Settings -->
      <v-window-item value="context">
        <ContextPriorityConfig />
      </v-window-item>

      <!-- Agents -->
      <v-window-item value="agents">
        <TemplateManager />
      </v-window-item>

      <!-- Setup Settings -->
      <v-window-item value="general">
        <v-card data-test="general-settings">
          <v-card-title>Setup</v-card-title>
          <v-card-text>
            <v-alert type="info" variant="tonal" density="compact">
              This section is reserved for future setup settings.
            </v-alert>
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

      <!-- API Keys -->
      <v-window-item value="api-keys">
        <!-- Removed outer card title/subtitle - ApiKeyManager has its own -->
        <ApiKeyManager />
      </v-window-item>

      <!-- Integrations -->
      <v-window-item value="integrations">
        <v-card>
          <v-card-title>Integrations</v-card-title>
          <v-card-subtitle>Configure MCP tools and integrations</v-card-subtitle>
          <v-card-text>
            <!-- GiljoAI MCP Integration -->
            <v-card variant="outlined" class="mb-4">
              <v-card-text>
                <div class="d-flex align-center mb-3">
                  <v-avatar size="40" rounded="0" class="mr-2">
                    <v-img :src="theme.global.current.value.dark ? '/giljo_YW_Face.svg' : '/icons/Giljo_BY_Face.svg'" alt="GiljoAI MCP" />
                  </v-avatar>
                  <h3 class="text-h6 mb-0">GiljoAI MCP Integration</h3>
                </div>
                <p class="text-body-2 text-medium-emphasis mb-4">
                  Connect your AI coding tool to GiljoAI orchestration. Supports Claude Code, Codex CLI, and Gemini CLI.
                </p>

                <!-- MCP Configuration Tool -->
                <v-card variant="tonal" class="mb-0">
                  <v-card-text class="pa-3">
                    <div class="d-flex align-center justify-between">
                      <div class="flex-grow-1">
                        <div class="text-subtitle-2 font-weight-medium">MCP Configuration Tool</div>
                        <div class="text-body-2 text-medium-emphasis">
                          Creates MCP integration CLI command for your coding agent of choice
                        </div>
                      </div>
                      <AiToolConfigWizard />
                    </div>
                  </v-card-text>
                </v-card>
              </v-card-text>
            </v-card>

            <!-- Slash Command Setup -->
            <SlashCommandSetup />

            <!-- Claude Code Agent Export -->
            <ClaudeCodeExport />

            <!-- Serena MCP Integration -->
            <v-card variant="outlined" class="mb-4">
              <v-card-text>
                <div class="d-flex align-center mb-3">
                  <v-avatar size="40" rounded="0" class="mr-2">
                    <v-img src="/Serena.png" alt="Serena MCP" />
                  </v-avatar>
                  <div class="flex-grow-1">
                    <div class="d-flex align-center">
                      <h3 class="text-h6 mb-0 mr-2">Serena MCP</h3>
                      <v-tooltip location="top" max-width="400">
                        <template #activator="{ props }">
                          <v-icon v-bind="props" size="small" color="medium-emphasis">mdi-help-circle-outline</v-icon>
                        </template>
                        <div>
                          <strong>Intelligent codebase understanding and navigation</strong>
                          <p class="mt-2 mb-0">
                            Serena provides deep semantic code analysis, intelligent symbol navigation, and contextual 
                            understanding of your codebase. It enables agents to efficiently explore and understand 
                            project structure without reading unnecessary code, significantly improving performance 
                            and reducing token usage.
                          </p>
                          <p class="mt-2 mb-0 text-caption">
                            <strong>Note:</strong> Serena must be installed separately in your AI coding tool.
                          </p>
                        </div>
                      </v-tooltip>
                    </div>
                    <p class="text-caption text-medium-emphasis mb-0">Intelligent codebase understanding and navigation</p>
                  </div>
                </div>

                <p class="text-body-2 text-medium-emphasis mb-3">
                  Enabling adds Serena tool instructions to agent prompts. Disabling removes them from agent tool startup.
                </p>

                <div class="d-flex align-center mb-3">
                  <v-btn variant="text" size="small" color="light-blue" href="https://github.com/oraios/serena" target="_blank">
                    <v-icon start>mdi-github</v-icon>
                    GitHub Repository
                  </v-btn>
                  <span class="text-caption text-medium-emphasis ml-3">
                    Credit: Oraios
                  </span>
                </div>

                <!-- Serena Controls -->
                <v-card variant="tonal" class="mb-0">
                  <v-card-text class="pa-3">
                    <div class="d-flex align-center justify-between">
                      <div class="flex-grow-1 d-flex align-center">
                        <div class="text-subtitle-2 font-weight-medium mr-4">Enable Serena MCP</div>
                        <v-switch
                          v-model="serenaEnabled"
                          @update:model-value="toggleSerena"
                          :loading="toggling"
                          hide-details
                          density="compact"
                          class="serena-toggle-inline"
                        />
                      </div>
                      <v-btn
                        color="primary"
                        variant="flat"
                        size="small"
                        width="120"
                        @click="openSerenaAdvanced"
                        :disabled="toggling"
                      >
                        Advanced
                      </v-btn>
                    </div>
                  </v-card-text>
                </v-card>
              </v-card-text>
            </v-card>

            <!-- Git + 360 Memory Integration (Handover 013B) -->
            <v-card variant="outlined" class="mb-4">
              <v-card-text>
                <div class="d-flex align-center mb-3">
                  <v-avatar size="40" rounded="0" class="mr-2" color="grey-darken-2">
                    <v-icon size="28" color="white">mdi-github</v-icon>
                  </v-avatar>
                  <div class="flex-grow-1">
                    <div class="d-flex align-center">
                      <h3 class="text-h6 mb-0 mr-2">Git + 360 Memory</h3>
                      <v-tooltip location="top" max-width="400">
                        <template #activator="{ props }">
                          <v-icon v-bind="props" size="small" color="medium-emphasis">mdi-help-circle-outline</v-icon>
                        </template>
                        <div>
                          <strong>Cumulative product knowledge tracking</strong>
                          <p class="mt-2 mb-0">
                            When enabled, GiljoAI captures git commit history at project closeout
                            and stores it in 360 Memory. This provides orchestrators with cumulative
                            context across all projects, including what was built, decisions made,
                            and implementation patterns used.
                          </p>
                          <p class="mt-2 mb-0 text-caption">
                            <strong>Note:</strong> Git must be configured on your system with access
                            to your repositories.
                          </p>
                        </div>
                      </v-tooltip>
                    </div>
                    <p class="text-caption text-medium-emphasis mb-0">Track git commits in 360 Memory for orchestrator context</p>
                  </div>
                </div>

                <p class="text-body-2 text-medium-emphasis mb-3">
                  Enable to automatically include git commit history in project summaries. Commits are stored in product memory for future orchestrator reference.
                </p>

                <div class="d-flex align-center mb-3">
                  <v-btn
                    variant="text"
                    size="small"
                    color="light-blue"
                    href="https://docs.github.com/en/get-started/quickstart/set-up-git"
                    target="_blank"
                  >
                    <v-icon start>mdi-book-open-variant</v-icon>
                    GitHub Setup Guide
                  </v-btn>
                </div>

                <!-- Git Integration Controls -->
                <v-card variant="tonal" class="mb-0">
                  <v-card-text class="pa-3">
                    <div class="d-flex align-center justify-between mb-3">
                      <div class="flex-grow-1 d-flex align-center">
                        <div class="text-subtitle-2 font-weight-medium mr-4">Enable Git Integration</div>
                        <v-switch
                          v-model="gitIntegration.enabled"
                          @update:model-value="onGitToggle"
                          :loading="savingGitIntegration"
                          hide-details
                          density="compact"
                          class="git-toggle-inline"
                        />
                      </div>
                      <v-btn
                        color="primary"
                        variant="flat"
                        size="small"
                        width="120"
                        @click="saveGitIntegration"
                        :disabled="savingGitIntegration"
                        :loading="savingGitIntegration"
                      >
                        Save
                      </v-btn>
                    </div>

                    <!-- Info Alert (shown when enabled) -->
                    <v-alert
                      v-if="gitIntegration.enabled"
                      type="info"
                      variant="tonal"
                      density="compact"
                      class="mb-3"
                    >
                      <div class="text-body-2">
                        <strong>Requirement:</strong> Git must be configured with access to your repositories
                        on your system (Windows/Linux/macOS). GiljoAI uses your local git
                        credentials - no server-side authentication needed.
                      </div>
                    </v-alert>

                    <!-- Advanced Settings (collapsible) -->
                    <v-expansion-panels v-if="gitIntegration.enabled" variant="accordion" class="mt-0">
                      <v-expansion-panel>
                        <v-expansion-panel-title>
                          <v-icon start size="small">mdi-cog</v-icon>
                          Advanced Settings
                        </v-expansion-panel-title>
                        <v-expansion-panel-text>
                          <v-text-field
                            v-model.number="gitIntegration.commit_limit"
                            label="Commit Limit"
                            type="number"
                            min="1"
                            max="100"
                            hint="Number of commits to include in orchestrator prompts"
                            persistent-hint
                            density="compact"
                            class="mb-3"
                          />
                          <v-text-field
                            v-model="gitIntegration.default_branch"
                            label="Default Branch"
                            placeholder="e.g., main, master, develop"
                            hint="Leave empty for repository default"
                            persistent-hint
                            density="compact"
                          />
                        </v-expansion-panel-text>
                      </v-expansion-panel>
                    </v-expansion-panels>
                  </v-card-text>
                </v-card>
              </v-card-text>
            </v-card>
          </v-card-text>
        </v-card>
      </v-window-item>
    </v-window>

    

    <!-- Serena Advanced Settings Dialog -->
    <SerenaAdvancedSettingsDialog
      v-model="showSerenaAdvanced"
      :value="serenaConfig"
      @save="saveSerenaConfig"
    />
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { useTheme } from 'vuetify'
import { useRouter } from 'vue-router'
import TemplateManager from '@/components/TemplateManager.vue'
import ApiKeyManager from '@/components/ApiKeyManager.vue'
import AiToolConfigWizard from '@/components/AiToolConfigWizard.vue'
import ClaudeCodeExport from '@/components/ClaudeCodeExport.vue'
import SlashCommandSetup from '@/components/SlashCommandSetup.vue'
import SerenaAdvancedSettingsDialog from '@/components/SerenaAdvancedSettingsDialog.vue'
import ContextPriorityConfig from '@/components/settings/ContextPriorityConfig.vue'
import setupService from '@/services/setupService'
import api from '@/services/api'

// Stores and Theme
const settingsStore = useSettingsStore()
const theme = useTheme()
const router = useRouter()

// State
const activeTab = ref('general')
const serenaEnabled = ref(false)
const toggling = ref(false)

const showSerenaAdvanced = ref(false)
const serenaConfig = ref({
  use_in_prompts: true,
  tailor_by_mission: true,
  dynamic_catalog: true,
  prefer_ranges: true,
  max_range_lines: 180,
  context_halo: 12,
})

// Git Integration state (Handover 013B)
const gitIntegration = ref({
  enabled: false,
  commit_limit: 20,
  default_branch: 'main'
})
const savingGitIntegration = ref(false)

// Settings object
const settings = ref({
  general: {
    // Handover 0052: Removed unused projectName field (had broken save function)
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
  // Handover 0052: General settings are empty after projectName field removal
  settings.value.general = {}
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

  // Load git integration settings (Handover 013B)
  await loadGitIntegration()
})

// Serena Advanced dialog handlers
async function openSerenaAdvanced() {
  try {
    const cfg = await setupService.getSerenaConfig()
    serenaConfig.value = cfg
    // keep main toggle in sync
    serenaEnabled.value = !!cfg.use_in_prompts
    showSerenaAdvanced.value = true
  } catch (error) {
    console.error('[USER SETTINGS] Failed to load Serena config:', error)
  }
}

async function saveSerenaConfig(payload, done) {
  try {
    const updated = await setupService.updateSerenaConfig(payload)
    serenaConfig.value = updated
    serenaEnabled.value = !!updated.use_in_prompts
    showSerenaAdvanced.value = false
  } catch (error) {
    console.error('[USER SETTINGS] Failed to save Serena config:', error)
  } finally {
    if (typeof done === 'function') done()
  }
}

// Git Integration handlers (Handover 013B)
async function loadGitIntegration() {
  try {
    // Load product info to get the active product ID
    await settingsStore.loadProductInfo()

    if (!settingsStore.productInfo?.id) {
      console.warn('[USER SETTINGS] No active product found - git integration disabled')
      return
    }

    const response = await api.products.getGitIntegration(settingsStore.productInfo.id)
    gitIntegration.value = {
      enabled: response.data.enabled || false,
      commit_limit: response.data.commit_limit || 20,
      default_branch: response.data.default_branch || 'main'
    }
    console.log('[USER SETTINGS] Git integration loaded:', gitIntegration.value)
  } catch (error) {
    console.error('[USER SETTINGS] Failed to load git integration:', error)
    // Set defaults on error
    gitIntegration.value = {
      enabled: false,
      commit_limit: 20,
      default_branch: 'main'
    }
  }
}

function onGitToggle(enabled) {
  console.log('[USER SETTINGS] Git integration toggled:', enabled)
  // If disabled, reset to defaults
  if (!enabled) {
    gitIntegration.value.commit_limit = 20
    gitIntegration.value.default_branch = 'main'
  }
}

async function saveGitIntegration() {
  if (!settingsStore.productInfo?.id) {
    console.error('[USER SETTINGS] No active product - cannot save git integration')
    return
  }

  savingGitIntegration.value = true
  try {
    const response = await api.products.updateGitIntegration(
      settingsStore.productInfo.id,
      {
        enabled: gitIntegration.value.enabled,
        commit_limit: gitIntegration.value.commit_limit || 20,
        default_branch: gitIntegration.value.default_branch || 'main'
      }
    )

    // Update local state with response
    gitIntegration.value = {
      enabled: response.data.enabled,
      commit_limit: response.data.commit_limit,
      default_branch: response.data.default_branch
    }

    console.log('[USER SETTINGS] Git integration saved successfully')

    // Show success notification (you can add toast notification here if available)
    console.log('[USER SETTINGS] ✓ Git integration settings saved')

  } catch (error) {
    console.error('[USER SETTINGS] Failed to save git integration:', error)
    // Show error notification
    console.error('[USER SETTINGS] ✗ Failed to save git integration:', error.message)
  } finally {
    savingGitIntegration.value = false
  }
}
</script>

<style scoped>
/* Integrations section divider should follow theme */
.integrations-divider {
  --v-theme-overlay-multiplier: 1; /* ensure visibility */
  border-color: var(--v-theme-on-surface) !important;
  opacity: 0.3 !important;
}
/* Make Serena toggle inline */
.serena-toggle-inline {
  flex: 0 0 auto;
}

/* Make Git toggle inline (Handover 013B) */
.git-toggle-inline {
  flex: 0 0 auto;
}

/* Disable sliding transitions, use simple fade instead */
:deep(.v-window__container) {
  overflow: visible !important;
}
:deep(.v-window-item) {
  transition: none !important;
  transform: none !important;
}
:deep(.v-window-item--active) {
  animation: fade-in 0.2s ease-in !important;
}

@keyframes fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
</style>
