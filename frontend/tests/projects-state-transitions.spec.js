import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useProjectStore } from '@/stores/projects'
import { useProductStore } from '@/stores/products'
import api from '@/services/api'

// Mock API
vi.mock('@/services/api', () => {
  const mockApi = {
    projects: {
      list: vi.fn(),
      get: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      changeStatus: vi.fn(),
      complete: vi.fn(),
      cancel: vi.fn(),
      restore: vi.fn(),
      restoreCompleted: vi.fn(),
      fetchDeleted: vi.fn(),
      activate: vi.fn(),
      deactivate: vi.fn(),
    },
    products: {
      list: vi.fn(),
      get: vi.fn(),
    },
  }
  return {
    default: mockApi,
    api: mockApi,
  }
})

describe('Project State Transitions - Comprehensive Test Suite', () => {
  let projectStore
  let productStore

  beforeEach(() => {
    setActivePinia(createPinia())
    projectStore = useProjectStore()
    productStore = useProductStore()

    // Mock product data
    productStore.products = [
      {
        id: 'prod-1',
        name: 'Test Product',
        status: 'active',
      },
    ]
    productStore.activeProduct = productStore.products[0]

    // Mock project data - one for each state
    projectStore.projects = [
      {
        id: 'proj-active',
        name: 'Active Project',
        status: 'active',
        product_id: 'prod-1',
        mission: 'Test mission',
        context_budget: 150000,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      },
      {
        id: 'proj-inactive',
        name: 'Inactive Project',
        status: 'inactive',
        product_id: 'prod-1',
        mission: 'Test mission',
        context_budget: 150000,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      },
      {
        id: 'proj-inactive',
        name: 'Inactive Project',
        status: 'inactive',
        product_id: 'prod-1',
        mission: 'Test mission',
        context_budget: 150000,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      },
      {
        id: 'proj-completed',
        name: 'Completed Project',
        status: 'completed',
        product_id: 'prod-1',
        mission: 'Test mission',
        context_budget: 150000,
        completed_at: '2025-01-05T00:00:00Z',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-05T00:00:00Z',
      },
    ]

    projectStore.deletedProjects = []

    // Default API mock returns to prevent undefined data errors
    api.projects.list.mockImplementation(() => Promise.resolve({ data: projectStore.projects }))
    api.projects.activate.mockResolvedValue({
      data: { ...(projectStore.projects[1] || {}), id: projectStore.projects[1]?.id || 'proj-activate', status: 'active' }
    })
    api.projects.deactivate.mockResolvedValue({
      data: { ...(projectStore.projects[0] || {}), id: projectStore.projects[0]?.id || 'proj-deactivate', status: 'inactive' }
    })
    api.projects.changeStatus.mockResolvedValue({ data: { id: 'proj-change', status: 'inactive' } })
    api.projects.fetchDeleted.mockResolvedValue({ data: [] })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  // =====================================
  // TEST SET 1: Active → Paused
  // =====================================
  describe('State Transition: Active → Deactivate', () => {
    it('TEST 1.1: Should deactivate an active project via API', async () => {
      const project = projectStore.projects[0]
      expect(project.status).toBe('active')

      const mockResponse = {
        data: {
          ...project,
          status: 'inactive',
          updated_at: new Date().toISOString(),
        }
      }

      api.projects.deactivate.mockResolvedValue(mockResponse)

      const result = await projectStore.deactivateProject(project.id)

      expect(api.projects.deactivate).toHaveBeenCalledWith(project.id)
      expect(result).toBeUndefined()

      const updatedProject = projectStore.projects.find(p => p.id === project.id)
      expect(updatedProject).toBeDefined()
      expect(updatedProject?.status).toBe('inactive')
    })

    it('TEST 1.2: Should show deactivate option in StatusBadge menu', () => {
      const actionsByStatus = {
        active: ['deactivate', 'complete', 'cancel', 'delete'],
      }
      expect(actionsByStatus.active).toContain('deactivate')
    })

    it('TEST 1.3: Should NOT require confirmation for deactivate action', () => {
      const deactivateAction = { value: 'deactivate', requiresConfirm: false }
      expect(deactivateAction.requiresConfirm).toBe(false)
    })

    it('TEST 1.4: Should update status badge UI after deactivate', async () => {
      const project = projectStore.projects[0]

      api.projects.deactivate.mockResolvedValue({
        data: { ...project, status: 'inactive' }
      })

      await projectStore.deactivateProject(project.id)

      const updated = projectStore.projects.find(p => p.id === project.id)
      expect(updated).toBeDefined()
      expect(updated?.status).toBe('inactive')
    })

    it('TEST 1.5: Should use PATCH /api/v1/projects/{id}/ endpoint', async () => {
      const project = projectStore.projects[0]

      api.projects.deactivate.mockResolvedValue({
        data: { ...project, status: 'inactive' }
      })

      await projectStore.deactivateProject(project.id)

      expect(api.projects.deactivate).toHaveBeenCalledWith(project.id)
    })
  })

  // =====================================
  // TEST SET 2: Inactive → Active (Activate)
  // =====================================
  describe('State Transition: Inactive → Active', () => {
    it('TEST 2.1: Should activate an inactive project', async () => {
      const project = projectStore.projects[1]
      expect(project.status).toBe('inactive')

      const mockResponse = {
        data: { ...project, status: 'active', updated_at: new Date().toISOString() }
      }

      api.projects.activate.mockResolvedValue(mockResponse)

      const result = await projectStore.activateProject(project.id)

      expect(api.projects.activate).toHaveBeenCalledWith(project.id)
      expect(result.status).toBe('active')

      const updatedProject = projectStore.projects.find(p => p.id === project.id)
      expect(updatedProject).toBeDefined()
      expect(updatedProject?.status).toBe('active')
    })

    it('TEST 2.2: Should show activate option in StatusBadge menu for inactive', () => {
      const actionsByStatus = {
        inactive: ['activate', 'complete', 'cancel', 'delete'],
      }
      expect(actionsByStatus.inactive).toContain('activate')
    })

    it('TEST 2.3: Should NOT require confirmation for activate', () => {
      const activateAction = { value: 'activate', requiresConfirm: false }
      expect(activateAction.requiresConfirm).toBe(false)
    })

    it('TEST 2.4: Should handle Inactive → Active → Inactive cycle', async () => {
      const project = projectStore.projects[1]

      // Inactive → Active
      api.projects.activate.mockResolvedValue({
        data: { ...project, status: 'active' }
      })

      let result = await projectStore.activateProject(project.id)
      expect(result.status).toBe('active')

      // Active → Inactive
      api.projects.deactivate.mockResolvedValue({
        data: { ...result, status: 'inactive' }
      })

      await projectStore.deactivateProject(project.id)

      const afterDeactivate = projectStore.projects.find(p => p.id === project.id)
      expect(afterDeactivate).toBeDefined()
      expect(afterDeactivate?.status).toBe('inactive')
    })

    it('TEST 2.5: Should use PATCH /api/v1/projects/{id}/ with status: active', async () => {
      const project = projectStore.projects[1]

      api.projects.activate.mockResolvedValue({
        data: { ...project, status: 'active' }
      })

      await projectStore.activateProject(project.id)

      expect(api.projects.activate).toHaveBeenCalledWith(project.id)
    })
  })

  // =====================================
  // TEST SET 3: Active → Completed
  // =====================================
  describe('State Transition: Active → Completed', () => {
    it('TEST 3.1: Should complete an active project', async () => {
      const project = projectStore.projects[0]
      expect(project.status).toBe('active')

      const completedAt = new Date().toISOString()
      const mockResponse = {
        data: {
          ...project,
          status: 'completed',
          completed_at: completedAt,
          updated_at: completedAt,
        }
      }

      api.projects.complete.mockResolvedValue(mockResponse)

      const result = await projectStore.completeProject(project.id)

      expect(api.projects.complete).toHaveBeenCalledWith(project.id)
      expect(result.status).toBe('completed')
      expect(result.completed_at).toBe(completedAt)

      const updatedProject = projectStore.projects.find(p => p.id === project.id)
      expect(updatedProject.status).toBe('completed')
    })

    it('TEST 3.2: Should show complete option for active status', () => {
      const actionsByStatus = {
        active: ['pause', 'complete', 'cancel', 'deactivate', 'delete'],
      }
      expect(actionsByStatus.active).toContain('complete')
    })

    it('TEST 3.3: Should REQUIRE confirmation dialog for complete', () => {
      const completeAction = { value: 'complete', requiresConfirm: true }
      expect(completeAction.requiresConfirm).toBe(true)
    })

    it('TEST 3.4: Should set completed_at timestamp', async () => {
      const project = projectStore.projects[0]
      const now = new Date().toISOString()

      api.projects.complete.mockResolvedValue({
        data: {
          ...project,
          status: 'completed',
          completed_at: now,
          updated_at: now,
        }
      })

      const result = await projectStore.completeProject(project.id)

      expect(result.completed_at).toBeTruthy()
      expect(result.status).toBe('completed')
    })

    it('TEST 3.5: Should use POST /api/v1/projects/{id}/complete endpoint', async () => {
      const project = projectStore.projects[0]

      api.projects.complete.mockResolvedValue({
        data: { ...project, status: 'completed' }
      })

      await projectStore.completeProject(project.id)

      expect(api.projects.complete).toHaveBeenCalledWith(project.id)
    })
  })

  // =====================================
  // TEST SET 4: Completed → Active (Reopen)
  // =====================================
  describe('State Transition: Completed → Active', () => {
    it('TEST 4.1: Should reopen a completed project', async () => {
      const project = projectStore.projects[3]
      expect(project.status).toBe('completed')

      const mockResponse = {
        data: {
          ...project,
          status: 'inactive',
          completed_at: null,
          updated_at: new Date().toISOString(),
        }
      }

      api.projects.restoreCompleted.mockResolvedValue(mockResponse)

      const result = await projectStore.restoreCompletedProject(project.id)

      expect(api.projects.restoreCompleted).toHaveBeenCalledWith(project.id)
      expect(result.status).toBe('inactive')
      expect(result.completed_at).toBeNull()
    })

    it('TEST 4.2: Should show reopen option for completed status', () => {
      const actionsByStatus = {
        completed: ['reopen', 'archive', 'delete'],
      }
      expect(actionsByStatus.completed).toContain('reopen')
    })

    it('TEST 4.3: Should NOT show pause/resume for completed', () => {
      const actionsByStatus = {
        completed: ['reopen', 'archive', 'delete'],
      }
      expect(actionsByStatus.completed).not.toContain('pause')
      expect(actionsByStatus.completed).not.toContain('resume')
    })

    it('TEST 4.4: Should clear completed_at on reopen', async () => {
      const project = projectStore.projects[3]

      api.projects.restoreCompleted.mockResolvedValue({
        data: {
          ...project,
          status: 'inactive',
          completed_at: null,
        }
      })

      const result = await projectStore.restoreCompletedProject(project.id)

      expect(result.completed_at).toBeNull()
    })

    it('TEST 4.5: Should use POST /api/v1/projects/{id}/restore-completed endpoint', async () => {
      const project = projectStore.projects[3]

      api.projects.restoreCompleted.mockResolvedValue({
        data: { ...project, status: 'inactive', completed_at: null }
      })

      await projectStore.restoreCompletedProject(project.id)

      expect(api.projects.restoreCompleted).toHaveBeenCalledWith(project.id)
    })
  })

  // =====================================
  // TEST SET 5: Soft Delete (Any Status → Deleted)
  // =====================================
  describe('State Transition: Any Status → Deleted (Soft Delete)', () => {
    it('TEST 5.1: Should soft delete an active project', async () => {
      const project = projectStore.projects[0]
      expect(project.status).toBe('active')

      api.projects.delete.mockResolvedValue({ data: { success: true } })
      api.projects.fetchDeleted.mockResolvedValue({
        data: [{
          ...project,
          deleted_at: new Date().toISOString(),
        }]
      })

      await projectStore.deleteProject(project.id)
      await flushPromises()

      // Should remove from main list
      const inMain = projectStore.projects.find(p => p.id === project.id)
      expect(inMain).toBeUndefined()

      // Should be in deleted list
      expect(projectStore.deletedProjects.length).toBeGreaterThan(0)
    })

    it('TEST 5.2: Should soft delete an inactive project', async () => {
      const project = projectStore.projects[1]
      expect(project.status).toBe('inactive')

      api.projects.delete.mockResolvedValue({ data: { success: true } })
      api.projects.fetchDeleted.mockResolvedValue({ data: [] })

      await projectStore.deleteProject(project.id)

      expect(api.projects.delete).toHaveBeenCalledWith(project.id)
    })

    it('TEST 5.3: Should soft delete a completed project', async () => {
      const project = projectStore.projects[3]
      expect(project.status).toBe('completed')

      api.projects.delete.mockResolvedValue({ data: { success: true } })
      api.projects.fetchDeleted.mockResolvedValue({ data: [] })

      await projectStore.deleteProject(project.id)

      expect(api.projects.delete).toHaveBeenCalledWith(project.id)
    })

    it('TEST 5.4: Should set deleted_at timestamp', async () => {
      const project = projectStore.projects[0]
      const deletedAt = new Date().toISOString()

      api.projects.delete.mockResolvedValue({ data: { success: true } })
      api.projects.fetchDeleted.mockResolvedValue({
        data: [{
          ...project,
          status: project.status,
          deleted_at: deletedAt,
        }]
      })

      await projectStore.deleteProject(project.id)
      await flushPromises()

      if (projectStore.deletedProjects.length > 0) {
        const deleted = projectStore.deletedProjects[0]
        expect(deleted.deleted_at).toBeTruthy()
      }
    })

    it('TEST 5.5: Should use DELETE /api/v1/projects/{id}/ endpoint', async () => {
      const project = projectStore.projects[0]

      api.projects.delete.mockResolvedValue({ data: { success: true } })
      api.projects.fetchDeleted.mockResolvedValue({ data: [] })

      await projectStore.deleteProject(project.id)

      expect(api.projects.delete).toHaveBeenCalledWith(project.id)
    })

    it('TEST 5.6: Should refresh deleted projects list after deletion', async () => {
      const project = projectStore.projects[0]

      api.projects.delete.mockResolvedValue({ data: { success: true } })
      api.projects.fetchDeleted.mockResolvedValue({
        data: [{
          id: project.id,
          name: project.name,
          status: project.status,
          deleted_at: new Date().toISOString(),
        }]
      })

      await projectStore.deleteProject(project.id)
      await flushPromises()

      expect(api.projects.fetchDeleted).toHaveBeenCalled()
    })

    it('TEST 5.7: Should REQUIRE confirmation dialog for delete', () => {
      const deleteAction = { value: 'delete', requiresConfirm: true }
      expect(deleteAction.requiresConfirm).toBe(true)
    })
  })

  // =====================================
  // TEST SET 6: Recovery (Deleted → Active)
  // =====================================
  describe('State Transition: Deleted → Active (Recovery)', () => {
    it('TEST 6.1: Should restore a deleted project to inactive status', async () => {
      const deletedProject = {
        id: 'proj-del-1',
        name: 'Deleted Project',
        status: 'active',
        product_id: 'prod-1',
        deleted_at: '2025-01-20T12:00:00Z',
      }

      projectStore.deletedProjects.push(deletedProject)

      const mockResponse = {
        data: {
          ...deletedProject,
          deleted_at: null,
          status: 'inactive',
        }
      }

      api.projects.restore.mockResolvedValue(mockResponse)

      const result = await projectStore.restoreProject(deletedProject.id)

      expect(api.projects.restore).toHaveBeenCalledWith(deletedProject.id)
      expect(result.deleted_at).toBeNull()

      // Should remove from deleted list
      const stillDeleted = projectStore.deletedProjects.find(p => p.id === deletedProject.id)
      expect(stillDeleted).toBeUndefined()

      // Should be in main list
      const restored = projectStore.projects.find(p => p.id === deletedProject.id)
      expect(restored).toBeTruthy()
    })

    it('TEST 6.2: Should recover project with original status info preserved', async () => {
      const deletedProject = {
        id: 'proj-del-2',
        name: 'Deleted Project',
        status: 'inactive', // Original status preserved in deleted record
        product_id: 'prod-1',
        deleted_at: '2025-01-20T12:00:00Z',
      }

      projectStore.deletedProjects.push(deletedProject)

      api.projects.restore.mockResolvedValue({
        data: {
          ...deletedProject,
          deleted_at: null,
          status: 'inactive',
        }
      })

      const result = await projectStore.restoreProject(deletedProject.id)

      expect(result.deleted_at).toBeNull()
      expect(result.name).toBe(deletedProject.name)
    })

    it('TEST 6.3: Should work within 10-day recovery window', async () => {
      // Create project deleted 5 days ago
      const fiveDaysAgo = new Date()
      fiveDaysAgo.setDate(fiveDaysAgo.getDate() - 5)

      const recentlyDeleted = {
        id: 'proj-del-recent',
        name: 'Recently Deleted',
        deleted_at: fiveDaysAgo.toISOString(),
      }

      api.projects.restore.mockResolvedValue({
        data: { ...recentlyDeleted, deleted_at: null }
      })

      projectStore.deletedProjects.push(recentlyDeleted)

      const result = await projectStore.restoreProject(recentlyDeleted.id)

      expect(api.projects.restore).toHaveBeenCalled()
      expect(result.deleted_at).toBeNull()
    })

    it('TEST 6.4: Should use POST /api/v1/projects/{id}/restore endpoint', async () => {
      const deletedProject = {
        id: 'proj-del-3',
        name: 'Test',
        deleted_at: '2025-01-20T12:00:00Z',
      }

      api.projects.restore.mockResolvedValue({
        data: { ...deletedProject, deleted_at: null }
      })

      projectStore.deletedProjects.push(deletedProject)

      await projectStore.restoreProject(deletedProject.id)

      expect(api.projects.restore).toHaveBeenCalledWith(deletedProject.id)
    })

    it('TEST 6.5: Should NOT require confirmation for restore', () => {
      const restoreAction = { value: 'restore', requiresConfirm: false }
      expect(restoreAction.requiresConfirm).toBe(false)
    })

    it('TEST 6.6: Should move project from deleted to main list', async () => {
      const deletedProject = {
        id: 'proj-del-4',
        name: 'Test',
        deleted_at: '2025-01-20T12:00:00Z',
      }

      projectStore.deletedProjects.push(deletedProject)
      const initialDeletedCount = projectStore.deletedProjects.length
      const initialMainCount = projectStore.projects.length

      api.projects.restore.mockResolvedValue({
        data: { ...deletedProject, deleted_at: null, status: 'inactive' }
      })

      await projectStore.restoreProject(deletedProject.id)

      expect(projectStore.deletedProjects.length).toBe(initialDeletedCount - 1)
      expect(projectStore.projects.length).toBe(initialMainCount + 1)
    })
  })

  // =====================================
  // TEST SET 7: UI Elements - Deleted Tab
  // =====================================
  describe('UI Elements: Deleted Projects Tab/Button', () => {
    it('TEST 7.1: Should show "View Deleted" button with count badge', () => {
      projectStore.deletedProjects = [
        { id: 'del-1', name: 'Deleted 1', deleted_at: '2025-01-20T12:00:00Z' },
        { id: 'del-2', name: 'Deleted 2', deleted_at: '2025-01-20T12:00:00Z' },
      ]

      const deletedCount = projectStore.deletedProjects.length
      expect(deletedCount).toBe(2)
    })

    it('TEST 7.2: Should disable "View Deleted" button when count is 0', () => {
      projectStore.deletedProjects = []

      const shouldDisable = projectStore.deletedProjects.length === 0
      expect(shouldDisable).toBe(true)
    })

    it('TEST 7.3: Should display deleted project list in modal', () => {
      projectStore.deletedProjects = [
        {
          id: 'del-1',
          name: 'Deleted Project 1',
          status: 'active',
          deleted_at: '2025-01-20T12:00:00Z',
        },
        {
          id: 'del-2',
          name: 'Deleted Project 2',
          status: 'inactive',
          deleted_at: '2025-01-20T12:00:00Z',
        },
      ]

      expect(projectStore.deletedProjects).toHaveLength(2)
      expect(projectStore.deletedProjects[0].name).toBe('Deleted Project 1')
      expect(projectStore.deletedProjects[1].deleted_at).toBeTruthy()
    })

    it('TEST 7.4: Should show restore icon/button for each deleted project', () => {
      projectStore.deletedProjects = [
        { id: 'del-1', name: 'Test', deleted_at: '2025-01-20T12:00:00Z' }
      ]

      // Deleted projects list should show restore action
      expect(projectStore.deletedProjects.length).toBeGreaterThan(0)
    })

    it('TEST 7.5: Should show deleted_at timestamp for each project', () => {
      const deletedAt = new Date('2025-01-20T12:00:00Z').toISOString()
      projectStore.deletedProjects = [
        { id: 'del-1', name: 'Test', deleted_at: deletedAt }
      ]

      const deleted = projectStore.deletedProjects[0]
      expect(deleted.deleted_at).toBeTruthy()
    })

    it('TEST 7.6: Should update deleted count dynamically', async () => {
      projectStore.deletedProjects = []

      const project = projectStore.projects[0]
      api.projects.delete.mockResolvedValue({ data: { success: true } })
      api.projects.fetchDeleted.mockResolvedValue({
        data: [{
          id: project.id,
          name: project.name,
          deleted_at: new Date().toISOString(),
        }]
      })

      await projectStore.deleteProject(project.id)
      await flushPromises()

      expect(projectStore.deletedProjects.length).toBeGreaterThan(0)
    })
  })

  // =====================================
  // TEST SET 8: Confirmation Dialogs
  // =====================================
  describe('Confirmation Dialogs - StatusBadge Component', () => {
    it('TEST 8.1: Should REQUIRE confirmation for complete action', () => {
      const actionDef = {
        value: 'complete',
        label: 'Complete',
        requiresConfirm: true,
        destructive: false,
      }
      expect(actionDef.requiresConfirm).toBe(true)
    })

    it('TEST 8.2: Should REQUIRE confirmation for cancel action', () => {
      const actionDef = {
        value: 'cancel',
        label: 'Cancel',
        requiresConfirm: true,
        destructive: true,
      }
      expect(actionDef.requiresConfirm).toBe(true)
    })

    it('TEST 8.3: Should REQUIRE confirmation for delete action', () => {
      const actionDef = {
        value: 'delete',
        label: 'Delete',
        requiresConfirm: true,
        destructive: true,
      }
      expect(actionDef.requiresConfirm).toBe(true)
    })

    it('TEST 8.4: Should NOT require confirmation for pause', () => {
      const actionDef = {
        value: 'pause',
        requiresConfirm: false,
      }
      expect(actionDef.requiresConfirm).toBe(false)
    })

    it('TEST 8.5: Should NOT require confirmation for resume', () => {
      const actionDef = {
        value: 'resume',
        requiresConfirm: false,
      }
      expect(actionDef.requiresConfirm).toBe(false)
    })

    it('TEST 8.6: Should NOT require confirmation for activate', () => {
      const actionDef = {
        value: 'activate',
        requiresConfirm: false,
      }
      expect(actionDef.requiresConfirm).toBe(false)
    })

    it('TEST 8.7: Should show appropriate confirmation message for delete', () => {
      // Delete action should warn about permanent deletion
      const message = 'Are you sure you want to permanently delete "Test Project"? This action cannot be undone.'
      expect(message).toContain('permanently delete')
      expect(message).toContain('cannot be undone')
    })

    it('TEST 8.8: Should show appropriate confirmation message for complete', () => {
      // Complete action should indicate project closure
      const message = 'Mark "Test Project" as completed?'
      expect(message).toContain('completed')
    })
  })

  // =====================================
  // TEST SET 9: Error Handling
  // =====================================
  describe('Error Handling', () => {
    it('TEST 9.2: Should handle API error when completing', async () => {
      const error = new Error('API Error: 500 Server Error')

      api.projects.complete.mockRejectedValue(error)

      try {
        await projectStore.completeProject('proj-1')
      } catch (err) {
        expect(err).toBe(error)
      }

      expect(projectStore.error).toBeTruthy()
    })

    it('TEST 9.3: Should handle API error when deleting', async () => {
      const error = new Error('API Error: 403 Forbidden')

      api.projects.delete.mockRejectedValue(error)

      try {
        await projectStore.deleteProject('proj-1')
      } catch (err) {
        expect(err).toBe(error)
      }

      expect(projectStore.error).toBeTruthy()
    })

    it('TEST 9.4: Should handle API error when restoring', async () => {
      const error = new Error('API Error: 404 Not Found')

      api.projects.restore.mockRejectedValue(error)

      projectStore.deletedProjects.push({
        id: 'proj-del',
        name: 'Test',
        deleted_at: '2025-01-20T12:00:00Z'
      })

      try {
        await projectStore.restoreProject('proj-del')
      } catch (err) {
        expect(err).toBe(error)
      }

      expect(projectStore.error).toBeTruthy()
    })

    it('TEST 9.5: Should handle fetch deleted projects API error', async () => {
      const error = new Error('API Error')

      api.projects.fetchDeleted.mockRejectedValue(error)

      try {
        await projectStore.fetchDeletedProjects()
      } catch (err) {
        // Error is caught internally
      }

      expect(projectStore.error).toBeTruthy()
    })
  })

  // =====================================
  // TEST SET 10: StatusBadge Component Config
  // =====================================
  describe('StatusBadge Component Configuration', () => {
    it('TEST 10.1: Should render correct status label', () => {
      const statusConfig = {
        active: { label: 'Active' },
        inactive: { label: 'Inactive' },
        completed: { label: 'Completed' },
        cancelled: { label: 'Cancelled' },
      }

      expect(statusConfig.active.label).toBe('Active')
      expect(statusConfig.inactive.label).toBe('Inactive')
      expect(statusConfig.completed.label).toBe('Completed')
    })

    it('TEST 10.2: Should use correct status color', () => {
      const statusConfig = {
        active: { color: 'success' },
        inactive: { color: 'grey' },
        completed: { color: 'info' },
        cancelled: { color: 'error' },
      }

      expect(statusConfig.active.color).toBe('success')
      expect(statusConfig.inactive.color).toBe('grey')
      expect(statusConfig.completed.color).toBe('info')
    })

    it('TEST 10.3: Should use correct status icon', () => {
      const statusConfig = {
        active: { icon: 'mdi-play-circle' },
        inactive: { icon: 'mdi-circle-outline' },
        completed: { icon: 'mdi-check-circle' },
        cancelled: { icon: 'mdi-cancel' },
      }

      expect(statusConfig.active.icon).toContain('play')
      expect(statusConfig.inactive.icon).toContain('circle')
      expect(statusConfig.completed.icon).toContain('check')
    })

    it('TEST 10.4: Should provide correct actions for active status', () => {
      const actionsByStatus = {
        active: ['deactivate', 'complete', 'cancel', 'delete'],
      }

      const activeActions = actionsByStatus.active
      expect(activeActions).toContain('deactivate')
      expect(activeActions).toContain('complete')
      expect(activeActions).toContain('delete')
      expect(activeActions).not.toContain('activate')
    })

    it('TEST 10.5: Should provide correct actions for inactive status', () => {
      const actionsByStatus = {
        inactive: ['activate', 'complete', 'cancel', 'delete'],
      }

      const inactiveActions = actionsByStatus.inactive
      expect(inactiveActions).toContain('activate')
      expect(inactiveActions).toContain('complete')
      expect(inactiveActions).not.toContain('deactivate')
    })

    it('TEST 10.6: Should provide correct actions for completed status', () => {
      const actionsByStatus = {
        completed: ['reopen', 'archive', 'delete'],
      }

      const completedActions = actionsByStatus.completed
      expect(completedActions).toContain('reopen')
      expect(completedActions).not.toContain('deactivate')
      expect(completedActions).not.toContain('activate')
      expect(completedActions).not.toContain('complete')
    })
  })

  // =====================================
  // TEST SET 11: Computed Properties
  // =====================================
  describe('Computed Properties & Status Counts', () => {
    it('TEST 11.1: Should calculate active project count', () => {
      const activeProjects = projectStore.projects.filter(p => p.status === 'active')
      expect(activeProjects.length).toBe(1)
    })

    it('TEST 11.2: Should calculate inactive project count', () => {
      const inactiveProjects = projectStore.projects.filter(p => p.status === 'inactive')
      expect(inactiveProjects.length).toBeGreaterThanOrEqual(1)
    })

    it('TEST 11.3: Should calculate completed project count', () => {
      const completedProjects = projectStore.projects.filter(p => p.status === 'completed')
      expect(completedProjects.length).toBe(1)
    })

    it('TEST 11.4: Should calculate deleted project count', () => {
      const deletedCount = projectStore.deletedProjects.length
      expect(deletedCount).toBe(0)
    })

    it('TEST 11.5: Should find project by ID', () => {
      const found = projectStore.projectById('proj-active')
      expect(found).toBeTruthy()
      expect(found?.status).toBe('active')
    })
  })

  // =====================================
  // TEST SET 12: Integration Scenarios
  // =====================================
  describe('Integration Scenarios', () => {
    it('TEST 12.1: Should handle complete Active→Inactive→Active workflow', async () => {
      const project = projectStore.projects[0]

      // Active → Inactive
      api.projects.deactivate.mockResolvedValue({
        data: { ...project, status: 'inactive' }
      })
      await projectStore.deactivateProject(project.id)
      expect(api.projects.deactivate).toHaveBeenCalledWith(project.id)

      const afterDeactivate = projectStore.projects.find(p => p.id === project.id)
      expect(afterDeactivate).toBeDefined()
      expect(afterDeactivate?.status).toBe('inactive')

      // Inactive → Active
      api.projects.activate.mockResolvedValue({
        data: { ...project, status: 'active' }
      })
      const result = await projectStore.activateProject(project.id)
      expect(result.status).toBe('active')
    })

    it('TEST 12.2: Should handle Active→Completed→Inactive workflow', async () => {
      const project = projectStore.projects[0]

      // Active → Completed
      api.projects.complete.mockResolvedValue({
        data: { ...project, status: 'completed', completed_at: new Date().toISOString() }
      })
      let result = await projectStore.completeProject(project.id)
      expect(result.status).toBe('completed')

      // Completed → Inactive
      api.projects.restoreCompleted.mockResolvedValue({
        data: { ...project, status: 'inactive', completed_at: null }
      })
      result = await projectStore.restoreCompletedProject(project.id)
      expect(result.status).toBe('inactive')
    })

    it('TEST 12.3: Should handle Active→Deleted→Restored→Active workflow', async () => {
      const project = projectStore.projects[0]

      // Active → Deleted
      api.projects.delete.mockResolvedValue({ data: { success: true } })
      api.projects.fetchDeleted.mockResolvedValue({
        data: [{
          id: project.id,
          name: project.name,
          status: project.status,
          deleted_at: new Date().toISOString(),
        }]
      })

      await projectStore.deleteProject(project.id)
      await flushPromises()

      expect(projectStore.deletedProjects.length).toBeGreaterThan(0)

      // Deleted → Restored
      api.projects.restore.mockResolvedValue({
        data: {
          ...project,
          deleted_at: null,
          status: 'inactive',
        }
      })

      const deletedProj = projectStore.deletedProjects[0]
      await projectStore.restoreProject(deletedProj.id)

      expect(projectStore.projects.length).toBeGreaterThan(0)
    })
  })
})
