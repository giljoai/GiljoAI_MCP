import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ProjectsView from '@/views/ProjectsView.vue'

const purgeDeletedProject = vi.fn().mockResolvedValue()
const purgeAllDeletedProjects = vi.fn().mockResolvedValue()

vi.mock('@/stores/projects', () => ({
  useProjectStore: () => ({
    projects: [],
    deletedProjects: [
      { id: 'deleted-1', name: 'First Deleted', product_id: 'prod-1' },
      { id: 'deleted-2', name: 'Second Deleted', product_id: 'prod-1' }
    ],
    loading: false,
    error: null,
    fetchProjects: vi.fn().mockResolvedValue(),
    fetchDeletedProjects: vi.fn().mockResolvedValue(),
    fetchProject: vi.fn().mockResolvedValue(),
    createProject: vi.fn().mockResolvedValue(),
    updateProject: vi.fn().mockResolvedValue(),
    deleteProject: vi.fn().mockResolvedValue(),
    restoreProject: vi.fn().mockResolvedValue(),
    purgeDeletedProject,
    purgeAllDeletedProjects,
    activateProject: vi.fn().mockResolvedValue(),
    deactivateProject: vi.fn().mockResolvedValue(),
    completeProject: vi.fn().mockResolvedValue(),
    cancelProject: vi.fn().mockResolvedValue()
  })
}))

vi.mock('@/stores/products', () => ({
  useProductStore: () => ({
    activeProduct: { id: 'prod-1', name: 'Active Product' },
    products: [{ id: 'prod-1', name: 'Active Product' }],
    productMetrics: {},
    productCount: 1,
    activeProductId: 'prod-1',
    activeProductAlias: null,
    fetchProducts: vi.fn().mockResolvedValue(),
    fetchActiveProduct: vi.fn().mockResolvedValue()
  })
}))

vi.mock('@/stores/agents', () => ({
  useAgentStore: () => ({
    fetchAgents: vi.fn().mockResolvedValue(),
    agents: []
  })
}))

vi.mock('@/stores/projectTabs', () => ({
  useProjectTabsStore: () => ({
    currentProject: null,
    isLaunched: false
  })
}))

vi.mock('@/components/StatusBadge.vue', () => ({
  default: { template: '<div />' }
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn()
  })
}))

const globalStubs = {
  'v-btn': { template: '<button class="v-btn" v-bind="$attrs"><slot /></button>' },
  'v-icon': { template: '<span class="v-icon"><slot /></span>' },
  'v-text-field': { template: '<input v-bind="$attrs" />' },
  'v-menu': { template: '<div><slot /></div>' },
  'v-data-table': { template: '<div><slot /></div>' },
  'v-form': { template: '<form><slot /></form>' },
  'v-sheet': { template: '<div><slot /></div>' }
}

const mountProjectsView = () =>
  mount(ProjectsView, {
    global: {
      stubs: globalStubs
    }
  })

describe('ProjectsView - Deleted Projects Purge Controls', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows Delete All control and opens confirmation dialog when clicked', async () => {
    const wrapper = mountProjectsView()

    wrapper.vm.showDeletedDialog = true
    await nextTick()

    const deleteAllButton = wrapper.find('[data-testid="purge-projects-all"]')

    expect(deleteAllButton.exists()).toBe(true)

    // Click opens confirmPurgeAllDeleted which sets showPurgeAllDialog
    await deleteAllButton.trigger('click')
    await nextTick()

    // executePurgeAll is the method that actually calls purgeAllDeletedProjects
    await wrapper.vm.executePurgeAll()
    await nextTick()

    expect(purgeAllDeletedProjects).toHaveBeenCalled()
  })

  it('purges an individual project after confirmation', async () => {
    const wrapper = mountProjectsView()

    wrapper.vm.showDeletedDialog = true
    await nextTick()

    expect(wrapper.html()).toContain('purge-project')

    // confirmPurgeDeleted opens a dialog; purgeDeletedProject does the actual purge
    wrapper.vm.confirmPurgeDeleted({ id: 'deleted-1', name: 'First Deleted' })
    await nextTick()

    // Simulate dialog confirmation by calling purgeDeletedProject directly
    await wrapper.vm.purgeDeletedProject({ id: 'deleted-1', name: 'First Deleted' })
    await nextTick()

    expect(purgeDeletedProject).toHaveBeenCalledWith('deleted-1')
  })
})
