<template>
  <div class="tools-directory smooth-border" data-testid="tools-connect-directory">
    <!-- Fleet rail — the user's tools with live status + "+ Add a tool" -->
    <aside class="dir-rail">
      <div class="dir-rail-top">
        <img src="/icons/Giljo_YW_Face.svg" alt="" class="dir-rail-logo" />
        <span class="dir-rail-kicker">YOUR TOOLS</span>
      </div>

      <div class="dir-rail-list">
        <button
          v-for="tool in fleet"
          :key="tool.id"
          :class="['dir-rail-row', { 'dir-rail-row--active': mode === 'card' && selectedId === tool.id }]"
          :data-testid="`dir-tool-${tool.id}`"
          @click="selectTool(tool.id)"
        >
          <span :class="['dir-rail-dot', `dir-rail-dot--${statusFor(tool.id)}`]" />
          <span class="dir-rail-label">{{ tool.name }}</span>
          <span class="dir-rail-status">{{ statusLabel(statusFor(tool.id)) }}</span>
        </button>

        <button
          :class="['dir-rail-row', 'dir-rail-row--add', { 'dir-rail-row--active': mode === 'picker' }]"
          data-testid="dir-add-tool"
          @click="openPicker"
        >
          <span class="dir-rail-add-icon"><v-icon size="14">mdi-plus</v-icon></span>
          <span class="dir-rail-label">Add a tool</span>
        </button>
      </div>
    </aside>

    <!-- Action window -->
    <div class="dir-window">
      <!-- Tool picker (from "+ Add a tool") -->
      <template v-if="mode === 'picker'">
        <div class="dir-eyebrow">TOOLS · ADD A TOOL</div>
        <h2 class="dir-title">Pick a tool to connect.</h2>
        <div class="dir-picker-grid">
          <div
            v-for="tool in SETUP_TOOLS"
            :key="tool.id"
            class="dir-picker-card smooth-border"
            :data-testid="`dir-pick-${tool.id}`"
            role="button"
            tabindex="0"
            @click="addTool(tool.id)"
            @keydown.enter.prevent="addTool(tool.id)"
            @keydown.space.prevent="addTool(tool.id)"
          >
            <span class="dir-picker-well">
              <img v-if="tool.logo" :src="tool.logo" :alt="tool.name" class="dir-picker-logo" />
              <v-icon v-else size="20">{{ tool.icon }}</v-icon>
            </span>
            <span class="dir-picker-name">{{ tool.name }}</span>
          </div>
        </div>
      </template>

      <!-- Selected tool's connect card -->
      <template v-else-if="selectedId">
        <div class="dir-eyebrow">TOOLS · {{ selectedName }}</div>
        <h2 class="dir-title">{{ selectedName }}.</h2>
        <ConnectToolCard
          :key="selectedId"
          :tool-id="selectedId"
          :connected="connStatus[selectedId] === 'connected'"
          :key-mode="!!keyMode[selectedId]"
          connected-next="This tool is live. Manage or remove it here anytime."
          :advance-label="''"
          :show-already-configured="true"
          @toggle-key-mode="toggleKeyMode"
          @mark-configured="markConfigured"
        />
        <div class="dir-window-foot">
          <span class="dir-remove-link" role="button" tabindex="0" data-testid="dir-remove-tool" @click="removeTool(selectedId)">
            Remove tool
          </span>
        </div>
      </template>

      <!-- Empty fleet -->
      <template v-else>
        <div class="dir-empty" data-testid="dir-empty">
          <p>No tools yet. Add your first with <strong>+ Add a tool</strong>.</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { useWebSocketStore } from '@/stores/websocket'
import { SETUP_TOOLS, TOOL_META, toolName } from '@/config/setupTools'
import ConnectToolCard from '@/components/setup/ConnectToolCard.vue'

const userStore = useUserStore()
const wsStore = useWebSocketStore()

// Fleet = the user's chosen tools (persisted via setup_selected_tools). "+ Add a tool"
// appends here. Per-tool connection status is SESSION-live (D3: persisted per-tool
// state is parked — the connect event is generic, so there is nothing to attribute).
const fleetIds = ref([...(userStore.currentUser?.setup_selected_tools ?? [])])
const fleet = computed(() =>
  fleetIds.value.filter((id) => TOOL_META[id]).map((id) => ({ id, name: toolName(id) })),
)

const connStatus = reactive({})
const keyMode = reactive({})
const selectedId = ref(fleetIds.value[0] || null)
const mode = ref(selectedId.value ? 'card' : 'picker')

const selectedName = computed(() => toolName(selectedId.value))

function statusFor(id) {
  if (connStatus[id] === 'connected') return 'connected'
  if (mode.value === 'card' && selectedId.value === id) return 'waiting'
  return 'idle'
}
function statusLabel(state) {
  return state === 'connected' ? 'Connected' : state === 'waiting' ? 'Waiting' : 'Not set up'
}

function selectTool(id) {
  selectedId.value = id
  mode.value = 'card'
}

function openPicker() {
  mode.value = 'picker'
}

async function addTool(id) {
  if (!fleetIds.value.includes(id)) {
    fleetIds.value = [...fleetIds.value, id]
    try {
      await userStore.updateSetupState({ setup_selected_tools: [...fleetIds.value] })
    } catch (e) {
      console.warn('[ToolsConnectDirectory] Failed to persist tool selection:', e)
    }
  }
  selectTool(id)
}

