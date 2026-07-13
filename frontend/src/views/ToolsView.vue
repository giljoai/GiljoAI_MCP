<template>
  <v-container>
    <!-- Page Header -->
    <h1 class="text-headline-large mb-2">Tools</h1>
    <p class="text-body-large mb-4 settings-subtitle">Manage connections, tune agents, and configure context</p>

    <!-- Settings Pills -->
    <div class="pill-toggle-row">
      <button
        class="pill-toggle smooth-border"
        :class="{ 'pill-toggle--active': activeTab === 'connect' }"
        data-testid="connect-settings-tab"
        @click="activeTab = 'connect'"
      >
        <v-icon size="16" class="pill-toggle-icon">mdi-puzzle</v-icon>
        Connect
      </button>
      <button
        class="pill-toggle smooth-border"
        :class="{ 'pill-toggle--active': activeTab === 'agents' }"
        data-testid="agent-templates-settings-tab"
        @click="activeTab = 'agents'"
      >
        <v-img :src="activeTab === 'agents' ? '/icons/Giljo_YW_Face.svg' : '/icons/Giljo_Inactive_Dark.svg'" width="16" height="16" class="pill-toggle-icon" />
        Agents
      </button>
      <button
        class="pill-toggle smooth-border"
        :class="{ 'pill-toggle--active': activeTab === 'context' }"
        data-testid="context-settings-tab"
        @click="activeTab = 'context'"
      >
        <v-icon size="16" class="pill-toggle-icon">mdi-layers-triple</v-icon>
        Context
      </button>
      <button
        class="pill-toggle smooth-border"
        :class="{ 'pill-toggle--active': activeTab === 'notifications' }"
        @click="activeTab = 'notifications'"
      >
        <v-icon size="16" class="pill-toggle-icon">mdi-bell</v-icon>
        Notifications
      </button>
      <button
        class="pill-toggle smooth-border"
        :class="{ 'pill-toggle--active': activeTab === 'startup' }"
        data-testid="startup-settings-tab"
        @click="activeTab = 'startup'"
      >
        <v-icon size="16" class="pill-toggle-icon">mdi-rocket-launch</v-icon>
        Startup
      </button>
    </div>

    <!-- Tab Content -->
    <div class="pill-tabs-content">
      <v-window v-model="activeTab" :touch="false" :reverse="false" class="global-tabs-window main-window-tabs">
      <!-- Context Settings -->
      <v-window-item value="context" eager>
        <ContextPriorityConfig :git-integration-enabled="gitEnabled" />
      </v-window-item>

      <!-- Agents -->
      <v-window-item value="agents">
        <TemplateManager />
      </v-window-item>

      <!-- Setup Settings -->
      <v-window-item value="startup">
        <div class="tab-header mb-4">
          <h2 class="text-title-large">Startup</h2>
          <p class="text-body-medium text-muted-a11y mt-1">Setup wizard and getting started</p>
        </div>
        <div class="startup-cards" data-test="startup-settings">
          <div
            class="startup-card smooth-border"
            style="--card-accent: var(--color-accent-primary)"
            @click="router.push({ path: '/home', query: { openSetup: 'true' } })"
          >
            <div class="startup-card-icon" style="background: rgba(255,195,0,0.1); color: var(--color-accent-primary)">
              <v-icon size="20">mdi-rocket-launch</v-icon>
            </div>
            <div class="startup-card-title">Setup Wizard</div>
            <div class="startup-card-desc">Connect AI coding tools, install skills, and configure GiljoAI MCP.</div>
          </div>
          <div
            class="startup-card smooth-border"
            style="--card-accent: var(--agent-documenter-primary)"
            @click="router.push({ path: '/home', query: { openGuide: 'true' } })"
          >
            <div class="startup-card-icon" style="background: rgba(94,196,142,0.12); color: var(--agent-documenter-primary)">
              <v-icon size="20">mdi-book-open-variant</v-icon>
            </div>
            <div class="startup-card-title">Learning</div>
            <div class="startup-card-desc">Understand products, projects, agents, memory, and slash commands.</div>
          </div>
          <div
            v-if="isCe"
            class="startup-card smooth-border"
            style="--card-accent: var(--agent-implementer-primary)"
            @click="showCertModal = true"
          >
            <div class="startup-card-icon" style="background: var(--agent-implementer-tinted); color: var(--agent-implementer-primary)">
              <v-icon size="20">mdi-certificate</v-icon>
            </div>
            <div class="startup-card-title">Certificate Trust</div>
            <div class="startup-card-desc">Trust the HTTPS certificate your server uses so AI coding tools can connect.</div>
          </div>
        </div>
        <CertTrustModal v-model="showCertModal" />
      </v-window-item>

      <!-- Notification Settings -->
      <v-window-item value="notifications">
        <div class="tab-header mb-4">
          <h2 class="text-title-large">Notification Display</h2>
          <p class="text-body-medium text-muted-a11y mt-1">Configure where and how long notifications appear</p>
        </div>
        <v-card variant="flat" class="smooth-border settings-card" data-test="notification-settings">
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

            <div v-if="isCe" data-test="agent-monitoring-settings">
              <v-divider class="my-4" />
              <h3 class="text-body-large mb-2">Agent Monitoring</h3>
              <v-text-field
                v-model.number="agentSilenceThresholdMinutes"
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
            </div>
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

      <!-- Connect (formerly Integrations + API Keys folded in as Credentials) -->
      <v-window-item value="connect">
        <div class="tab-header mb-4">
          <h2 class="text-title-large">Connect</h2>
          <p class="text-body-medium text-muted-a11y mt-1">Connect external tools and services to your GiljoAI workspace</p>
        </div>

        <!-- Connect cards — 5-up on wide (16:9), down to 1 column on mobile -->
        <div class="connect-grid mb-5">
          <McpIntegrationCard />
          <AgentExport />
          <SerenaIntegrationCard
            :enabled="serenaEnabled"
            :loading="toggling"
            @update:enabled="toggleSerena"
          />
          <GitIntegrationCard
            :enabled="gitEnabled"
            :loading="togglingGit"
            @update:enabled="toggleGit"
          />
          <McpGenericCard />
        </div>

        <!-- Credentials (compact section, formerly the "API Keys" peer tab) -->
        <div class="credentials-section">
          <ApiKeyManager />
        </div>
      </v-window-item>
    </v-window>
    </div>

  </v-container>
