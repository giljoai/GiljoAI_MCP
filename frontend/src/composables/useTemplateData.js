/**
 * useTemplateData Composable
 *
 * Encapsulates template data fetching, active-agent stats, and filtering logic
 * for the TemplateManager component.
 *
 * Extracted from TemplateManager.vue (Handover 0950k).
 *
 * @param {import('vue').Ref<string>} search - Search text ref
 * @param {import('vue').Ref<string|null>} filterCategory - Category filter ref
 * @param {import('vue').Ref<string|null>} filterStatus - Status filter ref
 * @returns {Object} Template data state, computeds, and load methods
 */
import { ref, computed } from 'vue'
import api from '@/services/api'

const ORCHESTRATOR_ROW = Object.freeze({
  id: '__orchestrator__',
  name: 'orchestrator',
  role: 'orchestrator',
  is_active: true,
  export_status: null,
  last_exported_at: null,
  updated_at: null,
  may_be_stale: false,
  _system: true,
})

const DEFAULT_EDITING_TEMPLATE = () => ({
  id: null,
  name: '',
  role: '',
  cli_tool: 'claude',
  custom_suffix: '',
  background_color: '',
  description: '',
  user_instructions: '',
  model: 'sonnet',
  tools: null,
})

export function useTemplateData(search, filterCategory, filterStatus) {
  const templates = ref([])
  const loading = ref(false)
  const activeStats = ref({
    totalActive: null,
    totalCapacity: null,
    userActive: 0,
    userLimit: 7,
    remainingUserSlots: 7,
    systemReserved: 1,
  })
  const previewContent = ref('')

  const editingTemplate = ref(DEFAULT_EDITING_TEMPLATE())

  const orchestratorRow = ORCHESTRATOR_ROW

  const filteredTemplates = computed(() => {
    let filtered = templates.value

    if (filterCategory.value) {
      filtered = filtered.filter((t) => t.category === filterCategory.value)
    }

    if (filterStatus.value) {
      filtered = filtered.filter((t) => t.status === filterStatus.value)
    }

    if (!filterCategory.value && !filterStatus.value) {
      return [orchestratorRow, ...filtered]
    }
    return filtered
  })

  const generatedName = computed(() => {
    const role = editingTemplate.value.role
    const suffix = editingTemplate.value.custom_suffix
    if (!role) return ''
    if (!suffix) return role
    const cleanSuffix = suffix
      .toLowerCase()
      .replace(/[^a-z0-9-]/g, '')
      .replace(/\s+/g, '-')
    return `${role}-${cleanSuffix}`
  })

  const totalActiveAgents = computed(() => activeStats.value.totalActive)

  const totalCapacity = computed(() => {
    if (activeStats.value.totalCapacity !== null) {
      return activeStats.value.totalCapacity
    }
    return (activeStats.value.userLimit || 7) + (activeStats.value.systemReserved || 1)
  })

  const remainingUserSlots = computed(() => {
    if (typeof activeStats.value.remainingUserSlots === 'number') {
      return Math.max(0, activeStats.value.remainingUserSlots)
    }
    return Math.max(0, (activeStats.value.userLimit || 7) - (activeStats.value.userActive || 0))
  })

  const userAgentLimit = computed(() => activeStats.value.userLimit ?? 7)

  const loadTemplates = async () => {
    loading.value = true
    try {
      const response = await api.templates.list()
      templates.value = (response.data || []).filter((t) => !t.is_system_role)
    } catch (error) {
      console.error('Failed to load templates:', error)
    } finally {
      loading.value = false
    }
  }

  const loadActiveCount = async () => {
    try {
      const response = await api.templates.activeCount()
      const data = response.data || {}
      const userActive = data.active_count ?? 0
      const userLimit = data.limit ?? 7
      const systemReserved = 1
      activeStats.value = {
        totalActive: userActive + systemReserved,
        totalCapacity: userLimit + systemReserved,
        userActive,
        userLimit,
        remainingUserSlots: Math.max(0, userLimit - userActive),
        systemReserved,
      }
    } catch (error) {
      console.error('[TEMPLATE MANAGER] Failed to load active count:', error)
      activeStats.value = {
        ...activeStats.value,
        totalActive: activeStats.value.totalActive ?? activeStats.value.systemReserved,
      }
    }
  }

  const resetEditingTemplate = () => {
    editingTemplate.value = DEFAULT_EDITING_TEMPLATE()
  }

  return {
    templates,
    loading,
    activeStats,
    previewContent,
    editingTemplate,
    orchestratorRow,
    filteredTemplates,
    generatedName,
    totalActiveAgents,
    totalCapacity,
    remainingUserSlots,
    userAgentLimit,
    loadTemplates,
    loadActiveCount,
    resetEditingTemplate,
  }
}
