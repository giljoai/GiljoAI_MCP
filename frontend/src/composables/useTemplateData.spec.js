import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { useTemplateData } from './useTemplateData'

vi.mock('@/services/api', () => {
  const apiObj = {
    templates: {
      list: vi.fn(() =>
        Promise.resolve({
          data: [
            { id: 1, name: 'analyzer', role: 'analyzer', is_active: true, is_system_role: false, status: 'active', category: 'role' },
            { id: 2, name: 'tester', role: 'tester', is_active: false, is_system_role: false, status: 'draft', category: 'role' },
            { id: 3, name: 'sys-template', role: 'system', is_active: true, is_system_role: true, status: 'active', category: 'role' },
          ],
        })
      ),
      activeCount: vi.fn(() =>
        Promise.resolve({
          data: { active_count: 2, limit: 7, available: 5 },
        })
      ),
    },
  }
  return { api: apiObj, default: apiObj }
})

describe('useTemplateData', () => {
  let search, filterCategory, filterStatus

  beforeEach(() => {
    vi.clearAllMocks()
    search = ref('')
    filterCategory = ref(null)
    filterStatus = ref(null)
  })

  it('initializes with empty templates and loading false', () => {
    const { templates, loading } = useTemplateData(search, filterCategory, filterStatus)
    expect(templates.value).toEqual([])
    expect(loading.value).toBe(false)
  })

  it('initializes activeStats with null totalActive', () => {
    const { activeStats } = useTemplateData(search, filterCategory, filterStatus)
    expect(activeStats.value.totalActive).toBeNull()
  })

  it('initializes previewContent as empty string', () => {
    const { previewContent } = useTemplateData(search, filterCategory, filterStatus)
    expect(previewContent.value).toBe('')
  })

  it('loadTemplates fetches and filters out system roles', async () => {
    const { templates, loadTemplates } = useTemplateData(search, filterCategory, filterStatus)
    await loadTemplates()
    // is_system_role = true entry should be filtered out
    expect(templates.value).toHaveLength(2)
    expect(templates.value.every((t) => !t.is_system_role)).toBe(true)
  })

  it('loadActiveCount populates activeStats', async () => {
    const { activeStats, loadActiveCount } = useTemplateData(search, filterCategory, filterStatus)
    await loadActiveCount()
    expect(activeStats.value.userActive).toBe(2)
    expect(activeStats.value.userLimit).toBe(7)
    expect(activeStats.value.totalActive).toBe(3) // 2 user + 1 system reserved
  })

  it('filteredTemplates includes orchestratorRow when no filters active', async () => {
    const { filteredTemplates, loadTemplates } = useTemplateData(search, filterCategory, filterStatus)
    await loadTemplates()
    const names = filteredTemplates.value.map((t) => t.name)
    expect(names[0]).toBe('orchestrator')
  })

  it('filteredTemplates excludes orchestratorRow when category filter is active', async () => {
    const { filteredTemplates, loadTemplates } = useTemplateData(search, filterCategory, filterStatus)
    await loadTemplates()
    filterCategory.value = 'role'
    const names = filteredTemplates.value.map((t) => t.name)
    expect(names).not.toContain('orchestrator')
  })

  it('filteredTemplates filters by status', async () => {
    const { filteredTemplates, loadTemplates } = useTemplateData(search, filterCategory, filterStatus)
    await loadTemplates()
    filterStatus.value = 'draft'
    expect(filteredTemplates.value).toHaveLength(1)
    expect(filteredTemplates.value[0].name).toBe('tester')
  })

  it('generatedName combines role and suffix', () => {
    const { generatedName, editingTemplate } = useTemplateData(search, filterCategory, filterStatus)
    editingTemplate.value.role = 'implementer'
    editingTemplate.value.custom_suffix = 'fastapi'
    expect(generatedName.value).toBe('implementer-fastapi')
  })

  it('generatedName returns just role when no suffix', () => {
    const { generatedName, editingTemplate } = useTemplateData(search, filterCategory, filterStatus)
    editingTemplate.value.role = 'reviewer'
    editingTemplate.value.custom_suffix = ''
    expect(generatedName.value).toBe('reviewer')
  })

  it('totalActiveAgents mirrors activeStats.totalActive', async () => {
    const { totalActiveAgents, loadActiveCount } = useTemplateData(search, filterCategory, filterStatus)
    await loadActiveCount()
    expect(totalActiveAgents.value).toBe(3)
  })

  it('remainingUserSlots is computed from activeStats', async () => {
    const { remainingUserSlots, loadActiveCount } = useTemplateData(search, filterCategory, filterStatus)
    await loadActiveCount()
    // limit 7 - active 2 = 5
    expect(remainingUserSlots.value).toBe(5)
  })

  it('userAgentLimit defaults to 7', () => {
    const { userAgentLimit } = useTemplateData(search, filterCategory, filterStatus)
    expect(userAgentLimit.value).toBe(7)
  })
})
