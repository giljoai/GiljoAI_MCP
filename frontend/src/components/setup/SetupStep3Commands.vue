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
        <span
          :class="[
            'tab-status-dot',
            isToolComplete(tool.id) ? 'tab-status-dot--complete' : '',
          ]"
        />
      </button>
    </div>

    <!-- Active tool panel -->
    <div class="tool-panel" role="tabpanel">
      <!-- 1. Bootstrap Prompt Block -->
      <div class="panel-section">
        <label class="section-label">
          Paste this into your {{ activeTool.name }} terminal and press Enter
        </label>

        <!-- Loading state -->
        <div v-if="promptLoading[activeToolId]" class="prompt-loading">
          <v-progress-circular size="20" width="2" indeterminate color="#8f97b7" />
          <span class="prompt-loading-text">Fetching bootstrap prompt...</span>
        </div>

        <!-- Error state -->
        <div v-else-if="promptErrors[activeToolId]" class="prompt-error">
          <v-icon size="16" color="#e57373">mdi-alert-circle-outline</v-icon>
          <span class="prompt-error-text">{{ promptErrors[activeToolId] }}</span>
          <v-btn
            size="small"
            variant="outlined"
            class="retry-btn"
            @click="fetchPrompt(activeToolId)"
          >
            Retry
          </v-btn>
        </div>

        <!-- Prompt code block -->
        <div v-else class="code-block smooth-border">
          <div class="code-block-header">
            <span class="code-block-label">Bootstrap Prompt</span>
            <v-btn
              size="small"
              variant="outlined"
              class="copy-btn"
              aria-label="Copy bootstrap prompt to clipboard"
              @click="copyPrompt(activeToolId)"
            >
              <v-icon size="14" start>mdi-content-copy</v-icon>
              Copy to Clipboard
            </v-btn>
          </div>
          <pre class="code-content">{{ prompts[activeToolId] || '' }}</pre>
        </div>
      </div>

      <!-- 2. Mini-Checklist -->
      <div class="panel-section">
        <label class="section-label">Installation Status</label>
        <div class="checklist">
          <div class="checklist-item">
            <v-icon
              size="20"
              :color="toolStatus[activeToolId]?.commands ? '#6bcf7f' : '#8f97b7'"
              class="checklist-icon"
            >
              {{ toolStatus[activeToolId]?.commands ? 'mdi-check-circle' : 'mdi-checkbox-blank-circle-outline' }}
            </v-icon>
            <span
              :class="[
                'checklist-text',
                { 'checklist-text--done': toolStatus[activeToolId]?.commands },
              ]"
            >
              Slash commands installed
            </span>
          </div>
          <div class="checklist-item">
            <v-icon
              size="20"
              :color="toolStatus[activeToolId]?.agents ? '#6bcf7f' : '#8f97b7'"
              class="checklist-icon"
            >
              {{ toolStatus[activeToolId]?.agents ? 'mdi-check-circle' : 'mdi-checkbox-blank-circle-outline' }}
            </v-icon>
            <span
              :class="[
                'checklist-text',
                { 'checklist-text--done': toolStatus[activeToolId]?.agents },
              ]"
            >
              Agents downloaded
            </span>
          </div>
        </div>
      </div>

      <!-- 3. Post-Install Command (appears after commands installed) -->
      <Transition name="fade-slide">
        <div v-if="toolStatus[activeToolId]?.commands" class="panel-section">
          <label class="section-label">
            Now run this command to install agent templates
          </label>
          <div class="code-block code-block--secondary smooth-border">
            <div class="code-block-header">
              <span class="code-block-label">Agent Import Command</span>
              <v-btn
                icon="mdi-content-copy"
                size="x-small"
                variant="text"
                aria-label="Copy agent import command"
                @click="copyAgentCommand(activeToolId)"
              />
            </div>
            <pre class="code-content">{{ getAgentCommand(activeToolId) }}</pre>
          </div>
          <p class="tip-text">
            Tip: Select "Use default model for all" on first import for fastest setup
          </p>
        </div>
      </Transition>
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

// Clipboard helpers
async function copyPrompt(toolId) {
  const text = prompts[toolId]
  if (!text) return
  const success = await clipboardCopy(text)
  if (success) {
    showToast({ message: 'Bootstrap prompt copied to clipboard!', type: 'success' })
    // Mark commands as installed once user copies the prompt
    if (toolStatus[toolId]) {
      toolStatus[toolId].commands = true
    }
  } else {
    showToast({ message: 'Copy failed -- select the text and press Ctrl+C', type: 'warning' })
  }
}

async function copyAgentCommand(toolId) {
  const text = getAgentCommand(toolId)
  const success = await clipboardCopy(text)
  if (success) {
    showToast({ message: 'Command copied to clipboard!', type: 'success' })
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

<style scoped>
.step-commands {
  max-width: 680px;
  margin: 0 auto;
}

.step-heading {
  font-size: 1rem;
  font-weight: 500;
  color: #e1e1e1;
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
  background: #1e3147;
  border: none;
  border-radius: 8px;
  color: #8f97b7;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 500;
  transition: color 250ms ease-out, box-shadow 250ms ease-out;
}

.tool-tab--active {
  color: #ffc300;
  --smooth-border-color: #ffc300;
}

.tool-tab:hover:not(.tool-tab--active) {
  color: #e1e1e1;
}

.tool-tab:focus-visible {
  outline: 2px solid #ffc300;
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
  background: #8f97b7;
  transition: background 250ms ease-out;
}

.tab-status-dot--complete {
  background: #6bcf7f;
}

/* Panel sections */
.panel-section {
  margin-bottom: 20px;
}

.section-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #e1e1e1;
  margin-bottom: 10px;
}

/* Loading state */
.prompt-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 24px;
  background: #0e1c2d;
  border-radius: 8px;
}

.prompt-loading-text {
  font-size: 0.875rem;
  color: #8f97b7;
}

/* Error state */
.prompt-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(229, 115, 115, 0.08);
  border-radius: 8px;
}

.prompt-error-text {
  flex: 1;
  font-size: 0.875rem;
  color: #e57373;
}

.retry-btn {
  color: #ffc300 !important;
  border-color: #ffc300 !important;
  text-transform: none;
  font-size: 0.75rem;
}

/* Code blocks */
.code-block {
  position: relative;
  background: #0e1c2d;
  border-radius: 8px;
  padding: 0;
  overflow: hidden;
}

.code-block--secondary {
  background: #0e1c2d;
}

.code-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: rgba(49, 80, 116, 0.3);
}

.code-block-label {
  font-size: 0.6875rem;
  font-weight: 600;
  color: #8f97b7;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.copy-btn {
  color: #ffc300 !important;
  border-color: #ffc300 !important;
  text-transform: none;
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0;
}

.code-content {
  padding: 12px;
  margin: 0;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: #e1e1e1;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
}

/* Checklist */
.checklist {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.checklist-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.checklist-icon {
  transition: color 250ms ease-out;
}

.checklist-text {
  font-size: 0.875rem;
  color: #8f97b7;
  transition: color 250ms ease-out;
}

.checklist-text--done {
  color: #6bcf7f;
}

/* Tip text */
.tip-text {
  font-size: 0.8125rem;
  color: #8f97b7;
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
  color: #8f97b7;
  cursor: pointer;
  text-decoration: none;
  transition: color 250ms ease-out, text-decoration 250ms ease-out;
}

.skip-link:hover,
.skip-link:focus-visible {
  color: #ffc300;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.skip-link:focus-visible {
  outline: 2px solid #ffc300;
  outline-offset: 2px;
  border-radius: 2px;
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
