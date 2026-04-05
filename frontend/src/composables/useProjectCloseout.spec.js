import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { ref, computed, nextTick } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import { useProjectCloseout } from './useProjectCloseout'

vi.mock('@/services/api', () => {
  const apiObj = {
    products: {
      getMemoryEntries: vi.fn(() => Promise.resolve({ data: { entries: [] } })),
    },
  }
  return { default: apiObj, api: apiObj }
})

vi.mock('@/stores/notifications', () => ({
  useNotificationStore: () => ({
    clearForProject: vi.fn(),
  }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn(),
  }),
}))

function makeProject(overrides = {}) {
  return ref({
    id: 'proj-1',
    project_id: 'proj-1',
    product_id: 'prod-1',
    status: 'active',
    ...overrides,
  })
}

function makeJobs(overrides = []) {
  return computed(() => overrides)
}

describe('useProjectCloseout', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('initial state', () => {
    it('exposes showCloseoutModal as false initially', () => {
      const project = makeProject()
      const sortedJobs = makeJobs([])
      const { showCloseoutModal } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs })
      expect(showCloseoutModal.value).toBe(false)
    })

    it('exposes memoryWritten as false initially', () => {
      const project = makeProject()
      const sortedJobs = makeJobs([])
      const { memoryWritten } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs })
      expect(memoryWritten.value).toBe(false)
    })

    it('exposes showContinueGuidance as false initially', () => {
      const project = makeProject()
      const sortedJobs = makeJobs([])
      const { showContinueGuidance } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs })
      expect(showContinueGuidance.value).toBe(false)
    })
  })

  describe('projectDoneStatus', () => {
    it('returns "completed" for a completed project', () => {
      const project = makeProject({ status: 'completed' })
      const { projectDoneStatus } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs([]) })
      expect(projectDoneStatus.value).toBe('completed')
    })

    it('returns "terminated" for a terminated project', () => {
      const project = makeProject({ status: 'terminated' })
      const { projectDoneStatus } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs([]) })
      expect(projectDoneStatus.value).toBe('terminated')
    })

    it('returns "cancelled" for a cancelled project', () => {
      const project = makeProject({ status: 'cancelled' })
      const { projectDoneStatus } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs([]) })
      expect(projectDoneStatus.value).toBe('cancelled')
    })

    it('returns null for an active project', () => {
      const project = makeProject({ status: 'active' })
      const { projectDoneStatus } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs([]) })
      expect(projectDoneStatus.value).toBeNull()
    })
  })

  describe('allJobsTerminal', () => {
    it('returns false when jobs array is empty', () => {
      const project = makeProject()
      const { allJobsTerminal } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs([]) })
      expect(allJobsTerminal.value).toBe(false)
    })

    it('returns false when project is already in a terminal status', () => {
      const project = makeProject({ status: 'completed' })
      const jobs = [
        { agent_display_name: 'orchestrator', status: 'complete' },
        { agent_display_name: 'implementer', status: 'complete' },
      ]
      const { allJobsTerminal } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs(jobs) })
      expect(allJobsTerminal.value).toBe(false)
    })

    it('returns false when not all jobs are terminal', () => {
      const project = makeProject()
      const jobs = [
        { agent_display_name: 'orchestrator', status: 'complete' },
        { agent_display_name: 'implementer', status: 'working' },
      ]
      const { allJobsTerminal } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs(jobs) })
      expect(allJobsTerminal.value).toBe(false)
    })

    it('returns false when all jobs are terminal but orchestrator is missing', () => {
      const project = makeProject()
      const jobs = [
        { agent_display_name: 'implementer', status: 'complete' },
        { agent_display_name: 'tester', status: 'decommissioned' },
      ]
      const { allJobsTerminal } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs(jobs) })
      expect(allJobsTerminal.value).toBe(false)
    })

    it('returns true when all jobs are terminal and orchestrator is complete', () => {
      const project = makeProject()
      const jobs = [
        { agent_display_name: 'orchestrator', status: 'complete' },
        { agent_display_name: 'implementer', status: 'decommissioned' },
      ]
      const { allJobsTerminal } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs(jobs) })
      expect(allJobsTerminal.value).toBe(true)
    })

    it('treats "completed" status (alternate spelling) as terminal', () => {
      const project = makeProject()
      const jobs = [
        { agent_display_name: 'orchestrator', status: 'completed' },
        { agent_display_name: 'implementer', status: 'complete' },
      ]
      const { allJobsTerminal } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs(jobs) })
      expect(allJobsTerminal.value).toBe(true)
    })
  })

  describe('showCloseoutButton', () => {
    it('returns false when jobs are not all terminal', () => {
      const project = makeProject()
      const jobs = [
        { agent_display_name: 'orchestrator', status: 'working' },
      ]
      const { showCloseoutButton } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs(jobs) })
      expect(showCloseoutButton.value).toBe(false)
    })

    it('returns true when all jobs terminal and no product_id (no memory gate)', () => {
      const project = makeProject({ product_id: null })
      const jobs = [
        { agent_display_name: 'orchestrator', status: 'complete' },
      ]
      const { showCloseoutButton } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs(jobs) })
      expect(showCloseoutButton.value).toBe(true)
    })

    it('returns false when all jobs terminal but memory not yet written (has product_id)', () => {
      const project = makeProject({ product_id: 'prod-1' })
      const jobs = [
        { agent_display_name: 'orchestrator', status: 'complete' },
      ]
      const { showCloseoutButton } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs(jobs) })
      expect(showCloseoutButton.value).toBe(false)
    })

    it('returns true when all jobs terminal and memory is written', () => {
      const project = makeProject({ product_id: 'prod-1' })
      const jobs = [
        { agent_display_name: 'orchestrator', status: 'complete' },
      ]
      const { showCloseoutButton, memoryWritten } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs(jobs) })
      memoryWritten.value = true
      expect(showCloseoutButton.value).toBe(true)
    })
  })

  describe('showMemoryPending', () => {
    it('returns false when jobs are not terminal', () => {
      const project = makeProject({ product_id: 'prod-1' })
      const jobs = [{ agent_display_name: 'orchestrator', status: 'working' }]
      const { showMemoryPending } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs(jobs) })
      expect(showMemoryPending.value).toBe(false)
    })

    it('returns false when no product_id', () => {
      const project = makeProject({ product_id: null })
      const jobs = [{ agent_display_name: 'orchestrator', status: 'complete' }]
      const { showMemoryPending } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs(jobs) })
      expect(showMemoryPending.value).toBe(false)
    })

    it('returns true when jobs terminal, has product_id, memory not written', () => {
      const project = makeProject({ product_id: 'prod-1' })
      const jobs = [{ agent_display_name: 'orchestrator', status: 'complete' }]
      const { showMemoryPending } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs(jobs) })
      expect(showMemoryPending.value).toBe(true)
    })

    it('returns false when memory is written', () => {
      const project = makeProject({ product_id: 'prod-1' })
      const jobs = [{ agent_display_name: 'orchestrator', status: 'complete' }]
      const { showMemoryPending, memoryWritten } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs(jobs) })
      memoryWritten.value = true
      expect(showMemoryPending.value).toBe(false)
    })
  })

  describe('openCloseoutModal', () => {
    it('sets showCloseoutModal to true', () => {
      const project = makeProject()
      const { showCloseoutModal, openCloseoutModal } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs([]) })
      expect(showCloseoutModal.value).toBe(false)
      openCloseoutModal()
      expect(showCloseoutModal.value).toBe(true)
    })
  })

  describe('handleCloseoutComplete', () => {
    it('closes the modal and calls the onComplete callback', async () => {
      const project = makeProject()
      const onComplete = vi.fn()
      const { showCloseoutModal, handleCloseoutComplete } = useProjectCloseout({
        project,
        projectId: computed(() => 'proj-1'),
        sortedJobs: makeJobs([]),
        onComplete,
      })
      showCloseoutModal.value = true
      await handleCloseoutComplete()
      expect(showCloseoutModal.value).toBe(false)
      expect(onComplete).toHaveBeenCalledOnce()
    })
  })

  describe('handleContinueWorking', () => {
    it('closes the modal, shows continue guidance, and calls onComplete', async () => {
      const project = makeProject()
      const onComplete = vi.fn()
      const { showCloseoutModal, showContinueGuidance, handleContinueWorking } = useProjectCloseout({
        project,
        projectId: computed(() => 'proj-1'),
        sortedJobs: makeJobs([]),
        onComplete,
      })
      showCloseoutModal.value = true
      await handleContinueWorking()
      expect(showCloseoutModal.value).toBe(false)
      expect(showContinueGuidance.value).toBe(true)
      expect(onComplete).toHaveBeenCalledOnce()
    })
  })

  describe('memory polling watcher', () => {
    it('sets memoryWritten when API returns existing entries', async () => {
      const api = (await import('@/services/api')).default
      api.products.getMemoryEntries.mockResolvedValue({ data: { entries: [{ id: 1 }] } })

      const project = makeProject({ product_id: 'prod-1' })
      const jobsRef = ref([{ agent_display_name: 'orchestrator', status: 'working' }])
      const sortedJobs = computed(() => jobsRef.value)
      const { memoryWritten } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs })

      jobsRef.value = [{ agent_display_name: 'orchestrator', status: 'complete' }]
      await nextTick()
      await nextTick()

      expect(memoryWritten.value).toBe(true)
    })

    it('fails open after 60s timeout when API returns no entries', async () => {
      const api = (await import('@/services/api')).default
      api.products.getMemoryEntries.mockResolvedValue({ data: { entries: [] } })

      const project = makeProject({ product_id: 'prod-1' })
      const jobs = [{ agent_display_name: 'orchestrator', status: 'complete' }]
      const { memoryWritten } = useProjectCloseout({ project, projectId: computed(() => 'proj-1'), sortedJobs: makeJobs(jobs) })

      await nextTick()
      await nextTick()
      expect(memoryWritten.value).toBe(false)

      vi.advanceTimersByTime(60_000)
      await nextTick()
      await nextTick()

      expect(memoryWritten.value).toBe(true)
    })
  })
})
