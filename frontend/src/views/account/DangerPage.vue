<template>
  <div class="danger-page" data-test="danger-page">
    <h2 class="text-h6 mb-1">Danger Zone</h2>
    <p class="text-body-2 mb-4 danger-subtitle">
      Account-level actions. These are permanent — proceed carefully.
    </p>

    <!--
      Download My Data (BE-5062 — GDPR data portability, CE-only).
      Hidden in saas/demo where this feature isn't offered.
      Server gates the endpoint itself; this v-if is just UX hygiene.
    -->
    <div
      v-if="isCe"
      class="danger-card danger-card--enabled smooth-border"
      data-test="download-my-data-section"
      :style="{ '--card-accent': 'var(--brand-yellow, #ffc300)' }"
    >
      <div
        class="danger-card-icon"
        :style="{ background: 'rgba(255,195,0,0.12)', color: 'var(--brand-yellow, #ffc300)' }"
      >
        <v-icon size="20">mdi-download-outline</v-icon>
      </div>
      <div class="danger-card-body">
        <div class="danger-card-title">Download my data</div>
        <div class="danger-card-desc">
          Download all your data as a portable ZIP. Includes products, projects,
          vision documents, agents, memory, tasks, and configuration. Credentials
          are redacted.
        </div>

        <!-- Progress feed (driven by WebSocket tenant:export_progress events). -->
        <div
          v-if="exporting || exportProgress"
          class="export-progress"
          data-test="export-progress"
        >
          <v-progress-linear
            :model-value="exportPercent"
            :indeterminate="exporting && !exportProgress"
            color="warning"
            height="4"
            class="mb-2"
          />
          <div
            class="export-progress-status"
            data-test="export-progress-status"
          >
            {{ exportStatusText }}
          </div>
        </div>

        <!-- Completed: download link + expiry + model counts. -->
        <div
          v-if="exportResult"
          class="export-result"
          data-test="export-result"
        >
          <a
            :href="exportResult.download_url"
            class="export-download-link"
            data-test="export-download-link"
            download
          >
            <v-icon size="16" class="mr-1">mdi-download</v-icon>
            Download tenant_export.zip
          </a>
          <div class="export-expiry" data-test="export-expiry">
            Link expires {{ expiresAtFormatted }}
          </div>
          <ul
            v-if="modelCountEntries.length"
            class="export-model-counts"
            data-test="export-model-counts"
          >
            <li
              v-for="[model, count] in modelCountEntries"
              :key="model"
            >
              <span class="model-name">{{ model }}</span>
              <span class="model-count">{{ count }}</span>
            </li>
          </ul>
        </div>

        <!-- Error surface. -->
        <div
          v-if="exportError"
          class="export-error"
          data-test="export-error"
        >
          {{ exportError }}
        </div>
      </div>
      <div class="danger-card-action">
        <v-btn
          color="warning"
          variant="flat"
          :loading="exporting"
          :disabled="exporting"
          data-test="generate-export-btn"
          @click="onGenerateExport"
        >
          {{ exportResult ? 'Generate again' : 'Generate export' }}
          <v-icon end>mdi-arrow-right</v-icon>
        </v-btn>
      </div>
    </div>

    <!-- Delete card (SaaS-only — wired by SAAS-022; cancel-pending added by SAAS-023) -->
    <div
      v-if="isSaas"
      class="danger-card danger-card--enabled smooth-border"
      data-test="delete-account-card"
      :style="{ '--card-accent': cardAccent }"
    >
      <div
        class="danger-card-icon"
        :class="{ 'danger-card-icon--danger': !hasPendingDeletion, 'danger-card-icon--warning': hasPendingDeletion }"
      >
        <v-icon size="20">{{ hasPendingDeletion ? 'mdi-clock-alert-outline' : 'mdi-trash-can-outline' }}</v-icon>
      </div>
      <div class="danger-card-body">
        <div
          class="danger-card-title"
          :class="{ 'danger-card-title--danger': !hasPendingDeletion, 'danger-card-title--warning': hasPendingDeletion }"
        >
          {{ hasPendingDeletion ? 'Pending account deletion' : 'Delete my account' }}
        </div>
        <div class="danger-card-desc">
          <template v-if="hasPendingDeletion">
            Your account is scheduled for permanent deletion on
            <strong>{{ accountStateStoreRef?.purgeAfterFormatted }}</strong>.
            You can still cancel and restore full access.
          </template>
          <template v-else>
            Permanently remove your account and tenant data. We'll email you a
            confirmation link with a 24-hour window before anything is changed.
          </template>
        </div>
      </div>
      <div class="danger-card-action">
        <!-- SAAS-023: when a deletion is pending or confirmed, the SAFE
             primary action is "Cancel pending deletion" (warning, not red). -->
        <v-btn
          v-if="hasPendingDeletion"
          color="warning"
          variant="flat"
          :loading="cancellingDeletion"
          data-test="cancel-pending-deletion-btn"
          @click="onCancelPendingDeletion"
        >
          Cancel pending deletion
          <v-icon end>mdi-arrow-right</v-icon>
        </v-btn>
        <v-btn
          v-else
          color="error"
          variant="flat"
          data-test="open-delete-account-dialog"
          @click="showDeleteDialog = true"
        >
          Delete account
          <v-icon end>mdi-arrow-right</v-icon>
        </v-btn>
      </div>
    </div>

    <!-- Lazy-load the SaaS-only dialog so the import never appears in CE bundles. -->
    <component
      :is="DeleteAccountDialog"
      v-if="isSaas && DeleteAccountDialog"
      v-model="showDeleteDialog"
    />
  </div>
