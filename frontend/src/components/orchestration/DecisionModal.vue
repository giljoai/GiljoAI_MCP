<template>
  <v-dialog
    :model-value="show"
    :max-width="isMobile ? undefined : '560'"
    :fullscreen="isMobile"
    persistent
    role="dialog"
    aria-labelledby="decision-modal-title"
    data-testid="decision-modal"
    @update:model-value="(v) => { if (!v) handleCancel() }"
    @keydown.esc="handleCancel"
  >
    <v-card v-draggable class="smooth-border decision-modal-card">
      <div id="decision-modal-title" class="dlg-header dlg-header--primary">
        <v-icon
          class="dlg-icon"
          :icon="decided ? 'mdi-check-circle-outline' : 'mdi-clipboard-check-outline'"
        />
        <span class="dlg-title">
          {{ decided ? 'Orchestrator unlocked' : 'Decision Required' }}
        </span>
        <v-btn
          icon
          variant="text"
          size="small"
          class="dlg-close"
          :aria-label="'Close dialog'"
          @click="handleCancel"
        >
          <v-icon icon="mdi-close" size="18" />
        </v-btn>
      </div>

      <v-divider />

      <div class="decision-modal-body">
        <!-- State 1: pre-decision — render ApprovalCard with the option buttons -->
        <ApprovalCard
          v-if="!decided && approval"
          :approval="approval"
          data-testid="decision-modal-card"
          @decided="handleDecided"
        />

        <!-- State 2: post-decision — static confirmation text.
             No spinner, no fetch, no waiting. Plain text in a div.
             User clicks Close and goes back to the orchestrator chat. -->
        <p
          v-else-if="decided"
          class="decision-modal-confirmation"
          data-testid="decision-modal-confirmation"
        >
          Your choice has been sent to the orchestrator. Please tell it to read
          its message and proceed.
        </p>
      </div>

      <div class="dlg-footer">
        <v-spacer />
        <v-btn
          v-if="decided"
          color="primary"
          variant="flat"
          data-testid="decision-modal-close"
          @click="handleCancel"
        >
          Close
        </v-btn>
        <v-btn
          v-else
          variant="text"
          :aria-label="'Cancel'"
          @click="handleCancel"
        >
          Cancel
        </v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useDisplay } from 'vuetify'
import ApprovalCard from '@/components/orchestration/ApprovalCard.vue'
import { useApprovalsStore } from '@/stores/useApprovalsStore'

const props = defineProps({
  show: {
    type: Boolean,
    required: true,
  },
  orchestratorJobId: {
    type: String,
    default: null,
  },
})

const emit = defineEmits(['close'])

const approvalsStore = useApprovalsStore()
const { mobile } = useDisplay()
const isMobile = computed(() => mobile.value)

const decided = ref(false)

const approval = computed(() => {
  if (!props.orchestratorJobId) return null
  return approvalsStore.findByJobId(props.orchestratorJobId)
})

// Reset local state every time the dialog opens, so a future approval doesn't
// land on a stale "decided" confirmation from a prior cycle.
watch(
  () => props.show,
  (open) => {
    if (open) {
      decided.value = false
      approvalsStore.fetchPending().catch(() => {})
    }
  },
)

function handleCancel() {
  emit('close')
}

function handleDecided() {
  // ApprovalCard already POSTed to /decide and the store optimistically removed
  // the row. Flip local state so the body renders the static confirmation text.
  decided.value = true
}
</script>

<style scoped lang="scss">
.decision-modal-card {
  background: rgb(var(--v-theme-surface));
}

.decision-modal-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.decision-modal-confirmation {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.45;
  color: rgba(255, 255, 255, 0.92);
}
</style>
