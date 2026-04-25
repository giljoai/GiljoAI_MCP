<template>
  <v-card variant="flat" class="smooth-border danger-card" data-test="danger-stub">
    <v-card-text class="pa-5">
      <h2 class="text-h6 mb-1">Danger Zone</h2>
      <p class="text-body-2 text-muted-a11y mb-4">
        Account-level actions. Both options are stubbed today -- coming with their respective backend wiring.
      </p>

      <div class="danger-row" data-test="export-data-row">
        <div class="danger-row-text">
          <div class="danger-row-title">Export my data</div>
          <div class="danger-row-desc">Download a copy of your products, projects, jobs, and 360 memory.</div>
        </div>
        <v-chip size="small" color="warning" variant="tonal" class="coming-soon-chip">Coming soon</v-chip>
      </div>

      <v-divider class="my-3" />

      <div class="danger-row" data-test="delete-account-row">
        <div class="danger-row-text">
          <div class="danger-row-title danger-row-title--danger">Delete my account</div>
          <div class="danger-row-desc">Permanently remove your account and associated tenant data.</div>
        </div>
        <v-chip size="small" color="error" variant="tonal" class="coming-soon-chip">Coming soon</v-chip>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
// Stub view -- SAAS-022 will wire actual delete-account endpoint; 0844 wires data export.
</script>

<style lang="scss" scoped>
.danger-card {
  max-width: 720px;
  margin: 0 auto;
}

.danger-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 0;
}

.danger-row-text {
  flex: 1;
  min-width: 0;
}

.danger-row-title {
  font-size: 0.95rem;
  font-weight: 600;
  margin-bottom: 2px;
}

.danger-row-title--danger {
  color: rgb(var(--v-theme-error));
}

.danger-row-desc {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.coming-soon-chip {
  flex-shrink: 0;
}
</style>
