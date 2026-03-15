import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
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
      created_at: '2024-10-01T00:00:00Z',
      updated_at: '2024-10-28T00:00:00Z',
      deleted_at: null,
    },
    {
      id: 'proj-2',
      name: 'Project 2',
      status: 'inactive',
      product_id: 'prod-1',
      mission: 'Test mission 2',
      agent_count: 1,
      created_at: '2024-10-15T00:00:00Z',
      updated_at: '2024-10-28T00:00:00Z',
      deleted_at: null,
    },
    {
      id: 'proj-3',
      name: 'Project 3',
      status: 'inactive',
      product_id: 'prod-1',
      mission: 'Test mission 3',
      agent_count: 2,
      created_at: '2024-10-20T00:00:00Z',
      updated_at: '2024-10-28T00:00:00Z',
      deleted_at: null,
    },
    {
      id: 'proj-4',
      name: 'Deleted Project',
      status: 'completed',
      product_id: 'prod-1',
      mission: 'Test mission 4',
      agent_count: 0,
      created_at: '2024-09-01T00:00:00Z',
      updated_at: '2024-10-28T00:00:00Z',
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
    setActivePinia(createPinia())
    pinia = useProjectStore().$pinia
    vuetify = createVuetify()
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/projects',
          component: ProjectsView,
        },
        {
          path: '/projects/:id',
          component: { template: '<div>Project Details</div>' },
        },
      ],
    })

    projectStore = useProjectStore()
    productStore = useProductStore()
    agentStore = useAgentStore()

    // Mock store methods
    projectStore.$patch({
      projects: mockProjects,
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

    // Mock API calls
    projectStore.fetchProjects = vi.fn().mockResolvedValue()
    projectStore.createProject = vi.fn().mockResolvedValue(mockProjects[0])
    projectStore.updateProject = vi.fn().mockResolvedValue(mockProjects[0])
    projectStore.deleteProject = vi.fn().mockResolvedValue()
    projectStore.activateProject = vi.fn().mockResolvedValue()
    projectStore.pauseProject = vi.fn().mockResolvedValue()
    projectStore.completeProject = vi.fn().mockResolvedValue()
    projectStore.cancelProject = vi.fn().mockResolvedValue()
    projectStore.restoreProject = vi.fn().mockResolvedValue()

    productStore.fetchProducts = vi.fn().mockResolvedValue()
    productStore.fetchActiveProduct = vi.fn().mockResolvedValue()

    agentStore.fetchAgents = vi.fn().mockResolvedValue()
  })

  const createWrapper = () => {
    return mount(ProjectsView, {
      global: {
        plugins: [pinia, vuetify, router],
        stubs: {
          teleport: true,
        },
      },
    })
  }

  describe('Rendering', () => {
    it('renders header with title', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('Project Management')
    })

    it('renders active product name in header', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('Product 1')
    })

    it('renders New Project button', () => {
      const wrapper = createWrapper()
      const button = wrapper.find('button[aria-label="Create new project"]')
      expect(button.exists()).toBe(true)
    })

    it('renders stats cards for active product', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('Total Projects')
      expect(wrapper.text()).toContain('Active')
      expect(wrapper.text()).toContain('Paused')
      expect(wrapper.text()).toContain('Completed')
    })

    it('renders search input field', () => {
      const wrapper = createWrapper()
      const searchInput = wrapper.find('input[aria-label="Search projects by name"]')
      expect(searchInput.exists()).toBe(true)
    })

    it('renders View Deleted button', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('View Deleted')
    })

    it('renders filter chips for all statuses', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('All')
      expect(wrapper.text()).toContain('Active')
      expect(wrapper.text()).toContain('Inactive')
      expect(wrapper.text()).toContain('Paused')
      expect(wrapper.text()).toContain('Completed')
      expect(wrapper.text()).toContain('Cancelled')
    })
  })

  describe('Search Functionality', () => {
    it('filters projects by name', async () => {
      const wrapper = createWrapper()
      const searchInput = wrapper.find('input[aria-label="Search projects by name"]')

      await searchInput.setValue('Project 1')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredBySearch.length).toBe(1)
      expect(wrapper.vm.filteredBySearch[0].name).toBe('Project 1')
    })

    it('filters projects by mission', async () => {
      const wrapper = createWrapper()
      const searchInput = wrapper.find('input[aria-label="Search projects by name"]')

      await searchInput.setValue('mission 1')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredBySearch.length).toBe(1)
      expect(wrapper.vm.filteredBySearch[0].mission).toContain('mission 1')
    })

    it('filters projects by ID', async () => {
      const wrapper = createWrapper()
      const searchInput = wrapper.find('input[aria-label="Search projects by name"]')

      await searchInput.setValue('proj-1')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredBySearch.length).toBe(1)
      expect(wrapper.vm.filteredBySearch[0].id).toBe('proj-1')
    })

    it('is case insensitive', async () => {
      const wrapper = createWrapper()
      const searchInput = wrapper.find('input[aria-label="Search projects by name"]')

      await searchInput.setValue('PROJECT 1')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredBySearch.length).toBe(1)
    })

    it('clears filter when search is empty', async () => {
      const wrapper = createWrapper()
      const searchInput = wrapper.find('input[aria-label="Search projects by name"]')

      await searchInput.setValue('Project 1')
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.filteredBySearch.length).toBe(1)

      await searchInput.setValue('')
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.filteredBySearch.length).toBe(3) // All non-deleted projects
    })
  })

  describe('Status Filtering', () => {
    it('shows all projects when All filter is selected', async () => {
      const wrapper = createWrapper()
      wrapper.vm.filterStatus = 'all'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredProjects.length).toBe(3)
    })

    it('filters by active status', async () => {
      const wrapper = createWrapper()
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
      const wrapper = createWrapper()
      wrapper.vm.filterStatus = 'inactive'
      await wrapper.vm.$nextTick()

      wrapper.vm.filteredProjects.forEach((p) => {
        expect(p.status).toBe('inactive')
      })
    })

    it('filters by completed status', async () => {
      const wrapper = createWrapper()
      wrapper.vm.filterStatus = 'completed'
      await wrapper.vm.$nextTick()

      wrapper.vm.filteredProjects.forEach((p) => {
        expect(p.status).toBe('completed')
      })
    })

    it('does not count deleted projects in status counts', () => {
      const wrapper = createWrapper()
      const totalCounted =
        wrapper.vm.statusCounts.active +
        wrapper.vm.statusCounts.inactive +
        wrapper.vm.statusCounts.completed +
        wrapper.vm.statusCounts.cancelled

      expect(totalCounted).toBe(3) // Only non-deleted projects
    })

    it('filters counts by active product', () => {
      productStore.$patch({
        activeProduct: null,
      })

      const wrapper = createWrapper()
      expect(wrapper.vm.activeProductProjects.length).toBe(0)
      expect(wrapper.vm.statusCounts.active).toBe(0)
    })
  })

  describe('Deleted Projects', () => {
    it('shows deleted projects count', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.deletedCount).toBe(1)
    })

    it('displays deleted projects in separate modal', async () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.deletedProjects.length).toBe(1)
      expect(wrapper.vm.deletedProjects[0].id).toBe('proj-4')
    })

    it('enables View Deleted button when deleted projects exist', async () => {
      const wrapper = createWrapper()
      const deleteButton = wrapper.find('button[aria-label="View deleted projects"]')

      expect(deleteButton.exists()).toBe(true)
      expect(deleteButton.attributes('disabled')).toBeUndefined()
    })

    it('disables View Deleted button when no deleted projects', async () => {
      projectStore.$patch({
        projects: mockProjects.filter((p) => !p.deleted_at),
      })

      const wrapper = createWrapper()
      const deleteButton = wrapper.find('button[aria-label="View deleted projects"]')

      expect(deleteButton.attributes('disabled')).toBeDefined()
    })

    it('can restore deleted projects', async () => {
      const wrapper = createWrapper()
      await wrapper.vm.restoreFromDelete(wrapper.vm.deletedProjects[0])

      expect(projectStore.restoreProject).toHaveBeenCalledWith('proj-4')
    })
  })

  describe('Sorting', () => {
    it('sorts by created date descending by default', () => {
      const wrapper = createWrapper()
      const sortedProjects = wrapper.vm.sortedProjects

      for (let i = 0; i < sortedProjects.length - 1; i++) {
        const current = new Date(sortedProjects[i].created_at)
        const next = new Date(sortedProjects[i + 1].created_at)
        expect(current.getTime()).toBeGreaterThanOrEqual(next.getTime())
      }
    })

    it('can change sort order', async () => {
      const wrapper = createWrapper()
      wrapper.vm.sortConfig = [{ key: 'name', order: 'asc' }]
      await wrapper.vm.$nextTick()

      const sortedProjects = wrapper.vm.sortedProjects
      for (let i = 0; i < sortedProjects.length - 1; i++) {
        expect(
          sortedProjects[i].name.toLowerCase() <= sortedProjects[i + 1].name.toLowerCase(),
        ).toBe(true)
      }
    })

    it('sorts by status', async () => {
      const wrapper = createWrapper()
      wrapper.vm.sortConfig = [{ key: 'status', order: 'asc' }]
      await wrapper.vm.$nextTick()

      const sortedProjects = wrapper.vm.sortedProjects
      for (let i = 0; i < sortedProjects.length - 1; i++) {
        expect(sortedProjects[i].status <= sortedProjects[i + 1].status).toBe(true)
      }
    })
  })

  describe('Project CRUD Operations', () => {
    it('opens create dialog when New Project button clicked', async () => {
      const wrapper = createWrapper()
      const button = wrapper.find('button[aria-label="Create new project"]')
      await button.trigger('click')

      expect(wrapper.vm.showCreateDialog).toBe(true)
    })

    it('creates new project with form data', async () => {
      const wrapper = createWrapper()
      wrapper.vm.projectData = {
        name: 'New Project',
        mission: 'New mission',

        status: 'inactive',
      }
      wrapper.vm.formValid = true

      await wrapper.vm.saveProject()

      expect(projectStore.createProject).toHaveBeenCalled()
      const callArgs = projectStore.createProject.mock.calls[0][0]
      expect(callArgs.name).toBe('New Project')
      expect(callArgs.product_id).toBe('prod-1')
    })

    it('updates existing project', async () => {
      const wrapper = createWrapper()
      wrapper.vm.editingProject = mockProjects[0]
      wrapper.vm.projectData = {
        name: 'Updated Project',
        mission: 'Updated mission',

        status: 'active',
      }
      wrapper.vm.formValid = true

      await wrapper.vm.saveProject()

      expect(projectStore.updateProject).toHaveBeenCalledWith(
        'proj-1',
        expect.objectContaining({
          name: 'Updated Project',
        }),
      )
    })

    it('deletes project after confirmation', async () => {
      const wrapper = createWrapper()
      wrapper.vm.projectToDelete = mockProjects[0]

      await wrapper.vm.deleteProject()

      expect(projectStore.deleteProject).toHaveBeenCalledWith('proj-1')
      expect(wrapper.vm.projectToDelete).toBeNull()
    })

    it('views project details on click', async () => {
      const wrapper = createWrapper()
      await wrapper.vm.viewProject(mockProjects[0])

      expect(router.currentRoute.value.path).toContain('/projects/proj-1')
    })
  })

  describe('Status Actions', () => {
    it('handles activate action', async () => {
      const wrapper = createWrapper()
      await wrapper.vm.handleStatusAction({ action: 'activate', projectId: 'proj-1' })

      expect(projectStore.activateProject).toHaveBeenCalledWith('proj-1')
    })

    it('handles pause action', async () => {
      const wrapper = createWrapper()
      await wrapper.vm.handleStatusAction({ action: 'pause', projectId: 'proj-1' })

      expect(projectStore.pauseProject).toHaveBeenCalledWith('proj-1')
    })

    it('handles complete action', async () => {
      const wrapper = createWrapper()
      await wrapper.vm.handleStatusAction({ action: 'complete', projectId: 'proj-1' })

      expect(projectStore.completeProject).toHaveBeenCalledWith('proj-1')
    })

    it('handles cancel action', async () => {
      const wrapper = createWrapper()
      await wrapper.vm.handleStatusAction({ action: 'cancel', projectId: 'proj-1' })

      expect(projectStore.cancelProject).toHaveBeenCalledWith('proj-1')
    })

    it('handles restore action', async () => {
      const wrapper = createWrapper()
      await wrapper.vm.handleStatusAction({ action: 'restore', projectId: 'proj-1' })

      expect(projectStore.restoreProject).toHaveBeenCalledWith('proj-1')
    })

    it('handles delete action by opening confirmation dialog', async () => {
      const wrapper = createWrapper()
      await wrapper.vm.handleStatusAction({ action: 'delete', projectId: 'proj-1' })

      expect(wrapper.vm.showDeleteDialog).toBe(true)
      expect(wrapper.vm.projectToDelete?.id).toBe('proj-1')
    })
  })

  describe('Form Validation', () => {
    it('disables Create button when form is invalid', async () => {
      const wrapper = createWrapper()
      wrapper.vm.showCreateDialog = true
      wrapper.vm.formValid = false
      await wrapper.vm.$nextTick()

      const createButton = wrapper.find('button:has-text("Create")')
      expect(createButton.attributes('disabled')).toBeDefined()
    })

    it('enables Create button when form is valid', async () => {
      const wrapper = createWrapper()
      wrapper.vm.showCreateDialog = true
      wrapper.vm.formValid = true
      await wrapper.vm.$nextTick()

      // Button should not have disabled attribute
      expect(wrapper.vm.formValid).toBe(true)
    })

    it('resets form after successful creation', async () => {
      const wrapper = createWrapper()
      wrapper.vm.projectData.name = 'Test Project'
      wrapper.vm.resetForm()

      expect(wrapper.vm.projectData.name).toBe('')
      expect(wrapper.vm.projectData.mission).toBe('')
      expect(wrapper.vm.projectData.status).toBe('inactive')
    })
  })

  describe('Product Integration', () => {
    it('disables New Project button when no active product', async () => {
      productStore.$patch({
        activeProduct: null,
      })

      const wrapper = createWrapper()
      const button = wrapper.find('button[aria-label="Create new project"]')

      expect(button.attributes('disabled')).toBeDefined()
    })

    it('shows alert when no active product', async () => {
      productStore.$patch({
        activeProduct: null,
      })

      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('No active product selected')
    })

    it('filters projects by active product', async () => {
      const wrapper = createWrapper()

      // Should only show projects for prod-1
      const productProjects = wrapper.vm.activeProductProjects
      productProjects.forEach((p) => {
        expect(p.product_id).toBe('prod-1')
      })
    })

    it('associates new projects with active product', async () => {
      const wrapper = createWrapper()
      wrapper.vm.projectData = {
        name: 'New Project',
        mission: 'New mission',

        status: 'inactive',
      }
      wrapper.vm.formValid = true

      await wrapper.vm.saveProject()

      const callArgs = projectStore.createProject.mock.calls[0][0]
      expect(callArgs.product_id).toBe('prod-1')
    })
  })

  describe('Date Formatting', () => {
    it('formats dates as MM/DD for current year', () => {
      const wrapper = createWrapper()
      const dateStr = '2024-10-28T00:00:00Z'
      const formatted = wrapper.vm.formatDateShort(dateStr)

      expect(formatted).toMatch(/10\/28/)
    })

    it('formats dates as MM/DD/YY for different years', () => {
      const wrapper = createWrapper()
      const dateStr = '2023-10-28T00:00:00Z'
      const formatted = wrapper.vm.formatDateShort(dateStr)

      expect(formatted).toMatch(/10\/28\/23/)
    })

    it('returns dash for empty dates', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.formatDateShort(null)).toBe('—')
      expect(wrapper.vm.formatDateShort('')).toBe('—')
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels on buttons', () => {
      const wrapper = createWrapper()

      const createButton = wrapper.find('button[aria-label="Create new project"]')
      const searchInput = wrapper.find('input[aria-label="Search projects by name"]')
      const deletedButton = wrapper.find('button[aria-label="View deleted projects"]')

      expect(createButton.exists()).toBe(true)
      expect(searchInput.exists()).toBe(true)
      expect(deletedButton.exists()).toBe(true)
    })

    it('has form labels for inputs', async () => {
      const wrapper = createWrapper()
      wrapper.vm.showCreateDialog = true
      await wrapper.vm.$nextTick()

      const nameInput = wrapper.find('input[aria-label="Project name"]')
      const statusSelect = wrapper.find('[aria-label="Project status"]')

      expect(nameInput.exists()).toBe(true)
      expect(statusSelect.exists()).toBe(true)
    })

    it('has semantic structure for data table', () => {
      const wrapper = createWrapper()
      const table = wrapper.find('[role="table"]')

      expect(table.exists()).toBe(true)
    })
  })
})
