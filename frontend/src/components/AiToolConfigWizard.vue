<template>
  <v-dialog v-model="showWizard" max-width="960" persistent scrollable>
    <!-- Activator pill — suppressed when noActivator=true so the parent
         can trigger the dialog programmatically via the exposed open() API. -->
    <template v-if="!noActivator" #activator="{ props }">
      <button v-bind="props" class="configurator-pill smooth-border">
        <v-icon size="16" class="mr-1">mdi-wrench-outline</v-icon>
        Configurator
      </button>
    </template>

    <v-card v-draggable class="smooth-border split-rail-card" data-testid="configurator-modal">
      <div class="dlg-header">
        <span class="dlg-title">Connect your AI coding tool</span>
        <v-btn icon variant="text" class="dlg-close" aria-label="Close" @click="showWizard = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </div>

      <v-card-text class="wizard-body">
        <p class="wizard-subtitle">
          <template v-if="isCe">
            Choose your AI coding tool and copy the API key configuration for your terminal.
          </template>
          <template v-else>
            Choose how your tool connects, and the setup on the right updates instantly.
          </template>
        </p>

        <div class="split-rail">
          <!-- LEFT RAIL: connection route + contextual tool picker -->
          <aside class="rail" aria-label="Connection route">
            <div class="rail-label">How do you connect?</div>

            <button
              v-for="r in visibleRoutes"
              :key="r.id"
              type="button"
              class="rail-btn"
              :class="['route-' + r.id, { 'rail-btn--selected': route === r.id }]"
              :data-testid="'route-rail-' + r.id"
              :aria-pressed="route === r.id"
              @click="selectRoute(r.id)"
            >
              <span class="rail-icon"><v-icon size="17">{{ r.icon }}</v-icon></span>
              <span class="rail-copy">
                <span class="rail-title">{{ r.label }}</span>
                <span class="rail-desc">{{ r.desc }}</span>
              </span>
            </button>

            <div v-if="toolsForRoute.length" class="rail-tools" data-testid="rail-tools">
              <div class="rail-tools-label">
                {{ route === 'cli' ? 'Select your CLI tool' : 'Select your tool' }}
              </div>
              <button
                v-for="t in toolsForRoute"
                :key="t.id"
                type="button"
                class="tool-pick"
                :class="['route-' + route, { 'tool-pick--selected': selectedTool === t.id }]"
                :data-testid="'tool-pick-' + t.id"
                :aria-pressed="selectedTool === t.id"
                @click="selectTool(t.id)"
              >
                <span class="tool-pick-logo">
                  <v-img
                    :src="toolLogos[t.id]"
                    width="16"
                    height="16"
                    contain
                    :class="{ 'mcp-logo-white': t.id === 'generic_mcp' }"
                  />
                </span>
                <span class="tool-pick-name">{{ t.name }}</span>
                <span class="tool-pick-vendor">{{ t.vendor }}</span>
              </button>
            </div>
          </aside>

          <!-- RIGHT PANE: one live artifact for the chosen route + tool -->
          <AiToolGeneratePanel
            class="pane"
            :route="route"
            :selected-tool="selectedTool"
            :selected-row="selectedRow"
            :is-ce="isCe"
            :backend-config="backendConfig"
          />
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import configService from '@/services/configService'
import setupService from '@/services/setupService'
import { isCeModeValue } from '@/composables/useGiljoMode'
import { getAuthCapabilities } from '@/composables/useMcpConfig'
import AiToolGeneratePanel from './AiToolGeneratePanel.vue'

defineProps({
  /**
   * When true, the built-in activator (Configurator pill) is suppressed.
   * The dialog must be opened programmatically via the exposed open() /
   * openForKeyGeneration() methods. Used by ApiKeyManager to avoid a duplicate
   * trigger alongside its own header button.
   */
  noActivator: { type: Boolean, default: false },
})

const showWizard = ref(false)

// Backend config (INF-5012) — used to detect self-signed HTTPS so CE Node tools
// get the cert-trust step. Never set for plain HTTP or proxied (SaaS) HTTPS.
const backendConfig = ref(null)
const isCe = ref(false)

