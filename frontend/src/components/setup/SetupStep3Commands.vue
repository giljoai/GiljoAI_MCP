<template>
  <div class="step-commands">
    <p class="step-heading">Install Skills and Agents</p>

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

      <!-- Primary path: giljo_setup -->
      <div class="panel-section">
        <p class="instruction-text">
          Ask your {{ activeTool.name }} to run:
        </p>
        <div class="setup-command-row">
          <code class="setup-command">giljo_setup</code>
        </div>
        <p class="instruction-hint">
          This installs slash commands and agent templates automatically
        </p>
      </div>

      <!-- Status checklist -->
      <div class="checklist-centered">
        <div class="checklist-item">
          <v-icon
            size="20"
            :color="toolStatus[activeToolId]?.commands ? COLOR_SUCCESS : COLOR_MUTED"
          >
            {{ toolStatus[activeToolId]?.commands ? 'mdi-check-circle' : 'mdi-checkbox-blank-circle-outline' }}
          </v-icon>
          <span :class="['checklist-text', { 'checklist-text--done': toolStatus[activeToolId]?.commands }]">
            Skills downloaded
          </span>
        </div>

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
        </div>
      </div>

      <Transition name="fade-slide">
        <p v-if="toolStatus[activeToolId]?.agents" class="instruction-hint" style="text-align: center;">
          Run <code class="inline-code">{{ getAgentCommand(activeToolId) }}</code> in the future to refresh agent templates
        </p>
      </Transition>

      <!-- Manual setup pointer -->
      <p class="manual-setup-hint">
        For manual setup, go to <strong>Settings &gt; Integrations</strong>
      </p>
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
import { useWebSocketStore } from '@/stores/websocket'

/* design-token-exempt: Vuetify color props require raw values, not SCSS vars or CSS custom properties */
const COLOR_MUTED = '#8f97b7' // $lightest-blue
const COLOR_SUCCESS = '#6bcf7f' // $gradient-brand-end

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

// Installation status per tool (initialize eagerly)
const toolStatus = reactive(
  Object.fromEntries(props.connectedTools.map((id) => [id, { commands: false, agents: false }])),
)

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

function handleBootstrapComplete() {
  // giljo_setup installs both commands and agents in one shot
  for (const id of props.connectedTools) {
    if (toolStatus[id]) {
      toolStatus[id].commands = true
      toolStatus[id].agents = true
    }
  }
}

let unsubBootstrap = null

onMounted(() => {
  unsubCommands = wsStore.on('setup:commands_installed', handleCommandsInstalled)
  unsubAgents = wsStore.on('setup:agents_downloaded', handleAgentsDownloaded)
  unsubBootstrap = wsStore.on('setup:bootstrap_complete', handleBootstrapComplete)
})

onUnmounted(() => {
  if (unsubCommands) unsubCommands()
  if (unsubAgents) unsubAgents()
  if (unsubBootstrap) unsubBootstrap()
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

/* giljo_setup command display */
.setup-command-row {
  display: flex;
  justify-content: center;
  margin-bottom: 8px;
}

.setup-command {
  font-family: "Roboto Mono", "Courier New", monospace;
  font-size: 1.125rem;
  font-weight: 600;
  background: rgba($color-brand-yellow, 0.1);
  color: $color-brand-yellow;
  padding: 8px 20px;
  border-radius: $border-radius-default;
}

.instruction-hint {
  font-size: 0.8125rem;
  color: $lightest-blue;
  text-align: center;
  margin-bottom: 16px;
}

/* Manual setup hint */
.manual-setup-hint {
  font-size: 0.8125rem;
  color: $lightest-blue;
  text-align: center;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

/* Checklist items */
.checklist-centered {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 8px;
}

.checklist-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
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
