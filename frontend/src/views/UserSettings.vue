<template>
  <v-container>
    <!-- Page Header -->
    <h1 class="text-h4 mb-2">My Settings</h1>
    <p class="text-subtitle-1 mb-4">Manage your personal preferences</p>

    <!-- Settings Tabs -->
    <v-tabs v-model="activeTab" class="mb-6 global-tabs">
      <v-tab value="startup" data-testid="startup-settings-tab">
        <v-icon start>mdi-rocket-launch</v-icon>
        Startup
        <v-btn
          icon
          size="x-small"
          variant="text"
          class="ml-1"
          aria-label="What is GiljoAI MCP?"
          @click.stop="openIntroTour"
          data-testid="startup-intro-help"
        >
          <v-icon size="18">mdi-help-circle-outline</v-icon>
          <v-tooltip activator="parent" location="bottom">What is this product?</v-tooltip>
        </v-btn>
      </v-tab>
      <v-tab value="appearance">
        <v-icon start>mdi-palette</v-icon>
        Appearance
      </v-tab>
      <v-tab value="notifications">
        <v-icon start>mdi-bell</v-icon>
        Notifications
      </v-tab>
      <v-tab value="agents" data-testid="agent-templates-settings-tab">
        <template #prepend>
          <v-img
            :src="
              theme.global.current.value.dark
                ? '/icons/Giljo_White_Face.svg'
                : '/icons/Giljo_Dark_Face.svg'
            "
            width="20"
            height="20"
            style="margin-right: 3px"
          />
        </template>
        Agents
      </v-tab>
      <v-tab value="context" data-testid="context-settings-tab">
        <v-icon start>mdi-layers-triple</v-icon>
        Context
      </v-tab>
      <v-tab value="api-keys">
        <v-icon start>mdi-key-variant</v-icon>
        API Keys
      </v-tab>
      <v-tab value="integrations" data-testid="integrations-settings-tab">
        <v-icon start>mdi-puzzle</v-icon>
        Integrations
      </v-tab>
    </v-tabs>

    <!-- Tab Content -->
    <v-window v-model="activeTab" :touch="false" :reverse="false" class="global-tabs-window">
      <!-- Context Settings -->
      <v-window-item value="context">
        <ContextPriorityConfig :git-integration-enabled="gitEnabled" />
      </v-window-item>

      <!-- Agents -->
      <v-window-item value="agents">
        <TemplateManager />
      </v-window-item>

      <!-- Setup Settings -->
      <v-window-item value="startup">
        <v-card data-test="startup-settings">
          <v-card-title>Startup</v-card-title>
          <v-card-subtitle>Visual setup quick start</v-card-subtitle>
          <v-card-text>
            <StartupQuickStart :git-enabled="gitEnabled" :serena-enabled="serenaEnabled" />
          </v-card-text>
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
            <v-btn variant="text" @click="resetAppearanceSettings" data-test="reset-appearance-btn"
              >Reset</v-btn
            >
            <v-btn
              color="primary"
              variant="flat"
              @click="saveAppearanceSettings"
              data-test="save-appearance-btn"
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
            <v-btn
              variant="text"
              @click="resetNotificationSettings"
              data-test="reset-notification-btn"
              >Reset</v-btn
            >
            <v-btn
              color="primary"
              variant="flat"
              @click="saveNotificationSettings"
              data-test="save-notification-btn"
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
            <McpIntegrationCard />

            <!-- Slash Command Setup -->
            <SlashCommandSetup />

            <!-- Claude Code Agent Export -->
            <ClaudeCodeExport />

            <!-- Codex CLI Integration -->
            <CodexCliIntegration />

            <!-- Serena MCP Integration (Handover 0277: Simplified to toggle only) -->
            <SerenaIntegrationCard
              :enabled="serenaEnabled"
              :loading="toggling"
              @update:enabled="toggleSerena"
            />

            <!-- Git + 360 Memory Integration (system-level) -->
            <GitIntegrationCard
              :enabled="gitEnabled"
              :config="gitConfig"
              :loading="togglingGit"
              @update:enabled="toggleGit"
              @openAdvanced="openGitAdvanced"
            />

            <!-- Vision Document Summarization Info (Handover 0345e) -->
            <v-card outlined class="mb-4">
              <v-card-title class="text-subtitle-1">
                <v-icon left color="primary">mdi-file-document-outline</v-icon>
                Vision Document Summarization
              </v-card-title>
              <v-card-text>
                <v-alert type="info" variant="tonal" density="compact" class="mb-3">
                  Vision documents are automatically compressed using Sumy LSA (Latent Semantic Analysis)
                  extractive summarization. Configure compression levels in
                  <strong>Context → Depth Configuration → Vision Documents</strong>.
                </v-alert>
                <v-list density="compact">
                  <v-list-item>
                    <v-list-item-title>Compression Levels</v-list-item-title>
                    <v-list-item-subtitle>
                      Light (5K tokens), Moderate (12.5K), Heavy (25K), Full (all)
                    </v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <v-list-item-title>Algorithm</v-list-item-title>
                    <v-list-item-subtitle>
                      LSA extractive summarization (CPU-based, fast, no hallucination)
                    </v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <v-list-item-title>Processing Time</v-list-item-title>
                    <v-list-item-subtitle>
                      ~5 seconds for 100K token documents
                    </v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>
          </v-card-text>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- Git Advanced Settings Dialog -->
    <GitAdvancedSettingsDialog
      v-model="showGitAdvanced"
      :value="gitConfig"
      @save="saveGitConfig"
    />

    <!-- Product intro tour (shown on first Startup visit unless hidden) -->
    <ProductIntroTour v-model="showIntroTour" />
  </v-container>
