<template>
  <v-container>
    <!-- Page Header -->
    <h1 class="text-h4 mb-2">My Settings</h1>
    <p class="text-subtitle-1 mb-4">Manage your personal preferences</p>

    <!-- Settings Tabs (v-btn-toggle - native Vuetify) -->
    <v-btn-toggle
      v-model="activeTab"
      mandatory
      variant="outlined"
      divided
      rounded="t-lg"
      color="primary"
      class="mb-0"
    >
      <v-btn value="startup" data-testid="startup-settings-tab">
        <v-icon start>mdi-rocket-launch</v-icon>
        Startup
        <v-icon
          size="18"
          class="ml-1 startup-help-icon"
          aria-label="What is GiljoAI MCP?"
          data-testid="startup-intro-help"
          @click.stop="openIntroTour"
        >mdi-help-circle-outline</v-icon>
      </v-btn>
      <v-btn value="notifications">
        <v-icon start>mdi-bell</v-icon>
        Notifications
      </v-btn>
      <v-btn value="agents" data-testid="agent-templates-settings-tab">
        <v-img
          src="/icons/Giljo_White_Face.svg"
          width="20"
          height="20"
          class="mr-1"
        />
        Agents
      </v-btn>
      <v-btn value="context" data-testid="context-settings-tab">
        <v-icon start>mdi-layers-triple</v-icon>
        Context
      </v-btn>
      <v-btn value="api-keys">
        <v-icon start>mdi-key-variant</v-icon>
        API Keys
      </v-btn>
      <v-btn value="integrations" data-testid="integrations-settings-tab">
        <v-icon start>mdi-puzzle</v-icon>
        Integrations
      </v-btn>
    </v-btn-toggle>

    <!-- Tab Content -->
    <div class="bordered-tabs-content">
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
          <v-card-subtitle>Setup wizard and getting started</v-card-subtitle>
          <v-card-text>
            <p class="text-body-2 mb-4" style="color: #8f97b7;">
              The setup wizard guides you through connecting AI coding tools and configuring GiljoAI MCP.
            </p>
            <v-btn
              color="primary"
              variant="flat"
              prepend-icon="mdi-rocket-launch"
              @click="router.push('/')"
            >
              Open Setup Wizard
            </v-btn>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- Notification Settings -->
      <v-window-item value="notifications">
        <v-card data-test="notification-settings">
          <v-card-title>Notification Display</v-card-title>
          <v-card-subtitle>Configure where and how long notifications appear</v-card-subtitle>
          <v-card-text>
            <v-select
              v-model="settings.notifications.position"
              :items="[
                { title: 'Top Left', value: 'top-left' },
                { title: 'Top Center', value: 'top-center' },
                { title: 'Top Right', value: 'top-right' },
                { title: 'Bottom Left', value: 'bottom-left' },
                { title: 'Bottom Center', value: 'bottom-center' },
                { title: 'Bottom Right', value: 'bottom-right' },
              ]"
              label="Position"
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
              color="primary"
              class="mt-4"
            />

            <!-- Handover 0491: Agent silence threshold -->
            <v-divider class="my-4" />
            <h3 class="text-subtitle-1 mb-2">Agent Monitoring</h3>
            <v-text-field
              v-model.number="settings.notifications.agent_silence_threshold_minutes"
              type="number"
              label="Agent Silence Threshold (minutes)"
              hint="Time without communication before an agent is marked as silent"
              persistent-hint
              variant="outlined"
              :min="1"
              :max="60"
              :rules="[
                v => (v >= 1 && v <= 60) || 'Must be between 1 and 60 minutes',
                v => Number.isInteger(v) || 'Must be a whole number',
              ]"
              data-test="silence-threshold-input"
              class="mt-2"
              style="max-width: 400px;"
            />
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn
              variant="text"
              data-test="reset-notification-btn"
              @click="resetNotificationSettings"
              >Reset</v-btn
            >
            <v-btn
              color="primary"
              variant="flat"
              data-test="save-notification-btn"
              @click="saveNotificationSettings"
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

            <!-- Agent Export (multi-platform — includes slash commands/skills) -->
            <AgentExport />

            <!-- Serena MCP Integration (Handover 0277: Simplified to toggle only) -->
            <SerenaIntegrationCard
              :enabled="serenaEnabled"
              :loading="toggling"
              @update:enabled="toggleSerena"
            />

            <!-- Git + 360 Memory Integration (system-level) -->
            <GitIntegrationCard
              :enabled="gitEnabled"
              :loading="togglingGit"
              @update:enabled="toggleGit"
            />

          </v-card-text>
        </v-card>
      </v-window-item>
    </v-window>
    </div>

    <!-- Product intro tour (shown on first Startup visit unless hidden) -->
    <ProductIntroTour v-model="showIntroTour" />
  </v-container>
