<template>
  <div
    v-if="pendingApprovals.length"
    class="approval-banner-stack"
    data-testid="approval-banner-stack"
  >
    <button
      v-for="approval in pendingApprovals"
      :key="approval.id"
      type="button"
      class="approval-banner smooth-border"
      :style="bannerStyle(approval)"
      :data-testid="`approval-banner-${approval.id}`"
      :aria-label="`Review and decide: ${approval.reason}`"
      @click="openDialog(approval)"
    >
      <span class="approval-banner__badge" :style="badgeStyle(approval)">
        {{ initials(approval) }}
      </span>
      <span class="approval-banner__body">
        <span class="approval-banner__title">
          {{ approval.agent_display_name || 'agent' }} needs your decision
        </span>
        <span class="approval-banner__reason">{{ approval.reason }}</span>
      </span>
      <span class="approval-banner__cta" aria-hidden="true">
        Review &amp; decide →
      </span>
    </button>

    <v-dialog
      :model-value="dialogApproval !== null"
      max-width="560"
      data-testid="approval-banner-dialog"
      @update:model-value="onDialogToggle"
    >
      <div v-if="dialogApproval" class="approval-banner-dialog-shell">
        <div class="approval-banner-dialog-hint">
          Read the agent's reasoning in chat before choosing.
        </div>
        <ApprovalCard
          :approval="dialogApproval"
          data-testid="approval-banner-dialog-card"
          @decided="closeDialog"
        />
        <div class="approval-banner-dialog-actions">
          <button
            type="button"
            class="approval-banner-dialog-close"
            data-testid="approval-banner-dialog-close"
            @click="closeDialog"
          >
            Close without deciding
          </button>
        </div>
      </div>
    </v-dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useApprovalsStore } from '@/stores/useApprovalsStore'
import ApprovalCard from '@/components/orchestration/ApprovalCard.vue'
import { getAgentColor } from '@/config/agentColors'
import { hexToRgba } from '@/utils/colorUtils'

const approvalsStore = useApprovalsStore()
const pendingApprovals = computed(() => approvalsStore.pendingApprovals)

const dialogApproval = ref(null)

function openDialog(approval) {
  dialogApproval.value = approval
}
function closeDialog() {
  dialogApproval.value = null
}
function onDialogToggle(value) {
  if (!value) closeDialog()
}

function colorFor(approval) {
  const c = getAgentColor(approval?.agent_display_name || '')
  return c?.hex || '#8895a8'
}
function initials(approval) {
  const c = getAgentColor(approval?.agent_display_name || '')
  return c?.badge || '?'
}
function bannerStyle(approval) {
  const hex = colorFor(approval)
  return {
    '--smooth-border-color': hexToRgba(hex, 0.55),
    background: hexToRgba(hex, 0.1),
  }
}
function badgeStyle(approval) {
  const hex = colorFor(approval)
  return {
    backgroundColor: hexToRgba(hex, 0.18),
    color: hex,
  }
}

defineExpose({ dialogApproval })
</script>

<style scoped lang="scss">
.approval-banner-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 16px 0;
}

.approval-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 14px;
  border-radius: 10px;
  text-align: left;
  cursor: pointer;
  background: transparent;
  color: inherit;
  font: inherit;
  transition: filter 120ms ease;
}

.approval-banner:hover,
.approval-banner:focus-visible {
  filter: brightness(1.08);
}
.approval-banner:focus-visible {
  outline: 2px solid var(--smooth-border-color, #ffd15b);
  outline-offset: 2px;
}

.approval-banner__badge {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 12px;
  letter-spacing: 0.5px;
  flex-shrink: 0;
}

.approval-banner__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.approval-banner__title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
}

.approval-banner__reason {
  font-size: 12px;
  color: var(--text-secondary, #a3aac4);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.approval-banner__cta {
  font-size: 12px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
  flex-shrink: 0;
}

.approval-banner-dialog-shell {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  background: #12202e;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
}

.approval-banner-dialog-hint {
  font-size: 12px;
  color: var(--text-muted, #8895a8);
}

.approval-banner-dialog-actions {
  display: flex;
  justify-content: flex-end;
}

.approval-banner-dialog-close {
  background: transparent;
  color: var(--text-secondary, #a3aac4);
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
}
.approval-banner-dialog-close:hover {
  color: rgba(255, 255, 255, 0.92);
}
</style>
