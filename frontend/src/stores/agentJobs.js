/**
 * agentJobs store
 * Pinia store for agent job table state (filters, sorting, selection).
 * State-only: WebSocket handling remains in components/composables.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

const STATUS_PRIORITY = {
  failed: 0,
  blocked: 1,
  working: 2,
  review: 3,
  preparing: 4,
  waiting: 5,
  complete: 6,
  cancelled: 7,
  decommissioned: 8,
}

export const useAgentJobsStore = defineStore('agentJobs', () => {
  const agents = ref([])
  const selectedAgentId = ref(null)

  const tableFilters = ref({
    status: [],
    health_status: [],
    agent_display_name: [],
    has_unread: null,
  })

  const tableSortBy = ref('last_progress_at')
  const tableSortOrder = ref('desc')
  const tableLimit = ref(50)
  const tableOffset = ref(0)
  const tableTotal = ref(0)
  const loading = ref(false)
  const error = ref(null)

  const filteredAgents = computed(() => {
    let filtered = [...agents.value]

    if (tableFilters.value.status.length) {
      filtered = filtered.filter((a) => tableFilters.value.status.includes(a.status))
    }

    if (tableFilters.value.health_status.length) {
      filtered = filtered.filter((a) =>
        tableFilters.value.health_status.includes(a.health_status),
      )
    }

    if (tableFilters.value.agent_display_name.length) {
      filtered = filtered.filter((a) =>
        tableFilters.value.agent_display_name.includes(a.agent_display_name),
      )
    }

    if (tableFilters.value.has_unread !== null) {
      filtered = filtered.filter((a) => {
        const unread = a.unread_count ?? a.messages_waiting_count ?? 0
        return tableFilters.value.has_unread ? unread > 0 : unread === 0
      })
    }

    return filtered
  })

  const sortedAgents = computed(() => {
    const sorted = [...filteredAgents.value]
    const sortKey = tableSortBy.value
    const order = tableSortOrder.value === 'asc' ? 1 : -1

    sorted.sort((a, b) => {
      if (sortKey === 'status') {
        const priA = STATUS_PRIORITY[a.status] ?? 999
        const priB = STATUS_PRIORITY[b.status] ?? 999
        return (priA - priB) * order
      }

      let aVal = a[sortKey]
      let bVal = b[sortKey]

      if (aVal === bVal) return 0
      if (aVal == null) return 1
      if (bVal == null) return -1

      // Date/ISO strings should sort consistently
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return aVal > bVal ? order : -order
      }

      return aVal > bVal ? order : -order
    })

    return sorted
  })

  const statusCounts = computed(() => {
    const counts = {}
    agents.value.forEach((a) => {
      counts[a.status] = (counts[a.status] || 0) + 1
    })
    return counts
  })

  const warningCount = computed(() =>
    agents.value.filter((a) =>
      ['warning', 'critical', 'timeout'].includes(a.health_status),
    ).length,
  )

  const setAgents = (rows = []) => {
    agents.value = Array.isArray(rows) ? [...rows] : []
  }

  const setFromTableResponse = (payload) => {
    setAgents(payload?.rows || [])
    tableTotal.value = payload?.total ?? payload?.rows?.length ?? 0
    tableLimit.value = payload?.limit ?? tableLimit.value
    tableOffset.value = payload?.offset ?? 0
  }

  const selectAgent = (jobId) => {
    selectedAgentId.value = jobId
  }

  const updateAgent = (updates) => {
    if (!updates?.job_id) return
    const idx = agents.value.findIndex((a) => a.job_id === updates.job_id)
    if (idx !== -1) {
      agents.value[idx] = { ...agents.value[idx], ...updates }
    } else {
      agents.value.unshift(updates)
    }
  }

  const removeAgent = (jobId) => {
    agents.value = agents.value.filter((a) => a.job_id !== jobId)
    if (selectedAgentId.value === jobId) {
      selectedAgentId.value = null
    }
  }

  const clearFilters = () => {
    tableFilters.value = {
      status: [],
      health_status: [],
      agent_display_name: [],
      has_unread: null,
    }
  }

  const setSorting = (key, order = 'asc') => {
    tableSortBy.value = key
    tableSortOrder.value = order
  }

  const loadAgents = async (projectId, params = {}) => {
    loading.value = true
    error.value = null
    try {
      const response = await api.agentJobs.list(projectId, params)
      const payload = response?.data || {}
      setFromTableResponse(payload)
      return payload
    } catch (err) {
      error.value = err?.message || 'Failed to load agents'
      throw err
    } finally {
      loading.value = false
    }
  }

  const $reset = () => {
    agents.value = []
    selectedAgentId.value = null
    clearFilters()
    tableSortBy.value = 'last_progress_at'
    tableSortOrder.value = 'desc'
    tableLimit.value = 50
    tableOffset.value = 0
    tableTotal.value = 0
    loading.value = false
    error.value = null
  }

  return {
    // state
    agents,
    selectedAgentId,
    tableFilters,
    tableSortBy,
    tableSortOrder,
    tableLimit,
    tableOffset,
    tableTotal,
    loading,
    error,

    // getters
    filteredAgents,
    sortedAgents,
    statusCounts,
    warningCount,

    // actions
    setAgents,
    setFromTableResponse,
    selectAgent,
    updateAgent,
    removeAgent,
    clearFilters,
    setSorting,
    loadAgents,
    $reset,
  }
})
