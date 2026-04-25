<template>
  <div class="danger-page" data-test="danger-page">
    <h2 class="text-h6 mb-1">Danger Zone</h2>
    <p class="text-body-2 mb-4 danger-subtitle">
      Account-level actions. These are permanent — proceed carefully.
    </p>

    <!-- Export card (still stubbed — wired by FE-0844) -->
    <div
      class="danger-card smooth-border"
      data-test="export-data-card"
      :style="{ '--card-accent': 'var(--brand-yellow, #ffc300)' }"
    >
      <div
        class="danger-card-icon"
        :style="{ background: 'rgba(255,195,0,0.12)', color: 'var(--brand-yellow, #ffc300)' }"
      >
        <v-icon size="20">mdi-download-outline</v-icon>
      </div>
      <div class="danger-card-body">
        <div class="danger-card-title">Export my data</div>
        <div class="danger-card-desc">
          Download a copy of your products, projects, jobs, and 360 memory.
        </div>
      </div>
      <div class="danger-card-action">
        <v-chip size="small" color="warning" variant="tonal">Coming soon</v-chip>
      </div>
    </div>

    <!-- Delete card (SaaS-only — wired by SAAS-022) -->
    <div
      v-if="isSaas"
      class="danger-card danger-card--enabled smooth-border"
      data-test="delete-account-card"
      :style="{ '--card-accent': 'rgb(var(--v-theme-error))' }"
    >
      <div
        class="danger-card-icon danger-card-icon--danger"
      >
        <v-icon size="20">mdi-trash-can-outline</v-icon>
      </div>
      <div class="danger-card-body">
        <div class="danger-card-title danger-card-title--danger">Delete my account</div>
        <div class="danger-card-desc">
          Permanently remove your account and tenant data. We'll email you a
          confirmation link with a 24-hour window before anything is changed.
        </div>
      </div>
      <div class="danger-card-action">
        <v-btn
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
import { ref, shallowRef, computed, onMounted } from 'vue'
import configService from '@/services/configService'

const showDeleteDialog = ref(false)
const DeleteAccountDialog = shallowRef(null)

const isSaas = computed(() => configService.getEdition() !== 'community')

// CE-export safety: use Vite's static glob discovery so the import string
// is *not* statically bound to a path that may have been stripped from the
// CE tree. In CE builds saas/ is removed before `vite build` runs, the glob
// resolves to an empty map, and DeleteAccountDialog stays null (and the
// gating v-if above keeps the card off the page anyway). Same pattern as
// main.js uses to load saas/routes/index.js.
const dlgLoaders = import.meta.glob('@/saas/components/DeleteAccountDialog.vue')

onMounted(async () => {
  if (!isSaas.value) return
  const [loader] = Object.values(dlgLoaders)
  if (!loader) return
  try {
    const mod = await loader()
    DeleteAccountDialog.value = mod.default
  } catch (e) {
    console.warn('[DangerPage] DeleteAccountDialog unavailable:', e?.message)
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

.danger-card-desc {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.45;
}

.danger-card-action {
  flex-shrink: 0;
  align-self: center;
}
</style>