</template>

<script setup>
/**
 * SAAS-022: Account "Danger Zone" sub-tab.
 *
 * Two stacked accent-bordered cards (Export, Delete) using the same
 * smooth-border + accent-stripe pattern as WelcomeView quick-launch cards.
 *
 * Edition gating:
 * - Export card is edition-neutral (still a stub for both editions).
 * - Delete card and its dialog are SaaS-only — gated via configService and
 *   the dialog is dynamically imported from saas/, so neither the import
 *   nor the deletion path strings end up in the CE bundle.
 */
import { ref, shallowRef, computed, onMounted, onBeforeUnmount } from 'vue'
import configService from '@/services/configService'
import { useToast } from '@/composables/useToast'
import api from '@/services/api'
import { useWebSocketV2 } from '@/composables/useWebSocket'

const showDeleteDialog = ref(false)
const DeleteAccountDialog = shallowRef(null)
const { showToast } = useToast()

// Edition flags. `getEdition()` returns 'community' for GILJO_MODE=ce, 'saas'
// for saas, 'demo' for demo. We use this for visibility of CE-only / SaaS-only
// affordances on this page (matches the existing pattern for the SaaS-only
// delete card). configService is the mode source of truth for components
// rendered well after initial navigation (ADR-002 § "Rule 1").
const isCe = computed(() => configService.getEdition() === 'community')
const isSaas = computed(() => configService.getEdition() !== 'community')

// ---------------------------------------------------------------------------
// BE-5062 — Download My Data
// ---------------------------------------------------------------------------
const exporting = ref(false)
const exportError = ref('')
// Latest WebSocket progress frame: { model, current, total, phase }.
const exportProgress = ref(null)
// Final result from POST /api/v1/account/export:
//   { download_url, expires_at, model_counts }
const exportResult = ref(null)

const exportPercent = computed(() => {
  const p = exportProgress.value
  if (!p) return 0
  if (p.phase === 'complete') return 100
  if (!p.total || p.total <= 0) return 0
  return Math.min(100, Math.round((p.current / p.total) * 100))
})

const exportStatusText = computed(() => {
  const p = exportProgress.value
  if (!p) return 'Preparing export…'
  if (p.phase === 'complete') {
    return p.records != null
      ? `Export complete — ${p.records} records.`
      : 'Export complete.'
  }
  // "exporting" phase — model + counts.
  const model = p.model || '…'
  return `Exporting ${model} (${p.current} / ${p.total})…`
})

