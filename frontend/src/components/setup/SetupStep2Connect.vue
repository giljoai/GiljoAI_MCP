<template>
  <div class="step-connect" data-testid="step2-connect">
    <!-- Eyebrow + title (action-window header — one tool at a time) -->
    <div class="connect-eyebrow">{{ eyebrow }}</div>
    <h2 class="connect-title">{{ title }}</h2>

    <ConnectToolCard
      :key="activeToolId"
      :tool-id="activeToolId"
      :connected="activeConnected"
      :key-mode="!!keyMode[activeToolId]"
      :connected-next="connectedNext"
      :advance-label="advanceLabel"
      @advance="handleAdvance"
      @toggle-key-mode="toggleKeyMode"
      @mark-configured="markActiveConfigured"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useWebSocketStore } from '@/stores/websocket'
import { toolName } from '@/config/setupTools'
import ConnectToolCard from './ConnectToolCard.vue'

const props = defineProps({
  selectedTools: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['can-proceed', 'step-data', 'walk-state', 'advance-step'])

const wsStore = useWebSocketStore()

// Walk position + per-tool state (the mock state machine: toolIdx, conn{}, keyMode{}).
const toolIdx = ref(0)
const connectionStatus = reactive(
  Object.fromEntries(props.selectedTools.map((id) => [id, 'waiting'])),
)
const keyMode = reactive({})

const order = computed(() => props.selectedTools)
const activeToolId = computed(
  () => order.value[Math.min(toolIdx.value, Math.max(0, order.value.length - 1))] || order.value[0],
)
const activeToolName = computed(() => toolName(activeToolId.value))
const activeConnected = computed(() => connectionStatus[activeToolId.value] === 'connected')

const isLast = computed(() => toolIdx.value >= order.value.length - 1)

// Middot separators, never an em dash: FE-6259b locks "no em dash in step-2 copy".
const eyebrow = computed(
  () => `02 · CONNECT · TOOL ${toolIdx.value + 1} OF ${order.value.length}`,
)
const title = computed(() =>
  activeToolId.value === 'generic' ? 'Connect your MCP client.' : `Connect ${activeToolName.value}.`,
)
const connectedNext = computed(() => {
  if (isLast.value) return 'All tools connected. Agents and skills are next.'
  return `${toolName(order.value[toolIdx.value + 1])} is next. Same move.`
})
const advanceLabel = computed(() => (isLast.value ? 'Install agents & skills' : 'Next tool'))

function toggleKeyMode() {
  keyMode[activeToolId.value] = !keyMode[activeToolId.value]
}

// Advance the walk: next tool, or (on the last tool) advance the wizard step.
function handleAdvance() {
  if (!isLast.value) {
    toolIdx.value += 1
  } else {
    emit('advance-step')
  }
}

// "I already configured this" — marks the ACTIVE tool connected only (ratified
// behavior change from the old marks-ALL, proposal §6 / CODE_GUIDANCE event wiring:
// with the walk-one-tool-at-a-time model, manual confirmation is per-tool).
function markActiveConfigured() {
  connectionStatus[activeToolId.value] = 'connected'
}

// setup:tool_connected is GENERIC — the server cannot tell which CLI connected
// (proposal §6). Contract: flip the ACTIVE tool only (the screen the user is on).
// Rail sub-checklist state comes from wizard progression (connectionStatus), never
// event attribution.
let wsUnsub = null
function handleToolConnected(payload) {
  // The server emits a GENERIC event (tool_name='mcp_connected') — it cannot tell
  // which CLI connected (proposal §6: do not attempt per-tool attribution). Flip the
  // tool currently being walked.
  if (payload?.tool_name === 'mcp_connected') {
    connectionStatus[activeToolId.value] = 'connected'
  }
}

// Gate: proceed once >= 1 tool is connected (footer Next; the hero drives the walk).
const hasConnectedTool = computed(() =>
  Object.values(connectionStatus).some((s) => s === 'connected'),
)
watch(hasConnectedTool, (val) => emit('can-proceed', val), { immediate: true })

const connectedTools = computed(() =>
  Object.entries(connectionStatus)
    .filter(([, status]) => status === 'connected')
    .map(([id]) => id),
)
watch(connectedTools, (val) => emit('step-data', { connectedTools: val }), { deep: true, immediate: true })

// Rail sub-rows: the overlay renders per-tool Connect sub-rows from this walk state
// (wizard progression, never event attribution).
const walkState = computed(() => ({
  order: order.value,
  activeId: activeToolId.value,
  conn: { ...connectionStatus },
}))
watch(walkState, (val) => emit('walk-state', val), { immediate: true, deep: true })

onMounted(() => {
  // Resume at the first not-yet-connected tool.
  const firstUnconnected = order.value.findIndex((id) => connectionStatus[id] !== 'connected')
  toolIdx.value = firstUnconnected === -1 ? 0 : firstUnconnected
  wsUnsub = wsStore.on('setup:tool_connected', handleToolConnected)
})

onUnmounted(() => {
  if (wsUnsub) wsUnsub()
})
</script>

<style scoped lang="scss">
@use '../../styles/variables' as *;
@use '../../styles/design-tokens' as *;

.step-connect {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.connect-eyebrow {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: $color-brand-yellow;
  margin-bottom: 8px;
}

.connect-title {
  font-family: 'Outfit', $typography-font-primary;
  font-weight: 700;
  font-size: 1.4rem;
  letter-spacing: -0.02em;
  color: $color-text-primary;
  margin: 0 0 16px;
}
</style>