</template>

<script setup>
import { ref, provide, onMounted, onUnmounted, watch } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { useRouter } from 'vue-router'
import { useWebSocketV2 } from '@/composables/useWebSocket'
import TemplateManager from '@/components/TemplateManager.vue'
import ApiKeyManager from '@/components/ApiKeyManager.vue'
import AgentExport from '@/components/AgentExport.vue'
import ContextPriorityConfig from '@/components/settings/ContextPriorityConfig.vue'
import ProductIntroTour from '@/components/settings/ProductIntroTour.vue'
import McpIntegrationCard from '@/components/settings/integrations/McpIntegrationCard.vue'
import SerenaIntegrationCard from '@/components/settings/integrations/SerenaIntegrationCard.vue'
import GitIntegrationCard from '@/components/settings/integrations/GitIntegrationCard.vue'
import setupService from '@/services/setupService'
// Stores and Theme
const settingsStore = useSettingsStore()
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
const togglingGit = ref(false)

// Settings object
const settings = ref({
  general: {
    // Handover 0052: Removed unused projectName field (had broken save function)
  },
  notifications: {
    position: 'bottom-right',
    duration: 5,
    agent_silence_threshold_minutes: 10,
  },
})

// Methods
async function saveNotificationSettings() {
  try {
    await settingsStore.updateSettings({ notifications: settings.value.notifications })
  } catch (error) {
    console.error('Failed to save notification settings:', error)
  }
}

function resetNotificationSettings() {
  settings.value.notifications = {
    position: 'bottom-right',
    duration: 5,
    agent_silence_threshold_minutes: 10,
  }
}

// Serena MCP Methods
async function checkSerenaStatus() {
  try {
    const status = await setupService.getSerenaStatus()
    serenaEnabled.value = status.enabled || false
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
  await settingsStore.loadSettings()
  // Apply stored notification settings to local state
  if (settingsStore.settings.notifications) {
    settings.value.notifications = { ...settings.value.notifications, ...settingsStore.settings.notifications }
  }

  // Load git integration settings (system-level)
  await loadGitSettings()

  // Listen for real-time Git integration changes via WebSocket
  // This listener is at parent level to ensure it captures events even when
  // ContextPriorityConfig tab is not actively mounted
  on('product:git:settings:changed', handleGitIntegrationUpdate)

  // Handover 0335: Listen for template export events at parent level
  // This ensures events are captured even when TemplateManager tab is not active
  on('template:exported', handleTemplateExportEvent)

  // Preface Startup with the product intro tour, unless user hid it
  maybeShowIntroTour()
})

watch(activeTab, (newTab) => {
  // Push tab to URL so browser back button returns to previous tab
  const currentQuery = router.currentRoute.value.query
  if (currentQuery.tab !== newTab) {
    router.push({ query: { ...currentQuery, tab: newTab } })
  }
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
})

// Git Integration Functions (system-level like Serena)
async function loadGitSettings() {
  try {
    const settings = await setupService.getGitSettings()
    gitEnabled.value = settings.enabled || false
  } catch (error) {
    console.error('[USER SETTINGS] Failed to load git settings:', error)
    gitEnabled.value = false
  }
}

async function toggleGit(enabled) {
  togglingGit.value = true

  try {
    const result = await setupService.toggleGit(enabled)
    gitEnabled.value = result.enabled
  } catch (error) {
    console.error('[USER SETTINGS] Git toggle failed:', error)
    // Revert on error
    gitEnabled.value = !enabled
  } finally {
    togglingGit.value = false
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
  border-color: var(--v-theme-on-surface);
  opacity: 0.3;
}

/* Tab animations are handled by global-tabs-window class */

.startup-help-icon {
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.2s ease;
}

.startup-help-icon:hover {
  opacity: 1;
}
</style>
