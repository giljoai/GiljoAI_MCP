<template>
  <!-- Home-screen hint cards. Two reminders, harmonized to a single visual shape.
       Avatar intentionally omitted: GilMascot is rendered in the hero above. -->

  <transition name="hint-fade">
    <div
      v-if="showInteg && !bothIntegrationsEnabled"
      class="hint-card smooth-border"
    >
      <button class="hint-close" aria-label="Dismiss" @click="$emit('dismiss:integration')">
        <v-icon size="14">mdi-close</v-icon>
      </button>
      <p class="hint-text">
        Hey {{ username }}, heads up! You can enable <strong>Git</strong> and
        <strong>Serena MCP</strong> in connect settings.
        <span class="hint-signoff">-Gil</span>
      </p>
      <router-link to="/tools" class="hint-link">
        <v-icon size="13">mdi-tools</v-icon> Go to Tools
      </router-link>
    </div>
  </transition>

  <transition name="hint-fade">
    <div
      v-if="showAgent"
      class="hint-card smooth-border"
    >
      <button class="hint-close" aria-label="Dismiss" @click="$emit('dismiss:agent')">
        <v-icon size="14">mdi-close</v-icon>
      </button>
      <p class="hint-text">
        Did you know you can tune your <strong>agent templates</strong> in the Agent
        Template Manager? You're using the defaults ;). Make them yours! There's also
        <strong>context tuning</strong> in the Context settings. Both live under the
        Tools menu.
        <span class="hint-signoff">-Gil</span>
      </p>
      <router-link to="/tools" class="hint-link">
        <v-icon size="13">mdi-tools</v-icon> Go to Tools
      </router-link>
    </div>
  </transition>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  showInteg: { type: Boolean, default: false },
  showAgent: { type: Boolean, default: false },
  username: { type: String, default: 'Friend' },
  gitEnabled: { type: Boolean, default: false },
  serenaEnabled: { type: Boolean, default: false },
})

defineEmits(['dismiss:integration', 'dismiss:agent'])

const bothIntegrationsEnabled = computed(() => props.gitEnabled && props.serenaEnabled)
</script>

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;

/* Match the surrounding Home cards (Quick Launch, Recent Projects, Setup CTA):
   theme surface background + default smooth-border, no tint. */
.hint-card {
  position: relative;
  background: rgb(var(--v-theme-surface));
  border-radius: $border-radius-rounded;
  padding: 12px 16px 10px;
  margin: 0 auto 10px;

  &:last-child {
    margin-bottom: 0;
  }
}

.hint-close {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 22px;
  height: 22px;
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

.hint-text {
  margin: 0;
  padding-right: 22px;
  font-size: 0.8rem;
  line-height: 1.5;
  color: $color-text-primary;

  strong {
    color: $color-text-primary;
    font-weight: 700;
  }
}

.hint-signoff {
  margin-left: 4px;
  font-style: italic;
  color: var(--text-muted);
}

.hint-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  font-size: 0.74rem;
  font-weight: 500;
  color: $color-brand-yellow;
  text-decoration: none;
  float: right;
  transition: color $transition-fast;

  &:hover {
    color: $color-brand-yellow-hover;
  }
}

/* Clear the float so the next card stacks cleanly */
.hint-card::after {
  content: '';
  display: block;
  clear: both;
}

.hint-fade-enter-active,
.hint-fade-leave-active {
  transition: opacity $transition-normal, transform $transition-normal;
}

.hint-fade-enter-from {
  opacity: 0;
  transform: translateY(-6px);
}

.hint-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
