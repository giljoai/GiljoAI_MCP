<template>
  <div class="thread-list" data-testid="thread-list">
    <!-- Filter controls -->
    <div class="thread-list__filters">
      <v-text-field
        v-model="searchQuery"
        placeholder="Search threads..."
        prepend-inner-icon="mdi-magnify"
        variant="solo"
        density="compact"
        flat
        hide-details
        class="thread-list__search mb-2"
        clearable
        data-testid="thread-search"
        @update:model-value="onSearchChange"
        @click:clear="onSearchClear"
      />
      <div class="thread-list__filter-row">
        <v-select
          v-model="localFilters.status"
          :items="statusOptions"
          item-title="label"
          item-value="value"
          placeholder="Status"
          variant="solo"
          density="compact"
          flat
          hide-details
          clearable
          class="thread-list__filter-select"
          data-testid="filter-status"
          @update:model-value="onFilterChange"
        />
      </div>
    </div>

    <!-- Thread rows -->
    <div class="thread-list__rows" data-testid="thread-rows">
      <div v-if="commHub.loading" class="thread-list__empty">
        <v-progress-circular indeterminate size="20" />
      </div>

      <div
        v-else-if="displayThreads.length === 0"
        class="thread-list__empty"
        data-testid="thread-list-empty"
      >
        No threads found.
      </div>

      <div
        v-for="thread in displayThreads"
        :key="thread.thread_id"
        class="thread-row smooth-border"
        :class="{
          'thread-row--selected': commHub.selectedThreadId === thread.thread_id,
          'thread-row--attention':
            commHub.unreadFor(thread.thread_id) > 0 ||
            thread.next_action_owner === userStore.currentUser?.id,
        }"
        data-testid="thread-row"
        @click="onSelect(thread.thread_id)"
      >
        <!-- Badge slot: unread count + baton indicator -->
        <div class="thread-row__badge-slot" data-testid="thread-badge-slot">
          <!-- Unread count badge -->
          <span
            v-if="commHub.unreadFor(thread.thread_id) > 0"
            class="thread-row__unread-badge smooth-border"
            :style="unreadBadgeStyle()"
            data-testid="unread-badge"
          >
            {{ commHub.unreadFor(thread.thread_id) > 99 ? '99+' : commHub.unreadFor(thread.thread_id) }}
          </span>
          <!-- Baton chip: your turn -->
          <span
            v-else-if="thread.next_action_owner === userStore.currentUser?.id"
            class="thread-row__baton-chip smooth-border"
            :style="batonChipStyle()"
            data-testid="baton-chip"
            title="Your turn"
          >
            <v-icon size="10" class="mr-1">mdi-account-arrow-right</v-icon>
          </span>
        </div>

        <div class="thread-row__body">
          <div class="thread-row__top">
            <button
              class="thread-row__chat-id"
              type="button"
              data-testid="thread-chat-id"
              :title="`Copy thread id\n${thread.thread_id}`"
              @click.stop="onCopyThreadId(thread)"
            >
              {{ thread.chat_id ? formatChatId(thread.chat_id) : '—' }}
              <v-icon size="11" class="thread-row__copy-icon">mdi-content-copy</v-icon>
            </button>
            <span
              class="thread-row__status smooth-border"
              :style="statusBadgeStyle(thread.status)"
              data-testid="thread-status-badge"
            >
              {{ thread.status }}
            </span>
          </div>
          <div class="thread-row__subject" data-testid="thread-subject">
            {{ thread.subject || '(no subject)' }}
          </div>
          <div class="thread-row__meta">
            <span class="thread-row__time" data-testid="thread-time">
              {{ formatTime(thread.last_activity_at || thread.created_at) }}
            </span>
          </div>
        </div>

        <!-- Delete (soft) — low-emphasis until hover. FE-9012c (D1): a PROJECT-BOUND
             thread shares its project's lifecycle (non-deletable while the project
             lives, §2.5 guard), so it shows NO delete affordance. Only standalone
             (town-square) threads can be deleted from the Hub. -->
        <button
          v-if="!thread.project_id"
          class="thread-row__delete"
          type="button"
          title="Delete thread"
          aria-label="Delete thread"
          data-testid="thread-delete"
          @click.stop="onRequestDelete(thread)"
        >
          <v-icon size="15">mdi-trash-can-outline</v-icon>
        </button>
      </div>
    </div>

    <!-- Soft-delete confirmation -->
    <BaseDialog
      v-model="showDeleteDialog"
      type="danger"
      title="Delete Thread?"
      confirm-label="Delete"
      size="sm"
      :loading="deleting"
      data-testid="thread-delete-dialog"
      @confirm="onConfirmDelete"
      @cancel="showDeleteDialog = false"
    >
      <p class="mb-3">
        Delete thread
        <strong>{{ threadToDelete?.chat_id ? formatChatId(threadToDelete.chat_id) : '' }}</strong>
        <span v-if="threadToDelete?.subject">— "{{ threadToDelete.subject }}"</span>?
      </p>
      <v-alert type="info" variant="tonal" density="compact">
        The thread is removed from the Message Hub. Its message history is retained
        but no longer shown.
      </v-alert>
    </BaseDialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useCommHubStore } from '@/stores/commHubStore'
