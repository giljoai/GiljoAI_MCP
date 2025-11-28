/**
 * Unit tests for projects store - Status Synchronization
 *
 * BEHAVIOR TESTS (Not Implementation):
 * - Projects list refreshes after creation to get actual backend status
 * - Frontend doesn't assume created project status matches request
 * - Backend is the source of truth for project state
 *
 * TDD RED Phase - These tests MUST FAIL initially
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProjectStore } from '@/stores/projects'

// Mock the API
vi.mock('@/services/api', () => ({
  default: {
    projects: {
      create: vi.fn(),
      list: vi.fn(),
      get: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      activate: vi.fn(),
      deactivate: vi.fn(),
      fetchDeleted: vi.fn(),
      restore: vi.fn(),
      purgeDeleted: vi.fn(),
      purgeAllDeleted: vi.fn()
    }
  }
}))

import api from '@/services/api'

describe('Projects Store - Status Synchronization', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should refresh projects after creation to get actual backend status', async () => {
    /**
     * BEHAVIOR: After creating a project, the store MUST fetch from backend
     * to get the actual status, not trust the local request data.
     *
     * This prevents the bug where:
     * 1. Frontend creates project with status='inactive'
     * 2. Backend auto-activates it (status='active')
     * 3. Frontend still thinks it's 'inactive'
     * 4. User tries to activate → 400 error (already active)
     */
    const projectStore = useProjectStore()

    // Backend returns 'active' (auto-activated due to Single Active Project logic)
    const backendResponse = {
      id: 'new-proj-123',
      name: 'Test Project',
      status: 'active',  // Backend changed status
      product_id: 'prod-456'
    }

    // Mock API responses
    api.projects.create.mockResolvedValue({ data: backendResponse })
    api.projects.list.mockResolvedValue({ data: [backendResponse] })

    // Act - Create project with status='inactive'
    const result = await projectStore.createProject({
      name: 'Test Project',
      status: 'inactive',  // Frontend requests inactive
      product_id: 'prod-456'
    })

    // Assert - BEHAVIOR: Store MUST reflect actual backend state
    expect(api.projects.list).toHaveBeenCalled()
    expect(projectStore.projects).toHaveLength(1)
    expect(projectStore.projects[0].status).toBe('active')  // Actual backend status
    expect(result.status).toBe('active')  // Return value should also reflect backend
  })

  it('should not assume created project matches request data', async () => {
    /**
     * BEHAVIOR: Store must not blindly push request data to projects array.
     * Backend may modify fields (status, timestamps, etc.)
     */
    const projectStore = useProjectStore()

    // Backend modifies the status
    const requestData = {
      name: 'Test',
      status: 'inactive',
      product_id: 'prod-789'
    }

    const backendResponse = {
      ...requestData,
      id: 'created-id',
      status: 'active',  // Backend changed this
      created_at: '2025-11-27T21:00:00Z'
    }

    api.projects.create.mockResolvedValue({ data: backendResponse })
    api.projects.list.mockResolvedValue({ data: [backendResponse] })

    // Act
    await projectStore.createProject(requestData)

    // Assert - BEHAVIOR: Store has backend's version, not request version
    const createdProject = projectStore.projects.find(p => p.id === 'created-id')
    expect(createdProject).toBeDefined()
    expect(createdProject.status).toBe('active')  // Backend's value
    expect(createdProject.status).not.toBe(requestData.status)  // Not request's value
  })

  it('should handle backend status transitions correctly', async () => {
    /**
     * BEHAVIOR: When backend auto-deactivates other projects (Single Active Project),
     * frontend must reflect those changes after creation.
     */
    const projectStore = useProjectStore()

    // Start with one active project
    const existingProject = {
      id: 'existing-123',
      name: 'Existing',
      status: 'active'
    }

    // New project will be active, existing becomes inactive
    const newProject = {
      id: 'new-456',
      name: 'New',
      status: 'active'
    }

    projectStore.projects = [existingProject]

    api.projects.create.mockResolvedValue({ data: newProject })
    api.projects.list.mockResolvedValue({
      data: [
        { ...existingProject, status: 'inactive' },  // Backend deactivated
        newProject
      ]
    })

    // Act
    await projectStore.createProject({ name: 'New', status: 'inactive' })

    // Assert - BEHAVIOR: Both projects reflect backend state
    expect(projectStore.projects).toHaveLength(2)
    const existing = projectStore.projects.find(p => p.id === 'existing-123')
    const created = projectStore.projects.find(p => p.id === 'new-456')

    expect(existing.status).toBe('inactive')  // Auto-deactivated by backend
    expect(created.status).toBe('active')  // New project is active
  })

  it('purgeDeletedProject removes the project from deleted list and refreshes state', async () => {
    const projectStore = useProjectStore()

    projectStore.deletedProjects = [
      { id: 'deleted-1', name: 'Old Deleted' },
      { id: 'deleted-2', name: 'Keep Me' }
    ]

    api.projects.purgeDeleted.mockResolvedValue({ data: { success: true } })
    api.projects.fetchDeleted.mockResolvedValue({ data: [{ id: 'deleted-2', name: 'Keep Me' }] })

    await projectStore.purgeDeletedProject('deleted-1')

    expect(api.projects.purgeDeleted).toHaveBeenCalledWith('deleted-1')
    expect(api.projects.fetchDeleted).toHaveBeenCalled()
    expect(projectStore.deletedProjects.find(p => p.id === 'deleted-1')).toBeUndefined()
    expect(projectStore.deletedProjects).toHaveLength(1)
  })

  it('purgeAllDeletedProjects clears deleted list for current tenant', async () => {
    const projectStore = useProjectStore()

    projectStore.deletedProjects = [
      { id: 'deleted-1', name: 'One' },
      { id: 'deleted-2', name: 'Two' }
    ]

    api.projects.purgeAllDeleted.mockResolvedValue({ data: { success: true, purged_count: 2 } })
    api.projects.fetchDeleted.mockResolvedValue({ data: [] })

    await projectStore.purgeAllDeletedProjects()

    expect(api.projects.purgeAllDeleted).toHaveBeenCalled()
    expect(api.projects.fetchDeleted).toHaveBeenCalled()
    expect(projectStore.deletedProjects).toHaveLength(0)
  })
})