// The three connection routes (Split Rail — FE-6259a). A 3-way fork, not a
// step sequence: exactly one route + tool combination is on screen at a time.
const ROUTE_DEFS = [
  { id: 'web', label: 'Web & app', desc: 'Paste a link into a connector', icon: 'mdi-earth' },
  { id: 'cli', label: 'Terminal / CLI', desc: 'One command, Browser sign-in', icon: 'mdi-console-line' },
  { id: 'key', label: 'API key', desc: 'Generic MCP · headless · CI', icon: 'mdi-key-variant' },
]

// CE is API-key-only (FE-6242 lineage): hide Web & app and Terminal/CLI,
// lead with the API-key route. Never default to the wider set on uncertainty.
const visibleRoutes = computed(() => (isCe.value ? ROUTE_DEFS.filter((r) => r.id === 'key') : ROUTE_DEFS))

const route = ref('web')
// If the mode resolves to CE after mount, snap to the only route CE offers.
watch(isCe, (v) => {
  if (v) route.value = 'key'
})

// Vendor-grouped tool metadata. The id is the canonical legacy tool id
// consumed by useMcpConfig's generators + AUTH_CAPABILITIES (FE-6157).
const TOOL_ROWS = [
  { id: 'claude', vendor: 'Anthropic', name: 'Claude' },
  { id: 'codex', vendor: 'OpenAI', name: 'ChatGPT + Codex CLI' },
  { id: 'gemini', vendor: 'Google', name: 'Gemini CLI' },
  { id: 'antigravity', vendor: 'Google', name: 'Antigravity' },
  { id: 'generic_mcp', vendor: 'Other', name: 'Generic MCP client' },
]

// Reuse the existing real logo assets — do NOT redraw.
const toolLogos = {
  claude: '/claude-color.svg',
  codex: '/icons/codex_mark_white.svg',
  gemini: '/gemini-icon.svg',
  antigravity: '/antigravity-color.svg',
  generic_mcp: '/logo-mcp.svg',
}

// Per-route tool memory so switching routes and back keeps the last pick.
const cliTool = ref('claude')
const keyTool = ref('claude')

const selectedTool = computed(() => (route.value === 'cli' ? cliTool.value : keyTool.value))
const selectedRow = computed(() => TOOL_ROWS.find((r) => r.id === selectedTool.value) || TOOL_ROWS[0])

// Contextual tool list per route (BE-6157 AUTH_CAPABILITIES is the source of
// truth for which tools can run their own browser sign-in):
//   - Web & app: no tool picker — one URL works for every connector.
//   - Terminal / CLI: only browser-sign-in-capable tools (Claude/Codex/Gemini).
//   - API key: every tool, including the key-only ones (Generic MCP, Antigravity)
//     that never appear anywhere else.
const toolsForRoute = computed(() => {
  if (route.value === 'cli') return TOOL_ROWS.filter((r) => getAuthCapabilities(r.id)?.supports_oauth)
  if (route.value === 'key') return TOOL_ROWS
  return []
})

function selectRoute(id) {
  route.value = id
}
function selectTool(id) {
  if (route.value === 'cli') cliTool.value = id
  else keyTool.value = id
}

async function loadBackendConfig() {
  try {
    const cfg = await configService.fetchConfig()
    if (cfg?.api) backendConfig.value = cfg.api
  } catch (e) {
    // Non-fatal — falls back to no self-signed flag.
    console.warn('[Wizard] Failed to fetch backend config:', e)
  }
}

async function loadModeFlag() {
  try {
    const status = await setupService.checkEnhancedStatus()
    isCe.value = isCeModeValue(status?.mode)
  } catch (e) {
    console.warn('[Wizard] Failed to resolve mode:', e)
  }
}

onMounted(() => {
  loadBackendConfig()
  loadModeFlag()
})

// Expose methods to programmatically open the wizard (ApiKeyManager's Configurator button).
defineExpose({
  open: () => {
    showWizard.value = true
  },
  // ApiKeyManager's "Configurator" button opens the wizard landed directly on
  // the API-key route.
  openForKeyGeneration: () => {
    route.value = 'key'
    showWizard.value = true
  },
})
</script>

<style lang="scss" scoped>
@use '../styles/design-tokens' as *;

/* Match the dialog title to the app's loaded system font. */
.dlg-title {
  font-family: 'Roboto', sans-serif;
}

.split-rail-card {
  overflow: hidden;
}

.wizard-body {
  padding: 12px 0 0;
}

