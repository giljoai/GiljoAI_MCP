import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

function ensureArray(value) {
  return Array.isArray(value) ? value : []
}

function normalizeJob(rawJob) {
  const job_id = rawJob?.job_id || rawJob?.id || rawJob?.agent_id
  // Handover 0462: Prefer agent_id (executor UUID) - always present and unique after spawn
  // This prevents unique_key mismatches between WebSocket and API data
  // Handover 0700i: Removed instance_number - use agent_id as unique_key
  const unique_key = rawJob?.agent_id || rawJob?.execution_id || job_id
  return {
    ...rawJob,
    job_id,
    unique_key,
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
    // Sort order: Working (top) -> Silent -> Blocked -> Waiting -> Completed (bottom)
    // Handover 0491: Removed failed/cancelled, added silent
    const priority = {
      working: 1,
      silent: 2,
      blocked: 3,
      waiting: 4,
      complete: 5,
      completed: 5,  // alias
      decommissioned: 6,
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
    // Handover 0700i: Removed instanceNumber parameter
    // Try direct lookup (might be unique_key already)
    if (jobsById.value.has(jobId)) {
      return jobsById.value.get(jobId)
    }
    // Fallback: find first job with matching job_id
    for (const job of jobsById.value.values()) {
      if (job.job_id === jobId) {
        return job
      }
    }
    return null
  }

  function setJobs(rows = []) {
    const next = new Map()
    for (const rawJob of ensureArray(rows)) {
      const job = normalizeJob(rawJob)
      if (!job.unique_key) continue

      // Handover 0463: Only preserve identity fields from existing entry
      // This prevents "??" avatars when API response lacks identity fields
      const existing = jobsById.value.get(job.unique_key)
      if (existing) {
        job.agent_display_name = job.agent_display_name || existing.agent_display_name
        job.agent_name = job.agent_name || existing.agent_name
      }

      next.set(job.unique_key, job)
    }
    jobsById.value = next
  }

  function upsertJob(patch) {
    const jobId = patch?.job_id || patch?.id || patch?.agent_id
    const agentId = patch?.agent_id
    if (!jobId && !agentId) return

    // CRITICAL FIX: Find existing job FIRST before computing unique_key
    // This prevents creating duplicates when WebSocket events use different ID formats
    // Handover 0700i: Removed instance_number matching
    let existingJob = null
    let existingKey = null

    // 1. Try execution_id (most specific)
    if (patch?.execution_id && jobsById.value.has(patch.execution_id)) {
      existingKey = patch.execution_id
      existingJob = jobsById.value.get(existingKey)
    }

    // 2. Try unique_key from patch
    if (!existingJob && patch?.unique_key && jobsById.value.has(patch.unique_key)) {
      existingKey = patch.unique_key
      existingJob = jobsById.value.get(existingKey)
    }

    // 3. Search by agent_id (executor UUID - used in WebSocket events)
    if (!existingJob && agentId) {
      for (const [key, job] of jobsById.value.entries()) {
        if (job.agent_id === agentId) {
          existingKey = key
          existingJob = job
          break
        }
      }
    }

    // 4. Search by job_id (work order UUID)
    if (!existingJob && jobId) {
      for (const [key, job] of jobsById.value.entries()) {
        if (job.job_id === jobId) {
          existingKey = key
          existingJob = job
          break
        }
      }
    }

    // Compute unique_key only if no existing job found (new entry)
    const uniqueKey = existingKey || patch?.execution_id || patch?.unique_key || jobId

    // Handover 0388: Filter undefined values to prevent state corruption
    // Spread operator preserves undefined, which overwrites existing valid data
    const cleanPatch = Object.fromEntries(
      Object.entries(patch || {}).filter(([_, v]) => v !== undefined)
    )

    const previous = existingJob || jobsById.value.get(uniqueKey)
    const nextJob = normalizeJob({ ...(previous || {}), ...cleanPatch, job_id: jobId || previous?.job_id })

    // Avoid unnecessary churn if nothing changed.
    if (previous && JSON.stringify(previous) === JSON.stringify(nextJob)) {
      return
    }

    // Use existing key if we found one, otherwise use the computed/normalized key
    const finalKey = existingKey || nextJob.unique_key
    jobsById.value = createNextMapWith(jobsById.value, finalKey, nextJob)
  }

  function removeJob(uniqueKeyOrJobId) {
    if (!uniqueKeyOrJobId) return
    // Try direct removal by unique_key
    if (jobsById.value.has(uniqueKeyOrJobId)) {
      jobsById.value = createNextMapWithout(jobsById.value, uniqueKeyOrJobId)
      return
    }
    // Fallback: find and remove by job_id
    for (const [key, job] of jobsById.value.entries()) {
      if (job.job_id === uniqueKeyOrJobId) {
        jobsById.value = createNextMapWithout(jobsById.value, key)
        return
      }
    }
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
    // Handover 0462 hardening (from 0463 recommendation):
    // Only update existing jobs, don't create new ones from status events
    // This prevents ghost rows from cross-project event leaks
    const existingKey = resolveJobId(payload?.job_id) || resolveJobId(payload?.agent_id)
    if (!existingKey) {
      // Job not in store - this might be cross-project leak, ignore
      // eslint-disable-next-line no-console
      console.debug('[handleStatusChanged] Ignoring status for unknown job:', payload?.job_id)
      return
    }
    upsertJob(payload)
  }

  // Handover 0462: Include identity fields to prevent "??" avatar bug from race conditions
  function handleMissionAcknowledged(payload) {
    if (!payload?.job_id) return
    const updates = {
      job_id: payload.job_id,
      mission_acknowledged_at: payload.mission_acknowledged_at,
    }
    // Handover 0462: Include identity fields if present in payload
    // If this event arrives before agent:created, these fields ensure the entry is complete
    if (payload.agent_display_name) {
      updates.agent_display_name = payload.agent_display_name
    }
    if (payload.agent_name) {
      updates.agent_name = payload.agent_name
    }
    if (payload.agent_id) {
      updates.agent_id = payload.agent_id
    }
    upsertJob(updates)
  }

  // Handover 0386: Handle progress updates from job:progress_update WebSocket events
  // Progress is now sent directly via WebSocket, NOT via message system
  // Handover 0388: Conditionally build updates to prevent undefined corruption
  // Handover 0401: Transform todo_steps array to steps summary object
  // Handover 0402: Store todo_items for Plan/TODOs tab display
  // Handover 0462: Include identity fields to prevent "??" avatar bug from race conditions
  function handleProgressUpdate(payload) {
    if (!payload?.job_id) return

    const updates = {
      job_id: payload.job_id,
      progress: payload.progress,
      current_task: payload.current_task,
      last_progress_at: payload.last_progress_at,
    }

    // Handover 0462: Include identity fields to prevent "??" avatar bug
    // If this event arrives before agent:created, these fields ensure the entry is complete
    if (payload.agent_display_name) {
      updates.agent_display_name = payload.agent_display_name
    }
    if (payload.agent_name) {
      updates.agent_name = payload.agent_name
    }
    if (payload.agent_id) {
      updates.agent_id = payload.agent_id
    }

    // Only add job_metadata when todo_steps exists (prevents undefined overwrite)
    // Handover 0401: Handle both object format { total_steps, completed_steps }
    // and array format [{ status: 'done' }, ...]
    if (payload.todo_steps) {
      updates.job_metadata = { todo_steps: payload.todo_steps }

      if (Array.isArray(payload.todo_steps)) {
        // Array format: count completed, skipped vs total
        const completed = payload.todo_steps.filter(
          (s) => s.status === 'done' || s.status === 'completed'
        ).length
        const skipped = payload.todo_steps.filter(
          (s) => s.status === 'skipped'
        ).length
        updates.steps = {
          completed,
          skipped,
          total: payload.todo_steps.length,
        }
      } else if (typeof payload.todo_steps === 'object') {
        // Object format from backend: { total_steps, completed_steps, skipped_steps }
        const total = payload.todo_steps.total_steps
        const completed = payload.todo_steps.completed_steps
        const skipped = payload.todo_steps.skipped_steps || 0
        if (typeof total === 'number' && typeof completed === 'number') {
          updates.steps = { completed, skipped, total }
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

    // Direct match by unique_key
    if (jobsById.value.has(identifier)) {
      return identifier
    }

    // Check by agent_id (executor UUID from messaging) - return unique_key
    for (const job of jobsById.value.values()) {
      if (job.agent_id === identifier) {
        return job.unique_key
      }
    }

    // Check by job_id - return unique_key of first match
    for (const job of jobsById.value.values()) {
      if (job.job_id === identifier) {
        return job.unique_key
      }
    }

    // Legacy fallback: from_agent may be agent_display_name (e.g., "orchestrator").
    for (const job of jobsById.value.values()) {
      if (job.agent_display_name === identifier || job.agent_name === identifier) {
        return job.unique_key
      }
    }

    return null
  }

  // Handover 0407: Use from_job_id (sender's agent_id) for reliable resolution
  // The backend now sends the sender's agent_id in the job_id/from_job_id field
  function handleMessageSent(payload) {
    const senderId = resolveJobId(payload?.from_job_id)
      || resolveJobId(payload?.job_id)
      || resolveJobId(payload?.from_agent)
    if (!senderId) return

    const previous = jobsById.value.get(senderId)
    if (!previous) return

    // Handover 0463: Spread previous to preserve identity fields and prevent ghost entries
    // Use server-provided counter from WebSocket event
    upsertJob({
      ...previous,
      messages_sent_count: payload.sender_sent_count ?? (previous.messages_sent_count || 0) + 1,
    })

    // Also update recipient's waiting count if provided
    const recipientIdentifier = payload?.to_agent_ids?.[0]
    if (recipientIdentifier) {
      const recipientId = resolveJobId(recipientIdentifier)
      if (recipientId) {
        const recipientPrevious = jobsById.value.get(recipientId)
        if (recipientPrevious) {
          // Handover 0463: Spread previous to preserve identity fields and prevent ghost entries
          upsertJob({
            ...recipientPrevious,
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

      // Handover 0463: Spread previous to preserve identity fields and prevent ghost entries
      // Use server-provided counter from WebSocket event
      upsertJob({
        ...previous,
        messages_waiting_count: payload.waiting_count ?? (previous.messages_waiting_count || 0) + 1,
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

    // Handover 0463: Spread previous to preserve identity fields and prevent ghost entries
    // Use server-provided counters from WebSocket event
    upsertJob({
      ...previous,
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
