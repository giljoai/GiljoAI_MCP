import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

function ensureArray(value) {
  return Array.isArray(value) ? value : []
}

function normalizeJob(rawJob) {
  return {
    ...rawJob,
    job_id: rawJob?.job_id || rawJob?.id || rawJob?.agent_id,
    messages_sent_count: rawJob?.messages_sent_count ?? 0,
    messages_waiting_count: rawJob?.messages_waiting_count ?? 0,
    messages_read_count: rawJob?.messages_read_count ?? 0,
  }
}

function createNextMapWith(map, key, value) {
  const next = new Map(map)
  next.set(key, value)
  return next
}

function createNextMapWithout(map, key) {
  const next = new Map(map)
  next.delete(key)
  return next
}

export const useAgentJobsStore = defineStore('agentJobsDomain', () => {
  const jobsById = ref(new Map())

  const jobCount = computed(() => jobsById.value.size)

  const jobs = computed(() => Array.from(jobsById.value.values()))

  const sortedJobs = computed(() => {
    // Sort order: Working (top) -> Failed -> Blocked -> Waiting -> Completed (bottom)
    const priority = {
      working: 1,
      failed: 2,
      blocked: 3,
      waiting: 4,
      complete: 5,
      completed: 5,  // alias
      cancelled: 6,
      decommissioned: 7,
    }

    const list = Array.from(jobsById.value.values())
    list.sort((a, b) => {
      const aPriority = priority[a.status] || 999
      const bPriority = priority[b.status] || 999

      if (aPriority !== bPriority) return aPriority - bPriority

      // Within same status group, apply timestamp-based sorting
      if (a.status === 'working' && b.status === 'working') {
        // Working: most recently started on top (descending by started_at)
        const aStarted = a.started_at ? new Date(a.started_at).getTime() : 0
        const bStarted = b.started_at ? new Date(b.started_at).getTime() : 0
        if (aStarted !== bStarted) return bStarted - aStarted  // descending
      }

      if ((a.status === 'complete' || a.status === 'completed') &&
          (b.status === 'complete' || b.status === 'completed')) {
        // Completed: most recently completed on top (descending by completed_at)
        const aCompleted = a.completed_at ? new Date(a.completed_at).getTime() : 0
        const bCompleted = b.completed_at ? new Date(b.completed_at).getTime() : 0
        if (aCompleted !== bCompleted) return bCompleted - aCompleted  // descending
      }

      // Orchestrators first within same status/timestamp
      const aIsOrchestrator = a.agent_display_name === 'orchestrator' ? 0 : 1
      const bIsOrchestrator = b.agent_display_name === 'orchestrator' ? 0 : 1
      if (aIsOrchestrator !== bIsOrchestrator) return aIsOrchestrator - bIsOrchestrator

      return (a.agent_display_name || '').localeCompare(b.agent_display_name || '')
    })

    return list
  })

  function getJob(jobId) {
    if (!jobId) return null
    return jobsById.value.get(jobId) || null
  }

  function setJobs(rows = []) {
    const next = new Map()
    for (const rawJob of ensureArray(rows)) {
      const job = normalizeJob(rawJob)
      if (!job.job_id) continue
      next.set(job.job_id, job)
    }
    jobsById.value = next
  }

  function upsertJob(patch) {
    const jobId = patch?.job_id || patch?.id || patch?.agent_id
    if (!jobId) return

    // Handover 0388: Filter undefined values to prevent state corruption
    // Spread operator preserves undefined, which overwrites existing valid data
    const cleanPatch = Object.fromEntries(
      Object.entries(patch || {}).filter(([_, v]) => v !== undefined)
    )

    const previous = jobsById.value.get(jobId)
    const nextJob = normalizeJob({ ...(previous || {}), ...cleanPatch, job_id: jobId })

    // Avoid unnecessary churn if nothing changed.
    if (previous && JSON.stringify(previous) === JSON.stringify(nextJob)) {
      return
    }

    jobsById.value = createNextMapWith(jobsById.value, jobId, nextJob)
  }

  function removeJob(jobId) {
    if (!jobId || !jobsById.value.has(jobId)) return
    jobsById.value = createNextMapWithout(jobsById.value, jobId)
  }

  // =========================
  // WebSocket event handlers
  // =========================

  function handleCreated(payload) {
    upsertJob(payload)
  }

  function handleUpdated(payload) {
    upsertJob(payload)
  }

  function handleStatusChanged(payload) {
    upsertJob(payload)
  }

  function handleMissionAcknowledged(payload) {
    if (!payload?.job_id) return
    upsertJob({
      job_id: payload.job_id,
      mission_acknowledged_at: payload.mission_acknowledged_at,
    })
  }

  // Handover 0386: Handle progress updates from job:progress_update WebSocket events
  // Progress is now sent directly via WebSocket, NOT via message system
  // Handover 0388: Conditionally build updates to prevent undefined corruption
  // Handover 0401: Transform todo_steps array to steps summary object
  // Handover 0402: Store todo_items for Plan/TODOs tab display
  function handleProgressUpdate(payload) {
    if (!payload?.job_id) return

    const updates = {
      job_id: payload.job_id,
      progress: payload.progress,
      current_task: payload.current_task,
      last_progress_at: payload.last_progress_at,
    }

    // Only add job_metadata when todo_steps exists (prevents undefined overwrite)
    // Handover 0401: Handle both object format { total_steps, completed_steps }
    // and array format [{ status: 'done' }, ...]
    if (payload.todo_steps) {
      updates.job_metadata = { todo_steps: payload.todo_steps }

      if (Array.isArray(payload.todo_steps)) {
        // Array format: count completed vs total
        const completed = payload.todo_steps.filter(
          (s) => s.status === 'done' || s.status === 'completed'
        ).length
        updates.steps = {
          completed,
          total: payload.todo_steps.length,
        }
      } else if (typeof payload.todo_steps === 'object') {
        // Object format from backend: { total_steps, completed_steps }
        const total = payload.todo_steps.total_steps
        const completed = payload.todo_steps.completed_steps
        if (typeof total === 'number' && typeof completed === 'number') {
          updates.steps = { completed, total }
        }
      }
    }

    // Handover 0402: Store todo_items array for display in Plan/TODOs tab
    // Backend sends: [{ content: "...", status: "pending|in_progress|completed" }, ...]
    if (payload.todo_items && Array.isArray(payload.todo_items)) {
      updates.todo_items = payload.todo_items
    }

    upsertJob(updates)
  }

  function resolveJobId(identifier) {
    if (!identifier) return null

    if (jobsById.value.has(identifier)) {
      return identifier
    }

    // Check by agent_id (executor UUID from messaging)
    for (const job of jobsById.value.values()) {
      if (job.agent_id === identifier) {
        return job.job_id
      }
    }

    // Legacy fallback: from_agent may be agent_display_name (e.g., "orchestrator").
    for (const job of jobsById.value.values()) {
      if (job.agent_display_name === identifier || job.agent_name === identifier) {
        return job.job_id
      }
    }

    return null
  }

  function handleMessageSent(payload) {
    const senderId = resolveJobId(payload?.from_agent)
    if (!senderId) return

    const previous = jobsById.value.get(senderId)
    if (!previous) return

    // Use server-provided counter from WebSocket event
    upsertJob({
      job_id: senderId,
      messages_sent_count: payload.sender_sent_count ?? (previous.messages_sent_count || 0) + 1,
    })

    // Also update recipient's waiting count if provided
    const recipientIdentifier = payload?.to_agent_ids?.[0]
    if (recipientIdentifier) {
      const recipientId = resolveJobId(recipientIdentifier)
      if (recipientId) {
        const recipientPrevious = jobsById.value.get(recipientId)
        if (recipientPrevious) {
          upsertJob({
            job_id: recipientId,
            messages_waiting_count: payload.recipient_waiting_count ?? (recipientPrevious.messages_waiting_count || 0) + 1,
          })
        }
      }
    }
  }

  function handleMessageReceived(payload) {
    const recipientIds = ensureArray(payload?.to_agent_ids)
    if (!recipientIds.length) return

    for (const recipientIdentifier of recipientIds) {
      const recipientId = resolveJobId(recipientIdentifier)
      if (!recipientId) continue

      const previous = jobsById.value.get(recipientId)
      if (!previous) continue

      // Use server-provided counter from WebSocket event
      upsertJob({
        job_id: recipientId,
        messages_waiting_count: payload.recipient_waiting_count ?? (previous.messages_waiting_count || 0) + 1,
      })
    }
  }

  // Handover 0387g: Simplified to use server-provided counters instead of array manipulation
  function handleMessageAcknowledged(payload) {
    // Try multiple resolution strategies: agent_id, job_id, from_job_id
    // Handover 0407: Backend sends agent_id (executor UUID), which may not
    // be directly in the store. Also try from_job_id for backward compat.
    const recipientId = resolveJobId(payload?.agent_id)
      || resolveJobId(payload?.job_id)
      || resolveJobId(payload?.from_job_id)

    if (!recipientId) {
      // eslint-disable-next-line no-console
      console.debug('[agentJobsStore] handleMessageAcknowledged: Could not resolve job ID', {
        agent_id: payload?.agent_id,
        job_id: payload?.job_id,
        from_job_id: payload?.from_job_id,
        available_jobs: Array.from(jobsById.value.keys()).slice(0, 5),
      })
      return
    }

    const previous = jobsById.value.get(recipientId)
    if (!previous) {
      // eslint-disable-next-line no-console
      console.debug('[agentJobsStore] handleMessageAcknowledged: Job not found in store', { recipientId })
      return
    }

    // Use server-provided counters from WebSocket event
    upsertJob({
      job_id: recipientId,
      messages_waiting_count: payload.waiting_count ?? previous.messages_waiting_count ?? 0,
      messages_read_count: payload.read_count ?? previous.messages_read_count ?? 0,
    })
  }

  function $reset() {
    jobsById.value = new Map()
  }

  // Create a proxy object that maintains .value structure
  const jobsByIdProxy = new Proxy(
    {},
    {
      get: (target, prop) => {
        if (prop === 'value') {
          return jobsById.value
        }
        return undefined
      },
    }
  )

  return {
    // state
    jobsById: jobsByIdProxy,

    // getters
    jobs,
    sortedJobs,
    jobCount,

    // selectors
    getJob,
    resolveJobId,

    // actions
    setJobs,
    upsertJob,
    removeJob,

    // ws handlers
    handleCreated,
    handleUpdated,
    handleStatusChanged,
    handleMissionAcknowledged,
    handleProgressUpdate,
    handleMessageSent,
    handleMessageReceived,
    handleMessageAcknowledged,

    // lifecycle
    $reset,
  }
})