</template>

<script setup>
import { ref, provide, onMounted, onUnmounted, watch } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { useRouter } from 'vue-router'
import { useWebSocketStore } from '@/stores/websocket'
import { useToast } from '@/composables/useToast'
import TemplateManager from '@/components/TemplateManager.vue'
import ApiKeyManager from '@/components/ApiKeyManager.vue'
import AgentExport from '@/components/AgentExport.vue'
import ContextPriorityConfig from '@/components/settings/ContextPriorityConfig.vue'
import McpIntegrationCard from '@/components/settings/integrations/McpIntegrationCard.vue'
import McpGenericCard from '@/components/settings/integrations/McpGenericCard.vue'
import SerenaIntegrationCard from '@/components/settings/integrations/SerenaIntegrationCard.vue'
import GitIntegrationCard from '@/components/settings/integrations/GitIntegrationCard.vue'
import setupService from '@/services/setupService'
import { isCeModeValue } from '@/composables/useGiljoMode'
import CertTrustModal from '@/components/setup/CertTrustModal.vue'
// Stores and Theme
const settingsStore = useSettingsStore()
const router = useRouter()

// WebSocket for real-time Git integration updates
const { on, off } = useWebSocketStore()
const { showToast } = useToast()

// State
const activeTab = ref('connect')

// Map legacy tab values to current ones (keep deep-links working after FE-0023 IA reshuffle).
function normalizeTab(tab) {
  if (!tab) return null
  if (tab === 'general') return 'startup'
  if (tab === 'integrations' || tab === 'api-keys') return 'connect'
  return tab
}
const isCe = ref(false)
const showCertModal = ref(false)
const serenaEnabled = ref(false)
const toggling = ref(false)
const agentSilenceThresholdMinutes = ref(10)

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
  },
})

// Methods
async function saveNotificationSettings() {
  try {
    const notifications = {
      position: settings.value.notifications.position,
      duration: settings.value.notifications.duration,
    }
    await settingsStore.updateSettings({ notifications })
    if (isCe.value) {
      await settingsStore.updateAgentSilenceThreshold(agentSilenceThresholdMinutes.value)
    }
  } catch (error) {
    console.error('Failed to save notification settings:', error)
    showToast({ message: 'Failed to save notification settings. Please try again.', type: 'error' })
  }
}

function resetNotificationSettings() {
  settings.value.notifications = {
    position: 'bottom-right',
    duration: 5,
  }
  agentSilenceThresholdMinutes.value = 10
}

