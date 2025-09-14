import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { API_CONFIG } from '@/config/api'

export const useProjectStore = defineStore('projects', () => {
  // State
  const projects = ref([])
  const currentProject = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const activeProjects = computed(() => 
    projects.value.filter(p => p.status === 'active')
  )
  
  const projectById = computed(() => (id) =>
    projects.value.find(p => p.id === id)
  )

  // Actions
  async function fetchProjects() {
    loading.value = true
    error.value = null
    try {
      const response = await axios.get(
        API_CONFIG.ENDPOINTS.projects,
        { baseURL: API_CONFIG.REST_API.baseURL }
      )
      projects.value = response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch projects:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(id) {
    loading.value = true
    error.value = null
    try {
      const url = API_CONFIG.ENDPOINTS.project.replace(':id', id)
      const response = await axios.get(url, {
        baseURL: API_CONFIG.REST_API.baseURL
      })
      currentProject.value = response.data
      
      // Update in list if exists
      const index = projects.value.findIndex(p => p.id === id)
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
      const response = await axios.post(
        API_CONFIG.ENDPOINTS.projects,
        projectData,
        { baseURL: API_CONFIG.REST_API.baseURL }
      )
      projects.value.push(response.data)
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
      const url = API_CONFIG.ENDPOINTS.project.replace(':id', id)
      const response = await axios.put(url, updates, {
        baseURL: API_CONFIG.REST_API.baseURL
      })
      
      const index = projects.value.findIndex(p => p.id === id)
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
      const url = API_CONFIG.ENDPOINTS.project.replace(':id', id)
      await axios.delete(url, {
        baseURL: API_CONFIG.REST_API.baseURL
      })
      
      projects.value = projects.value.filter(p => p.id !== id)
      
      if (currentProject.value?.id === id) {
        currentProject.value = null
      }
    } catch (err) {
      error.value = err.message
      console.error('Failed to delete project:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  return {
    // State
    projects,
    currentProject,
    loading,
    error,
    
    // Getters
    activeProjects,
    projectById,
    
    // Actions
    fetchProjects,
    fetchProject,
    createProject,
    updateProject,
    deleteProject,
    clearError
  }
})