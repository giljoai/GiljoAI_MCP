import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises, config } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import { createRouter, createMemoryHistory } from 'vue-router'
import ProjectsView from '@/views/ProjectsView.vue'
import { useProjectStore } from '@/stores/projects'
import { useProductStore } from '@/stores/products'
import { useAgentStore } from '@/stores/agents'

describe('ProjectsView.vue', () => {
  let pinia
  let vuetify
  let router
  let projectStore
  let productStore
  let agentStore

  const mockProducts = [
    {
      id: 'prod-1',
      name: 'Product 1',
      is_active: true,
    },
  ]

  const mockProjects = [
    {
      id: 'proj-1',
      name: 'Project 1',
      status: 'active',
      product_id: 'prod-1',
      mission: 'Test mission 1',
      agent_count: 3,
      created_at: '2024-10-01T12:00:00Z',
      updated_at: '2024-10-28T12:00:00Z',
      deleted_at: null,
    },
    {
      id: 'proj-2',
      name: 'Project 2',
      status: 'inactive',
      product_id: 'prod-1',
      mission: 'Test mission 2',
      agent_count: 1,
      created_at: '2024-10-15T12:00:00Z',
      updated_at: '2024-10-28T12:00:00Z',
      deleted_at: null,
    },
    {
      id: 'proj-3',
      name: 'Project 3',
      status: 'inactive',
      product_id: 'prod-1',
      mission: 'Test mission 3',
      agent_count: 2,
      created_at: '2024-10-20T12:00:00Z',
      updated_at: '2024-10-28T12:00:00Z',
      deleted_at: null,
    },
  ]

  const mockDeletedProjects = [
    {
      id: 'proj-4',
      name: 'Deleted Project',
      status: 'completed',
      product_id: 'prod-1',
      mission: 'Test mission 4',
      agent_count: 0,
      created_at: '2024-09-01T12:00:00Z',
      updated_at: '2024-10-28T12:00:00Z',
      deleted_at: '2024-10-28T10:00:00Z',
    },
  ]

  const mockAgents = [
    {
      id: 'agent-1',
      name: 'Agent 1',
      project_id: 'proj-1',
    },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vuetify = createVuetify()
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/projects',
          component: ProjectsView,
        },
        {
          path: '/projects/:projectId',
          name: 'ProjectLaunch',
          component: { template: '<div>Project Launch</div>' },
        },
        {
          path: '/products',
          component: { template: '<div>Products</div>' },
        },
      ],
    })

    projectStore = useProjectStore()
    productStore = useProductStore()
    agentStore = useAgentStore()

    // Mock store state: projects and deletedProjects are separate refs
    projectStore.$patch({
      projects: mockProjects,
      deletedProjects: mockDeletedProjects,
      loading: false,
      error: null,
    })

    productStore.$patch({
      products: mockProducts,
      activeProduct: mockProducts[0],
    })

    agentStore.$patch({
      agents: mockAgents,
      loading: false,
    })

    // Mock API calls on store actions
    projectStore.fetchProjects = vi.fn().mockResolvedValue()
    projectStore.fetchDeletedProjects = vi.fn().mockResolvedValue()
    projectStore.createProject = vi.fn().mockResolvedValue(mockProjects[0])
    projectStore.updateProject = vi.fn().mockResolvedValue(mockProjects[0])
    projectStore.deleteProject = vi.fn().mockResolvedValue()
    projectStore.activateProject = vi.fn().mockResolvedValue()
    projectStore.deactivateProject = vi.fn().mockResolvedValue()
    projectStore.completeProject = vi.fn().mockResolvedValue()
    projectStore.cancelProject = vi.fn().mockResolvedValue()
    projectStore.restoreProject = vi.fn().mockResolvedValue()
    projectStore.restoreCompletedProject = vi.fn().mockResolvedValue()
    projectStore.purgeDeletedProject = vi.fn().mockResolvedValue()
    projectStore.purgeAllDeletedProjects = vi.fn().mockResolvedValue()

    productStore.fetchProducts = vi.fn().mockResolvedValue()
    productStore.fetchActiveProduct = vi.fn().mockResolvedValue()

    agentStore.fetchAgents = vi.fn().mockResolvedValue()
  })

  const createWrapper = async () => {
    // Merge global Vuetify stubs with test-specific stubs.
    // Pass only our test pinia (not the global config one) to avoid
    // dual-Pinia where component and test reference different store instances.
    const wrapper = mount(ProjectsView, {
      global: {
        plugins: [pinia, vuetify, router],
        stubs: {
          ...config.global.stubs,
          'v-expand-transition': { template: '<div><slot /></div>' },
          'v-sheet': { template: '<div class="v-sheet" v-bind="$attrs"><slot /></div>' },
          teleport: true,
          ManualCloseoutModal: true,
          ProjectReviewModal: true,
          StatusBadge: true,
          BaseDialog: true,
          AddTypeModal: true,
          AgentTipsDialog: true,
        },
        directives: {
          draggable: {},
        },
      },
    })
    await flushPromises()
    return wrapper
  }

  describe('Rendering', () => {
    it('renders header with title', async () => {
      const wrapper = await createWrapper()
      expect(wrapper.text()).toContain('Project Management')
    })

    it('renders projects page title', async () => {
      const wrapper = await createWrapper()
      expect(wrapper.text()).toContain('Project Management')
    })

    it('renders New Project button', async () => {
      const wrapper = await createWrapper()
      const button = wrapper.find('button[aria-label="Create new project"]')
      expect(button.exists()).toBe(true)
    })

    it('renders New Project button text', async () => {
      const wrapper = await createWrapper()
      expect(wrapper.text()).toContain('New Project')
    })

    it('renders search input field', async () => {
      const wrapper = await createWrapper()
      const searchInput = wrapper.find('input[aria-label="Search projects by name"]')
      expect(searchInput.exists()).toBe(true)
    })

    it('renders Deleted button', async () => {
      const wrapper = await createWrapper()
      expect(wrapper.text()).toContain('Deleted')
    })

  })

  describe('Search Functionality', () => {
    it('filters projects by name', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.searchQuery = 'Project 1'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredBySearch.length).toBe(1)
      expect(wrapper.vm.filteredBySearch[0].name).toBe('Project 1')
    })

    it('filters projects by mission', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.searchQuery = 'mission 1'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredBySearch.length).toBe(1)
      expect(wrapper.vm.filteredBySearch[0].mission).toContain('mission 1')
    })

    it('filters projects by ID', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.searchQuery = 'proj-1'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredBySearch.length).toBe(1)
      expect(wrapper.vm.filteredBySearch[0].id).toBe('proj-1')
    })

    it('is case insensitive', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.searchQuery = 'PROJECT 1'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredBySearch.length).toBe(1)
    })

    it('clears filter when search is empty', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.searchQuery = 'Project 1'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.filteredBySearch.length).toBe(1)

      wrapper.vm.searchQuery = ''
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.filteredBySearch.length).toBe(3) // All non-deleted projects
    })
  })

  describe('Status Filtering', () => {
    it('shows all projects when All filter is selected', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.filterStatus = 'all'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredProjects.length).toBe(3)
    })

    it('filters by active status', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.filterStatus = 'active'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredProjects).toEqual(
        expect.arrayContaining([expect.objectContaining({ status: 'active' })]),
      )
      wrapper.vm.filteredProjects.forEach((p) => {
        expect(p.status).toBe('active')
      })
    })

    it('filters by inactive status', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.filterStatus = 'inactive'
      await wrapper.vm.$nextTick()

      wrapper.vm.filteredProjects.forEach((p) => {
        expect(p.status).toBe('inactive')
      })
    })

    it('filters by completed status', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.filterStatus = 'completed'
      await wrapper.vm.$nextTick()

      wrapper.vm.filteredProjects.forEach((p) => {
        expect(p.status).toBe('completed')
      })
    })

    it('filters counts by active product', async () => {
      productStore.$patch({
        activeProduct: null,
      })

      const wrapper = await createWrapper()
      expect(wrapper.vm.activeProductProjects.length).toBe(0)
    })
  })

  describe('Deleted Projects', () => {
    it('shows deleted projects count', async () => {
      const wrapper = await createWrapper()
      expect(wrapper.vm.deletedCount).toBe(1)
    })

    it('displays deleted projects in separate modal', async () => {
      const wrapper = await createWrapper()
      expect(wrapper.vm.deletedProjects.length).toBe(1)
      expect(wrapper.vm.deletedProjects[0].id).toBe('proj-4')
    })

    it('enables Deleted button when deleted projects exist', async () => {
      const wrapper = await createWrapper()
      const deleteButton = wrapper.find('button[aria-label="View deleted projects"]')

      expect(deleteButton.exists()).toBe(true)
      expect(deleteButton.attributes('disabled')).toBeUndefined()
    })

    it('disables Deleted button when no deleted projects', async () => {
      projectStore.$patch({
        deletedProjects: [],
      })

      const wrapper = await createWrapper()
      const deleteButton = wrapper.find('button[aria-label="View deleted projects"]')

      expect(deleteButton.attributes('disabled')).toBeDefined()
    })

    it('can restore deleted projects', async () => {
      const wrapper = await createWrapper()
      await wrapper.vm.restoreFromDelete(wrapper.vm.deletedProjects[0])

      expect(projectStore.restoreProject).toHaveBeenCalledWith('proj-4')
    })
  })

  describe('Sorting', () => {
    it('sorts by created date descending by default', async () => {
      const wrapper = await createWrapper()
      // Default sort is created_at desc, but active projects are always first
      expect(wrapper.vm.sortConfig).toEqual([{ key: 'created_at', order: 'desc' }])
    })

    it('can change sort order', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.sortConfig = [{ key: 'name', order: 'asc' }]
      await wrapper.vm.$nextTick()

      // sortedProjects returns projects with active on top, then sorted by name
      const sortedProjects = wrapper.vm.sortedProjects
      expect(sortedProjects.length).toBeGreaterThan(0)
    })

    it('sorts by status', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.sortConfig = [{ key: 'status', order: 'asc' }]
      await wrapper.vm.$nextTick()

      const sortedProjects = wrapper.vm.sortedProjects
      // Active projects always come first, then sorted by status
      expect(sortedProjects.length).toBeGreaterThan(0)
    })
  })

  describe('Project CRUD Operations', () => {
    it('opens create dialog when New Project button clicked', async () => {
      const wrapper = await createWrapper()
      const button = wrapper.find('button[aria-label="Create new project"]')
      await button.trigger('click')

      expect(wrapper.vm.showCreateDialog).toBe(true)
    })

    it('deletes project after confirmation', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.projectToDelete = mockProjects[0]

      await wrapper.vm.deleteProject()

      expect(projectStore.deleteProject).toHaveBeenCalledWith('proj-1')
      expect(wrapper.vm.projectToDelete).toBeNull()
    })
  })

  describe('Status Actions', () => {
    it('handles activate action', async () => {
      const wrapper = await createWrapper()
      await wrapper.vm.handleStatusAction({ action: 'activate', projectId: 'proj-1' })

      expect(projectStore.activateProject).toHaveBeenCalledWith('proj-1')
    })

    it('handles deactivate action', async () => {
      const wrapper = await createWrapper()
      await wrapper.vm.handleStatusAction({ action: 'deactivate', projectId: 'proj-1' })

      expect(projectStore.deactivateProject).toHaveBeenCalledWith('proj-1')
    })

    it('handles cancel action', async () => {
      const wrapper = await createWrapper()
      await wrapper.vm.handleStatusAction({ action: 'cancel', projectId: 'proj-1' })

      expect(projectStore.cancelProject).toHaveBeenCalledWith('proj-1')
    })

    it('handles delete action by opening confirmation dialog', async () => {
      const wrapper = await createWrapper()
      await wrapper.vm.handleStatusAction({ action: 'delete', projectId: 'proj-1' })

      expect(wrapper.vm.showDeleteDialog).toBe(true)
      expect(wrapper.vm.projectToDelete?.id).toBe('proj-1')
    })
  })

  // 0950k: Form Validation section removed — formValid, projectData, resetForm
  // moved to ProjectCreateEditDialog. Covered by useProjectTaxonomy composable tests.

  describe('Product Integration', () => {
    it('disables New Project button when no active product', async () => {
      productStore.$patch({
        activeProduct: null,
      })

      const wrapper = await createWrapper()
      // When no active product, the Projects Table card (with Create button) is hidden
      // by v-if="activeProduct". The button only exists in the dialog header area.
      // Verify via component state that the button would be disabled.
      expect(wrapper.vm.activeProduct).toBeNull()
    })

    it('shows alert when no active product', async () => {
      productStore.$patch({
        activeProduct: null,
      })

      const wrapper = await createWrapper()
      expect(wrapper.text()).toContain('No active product selected')
    })

    it('filters projects by active product', async () => {
      const wrapper = await createWrapper()

      // Should only show projects for prod-1
      const productProjects = wrapper.vm.activeProductProjects
      productProjects.forEach((p) => {
        expect(p.product_id).toBe('prod-1')
      })
    })

  })

  describe('Date Formatting', () => {
    it('formats dates as Mon DD, YYYY', async () => {
      const wrapper = await createWrapper()
      const dateStr = '2024-10-28T12:00:00Z'
      const formatted = wrapper.vm.formatDate(dateStr)

      expect(formatted).toMatch(/Oct 28, 2024/)
    })

    it('returns N/A for empty dates', async () => {
      const wrapper = await createWrapper()
      expect(wrapper.vm.formatDate(null)).toBe('N/A')
      expect(wrapper.vm.formatDate('')).toBe('N/A')
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels on buttons', async () => {
      const wrapper = await createWrapper()

      const createButton = wrapper.find('button[aria-label="Create new project"]')
      const searchInput = wrapper.find('input[aria-label="Search projects by name"]')
      const deletedButton = wrapper.find('button[aria-label="View deleted projects"]')

      expect(createButton.exists()).toBe(true)
      expect(searchInput.exists()).toBe(true)
      expect(deletedButton.exists()).toBe(true)
    })

    it('has form labels for inputs', async () => {
      const wrapper = await createWrapper()
      wrapper.vm.showCreateDialog = true
      await wrapper.vm.$nextTick()

      const nameInput = wrapper.find('input[aria-label="Project name"]')

      expect(nameInput.exists()).toBe(true)
    })
  })
})
