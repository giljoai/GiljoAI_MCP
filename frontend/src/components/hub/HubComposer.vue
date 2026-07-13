<template>
  <div class="hub-composer smooth-border" data-testid="hub-composer">
    <!-- Request Auto Check-in cadence (AutoCheckinControls reused) -->
    <AutoCheckinControls
      :enabled="loopEnabled"
      :interval="loopInterval"
      :orchestrator-running="false"
      label="Request Auto Check-in"
      tooltip="Request that the agent(s) on this thread check in every N minutes by re-polling for replies, until the thread is resolved or closed. Best-effort — a model may or may not comply; stop by telling the agent in conversation."
      class="hub-composer__loop"
      data-testid="hub-composer-loop"
      @update:checkin="onCheckinUpdate"
    />

    <!-- Your turn badge — shown when the selected thread's baton is on the operator -->
    <div v-if="isYourTurn" class="hub-composer__your-turn" data-testid="composer-your-turn">
      <span
        class="hub-composer__your-turn-badge smooth-border"
        :style="yourTurnBadgeStyle()"
      >
        <v-icon size="12" class="mr-1">mdi-account-arrow-right</v-icon>
        Your turn
      </span>
    </div>

    <!-- Broadcast / direct row -->
    <div class="hub-composer__controls">
      <div class="hub-composer__broadcast-row">
        <button
          class="hub-composer__toggle smooth-border"
          :class="{ 'hub-composer__toggle--active': isBroadcast }"
          data-testid="toggle-broadcast"
          @click="isBroadcast = true"
        >
          <v-icon size="14">mdi-bullhorn</v-icon>
          Broadcast
        </button>
        <button
          class="hub-composer__toggle smooth-border"
          :class="{ 'hub-composer__toggle--active': !isBroadcast }"
          data-testid="toggle-direct"
          @click="isBroadcast = false"
        >
          <v-icon size="14">mdi-account-arrow-right</v-icon>
          Direct
        </button>

        <!-- Agent dropdown — only shown for direct mode. Each item carries the
             agent's tinted color badge + abbrev, matching the Home-screen/timeline. -->
        <v-select
          v-if="!isBroadcast"
          v-model="selectedParticipant"
          :items="participantItems"
          item-title="display_name"
          item-value="participant_id"
          placeholder="To agent..."
          variant="solo"
          density="compact"
          flat
          hide-details
          clearable
          class="hub-composer__agent-select"
          data-testid="agent-select"
          @update:menu="onAgentMenu"
        >
          <template #selection="{ item }">
            <span
              class="agent-badge-sq agent-badge-sq--sm hub-composer__agent-badge"
              :style="agentBadgeStyle(item.display_name)"
              aria-hidden="true"
            >{{ agentAbbr(item.display_name) }}</span>
            <span class="hub-composer__agent-name">{{ item.display_name }}</span>
          </template>
          <template #item="{ item, props: itemProps }">
            <v-list-item v-bind="itemProps" :title="undefined" data-testid="agent-select-item">
              <template #prepend>
                <span
                  class="agent-badge-sq agent-badge-sq--sm"
                  :style="agentBadgeStyle(item.display_name)"
                  aria-hidden="true"
                >{{ agentAbbr(item.display_name) }}</span>
              </template>
              <v-list-item-title>{{ item.display_name }}</v-list-item-title>
            </v-list-item>
          </template>
        </v-select>
      </div>

      <!-- Message input -->
      <v-textarea
        v-model="content"
        placeholder="Type a message..."
        variant="solo"
        density="compact"
        flat
        rows="2"
        auto-grow
        hide-details
        class="hub-composer__input"
        data-testid="message-input"
        @keydown.enter.ctrl.prevent="onSend"
      />

      <!-- Send row -->
      <div class="hub-composer__send-row">
        <span class="hub-composer__hint">Ctrl+Enter to send</span>
        <v-btn
          :disabled="!canSend"
          :loading="sending"
          size="small"
          variant="tonal"
          color="primary"
          class="hub-composer__send-btn"
          data-testid="send-btn"
          @click="onSend"
        >
          <v-icon size="16" start>mdi-send</v-icon>
          Send
        </v-btn>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useCommHubStore } from '@/stores/commHubStore'
import { useUserStore } from '@/stores/user'
import { useToast } from '@/composables/useToast'
import { getAgentColor } from '@/config/agentColors'
import { hexToRgba } from '@/utils/colorUtils'
import AutoCheckinControls from '@/components/projects/AutoCheckinControls.vue'

const commHub = useCommHubStore()
const userStore = useUserStore()
const { showToast } = useToast()

/** True when the selected thread's baton points at the current user */
const isYourTurn = computed(() => {
  const thread = commHub.selectedThread
  return thread?.next_action_owner != null && thread.next_action_owner === userStore.currentUser?.id
})

function yourTurnBadgeStyle() {
  const hex = getAgentColor('orchestrator')?.hex
  return {
    backgroundColor: hexToRgba(hex, 0.18),
    color: hex,
    borderRadius: '8px',
  }
}

// Agent identity in the "To agent" dropdown — tinted color badge + abbrev from
// the same source of truth as the timeline/Home screen (FE-6122). No new map.
function agentBadgeStyle(name) {
  const hex = getAgentColor(name)?.hex
  return {
    backgroundColor: hexToRgba(hex, 0.2),
    color: hex,
  }
}

