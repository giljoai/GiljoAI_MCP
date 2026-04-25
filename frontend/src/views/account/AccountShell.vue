<template>
  <v-container>
    <!-- Page Header -->
    <h1 class="text-h4 mb-2">Account</h1>
    <p class="text-subtitle-1 mb-4 settings-subtitle">Profile, plan, and account management</p>

    <!-- Sub-tab Pills (sub-routes) -->
    <div class="pill-toggle-row">
      <router-link
        v-for="tab in tabs"
        :key="tab.name"
        v-slot="{ navigate, isActive, isExactActive }"
        :to="{ name: tab.name }"
        custom
      >
        <button
          class="pill-toggle smooth-border"
          :class="{ 'pill-toggle--active': isActive || isExactActive }"
          :data-test="tab.dataTest"
          @click="navigate"
        >
          <v-icon size="16" class="pill-toggle-icon">{{ tab.icon }}</v-icon>
          {{ tab.label }}
        </button>
      </router-link>
    </div>

    <!-- Sub-route content -->
    <div class="pill-tabs-content">
      <router-view />
    </div>
  </v-container>
</template>

<script setup>
const tabs = [
  {
    name: 'AccountProfile',
    label: 'Profile',
    icon: 'mdi-account',
    dataTest: 'account-profile-tab',
  },
  {
    name: 'AccountBilling',
    label: 'Billing',
    icon: 'mdi-credit-card-outline',
    dataTest: 'account-billing-tab',
  },
  {
    name: 'AccountDanger',
    label: 'Danger Zone',
    icon: 'mdi-alert-octagon-outline',
    dataTest: 'account-danger-tab',
  },
]
</script>

<style lang="scss" scoped>
@use '../../styles/design-tokens' as *;

.settings-subtitle {
  color: var(--text-muted);
}

/* Pill toggle row -- mirrors UserSettings/SystemSettings shell pattern. */
.pill-toggle-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.pill-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: $border-radius-pill;
  padding: 8px 18px;
  font-size: 0.78rem;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: background $transition-normal, color $transition-normal, box-shadow $transition-normal;
  background: transparent;
  color: var(--text-muted);
  border: none;
  --smooth-border-color: #{$color-pill-border};
}

.pill-toggle:hover {
  color: $color-text-hover;
}

.pill-toggle--active,
.pill-toggle--active:hover {
  background: rgba($color-brand-yellow, 0.12);
  color: $color-brand-yellow;
  box-shadow: none;
}

.pill-toggle-icon {
  flex-shrink: 0;
}

.pill-tabs-content {
  padding: 16px 0;
}
</style>
