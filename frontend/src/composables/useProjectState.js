import api from '@/services/api'
import { useProjectStateStore } from '@/stores/projectStateStore'

export function useProjectState() {
  const store = useProjectStateStore()

  async function refreshProject(projectId) {
    if (!projectId) return null
    const response = await api.projects.get(projectId)
    store.setProject(response?.data)
    return response?.data || null
  }

  return {
    store,
    refreshProject,
  }
}
