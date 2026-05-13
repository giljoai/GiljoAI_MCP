/**
 * useApprovalsStore — pending user_approval inbox (FE-5017 Phase C).
 *
 * Edition Scope: CE.
 *
 * Purpose: surface backend `user_approvals` rows the dashboard needs to render
 * an ApprovalCard inside CloseoutModal (and potentially a future inbox view).
 *
 * Wire-up:
 *  - Hydration:    api.approvals.listPending() — backend GET /api/approvals
 *  - Realtime IN:  agentEventRoutes.js refreshes this store when a
 *                  `agent:status_changed` event arrives with
 *                  payload.user_approval_id (status=='awaiting_user') OR
 *                  payload.decided_option_id (resume).
 *  - Decide:       api.approvals.decide(id, optionId) — POST .../decide.
 *
 * Tenant isolation: backend filters every list response and every NOTIFY by
 * tenant_key. The store trusts the server; it never compares tenant_key
 * client-side.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useApprovalsStore = defineStore('approvals', () => {
  // State — keyed by approval_id, not job_id (one execution can only have one
  // pending approval at a time per service invariant, but keying on the
  // approval_id is safer for future N-pending support).
  const approvalsById = ref(new Map())
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const pendingApprovals = computed(() => Array.from(approvalsById.value.values()))

  const findByJobId = (jobId) => {
    if (!jobId) return null
    for (const row of approvalsById.value.values()) {
      if (row.job_id === jobId) return row
    }
    return null
  }

  // Actions
  async function fetchPending() {
    loading.value = true
    error.value = null
    try {
      const res = await api.approvals.listPending()
      const items = Array.isArray(res?.data?.items) ? res.data.items : []
      const next = new Map()
      for (const item of items) {
        if (item?.id) next.set(item.id, item)
      }
      approvalsById.value = next
      return items
    } catch (err) {
      error.value = err?.response?.data?.message || err?.message || 'Failed to load pending approvals'
      throw err
    } finally {
      loading.value = false
    }
  }

  function upsertApproval(row) {
    if (!row?.id) return
    const next = new Map(approvalsById.value)
    next.set(row.id, row)
    approvalsById.value = next
  }

  function removeApproval(approvalId) {
    if (!approvalId || !approvalsById.value.has(approvalId)) return
    const next = new Map(approvalsById.value)
    next.delete(approvalId)
    approvalsById.value = next
  }

  /**
   * Called from agentEventRoutes when agent:status_changed carries an
   * approval-related field. status==='awaiting_user' + user_approval_id =>
   * a new approval just landed; refresh from server (cheap, indexed query).
   * decided_option_id present => approval was decided; remove the row.
   */
  async function handleStatusEvent(payload) {
    if (!payload) return
    if (payload.decided_option_id && payload.user_approval_id) {
      removeApproval(payload.user_approval_id)
      return
    }
    if (payload.status === 'awaiting_user' && payload.user_approval_id) {
      // Refresh — server is the source of truth for the row contents.
      try {
        await fetchPending()
      } catch {
        // Swallow: error already surfaced via store.error
      }
    }
  }

  async function decide(approvalId, optionId) {
    if (!approvalId || !optionId) {
      throw new Error('approvalId and optionId are required')
    }
    const res = await api.approvals.decide(approvalId, optionId)
    // Intentionally do NOT removeApproval here. The server broadcasts a
    // resume event via WebSocket and handleStatusEvent clears the row a
    // beat later. Removing inside decide() makes any consumer using v-if
    // on the row (e.g. ApprovalCard inside DecisionModal) unmount before
    // its 'decided' emit can propagate to its parent — the message reaches
    // the parent's listener in the SAME synchronous tick, but the v-if
    // having already flipped to false in the parent can cause the parent
    // to also tear down its dialog before reacting. Leaving the row in
    // the store lets the parent handle the emit cleanly and trigger its
    // own state change first, then the WS event cleans up the store.
    return res?.data
  }

  function $reset() {
    approvalsById.value = new Map()
    loading.value = false
    error.value = null
  }

  return {
    // state
    approvalsById,
    loading,
    error,
    // getters
    pendingApprovals,
    findByJobId,
    // actions
    fetchPending,
    upsertApproval,
    removeApproval,
    handleStatusEvent,
    decide,
    $reset,
  }
})
