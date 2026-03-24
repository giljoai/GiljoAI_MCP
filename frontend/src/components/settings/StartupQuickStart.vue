<template>
  <div class="startup-quickstart">
    <!-- Checklist bar (unchanged) -->
    <v-card variant="outlined" class="mb-4 setup-checklist">
      <v-card-text>
        <div class="d-flex flex-column align-center ga-1 mb-3 text-center">
          <div class="text-h6 font-weight-bold">{{ checklistTitle }}</div>
        </div>

        <div class="checklist-grid" :class="{ finished: setupFinished }">
          <div class="checklist-items-row">
            <div v-for="item in checklistItems" :key="item.id" class="checklist-item">
              <v-checkbox-btn
                v-model="checklist[item.id]"
                density="compact"
                hide-details
                :color="setupFinished ? 'success' : 'secondary'"
                class="checklist-item-checkbox"
                false-icon="mdi-radiobox-blank"
                true-icon="mdi-radiobox-marked"
                :aria-label="item.label"
                :disabled="setupFinished || !isStepReachable(item.id)"
                @update:model-value="() => handleChecklistToggle(item)"
              />
              <div class="checklist-item-label">
                {{ item.label }}
              </div>
            </div>
          </div>

          <div
            class="checklist-bar"
            aria-label="Setup progress"
            :style="{
              '--progress': setupFinished ? 1 : checklistProgress,
              '--progress-color': setupFinished ? 'rgb(var(--v-theme-success))' : (checklistCompleted === checklistItems.length ? 'rgb(var(--v-theme-success))' : 'rgb(var(--v-theme-secondary))'),
            }"
          >
            <div class="checklist-progress-track" />
            <div class="checklist-progress-fill" />
            <div class="checklist-dots">
              <div
                v-for="item in checklistItems"
                :key="`${item.id}-dot`"
                class="checklist-dot"
                :class="{ done: checklist[item.id], finished: setupFinished }"
                :title="item.label"
              />
            </div>
          </div>
        </div>

        <div v-if="allChecked && !setupFinished" class="d-flex justify-center mt-4">
          <v-btn color="success" variant="flat" @click="finishSetup">
            Finished
          </v-btn>
        </div>
      </v-card-text>
    </v-card>

    <!-- Active step card: shows the last-clicked checklist item -->
    <transition name="step-card" mode="out-in">
      <v-card
        v-if="activeStep"
        :key="activeStep.id"
        variant="outlined"
        class="mb-4"
      >
        <v-card-title class="d-flex align-center justify-space-between">
          <div class="d-flex align-center ga-2">
            <GiljoFaceIcon
              v-if="activeStep.useGiljoIcon"
              :active="true"
              :size="29"
              alt="GiljoAI"
            />
            <v-icon v-else :color="accentColor">{{ activeStep.icon }}</v-icon>
            <span>{{ activeStep.title }}</span>
          </div>
          <v-btn
            v-if="activeStep.primaryAction"
            size="small"
            color="secondary"
            variant="flat"
            @click="runAction(activeStep.primaryAction)"
          >
            {{ activeStep.primaryAction.label }}
          </v-btn>
        </v-card-title>
        <v-card-text>
          <div class="text-body-2 mb-3">{{ activeStep.body }}</div>

          <v-alert
            v-if="activeStep.note"
            type="warning"
            variant="tonal"
            density="compact"
            class="mb-3"
          >
            {{ activeStep.note }}
          </v-alert>

          <ToolConfigSnippet
            v-if="activeStep.showMcpSnippet"
            :config="mcpHttpSnippet"
            language="json"
            class="mb-3"
          />

          <div v-if="activeStep.actions && activeStep.actions.length" class="d-flex flex-wrap ga-2">
            <v-btn
              v-for="action in activeStep.actions"
              :key="action.id"
              :color="action.tone || 'primary'"
              :variant="action.variant || 'tonal'"
              size="small"
              :style="action.textColor ? { color: `rgb(var(--v-theme-${action.textColor}))` } : undefined"
              @click="runAction(action)"
            >
              <v-icon v-if="action.icon" start>{{ action.icon }}</v-icon>
              {{ action.label }}
            </v-btn>
          </div>
        </v-card-text>
      </v-card>
    </transition>

    <!-- Next Steps: visible once all 6 checklist items are checked -->
    <template v-if="allSetupComplete">
      <div class="setup-phase-divider my-5" role="separator" aria-label="Next steps">
        <span class="setup-phase-divider-text">Next Steps</span>
      </div>

      <v-row>
        <v-col v-for="step in productSteps" :key="step.id" cols="12" md="4">
          <v-card variant="outlined" class="fill-height">
            <v-card-title class="d-flex align-center ga-2">
              <v-icon :color="accentColor">{{ step.icon }}</v-icon>
              <span>{{ step.title }}</span>
            </v-card-title>
            <v-card-subtitle>{{ step.subtitle }}</v-card-subtitle>
            <v-card-text>
              <div class="text-body-2">{{ step.body }}</div>
            </v-card-text>
            <v-card-actions>
              <v-spacer />
              <v-btn
                v-if="step.primaryAction"
                color="secondary"
                variant="flat"
                size="small"
                @click="runAction(step.primaryAction)"
              >
                {{ step.primaryAction.label }}
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import ToolConfigSnippet from '@/components/ToolConfigSnippet.vue'
import GiljoFaceIcon from '@/components/icons/GiljoFaceIcon.vue'

