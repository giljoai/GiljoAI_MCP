import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useProjectStore } from '@/stores/projects'

// Mock the api module used by the store
vi.mock('@/services/api', () => ({
  api: {
    projects: {
      list: vi.fn().mockResolvedValue({ data: [] }),
    },
  },
}))

describe('projects store — handleRealtimeUpdate', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useProjectStore()
    // Seed with a known project
    store.projects = [
      {
        id: 'proj-1',
        name: 'Original Name',
        description: 'Original description',
        status: 'active',
        mission: 'Original mission',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ]
  })

  it('handles update_type "updated" — patches name, description, status, mission', () => {
    store.handleRealtimeUpdate({
      project_id: 'proj-1',
      update_type: 'updated',
      name: 'New Name',
      description: 'New description',
      status: 'inactive',
      mission: 'New mission',
    })

    const project = store.projects[0]
    expect(project.name).toBe('New Name')
    expect(project.description).toBe('New description')
    expect(project.status).toBe('inactive')
    expect(project.mission).toBe('New mission')
  })

  it('handles update_type "updated" — partial update (only name)', () => {
    store.handleRealtimeUpdate({
      project_id: 'proj-1',
      update_type: 'updated',
      name: 'Renamed',
    })

    const project = store.projects[0]
    expect(project.name).toBe('Renamed')
    // Other fields unchanged
    expect(project.description).toBe('Original description')
    expect(project.status).toBe('active')
    expect(project.mission).toBe('Original mission')
  })

  it('handles update_type "updated" — clears mission when set to empty string', () => {
    store.handleRealtimeUpdate({
      project_id: 'proj-1',
      update_type: 'updated',
      mission: '',
    })

    const project = store.projects[0]
    expect(project.mission).toBe('')
  })

  it('handles update_type "closed" — sets status to closed', () => {
    store.handleRealtimeUpdate({
      project_id: 'proj-1',
      update_type: 'closed',
    })

    expect(store.projects[0].status).toBe('closed')
  })

  it('handles update_type "activated" — sets status to active', () => {
    store.projects[0].status = 'inactive'
    store.handleRealtimeUpdate({
      project_id: 'proj-1',
      update_type: 'activated',
    })

    expect(store.projects[0].status).toBe('active')
  })

  it('handles update_type "deactivated" — sets status to inactive', () => {
    store.handleRealtimeUpdate({
      project_id: 'proj-1',
      update_type: 'deactivated',
    })

    expect(store.projects[0].status).toBe('inactive')
  })

  it('handles update_type "created" — adds new project to list', () => {
    store.handleRealtimeUpdate({
      project_id: 'proj-new',
      update_type: 'created',
      name: 'New Project',
      status: 'active',
      mission: 'Go',
    })

    expect(store.projects).toHaveLength(2)
    expect(store.projects[1].id).toBe('proj-new')
    expect(store.projects[1].name).toBe('New Project')
  })

  it('updates updated_at timestamp on any known-project update', () => {
    const before = store.projects[0].updated_at
    store.handleRealtimeUpdate({
      project_id: 'proj-1',
      update_type: 'updated',
      name: 'Touched',
    })

    expect(store.projects[0].updated_at).not.toBe(before)
  })

  it('ignores "updated" event for unknown project_id and triggers fetchProjects', () => {
    // Unknown project_id should not crash and should not add a project inline
    store.handleRealtimeUpdate({
      project_id: 'proj-unknown',
      update_type: 'updated',
      name: 'Ghost',
    })

    // Should still only have the original project
    expect(store.projects).toHaveLength(1)
    expect(store.projects[0].id).toBe('proj-1')
  })

  it('handles "status_changed" update_type with explicit status', () => {
    store.handleRealtimeUpdate({
      project_id: 'proj-1',
      update_type: 'status_changed',
      status: 'completed',
    })

    expect(store.projects[0].status).toBe('completed')
  })

  it('does not duplicate project when "created" event arrives for existing project_id', () => {
    store.handleRealtimeUpdate({
      project_id: 'proj-1',
      update_type: 'created',
      name: 'Duplicate Attempt',
      status: 'active',
    })

    // Should still be length 1, not duplicated
    expect(store.projects).toHaveLength(1)
  })

  it('handles "updated" event with only description change', () => {
    store.handleRealtimeUpdate({
      project_id: 'proj-1',
      update_type: 'updated',
      description: 'New description only',
    })

    const project = store.projects[0]
    expect(project.description).toBe('New description only')
    // Other fields unchanged
    expect(project.name).toBe('Original Name')
    expect(project.status).toBe('active')
  })
})
