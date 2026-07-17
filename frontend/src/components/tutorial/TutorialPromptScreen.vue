<template>
  <div class="prompt-screen">
    <div class="beat-eyebrow">{{ meta.eyebrow }}</div>
    <h2 class="beat-title">{{ meta.title }}</h2>
    <p class="beat-sub">{{ meta.sub }}</p>

    <div class="prompt-box" data-testid="tutorial-prompt-text">{{ promptText }}</div>

    <div class="prompt-actions">
      <v-btn
        color="primary"
        variant="flat"
        class="copy-btn"
        data-testid="tutorial-copy-prompt"
        :prepend-icon="copied ? 'mdi-check' : 'mdi-content-copy'"
        @click="copyPrompt"
      >
        {{ copied ? 'Copied' : 'Copy prompt' }}
      </v-btn>

      <v-btn
        v-if="path === 'B'"
        variant="text"
        class="continue-btn"
        data-testid="tutorial-b-upload"
        prepend-icon="mdi-file-upload-outline"
        @click="$emit('upload')"
      >
        I have my vision document
      </v-btn>

      <span v-if="path === 'D' && agentDone" class="agent-done" data-testid="tutorial-agent-done">
        Your agent reports done — review it
      </span>
      <span v-else-if="path === 'D'" class="agent-waiting">
        <span class="waiting-dot" /> Waiting for your agent…
      </span>
    </div>

    <p class="prompt-hint">{{ meta.hint }}</p>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useProductStore } from '@/stores/products'
import { useClipboard } from '@/composables/useClipboard'
import { useGiljoMode } from '@/composables/useGiljoMode'
import { PROMPT_META, buildPromptB, buildPromptD } from '@/content/onboarding/prompts'

const props = defineProps({
  /** Router door: 'D' (existing codebase) or 'B' (guided interview). */
  path: {
    type: String,
    required: true,
    validator: (v) => v === 'D' || v === 'B',
  },
  /** THE tutorial-run product id, threaded via useTutorialState (gate F1). */
  productId: {
    type: String,
    default: null,
  },
})

const emit = defineEmits(['review', 'upload', 'product-created'])

const productStore = useProductStore()
const { copy } = useClipboard()
const { isSaasMode } = useGiljoMode()

const meta = computed(() => PROMPT_META[props.path])
const productId = ref('')
const agentDone = ref(false)
const copied = ref(false)

const promptText = computed(() =>
  props.path === 'D'
    ? buildPromptD({ productId: productId.value, saas: isSaasMode() })
    : buildPromptB({ saas: isSaasMode() }),
)

let copiedTimer = null
async function copyPrompt() {
  const ok = await copy(promptText.value)
  if (!ok) return
  copied.value = true
  clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => {
    copied.value = false
  }, 1500)
}

// ── Path D "agent is done" DONE-SIGNAL SEAM ──────────────────────────────────
// agentReportsDone() is the SINGLE decision point for "the agent's pass is
// complete" — every signal (WS event AND poll tick AND mount check) funnels
// a freshly fetched product row through it.
//
// PROGRESSIVE-FILL contract (design ruling, Patrik-ratified): Prompt-D writes
// the card section by section (Info → Tech → Arch → Testing) and the
// consolidated vision LAST. Intermediate writes only refresh the card display
// (each WS event/poll tick re-fetches the row into the store) — ONLY the
// final consolidated-vision write advances to review. NOT the
// vision_analysis_complete flag: with zero uploaded docs the evaluator never
// flips it (requires >=1 active doc — locked by
// tests/test_fe9200_tutorial_prompt_contract.py).
function agentReportsDone(product) {
  return Boolean(product?.consolidated_vision_light)
}

// LIVE signal: update_product_fields emits vision:analysis_complete on every
// write (post-commit) — caught below via the window event, then verified
// through the seam. POLL fallback: FE-9166 idiom, 10s.
const POLL_INTERVAL_MS = 10_000
let pollTimer = null
let pollInFlight = false

function markAgentDone() {
  if (agentDone.value) return
  agentDone.value = true
  stopPolling()
  // Surface the "reports done" line, then advance to review.
  setTimeout(() => emit('review'), 1200)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  pollInFlight = false
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (pollInFlight || !productId.value) return
    pollInFlight = true
    try {
      const updated = await productStore.fetchProductById(productId.value)
      if (agentReportsDone(updated)) markAgentDone()
    } catch {
      // Transient poll failures are fine — next tick retries.
    } finally {
      pollInFlight = false
    }
  }, POLL_INTERVAL_MS)
}

