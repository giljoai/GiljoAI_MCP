<template>
  <v-dialog :model-value="modelValue" max-width="980" @update:model-value="emitModelValue">
    <v-card v-draggable>
      <v-card-title class="d-flex align-center justify-space-between">
        <div class="d-flex align-center ga-2">
          <v-icon color="secondary">mdi-information-outline</v-icon>
          <span>What is GiljoAI MCP?</span>
          <v-chip size="small" variant="tonal" color="secondary">{{ activeIndex + 1 }}/{{ slides.length }}</v-chip>
        </div>
        <div class="d-flex align-center ga-2">
          <v-checkbox
            v-model="dontShowAgain"
            density="compact"
            hide-details
            label="Don’t show again"
            color="secondary"
            class="intro-hide-checkbox"
          />
          <v-btn icon="mdi-close" variant="text" @click="close()" />
        </div>
      </v-card-title>

      <v-card-text>
        <v-window v-model="activeIndex" :touch="false" :reverse="false">
          <v-window-item v-for="slide in slides" :key="slide.id">
            <div class="intro-slide-header">
              <div class="intro-slide-title">{{ slide.title }}</div>
              <div class="intro-slide-body" :style="slideBodyStyle(slide)">{{ slide.body }}</div>
            </div>

            <v-row v-if="slide.panels?.length" class="mt-4" dense justify="center">
              <v-col v-for="panel in slide.panels" :key="panel.title" cols="12" sm="6" md="6">
                <v-card variant="outlined" class="h-100 intro-panel-card">
                  <v-card-text class="d-flex align-center justify-center intro-panel-content">
                    <div class="d-flex align-center ga-4 intro-panel-inner">
                      <div class="d-flex align-center justify-center intro-panel-icon">
                        <GiljoFaceIcon
                          v-if="panel.useGiljoIcon"
                          :active="true"
                          :size="36"
                          alt="Agent"
                        />
                        <v-icon v-else size="36" color="secondary">{{ panel.icon }}</v-icon>
                      </div>
                      <div class="intro-panel-text">
                        <div class="intro-panel-title">{{ panel.title }}</div>
                        <div class="intro-panel-caption">{{ panel.caption }}</div>
                      </div>
                    </div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <v-list v-if="slide.bullets?.length" density="compact" class="intro-bullets mt-2">
              <v-list-item v-for="bullet in slide.bullets" :key="bullet">
                <template #prepend>
                  <v-icon size="18" color="secondary">mdi-check</v-icon>
                </template>
                <v-list-item-title class="text-body-2">{{ bullet }}</v-list-item-title>
              </v-list-item>
            </v-list>

            <v-img
              v-if="slide.imageSrc"
              :src="slide.imageSrc"
              :alt="slide.imageAlt || slide.title"
              class="mt-4 rounded"
              max-height="360"
              cover
            />

            <v-alert v-if="slide.note" type="info" variant="tonal" density="compact" class="mt-3">
              {{ slide.note }}
            </v-alert>

            <div v-if="slide.actions?.length" class="d-flex flex-wrap ga-2 mt-4">
              <v-btn
                v-for="action in slide.actions"
                :key="action.id"
                :color="action.tone || 'primary'"
                :variant="action.variant || 'tonal'"
                size="small"
                @click="runAction(action)"
              >
                <v-icon v-if="action.icon" start>{{ action.icon }}</v-icon>
                {{ action.label }}
              </v-btn>
            </div>
          </v-window-item>
        </v-window>
      </v-card-text>

      <v-divider />

      <v-card-actions class="d-flex flex-column align-center ga-2">
        <div class="d-flex ga-2 flex-wrap justify-center w-100">
          <v-btn variant="text" :disabled="activeIndex === 0" @click="prev">Back</v-btn>
          <v-btn variant="tonal" @click="skip">Skip</v-btn>
          <v-btn color="secondary" variant="flat" @click="next">
            {{ activeIndex === slides.length - 1 ? 'Finish' : 'Next' }}
          </v-btn>
        </div>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import GiljoFaceIcon from '@/components/icons/GiljoFaceIcon.vue'

const INTRO_HIDDEN_KEY = 'giljo_intro_tour_hidden'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'navigate'])

const router = useRouter()

const activeIndex = ref(0)
const dontShowAgain = ref(false)

