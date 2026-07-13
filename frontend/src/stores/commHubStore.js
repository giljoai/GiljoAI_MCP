/**
 * commHubStore.js — FE-6054e Agent Message Hub
 *
 * Pinia store for thread-based agent communications.
 * Mirrors the proven Map-based, immutable-upsert pattern from projectMessagesStore.js.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import { immutableMapSet, immutableMapDelete, immutableObjectPatch } from './immutableHelpers'
import api from '@/services/api'
import { useUserStore } from '@/stores/user'

// ---------------------------------------------------------------------------
// Normalization helpers
// ---------------------------------------------------------------------------

function normalizeMessage(raw) {
  if (!raw) return null
  const id = raw.message_id || raw.id
  if (!id) return null
  return {
    message_id: id,
    thread_id: raw.thread_id || null,
    from_agent_id: raw.from_agent_id || null,
    from_display_name: raw.from_display_name || raw.from_agent_id || 'unknown',
    content: raw.content || '',
    message_type: raw.message_type || 'broadcast',
    priority: raw.priority || 'normal',
    status: raw.status || null,
    requires_action: raw.requires_action || false,
    created_at: raw.created_at || null,
    // FE-9012c (D3/D4): per-message recipient acted-on state for the in-thread
    // waiting/read/sent filter. Present only on a history read with
    // include_recipient_state=true; null (not []) when absent so the filter can
    // tell "no junction data loaded" (e.g. a live WS message) from "no recipients".
    recipients: Array.isArray(raw.recipients) ? raw.recipients : null,
    acked_by: Array.isArray(raw.acked_by) ? raw.acked_by : null,
    completed_by: Array.isArray(raw.completed_by) ? raw.completed_by : null,
    pending_for: Array.isArray(raw.pending_for) ? raw.pending_for : null,
  }
}

function normalizeThread(raw) {
  if (!raw) return null
  const id = raw.thread_id || raw.id
  if (!id) return null
  return {
    thread_id: id,
    chat_id: raw.chat_id || null,
    subject: raw.subject || null,
    status: raw.status || 'open',
    next_action_owner: raw.next_action_owner || null,
    severity: raw.severity || null,
    product_id: raw.product_id || null,
    project_id: raw.project_id || null,
    created_at: raw.created_at || null,
    // Derived: use updated_at if provided, else created_at, for activity sort
    last_activity_at: raw.updated_at || raw.last_activity_at || raw.created_at || null,
  }
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useCommHubStore = defineStore('commHub', () => {
  // ----- state -----
  const threadsById = ref(new Map())
  const messagesByThreadId = ref(new Map())
  const participantsByThreadId = ref(new Map())
  const selectedThreadId = ref(null)
  /** Map<thread_id, number> — unread message count per thread */
  const unreadByThreadId = ref(new Map())
  const filters = ref({
    status: null,
    owner: null,
    product_id: null,
    project_id: null,
  })
  const loading = ref(false)
  const error = ref(null)

  // ----- getters -----

  /** Sorted thread array: newest last_activity_at first */
  const threadList = computed(() => {
    const arr = Array.from(threadsById.value.values())
    arr.sort((a, b) => {
      const ta = a.last_activity_at ? new Date(a.last_activity_at).getTime() : 0
      const tb = b.last_activity_at ? new Date(b.last_activity_at).getTime() : 0
      return tb - ta
    })
    return arr
  })

  // ----- FE-9012c (D2): two-tab split of the SAME thread list -----
  // "Project comms" = threads bound to a project; "Town square" = standalone.
  // Both derive from threadList (already newest-first) so sorting stays shared.

  /** Threads with a project_id (project-bound). */
  const projectThreadList = computed(() => threadList.value.filter((t) => t.project_id != null))

  /** Standalone threads (no project_id). */
  const townSquareThreadList = computed(() => threadList.value.filter((t) => t.project_id == null))

  /** Per-tab unread totals: sum the (a) cursor-derived per-thread unread counts. */
  const projectUnreadTotal = computed(() =>
    projectThreadList.value.reduce((sum, t) => sum + unreadFor(t.thread_id), 0),
  )
  const townSquareUnreadTotal = computed(() =>
    townSquareThreadList.value.reduce((sum, t) => sum + unreadFor(t.thread_id), 0),
  )

  function messagesFor(threadId) {
    return messagesByThreadId.value.get(threadId) || []
  }

  function participantsFor(threadId) {
    return participantsByThreadId.value.get(threadId) || []
  }

  const selectedThread = computed(() => {
    if (!selectedThreadId.value) return null
    return threadsById.value.get(selectedThreadId.value) || null
  })

  // ----- unread + baton getters -----

  function unreadFor(threadId) {
    return unreadByThreadId.value.get(threadId) || 0
  }

  const totalUnread = computed(() => {
    let sum = 0
    for (const count of unreadByThreadId.value.values()) {
      sum += count
    }
    return sum
  })

  /** thread_ids where next_action_owner === currentUser.id */
  const batonThreadIds = computed(() => {
    const userId = useUserStore().currentUser?.id
    if (!userId) return []
    const ids = []
    for (const thread of threadsById.value.values()) {
      if (thread.next_action_owner === userId) ids.push(thread.thread_id)
    }
    return ids
  })

  const yourTurnCount = computed(() => batonThreadIds.value.length)

  const hasUserAttention = computed(() => totalUnread.value > 0 || yourTurnCount.value > 0)

  // ----- internal upsert helpers -----

  function _upsertThread(raw) {
    const thread = normalizeThread(raw)
    if (!thread) return
    const existing = threadsById.value.get(thread.thread_id)
    if (existing) {
      const patched = immutableObjectPatch(existing, thread)
      if (JSON.stringify(existing) === JSON.stringify(patched)) return
      threadsById.value = immutableMapSet(threadsById.value, thread.thread_id, patched)
    } else {
      threadsById.value = immutableMapSet(threadsById.value, thread.thread_id, thread)
    }
  }

  function _upsertMessage(threadId, rawMessage) {
    const message = normalizeMessage(rawMessage)
    if (!message || !threadId) return

    const previousList = messagesByThreadId.value.get(threadId) || []
    const existingIndex = previousList.findIndex((m) => m.message_id === message.message_id)

    if (existingIndex === -1) {
      const nextList = [...previousList, message]
      messagesByThreadId.value = immutableMapSet(messagesByThreadId.value, threadId, nextList)
      return
    }

    const previousMessage = previousList[existingIndex]
    const nextMessage = immutableObjectPatch(previousMessage, message)
    if (JSON.stringify(previousMessage) === JSON.stringify(nextMessage)) return

    const nextList = [...previousList]
    nextList[existingIndex] = nextMessage
    messagesByThreadId.value = immutableMapSet(messagesByThreadId.value, threadId, nextList)
  }

  // ----- actions -----

  async function loadThreads(filterOverride) {
    loading.value = true
    error.value = null
    try {
      const params = { ...(filterOverride ?? filters.value) }
      // Strip null/undefined params
      Object.keys(params).forEach((k) => {
        if (params[k] == null) delete params[k]
      })
      const res = await api.threads.list(params)
      const threads = res.data?.threads || []
      threads.forEach((t) => _upsertThread(t))
    } catch (err) {
      error.value = err?.message || 'Failed to load threads'
    } finally {
      loading.value = false
    }
  }

  async function loadThread(id) {
    loading.value = true
    error.value = null
    try {
      const res = await api.threads.history(id, { includeRecipientState: true })
      const thread = res.data?.thread
      const messages = res.data?.messages || []
      if (thread) _upsertThread(thread)
      // Replace the message list for this thread with the full history
      const normalized = messages
        .map((m) => normalizeMessage(m))
        .filter(Boolean)
        .reduce((acc, m) => {
          if (!acc.find((x) => x.message_id === m.message_id)) acc.push(m)
          return acc
        }, [])
      messagesByThreadId.value = immutableMapSet(messagesByThreadId.value, id, normalized)
      // Viewing a thread clears its unread count
      markThreadRead(id)
    } catch (err) {
      error.value = err?.message || 'Failed to load thread'
    } finally {
      loading.value = false
    }
  }

  async function loadParticipants(id) {
    try {
      const res = await api.threads.participants(id)
      const participants = res.data?.participants || []
      participantsByThreadId.value = immutableMapSet(
        participantsByThreadId.value,
        id,
        participants,
      )
    } catch (err) {
      error.value = err?.message || 'Failed to load participants'
    }
  }

  async function createThread(body) {
    const res = await api.threads.create(body)
    const thread = res.data
    if (thread) _upsertThread(thread)
    return thread
  }

  async function postMessage(id, body) {
    const res = await api.threads.post(id, body)
    return res.data
  }

  async function passBaton(id, to) {
    const res = await api.threads.passBaton(id, to)
    const updated = res.data
    if (updated?.thread_id) {
      const existing = threadsById.value.get(updated.thread_id)
      if (existing) {
        threadsById.value = immutableMapSet(
          threadsById.value,
          updated.thread_id,
          immutableObjectPatch(existing, { next_action_owner: updated.next_action_owner }),
        )
      }
    }
    return updated
  }

  /**
   * Soft-delete a thread, then drop it from local state (thread, its messages,
   * participants, unread count) and clear the selection if it was open.
   */
  async function deleteThread(id) {
    if (!id) return
    await api.threads.delete(id)
    _removeThreadLocal(id)
  }

  function _removeThreadLocal(id) {
    threadsById.value = immutableMapDelete(threadsById.value, id)
    messagesByThreadId.value = immutableMapDelete(messagesByThreadId.value, id)
    participantsByThreadId.value = immutableMapDelete(participantsByThreadId.value, id)
    unreadByThreadId.value = immutableMapDelete(unreadByThreadId.value, id)
    if (selectedThreadId.value === id) selectedThreadId.value = null
  }

  async function searchThreads(query) {
    loading.value = true
    error.value = null
    try {
      const res = await api.threads.search({ query })
      const threads = res.data?.threads || []
      threads.forEach((t) => _upsertThread(t))
      return threads
    } catch (err) {
      error.value = err?.message || 'Search failed'
      return []
    } finally {
      loading.value = false
    }
  }

  /** Mark a thread's unread count as zero */
  function markThreadRead(threadId) {
    if (!threadId) return
    if ((unreadByThreadId.value.get(threadId) || 0) === 0) return
    unreadByThreadId.value = immutableMapSet(unreadByThreadId.value, threadId, 0)
  }

  function selectThread(id) {
    selectedThreadId.value = id
    markThreadRead(id)
  }

  // ----- WebSocket handlers -----

  /**
   * handleThreadMessage — new message arrives on a thread.
   * Store-first: upsert into messagesByThreadId; deduplicate by message_id.
   * Increments unread count for threads that are not currently open.
   */
  function handleThreadMessage(payload) {
    const threadId = payload?.thread_id
    if (!threadId) return
    _upsertMessage(threadId, payload)
    // Bump thread last_activity_at so sorting stays live
    const existing = threadsById.value.get(threadId)
    if (existing && payload.created_at) {
      threadsById.value = immutableMapSet(
        threadsById.value,
        threadId,
        immutableObjectPatch(existing, { last_activity_at: payload.created_at }),
      )
    }
    // Increment unread only for threads that are not currently open
    if (threadId !== selectedThreadId.value) {
      const prev = unreadByThreadId.value.get(threadId) || 0
      unreadByThreadId.value = immutableMapSet(unreadByThreadId.value, threadId, prev + 1)
    }
  }

  /**
   * handleThreadUpdate — thread meta changes (status, baton, new thread).
   */
  function handleThreadUpdate(payload) {
    const threadId = payload?.thread_id
    if (!threadId) return

    if (payload.update_type === 'deleted') {
      // Another client soft-deleted this thread — drop it everywhere locally.
      _removeThreadLocal(threadId)
      return
    }

    if (payload.update_type === 'created' && !threadsById.value.has(threadId)) {
      // Unknown thread created — trigger a refresh
      loadThreads(filters.value)
      return
    }

    if (payload.update_type === 'restored' && !threadsById.value.has(threadId)) {
      // A soft-deleted thread was recovered (FE-6138) — re-surface it in the list.
      loadThreads(filters.value)
      return
    }

    const existing = threadsById.value.get(threadId)
    if (!existing) return

    const patch = {}
    if (payload.status != null) patch.status = payload.status
    if (payload.next_action_owner != null) patch.next_action_owner = payload.next_action_owner
    if (payload.chat_id != null) patch.chat_id = payload.chat_id

    if (Object.keys(patch).length === 0) return
    const updated = immutableObjectPatch(existing, patch)
    if (JSON.stringify(existing) === JSON.stringify(updated)) return
    threadsById.value = immutableMapSet(threadsById.value, threadId, updated)
  }

  // ----- lifecycle -----

  function $reset() {
    threadsById.value = new Map()
    messagesByThreadId.value = new Map()
    participantsByThreadId.value = new Map()
    unreadByThreadId.value = new Map()
    selectedThreadId.value = null
    filters.value = { status: null, owner: null, product_id: null, project_id: null }
    loading.value = false
    error.value = null
  }

  /**
   * Test-only helper: directly seed a thread into the store without an API call.
   * Only exposed in the return map; tree-shaken in production by the store.
   */
  function _testSeedThread(raw) {
    _upsertThread(raw)
  }

  return {
    // state
    threadsById,
    messagesByThreadId,
    participantsByThreadId,
    unreadByThreadId,
    selectedThreadId,
    filters,
    loading,
    error,

    // getters
    threadList,
    projectThreadList,
    townSquareThreadList,
    projectUnreadTotal,
    townSquareUnreadTotal,
    messagesFor,
    participantsFor,
    selectedThread,
    unreadFor,
    totalUnread,
    batonThreadIds,
    yourTurnCount,
    hasUserAttention,

    // actions
    loadThreads,
    loadThread,
    loadParticipants,
    createThread,
    postMessage,
    passBaton,
    deleteThread,
    searchThreads,
    selectThread,
    markThreadRead,

    // ws handlers
    handleThreadMessage,
    handleThreadUpdate,

    // lifecycle
    $reset,

    // test helpers (used in commHubStore.spec.js — tree-shaken otherwise)
    _testSeedThread,
  }
})
