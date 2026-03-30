<template>
  <div class="step-complete">
    <!-- Header -->
    <div class="complete-header">
      <v-icon size="36" color="#6bcf7f" class="complete-icon">
        mdi-check-circle
      </v-icon>
      <h2 class="complete-title">You're all set!</h2>
      <p class="complete-subtitle">
        Your AI coding tools are connected and ready. Here's what to do next.
      </p>
    </div>

    <!-- Launchpad cards -->
    <div class="launchpad-grid">
      <div
        v-for="card in cards"
        :key="card.action"
        class="launchpad-card smooth-border"
      >
        <div class="card-icon-wrap">
          <v-icon size="24" color="#ffc300">{{ card.icon }}</v-icon>
        </div>
        <h3 class="card-title">{{ card.title }}</h3>
        <p class="card-body">{{ card.body }}</p>
        <v-btn
          color="primary"
          variant="flat"
          class="card-btn"
          @click="handleCardClick(card)"
        >
          {{ card.buttonLabel }}
        </v-btn>
      </div>
    </div>

    <!-- Dashboard link -->
    <div class="dashboard-link-area">
      <span
        class="dashboard-link"
        role="button"
        tabindex="0"
        @click="handleDashboard"
        @keydown.enter.prevent="handleDashboard"
      >
        Go to Dashboard
      </span>
    </div>
  </div>
</template>

<script setup>
const emit = defineEmits(['complete'])

const cards = [
  {
    icon: 'mdi-package-variant-closed',
    title: 'Define Your Product',
    body: 'Create a product to organize projects, tasks, and agent configurations.',
    buttonLabel: 'OPEN PRODUCTS',
    action: 'products',
    route: '/products',
  },
  {
    icon: 'mdi-folder-open',
    title: 'Start a Project',
    body: 'Create your first project to begin orchestrating AI agents.',
    buttonLabel: 'OPEN PROJECTS',
    action: 'projects',
    route: '/projects',
  },
  {
    icon: 'mdi-checkbox-marked-outline',
    title: 'Track Your Work',
    body: 'Add tasks and ideas to your dashboard using /gil_add.',
    buttonLabel: 'OPEN TASKS',
    action: 'tasks',
    route: '/tasks',
  },
]

function handleCardClick(card) {
  emit('complete', { action: card.action, route: card.route })
}

function handleDashboard() {
  emit('complete', { action: 'dashboard', route: '/dashboard' })
}
</script>

<style scoped>
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

.complete-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #e1e1e1;
  margin: 0 0 8px;
}

.complete-subtitle {
  font-size: 0.875rem;
  color: #8f97b7;
  margin: 0;
  line-height: 1.5;
}

/* Launchpad grid */
.launchpad-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.launchpad-card {
  background: #1e3147;
  border-radius: 12px;
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  transition: box-shadow 250ms ease-out;
}

.launchpad-card:hover {
  box-shadow:
    inset 0 0 0 1px var(--smooth-border-color, #315074),
    0 4px 16px rgba(0, 0, 0, 0.25);
}

/* Icon circle */
.card-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(255, 195, 0, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.card-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #e1e1e1;
  margin: 0 0 8px;
}

.card-body {
  font-size: 0.8125rem;
  color: #8f97b7;
  line-height: 1.5;
  margin: 0 0 20px;
  flex: 1;
}

.card-btn {
  text-transform: none;
  font-weight: 600;
  font-size: 0.8125rem;
  letter-spacing: 0.04em;
  border-radius: 6px;
  min-width: 140px;
}

/* Dashboard link */
.dashboard-link-area {
  text-align: center;
  padding-top: 4px;
}

.dashboard-link {
  font-size: 0.8125rem;
  color: #8f97b7;
  cursor: pointer;
  text-decoration: none;
  transition: color 250ms ease-out, text-decoration 250ms ease-out;
}

.dashboard-link:hover,
.dashboard-link:focus-visible {
  color: #ffc300;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.dashboard-link:focus-visible {
  outline: 2px solid #ffc300;
  outline-offset: 2px;
  border-radius: 2px;
}

/* Responsive: stack on mobile */
@media (max-width: 599px) {
  .launchpad-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .launchpad-card {
    padding: 20px 16px;
  }
}

/* Responsive: tablet — 2+1 or maintain 3 */
@media (min-width: 600px) and (max-width: 960px) {
  .launchpad-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .launchpad-card:last-child {
    grid-column: 1 / -1;
    max-width: 50%;
    justify-self: center;
  }
}
</style>
