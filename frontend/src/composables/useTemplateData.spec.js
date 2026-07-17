import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { useTemplateData } from './useTemplateData'

vi.mock('@/services/api', () => {
  const apiObj = {
    templates: {
      list: vi.fn(() =>
        Promise.resolve({
          // FE-9203: fixtures mirror the real TemplateResponse shape — there is
          // NO `status` field on the wire (only is_active). The old fixtures
          // invented one, so the filter tests exercised the mock, not the API.
          data: [
            { id: 1, name: 'analyzer', role: 'analyzer', is_active: true, is_system_role: false, category: 'role' },
            { id: 2, name: 'tester', role: 'tester', is_active: false, is_system_role: false, category: 'role' },
            { id: 3, name: 'sys-template', role: 'system', is_active: true, is_system_role: true, category: 'role' },
          ],
        })
      ),
      activeCount: vi.fn(() =>
        Promise.resolve({
          data: { active_count: 2, limit: 15, available: 13 },
        })
      ),
    },
  }
  return { api: apiObj, default: apiObj }
})

describe('useTemplateData', () => {
  let search, filterRole, filterStatus

  beforeEach(() => {
    vi.clearAllMocks()
    search = ref('')
    filterRole = ref(null)
    filterStatus = ref(null)
  })

  it('initializes with empty templates and loading false', () => {
    const { templates, loading } = useTemplateData(search, filterRole, filterStatus)
    expect(templates.value).toEqual([])
    expect(loading.value).toBe(false)
  })

  it('initializes activeStats with null totalActive', () => {
    const { activeStats } = useTemplateData(search, filterRole, filterStatus)
    expect(activeStats.value.totalActive).toBeNull()
  })

  it('initializes previewContent as empty string', () => {
    const { previewContent } = useTemplateData(search, filterRole, filterStatus)
    expect(previewContent.value).toBe('')
  })

  it('loadTemplates fetches and filters out system roles', async () => {
    const { templates, loadTemplates } = useTemplateData(search, filterRole, filterStatus)
    await loadTemplates()
    // is_system_role = true entry should be filtered out
    expect(templates.value).toHaveLength(2)
    expect(templates.value.every((t) => !t.is_system_role)).toBe(true)
  })

  it('loadActiveCount populates activeStats', async () => {
    const { activeStats, loadActiveCount } = useTemplateData(search, filterRole, filterStatus)
    await loadActiveCount()
    expect(activeStats.value.userActive).toBe(2)
    expect(activeStats.value.userLimit).toBe(15)
    expect(activeStats.value.totalActive).toBe(3) // 2 user + 1 system reserved
  })

  it('filteredTemplates includes orchestratorRow when no filters active', async () => {
    const { filteredTemplates, loadTemplates } = useTemplateData(search, filterRole, filterStatus)
    await loadTemplates()
    const names = filteredTemplates.value.map((t) => t.name)
    expect(names[0]).toBe('orchestrator')
  })

  it('filteredTemplates excludes orchestratorRow when role filter is active', async () => {
    const { filteredTemplates, loadTemplates } = useTemplateData(search, filterRole, filterStatus)
    await loadTemplates()
    filterRole.value = 'analyzer'
    const names = filteredTemplates.value.map((t) => t.name)
    expect(names).not.toContain('orchestrator')
  })

  it('filteredTemplates filters by status (is_active on the model)', async () => {
    const { filteredTemplates, loadTemplates } = useTemplateData(search, filterRole, filterStatus)
    await loadTemplates()
    filterStatus.value = 'inactive'
    expect(filteredTemplates.value).toHaveLength(1)
    expect(filteredTemplates.value[0].name).toBe('tester')
  })

  it('generatedName combines role and suffix', () => {
    const { generatedName, editingTemplate } = useTemplateData(search, filterRole, filterStatus)
    editingTemplate.value.role = 'implementer'
    editingTemplate.value.custom_suffix = 'fastapi'
    expect(generatedName.value).toBe('implementer-fastapi')
  })

  it('generatedName returns just role when no suffix', () => {
    const { generatedName, editingTemplate } = useTemplateData(search, filterRole, filterStatus)
    editingTemplate.value.role = 'reviewer'
    editingTemplate.value.custom_suffix = ''
    expect(generatedName.value).toBe('reviewer')
  })

  it('totalActiveAgents mirrors activeStats.totalActive', async () => {
    const { totalActiveAgents, loadActiveCount } = useTemplateData(search, filterRole, filterStatus)
    await loadActiveCount()
    expect(totalActiveAgents.value).toBe(3)
  })

  it('remainingUserSlots is computed from activeStats', async () => {
    const { remainingUserSlots, loadActiveCount } = useTemplateData(search, filterRole, filterStatus)
    await loadActiveCount()
    // limit 15 - active 2 = 13
    expect(remainingUserSlots.value).toBe(13)
  })

  it('userAgentLimit defaults to 15', () => {
    const { userAgentLimit } = useTemplateData(search, filterRole, filterStatus)
    expect(userAgentLimit.value).toBe(15)
  })
})
