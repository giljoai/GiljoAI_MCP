import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises, config } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import ProjectsView from '@/views/ProjectsView.vue'
import { useProjectStore } from '@/stores/projects'
import { useProductStore } from '@/stores/products'
import { useAgentStore } from '@/stores/agents'

// Mock api service at module level (overrides global mock from setup.js)
vi.mock('@/services/api', () => ({
  default: {
    projectTypes: {
      list: vi.fn(() => Promise.resolve({ data: [] })),
    },
    projects: {
      checkSeries: vi.fn(() => Promise.resolve({ data: { available: true } })),
      usedSubseries: vi.fn(() => Promise.resolve({ data: { used_subseries: [] } })),
    },
    get: vi.fn(() => Promise.resolve({ data: {} })),
    post: vi.fn(() => Promise.resolve({ data: { success: true } })),
    put: vi.fn(() => Promise.resolve({ data: { success: true } })),
    delete: vi.fn(() => Promise.resolve({ data: { success: true } })),
  },
}))

describe('ProjectsView - Taxonomy Display (Handover 0440c)', () => {
  let router
  let projectStore
  let productStore
  let agentStore
  let savedPlugins

  const mockProduct = {
    id: 'prod-1',
    name: 'Test Product',
    is_active: true,
  }

  // Project WITH taxonomy data (series-assigned, Feature type)
  const taxonomyProject = {
    id: 'proj-tax-1',
    name: 'Taxonomy Feature Build',
    status: 'active',
    product_id: 'prod-1',
    mission: 'Build taxonomy system',
    description: 'Implement project taxonomy',
    agent_count: 2,
    created_at: '2026-02-10T00:00:00Z',
    updated_at: '2026-02-20T00:00:00Z',
    deleted_at: null,
    project_type_id: 'type-feat',
    series_number: 440,
    subseries: 'c',
    taxonomy_alias: 'FEAT-0440c',
    project_type: {
      id: 'type-feat',
      label: 'Feature',
      abbreviation: 'FEAT',
      color: '#4CAF50',
    },
  }

  // Project WITHOUT taxonomy data (legacy project)
  const legacyProject = {
    id: 'proj-legacy-1',
    name: 'Legacy Project',
    status: 'inactive',
    product_id: 'prod-1',
    mission: 'Some legacy work',
    description: 'No taxonomy assigned',
    agent_count: 1,
    created_at: '2026-01-15T00:00:00Z',
    updated_at: '2026-02-01T00:00:00Z',
    deleted_at: null,
    project_type_id: null,
    series_number: null,
    subseries: null,
    taxonomy_alias: null,
    project_type: null,
  }

  // Second taxonomy project (Bugfix type)
  const taxonomyProjectBugfix = {
    id: 'proj-tax-2',
    name: 'Fix Login Bug',
    status: 'inactive',
    product_id: 'prod-1',
    mission: 'Fix authentication bug',
    description: 'Debug login flow',
    agent_count: 1,
    created_at: '2026-02-12T00:00:00Z',
    updated_at: '2026-02-18T00:00:00Z',
    deleted_at: null,
    project_type_id: 'type-bug',
    series_number: 501,
    subseries: null,
    taxonomy_alias: 'BUG-0501',
    project_type: {
      id: 'type-bug',
      label: 'Bugfix',
      abbreviation: 'BUG',
      color: '#F44336',
    },
  }

  const mockProjectTypes = [
    {
      id: 'type-feat',
      label: 'Feature',
      abbreviation: 'FEAT',
      color: '#4CAF50',
    },
    {
      id: 'type-bug',
      label: 'Bugfix',
      abbreviation: 'BUG',
      color: '#F44336',
    },
  ]

  beforeEach(() => {
    // Replace the global pinia (from setup.js) with a fresh instance so that
    // the component's useXxxStore() calls resolve to our test stores.
    savedPlugins = [...config.global.plugins]
    const pinia = createPinia()
    setActivePinia(pinia)
    config.global.plugins = savedPlugins.map((p) => {
      if (p && typeof p === 'object' && ('_s' in p || '_a' in p)) return pinia
      return p
    })

    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/projects', component: ProjectsView },
        { path: '/projects/:id', component: { template: '<div>Detail</div>' } },
        { path: '/projects/:projectId/launch', name: 'ProjectLaunch', component: { template: '<div>Launch</div>' } },
      ],
    })

    projectStore = useProjectStore()
    productStore = useProductStore()
    agentStore = useAgentStore()

    // Mock store actions before patching state so that onMounted
    // does not reset patched state via real API calls.
    projectStore.fetchProjects = vi.fn().mockResolvedValue()
    projectStore.fetchDeletedProjects = vi.fn().mockResolvedValue()
    projectStore.createProject = vi.fn().mockResolvedValue(taxonomyProject)
    projectStore.updateProject = vi.fn().mockResolvedValue(taxonomyProject)
    projectStore.deleteProject = vi.fn().mockResolvedValue()
    projectStore.activateProject = vi.fn().mockResolvedValue()
    projectStore.pauseProject = vi.fn().mockResolvedValue()
    projectStore.completeProject = vi.fn().mockResolvedValue()
    projectStore.cancelProject = vi.fn().mockResolvedValue()
    projectStore.restoreProject = vi.fn().mockResolvedValue()

    productStore.fetchProducts = vi.fn().mockResolvedValue()
    productStore.fetchActiveProduct = vi.fn().mockResolvedValue()

    agentStore.fetchAgents = vi.fn().mockResolvedValue()

    // Set store state
    projectStore.$patch({
      projects: [taxonomyProject, legacyProject, taxonomyProjectBugfix],
      loading: false,
      error: null,
    })

    productStore.$patch({
      products: [mockProduct],
      activeProduct: mockProduct,
    })

    agentStore.$patch({
      agents: [],
      loading: false,
    })
  })

  afterEach(() => {
    config.global.plugins = savedPlugins
  })

  const createWrapper = async () => {
    const wrapper = mount(ProjectsView, {
      global: {
        plugins: [router],
        stubs: { teleport: true },
        directives: { draggable: () => {} },
      },
    })
    await flushPromises()
    return wrapper
  }

  // ----------------------------------------------------------------
  // 1. Taxonomy chip data in sorted project list
  //    The v-data-table stub does not render scoped slots, so we verify
  //    the data that feeds the template rather than rendered DOM text.
  //    The template renders a v-chip when item.taxonomy_alias && item.series_number.
  // ----------------------------------------------------------------
  describe('Taxonomy Chip Rendering', () => {
    it('provides taxonomy_alias and series_number for chip rendering (Feature)', async () => {
      const wrapper = await createWrapper()
      const featProject = wrapper.vm.sortedProjects.find((p) => p.id === 'proj-tax-1')

      expect(featProject).toBeTruthy()
      expect(featProject.taxonomy_alias).toBe('FEAT-0440c')
      expect(featProject.series_number).toBe(440)
      expect(featProject.project_type?.color).toBe('#4CAF50')
    })

    it('provides taxonomy_alias and series_number for chip rendering (Bugfix)', async () => {
      const wrapper = await createWrapper()
      const bugProject = wrapper.vm.sortedProjects.find((p) => p.id === 'proj-tax-2')

      expect(bugProject).toBeTruthy()
      expect(bugProject.taxonomy_alias).toBe('BUG-0501')
      expect(bugProject.series_number).toBe(501)
      expect(bugProject.project_type?.color).toBe('#F44336')
    })

    it('legacy project has no taxonomy_alias or series_number (no chip rendered)', async () => {
      projectStore.$patch({ projects: [legacyProject] })

      const wrapper = await createWrapper()
      const legacy = wrapper.vm.sortedProjects.find((p) => p.id === 'proj-legacy-1')

      expect(legacy).toBeTruthy()
      expect(legacy.name).toBe('Legacy Project')
      // These being falsy means the v-if="item.taxonomy_alias && item.series_number" is false
      expect(legacy.taxonomy_alias).toBeFalsy()
      expect(legacy.series_number).toBeFalsy()
    })

    it('mixed list contains both taxonomy and non-taxonomy projects', async () => {
      const wrapper = await createWrapper()
      const sorted = wrapper.vm.sortedProjects

      expect(sorted.length).toBe(3)

      const withTaxonomy = sorted.filter((p) => p.taxonomy_alias && p.series_number)
      const withoutTaxonomy = sorted.filter((p) => !p.taxonomy_alias || !p.series_number)

      expect(withTaxonomy.length).toBe(2)
      expect(withoutTaxonomy.length).toBe(1)
      expect(withoutTaxonomy[0].name).toBe('Legacy Project')
    })
  })

  // ----------------------------------------------------------------
  // 2. Type filter chip rendering
  // ----------------------------------------------------------------
  describe('Type Filter Chips Rendering', () => {
    it('renders filter button and collapsible pills when projectTypes populated', async () => {
      const wrapper = await createWrapper()

      wrapper.vm.projectTypes = mockProjectTypes
      await wrapper.vm.$nextTick()

      // Filter button is an icon button (mdi-filter-variant) with aria-label
      const filterBtn = wrapper.find('button[aria-label="Toggle filters"]')
      expect(filterBtn.exists()).toBe(true)

      // Expand the filter row
      wrapper.vm.showFilterRow = true
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('FEAT')
      expect(wrapper.text()).toContain('BUG')
    })

    it('does not render type filter section when projectTypes is empty', async () => {
      const wrapper = await createWrapper()

      // projectTypes defaults to empty array
      expect(wrapper.text()).not.toContain('Type:')
      expect(wrapper.text()).not.toContain('No Type')
    })

    it('shows all expected type filter labels including All and No Type', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.projectTypes = mockProjectTypes
      wrapper.vm.showFilterRow = true
      await wrapper.vm.$nextTick()

      const text = wrapper.text()
      expect(text).toContain('All')
      expect(text).toContain('FEAT')
      expect(text).toContain('BUG')
      expect(text).toContain('No Type')
    })
  })

  // ----------------------------------------------------------------
  // 3. filteredBySearch computed -- type filter logic
  // ----------------------------------------------------------------
  describe('filteredBySearch - Type Filtering', () => {
    it('returns all projects when filterType is "all"', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.filterType = 'all'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredBySearch.length).toBe(3)
    })

    it('filters to only Feature projects when filterType is set to type-feat', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.filterType = 'type-feat'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredBySearch.length).toBe(1)
      expect(wrapper.vm.filteredBySearch[0].id).toBe('proj-tax-1')
      expect(wrapper.vm.filteredBySearch[0].project_type_id).toBe('type-feat')
    })

    it('filters to only Bugfix projects when filterType is set to type-bug', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.filterType = 'type-bug'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredBySearch.length).toBe(1)
      expect(wrapper.vm.filteredBySearch[0].id).toBe('proj-tax-2')
      expect(wrapper.vm.filteredBySearch[0].project_type_id).toBe('type-bug')
    })

    it('filters to projects with no type when filterType is "none"', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.filterType = 'none'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredBySearch.length).toBe(1)
      expect(wrapper.vm.filteredBySearch[0].id).toBe('proj-legacy-1')
      expect(wrapper.vm.filteredBySearch[0].project_type_id).toBeNull()
    })

    it('combines text search with type filter', async () => {
      const wrapper = await createWrapper()

      // Filter to Feature type only
      wrapper.vm.filterType = 'type-feat'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.filteredBySearch.length).toBe(1)

      // Add text search that does NOT match the Feature project
      wrapper.vm.searchQuery = 'Login'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.filteredBySearch.length).toBe(0)
    })

    it('searches by taxonomy_alias text', async () => {
      const wrapper = await createWrapper()

      wrapper.vm.searchQuery = 'FEAT-0440'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredBySearch.length).toBe(1)
      expect(wrapper.vm.filteredBySearch[0].taxonomy_alias).toBe('FEAT-0440c')
    })

    it('taxonomy_alias search is case insensitive', async () => {
      const wrapper = await createWrapper()

      wrapper.vm.searchQuery = 'feat-0440'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredBySearch.length).toBe(1)
      expect(wrapper.vm.filteredBySearch[0].id).toBe('proj-tax-1')
    })
  })

  // ----------------------------------------------------------------
  // 4. Series-aware sorting
  // ----------------------------------------------------------------
  describe('Series-Aware Sorting', () => {
    it('sorts by type abbreviation when sorting by name ascending', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.sortConfig = [{ key: 'name', order: 'asc' }]
      await wrapper.vm.$nextTick()

      const sorted = wrapper.vm.sortedProjects
      // Active project comes first (active-first rule), then inactive sorted by type
      const inactiveProjects = sorted.filter((p) => p.status === 'inactive')
      expect(inactiveProjects.length).toBe(2)

      // BUG (abbreviation B) should appear before legacy (no type = 'ZZZ')
      const bugIdx = inactiveProjects.findIndex((p) => p.id === 'proj-tax-2')
      const legacyIdx = inactiveProjects.findIndex((p) => p.id === 'proj-legacy-1')
      expect(bugIdx).toBeLessThan(legacyIdx)
    })

    it('places active projects first regardless of sort configuration', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.sortConfig = [{ key: 'name', order: 'asc' }]
      await wrapper.vm.$nextTick()

      const sorted = wrapper.vm.sortedProjects
      expect(sorted.length).toBeGreaterThan(0)
      expect(sorted[0].status).toBe('active')
      expect(sorted[0].id).toBe('proj-tax-1')
    })

    it('sorts by series_number within same type abbreviation', async () => {
      // Add a second Feature project with lower series_number
      const secondFeature = {
        ...taxonomyProject,
        id: 'proj-tax-3',
        name: 'Another Feature',
        status: 'inactive',
        series_number: 100,
        taxonomy_alias: 'FEAT-0100',
      }

      // Make both Feature projects inactive so active-first rule does not interfere
      const inactiveTaxonomy = { ...taxonomyProject, status: 'inactive' }

      projectStore.$patch({
        projects: [inactiveTaxonomy, secondFeature, legacyProject, taxonomyProjectBugfix],
      })

      const wrapper = await createWrapper()
      wrapper.vm.sortConfig = [{ key: 'name', order: 'asc' }]
      await wrapper.vm.$nextTick()

      const sorted = wrapper.vm.sortedProjects
      const featProjects = sorted.filter((p) => p.project_type?.abbreviation === 'FEAT')

      expect(featProjects.length).toBe(2)
      expect(featProjects[0].series_number).toBe(100)
      expect(featProjects[1].series_number).toBe(440)
    })
  })

  // ----------------------------------------------------------------
  // 5. Taxonomy fields in form / edit dialog
  // ----------------------------------------------------------------
  describe('Taxonomy in Form / Edit Dialog', () => {
    it('includes taxonomy fields in resetForm', async () => {
      const wrapper = await createWrapper()

      wrapper.vm.projectData.project_type_id = 'type-feat'
      wrapper.vm.projectData.series_number = 440
      wrapper.vm.projectData.subseries = 'c'

      wrapper.vm.resetForm()

      expect(wrapper.vm.projectData.project_type_id).toBeNull()
      expect(wrapper.vm.projectData.series_number).toBeNull()
      expect(wrapper.vm.projectData.subseries).toBeNull()
    })

    it('populates taxonomy fields when editing a taxonomy project', async () => {
      const wrapper = await createWrapper()

      wrapper.vm.editProject(taxonomyProject)

      expect(wrapper.vm.projectData.project_type_id).toBe('type-feat')
      expect(wrapper.vm.projectData.series_number).toBe(440)
      expect(wrapper.vm.projectData.subseries).toBe('c')
    })

    it('populates null taxonomy fields when editing a legacy project', async () => {
      const wrapper = await createWrapper()

      wrapper.vm.editProject(legacyProject)

      expect(wrapper.vm.projectData.project_type_id).toBeNull()
      expect(wrapper.vm.projectData.series_number).toBeNull()
      expect(wrapper.vm.projectData.subseries).toBeNull()
    })

    it('sends taxonomy fields when saving a project update', async () => {
      const wrapper = await createWrapper()

      wrapper.vm.editingProject = taxonomyProject
      wrapper.vm.projectData = {
        name: 'Updated Taxonomy Project',
        description: 'Updated description',
        mission: 'Updated mission',
        status: 'active',
        project_type_id: 'type-bug',
        series_number: 600,
        subseries: 'a',
      }
      wrapper.vm.formValid = true
      await wrapper.vm.$nextTick()

      await wrapper.vm.saveProject()
      await flushPromises()

      expect(projectStore.updateProject).toHaveBeenCalledWith(
        'proj-tax-1',
        expect.objectContaining({
          project_type_id: 'type-bug',
          series_number: 600,
          subseries: 'a',
        }),
      )
    })

    it('includes taxonomy fields when creating a new project', async () => {
      const wrapper = await createWrapper()

      wrapper.vm.projectData = {
        name: 'New Taxonomy Project',
        description: 'A new project with taxonomy',
        mission: '',
        status: 'inactive',
        project_type_id: 'type-feat',
        series_number: 900,
        subseries: 'b',
      }
      wrapper.vm.formValid = true
      await wrapper.vm.$nextTick()

      await wrapper.vm.saveProject()
      await flushPromises()

      expect(projectStore.createProject).toHaveBeenCalledWith(
        expect.objectContaining({
          project_type_id: 'type-feat',
          series_number: 900,
          subseries: 'b',
          product_id: 'prod-1',
        }),
      )
    })
  })

  // ----------------------------------------------------------------
  // 6. Inline Taxonomy Row (Handover 0440c)
  // ----------------------------------------------------------------
  describe('Inline Taxonomy Row', () => {
    it('typeDropdownItems includes project types plus "Add custom type..." option', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.projectTypes = mockProjectTypes
      await wrapper.vm.$nextTick()

      const items = wrapper.vm.typeDropdownItems
      expect(items.length).toBe(3) // 2 types + 1 "Add custom type..."
      expect(items[0].display).toContain('Feature')
      expect(items[1].display).toContain('Bugfix')
      expect(items[2].id).toBe('__add_custom__')
    })

    it('typeDropdownItems is empty when no project types loaded', async () => {
      const wrapper = await createWrapper()
      const items = wrapper.vm.typeDropdownItems
      expect(items.length).toBe(1)
      expect(items[0].id).toBe('__add_custom__')
    })

    it('subseriesItems contains a-z letters when none are used', async () => {
      const wrapper = await createWrapper()
      const items = wrapper.vm.subseriesItems
      expect(items.length).toBe(26)
      expect(items[0]).toEqual({ title: 'a', value: 'a' })
      expect(items[25]).toEqual({ title: 'z', value: 'z' })
    })

    it('subseriesItems excludes used letters', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.usedSubseries = ['a', 'c', 'f']
      await wrapper.vm.$nextTick()

      const items = wrapper.vm.subseriesItems
      expect(items.length).toBe(23) // 26 - 3 used
      expect(items.find((i) => i.value === 'a')).toBeUndefined()
      expect(items.find((i) => i.value === 'c')).toBeUndefined()
      expect(items.find((i) => i.value === 'f')).toBeUndefined()
      expect(items.find((i) => i.value === 'b')).toBeTruthy()
      expect(items.find((i) => i.value === 'd')).toBeTruthy()
    })

    it('seriesNumberInput is populated when editing a taxonomy project', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.editProject(taxonomyProject)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.seriesNumberInput).toBe('0440')
      expect(wrapper.vm.seriesCheckResult).toBe(true)
      expect(wrapper.vm.seriesCheckMessage).toBe('Current value')
    })

    it('seriesNumberInput is empty when editing a legacy project', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.editProject(legacyProject)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.seriesNumberInput).toBe('')
      expect(wrapper.vm.seriesCheckResult).toBeNull()
    })

    it('resetForm clears inline taxonomy state including usedSubseries', async () => {
      const wrapper = await createWrapper()

      wrapper.vm.seriesNumberInput = '0500'
      wrapper.vm.seriesCheckResult = true
      wrapper.vm.seriesCheckMessage = 'Available'
      wrapper.vm.usedSubseries = ['a', 'b']

      wrapper.vm.resetForm()

      expect(wrapper.vm.seriesNumberInput).toBe('')
      expect(wrapper.vm.seriesCheckResult).toBeNull()
      expect(wrapper.vm.seriesCheckMessage).toBe('')
      expect(wrapper.vm.usedSubseries).toEqual([])
    })
  })

  // ----------------------------------------------------------------
  // 7. Handover 0440d: handleTypeChange resets taxonomy state
  // ----------------------------------------------------------------
  describe('Handover 0440d: handleTypeChange resets taxonomy state', () => {
    it('handleTypeChange preserves serial/subseries and re-validates', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.projectTypes = mockProjectTypes

      // Pre-populate taxonomy state as if user had previously selected a type and serial
      wrapper.vm.projectData.project_type_id = 'type-feat'
      wrapper.vm.projectData.series_number = 440
      wrapper.vm.projectData.subseries = 'c'
      wrapper.vm.seriesNumberInput = '0440'
      wrapper.vm.seriesCheckResult = true
      wrapper.vm.seriesCheckMessage = '0440 available'
      wrapper.vm.usedSubseries = ['a', 'b']
      await wrapper.vm.$nextTick()

      // Change to a different type — serial/subseries preserved, validation reset
      wrapper.vm.handleTypeChange('type-bug')

      expect(wrapper.vm.projectData.series_number).toBe(440)
      expect(wrapper.vm.projectData.subseries).toBe('c')
      expect(wrapper.vm.seriesNumberInput).toBe('0440')
      expect(wrapper.vm.seriesCheckResult).toBeNull()
      expect(wrapper.vm.seriesCheckMessage).toBe('')
      expect(wrapper.vm.usedSubseries).toEqual([])
      expect(wrapper.vm.seriesChecking).toBe(true) // re-validation triggered
    })

    it('handleTypeChange with __add_custom__ opens modal and clears type', async () => {
      const wrapper = await createWrapper()

      wrapper.vm.projectData.project_type_id = 'type-feat'
      await wrapper.vm.$nextTick()

      wrapper.vm.handleTypeChange('__add_custom__')

      expect(wrapper.vm.showAddTypeModal).toBe(true)
      expect(wrapper.vm.projectData.project_type_id).toBeNull()
    })
  })

  // ----------------------------------------------------------------
  // 8. Handover 0440d: onSubseriesChange triggers re-validation
  // ----------------------------------------------------------------
  describe('Handover 0440d: onSubseriesChange triggers re-validation', () => {
    it('onSubseriesChange triggers re-check when type and serial are set', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.projectTypes = mockProjectTypes

      // Set up state so both type and series_number are present
      wrapper.vm.projectData.project_type_id = 'type-feat'
      wrapper.vm.projectData.series_number = 440
      await wrapper.vm.$nextTick()

      // Call onSubseriesChange -- it synchronously sets seriesChecking = true
      wrapper.vm.onSubseriesChange()

      expect(wrapper.vm.seriesChecking).toBe(true)
    })

    it('onSubseriesChange triggers re-check even without type (serial-only)', async () => {
      const wrapper = await createWrapper()

      // No type set, only series_number — still triggers validation
      wrapper.vm.projectData.project_type_id = null
      wrapper.vm.projectData.series_number = 440
      wrapper.vm.seriesChecking = false
      await wrapper.vm.$nextTick()

      wrapper.vm.onSubseriesChange()

      expect(wrapper.vm.seriesChecking).toBe(true)
    })

    it('onSubseriesChange does nothing when no series_number is set', async () => {
      const wrapper = await createWrapper()

      // Type set but no series_number
      wrapper.vm.projectData.project_type_id = 'type-feat'
      wrapper.vm.projectData.series_number = null
      wrapper.vm.seriesChecking = false
      await wrapper.vm.$nextTick()

      wrapper.vm.onSubseriesChange()

      expect(wrapper.vm.seriesChecking).toBe(false)
    })
  })

  // ----------------------------------------------------------------
  // 9. Handover 0440d: Unmount cleanup
  // ----------------------------------------------------------------
  describe('Handover 0440d: Unmount cleanup', () => {
    it('unmount clears seriesCheckTimer', async () => {
      const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout')

      const wrapper = await createWrapper()
      wrapper.vm.projectTypes = mockProjectTypes

      // Trigger onSeriesInput to set up a timer (300ms debounce)
      wrapper.vm.projectData.project_type_id = 'type-feat'
      await wrapper.vm.$nextTick()
      wrapper.vm.onSeriesInput('0500')
      await wrapper.vm.$nextTick()

      // Unmount should invoke clearTimeout for the pending timer
      wrapper.unmount()

      expect(clearTimeoutSpy).toHaveBeenCalled()
      clearTimeoutSpy.mockRestore()
    })
  })

})
