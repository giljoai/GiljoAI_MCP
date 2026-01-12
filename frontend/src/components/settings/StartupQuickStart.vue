<template>
  <div class="startup-quickstart">
    <v-alert type="info" variant="tonal" density="comfortable" class="mb-4">
      This is a guided quick start to get you connected and productive. It’s intentionally lightweight for now
      (we’ll expand it into full docs, tutorials, and admin onboarding later).
    </v-alert>

    <v-row>
      <v-col cols="12" lg="5">
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="d-flex align-center justify-space-between">
            <span>Setup Quick Start</span>
            <v-chip size="small" variant="tonal" :color="accentColor" class="steps-chip"
              >{{ steps.length }} steps</v-chip
            >
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item
                v-for="(step, index) in steps"
                :key="step.id"
                :active="selectedStepId === step.id"
                @click="selectedStepId = step.id"
                class="rounded"
                data-testid="quickstart-step"
              >
                <template #prepend>
                  <div class="d-flex align-center justify-center" style="width: 32px; height: 32px">
                    <GiljoFaceIcon v-if="step.useGiljoIcon" :active="true" :size="25" alt="Agent" />
                    <v-icon v-else size="20" :color="accentColor">{{ step.icon }}</v-icon>
                  </div>
                </template>

                <v-list-item-title class="text-body-2">
                  {{ index + 1 }}. {{ step.title }}
                </v-list-item-title>
                <v-list-item-subtitle class="text-caption">
                  {{ step.subtitle }}
                </v-list-item-subtitle>

                <template #append>
                  <v-btn
                    v-if="step.primaryAction"
                    size="small"
                    density="compact"
                    variant="flat"
                    color="secondary"
                    rounded="pill"
                    class="quickstart-go-btn"
                    @click.stop="runAction(step.primaryAction)"
                    data-testid="quickstart-primary-action"
                  >
                    Go!
                    <v-tooltip activator="parent" location="top">{{ step.primaryAction.label }}</v-tooltip>
                  </v-btn>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>

        <v-card variant="outlined">
          <v-card-title class="d-flex align-center justify-space-between">
            <span>Shortcuts</span>
            <v-btn size="small" variant="text" @click="showShortcuts = true">Open</v-btn>
          </v-card-title>
          <v-card-text class="text-body-2">
            A few useful “quick start” shortcuts (placeholder for a fuller shortcuts/help center).
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" lg="7">
        <v-card variant="outlined" class="mb-4">
        <v-card-title class="d-flex align-center justify-space-between">
          <div class="d-flex align-center ga-2">
            <GiljoFaceIcon
              v-if="selectedStep.useGiljoIcon"
              :active="true"
              :size="29"
              alt="GiljoAI"
            />
            <v-icon v-else :color="accentColor">{{ selectedStep.icon }}</v-icon>
            <span>{{ selectedStep.title }}</span>
          </div>
          <div class="d-flex ga-2">
            <v-btn size="small" variant="text" @click="openDetails(selectedStep)">Details</v-btn>
            <v-btn
              v-if="selectedStep.primaryAction"
              size="small"
              color="secondary"
              variant="flat"
              @click="runAction(selectedStep.primaryAction)"
            >
              {{ selectedStep.primaryAction.label }}
            </v-btn>
          </div>
          </v-card-title>
          <v-card-text>
            <div class="text-body-2 mb-3">{{ selectedStep.body }}</div>

            <v-alert
              v-if="selectedStep.note"
              type="warning"
              variant="tonal"
              density="compact"
              class="mb-3"
            >
              {{ selectedStep.note }}
            </v-alert>

            <ToolConfigSnippet
              v-if="selectedStep.showMcpSnippet"
              :config="mcpHttpSnippet"
              language="json"
              class="mb-3"
            />

            <div class="d-flex flex-wrap ga-2">
              <v-btn
                v-for="action in selectedStep.actions"
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

        <v-card variant="outlined">
          <v-card-title>Help & Manuals (mock)</v-card-title>
          <v-card-text class="text-body-2">
            This area will become the searchable help center: quick starts, troubleshooting, best practices,
            and “what’s new”. For now, it’s a placeholder so we can design the UX flows.
          </v-card-text>
          <v-card-actions>
            <v-btn variant="tonal" color="primary" @click="showHelpMock = true">Open mock help</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- Step details dialog -->
    <v-dialog v-model="showDetails" max-width="760">
      <v-card>
        <v-card-title class="d-flex align-center justify-space-between">
          <div class="d-flex align-center ga-2">
            <GiljoFaceIcon
              v-if="detailsStep?.useGiljoIcon"
              :active="true"
              :size="29"
              alt="GiljoAI"
            />
            <v-icon v-else :color="accentColor">{{ detailsStep?.icon }}</v-icon>
            <span>{{ detailsStep?.title }}</span>
          </div>
          <v-btn icon="mdi-close" variant="text" @click="showDetails = false" />
        </v-card-title>
        <v-card-text>
          <div class="text-body-2 mb-4">{{ detailsStep?.details }}</div>
          <ToolConfigSnippet v-if="detailsStep?.showMcpSnippet" :config="mcpHttpSnippet" language="json" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDetails = false">Close</v-btn>
          <v-btn
            v-if="detailsStep?.primaryAction"
            color="primary"
            variant="flat"
            @click="runAction(detailsStep.primaryAction)"
          >
            {{ detailsStep.primaryAction.label }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Shortcuts dialog (mock) -->
    <v-dialog v-model="showShortcuts" max-width="760">
      <v-card>
        <v-card-title class="d-flex align-center justify-space-between">
          <span>Quick Start Shortcuts</span>
          <v-btn icon="mdi-close" variant="text" @click="showShortcuts = false" />
        </v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" density="compact" class="mb-3">
            Placeholder: this will become a searchable shortcuts + docs launcher.
          </v-alert>
          <v-list density="compact">
            <v-list-item>
              <v-list-item-title>Open Integrations</v-list-item-title>
              <v-list-item-subtitle>User Settings → Integrations</v-list-item-subtitle>
              <template #append>
                <v-btn size="small" variant="text" @click="goUserSettingsTab('integrations')">Open</v-btn>
              </template>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Open Agent Templates</v-list-item-title>
              <v-list-item-subtitle>User Settings → Agents</v-list-item-subtitle>
              <template #append>
                <v-btn size="small" variant="text" @click="goUserSettingsTab('agents')">Open</v-btn>
              </template>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Create a Product</v-list-item-title>
              <v-list-item-subtitle>Products page</v-list-item-subtitle>
              <template #append>
                <v-btn size="small" variant="text" @click="router.push({ name: 'Products' })">Open</v-btn>
              </template>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Create a Project</v-list-item-title>
              <v-list-item-subtitle>Projects page</v-list-item-subtitle>
              <template #append>
                <v-btn size="small" variant="text" @click="router.push({ name: 'Projects' })">Open</v-btn>
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showShortcuts = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Help mock dialog -->
    <v-dialog v-model="showHelpMock" max-width="760">
      <v-card>
        <v-card-title class="d-flex align-center justify-space-between">
          <span>Help (mock)</span>
          <v-btn icon="mdi-close" variant="text" @click="showHelpMock = false" />
        </v-card-title>
        <v-card-text>
          <v-list density="compact">
            <v-list-item>
              <v-list-item-title>Getting started</v-list-item-title>
              <v-list-item-subtitle>Install, connect, create product/project, run tasks</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Claude Code mode</v-list-item-title>
              <v-list-item-subtitle>Subagents, templates export, slash commands</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Codex + others mode</v-list-item-title>
              <v-list-item-subtitle>Multi-terminal, MCP over HTTP, shared tenant isolation</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Troubleshooting</v-list-item-title>
              <v-list-item-subtitle>Server not reachable, API key issues, CORS, logs</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showHelpMock = false">Close</v-btn>
          <v-btn variant="tonal" color="secondary" @click="goUserSettingsTab('integrations')"
            >Open Integrations</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import ToolConfigSnippet from '@/components/ToolConfigSnippet.vue'
import GiljoFaceIcon from '@/components/icons/GiljoFaceIcon.vue'

const props = defineProps({
  gitEnabled: { type: Boolean, default: false },
  serenaEnabled: { type: Boolean, default: false },
})

const router = useRouter()
const theme = useTheme()

const showDetails = ref(false)
const detailsStep = ref(null)
const showShortcuts = ref(false)
const showHelpMock = ref(false)

const steps = computed(() => [
  {
    id: 'tools',
    icon: 'mdi-console-line',
    title: 'Pick your coding tool(s)',
    subtitle: 'Claude Code or multi-terminal mode',
    body:
      'Giljo MCP works with Claude Code CLI (tightly integrated subagents) and also with “multi-terminal mode” (Codex + others) where multiple tools share one MCP server over HTTP.',
    details:
      'Claude Code CLI is the most integrated experience (subagents + Task Tool). Multi-terminal mode means you can run any combination of agentic coding tools in separate terminals, all talking to the same MCP server via HTTP JSON-RPC.',
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
      'Attach your tool(s) to this server’s MCP endpoint. The Integrations tab contains tool-specific helpers and copy/paste snippets.',
    details:
      'Giljo MCP exposes an HTTP JSON-RPC MCP endpoint at /mcp. Most tools require an API key header (X-API-Key). Use User Settings → Integrations for guided setup for Claude Code, Codex, and other clients.',
    showMcpSnippet: true,
    primaryAction: {
      id: 'open-integrations-primary',
      label: 'Configure Integrations',
      type: 'userSettingsTab',
      tab: 'integrations',
    },
    actions: [
    ],
  },
  {
    id: 'slash',
    icon: 'mdi-slash-forward',
    title: 'Install slash commands',
    subtitle: 'Required for best CLI flows',
    body:
      'Install the Giljo slash commands so your CLI tool can quickly call MCP tools and fetch instructions. This is the baseline for a great UX.',
    details:
      'Slash commands provide short, consistent “entry points” so you can fetch missions, refresh instructions, and run guided actions without copying large prompts around.',
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
    details:
      'Templates are the “profiles” for orchestrator + agents. Claude Code can optionally install/export templates locally for maximum convenience. In multi-terminal mode, templates can be fetched from the server as agents run.',
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
    details:
      'Context settings allow you to turn context sources on/off and define their level of importance. This frames how the MCP server prepares tools and prompts for agents. You can also configure context depth (how much information is provided) for selected sources.',
    primaryAction: {
      id: 'open-context-primary',
      label: 'Open Context',
      type: 'userSettingsTab',
      tab: 'context',
    },
    actions: [],
  },
  {
    id: 'product',
    icon: 'mdi-package-variant-closed',
    title: 'Add a product',
    subtitle: 'Your top-level container',
    body:
      'Create a product to hold your vision, architecture, context, and long-lived memory. This is what keeps agents focused and consistent.',
    details:
      'A product is your top-level object. You can have multiple products. Each product can have many projects and tasks, and is the anchor for long-term context and 360 memory.',
    primaryAction: {
      id: 'open-products-primary',
      label: 'Open Products',
      type: 'route',
      route: { name: 'Products' },
    },
    actions: [],
  },
  {
    id: 'project',
    icon: 'mdi-briefcase-outline',
    title: 'Add a project',
    subtitle: 'Incremental work inside a product',
    body:
      'Create a project to describe the work you want to implement. Projects are incremental and historical “units of work” inside a product.',
    details:
      'Projects let you plan, execute, and review work in a product over time. They pair naturally with tasks and agent runs.',
    primaryAction: {
      id: 'open-projects-primary',
      label: 'Open Projects',
      type: 'route',
      route: { name: 'Projects' },
    },
    actions: [],
  },
  {
    id: 'tasks',
    icon: 'mdi-clipboard-check-outline',
    title: 'Run & track tasks',
    subtitle: 'User-managed TODO tracking',
    body:
      'Use tasks to break work down, track progress, and keep orchestrations aligned. This is also where “technical” housekeeping work can live.',
    details:
      'Tasks are user-managed, visible tracking. They’re ideal for splitting work into small, auditable pieces and keeping agents aligned with the current plan.',
    primaryAction: {
      id: 'open-tasks-primary',
      label: 'Open Tasks',
      type: 'route',
      route: { name: 'Tasks' },
    },
    actions: [],
  },
  {
    id: 'advanced',
    icon: 'mdi-cog-outline',
    title: 'Advanced integrations',
    subtitle: 'Git, Serena, and more',
    body:
      'Enable advanced integrations like Git and Serena prompt-injection helpers. These are optional, but can significantly improve workflows.',
    details:
      `Current status: Git is ${props.gitEnabled ? 'enabled' : 'disabled'}; Serena is ${
        props.serenaEnabled ? 'enabled' : 'disabled'
      }. Configure these (and more) under Integrations.`,
    primaryAction: {
      id: 'open-integrations-advanced-primary',
      label: 'Open Integrations',
      type: 'userSettingsTab',
      tab: 'integrations',
    },
    actions: [],
  },
])

const selectedStepId = ref(steps.value[0]?.id ?? 'tools')

const selectedStep = computed(() => steps.value.find((s) => s.id === selectedStepId.value) ?? steps.value[0])

const accentColor = computed(() => (theme.global.current.value.dark ? 'secondary' : 'primary'))

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

function stepTone(step) {
  if (!step) return 'primary'
  if (step.id === 'advanced' && (props.gitEnabled || props.serenaEnabled)) return 'success'
  return accentColor.value
}

function openDetails(step) {
  detailsStep.value = step
  showDetails.value = true
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
</script>

<style scoped>
/* Tighten the "bullet" indent so icon → text spacing matches desired feel */
.startup-quickstart :deep(.v-list-item__prepend) {
  margin-inline-end: 15px !important;
}

/* Improve button readability in dark mode by nudging tonal backgrounds brighter */
.v-theme--dark .startup-quickstart :deep(.v-btn.v-btn--variant-tonal) {
  filter: brightness(1.08);
}

.quickstart-go-btn {
  border-radius: 9999px !important;
  font-weight: 700;
  letter-spacing: 0.02em;
  min-width: 56px;
  --v-btn-height: 24px;
  height: var(--v-btn-height) !important;
  min-height: var(--v-btn-height) !important;
  padding-inline: 14px !important;
  color: rgb(var(--v-theme-on-secondary)) !important;
}

.steps-chip {
  margin-right: 6px;
}
</style>
