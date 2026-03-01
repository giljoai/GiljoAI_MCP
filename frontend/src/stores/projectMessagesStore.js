import { defineStore } from 'pinia'
import { ref } from 'vue'

import { immutableMapSet, immutableObjectPatch } from './immutableHelpers'

function resolveProjectId(value) {
  if (!value) return null
  return typeof value === 'string' ? value : value.project_id || value.id || null
}

function resolveMessageId(value) {
  if (!value) return null
  return value.id || value.message_id || null
}

function normalizeMessage(raw) {
  const id = resolveMessageId(raw)
  if (!id) return null

  return {
    ...raw,
    id,
    status: raw?.status || raw?.update_type || 'sent',
  }
}

export const useProjectMessagesStore = defineStore('projectMessagesDomain', () => {
  const messagesByProjectId = ref(new Map())

  function getMessages(projectId) {
    const resolved = resolveProjectId(projectId)
    if (!resolved) return []
    return messagesByProjectId.value.get(resolved) || []
  }

  function setMessages(projectId, rows = []) {
    const resolved = resolveProjectId(projectId)
    if (!resolved) return

    const next = []
    const seen = new Set()
    for (const raw of Array.isArray(rows) ? rows : []) {
      const message = normalizeMessage(raw)
      if (!message || seen.has(message.id)) continue
      seen.add(message.id)
      next.push(message)
    }

    messagesByProjectId.value = immutableMapSet(messagesByProjectId.value, resolved, next)
  }

  function upsertMessage(projectId, rawMessage) {
    const resolvedProjectId = resolveProjectId(projectId || rawMessage)
    const message = normalizeMessage(rawMessage)
    if (!resolvedProjectId || !message) return

    const previousList = messagesByProjectId.value.get(resolvedProjectId) || []
    const existingIndex = previousList.findIndex((m) => m.id === message.id)

    if (existingIndex === -1) {
      const nextList = [...previousList, message]
      messagesByProjectId.value = immutableMapSet(messagesByProjectId.value, resolvedProjectId, nextList)
      return
    }

    const previousMessage = previousList[existingIndex]
    const nextMessage = immutableObjectPatch(previousMessage, message)
    if (JSON.stringify(previousMessage) === JSON.stringify(nextMessage)) {
      return
    }

    const nextList = [...previousList]
    nextList[existingIndex] = nextMessage
    messagesByProjectId.value = immutableMapSet(messagesByProjectId.value, resolvedProjectId, nextList)
  }

  function updateMessages(projectId, updater) {
    const resolved = resolveProjectId(projectId)
    if (!resolved) return

    const previousList = messagesByProjectId.value.get(resolved) || []
    const nextList = updater(previousList)
    if (nextList === previousList) return

    messagesByProjectId.value = immutableMapSet(messagesByProjectId.value, resolved, nextList)
  }

  // =========================
  // WebSocket event handlers
  // =========================

  function handleSent(payload) {
    const projectId = payload?.project_id
    if (!projectId) return
    upsertMessage(projectId, payload)
  }

  function handleReceived(payload) {
    const projectId = payload?.project_id
    if (!projectId) return
    upsertMessage(projectId, payload)
  }

  function handleNew(payload) {
    const projectId = payload?.project_id
    if (!projectId) return
    upsertMessage(projectId, payload)
  }

  function handleAcknowledged(payload) {
    const projectId = payload?.project_id
    if (!projectId) return

    const messageIds = Array.isArray(payload?.message_ids)
      ? payload.message_ids
      : payload?.message_id
        ? [payload.message_id]
        : []

    if (!messageIds.length) return

    const idSet = new Set(messageIds)

    updateMessages(projectId, (previousList) => {
      let changed = false
      const next = previousList.map((message) => {
        if (idSet.has(message.id) && message.status !== 'acknowledged') {
          changed = true
          return { ...message, status: 'acknowledged' }
        }
        return message
      })

      return changed ? next : previousList
    })
  }

  function $reset() {
    messagesByProjectId.value = new Map()
  }

  return {
    // state
    messagesByProjectId,

    // selectors
    getMessages,

    // actions
    setMessages,
    upsertMessage,

    // ws handlers
    handleSent,
    handleReceived,
    handleNew,
    handleAcknowledged,

    // lifecycle
    $reset,
  }
})
