import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

function ensureArray(value) {
  return Array.isArray(value) ? value : []
}

function deriveMessageCounters(messages) {
  let sent = 0
  let waiting = 0
  let read = 0

  for (const message of ensureArray(messages)) {
    if (message?.direction === 'outbound') {
      sent += 1
      continue
    }

    if (message?.direction === 'inbound') {
      if (message.status === 'waiting' || message.status === 'pending') {
        waiting += 1
      } else if (message.status === 'acknowledged' || message.status === 'read') {
        read += 1
      }
    }
  }

  return { sent, waiting, read }
}

function normalizeJob(rawJob) {
  const messages = ensureArray(rawJob?.messages)
  const { sent, waiting, read } = deriveMessageCounters(messages)

  return {
    ...rawJob,
    job_id: rawJob?.job_id || rawJob?.id || rawJob?.agent_id,
    messages,
    messages_sent_count: Number.isFinite(rawJob?.messages_sent_count)
      ? rawJob.messages_sent_count
      : sent,
    messages_waiting_count: Number.isFinite(rawJob?.messages_waiting_count)
      ? rawJob.messages_waiting_count
      : waiting,
    messages_read_count: Number.isFinite(rawJob?.messages_read_count)
      ? rawJob.messages_read_count
      : read,
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

    const messageId = payload?.message_id
    const previousMessages = ensureArray(previous.messages)
    const alreadyTracked =
      messageId &&
      previousMessages.some((m) => m?.id === messageId && m?.direction === 'outbound')

    if (alreadyTracked) return

    const nextMessages = [
      ...previousMessages,
      {
        id: messageId,
        direction: 'outbound',
        status: 'sent',
        from_agent: payload?.from_agent,
        to_agent_ids: ensureArray(payload?.to_agent_ids),
        timestamp: payload?.timestamp,
        message_type: payload?.message_type,
      },
    ]

    const nextJob = normalizeJob({
      ...previous,
      messages: nextMessages,
      messages_sent_count: (previous.messages_sent_count || 0) + 1,
    })

    jobsById.value = createNextMapWith(jobsById.value, senderId, nextJob)
  }

  function handleMessageReceived(payload) {
    const recipientIds = ensureArray(payload?.to_agent_ids)
    if (!recipientIds.length) return

    let nextMap = jobsById.value

    for (const recipientIdentifier of recipientIds) {
      const recipientId = resolveJobId(recipientIdentifier)
      if (!recipientId) continue

      const previous = nextMap.get(recipientId)
      if (!previous) continue

      const messageId = payload?.message_id
      const previousMessages = ensureArray(previous.messages)
      const alreadyTracked =
        messageId &&
        previousMessages.some((m) => m?.id === messageId && m?.direction === 'inbound')

      if (alreadyTracked) continue

      const nextMessages = [
        ...previousMessages,
        {
          id: messageId,
          direction: 'inbound',
          status: 'waiting',
          from_agent: payload?.from_agent,
          timestamp: payload?.timestamp,
          message_type: payload?.message_type,
        },
      ]

      const nextJob = normalizeJob({
        ...previous,
        messages: nextMessages,
        messages_waiting_count: (previous.messages_waiting_count || 0) + 1,
      })

      nextMap = createNextMapWith(nextMap, recipientId, nextJob)
    }

    jobsById.value = nextMap
  }

  // Handover 0405: Fixed fallback for message counter updates when messages
  // aren't tracked locally. Also improved job ID resolution (Handover 0407).
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

    const messageIds = ensureArray(payload?.message_ids).length
      ? ensureArray(payload?.message_ids)
      : payload?.message_id
        ? [payload.message_id]
        : []

    if (!messageIds.length) return

    const idSet = new Set(messageIds)
    const previousMessages = ensureArray(previous.messages)

    let acknowledgedNow = 0
    const nextMessages = previousMessages.map((message) => {
      if (
        message?.direction === 'inbound' &&
        idSet.has(message.id) &&
        message.status !== 'acknowledged' &&
        message.status !== 'read'
      ) {
        acknowledgedNow += 1
        return { ...message, status: 'acknowledged' }
      }
      return message
    })

    // Handover 0405: Fallback when messages aren't tracked locally
    // Backend acknowledged messages we don't have in the local messages array.
    // This happens when the page wasn't open when message:received was sent,
    // or messages were loaded from JSONB without full detail.
    if (acknowledgedNow === 0 && messageIds.length > 0) {
      // eslint-disable-next-line no-console
      console.debug('[agentJobsStore] handleMessageAcknowledged: Using fallback counter update', {
        recipientId,
        messageCount: messageIds.length,
        previousWaiting: previous.messages_waiting_count,
        previousRead: previous.messages_read_count,
      })

      const nextJob = normalizeJob({
        ...previous,
        messages_waiting_count: Math.max(0, (previous.messages_waiting_count || 0) - messageIds.length),
        messages_read_count: (previous.messages_read_count || 0) + messageIds.length,
      })

      jobsById.value = createNextMapWith(jobsById.value, recipientId, nextJob)
      return
    }

    if (acknowledgedNow === 0) return

    const nextJob = normalizeJob({
      ...previous,
      messages: nextMessages,
      messages_waiting_count: Math.max(
        0,
        (previous.messages_waiting_count || 0) - acknowledgedNow,
      ),
      messages_read_count: (previous.messages_read_count || 0) + acknowledgedNow,
    })

    jobsById.value = createNextMapWith(jobsById.value, recipientId, nextJob)
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