const props = defineProps({
  gitEnabled: { type: Boolean, default: false },
  serenaEnabled: { type: Boolean, default: false },
})

const router = useRouter()

const CHECKLIST_STORAGE_KEY = 'giljo_startup_checklist_v1'
const FINISHED_STORAGE_KEY = 'giljo_startup_finished_v1'
const checklistItems = [
  { id: 'tools', label: 'Installed AI coding agents', stepId: 'tools' },
  { id: 'connect', label: 'Attach MCP server', stepId: 'connect' },
  { id: 'slash', label: 'Install slash commands', stepId: 'slash' },
  { id: 'templates', label: 'Reviewed agents', stepId: 'templates' },
  { id: 'context', label: 'Tuned context', stepId: 'context' },
  { id: 'integrations', label: 'Configure integrations', stepId: 'integrations' },
]
const checklist = ref({
  tools: false,
  connect: false,
  slash: false,
  templates: false,
  context: false,
  integrations: false,
})

const setupSteps = [
  {
    id: 'tools',
    icon: 'mdi-console-line',
    title: 'Pick your AI coding agent(s)',
    subtitle: 'Claude Code or multi-terminal mode',
    body:
      'Giljo MCP works with Claude Code CLI (tightly integrated subagents) and also with "multi-terminal mode" (Codex + others) where multiple tools share one MCP server over HTTP.',
    actions: [
      {
        id: 'open-integrations',
        label: 'Open Integrations',
        icon: 'mdi-puzzle',
        tone: 'primary',
        variant: 'tonal',
        type: 'userSettingsTab',
        tab: 'integrations',
      },
    ],
  },
  {
    id: 'connect',
    icon: 'mdi-lan-connect',
    title: 'Connect to the MCP server',
    subtitle: 'HTTP JSON-RPC at /mcp',
    body:
      'Attach your tool(s) to this server\'s MCP endpoint. The Integrations tab contains tool-specific helpers and copy/paste snippets.',
    showMcpSnippet: true,
    primaryAction: {
      id: 'open-integrations-primary',
      label: 'Configure Integrations',
      type: 'userSettingsTab',
      tab: 'integrations',
    },
    actions: [],
  },
  {
    id: 'slash',
    icon: 'mdi-slash-forward',
    title: 'Install slash commands',
    subtitle: 'Required for best CLI flows',
    body:
      'Install the Giljo slash commands so your AI coding agent can quickly call MCP tools and fetch instructions. This is the baseline for a great UX.',
    primaryAction: {
      id: 'open-slash-primary',
      label: 'Configure Integrations',
      type: 'userSettingsTab',
      tab: 'integrations',
    },
    actions: [],
  },
  {
    id: 'templates',
    icon: 'mdi-robot-outline',
    useGiljoIcon: true,
    title: 'Agents & templates',
    subtitle: 'Template manager + exports',
    body:
      'Use the agent template manager to create/edit templates. If you use Claude Code, you can export templates. In other tools, agents can fetch their profile dynamically via MCP.',
    primaryAction: {
      id: 'open-agents-primary',
      label: 'Open Templates',
      type: 'userSettingsTab',
      tab: 'agents',
    },
    actions: [],
  },
  {
    id: 'context',
    icon: 'mdi-layers-triple',
    title: 'Tune context',
    subtitle: 'Define what agents get',
    body:
      'Define what information agents receive. Context settings let you control importance and depth so prepared tools and prompts stay aligned with your product.',
    primaryAction: {
      id: 'open-context-primary',
      label: 'Open Context',
      type: 'userSettingsTab',
      tab: 'context',
    },
    actions: [],
  },
  {
    id: 'integrations',
    icon: 'mdi-puzzle',
    title: 'Configure integrations',
    subtitle: 'Connect tools + enable power-ups',
    body:
      'Configure integrations to connect your AI coding agents via MCP, and optionally enable power-ups like Git and Serena.',
    primaryAction: {
      id: 'open-integrations-primary',
      label: 'Configure Integrations',
      type: 'userSettingsTab',
      tab: 'integrations',
    },
    actions: [],
  },
]