</template>

<script setup>
import { ref, provide, onMounted, onUnmounted, watch } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { useTheme } from 'vuetify'
import { useRouter } from 'vue-router'
import { useWebSocketV2 } from '@/composables/useWebSocket'
import TemplateManager from '@/components/TemplateManager.vue'
import ApiKeyManager from '@/components/ApiKeyManager.vue'
import ClaudeCodeExport from '@/components/ClaudeCodeExport.vue'
import CodexCliIntegration from '@/components/CodexCliIntegration.vue'
import SlashCommandSetup from '@/components/SlashCommandSetup.vue'
import GitAdvancedSettingsDialog from '@/components/GitAdvancedSettingsDialog.vue'
import ContextPriorityConfig from '@/components/settings/ContextPriorityConfig.vue'
import StartupQuickStart from '@/components/settings/StartupQuickStart.vue'
import ProductIntroTour from '@/components/settings/ProductIntroTour.vue'
import McpIntegrationCard from '@/components/settings/integrations/McpIntegrationCard.vue'
import SerenaIntegrationCard from '@/components/settings/integrations/SerenaIntegrationCard.vue'
import GitIntegrationCard from '@/components/settings/integrations/GitIntegrationCard.vue'
import setupService from '@/services/setupService'
import api from '@/services/api'

// Stores and Theme
const settingsStore = useSettingsStore()
const theme = useTheme()
const router = useRouter()

// WebSocket for real-time Git integration updates
const { on, off } = useWebSocketV2()

// State
const activeTab = ref('startup')
const serenaEnabled = ref(false)
const toggling = ref(false)
const showIntroTour = ref(false)
const introTourShownThisSession = ref(false)

// Git Integration state (system-level like Serena)
// This state is shared with ContextPriorityConfig via props
const gitEnabled = ref(false)

