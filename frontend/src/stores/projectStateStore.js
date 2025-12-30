import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { immutableMapSet, immutableObjectPatch } from './immutableHelpers'

function resolveProjectId(value) {
  if (!value) return null
  if (typeof value === 'string') return value
  return value.id || value.project_id || null
}

function normalizeProjectState(project) {
  const projectId = resolveProjectId(project)
  if (!projectId) return null

  return {
    project_id: projectId,
    mission: project?.mission || '',
    status: project?.status || null,
    execution_mode: project?.execution_mode || null,
    stagingComplete: Boolean(project?.stagingComplete) || false,
    isStaging: Boolean(project?.isStaging) || false,
    isLaunched: Boolean(project?.isLaunched) || false,
  }
}

export const useProjectStateStore = defineStore('projectStateDomain', () => {
  const stateByProjectId = ref(new Map())

  const projectCount = computed(() => stateByProjectId.value.size)

  function getProjectState(projectId) {
    const resolved = resolveProjectId(projectId)
    if (!resolved) return null
    return stateByProjectId.value.get(resolved) || null
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
    upsertProjectState(projectId, { stagingComplete: Boolean(complete) })
  }

  function setMission(projectId, mission) {
    upsertProjectState(projectId, { mission: mission || '' })
  }

  function setIsStaging(projectId, isStaging) {
    upsertProjectState(projectId, { isStaging: Boolean(isStaging) })
  }

  function setLaunched(projectId, isLaunched) {
    upsertProjectState(projectId, { isLaunched: Boolean(isLaunched) })
  }

  // =========================
  // WebSocket event handlers
  // =========================

  function handleMissionUpdated(payload) {
    const projectId = payload?.project_id || payload?.id
    if (!projectId) return
    setMission(projectId, payload?.mission || '')
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
    projectCount,

    // selectors
    getProjectState,

    // actions
    setProject,
    setStagingComplete,
    setMission,
    setIsStaging,
    setLaunched,

    // ws handlers
    handleMissionUpdated,
    handleMessageSent,
    handleMessageReceived,

    // lifecycle
    $reset,
  }
})
