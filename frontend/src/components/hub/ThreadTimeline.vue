<template>
  <div ref="timelineEl" class="thread-timeline" data-testid="thread-timeline">
    <div
      v-if="!effectiveThreadId"
      class="thread-timeline__empty"
      data-testid="timeline-no-thread"
    >
      Select a thread to view messages.
    </div>

    <div
      v-else-if="messages.length === 0"
      class="thread-timeline__empty"
      data-testid="timeline-empty"
    >
      No messages yet.
    </div>

    <!-- FE-9012c (D3): message-relative waiting/read/sent filter, backed by the D4
         recipient junctions (surfaced via include_recipient_state). Waiting = an
         action-required post with recipients yet to act; Read = recipients acted;
         Sent = authored by you. Hidden in readonly mode (Phase 5 / D1(a) surfaces
         like the Project Review pane show the plain message list only). -->
    <div
      v-if="effectiveThreadId && messages.length > 0 && !readonly"
      class="tab-pills thread-timeline__filter"
      role="tablist"
      data-testid="thread-filter"
    >
      <button
        v-for="opt in filterOptions"
        :key="opt.key"
        type="button"
        class="pill-btn"
        :class="{ active: activeFilter === opt.key }"
        role="tab"
        :aria-selected="activeFilter === opt.key ? 'true' : 'false'"
        :data-testid="`thread-filter-${opt.key}`"
        @click="activeFilter = opt.key"
      >
        {{ opt.label }} ({{ opt.count }})
      </button>
    </div>

    <div
      v-if="effectiveThreadId && messages.length > 0 && visibleMessages.length === 0 && !readonly"
      class="thread-timeline__empty"
      data-testid="timeline-filter-empty"
    >
      No {{ activeFilterLabel }} messages.
    </div>

    <div
      v-for="message in decoratedMessages"
      :key="message.message_id"
      class="timeline-msg"
      :class="message._isUser ? 'timeline-msg--user' : 'timeline-msg--agent'"
      :data-testid="`timeline-message-${message.message_id}`"
    >
      <!-- Sender badge: user -> brand-yellow avatar+initials; agent -> tinted role color badge -->
      <div
        class="timeline-msg__avatar smooth-border"
        :class="{ 'timeline-msg__avatar--user': message._isUser }"
        :style="message._isUser ? undefined : avatarStyle(message._name)"
        :title="message._name"
        aria-hidden="true"
      >
        {{ avatarInitials(message._name) }}
      </div>

      <div class="timeline-msg__body">
        <!-- Header row -->
        <div class="timeline-msg__header">
          <span
            class="timeline-msg__sender"
            :class="{ 'timeline-msg__sender--user': message._isUser }"
            :style="message._isUser ? undefined : senderColor(message._name)"
          >
            {{ message._name }}
          </span>
          <span class="timeline-msg__time" data-testid="message-time">
            {{ formatTime(message.created_at) }}
          </span>
          <!-- broadcast / direct chip -->
          <span
            class="timeline-msg__type-chip smooth-border"
            :style="typeChipStyle(message.message_type)"
            data-testid="message-type-chip"
          >
            {{ message.message_type === 'broadcast' ? 'broadcast' : 'direct' }}
          </span>
          <!-- requires_action marker -->
          <span
            v-if="message.requires_action"
            class="timeline-msg__action-flag smooth-border"
            data-testid="message-action-flag"
          >
            <v-icon size="12">mdi-alert-circle-outline</v-icon>
            action required
          </span>
        </div>

        <!-- Content -->
        <div class="timeline-msg__content" data-testid="message-content">
          {{ message.content }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useCommHubStore } from '@/stores/commHubStore'
import { getAgentColor } from '@/config/agentColors'
import { hexToRgba } from '@/utils/colorUtils'

const props = defineProps({
  // Explicit thread to render (Phase 5 / D1(a) read-only surfaces). Falls back
  // to the store's selected thread when omitted, so existing callers like
  // HubView.vue (`<ThreadTimeline />` with no props) keep working identically.
  threadId: { type: String, default: null },
  // Hides the interactive waiting/read/sent filter pills -- for embedding in a
  // read-only pane (e.g. ProjectReviewModal's "Project Comms" section) that
  // must not offer interactive filtering chrome.
  readonly: { type: Boolean, default: false },
})