async function onVisionComplete(event) {
  if (!event.detail?.product_id || event.detail.product_id !== productId.value) return
  // The event only says "a write landed" — the seam decides whether the pass
  // is COMPLETE (guards progressive fill's intermediate writes).
  try {
    const updated = await productStore.fetchProductById(productId.value)
    if (agentReportsDone(updated)) markAgentDone()
  } catch {
    // Poll fallback keeps running.
  }
}

// Path D needs an existing product card for the agent to populate: the
// silent-create idiom (useProductVisionUpload), created with an EMPTY name so
// the agent can set product_name from the repo (merge-write only skips fields
// that are already non-empty).
//
// GATE F1: only a product THIS RUN owns may drive the flow. The threaded
// s.productId is authoritative; absent that, we may adopt ONLY a previous
// tutorial draft (empty-named AND inactive — user-created products always
// carry a name). NEVER products[0]: the list is ordered is_active.desc, so
// [0] is the user's real ACTIVE product whenever one exists — selecting it
// would present it as "proposed" and let Activate deactivate it.
async function ensureProduct() {
  if (props.productId) {
    productId.value = props.productId
    try {
      const row = await productStore.fetchProductById(props.productId)
      if (agentReportsDone(row)) markAgentDone()
    } catch {
      // Poll will retry.
    }
    return
  }

  const draft = productStore.products.find((p) => !p.is_active && !(p.name || '').trim())
  if (draft) {
    productId.value = draft.id
    emit('product-created', draft.id)
    return
  }

  try {
    const product = await productStore.createProduct({ name: '' })
    productId.value = product?.id || ''
  } catch {
    // Fall back to a named draft if the backend rejects an empty name; the
    // user can rename it from the product form afterwards.
    try {
      const product = await productStore.createProduct({ name: 'My product' })
      productId.value = product?.id || ''
    } catch {
      productId.value = ''
    }
  }
  if (productId.value) emit('product-created', productId.value)
}

onMounted(async () => {
  if (props.path !== 'D') return
  await ensureProduct()
  if (!agentDone.value) {
    window.addEventListener('vision-analysis-complete', onVisionComplete)
    startPolling()
  }
})

onBeforeUnmount(() => {
  stopPolling()
  clearTimeout(copiedTimer)
  window.removeEventListener('vision-analysis-complete', onVisionComplete)
})
</script>

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;

.prompt-screen {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.beat-eyebrow {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.2em;
  color: $color-brand-yellow;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.beat-title {
  margin: 0 0 6px;
  font-family: 'Outfit', $typography-font-primary;
  font-weight: 700;
  font-size: 26px;
  letter-spacing: -0.02em;
  color: $color-text-primary;
}

.beat-sub {
  margin: 0 0 14px;
  font-size: 14px;
  line-height: 1.55;
  color: var(--text-secondary);
}

.prompt-box {
  background: $color-background-primary;
  border-radius: $border-radius-md;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
  padding: 16px 18px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  line-height: 1.75;
  color: var(--text-secondary);
  white-space: pre-wrap;
  overflow-y: auto;
  min-height: 0;
}

.prompt-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 14px;
}

.copy-btn {
  font-family: 'Outfit', $typography-font-primary;
  font-weight: 600;
  border-radius: $border-radius-default;
  background: $color-brand-yellow !important;
  color: $color-on-yellow-ink !important;

  &:hover {
    background: $color-brand-yellow-hover !important;
  }
}

.continue-btn {
  color: var(--text-secondary) !important;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14);
  border-radius: $border-radius-default;
}

.agent-waiting {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  color: var(--text-muted);
}

.waiting-dot {
  width: 8px;
  height: 8px;
  border-radius: $border-radius-pill;
  background: $color-status-waiting;
  animation: tutorialPulse 1.6s ease infinite;
}

@keyframes tutorialPulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

.agent-done {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  color: $color-status-complete;
}

.prompt-hint {
  margin: 12px 0 0;
  font-size: 12px;
  color: var(--text-muted);
}
</style>