const slides = computed(() => [
  {
    id: 'what',
    icon: 'mdi-rocket-launch-outline',
    title: 'Your orchestration server for AI coding tools',
    body:
      'GiljoAI MCP is a web dashboard + backend that coordinates your AI coding tools via MCP over HTTP. It keeps your product context organized, enables multi-agent workflows, tracks projects for audit, and captures technical debt as tasks.',
    bodyMaxWidth: 760,
    panels: [
      { icon: 'mdi-package-variant-closed', title: 'Products', caption: 'Structured product context' },
      { icon: 'mdi-briefcase-outline', title: 'Projects', caption: 'Staging → launch workflows' },
      { icon: 'mdi-clipboard-check-outline', title: 'Tasks', caption: 'Capture ideas; stay focused' },
      { icon: 'mdi-lan-connect', title: 'MCP over HTTP', caption: 'Tool-agnostic integrations' },
    ],
    bullets: [
      'Coordinate CLI tools via MCP over HTTP (Claude Code, Codex, Gemini, others).',
      'Keep product context structured so agents stay aligned.',
      'Capture ideas as tasks without breaking flow.',
    ],
  },
  {
    id: 'problem',
    icon: 'mdi-alert-decagram-outline',
    title: 'The problem: context limits and drift',
    body:
      'Large codebases and long-running work cause context drift. Tools re-discover the same patterns, prompts bloat, and progress becomes hard to track.',
    bullets: [
      'One assistant can’t keep the whole system in mind forever.',
      'Copy/paste “mega prompts” are brittle and hard to audit.',
      'Ideas appear mid-flow; without capture, you either derail or forget them.',
    ],
  },
  {
    id: 'solution',
    icon: 'mdi-brain',
    title: 'The solution: persistent missions + focused agents',
    body:
      'GiljoAI stores “what you’re building” in a structured hierarchy (product → projects → jobs). You enter context once, and the orchestrator uses it to generate focused, role-based missions for each run.',
    panels: [
      { icon: 'mdi-clipboard-check-outline', title: 'Jobs', caption: 'Tracked work units & progress' },
      { icon: 'mdi-memory', title: '360 Memory', caption: 'Cumulative learnings across projects (as context depth)' },
      { icon: 'mdi-layers-triple', title: 'Context controls', caption: 'Toggle + depth settings' },
      { icon: 'mdi-robot-outline', title: 'Agent templates', caption: 'Reusable roles + profiles', useGiljoIcon: true },
    ],
    bullets: [
      'Thin prompts: fetch instructions/missions from the server when needed.',
      'Context toggles + depth controls decide what to include.',
      'Agents coordinate via jobs, status updates, and stored outcomes.',
    ],
  },
  {
    id: 'modes',
    icon: 'mdi-console',
    title: 'Two working styles',
    body:
      'Pick what fits your workflow. Claude Code is the most integrated path; multi-terminal mode is the most flexible path.',
    bodyMaxWidth: 660,
    panels: [
      { icon: 'mdi-console', title: 'Claude Code mode', caption: 'Subagents from templates' },
      { icon: 'mdi-console-network', title: 'Multi-terminal mode', caption: 'Codex + others side-by-side' },
      { icon: 'mdi-slash-forward', title: 'Slash commands', caption: 'Fast “thin prompt” entry points' },
      { icon: 'mdi-puzzle', title: 'Integrations', caption: 'Connect tools via /mcp' },
    ],
    bullets: [
      'Claude Code mode: orchestrator spawns subagents from templates.',
      'Multi-terminal mode: you run agent terminals (Codex + others) side-by-side.',
      'Both modes talk to the same MCP server via HTTP JSON-RPC.',
    ],
    actions: [
      {
        id: 'go-integrations',
        label: 'Open Integrations',
        icon: 'mdi-puzzle',
        type: 'userSettingsTab',
        tab: 'integrations',
      },
    ],
  },
  {
    id: 'flow',
    icon: 'mdi-transit-connection-variant',
    title: 'Orchestrator workflow',
    body:
      'GiljoAI follows a predictable pipeline: staging → discovery → spawning → execution. Jobs are tracked, progress is visible, and communication is logged.',
    imageSrc: '/onboarding/workflow.jpg',
    imageAlt: 'GiljoAI MCP workflow overview diagram',
    bullets: [
      'Jobs: pending → working → complete (with progress reporting).',
      'Messaging + status updates stream to the UI in real time.',
      'Missions live on the server for replay and auditability.',
    ],
  },
  {
    id: 'tasks',
    icon: 'mdi-clipboard-check-outline',
    title: 'Tasks keep you disciplined',
    body:
      'When ideas pop up mid-coding, you can “punt” them into tasks without derailing. Later, tasks can be promoted into full projects.',
    bullets: [
      'Capture ideas instantly via MCP tools.',
      'Track technical debt and TODOs in one place.',
      'Convert a task into a project when you’re ready.',
    ],
    actions: [
      { id: 'go-tasks', label: 'Open Tasks', icon: 'mdi-clipboard-check', type: 'route', route: { name: 'Tasks' } },
    ],
  },
  {
    id: 'advanced',
    icon: 'mdi-cog-outline',
    title: 'Optional power-ups',
    body:
      'Integrations like Git and Serena can improve ergonomics and help agents stay aligned. You can enable these when you’re ready.',
    bullets: [
      'Git integration: commit history + context injection options.',
      'Serena: prompt-injection helper toggle.',
      'Context settings: prioritize what matters most for your product.',
    ],
    actions: [
      { id: 'go-context', label: 'Open Context Settings', icon: 'mdi-layers-triple', type: 'userSettingsTab', tab: 'context' },
    ],
  },
  {
    id: 'next',
    icon: 'mdi-flag-checkered',
    title: 'Next: run the Startup quick start',
    body:
      'The Startup tab is your “do this now” checklist: connect your tool(s), install slash commands, create a product/project, and start running tasks.',
    note: 'Tip: you can always reopen this mini-tour using the (?) button next to the Startup tab.',
    actions: [
      { id: 'go-startup', label: 'Go to Startup', icon: 'mdi-rocket-launch', type: 'userSettingsTab', tab: 'startup' },
    ],
  },
])

