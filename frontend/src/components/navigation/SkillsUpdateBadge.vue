<template>
  <v-tooltip
    v-if="showBadge"
    location="right"
    max-width="300"
  >
    <template #activator="{ props: tipProps }">
      <div
        v-bind="tipProps"
        class="skills-badge"
        data-testid="skills-update-badge"
        role="status"
        tabindex="0"
        aria-label="New agent skills available"
      >
        <v-icon size="16" class="skills-badge-icon">mdi-arrow-up-circle</v-icon>
        <v-btn
          icon
          variant="text"
          size="x-small"
          class="skills-dismiss"
          data-testid="skills-dismiss-btn"
          aria-label="Dismiss skills update notification"
          @click.stop="handleDismiss"
        >
          <v-icon size="12">mdi-close</v-icon>
        </v-btn>
      </div>
    </template>
    <div class="skills-tooltip-content">
      <div class="font-weight-medium mb-1">New skills available</div>
      <div class="text-caption">
        Run <code>giljo_setup</code> to update your agent templates.
      </div>
    </div>
  </v-tooltip>
</template>

<script setup>
import { onMounted } from 'vue'
import { useSkillsVersion } from '@/composables/useSkillsVersion'

const { showBadge, serverVersion, checkServerVersion, dismiss } = useSkillsVersion()

function handleDismiss() {
  dismiss(serverVersion.value)
}

onMounted(() => {
  checkServerVersion()
})
</script>

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;

.skills-badge {
  position: relative;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all $transition-normal ease;
  background: rgba($color-accent-success, 0.15);

  &:hover {
    background: rgba($color-accent-success, 0.25);
    transform: scale(1.08);
  }

  &:active {
    transform: scale(0.95);
  }

  &:focus-visible {
    outline: 2px solid $color-accent-success;
    outline-offset: 2px;
  }
}

.skills-badge-icon {
  color: $color-accent-success;
}

.skills-dismiss {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 18px !important; /* !important: override Vuetify v-btn min-width */
  height: 18px !important; /* !important: override Vuetify v-btn min-height */
  background: rgb(var(--v-theme-surface));
  border-radius: 50%;
  opacity: 0;
  transition: opacity $transition-normal ease;

  .skills-badge:hover & {
    opacity: 1;
  }
}

.skills-tooltip-content code {
  color: $color-brand-yellow;
  background: rgba($color-brand-yellow, 0.1);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 0.8rem;
}

@media (max-width: 1024px) {
  .skills-badge {
    width: 44px;
    height: 44px;
  }
}
</style>
