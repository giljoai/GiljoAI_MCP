<template>
  <div class="step-complete">
    <!-- Header -->
    <div class="complete-header">
      <v-icon size="36" class="complete-icon success-icon">
        mdi-check-circle
      </v-icon>
      <h2 class="complete-title">You're all set!</h2>
      <p class="complete-subtitle">
        Your AI coding tools are connected and ready. Here's what to do next.
      </p>
    </div>

    <!-- Go to Home -->
    <div class="dashboard-link-area" style="margin-top: 24px;">
      <v-btn
        color="primary"
        variant="flat"
        class="card-btn"
        @click="handleDashboard"
      >
        Continue
      </v-btn>
    </div>
  </div>
</template>

<script setup>
const emit = defineEmits(['complete'])

function handleDashboard() {
  emit('complete', { action: 'home', route: '/home' })
}
</script>

<style lang="scss" scoped>
@use '../../styles/variables' as *;
@use '../../styles/design-tokens' as *;

.step-complete {
  max-width: 780px;
  margin: 0 auto;
}

/* Header */
.complete-header {
  text-align: center;
  margin-bottom: 32px;
}

.complete-icon {
  margin-bottom: 12px;
}

.success-icon {
  color: $gradient-brand-end;
}

.complete-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: $color-text-primary;
  margin: 0 0 8px;
}

.complete-subtitle {
  font-size: 0.875rem;
  color: $lightest-blue;
  margin: 0;
  line-height: 1.5;
}

.card-btn {
  text-transform: none;
  font-weight: 600;
  font-size: 0.8125rem;
  letter-spacing: 0.04em;
  border-radius: $border-radius-sharp;
  min-width: 140px;
}

/* Dashboard link */
.dashboard-link-area {
  text-align: center;
  padding-top: 4px;
}

.dashboard-link {
  font-size: 0.8125rem;
  color: $lightest-blue;
  cursor: pointer;
  text-decoration: none;
  transition: color 250ms ease-out, text-decoration 250ms ease-out;
}

.dashboard-link:hover,
.dashboard-link:focus-visible {
  color: $color-brand-yellow;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.dashboard-link:focus-visible {
  outline: 2px solid $color-brand-yellow;
  outline-offset: 2px;
  border-radius: $border-radius-sharp;
}

</style>