import { useUserStore } from '@/stores/user'
import { getAgentColor } from '@/config/agentColors'
import { hexToRgba } from '@/utils/colorUtils'
import { useClipboard } from '@/composables/useClipboard'
import { useToast } from '@/composables/useToast'
import BaseDialog from '@/components/common/BaseDialog.vue'

const commHub = useCommHubStore()
const userStore = useUserStore()
const { copy } = useClipboard()
const { showToast } = useToast()

const emit = defineEmits(['select'])

// FE-9012c (D2): which slice of the thread list to render. 'all' keeps the
// pre-two-tab behavior (used by any caller that doesn't split); 'project' shows
// only project-bound threads, 'town' only standalone. Search spans all scopes.
const props = defineProps({
  scope: {
    type: String,
    default: 'all',
    validator: (v) => ['all', 'project', 'town'].includes(v),
  },
})

// ---- soft delete ----
const showDeleteDialog = ref(false)
const threadToDelete = ref(null)
const deleting = ref(false)

function onRequestDelete(thread) {
  threadToDelete.value = thread
  showDeleteDialog.value = true
}

async function onConfirmDelete() {
  const thread = threadToDelete.value
  if (!thread?.thread_id) return
  deleting.value = true
  try {
    await commHub.deleteThread(thread.thread_id)
    showToast({ type: 'success', message: 'Thread deleted.' })
    showDeleteDialog.value = false
    threadToDelete.value = null
  } catch (err) {
    const msg = err?.response?.data?.detail || err?.message || 'Failed to delete thread.'
    showToast({ type: 'error', message: msg })
  } finally {
    deleting.value = false
  }
}

// Copy the thread id agents use (thread_id UUID) — the chip shows the friendly
// CHT-#### label but the copyable value is the real thread id (FE-6121 DoD-2).
async function onCopyThreadId(thread) {
  if (!thread?.thread_id) return
  const ok = await copy(thread.thread_id)
  showToast(
    ok
      ? { type: 'success', message: 'Thread id copied.' }
      : { type: 'error', message: 'Browser blocked the copy — select and copy manually.' },
  )
}

// ---- search ----
const searchQuery = ref('')
const searchResults = ref(null) // null = not searching; array = search results

let searchDebounce = null
function onSearchChange(val) {
  clearTimeout(searchDebounce)
  if (!val || val.trim() === '') {
    searchResults.value = null
    return
  }
  searchDebounce = setTimeout(async () => {
    const results = await commHub.searchThreads(val.trim())
    searchResults.value = results
  }, 350)
}

function onSearchClear() {
  searchResults.value = null
}

// ---- filters ----
const localFilters = ref({
  status: null,
})

const statusOptions = [
  { label: 'Open', value: 'open' },
  { label: 'Closed', value: 'closed' },
  { label: 'Pending', value: 'pending' },
  { label: 'Resolved', value: 'resolved' },
]

function onFilterChange() {
  commHub.filters.status = localFilters.value.status || null
  commHub.loadThreads(commHub.filters)
}

// ---- display list ----
const displayThreads = computed(() => {
  // Search spans every scope (a match in either tab should surface).
  if (searchResults.value !== null) return searchResults.value
  if (props.scope === 'project') return commHub.projectThreadList
  if (props.scope === 'town') return commHub.townSquareThreadList
  return commHub.threadList
})

// ---- selection ----
function onSelect(threadId) {
  commHub.selectThread(threadId)
  emit('select', threadId)
}

// ---- formatters ----
function formatChatId(chatId) {
  if (!chatId) return ''
  const match = String(chatId).match(/(\d+)$/)
  if (match) return `CHT-${String(match[1]).padStart(4, '0')}`
  return `CHT-${chatId}`
}

function formatTime(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    const now = new Date()
    const diffMs = now - d
    const diffMins = Math.floor(diffMs / 60000)
    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    return d.toLocaleDateString()
  } catch {
    return ''
  }
}

// Status badge: tinted. Hex values derived from getAgentColor() — the canonical
// JS token source for agent/semantic palette colors (no hardcoded hex literals).
const STATUS_AGENT_MAP = {
  open: 'implementer',    // sky-blue — active/positive
  closed: 'reviewer',    // lavender — neutral/done
  pending: 'tester',     // warm-yellow — waiting
  resolved: 'documenter', // mint-green — success
  default: 'orchestrator',
}

function statusBadgeStyle(status) {
  const agentName = STATUS_AGENT_MAP[status?.toLowerCase()] || STATUS_AGENT_MAP.default
  const hex = getAgentColor(agentName)?.hex
  return {
    backgroundColor: hexToRgba(hex, 0.15),
    color: hex,
    borderRadius: '8px',
  }
}

