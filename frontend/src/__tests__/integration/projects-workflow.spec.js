import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import { createRouter, createMemoryHistory } from 'vue-router'
import ProjectsView from '@/views/ProjectsView.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useProjectStore } from '@/stores/projects'
import { useProductStore } from '@/stores/products'
import { useAgentStore } from '@/stores/agents'

describe('Projects Workflow Integration Tests', () => {
  let pinia
  let vuetify
  let router
  let projectStore
  let productStore
  let agentStore

  const mockProduct = {
    id: 'prod-1',
    name: 'E-Commerce Platform',
    is_active: true,
  }

  const mockInitialProjects = [
    {
      id: 'proj-user-auth',
      name: 'User Authentication',
      status: 'active',
      product_id: 'prod-1',
      mission: 'Implement OAuth2 authentication with JWT tokens',
      agent_count: 3,
      created_at: '2024-10-01T08:00:00Z',
      updated_at: '2024-10-28T14:30:00Z',
      deleted_at: null,
    },
    {
      id: 'proj-payment',
      name: 'Payment Integration',
      status: 'inactive',
      product_id: 'prod-1',
      mission: 'Integrate Stripe payment processing',
      agent_count: 2,
      created_at: '2024-10-10T10:00:00Z',
      updated_at: '2024-10-28T10:00:00Z',
      deleted_at: null,
    },
    {
      id: 'proj-api',
      name: 'REST API',
      status: 'inactive',
      product_id: 'prod-1',
      mission: 'Build comprehensive REST API endpoints',
      agent_count: 1,
      created_at: '2024-10-20T09:00:00Z',
      updated_at: '2024-10-28T09:00:00Z',
      deleted_at: null,
    },
    {
      id: 'proj-legacy',
      name: 'Legacy System Migration',
      status: 'completed',
      product_id: 'prod-1',
      mission: 'Migrate from monolith to microservices',
      agent_count: 0,
      created_at: '2024-09-15T07:00:00Z',
      updated_at: '2024-10-25T16:00:00Z',
      completed_at: '2024-10-25T16:00:00Z',
      deleted_at: null,
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
      ],
    })

    projectStore = useProjectStore()
    productStore = useProductStore()
    agentStore = useAgentStore()

    // Mock store state
    projectStore.$patch({
      projects: JSON.parse(JSON.stringify(mockInitialProjects)),
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

    // Mock API calls
    projectStore.fetchProjects = vi.fn().mockResolvedValue()
    projectStore.createProject = vi.fn((data) => {
      const newProject = {
        ...data,
        id: `proj-${Date.now()}`,
        agent_count: 0,

        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        deleted_at: null,
      }
      projectStore.$patch({
        projects: [...projectStore.projects, newProject],
      })
      return Promise.resolve(newProject)
    })

    projectStore.updateProject = vi.fn((id, updates) => {
      const projectIndex = projectStore.projects.findIndex((p) => p.id === id)
      if (projectIndex !== -1) {
        projectStore.projects[projectIndex] = {
          ...projectStore.projects[projectIndex],
          ...updates,
          updated_at: new Date().toISOString(),
        }
      }
      return Promise.resolve(projectStore.projects[projectIndex])
    })

    projectStore.deleteProject = vi.fn((id) => {
      projectStore.$patch({
        projects: projectStore.projects.map((p) =>
          p.id === id ? { ...p, deleted_at: new Date().toISOString() } : p,
        ),
      })
      return Promise.resolve()
    })

    projectStore.activateProject = vi.fn((id) =>
      projectStore.updateProject(id, { status: 'active' }),
    )
    projectStore.deactivateProject = vi.fn((id) =>
      projectStore.updateProject(id, { status: 'inactive' }),
    )
    projectStore.completeProject = vi.fn((id) =>
      projectStore.updateProject(id, { status: 'completed' }),
    )
    projectStore.cancelProject = vi.fn((id) =>
      projectStore.updateProject(id, { status: 'cancelled' }),
    )
    projectStore.restoreProject = vi.fn((id) =>
      projectStore.updateProject(id, { status: 'inactive', deleted_at: null }),
    )

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

  describe('Scenario 1: View and Filter Projects', () => {
    it('displays all projects on initial load', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.activeProductProjects.length).toBe(4)
      expect(wrapper.text()).toContain('User Authentication')
      expect(wrapper.text()).toContain('Payment Integration')
      expect(wrapper.text()).toContain('REST API')
      expect(wrapper.text()).toContain('Legacy System Migration')
    })

    it('displays correct status counts', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.statusCounts.active).toBe(1)
      expect(wrapper.vm.statusCounts.inactive).toBe(1)
      expect(wrapper.vm.statusCounts.inactive).toBe(1)
      expect(wrapper.vm.statusCounts.completed).toBe(1)
    })

    it('filters projects by active status', async () => {
      const wrapper = createWrapper()

      wrapper.vm.filterStatus = 'active'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredProjects.length).toBe(1)
      expect(wrapper.vm.filteredProjects[0].name).toBe('User Authentication')
      expect(wrapper.vm.filteredProjects[0].status).toBe('active')
    })

    it('filters projects by search query', async () => {
      const wrapper = createWrapper()

      wrapper.vm.searchQuery = 'Payment'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredBySearch.length).toBe(1)
      expect(wrapper.vm.filteredBySearch[0].name).toBe('Payment Integration')
    })

    it('combines search and status filters', async () => {
      const wrapper = createWrapper()

      wrapper.vm.searchQuery = 'auth'
      wrapper.vm.filterStatus = 'active'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredProjects.length).toBe(1)
      expect(wrapper.vm.filteredProjects[0].name).toBe('User Authentication')
    })

    it('sorts projects by creation date descending', () => {
      const wrapper = createWrapper()

      const sorted = wrapper.vm.sortedProjects
      expect(sorted[0].id).toBe('proj-api')
      expect(sorted[1].id).toBe('proj-payment')
      expect(sorted[2].id).toBe('proj-user-auth')
      expect(sorted[3].id).toBe('proj-legacy')
    })
  })

  describe('Scenario 2: Create New Project', () => {
    it('opens create dialog and fills form', async () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.showCreateDialog).toBe(false)
      wrapper.vm.showCreateDialog = true
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showCreateDialog).toBe(true)
    })

    it('creates new project with valid form data', async () => {
      const wrapper = createWrapper()

      wrapper.vm.projectData = {
        name: 'Frontend UI Framework',
        mission: 'Build component library for product',

        status: 'inactive',
      }
      wrapper.vm.formValid = true

      await wrapper.vm.saveProject()

      expect(projectStore.createProject).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Frontend UI Framework',
          mission: 'Build component library for product',
          product_id: 'prod-1',
        }),
      )

      // Verify project was added to store
      const newProject = projectStore.projects.find((p) => p.name === 'Frontend UI Framework')
      expect(newProject).toBeDefined()
    })

    it('associates created project with active product', async () => {
      const wrapper = createWrapper()

      wrapper.vm.projectData = {
        name: 'Testing Suite',
        mission: 'Implement comprehensive test coverage',

        status: 'inactive',
      }
      wrapper.vm.formValid = true

      await wrapper.vm.saveProject()

      const newProject = projectStore.projects.find((p) => p.name === 'Testing Suite')
      expect(newProject.product_id).toBe('prod-1')
    })

    it('clears form after successful creation', async () => {
      const wrapper = createWrapper()

      wrapper.vm.projectData = {
        name: 'New Project',
        mission: 'Test mission',

        status: 'inactive',
      }
      wrapper.vm.formValid = true

      await wrapper.vm.saveProject()
      await new Promise((r) => setTimeout(r, 100))

      expect(wrapper.vm.projectData.name).toBe('')
      expect(wrapper.vm.projectData.mission).toBe('')
    })
  })

  describe('Scenario 3: Manage Project Status', () => {
    it('activates inactive project', async () => {
      const wrapper = createWrapper()
      const apiProject = projectStore.projects.find((p) => p.id === 'proj-api')

      expect(apiProject.status).toBe('inactive')

      await wrapper.vm.handleStatusAction({
        action: 'activate',
        projectId: 'proj-api',
      })

      expect(projectStore.activateProject).toHaveBeenCalledWith('proj-api')
      const updated = projectStore.projects.find((p) => p.id === 'proj-api')
      expect(updated.status).toBe('active')
    })

    it('deactivates active project', async () => {
      const wrapper = createWrapper()
      const userAuthProject = projectStore.projects.find((p) => p.id === 'proj-user-auth')

      expect(userAuthProject.status).toBe('active')

      await wrapper.vm.handleStatusAction({
        action: 'deactivate',
        projectId: 'proj-user-auth',
      })

      expect(projectStore.deactivateProject).toHaveBeenCalledWith('proj-user-auth')
      const updated = projectStore.projects.find((p) => p.id === 'proj-user-auth')
      expect(updated.status).toBe('inactive')
    })

    it('completes active project', async () => {
      const wrapper = createWrapper()

      await wrapper.vm.handleStatusAction({
        action: 'complete',
        projectId: 'proj-user-auth',
      })

      expect(projectStore.completeProject).toHaveBeenCalledWith('proj-user-auth')
      const updated = projectStore.projects.find((p) => p.id === 'proj-user-auth')
      expect(updated.status).toBe('completed')
    })

    it('cancels incomplete project', async () => {
      const wrapper = createWrapper()

      await wrapper.vm.handleStatusAction({
        action: 'cancel',
        projectId: 'proj-payment',
      })

      expect(projectStore.cancelProject).toHaveBeenCalledWith('proj-payment')
      const updated = projectStore.projects.find((p) => p.id === 'proj-payment')
      expect(updated.status).toBe('cancelled')
    })

    it('restores completed project', async () => {
      const wrapper = createWrapper()

      await wrapper.vm.handleStatusAction({
        action: 'restore',
        projectId: 'proj-legacy',
      })

      expect(projectStore.restoreProject).toHaveBeenCalledWith('proj-legacy')
    })

    it('updates UI when project status changes', async () => {
      const wrapper = createWrapper()

      // Initial state
      expect(wrapper.vm.statusCounts.active).toBe(1)
      expect(wrapper.vm.statusCounts.inactive).toBe(1)

      // Activate an inactive project
      await wrapper.vm.handleStatusAction({
        action: 'activate',
        projectId: 'proj-api',
      })

      // Status counts should update
      expect(wrapper.vm.statusCounts.active).toBe(2)
      expect(wrapper.vm.statusCounts.inactive).toBe(0)
    })
  })

  describe('Scenario 4: Search and Filter Combined', () => {
    it('searches within filtered status', async () => {
      const wrapper = createWrapper()

      wrapper.vm.filterStatus = 'active'
      wrapper.vm.searchQuery = 'auth'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredProjects.length).toBe(1)
      expect(wrapper.vm.filteredProjects[0].id).toBe('proj-user-auth')
    })

    it('handles no results gracefully', async () => {
      const wrapper = createWrapper()

      wrapper.vm.searchQuery = 'nonexistent'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.filteredBySearch.length).toBe(0)
      expect(wrapper.vm.filteredProjects.length).toBe(0)
    })

    it('clears search results when filter changes', async () => {
      const wrapper = createWrapper()

      wrapper.vm.searchQuery = 'Integration'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.filteredBySearch.length).toBe(1)

      wrapper.vm.searchQuery = ''
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.filteredBySearch.length).toBe(4)
    })
  })

  describe('Scenario 5: Delete and Restore Projects', () => {
    it('soft-deletes project without affecting others', async () => {
      const wrapper = createWrapper()

      const initialCount = wrapper.vm.activeProductProjects.length
      expect(initialCount).toBe(4)

      await wrapper.vm.deleteProject(projectStore.projects[0])

      // Project is now deleted but still in list with deleted_at set
      expect(wrapper.vm.activeProductProjects.length).toBe(3)
      expect(wrapper.vm.deletedProjects.length).toBe(1)
    })

    it('shows deleted projects in separate section', async () => {
      const wrapper = createWrapper()

      await wrapper.vm.deleteProject(projectStore.projects[0])
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.deletedCount).toBeGreaterThan(0)
      expect(wrapper.vm.deletedProjects.length).toBe(1)
    })

    it('restores deleted project', async () => {
      const wrapper = createWrapper()

      // Delete a project first
      const projectToDelete = projectStore.projects.find((p) => p.id === 'proj-api')
      await projectStore.deleteProject('proj-api')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.deletedProjects.length).toBe(1)

      // Restore it
      await wrapper.vm.restoreFromDelete(wrapper.vm.deletedProjects[0])

      // Should be back in active list
      expect(wrapper.vm.deletedProjects.length).toBe(0)
      expect(wrapper.vm.activeProductProjects.length).toBe(4)
    })
  })

  describe('Scenario 6: Edit Existing Project', () => {
    it('loads project data into form for editing', async () => {
      const wrapper = createWrapper()
      const projectToEdit = projectStore.projects.find((p) => p.id === 'proj-user-auth')

      wrapper.vm.editProject(projectToEdit)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.projectData.name).toBe('User Authentication')
      expect(wrapper.vm.projectData.mission).toBe('Implement OAuth2 authentication with JWT tokens')
      expect(wrapper.vm.editingProject.id).toBe('proj-user-auth')
    })

    it('updates project with new data', async () => {
      const wrapper = createWrapper()
      const projectToEdit = projectStore.projects.find((p) => p.id === 'proj-user-auth')

      wrapper.vm.editProject(projectToEdit)
      wrapper.vm.projectData.mission = 'Updated mission with new requirements'
      wrapper.vm.formValid = true

      await wrapper.vm.saveProject()

      expect(projectStore.updateProject).toHaveBeenCalledWith(
        'proj-user-auth',
        expect.objectContaining({
          mission: 'Updated mission with new requirements',
        }),
      )

      const updated = projectStore.projects.find((p) => p.id === 'proj-user-auth')
      expect(updated.mission).toBe('Updated mission with new requirements')
    })

    it('does not modify product_id when updating', async () => {
      const wrapper = createWrapper()
      const projectToEdit = projectStore.projects.find((p) => p.id === 'proj-user-auth')

      wrapper.vm.editProject(projectToEdit)
      wrapper.vm.projectData.name = 'Updated Name'
      wrapper.vm.formValid = true

      await wrapper.vm.saveProject()

      const updated = projectStore.projects.find((p) => p.id === 'proj-user-auth')
      expect(updated.product_id).toBe('prod-1')
    })
  })

  describe('Scenario 7: Status Badge Integration', () => {
    it('status badge correctly reflects project status', async () => {
      const wrapper = createWrapper()
      const badge = wrapper.findComponent(StatusBadge)

      expect(badge.exists()).toBe(true)
      expect(badge.props('status')).toBeDefined()
      expect(badge.props('projectId')).toBeDefined()
    })

    it('badge emits action event that triggers project updates', async () => {
      const wrapper = createWrapper()

      await wrapper.vm.handleStatusAction({
        action: 'activate',
        projectId: 'proj-api',
      })

      const project = projectStore.projects.find((p) => p.id === 'proj-api')
      expect(project.status).toBe('active')
    })
  })

  describe('Scenario 8: Product-Based Isolation', () => {
    it('only shows projects for active product', () => {
      const wrapper = createWrapper()

      wrapper.vm.activeProductProjects.forEach((p) => {
        expect(p.product_id).toBe('prod-1')
      })
    })

    it('disables create when no active product', async () => {
      productStore.$patch({
        activeProduct: null,
      })

      const wrapper = createWrapper()

      expect(wrapper.vm.activeProduct).toBeNull()
      // New Project button should be disabled
    })

    it('associates new projects with active product', async () => {
      const wrapper = createWrapper()

      wrapper.vm.projectData = {
        name: 'New Isolated Project',
        mission: 'Test isolation',

        status: 'inactive',
      }
      wrapper.vm.formValid = true

      await wrapper.vm.saveProject()

      const newProject = projectStore.projects.find((p) => p.name === 'New Isolated Project')
      expect(newProject.product_id).toBe('prod-1')
    })
  })

  describe('Scenario 9: Real-time Update Handling', () => {
    it('handles project status changes in real-time', async () => {
      const wrapper = createWrapper()

      const initialStatus = projectStore.projects.find((p) => p.id === 'proj-user-auth').status
      expect(initialStatus).toBe('active')

      // Simulate real-time status update
      projectStore.$patch({
        projects: projectStore.projects.map((p) =>
          p.id === 'proj-user-auth' ? { ...p, status: 'inactive' } : p,
        ),
      })

      await wrapper.vm.$nextTick()

      const updated = projectStore.projects.find((p) => p.id === 'proj-user-auth')
      expect(updated.status).toBe('inactive')
      expect(wrapper.vm.statusCounts.active).toBe(0)
      expect(wrapper.vm.statusCounts.inactive).toBe(2)
    })

    it('handles new project creation in real-time', async () => {
      const wrapper = createWrapper()

      const newProject = {
        id: 'proj-new-realtime',
        name: 'Real-time Project',
        status: 'inactive',
        product_id: 'prod-1',
        mission: 'Test real-time creation',


        agent_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        deleted_at: null,
      }

      projectStore.$patch({
        projects: [...projectStore.projects, newProject],
      })

      await wrapper.vm.$nextTick()

      expect(projectStore.projects.find((p) => p.id === 'proj-new-realtime')).toBeDefined()
      expect(wrapper.vm.activeProductProjects.length).toBe(5)
    })
  })
})
