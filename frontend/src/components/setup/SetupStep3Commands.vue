<template>
  <div class="step-commands">
    <p class="step-heading">Install commands and agents</p>

    <!-- Tool tabs (only if multiple connected tools) -->
    <div v-if="tools.length > 1" class="tool-tabs" role="tablist">
      <button
        v-for="tool in tools"
        :key="tool.id"
        role="tab"
        :aria-selected="activeToolId === tool.id"
        :class="['tool-tab', 'smooth-border', { 'tool-tab--active': activeToolId === tool.id }]"
        @click="activeToolId = tool.id"
      >
        <img :src="tool.logo" :alt="tool.name" class="tool-tab-logo" />
        <span>{{ tool.name }}</span>
      </button>
    </div>

    <!-- Active tool panel -->
    <div class="tool-panel" role="tabpanel">

      <!-- 1. Copy Prompt Button -->
      <div class="panel-section">
        <p class="instruction-text">
          Paste this into your {{ activeTool.name }} terminal and press Enter
        </p>

        <!-- Loading state -->
        <div v-if="promptLoading[activeToolId]" class="prompt-loading">
          <v-progress-circular size="20" width="2" indeterminate :color="COLOR_MUTED" />
          <span class="prompt-loading-text">Preparing prompt...</span>
        </div>

        <!-- Error state -->
        <div v-else-if="promptErrors[activeToolId]" class="prompt-error">
          <v-icon size="16" :color="COLOR_ERROR_LIGHT">mdi-alert-circle-outline</v-icon>
          <span class="prompt-error-text">{{ promptErrors[activeToolId] }}</span>
          <v-btn size="small" variant="outlined" class="retry-btn" @click="fetchPrompt(activeToolId)">
            Retry
          </v-btn>
        </div>

        <!-- Copy button (no visible prompt text) -->
        <div v-else class="copy-prompt-row">
          <v-btn
            color="primary"
            variant="flat"
            prepend-icon="mdi-content-copy"
            :disabled="!prompts[activeToolId]"
            @click="handleCopyPrompt(activeToolId)"
          >
            Copy Prompt
          </v-btn>
        </div>
      </div>

      <!-- 2. Slash commands status -->
      <div class="checklist-item">
        <v-icon
          size="20"
          :color="toolStatus[activeToolId]?.commands ? COLOR_SUCCESS : COLOR_MUTED"
        >
          {{ toolStatus[activeToolId]?.commands ? 'mdi-check-circle' : 'mdi-checkbox-blank-circle-outline' }}
        </v-icon>
        <span :class="['checklist-text', { 'checklist-text--done': toolStatus[activeToolId]?.commands }]">
          Slash commands installed
        </span>
      </div>

      <!-- 3. Agent command instruction -->
      <div class="panel-section agent-section">
        <p class="instruction-text">
          Run <code class="inline-code">{{ getAgentCommand(activeToolId) }}</code> in your {{ activeTool.name }} terminal session
        </p>
      </div>

      <!-- 4. Agents downloaded status -->
      <div class="checklist-item">
        <v-icon
          size="20"
          :color="toolStatus[activeToolId]?.agents ? COLOR_SUCCESS : COLOR_MUTED"
        >
          {{ toolStatus[activeToolId]?.agents ? 'mdi-check-circle' : 'mdi-checkbox-blank-circle-outline' }}
        </v-icon>
        <span :class="['checklist-text', { 'checklist-text--done': toolStatus[activeToolId]?.agents }]">
          Agents downloaded
        </span>
        <Transition name="fade-slide">
          <p v-if="toolStatus[activeToolId]?.agents" class="agent-refresh-tip">
            You can run this command again when you update your agent templates to refresh agents from your tool.
          </p>
        </Transition>
      </div>
    </div>

    <!-- Skip link -->
    <div class="skip-area">
      <span
        class="skip-link"
        role="button"
        tabindex="0"
        @click="$emit('skip')"
        @keydown.enter.prevent="$emit('skip')"
      >
        Skip — I'll do this later
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useClipboard } from '@/composables/useClipboard'
import { useToast } from '@/composables/useToast'
import { useWebSocketStore } from '@/stores/websocket'

/* design-token-exempt: Vuetify color props require raw values, not SCSS vars or CSS custom properties */
const COLOR_MUTED = '#8f97b7' // $lightest-blue
const COLOR_SUCCESS = '#6bcf7f' // $gradient-brand-end
const COLOR_ERROR_LIGHT = '#e57373' // lightened $color-status-error