// Unread count badge: tinted implementer (sky-blue) — active/new
function unreadBadgeStyle() {
  const hex = getAgentColor('implementer')?.hex
  return {
    backgroundColor: hexToRgba(hex, 0.2),
    color: hex,
    borderRadius: '8px',
  }
}

// Baton chip: tinted orchestrator (warm-gold) — action required
function batonChipStyle() {
  const hex = getAgentColor('orchestrator')?.hex
  return {
    backgroundColor: hexToRgba(hex, 0.18),
    color: hex,
    borderRadius: '8px',
  }
}
</script>

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;
@use '../../styles/variables' as v;

.thread-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;

  &__filters {
    padding: v.$spacing-md v.$spacing-md v.$spacing-sm;
    flex-shrink: 0;
  }

  // Search + filter inputs: match the Projects filter bar — solo+flat field with
  // an inset smooth-border (not Vuetify's outline) and a brand-yellow focus ring.
  &__search {
    :deep(.v-field) {
      font-size: 0.82rem;
      box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255, 255, 255, 0.10));
      border-radius: $border-radius-default;
    }
    :deep(.v-field:focus-within) {
      box-shadow: inset 0 0 0 1px rgba($color-brand-yellow, 0.3);
    }
  }

  &__filter-row {
    display: flex;
    gap: v.$spacing-sm;
    margin-top: v.$spacing-xs;
  }

  &__filter-select {
    flex: 1;
    :deep(.v-field) {
      font-size: 0.78rem;
      box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255, 255, 255, 0.10));
      border-radius: $border-radius-default;
    }
    :deep(.v-field:focus-within) {
      box-shadow: inset 0 0 0 1px rgba($color-brand-yellow, 0.3);
    }
  }

  &__rows {
    flex: 1;
    overflow-y: auto;
    padding: v.$spacing-sm;
  }

  &__empty {
    padding: v.$spacing-lg v.$spacing-md;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.82rem;
  }
}

.thread-row {
  display: flex;
  align-items: flex-start;
  gap: v.$spacing-sm;
  padding: v.$spacing-sm v.$spacing-md;
  margin-bottom: v.$spacing-sm;
  border-radius: $border-radius-md;
  background: $elevation-raised;
  cursor: pointer;
  transition: $transition-all-fast;

  &:hover {
    background: $elevation-elevated;
  }

  // Selected: brand-accent ring via the smooth-border CSS var (no extra border).
  &--selected {
    --smooth-border-color: #{rgba($color-brand-yellow, 0.4)};
    background: rgba($color-brand-yellow, 0.07);
  }

  // Attention (unread / your turn) when not selected: subtle implementer-tint ring.
  &--attention:not(.thread-row--selected) {
    --smooth-border-color: #{rgba($color-agent-implementor, 0.35)};
  }

  &__badge-slot {
    width: 20px;
    min-width: 20px;
    flex-shrink: 0;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: 2px;
  }

  &__unread-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.62rem;
    font-weight: 700;
    min-width: 16px;
    height: 16px;
    padding: 0 4px;
    line-height: 1;
  }

  &__baton-chip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 16px;
    width: 16px;
  }

  &__body {
    flex: 1;
    min-width: 0;
  }

  &__top {
    display: flex;
    align-items: center;
    gap: v.$spacing-xs;
    flex-wrap: wrap;
    margin-bottom: 2px;
  }

  &__chat-id {
    display: inline-flex;
    align-items: center;
    gap: v.$spacing-xs;
    padding: 0;
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 0.7rem;
    font-weight: 700;
    color: var(--text-muted);
    letter-spacing: 0.03em;
    font-family: 'IBM Plex Mono', monospace;
    transition: color $transition-fast;

    &:hover {
      color: $color-brand-yellow;
    }
  }

  // Always visible (was hover-only, so it read as "no copy button") — dims to
  // full strength on hover. Tooltip + click copy the real thread id (UUID).
  &__copy-icon {
    opacity: 0.5;
    transition: opacity $transition-fast;
  }

  &__chat-id:hover &__copy-icon {
    opacity: 0.9;
  }

  // Soft-delete trash: low-emphasis until hover, then danger-magenta.
  &__delete {
    flex-shrink: 0;
    align-self: flex-start;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    padding: 0;
    border: none;
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    border-radius: $border-radius-sharp;
    opacity: 0.55;
    transition: opacity $transition-fast, color $transition-fast, background $transition-fast;

    &:hover {
      opacity: 1;
      color: $color-accent-danger;
      background: rgba($color-accent-danger, 0.12);
    }
  }

  &__status {
    font-size: 0.68rem;
    font-weight: 600;
    padding: 1px 6px;
    text-transform: capitalize;
  }

  &__subject {
    font-size: 0.82rem;
    font-weight: 500;
    color: $color-text-primary;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &__meta {
    display: flex;
    align-items: center;
    gap: v.$spacing-sm;
    margin-top: v.$spacing-xs;
  }

  &__time {
    font-size: 0.7rem;
    color: var(--text-muted);
  }
}
</style>