function agentAbbr(name) {
  if (!name) return '??'
  const parts = String(name).split(/[-_\s]+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return String(name).slice(0, 2).toUpperCase()
}

// ---- state ----
const content = ref('')
const isBroadcast = ref(true)
const selectedParticipant = ref(null)
const sending = ref(false)

// ---- Request Auto Check-in (slider) ----
// FE-6140: the slider enabled (interval != Off) → loop_directive: true, and the
// chosen interval rides along as loop_interval_minutes. The backend persists it on
// the loop_directive post and surfaces it on the get_my_turn/get_thread_history
// poll responses so a running agent re-reads the cadence and self-schedules a wake.
const loopEnabled = ref(false)
const loopInterval = ref(10)

function onCheckinUpdate(val) {
  loopEnabled.value = val.enabled
  if (val.interval != null) loopInterval.value = val.interval
}

// ---- participants ----
const participantItems = computed(() => {
  const threadId = commHub.selectedThreadId
  if (!threadId) return []
  return commHub.participantsFor(threadId).filter((p) => p.participant_type !== 'user')
})

// Participants are fetched once on thread-select, so a freshly join_thread'd agent
// would not appear in the "To agent" dropdown without a manual page refresh. Refetch
// at the moments the operator actually reaches for the dropdown — switching to Direct
// mode and opening the menu — so new joins show up reactively (FE-6121 DoD-3).
function refreshParticipants() {
  const threadId = commHub.selectedThreadId
  if (threadId) commHub.loadParticipants(threadId)
}

watch(isBroadcast, (broadcast) => {
  if (!broadcast) refreshParticipants()
})

function onAgentMenu(open) {
  if (open) refreshParticipants()
}

// ---- derived ----
const canSend = computed(() => {
  if (!commHub.selectedThreadId) return false
  if (!content.value.trim()) return false
  if (!isBroadcast.value && !selectedParticipant.value) return false
  return true
})

// ---- send ----
async function onSend() {
  if (!canSend.value) return
  const threadId = commHub.selectedThreadId
  const body = {
    content: content.value.trim(),
    loop_directive: loopEnabled.value ? true : undefined,
    // FE-6140: carry the chosen cadence so it round-trips to the backend.
    loop_interval_minutes: loopEnabled.value ? loopInterval.value : undefined,
  }
  if (!isBroadcast.value && selectedParticipant.value) {
    body.to_participant = selectedParticipant.value
  }

  sending.value = true
  try {
    await commHub.postMessage(threadId, body)
    content.value = ''
    showToast({ type: 'success', message: 'Message sent.' })
  } catch (err) {
    const msg = err?.response?.data?.detail || err?.message || 'Failed to send message.'
    showToast({ type: 'error', message: msg })
  } finally {
    sending.value = false
  }
}
</script>

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;
@use '../../styles/variables' as v;

.hub-composer {
  flex-shrink: 0;
  // Panel container echoing the project jobs-tab composer (MessageComposer):
  // raised surface + inset smooth-border + rounded corners.
  background: $elevation-raised;
  border-radius: $border-radius-rounded;
  margin: v.$spacing-sm v.$spacing-md v.$spacing-md;
  overflow: hidden;

  &__your-turn {
    padding: v.$spacing-xs v.$spacing-sm 0;
  }

  &__your-turn-badge {
    display: inline-flex;
    align-items: center;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 8px;
  }

  &__loop {
    // AutoCheckinControls already has its own border-bottom padding
  }

  &__controls {
    padding: v.$spacing-sm v.$spacing-sm v.$spacing-md;
    display: flex;
    flex-direction: column;
    gap: v.$spacing-sm;
  }

  &__broadcast-row {
    display: flex;
    align-items: center;
    gap: v.$spacing-xs;
    flex-wrap: wrap;
  }

  &__toggle {
    display: inline-flex;
    align-items: center;
    gap: v.$spacing-xs;
    padding: 4px 10px;
    border-radius: $border-radius-default;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    background: transparent;
    color: var(--text-muted);
    border: none;
    transition: background 0.15s ease, color 0.15s ease;

    &:hover {
      background: rgba(255, 255, 255, 0.06);
      color: var(--text-secondary);
    }

    &--active {
      background: rgba($color-brand-yellow, 0.14);
      color: $color-brand-yellow;
    }
  }

  &__agent-select {
    flex: 1;
    max-width: 220px;
    :deep(.v-field) {
      font-size: 0.78rem;
      background: $elevation-elevated;
      box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255, 255, 255, 0.10));
      border-radius: $border-radius-default;
    }
  }

  &__agent-badge {
    margin-right: v.$spacing-xs;
  }

  &__agent-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  // Filled message field matching MessageComposer: recessed elevated surface,
  // inset smooth-border, brand-yellow focus ring (no Vuetify outline).
  &__input {
    :deep(.v-field) {
      font-size: 0.85rem;
      background: $elevation-elevated;
      box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255, 255, 255, 0.10));
      border-radius: $border-radius-default;
    }
    :deep(.v-field:hover) {
      box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255, 255, 255, 0.14));
    }
    :deep(.v-field--focused) {
      box-shadow: inset 0 0 0 1px rgba($color-brand-yellow, 0.3);
    }
  }

  &__send-row {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: v.$spacing-sm;
  }

  &__hint {
    font-size: 0.68rem;
    color: var(--text-muted);
  }

  &__send-btn {
    min-width: 80px;
  }
}
</style>