const productSteps = [
  {
    id: 'product',
    icon: 'mdi-package-variant',
    title: 'Add a product',
    subtitle: 'Your top-level container',
    body:
      'Create a product to hold your vision, architecture, context, and long-lived memory. This is what keeps agents focused and consistent.',
    primaryAction: {
      id: 'open-products-primary',
      label: 'Open Products',
      type: 'route',
      route: { name: 'Products' },
    },
  },
  {
    id: 'project',
    icon: 'mdi-folder-multiple',
    title: 'Add a project',
    subtitle: 'Incremental work inside a product',
    body:
      'Create a project to describe the work you want to implement. Projects are incremental and historical "units of work" inside a product.',
    primaryAction: {
      id: 'open-projects-primary',
      label: 'Open Projects',
      type: 'route',
      route: { name: 'Projects' },
    },
  },
  {
    id: 'tasks',
    icon: 'mdi-clipboard-check',
    title: 'Add tasks',
    subtitle: 'User-managed TODO tracking',
    body:
      'Add tasks to capture technical debt and ideas as you work, and keep your execution aligned without breaking focus.',
    primaryAction: {
      id: 'open-tasks-primary',
      label: 'Open Tasks',
      type: 'route',
      route: { name: 'Tasks' },
    },
  },
]

const accentColor = computed(() => 'primary')

const activeStepId = ref(null)
const setupFinished = ref(false)

const activeStep = computed(() =>
  activeStepId.value ? setupSteps.find((s) => s.id === activeStepId.value) : null,
)

const allChecked = computed(() =>
  checklistItems.every((item) => checklist.value[item.id]),
)

const allSetupComplete = computed(() => allChecked.value && setupFinished.value)

const checklistTitle = computed(() => {
  if (setupFinished.value) return 'Congratulations! You are set up!'
  const anyChecked = checklistItems.some((item) => checklist.value[item.id])
  if (!anyChecked) return 'My setup check list, Lets get going!'
  return 'My setup check list!'
})

const checklistCompleted = computed(() => checklistItems.filter((i) => checklist.value[i.id]).length)
const checklistProgress = computed(() => {
  const total = checklistItems.length
  if (total <= 1) return checklistCompleted.value ? 1 : 0
  const filledSegments = Math.max(0, checklistCompleted.value - 1)
  return Math.min(1, filledSegments / (total - 1))
})

const mcpHttpSnippet = computed(() => {
  const origin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:7274'
  return JSON.stringify(
    {
      name: 'giljo-mcp',
      transport: 'http',
      url: `${origin}/mcp`,
      headers: {
        'X-API-Key': 'YOUR_API_KEY',
      },
      notes: 'Use User Settings → Integrations for tool-specific setup.',
    },
    null,
    2,
  )
})

function loadChecklist() {
  try {
    const raw = localStorage.getItem(CHECKLIST_STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      checklist.value = { ...checklist.value, ...parsed }
    }
    const finishedRaw = localStorage.getItem(FINISHED_STORAGE_KEY)
    if (finishedRaw) {
      setupFinished.value = JSON.parse(finishedRaw)
    }
  } catch {
    // ignore
  }
}

function saveChecklist() {
  try {
    localStorage.setItem(CHECKLIST_STORAGE_KEY, JSON.stringify(checklist.value))
  } catch {
    // ignore
  }
}

function isStepReachable(stepId) {
  const idx = checklistItems.findIndex((i) => i.id === stepId)
  if (idx === 0) return true
  // Can only reach step N if step N-1 is checked
  return checklist.value[checklistItems[idx - 1].id]
}

