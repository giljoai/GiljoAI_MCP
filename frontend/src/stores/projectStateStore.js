import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { immutableMapSet, immutableObjectPatch } from './immutableHelpers'
import api from '@/services/api'

function resolveProjectId(value) {
  if (!value) return null
  if (typeof value === 'string') return value
  return value.id || value.project_id || null
}

function normalizeProjectState(project) {
  const projectId = resolveProjectId(project)
  if (!projectId) return null

  const ss = project?.staging_status
  return {
    project_id: projectId,
    mission: project?.mission || '',
    status: project?.status || null,
    execution_mode: project?.execution_mode || null,
    stagingComplete: Boolean(project?.stagingComplete) || ss === 'staging_complete' || false,
    isStaged: Boolean(project?.isStaged) || ss === 'staged' || false,
    isStaging: Boolean(project?.isStaging) || ss === 'staging' || false,
    isLaunched: Boolean(project?.isLaunched) || false,
  }
}

export const useProjectStateStore = defineStore('projectStateDomain', () => {
  const stateByProjectId = ref(new Map())

  // Fix: Reactive array for Map contents - enables Vue reactivity for computed properties
  // Vue 3 doesn't deeply track Map.get() calls, but does track Array.from() iterations
  const allProjects = computed(() => Array.from(stateByProjectId.value.values()))

  function getProjectState(projectId) {
    const resolved = resolveProjectId(projectId)
    if (!resolved) return null
    // Fix: Use computed array instead of Map.get() for proper Vue reactivity
    return allProjects.value.find((p) => p.project_id === resolved) || null
  }

  function upsertProjectState(projectId, patch) {
    const resolved = resolveProjectId(projectId)
    if (!resolved) return

    const previous = stateByProjectId.value.get(resolved)
    const base =
      previous ||
      normalizeProjectState({ id: resolved }) || {
        project_id: resolved,
        mission: '',
        status: null,
        execution_mode: null,
        stagingComplete: false,
        isStaged: false,
        isStaging: false,
        isLaunched: false,
      }

    const next = immutableObjectPatch(base, patch)

    if (previous && JSON.stringify(previous) === JSON.stringify(next)) {
      return
    }

    stateByProjectId.value = immutableMapSet(stateByProjectId.value, resolved, next)
  }

  function setProject(project) {
    const normalized = normalizeProjectState(project)
    if (!normalized) return

    const previous = stateByProjectId.value.get(normalized.project_id)
    const next = previous ? immutableObjectPatch(previous, normalized) : normalized

    stateByProjectId.value = immutableMapSet(stateByProjectId.value, normalized.project_id, next)
  }

  function setStagingComplete(projectId, complete = true) {
    const patch = { stagingComplete: Boolean(complete) }
    if (complete) patch.isStaging = false
    upsertProjectState(projectId, patch)
  }

  function setMission(projectId, mission) {
    upsertProjectState(projectId, { mission: mission || '' })
  }

  function setIsStaged(projectId, isStaged) {
    upsertProjectState(projectId, { isStaged: Boolean(isStaged) })
  }

  function setIsStaging(projectId, isStaging) {
    upsertProjectState(projectId, { isStaging: Boolean(isStaging) })
  }

  function setLaunched(projectId, isLaunched) {
    upsertProjectState(projectId, { isLaunched: Boolean(isLaunched) })
  }

  async function restageProject(projectId) {
    const resolved = resolveProjectId(projectId)
    if (!resolved) return

    await api.projects.restage(resolved)
    upsertProjectState(resolved, {
      isStaged: false,
      isStaging: false,
      stagingComplete: false,
    })
  }

  async function unstageProject(projectId) {
    const resolved = resolveProjectId(projectId)
    if (!resolved) return

    await api.projects.unstage(resolved)
    upsertProjectState(resolved, {
      isStaged: false,
      isStaging: false,
    })
  }

  // =========================
  // WebSocket event handlers
  // =========================

  function handleMissionUpdated(payload) {
    const projectId = payload?.project_id || payload?.id
    if (!projectId) return
    setMission(projectId, payload?.mission || '')
    // Mission written = agent made first contact → move from staged to staging (irreversible)
    if (payload?.mission) {
      upsertProjectState(projectId, { isStaged: false, isStaging: true })
    }
  }

  function handleMessageSent(payload) {
    const projectId = payload?.project_id
    if (!projectId) return

    // Handover 0291: Staging completion signal is the first broadcast message.
    if (payload?.message_type !== 'broadcast') {
      return
    }

    setStagingComplete(projectId, true)
  }

  // Handover 0826: Server-side staging completion signal
  function handleStagingComplete(payload) {
    const projectId = payload?.project_id
    if (!projectId) return
    setStagingComplete(projectId, true)
  }

  function handleMessageReceived(payload) {
    const projectId = payload?.project_id
    if (!projectId) return

    // Any received message implies staging is done (agents have been spawned).
    setStagingComplete(projectId, true)
  }

  function $reset() {
    stateByProjectId.value = new Map()
  }

  return {
    // state
    stateByProjectId,

    // getters
    allProjects, // Fix: Export for reactive access

    // selectors
    getProjectState,

    // actions
    setProject,
    setStagingComplete,
    setMission,
    setIsStaged,
    setIsStaging,
    setLaunched,
    restageProject,
    unstageProject,

    // ws handlers
    handleMissionUpdated,
    handleStagingComplete,
    handleMessageSent,
    handleMessageReceived,

    // lifecycle
    $reset,
  }
})