const expiresAtFormatted = computed(() => {
  const iso = exportResult.value?.expires_at
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
})

const modelCountEntries = computed(() => {
  const counts = exportResult.value?.model_counts
  if (!counts || typeof counts !== 'object') return []
  return Object.entries(counts).sort(([a], [b]) => a.localeCompare(b))
})

// Subscribe to tenant:export_progress on the shared WebSocket connection.
// useWebSocketV2().on(...) returns an unsubscribe function — we capture both
// so saas/demo renders don't leak handlers and the explicit cleanup runs
// before the auto-cleanup that fires on component unmount.
const ws = useWebSocketV2()
let unsubscribeExportProgress = null

function handleExportProgress(payload) {
  // Payload is normalized to the flat data shape by the WS store; the data
  // field may be nested or flat depending on transport. Read defensively.
  const data = payload?.data && typeof payload.data === 'object' ? payload.data : payload
  if (!data) return
  exportProgress.value = {
    model: data.model ?? '',
    current: Number(data.current ?? 0),
    total: Number(data.total ?? 0),
    records: data.records != null ? Number(data.records) : null,
    phase: data.phase ?? 'exporting',
  }
}

async function onGenerateExport() {
  if (exporting.value) return
  exporting.value = true
  exportError.value = ''
  exportProgress.value = null
  exportResult.value = null

  // Subscribe lazily on first click so we don't pay handler cost for users
  // who never trigger an export.
  if (!unsubscribeExportProgress) {
    unsubscribeExportProgress = ws.on('tenant:export_progress', handleExportProgress)
  }

  try {
    const response = await api.account.exportMyData()
    const body = response?.data ?? response
    exportResult.value = {
      download_url: body?.download_url ?? '',
      expires_at: body?.expires_at ?? '',
      model_counts: body?.model_counts ?? {},
    }
    if (!exportResult.value.download_url) {
      throw new Error('Backend did not return a download URL.')
    }
  } catch (err) {
    // Backend exception handlers can return either { detail } (FastAPI default)
    // or { error_code, message, timestamp } (wrapped). Surface either, plus
    // the 403 "Data export is not available in this edition." case.
    const data = err?.response?.data
    const message =
      data?.detail ||
      data?.message ||
      err?.message ||
      'Could not generate export. Please try again.'
    exportError.value = message
    showToast({ message, type: 'error' })
  } finally {
    exporting.value = false
  }
}

// SAAS-023: lazy account-state store handle (CE-export safe).
const accountStateStoreRef = shallowRef(null)
const hasPendingDeletion = computed(
  () => accountStateStoreRef.value?.isAccountScheduledForDeletion ?? false,
)
const cardAccent = computed(() =>
  hasPendingDeletion.value ? 'var(--brand-yellow, #ffc300)' : 'rgb(var(--v-theme-error))',
)
const cancellingDeletion = ref(false)

async function onCancelPendingDeletion() {
  const store = accountStateStoreRef.value
  if (!store || cancellingDeletion.value) return
  cancellingDeletion.value = true
  try {
    await store.cancelDeletion()
    showToast({ message: 'Account deletion cancelled.', type: 'success' })
  } catch (err) {
    const detail = err?.response?.data?.detail
    showToast({
      message: detail || 'Could not cancel deletion. Please try again.',
      type: 'error',
    })
  } finally {
    cancellingDeletion.value = false
  }
}

// CE-export safety: use Vite's static glob discovery so the import string
// is *not* statically bound to a path that may have been stripped from the
// CE tree. In CE builds saas/ is removed before `vite build` runs, the glob
// resolves to an empty map, and DeleteAccountDialog stays null (and the
// gating v-if above keeps the card off the page anyway). Same pattern as
// main.js uses to load saas/routes/index.js.
const dlgLoaders = import.meta.glob('@/saas/components/DeleteAccountDialog.vue')