function handleChecklistToggle(item) {
  // If unchecking, also uncheck all subsequent steps
  const idx = checklistItems.findIndex((i) => i.id === item.id)
  if (!checklist.value[item.id]) {
    for (let i = idx + 1; i < checklistItems.length; i++) {
      checklist.value[checklistItems[i].id] = false
    }
    // Reset finished state if any item is unchecked
    setupFinished.value = false
    saveFinished()
  }

  // Show the card for the last checked item
  const lastChecked = [...checklistItems].reverse().find((i) => checklist.value[i.id])
  activeStepId.value = lastChecked ? lastChecked.id : null

  saveChecklist()
}

function resetChecklist() {
  for (const item of checklistItems) {
    checklist.value[item.id] = false
  }
  setupFinished.value = false
  activeStepId.value = null
  saveChecklist()
  saveFinished()
}

function finishSetup() {
  setupFinished.value = true
  activeStepId.value = null
  saveFinished()
}

function saveFinished() {
  try {
    localStorage.setItem(FINISHED_STORAGE_KEY, JSON.stringify(setupFinished.value))
  } catch {
    // ignore
  }
}

function goUserSettingsTab(tab) {
  router.push({ name: 'UserSettings', query: { tab } })
}

function runAction(action) {
  if (!action) return
  if (action.type === 'userSettingsTab') {
    goUserSettingsTab(action.tab)
    return
  }
  if (action.type === 'route') {
    router.push(action.route)
    return
  }
}

onMounted(() => {
  loadChecklist()
})

defineExpose({ setupFinished, resetChecklist })
</script>

<style scoped>
.setup-checklist {
  border-radius: 18px;
}

.checklist-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.checklist-items-row {
  display: flex;
  flex-wrap: nowrap;
  gap: 36px;
  align-items: center;
  justify-content: center;
  overflow-x: auto;
  padding-bottom: 2px;
}

.checklist-item {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 5px;
  min-height: 26px;
  white-space: nowrap;
}

.checklist-item-label {
  text-align: left;
  font-size: 0.82rem;
  line-height: 1.1;
  color: rgba(var(--v-theme-on-surface), 0.92);
}

.checklist-progress-track,
.checklist-progress-fill {
  position: absolute;
  left: 8px;
  right: 8px;
  top: 50%;
  height: 4px;
  transform: translateY(-50%);
  border-radius: 9999px;
}

.checklist-bar {
  position: relative;
  height: 18px;
}

.checklist-progress-track {
  background: rgba(var(--v-theme-on-surface), 0.18);
}

.checklist-progress-fill {
  background: var(--progress-color, rgb(var(--v-theme-secondary)));
  right: auto;
  width: calc((100% - 16px) * var(--progress));
}

.checklist-dot {
  width: 12px;
  height: 12px;
  border-radius: 9999px;
  background: rgba(var(--v-theme-on-surface), 0.35);
  border: 2px solid rgba(var(--v-theme-on-surface), 0.25);
}

.checklist-dot.done {
  background: rgb(var(--v-theme-secondary));
  border-color: rgb(var(--v-theme-secondary));
}

.checklist-dot.finished {
  background: rgb(var(--v-theme-success));
  border-color: rgb(var(--v-theme-success));
}

.checklist-grid.finished .checklist-progress-track {
  background: rgb(var(--v-theme-success));
}

.checklist-grid.finished .checklist-item-label {
  color: rgb(var(--v-theme-success));
}

.checklist-dots {
  position: absolute;
  left: 8px;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  justify-content: space-between;
  pointer-events: none;
}

.startup-quickstart :deep(.checklist-item-checkbox .v-selection-control) {
  min-height: 0;
}

.startup-quickstart :deep(.checklist-item-checkbox .v-selection-control__wrapper) {
  width: 20px;
  height: 20px;
}

/* Transition for step cards appearing/disappearing */
.step-card-enter-active {
  transition: all 0.3s ease-out;
}

.step-card-leave-active {
  transition: all 0.2s ease-in;
}

.step-card-enter-from {
  opacity: 0;
  transform: translateY(-12px);
}

.step-card-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}

.setup-phase-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.setup-phase-divider::before,
.setup-phase-divider::after {
  content: '';
  flex: 1 1 auto;
  border-top: 2px solid rgba(var(--v-theme-on-surface), 0.85);
}

.setup-phase-divider-text {
  color: rgba(var(--v-theme-on-surface), 0.9);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 600;
  font-size: 0.72rem;
  white-space: nowrap;
}

/* Improve button readability in dark mode */
.v-theme--dark .startup-quickstart :deep(.v-btn.v-btn--variant-tonal) {
  filter: brightness(1.08);
}
</style>
