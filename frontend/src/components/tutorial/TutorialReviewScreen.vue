<template>
  <div class="review-screen">
    <div class="beat-eyebrow">Agent report · done</div>
    <h2 class="beat-title">Your agent proposed this product.</h2>
    <p class="beat-sub">Glance it over. Activating makes it the brief every agent reads.</p>

    <div class="review-card" data-testid="tutorial-review-card">
      <div class="review-head">
        <span class="review-name">{{ product?.name || 'Your product' }}</span>
        <span class="proposed-pill">PROPOSED BY YOUR AGENT</span>
      </div>

      <div v-if="techChips.length" class="chip-row">
        <span v-for="chip in techChips" :key="chip" class="chip chip--tech">{{ chip }}</span>
        <span v-if="product?.vision_analysis_complete" class="chip chip--vision">Vision doc · generated ✓</span>
      </div>

      <p v-if="descriptionExcerpt" class="review-desc">{{ descriptionExcerpt }}</p>
    </div>

    <div class="review-actions">
      <v-btn
        color="primary"
        variant="flat"
        class="activate-btn"
        data-testid="tutorial-activate"
        prepend-icon="mdi-play"
        :disabled="!product"
        @click="activate"
      >
        Activate product
      </v-btn>
      <span class="review-hint">
        Want changes? Tell your agent in your CLI — e.g.
        <span class="hint-mono">"tighten the tech stack to…"</span>
        — or edit the form manually.
      </span>
    </div>

    <!-- First product never triggers this (no prior active product —
         useProductActivation only opens it when another product is active),
         but the flow is reused EXACTLY, dialog included. -->
    <ActivationWarningDialog
      v-model="showActivationWarning"
      :new-product="pendingActivation || {}"
      :current-active="currentActiveProduct || {}"
      @confirm="confirmAndFinish"
      @cancel="cancelActivation"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import ActivationWarningDialog from '@/components/products/ActivationWarningDialog.vue'
import { useProductActivation } from '@/composables/useProductActivation'
import { useProductStore } from '@/stores/products'

const props = defineProps({
  /** THE tutorial-run product id, threaded via useTutorialState (gate F1) —
   *  this screen must NEVER re-derive products[0] (ordered is_active.desc,
   *  i.e. the user's real active product). */
  productId: {
    type: String,
    default: null,
  },
})

const emit = defineEmits(['activated'])

const productStore = useProductStore()

const {
  showActivationWarning,
  pendingActivation,
  currentActiveProduct,
  toggleProductActivation,
  confirmActivation,
  cancelActivation,
} = useProductActivation(() => productStore.fetchProducts())

const product = ref(null)

onMounted(async () => {
  // Render THE run-owned product — freshly fetched so the agent's writes are
  // in. No id = no product; Activate stays disabled (never guess from the
  // store list).
  if (!props.productId) return
  try {
    product.value = (await productStore.fetchProductById(props.productId)) || null
  } catch {
    product.value = null
  }
})

const techChips = computed(() => {
  const ts = product.value?.tech_stack || {}
  const chips = []
  for (const key of ['programming_languages', 'frontend_frameworks', 'backend_frameworks', 'databases_storage']) {
    const value = ts[key]
    if (typeof value === 'string' && value.trim()) {
      chips.push(...value.split(',').map((s) => s.trim()).filter(Boolean))
    }
  }
  return chips.slice(0, 6)
})

const descriptionExcerpt = computed(() => {
  const desc = product.value?.description || ''
  return desc.length > 220 ? `${desc.slice(0, 220)}…` : desc
})

async function activate() {
  if (!product.value) return
  // Already active (e.g. the user activated it from the Products page
  // mid-flow): toggleProductActivation would DEACTIVATE it — skip straight
  // to done instead (gate F1's deactivation hazard).
  if (product.value.is_active || productStore.activeProduct?.id === product.value.id) {
    emit('activated')
    return
  }
  await toggleProductActivation(product.value)
  // First-product path: no warning dialog opened → activation ran directly.
  if (!showActivationWarning.value) emit('activated')
}

async function confirmAndFinish() {
  await confirmActivation()
  emit('activated')
}
</script>

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;

.review-screen {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.beat-eyebrow {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.2em;
  color: $color-agent-researcher;
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

.review-card {
  background: $elevation-raised;
  border-radius: $border-radius-rounded;
  box-shadow: inset 0 0 0 1px rgba($color-agent-researcher, 0.35);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 11px;
}

.review-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.review-name {
  font-family: 'Outfit', $typography-font-primary;
  font-weight: 600;
  font-size: 17px;
  color: $color-text-primary;
}

.proposed-pill {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 9.5px;
  color: $color-agent-researcher;
  background: rgba($color-agent-researcher, 0.12);
  padding: 4px 10px;
  border-radius: $border-radius-pill;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.chip {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10.5px;
  padding: 5px 10px;
  border-radius: $border-radius-pill;
}

.chip--tech {
  color: $color-agent-implementor;
  background: rgba($color-agent-implementor, 0.12);
}

.chip--vision {
  color: $color-agent-researcher;
  background: rgba($color-agent-researcher, 0.12);
}

.review-desc {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.review-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 16px;
}

.activate-btn {
  font-family: 'Outfit', $typography-font-primary;
  font-weight: 600;
  font-size: 13.5px;
  border-radius: $border-radius-default;
  flex-shrink: 0;
  background: $color-brand-yellow !important;
  color: $color-on-yellow-ink !important;

  &:hover {
    background: $color-brand-yellow-hover !important;
  }
}

.review-hint {
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-muted);
}

.hint-mono {
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-secondary);
}
</style>