const commHub = useCommHubStore()
const timelineEl = ref(null)

const effectiveThreadId = computed(() => props.threadId || commHub.selectedThreadId)
const messages = computed(() => {
  if (!effectiveThreadId.value) return []
  return commHub.messagesFor(effectiveThreadId.value)
})

// ---- FE-9012c (D3): waiting / read / sent filter ----
// MESSAGE-relative (per-recipient junction state), NOT the viewer's inbox — this
// is what the human user audits: what did agents DO with each post. A message
// with no loaded junction state (e.g. a live WS arrival) simply isn't counted in
// Waiting/Read until the thread reloads with include_recipient_state.
const activeFilter = ref('all')

function isSent(m) {
  // Authored by the human user (participant_type "user" on the thread).
  return isUserMessage(m)
}
function isWaiting(m) {
  return !!m.requires_action && Array.isArray(m.pending_for) && m.pending_for.length > 0
}
function isRead(m) {
  // Every recipient has acted (acked or completed) — nobody left pending.
  if (!Array.isArray(m.recipients) || m.recipients.length === 0) return false
  const acted = (m.acked_by?.length || 0) + (m.completed_by?.length || 0)
  return acted > 0 && Array.isArray(m.pending_for) && m.pending_for.length === 0
}

const filterOptions = computed(() => [
  { key: 'all', label: 'All', count: messages.value.length },
  { key: 'waiting', label: 'Waiting', count: messages.value.filter(isWaiting).length },
  { key: 'read', label: 'Read', count: messages.value.filter(isRead).length },
  { key: 'sent', label: 'Sent', count: messages.value.filter(isSent).length },
])

const activeFilterLabel = computed(
  () => (filterOptions.value.find((o) => o.key === activeFilter.value)?.label || 'All').toLowerCase(),
)

const visibleMessages = computed(() => {
  const list = messages.value
  if (activeFilter.value === 'waiting') return list.filter(isWaiting)
  if (activeFilter.value === 'read') return list.filter(isRead)
  if (activeFilter.value === 'sent') return list.filter(isSent)
  return list
})

// Auto-scroll to bottom when new messages arrive
watch(
  () => messages.value.length,
  () => {
    nextTick(() => {
      if (timelineEl.value) {
        timelineEl.value.scrollTop = timelineEl.value.scrollHeight
      }
    })
  },
)

// ---- display helpers ----

// Resolve each message's author from the thread's participant directory — the
// AUTHORITATIVE signal: participant_type distinguishes a genuine human user from
// an agent, and display_name carries the agent's friendly role. This replaces the
// old "from_agent_id is UUID-shaped => user" heuristic, which misfired once the
// worker protocol had agents post under their own agent_id UUID: agent posts were
// mislabeled as USER posts and rendered with the brand-yellow user avatar and a raw
// UUID name. Falls back to the message's own fields + the UUID heuristic when the
// author isn't in the loaded participant list, so an un-enrolled poster never
// renders worse than before.
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function authorFor(message) {
  const p = commHub
    .participantsFor(effectiveThreadId.value)
    .find((x) => x.participant_id === message.from_agent_id)
  if (p) {
    return {
      isUser: p.participant_type === 'user',
      name: p.display_name || message.from_display_name || message.from_agent_id,
    }
  }
  return {
    isUser: UUID_RE.test(message.from_agent_id || ''),
    name: message.from_display_name || message.from_agent_id,
  }
}

function isUserMessage(message) {
  return authorFor(message).isUser
}

// Enrich the visible messages with resolved author identity so the template binds
// off stable per-message fields (_isUser / _name) instead of re-resolving per node.
const decoratedMessages = computed(() =>
  visibleMessages.value.map((m) => {
    const author = authorFor(m)
    return { ...m, _isUser: author.isUser, _name: author.name }
  }),
)