.wizard-subtitle {
  color: var(--text-secondary);
  font-size: 0.875rem;
  margin: 0 20px 16px;
}

/* ── Split Rail: 2-column layout ── */
.split-rail {
  display: grid;
  grid-template-columns: 260px 1fr;
  min-height: 420px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

@media (max-width: 720px) {
  .split-rail {
    grid-template-columns: 1fr;
  }
}

/* ── LEFT RAIL ── */
.rail {
  background: $color-background-tertiary;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  padding: 16px 14px;
}

@media (max-width: 720px) {
  .rail {
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }
}

.rail-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.6rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin: 6px 8px 10px;
}

.rail-btn {
  width: 100%;
  text-align: left;
  border: none;
  cursor: pointer;
  background: transparent;
  color: $color-text-primary;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: $border-radius-md;
  position: relative;
  margin-bottom: 4px;
  transition: background $transition-fast;
}
.rail-btn:hover {
  background: rgba(255, 255, 255, 0.03);
}
.rail-btn:focus-visible {
  outline: 2px solid rgba($color-brand-yellow, 0.5);
  outline-offset: 2px;
}
.rail-btn--selected {
  background: rgba(255, 255, 255, 0.05);
}
.rail-btn--selected::before {
  content: '';
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 3px;
  background: var(--rail-accent);
}
.rail-btn.route-web {
  --rail-accent: #{$color-brand-yellow};
}
.rail-btn.route-cli {
  --rail-accent: #{$color-agent-implementor};
}
.rail-btn.route-key {
  --rail-accent: #{$color-agent-reviewer};
}

.rail-icon {
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  background: color-mix(in srgb, var(--rail-accent, $color-brand-yellow) 15%, transparent);
  color: var(--rail-accent, $color-brand-yellow);
}
.rail-title {
  display: block;
  font-family: 'Outfit', sans-serif;
  font-weight: 600;
  font-size: 0.9rem;
}
.rail-desc {
  display: block;
  color: var(--text-muted);
  font-size: 0.74rem;
  margin-top: 1px;
}

/* Contextual tool list under the selected route */
.rail-tools {
  margin: 6px 6px 0;
  padding: 10px 4px 4px;
  border-top: 1px dashed rgba(255, 255, 255, 0.08);
}
.rail-tools-label {
  font-size: 0.68rem;
  color: var(--text-muted);
  margin: 0 8px 8px;
}
.tool-pick {
  width: 100%;
  text-align: left;
  border: none;
  cursor: pointer;
  background: transparent;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: $border-radius-default;
  transition: background $transition-fast, color $transition-fast, box-shadow $transition-fast;
}
.tool-pick:hover {
  background: rgba(255, 255, 255, 0.03);
  color: $color-text-primary;
}
.tool-pick:focus-visible {
  outline: 2px solid rgba($color-brand-yellow, 0.5);
  outline-offset: 2px;
}
.tool-pick.route-cli.tool-pick--selected {
  background: color-mix(in srgb, $color-agent-implementor 12%, transparent);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, $color-agent-implementor 45%, transparent);
  color: $color-text-primary;
}
.tool-pick.route-key.tool-pick--selected {
  background: color-mix(in srgb, $color-agent-reviewer 12%, transparent);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, $color-agent-reviewer 45%, transparent);
  color: $color-text-primary;
}
.tool-pick-logo {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.06);
  display: grid;
  place-items: center;
  flex: 0 0 26px;
}
.tool-pick-name {
  font-size: 0.82rem;
}
.tool-pick-vendor {
  color: var(--text-muted);
  font-size: 0.68rem;
}

.mcp-logo-white {
  filter: brightness(0) invert(1);
}

@media (prefers-reduced-motion: reduce) {
  .rail-btn,
  .tool-pick {
    transition: none;
  }
}

/* ── Activator pill (unchanged) ── */
.configurator-pill {
  --smooth-border-color: #{$color-brand-yellow};
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: $border-radius-rounded;
  padding: 8px 20px;
  height: 40px;
  font-size: 0.82rem;
  font-weight: 500;
  background: transparent;
  color: $color-brand-yellow;
  border: none;
  cursor: pointer;
  transition: background $transition-fast;
  white-space: nowrap;
}
.configurator-pill:hover {
  background: rgba($color-brand-yellow, 0.12);
}
</style>