// Handover 0335: Provide template export event data to child components
// This allows TemplateManager to receive export events even when not actively mounted
const templateExportEvent = ref(null)
provide('templateExportEvent', templateExportEvent)
const showGitAdvanced = ref(false)
const gitConfig = ref({
  use_in_prompts: false,
  include_commit_history: true,
  max_commits: 50,
  branch_strategy: 'main',
})
const togglingGit = ref(false)

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
async function saveAppearanceSettings() {
  try {
    // Apply theme immediately
    if (settings.value.appearance.theme !== 'system') {
      theme.global.name.value = settings.value.appearance.theme // TODO: Upgrade to theme.change() after Vuetify 3.7+
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
    activeTab.value = route.query.tab === 'general' ? 'startup' : route.query.tab
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

  // Load git integration settings (system-level)
  await loadGitSettings()

  // Listen for real-time Git integration changes via WebSocket
  // This listener is at parent level to ensure it captures events even when
  // ContextPriorityConfig tab is not actively mounted
  on('product:git:settings:changed', handleGitIntegrationUpdate)
  console.log('[USER SETTINGS] WebSocket listener registered for git integration updates')

  // Handover 0335: Listen for template export events at parent level
  // This ensures events are captured even when TemplateManager tab is not active
  on('template:exported', handleTemplateExportEvent)
  console.log('[USER SETTINGS] WebSocket listener registered for template export events')

  // Preface Startup with the product intro tour, unless user hid it
  maybeShowIntroTour()
})

watch(activeTab, () => {
  maybeShowIntroTour()
})

watch(
  () => router.currentRoute.value.query.tab,
  (tab) => {
    if (!tab) return
    activeTab.value = tab === 'general' ? 'startup' : tab
  },
)

onUnmounted(() => {
  // Clean up WebSocket listeners to prevent memory leaks
  off('product:git:settings:changed', handleGitIntegrationUpdate)
  off('template:exported', handleTemplateExportEvent) // Handover 0335
  console.log('[USER SETTINGS] WebSocket listeners cleaned up')
})

// Git Integration Functions (system-level like Serena)
async function loadGitSettings() {
  console.log('[USER SETTINGS] Loading git settings...')

  try {
    const settings = await setupService.getGitSettings()
    gitConfig.value = settings
    gitEnabled.value = settings.enabled || false
    console.log('[USER SETTINGS] Git settings loaded:', settings)
  } catch (error) {
    console.error('[USER SETTINGS] Failed to load git settings:', error)
    // Set defaults on error
    gitEnabled.value = false
    gitConfig.value = {
      use_in_prompts: false,
      include_commit_history: true,
      max_commits: 50,
      branch_strategy: 'main',
    }
  }
}

async function toggleGit(enabled) {
  console.log('[USER SETTINGS] Git integration toggled:', enabled)
  togglingGit.value = true

  try {
    const result = await setupService.toggleGit(enabled)
    gitEnabled.value = result.enabled
    // Update config from server response
    if (result.settings) {
      gitConfig.value = result.settings
    }
    console.log('[USER SETTINGS] Git toggle result:', result)
  } catch (error) {
    console.error('[USER SETTINGS] Git toggle failed:', error)
    // Revert on error
    gitEnabled.value = !enabled
  } finally {
    togglingGit.value = false
  }
}

async function openGitAdvanced() {
  // Load fresh config before opening
  try {
    const settings = await setupService.getGitSettings()
    gitConfig.value = settings
    gitEnabled.value = settings.enabled || false
    showGitAdvanced.value = true
  } catch (error) {
    console.error('[USER SETTINGS] Failed to load Git config:', error)
  }
}

async function saveGitConfig(payload, done) {
  try {
    const updated = await setupService.updateGitSettings(payload)
    gitConfig.value = updated.settings || payload
    gitEnabled.value = updated.enabled || payload.use_in_prompts
    showGitAdvanced.value = false
  } catch (error) {
    console.error('[USER SETTINGS] Failed to save Git config:', error)
  } finally {
    if (typeof done === 'function') done()
  }
}

/**
 * Handle real-time Git integration updates from WebSocket
 * This handler is at parent level to ensure it fires regardless of
 * which tab is currently active
 * @param {Object} data - WebSocket event data
 * @param {string} data.product_id - Product ID
 * @param {Object} data.settings - Git integration settings
 * @param {boolean} data.settings.enabled - Whether git integration is enabled
 */
function handleGitIntegrationUpdate(data) {
  if (!data || !data.settings) {
    console.warn('[USER SETTINGS] Received invalid git integration update:', data)
    return
  }

  const newState = data.settings.enabled || false
  gitEnabled.value = newState

  console.log('[USER SETTINGS] Git integration updated via WebSocket:', {
    enabled: newState,
    timestamp: new Date().toISOString(),
  })
}


/**
 * Handover 0335: Handle template export WebSocket events
 * This handler is at parent level to ensure it fires regardless of
 * which tab is currently active. The event data is provided to TemplateManager
 * via Vue's provide/inject system.
 *
 * @param {Object} data - WebSocket event data (already normalized by websocket store)
 * @param {string} data.tenant_key - Multi-tenant isolation key
 * @param {string[]} data.template_ids - List of exported template UUIDs
 * @param {string} data.export_type - Export type (manual_zip, personal_agents, product_agents)
 * @param {string} data.exported_at - ISO timestamp of export
 */
function handleTemplateExportEvent(data) {
  console.log('[USER SETTINGS] Received template:exported event:', data)

  if (!data || !data.template_ids || !data.exported_at) {
    console.warn('[USER SETTINGS] Invalid template export event - missing required fields:', data)
    return
  }

  // Update the provided ref so TemplateManager can react to it
  // Include a unique ID to ensure Vue detects the change even if same templates
  templateExportEvent.value = {
    ...data,
    _eventId: Date.now(), // Force reactivity
  }

  console.log('[USER SETTINGS] Template export event forwarded to child components:', {
    templateCount: data.template_ids?.length || 0,
    exportType: data.export_type,
  })
}

function isIntroTourHidden() {
  try {
    return localStorage.getItem('giljo_intro_tour_hidden') === '1'
  } catch {
    return false
  }
}

function maybeShowIntroTour() {
  if (introTourShownThisSession.value) return
  if (activeTab.value !== 'startup') return
  if (isIntroTourHidden()) return
  showIntroTour.value = true
  introTourShownThisSession.value = true
}

function openIntroTour() {
  showIntroTour.value = true
  introTourShownThisSession.value = true
}
</script>

<style scoped>
/* Integrations section divider should follow theme */
.integrations-divider {
  --v-theme-overlay-multiplier: 1; /* ensure visibility */
  border-color: var(--v-theme-on-surface) !important;
  opacity: 0.3 !important;
}

/* Tab animations are handled by global-tabs-window class */
</style>
