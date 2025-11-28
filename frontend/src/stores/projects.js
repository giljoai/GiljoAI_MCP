import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/services/api'

export const useProjectStore = defineStore('projects', () => {
  // State
  const projects = ref([])
  const deletedProjects = ref([])
  const currentProject = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const activeProjects = computed(() => projects.value.filter((p) => p.status === 'active'))

  const projectById = computed(() => (id) => projects.value.find((p) => p.id === id))

  // Actions
  async function fetchProjects() {
    loading.value = true
    error.value = null
    try {
      const response = await api.projects.list()
      projects.value = response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch projects:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchDeletedProjects() {
    loading.value = true
    error.value = null
    try {
      const response = await api.projects.fetchDeleted()
      deletedProjects.value = response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch deleted projects:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(id) {
    loading.value = true
    error.value = null
    try {
      const response = await api.projects.get(id)
      currentProject.value = response.data

      // Update in list if exists
      const index = projects.value.findIndex((p) => p.id === id)
      if (index !== -1) {
        projects.value[index] = response.data
      }
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch project:', err)
    } finally {
      loading.value = false
    }
  }

  async function createProject(projectData) {
    loading.value = true
    error.value = null
    try {
      const response = await api.projects.create(projectData)

      // CRITICAL: Refresh from backend to get actual status
      // Backend may auto-activate project (Single Active Project constraint)
      // or modify other fields. Don't trust local request data.
      await fetchProjects()

      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to create project:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateProject(id, updates) {
    loading.value = true
    error.value = null
    try {
      const response = await api.projects.update(id, updates)

      const index = projects.value.findIndex((p) => p.id === id)
      if (index !== -1) {
        projects.value[index] = response.data
      }

      if (currentProject.value?.id === id) {
        currentProject.value = response.data
      }

      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to update project:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteProject(id) {
    loading.value = true
    error.value = null
    try {
      await api.projects.delete(id)

      projects.value = projects.value.filter((p) => p.id !== id)

      if (currentProject.value?.id === id) {
        currentProject.value = null
      }

      // Refresh deleted projects list after deletion
      await fetchDeletedProjects()
    } catch (err) {
      error.value = err.message
      console.error('Failed to delete project:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function activateProject(id) {
    loading.value = true
    error.value = null
    try {
      const response = await api.projects.changeStatus(id, 'active')

      const index = projects.value.findIndex((p) => p.id === id)
      if (index !== -1) {
        projects.value[index] = response.data
      }

      if (currentProject.value?.id === id) {
        currentProject.value = response.data
      }

      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to activate project:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // Handover 0062: Activate project
  async function activateProject(id) {
    loading.value = true
    error.value = null
    // Optimistic update with rollback on failure
    const index = projects.value.findIndex((p) => p.id === id)
    const previous = index !== -1 ? { ...projects.value[index] } : null
    if (index !== -1) {
      projects.value[index] = {
        ...projects.value[index],
        status: 'active',
        updated_at: new Date().toISOString(),
      }
    }
    try {
      const response = await api.projects.activate(id)
      // Sync with server state
      await fetchProjects()
      return response.data
    } catch (err) {
      // Roll back optimistic update
      if (index !== -1 && previous) {
        projects.value[index] = previous
      }
      error.value = err.message || 'Failed to activate project'
      console.error('Failed to activate project:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deactivateProject(id) {
    loading.value = true
    error.value = null
    // Optimistic update with rollback on failure
    const index = projects.value.findIndex((p) => p.id === id)
    const previous = index !== -1 ? { ...projects.value[index] } : null
    if (index !== -1) {
      projects.value[index] = {
        ...projects.value[index],
        status: 'inactive',
        updated_at: new Date().toISOString(),
      }
    }
    try {
      await api.projects.deactivate(id)
      // Sync with server state
      await fetchProjects()
    } catch (err) {
      // Roll back optimistic update
      if (index !== -1 && previous) {
        projects.value[index] = previous
      }
      error.value = err.message || 'Failed to deactivate project'
      console.error('Failed to deactivate project:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function completeProject(id) {
    loading.value = true
    error.value = null
    try {
      const response = await api.projects.complete(id)

      const index = projects.value.findIndex((p) => p.id === id)
      if (index !== -1) {
        projects.value[index] = response.data
      }

      if (currentProject.value?.id === id) {
        currentProject.value = response.data
      }

      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to complete project:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function cancelProject(id) {
    loading.value = true
    error.value = null
    try {
      const response = await api.projects.cancel(id)

      const index = projects.value.findIndex((p) => p.id === id)
      if (index !== -1) {
        projects.value[index] = response.data
      }

      if (currentProject.value?.id === id) {
        currentProject.value = response.data
      }

      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to cancel project:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function restoreProject(id) {
    loading.value = true
    error.value = null
    try {
      const response = await api.projects.restore(id)

      // Remove from deleted projects list
      deletedProjects.value = deletedProjects.value.filter((p) => p.id !== id)

      // Add to active projects list
      projects.value.push(response.data)

      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to restore project:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function purgeDeletedProject(id) {
    loading.value = true
    error.value = null
    try {
      await api.projects.purgeDeleted(id)
      deletedProjects.value = deletedProjects.value.filter((p) => p.id !== id)
      await fetchDeletedProjects()
    } catch (err) {
      error.value = err.message
      console.error('Failed to purge deleted project:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function purgeAllDeletedProjects() {
    loading.value = true
    error.value = null
    try {
      await api.projects.purgeAllDeleted()
      deletedProjects.value = []
      await fetchDeletedProjects()
    } catch (err) {
      error.value = err.message
      console.error('Failed to purge all deleted projects:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function restoreCompletedProject(id) {
    loading.value = true
    error.value = null
    try {
      const response = await api.projects.restoreCompleted(id)

      const index = projects.value.findIndex((p) => p.id === id)
      if (index !== -1) {
        projects.value[index] = response.data
      }

      if (currentProject.value?.id === id) {
        currentProject.value = response.data
      }

      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to restore completed project:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  // Handle real-time updates from WebSocket
  function handleRealtimeUpdate(data) {
    const { project_id, update_type, name, status, mission, context_used, context_budget } = data

    // Find project by ID
    const projectIndex = projects.value.findIndex((p) => p.id === project_id)

    if (update_type === 'created' && projectIndex === -1) {
      // New project - add to list
      projects.value.push({
        id: project_id,
        name,
        status,
        mission,
        context_used: context_used || 0,
        context_budget: context_budget || 150000,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
    } else if (projectIndex !== -1) {
      // Update existing project
      const project = projects.value[projectIndex]

      if (update_type === 'closed') {
        project.status = 'closed'
      } else if (
        update_type === 'status_changed' ||
        update_type === 'activated' ||
        update_type === 'deactivated'
      ) {
        // Handle status changes including activation/deactivation
        if (status) {
          project.status = status
        } else if (update_type === 'activated') {
          project.status = 'active'
        } else if (update_type === 'deactivated') {
          project.status = 'inactive'
        }
      }

      // Update other fields if provided
      if (name) {
        project.name = name
      }
      if (mission) {
        project.mission = mission
      }
      if (context_used !== undefined) {
        project.context_used = context_used
      }
      if (context_budget !== undefined) {
        project.context_budget = context_budget
      }

      project.updated_at = new Date().toISOString()

      // Update current project if it's the same
      if (currentProject.value?.id === project_id) {
        currentProject.value = { ...project }
      }
    } else if (project_id) {
      // Unknown project - fetch updated list
      fetchProjects()
    }
  }

  return {
    // State
    projects,
    deletedProjects,
    currentProject,
    loading,
    error,

    // Getters
    activeProjects,
    projectById,

    // Actions
    fetchProjects,
    fetchDeletedProjects,
    fetchProject,
    createProject,
    updateProject,
    deleteProject,
    activateProject,
    deactivateProject,
    completeProject,
    cancelProject,
    restoreProject,
    restoreCompletedProject,
    purgeDeletedProject,
    purgeAllDeletedProjects,
    clearError,
    handleRealtimeUpdate,
  }
})
