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
  // CE-0029 Item 3: implementation_launched derives from the API field
  // implementation_launched_at, which CE-0028b added to ProjectResponse /
  // ProjectListItem. After Implement-click the launch_implementation
  // endpoint also fires project:implementation_launched, which patches the
  // boolean+timestamp directly via setImplementationLaunched().
  const implLaunchedAt = project?.implementationLaunchedAt || project?.implementation_launched_at || null
  return {
    project_id: projectId,
    mission: project?.mission || '',
    status: project?.status || null,
    execution_mode: project?.execution_mode || null,
    stagingComplete: Boolean(project?.stagingComplete) || ss === 'staging_complete' || false,
    isStaged: Boolean(project?.isStaged) || ss === 'staged' || false,
    isStaging: Boolean(project?.isStaging) || ss === 'staging' || false,
    isLaunched: Boolean(project?.isLaunched) || false,
    implementationLaunched: Boolean(project?.implementationLaunched) || Boolean(implLaunchedAt) || false,
    implementationLaunchedAt: implLaunchedAt,
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
        implementationLaunched: false,
        implementationLaunchedAt: null,
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

    let next
    if (previous) {
      // Apply normalized OVER previous (picks up new mission, status, mode, etc.)
      const patched = immutableObjectPatch(previous, normalized)

      // FE-6061: monotonic flags — once set true by a WS event (setStagingComplete,
      // handleImplementationLaunched) they must NOT revert to false when setProject
      // is called with a stale or thin entity snapshot (e.g. a list-wire row where
      // crud.py hardcodes implementation_launched_at=None, or a 'staged' entity
      // arriving after setStagingComplete already fired from loaded messages).
      // Explicit clears (restageProject / unstageProject) go through
      // upsertProjectState directly and bypass this guard — they still work.
      next = {
        ...patched,
        stagingComplete: previous.stagingComplete || normalized.stagingComplete,
        implementationLaunched: previous.implementationLaunched || normalized.implementationLaunched,
        // Preserve the timestamp whenever either side carries it
        implementationLaunchedAt: previous.implementationLaunchedAt || normalized.implementationLaunchedAt,
        // FE-9122: setProject now also runs on every project_update refetch
        // (the projects.js _upsertEntity bridge). normalizeProjectState
        // defaults isLaunched:false (API entities don't carry it), so without
        // this a background refetch would clobber a true isLaunched.
        isLaunched: previous.isLaunched || normalized.isLaunched,
      }
    } else {
      next = normalized
    }

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

  // CE-0029 Item 3: WS-driven mirror of mark_staging_complete's
  // setStagingComplete. The launch_implementation endpoint emits
  // project:implementation_launched with the timestamp; this action and the
  // handler below patch the store so children reading the reactive state
  // see the transition without waiting on the next API fetch.
  //
  // TSK-6254: the broadcast also carries an authoritative source tag
  // ("mcp" = headless MCP drive | "ui" = dashboard Implement click | absent =
  // older backend). We surface it as lastLaunchSource so useChainAutoNav can
  // gate the same-project auto-nav flip on the drive origin (follow "mcp", stay
  // on "ui") instead of relying only on the client-side anti-hijack window.
  function setImplementationLaunched(projectId, timestamp, source = null) {
    upsertProjectState(projectId, {
      implementationLaunched: Boolean(timestamp),
      implementationLaunchedAt: timestamp || null,
      lastLaunchSource: source || null,
    })
  }

  async function restageProject(projectId) {
    const resolved = resolveProjectId(projectId)
    if (!resolved) return

    // BE-6047: await before patching so a 409 (impl already launched) leaves state intact
    await api.projects.restage(resolved)
    upsertProjectState(resolved, {
      isStaged: false,
      isStaging: false,
      stagingComplete: false,
      // Clear mission so isExecutionModeLocked releases (backend sets mission="" on restage)
      mission: '',
      // Backend clears implementation_launched_at on restage — mirror it
      implementationLaunched: false,
      implementationLaunchedAt: null,
    })
  }

  async function unstageProject(projectId) {
    const resolved = resolveProjectId(projectId)
    if (!resolved) return

    // BE-6047: await before patching so errors leave state intact
    await api.projects.unstage(resolved)
    upsertProjectState(resolved, {
      isStaged: false,
      isStaging: false,
      // Clear mission so isExecutionModeLocked releases (backend sets mission="" on unstage)
      mission: '',
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

  // Handover 0826: Server-side staging completion signal
  function handleStagingComplete(payload) {
    const projectId = payload?.project_id
    if (!projectId) return
    setStagingComplete(projectId, true)
  }

  // CE-0029 Item 3: Symmetric handler for the launch_implementation WS event.
  // TSK-6254: capture payload.source ("mcp"|"ui"|absent) from the broadcast so
  // the auto-nav composable can distinguish a headless drive from a user click.
  function handleImplementationLaunched(payload) {
    const projectId = payload?.project_id
    if (!projectId) return
    setImplementationLaunched(projectId, payload?.implementation_launched_at || null, payload?.source || null)
  }

  function $reset() {
    stateByProjectId.value = new Map()
  }

  return {
    // state
    stateByProjectId,

    // selectors
    getProjectState,

    // actions
    setProject,
    setStagingComplete,
    setMission,
    setIsStaged,
    setIsStaging,
    setLaunched,
    setImplementationLaunched,
    restageProject,
    unstageProject,

    // ws handlers
    handleMissionUpdated,
    handleStagingComplete,
    handleImplementationLaunched,

    // lifecycle
    $reset,
  }
})