function avatarInitials(name) {
  if (!name) return '?'
  const parts = name.split(/[-_\s]+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.slice(0, 2).toUpperCase()
}

// Fallback to orchestrator color (the canonical default from agentColors.js)
const FALLBACK_HEX = getAgentColor('orchestrator')?.hex

function avatarStyle(name) {
  const colorObj = getAgentColor(name)
  const hex = colorObj?.hex || FALLBACK_HEX
  return {
    backgroundColor: hexToRgba(hex, 0.2),
    color: hex,
    borderRadius: '8px',
  }
}

function senderColor(name) {
  const colorObj = getAgentColor(name)
  const hex = colorObj?.hex || FALLBACK_HEX
  return { color: hex }
}

// Type chip: broadcast = sky-blue (implementer), direct = lavender (reviewer).
// Hex derived from getAgentColor() — no hardcoded hex literals.
const TYPE_CHIP_AGENT_MAP = {
  broadcast: 'implementer',
  direct: 'reviewer',
}

function typeChipStyle(type) {
  const agentName = TYPE_CHIP_AGENT_MAP[type?.toLowerCase()] || TYPE_CHIP_AGENT_MAP.direct
  const hex = getAgentColor(agentName)?.hex
  return {
    backgroundColor: hexToRgba(hex, 0.15),
    color: hex,
    borderRadius: '8px',
  }
}

function formatTime(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}
</script>

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;
@use '../../styles/variables' as v;

.thread-timeline {
  flex: 1;
  overflow-y: auto;
  padding: v.$spacing-md;
  display: flex;
  flex-direction: column;
  gap: v.$spacing-md;

  &__empty {
    margin: auto;
    color: var(--text-muted);
    font-size: 0.85rem;
    text-align: center;
    padding: v.$spacing-xl 0;
  }

  // FE-9012c (D3): the filter stays pinned while the message list scrolls under it.
  // Opaque base-surface background so scrolled messages don't bleed through.
  &__filter {
    position: sticky;
    top: 0;
    z-index: 1;
    flex-shrink: 0;
    padding: v.$spacing-xs v.$spacing-xs v.$spacing-sm;
    margin: (-#{v.$spacing-md}) (-#{v.$spacing-md}) 0;
    background: $elevation-flat;
    flex-wrap: wrap;
    gap: 4px;
  }
}

.timeline-msg {
  display: flex;
  gap: v.$spacing-sm;
  align-items: flex-start;

  &--user {
    flex-direction: row-reverse;

    .timeline-msg__body {
      align-items: flex-end;
    }

    .timeline-msg__header {
      flex-direction: row-reverse;
    }

    .timeline-msg__content {
      background: rgba($color-agent-implementor, 0.1);
      border-radius: $border-radius-md $border-radius-sharp $border-radius-md $border-radius-md;
    }
  }

  &--agent {
    .timeline-msg__content {
      background: rgba(255, 255, 255, 0.04);
      border-radius: $border-radius-sharp $border-radius-md $border-radius-md $border-radius-md;
    }
  }

  &__avatar {
    width: 32px;
    height: 32px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.02em;

    // USER identity: brand-yellow avatar + initials (matches the nav avatar orb),
    // visually distinct from the agent role-color badges.
    &--user {
      background: rgba($color-brand-yellow, 0.18);
      color: $color-brand-yellow;
      border-radius: 8px;
    }
  }

  &__body {
    display: flex;
    flex-direction: column;
    gap: v.$spacing-xs;
    max-width: calc(100% - 44px);
  }

  &__header {
    display: flex;
    align-items: center;
    gap: v.$spacing-xs;
    flex-wrap: wrap;
  }

  &__sender {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: capitalize;

    &--user {
      color: $color-brand-yellow;
    }
  }

  &__time {
    font-size: 0.68rem;
    color: var(--text-muted);
  }

  &__type-chip,
  &__action-flag {
    font-size: 0.65rem;
    font-weight: 600;
    padding: 1px 6px;
    text-transform: lowercase;
  }

  &__action-flag {
    background: rgba($color-agent-analyzer, 0.15);
    color: $color-agent-analyzer;
    border-radius: $border-radius-default;
    display: inline-flex;
    align-items: center;
    gap: 3px;
  }

  &__content {
    font-size: 0.83rem;
    line-height: 1.55;
    color: $color-text-primary;
    padding: v.$spacing-sm v.$spacing-md;
    white-space: pre-wrap;
    word-break: break-word;
  }
}
</style>