const TOOL_META = {
  claude_code: { name: 'Claude Code', logo: '/claude_pix.svg' },
  codex_cli: { name: 'Codex CLI', logo: '/icons/codex_mark_white.svg' },
  gemini_cli: { name: 'Gemini CLI', logo: '/gemini-icon.svg' },
}

const AGENT_COMMANDS = {
  claude_code: '/gil_get_agents',
  codex_cli: '$gil-get-agents',
  gemini_cli: '/gil_get_agents',
}

const props = defineProps({
  selectedTools: {
    type: Array,
    required: true,
  },
  connectedTools: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['can-proceed', 'step-data', 'skip'])

const { copy: clipboardCopy } = useClipboard()
const { showToast } = useToast()
const wsStore = useWebSocketStore()

// Derive tool list from connectedTools
const tools = computed(() =>
  props.connectedTools.map((id) => ({
    id,
    ...TOOL_META[id],
  })),
)

const activeTool = computed(() => TOOL_META[activeToolId.value] || { name: 'Tool' })

// Active tab
const activeToolId = ref(props.connectedTools[0] || 'claude_code')

// Bootstrap prompt state per tool (initialize eagerly so template sees loading state)
const prompts = reactive(Object.fromEntries(props.connectedTools.map((id) => [id, null])))
const promptLoading = reactive(Object.fromEntries(props.connectedTools.map((id) => [id, true])))
const promptErrors = reactive(Object.fromEntries(props.connectedTools.map((id) => [id, null])))

// Installation status per tool (initialize eagerly)
const toolStatus = reactive(
  Object.fromEntries(props.connectedTools.map((id) => [id, { commands: false, agents: false }])),
)

// Fetch bootstrap prompt from backend
async function fetchBootstrapPrompt(toolId) {
  const response = await fetch(
    `/api/download/bootstrap-prompt?platform=${toolId}`,
    {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
      },
    },
  )
  if (!response.ok) throw new Error(`Failed: ${response.status}`)
  const data = await response.json()
  return data.prompt
}

async function fetchPrompt(toolId) {
  promptLoading[toolId] = true
  promptErrors[toolId] = null
  try {
    const promptText = await fetchBootstrapPrompt(toolId)
    prompts[toolId] = promptText
  } catch (e) {
    promptErrors[toolId] = e.message || 'Failed to fetch bootstrap prompt'
  } finally {
    promptLoading[toolId] = false
  }
}

// Fetch prompts for all connected tools
function fetchAllPrompts() {
  for (const id of props.connectedTools) {
    fetchPrompt(id)
  }
}

// Copy prompt — resets both checkboxes until server detects real downloads
async function handleCopyPrompt(toolId) {
  const text = prompts[toolId]
  if (!text) return

  // Reset status — user is re-running the flow
  if (toolStatus[toolId]) {
    toolStatus[toolId].commands = false
    toolStatus[toolId].agents = false
  }

  const success = await clipboardCopy(text)
  if (success) {
    showToast({ message: 'Bootstrap prompt copied to clipboard', type: 'success' })
  } else {
    showToast({ message: 'Copy failed -- select the text and press Ctrl+C', type: 'warning' })
  }
}

function getAgentCommand(toolId) {
  return AGENT_COMMANDS[toolId] || '/gil_get_agents'
}

// Check if a tool has commands installed (agents are optional for proceeding)
function isToolComplete(toolId) {
  return !!toolStatus[toolId]?.commands
}

// can-proceed: at least 1 tool with both checkmarks
const canProceed = computed(() =>
  props.connectedTools.some((id) => isToolComplete(id)),
)

// Installed tools list for step-data
const installedTools = computed(() =>
  props.connectedTools.filter((id) => isToolComplete(id)),
)

// Emit can-proceed whenever status changes
watch(canProceed, (val) => {
  emit('can-proceed', val)
}, { immediate: true })

// Emit step-data whenever installed tools change
watch(installedTools, (val) => {
  emit('step-data', { installedTools: [...val] })
}, { deep: true })

// WebSocket subscriptions
let unsubCommands = null
let unsubAgents = null

function handleCommandsInstalled(payload) {
  const toolName = payload?.tool_name
  if (!toolName) return

  // "all" means the CLI downloaded slash commands (we can't tell which tool)
  if (toolName === 'all') {
    for (const id of props.connectedTools) {
      if (toolStatus[id]) toolStatus[id].commands = true
    }
    return
  }

  if (toolStatus[toolName]) {
    toolStatus[toolName].commands = true
  }
}

function handleAgentsDownloaded() {
  for (const id of props.connectedTools) {
    if (toolStatus[id]) {
      toolStatus[id].agents = true
    }
  }
}

