<template>
  <!-- Integration Reminder -->
  <transition name="reminder-fade">
    <div
      v-if="showInteg"
      class="onboard-reminder smooth-border"
    >
      <button class="onboard-close" aria-label="Dismiss" @click="$emit('dismiss:integration')">
        <v-icon size="16">mdi-close</v-icon>
      </button>
      <div class="onboard-body">
        <v-img
          src="/giljo_YW_Face.svg"
          width="36"
          height="36"
          class="onboard-avatar"
          alt="GiljoAI"
        />
        <div class="onboard-text">
          <span>Hey! Just a reminder that you can enable</span>
          <span class="onboard-integ-badge onboard-integ-badge--git">
            <v-icon size="14">mdi-github</v-icon> Git
          </span>
          <span>and</span>
          <span class="onboard-integ-badge onboard-integ-badge--serena">
            <v-avatar size="14" rounded="0" class="onboard-serena-icon">
              <v-img src="/Serena.png" alt="Serena" />
            </v-avatar>
            Serena MCP
          </span>
          <span>integrations in the Connect settings.</span>
        </div>
      </div>
      <router-link to="/tools" class="onboard-link">
        <v-icon size="14">mdi-puzzle</v-icon>
        Go to Tools
      </router-link>
    </div>
  </transition>

  <!-- Agent & Context Reminder -->
  <transition name="reminder-fade">
    <div
      v-if="showAgent"
      class="onboard-reminder smooth-border"
    >
      <button class="onboard-close" aria-label="Dismiss" @click="$emit('dismiss:agent')">
        <v-icon size="16">mdi-close</v-icon>
      </button>
      <div class="onboard-body">
        <v-img
          src="/giljo_YW_Face.svg"
          width="36"
          height="36"
          class="onboard-avatar"
          alt="GiljoAI"
        />
        <div class="onboard-text">
          Hello! Did you know you can tune your agent templates in the
          <strong>Agent Template Manager</strong>? You are currently working with
          the default agents. Make them yours! There is also
          <strong>Context tuning</strong> you can adjust in the Context settings.
          Both can be found in the Tools menu.
        </div>
      </div>
      <router-link to="/tools" class="onboard-link">
        <v-icon size="14">mdi-cog</v-icon>
        Go to Tools
      </router-link>
    </div>
  </transition>
</template>

<script setup>
defineProps({
  showInteg: { type: Boolean, default: false },
  showAgent: { type: Boolean, default: false },
})

defineEmits(['dismiss:integration', 'dismiss:agent'])
</script>

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;

.onboard-reminder {
  position: relative;
  background: $elevation-raised;
  border-radius: $border-radius-rounded;
  padding: 18px 20px 14px;
  margin-bottom: 16px;
  --smooth-border-color: rgba(255, 195, 0, 0.18);
}

.onboard-close {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 50%;
  transition: background $transition-fast, color $transition-fast;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    color: $color-text-primary;
  }
}

.onboard-body {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.onboard-avatar {
  flex-shrink: 0;
  margin-top: 2px;
}

.onboard-text {
  font-size: 0.85rem;
  line-height: 1.55;
  color: $color-text-secondary;
  padding-right: 20px;

  strong {
    color: $color-text-primary;
  }
}

.onboard-integ-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 1px 8px;
  border-radius: 6px;
  font-weight: 500;
  font-size: 0.82rem;
  vertical-align: middle;
}

.onboard-integ-badge--git {
  background: rgba(255, 255, 255, 0.08);
  color: $color-text-primary;
}

.onboard-integ-badge--serena {
  background: rgba(139, 92, 246, 0.12);
  color: #b794f6;
}

.onboard-serena-icon {
  flex-shrink: 0;
}

.onboard-link {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 10px;
  font-size: 0.78rem;
  font-weight: 500;
  color: $color-brand-yellow;
  text-decoration: none;
  transition: color $transition-fast;

  &:hover {
    color: $color-brand-yellow-hover;
  }
}

/* Fade transition */
.reminder-fade-enter-active,
.reminder-fade-leave-active {
  transition: opacity $transition-normal, transform $transition-normal;
}

.reminder-fade-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}

.reminder-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