async function removeTool(id) {
  fleetIds.value = fleetIds.value.filter((t) => t !== id)
  delete connStatus[id]
  try {
    await userStore.updateSetupState({ setup_selected_tools: [...fleetIds.value] })
  } catch (e) {
    console.warn('[ToolsConnectDirectory] Failed to persist tool removal:', e)
  }
  if (selectedId.value === id) {
    selectedId.value = fleetIds.value[0] || null
    mode.value = selectedId.value ? 'card' : 'picker'
  }
}

function toggleKeyMode() {
  keyMode[selectedId.value] = !keyMode[selectedId.value]
}

// "I already configured this" — marks the SELECTED tool only (same active-only
// contract as the wizard walk).
function markConfigured() {
  if (selectedId.value) connStatus[selectedId.value] = 'connected'
}

// The server emits a GENERIC event (tool_name='mcp_connected') — it cannot tell
// which CLI connected (proposal §6: do not attempt per-tool attribution). Flip the
// SELECTED tool only.
let wsUnsub = null
function handleToolConnected(payload) {
  if (payload?.tool_name === 'mcp_connected' && selectedId.value) {
    connStatus[selectedId.value] = 'connected'
  }
}

onMounted(() => {
  wsUnsub = wsStore.on('setup:tool_connected', handleToolConnected)
})
onUnmounted(() => {
  if (wsUnsub) wsUnsub()
})
</script>

<style scoped lang="scss">
@use '../../styles/variables' as *;
@use '../../styles/design-tokens' as *;

.tools-directory {
  display: grid;
  grid-template-columns: 240px 1fr;
  min-height: 460px;
  background: $elevation-raised;
  border-radius: $border-radius-rounded;
  overflow: hidden;
  max-width: 1000px;
}

/* Fleet rail */
.dir-rail {
  background: $color-background-tertiary;
  box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.08);
  padding: 22px 16px;
  display: flex;
  flex-direction: column;
}

.dir-rail-top {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 20px;
}

.dir-rail-logo {
  height: 20px;
}

.dir-rail-kicker {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.62rem;
  letter-spacing: 0.16em;
  color: var(--text-muted);
}

.dir-rail-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.dir-rail-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 9px;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  width: 100%;
}

.dir-rail-row:hover {
  background: rgba(255, 255, 255, 0.04);
}

.dir-rail-row--active {
  background: rgba($color-brand-yellow, 0.08);
}

.dir-rail-dot {
  width: 8px;
  height: 8px;
  flex-shrink: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
}

.dir-rail-dot--connected {
  background: $color-status-success;
}

.dir-rail-dot--waiting {
  background: $color-indicator-disconnected;
  animation: dir-wait 1.6s ease infinite;
}

@keyframes dir-wait {
  0%, 100% { opacity: 0.35; transform: scale(0.85); }
  50% { opacity: 1; transform: scale(1.1); }
}

@media (prefers-reduced-motion: reduce) {
  .dir-rail-dot--waiting {
    animation: none;
  }
}

.dir-rail-label {
  flex: 1;
  font-size: 0.8rem;
  font-weight: 500;
  color: $lightest-blue;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dir-rail-row--active .dir-rail-label {
  color: $color-text-primary;
}

.dir-rail-status {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.52rem;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.dir-rail-row--add {
  margin-top: 6px;
  color: var(--text-muted);
}

.dir-rail-add-icon {
  width: 8px;
  height: 8px;
  display: grid;
  place-items: center;
  color: var(--text-muted);
}

/* Action window */
.dir-window {
  padding: 26px 30px;
  min-width: 0;
}

.dir-eyebrow {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.66rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: $color-brand-yellow;
  margin-bottom: 8px;
}

.dir-title {
  font-family: 'Outfit', $typography-font-primary;
  font-weight: 700;
  font-size: 1.35rem;
  letter-spacing: -0.02em;
  color: $color-text-primary;
  margin: 0 0 16px;
}

.dir-picker-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.dir-picker-card {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 13px 15px;
  border-radius: $border-radius-md;
  background: $elevation-elevated;
  cursor: pointer;
  transition: transform 0.15s;
}

.dir-picker-card:hover {
  transform: translateY(-1px);
  --smooth-border-color: #{rgba($color-brand-yellow, 0.4)};
}

.dir-picker-card:focus-visible {
  outline: 2px solid $color-brand-yellow;
  outline-offset: 2px;
}

.dir-picker-well {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: $border-radius-default;
  background: rgba(255, 255, 255, 0.05);
  display: grid;
  place-items: center;
  color: $lightest-blue;
}

.dir-picker-logo {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.dir-picker-name {
  font-family: 'Outfit', $typography-font-primary;
  font-size: 0.86rem;
  font-weight: 600;
  color: $color-text-primary;
}

.dir-window-foot {
  margin-top: 14px;
}

.dir-remove-link {
  font-size: 0.74rem;
  color: var(--text-muted);
  cursor: pointer;
}

.dir-remove-link:hover,
.dir-remove-link:focus-visible {
  color: $color-status-error;
}

.dir-empty {
  color: var(--text-secondary);
  font-size: 0.88rem;
  padding: 40px 0;
  text-align: center;
}

@media (max-width: 720px) {
  .tools-directory {
    grid-template-columns: 1fr;
  }

  .dir-rail {
    box-shadow: inset 0 -1px 0 rgba(255, 255, 255, 0.08);
  }

  .dir-picker-grid {
    grid-template-columns: 1fr;
  }
}
</style>