onMounted(() => {
  fetchAllPrompts()
  unsubCommands = wsStore.on('setup:commands_installed', handleCommandsInstalled)
  unsubAgents = wsStore.on('setup:agents_downloaded', handleAgentsDownloaded)
})

onUnmounted(() => {
  if (unsubCommands) unsubCommands()
  if (unsubAgents) unsubAgents()
})
</script>

<style scoped lang="scss">
@use '../../styles/variables' as *;
@use '../../styles/design-tokens' as *;
.step-commands {
  max-width: 680px;
  margin: 0 auto;
}

.step-heading {
  font-size: 1rem;
  font-weight: 500;
  color: $color-text-primary;
  margin-bottom: 20px;
  text-align: center;
}

/* Tool tabs */
.tool-tabs {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-bottom: 20px;
}

.tool-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: $elevation-elevated;
  border: none;
  border-radius: $border-radius-default;
  color: $lightest-blue;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 500;
  transition: color 250ms ease-out, box-shadow 250ms ease-out;
}

.tool-tab--active {
  color: $color-brand-yellow;
  --smooth-border-color: #{$color-brand-yellow};
}

.tool-tab:hover:not(.tool-tab--active) {
  color: $color-text-primary;
}

.tool-tab:focus-visible {
  outline: 2px solid $color-brand-yellow;
  outline-offset: 2px;
}

.tool-tab-logo {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.tab-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: $lightest-blue;
  transition: background 250ms ease-out;
}

.tab-status-dot--complete {
  background: $gradient-brand-end;
}

/* Panel sections */
.panel-section {
  margin-bottom: 20px;
}

.section-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: $color-text-primary;
  margin-bottom: 10px;
}

/* Instruction text */
.instruction-text {
  font-size: 0.875rem;
  color: $color-text-primary;
  margin-bottom: 12px;
  text-align: center;
}

.inline-code {
  font-family: "Roboto Mono", "Courier New", monospace;
  font-size: 0.8125rem;
  background: rgba($color-brand-yellow, 0.1);
  color: $color-brand-yellow;
  padding: 2px 6px;
  border-radius: $border-radius-sharp;
}

/* Copy prompt row */
.copy-prompt-row {
  display: flex;
  justify-content: center;
  margin-bottom: 8px;
}

/* Loading state */
.prompt-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 16px;
}

.prompt-loading-text {
  font-size: 0.875rem;
  color: $lightest-blue;
}

/* Error state */
.prompt-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(229, 115, 115, 0.08); /* design-token-exempt: error background tint, no exact token */
  border-radius: $border-radius-default;
}

.prompt-error-text {
  flex: 1;
  font-size: 0.875rem;
  color: #e57373; /* design-token-exempt: lightened error variant, no exact token */
}

.retry-btn {
  color: $color-brand-yellow !important;
  border-color: $color-brand-yellow !important;
  text-transform: none;
  font-size: 0.75rem;
}

/* Agent section */
.agent-section {
  margin-top: 20px;
}

/* Checklist items */
.checklist-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.checklist-text {
  font-size: 0.875rem;
  color: $lightest-blue;
  transition: color 250ms ease-out;
}

.agent-refresh-tip {
  width: 100%;
  margin-top: 6px;
  margin-left: 30px;
  font-size: 0.8125rem;
  color: $color-brand-yellow;
}

.checklist-text--done {
  color: $gradient-brand-end;
}

/* Tip text */
.tip-text {
  font-size: 0.8125rem;
  color: $lightest-blue;
  margin-top: 8px;
  line-height: 1.5;
  font-style: italic;
}

/* Skip area */
.skip-area {
  text-align: center;
  margin-top: 12px;
  padding-top: 8px;
}

.skip-link {
  font-size: 0.8125rem;
  color: $lightest-blue;
  cursor: pointer;
  text-decoration: none;
  transition: color 250ms ease-out, text-decoration 250ms ease-out;
}

.skip-link:hover,
.skip-link:focus-visible {
  color: $color-brand-yellow;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.skip-link:focus-visible {
  outline: 2px solid $color-brand-yellow;
  outline-offset: 2px;
  border-radius: $border-radius-sharp;
}

/* Transition for post-install command */
.fade-slide-enter-active {
  transition: opacity 250ms ease-out, transform 250ms ease-out;
}

.fade-slide-leave-active {
  transition: opacity 200ms ease-in, transform 200ms ease-in;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* Responsive: mobile */
@media (max-width: 599px) {
  .tool-tabs {
    flex-direction: column;
    align-items: stretch;
  }

  .tool-tab {
    justify-content: center;
  }

  .code-block-header {
    flex-direction: column;
    gap: 6px;
    align-items: flex-start;
  }

  .copy-btn {
    align-self: flex-end;
  }
}
</style>