// SAAS-023: also lazy-load the account-state store so the Cancel-pending
// affordance can read deletion status. CE export drops both globs.
const acctStoreLoaders = import.meta.glob('@/saas/stores/useAccountStateStore.js')

onBeforeUnmount(() => {
  if (unsubscribeExportProgress) {
    try {
      unsubscribeExportProgress()
    } catch {
      /* useWebSocketV2 auto-cleanup will handle it anyway */
    }
    unsubscribeExportProgress = null
  }
})

onMounted(async () => {
  if (!isSaas.value) return
  const [loader] = Object.values(dlgLoaders)
  if (loader) {
    try {
      const mod = await loader()
      DeleteAccountDialog.value = mod.default
    } catch (e) {
      console.warn('[DangerPage] DeleteAccountDialog unavailable:', e?.message)
    }
  }
  const [storeLoader] = Object.values(acctStoreLoaders)
  if (storeLoader) {
    try {
      const mod = await storeLoader()
      const store = mod.useAccountStateStore()
      accountStateStoreRef.value = store
      // Refresh on mount in case the user landed here directly.
      store.fetchStatus()
    } catch (e) {
      console.warn('[DangerPage] account-state store unavailable:', e?.message)
    }
  }
})
</script>

<style lang="scss" scoped>
.danger-page {
  max-width: 720px;
  margin: 0 auto;
}

.danger-subtitle {
  color: var(--text-secondary);
}

.danger-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  background: rgb(var(--v-theme-surface));
  border-radius: 12px;
  position: relative;
  overflow: hidden;
  margin-bottom: 14px;
  transition: transform 200ms ease, box-shadow 200ms ease;
}

/* Left-edge accent stripe via CSS var (matches WelcomeView pattern). */
.danger-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 3px;
  background: var(--card-accent, transparent);
  opacity: 0.85;
}

.danger-card--enabled:hover {
  transform: translateY(-2px);
  box-shadow:
    inset 0 0 0 1px var(--smooth-border-color, rgba(255, 255, 255, 0.10)),
    0 8px 18px -6px rgba(0, 0, 0, 0.30);
}

.danger-card-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.danger-card-icon--danger {
  /* rgba() form gives ~12% tint of theme error without hardcoding hex. */
  background: rgba(var(--v-theme-error), 0.12);
  color: rgb(var(--v-theme-error));
}

.danger-card-body {
  flex: 1;
  min-width: 0;
}

.danger-card-title {
  font-size: 0.95rem;
  font-weight: 600;
  margin-bottom: 3px;
}

.danger-card-title--danger {
  color: rgb(var(--v-theme-error));
}

/* SAAS-023: SAFE-action variant — yellow accent for "Cancel pending deletion". */
.danger-card-icon--warning {
  background: rgba(255, 195, 0, 0.12);
  color: var(--brand-yellow, #ffc300);
}

.danger-card-title--warning {
  color: var(--brand-yellow, #ffc300);
}

.danger-card-desc {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.45;
}

.danger-card-action {
  flex-shrink: 0;
  align-self: center;
}

/* BE-5062: Download My Data — progress, result, error blocks
   Render inline below the description so the card grows naturally. */
.export-progress,
.export-result,
.export-error {
  margin-top: 12px;
}

.export-progress-status {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.45;
}

.export-download-link {
  display: inline-flex;
  align-items: center;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--brand-yellow, #ffc300);
  text-decoration: none;
}

.export-download-link:hover {
  text-decoration: underline;
}

.export-expiry {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-top: 2px;
}

.export-model-counts {
  list-style: none;
  padding: 0;
  margin: 8px 0 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 4px 12px;
}

.export-model-counts li {
  display: flex;
  justify-content: space-between;
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.export-model-counts .model-count {
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.export-error {
  font-size: 0.8rem;
  color: rgb(var(--v-theme-error));
  line-height: 1.45;
}
</style>