function slideBodyStyle(slide) {
  if (!slide?.bodyMaxWidth) return undefined
  return { maxWidth: `${slide.bodyMaxWidth}px` }
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    activeIndex.value = 0
    dontShowAgain.value = isHidden()
  },
)

function isHidden() {
  try {
    return localStorage.getItem(INTRO_HIDDEN_KEY) === '1'
  } catch {
    return false
  }
}

function persistHiddenPreference() {
  try {
    if (dontShowAgain.value) {
      localStorage.setItem(INTRO_HIDDEN_KEY, '1')
    } else {
      localStorage.removeItem(INTRO_HIDDEN_KEY)
    }
  } catch {
    // ignore (e.g. storage blocked)
  }
}

function emitModelValue(value) {
  emit('update:modelValue', value)
}

function close() {
  persistHiddenPreference()
  emitModelValue(false)
}

function next() {
  if (activeIndex.value >= slides.value.length - 1) {
    close()
    return
  }
  activeIndex.value += 1
}

function prev() {
  if (activeIndex.value <= 0) return
  activeIndex.value -= 1
}

function skip() {
  close()
}

function runAction(action) {
  if (!action) return
  if (action.type === 'userSettingsTab') {
    close()
    router.push({ name: 'UserSettings', query: { tab: action.tab } })
    return
  }
  if (action.type === 'route') {
    close()
    router.push(action.route)
  }
}
</script>

<style scoped>
.intro-slide-header {
  text-align: center;
  max-width: 820px;
  margin: 0 auto 8px auto;
}

.intro-slide-title {
  font-weight: 600;
  background: var(--gradient-brand);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-size: clamp(1.05rem, 1.32vw + 0.77rem, 1.6rem);
  line-height: 1.15;
}

.intro-slide-body {
  max-width: 760px;
  margin: 6px auto 0 auto;
  color: rgba(var(--v-theme-on-surface), 0.86);
  font-size: clamp(0.75rem, 0.85vw + 0.45rem, 1.0rem);
  line-height: 1.2;
}

.intro-bullets {
  max-width: 760px;
  margin-left: min(33%, 260px);
  margin-right: auto;
}

@media (max-width: 600px) {
  .intro-bullets {
    margin-left: 0;
  }
}

.intro-panel-card {
  border-radius: 18px;
  position: relative;
  background: rgb(var(--v-theme-surface));
}

.intro-panel-card::before {
  content: '';
  position: absolute;
  inset: 0;
  padding: 4px; /* border thickness */
  border-radius: inherit;
  background: var(--gradient-brand);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}

.intro-panel-content {
  padding: 18px;
  min-height: 96px;
}

.intro-panel-inner {
  width: 100%;
  justify-content: flex-start;
  padding-left: clamp(18px, 22%, 150px);
}

@media (max-width: 600px) {
  .intro-panel-inner {
    padding-left: 16px;
  }
}

.intro-panel-icon {
  width: 56px;
  height: 56px;
  flex: 0 0 56px;
}

.intro-panel-text {
  text-align: left;
}

/* "Tripled" emphasis: scale up the box typography significantly */
.intro-panel-title {
  font-weight: 700;
  line-height: 1.15;
  font-size: clamp(0.95rem, 1.2vw + 0.7rem, 1.45rem);
}

.intro-panel-caption {
  margin-top: 4px;
  line-height: 1.2;
  color: rgba(var(--v-theme-on-surface), 0.82);
  font-size: clamp(0.75rem, 0.85vw + 0.45rem, 1.0rem);
}

.intro-hide-checkbox :deep(.v-label) {
  font-size: 0.875rem;
}
</style>