async function loadEditionMode() {
  try {
    const status = await setupService.checkEnhancedStatus()
    isCe.value = isCeModeValue(status?.mode)
  } catch {
    isCe.value = false
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
    const normalized = normalizeTab(route.query.tab)
    if (normalized) activeTab.value = normalized
  }

  // Check Serena MCP status
  await checkSerenaStatus()
  await loadEditionMode()

  // Load settings from store
  await settingsStore.loadSettings()
  // Apply stored notification settings to local state
  if (settingsStore.settings.notifications) {
    settings.value.notifications = { ...settings.value.notifications, ...settingsStore.settings.notifications }
  }
  if (isCe.value) {
    agentSilenceThresholdMinutes.value = await settingsStore.loadAgentSilenceThreshold()
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

})

watch(activeTab, (newTab) => {
  // Replace (don't push) so browser back button returns to the previous PAGE,
  // not through every intermediate tab click within ToolsView.
  const currentQuery = router.currentRoute.value.query
  if (currentQuery.tab !== newTab) {
    router.replace({ query: { ...currentQuery, tab: newTab } })
  }
})

watch(
  () => router.currentRoute.value.query.tab,
  (tab) => {
    if (!tab) return
    const normalized = normalizeTab(tab)
    if (normalized) activeTab.value = normalized
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

</script>

<style lang="scss" scoped>
@use '../styles/design-tokens' as *;
.settings-subtitle {
  color: var(--text-muted);
}

.settings-card {
  background: $elevation-raised;
  border-radius: $border-radius-rounded;
}

/* Startup quick-launch cards (mirrors Home page .quick-card) */
.startup-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.startup-card {
  background: rgb(var(--v-theme-surface));
  border-radius: $border-radius-rounded;
  padding: 20px;
  cursor: pointer;
  transition: all $transition-normal;
  position: relative;
  overflow: hidden;
}

.startup-card:hover {
  transform: translateY(-3px);
  box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255,255,255,0.10)), 0 10px 20px -6px rgba(0,0,0,0.25);
}

.startup-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--card-accent, rgba(255,255,255,0.10));
  opacity: 0;
  transition: opacity $transition-normal;
}

.startup-card:hover::before {
  opacity: 1;
}

.startup-card-icon {
  width: 40px;
  height: 40px;
  border-radius: $border-radius-default;
  display: grid;
  place-items: center;
  margin-bottom: 12px;
}

.startup-card-title {
  font-size: 0.92rem;
  font-weight: 600;
  margin-bottom: 5px;
}

.startup-card-desc {
  font-size: 0.75rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

@media (max-width: 599px) {
  .startup-cards {
    grid-template-columns: 1fr;
  }
}

/* Integration page section labels (IBM Plex Mono uppercase) */
.integration-section-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.62rem;
  color: $color-text-muted;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 12px;
  margin-top: 28px;
}

.integration-section-label:first-of-type {
  margin-top: 0;
}

/* Connect cards — full-width horizontal rows, stacked vertically. */
.connect-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 1100px;
}

/* Integrations section divider should follow theme */
.integrations-divider {
  --v-theme-overlay-multiplier: 1; /* ensure visibility */
  border-color: var(--v-theme-on-surface);
  opacity: 0.3;
}

.startup-help-icon {
  cursor: pointer;
  opacity: 0.7;
  transition: opacity $transition-normal ease;
}

.startup-help-icon:hover {
  opacity: 1;
}

/* Pill toggle row */
.pill-toggle-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.pill-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: $border-radius-pill;
  padding: 8px 18px;
  font-size: 0.78rem;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: background $transition-normal, color $transition-normal, box-shadow $transition-normal;
  background: transparent;
  color: var(--text-muted);
  border: none;
  --smooth-border-color: #{$color-pill-border};
}

.pill-toggle:hover {
  color: $color-text-hover;
}

.pill-toggle--active,
.pill-toggle--active:hover {
  background: rgba($color-brand-yellow, 0.12);
  color: $color-brand-yellow;
  box-shadow: none;
}

.pill-toggle-icon {
  flex-shrink: 0;
}

.pill-tabs-content {
  padding: 16px 0;
}

/* Credentials section -- compact API key manager folded under Connect tab */
.credentials-section {
  margin-top: 24px;
  padding-top: 24px;
  position: relative;
}

.credentials-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: rgba(255, 255, 255, 0.08);
}

</style>
