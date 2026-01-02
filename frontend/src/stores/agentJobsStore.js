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
    const priority = {
      failed: 1,
      blocked: 2,
      waiting: 3,
      working: 4,
      complete: 5,
    }

    const list = Array.from(jobsById.value.values())
    list.sort((a, b) => {
      const aPriority = priority[a.status] || 999
      const bPriority = priority[b.status] || 999

      if (aPriority !== bPriority) return aPriority - bPriority

      const aIsOrchestrator = a.agent_type === 'orchestrator' ? 0 : 1
      const bIsOrchestrator = b.agent_type === 'orchestrator' ? 0 : 1
      if (aIsOrchestrator !== bIsOrchestrator) return aIsOrchestrator - bIsOrchestrator

      return (a.agent_type || '').localeCompare(b.agent_type || '')
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

    const previous = jobsById.value.get(jobId)
    const nextJob = normalizeJob({ ...(previous || {}), ...(patch || {}), job_id: jobId })

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
  function handleProgressUpdate(payload) {
    if (!payload?.job_id) return
    upsertJob({
      job_id: payload.job_id,
      progress: payload.progress,
      current_task: payload.current_task,
      last_progress_at: payload.last_progress_at,
      // Store todo_steps in job_metadata for Steps column display
      job_metadata: payload.todo_steps ? { todo_steps: payload.todo_steps } : undefined,
    })
  }

  function resolveJobId(identifier) {
    if (!identifier) return null

    if (jobsById.value.has(identifier)) {
      return identifier
    }

    // Legacy fallback: from_agent may be agent_type (e.g., "orchestrator").
    for (const job of jobsById.value.values()) {
      if (job.agent_type === identifier || job.agent_name === identifier) {
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

  function handleMessageAcknowledged(payload) {
    const recipientId = resolveJobId(payload?.agent_id || payload?.job_id)
    if (!recipientId) return

    const previous = jobsById.value.get(recipientId)
    if (!previous) return

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

  return {
    // state
    jobsById,

    // getters
    jobs,
    sortedJobs,
    jobCount,

    // selectors
    getJob,

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
