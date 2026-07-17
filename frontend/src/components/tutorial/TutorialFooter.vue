<template>
  <div class="tutorial-footer">
    <button
      type="button"
      class="footer-skip"
      data-testid="tutorial-skip"
      @click="$emit('skip')"
    >
      Skip — I'll explore on my own
    </button>

    <div class="footer-actions">
      <v-btn
        v-if="showReplay"
        variant="text"
        size="small"
        icon
        class="footer-replay"
        aria-label="Replay animation"
        title="Replay animation"
        data-testid="tutorial-replay"
        @click="$emit('replay')"
      >
        <v-icon size="18">mdi-replay</v-icon>
      </v-btn>

      <v-btn
        v-if="showBack"
        variant="text"
        class="footer-back"
        data-testid="tutorial-back"
        @click="$emit('back')"
      >
        Back
      </v-btn>

      <v-btn
        v-if="showNext"
        color="primary"
        variant="flat"
        class="footer-next"
        data-testid="tutorial-next"
        append-icon="mdi-arrow-right"
        @click="$emit('next')"
      >
        {{ nextLabel }}
      </v-btn>
    </div>
  </div>
</template>

<script setup>
defineProps({
  showBack: { type: Boolean, default: false },
  showNext: { type: Boolean, default: false },
  showReplay: { type: Boolean, default: false },
  nextLabel: { type: String, default: 'Next' },
})

defineEmits(['skip', 'back', 'next', 'replay'])
</script>

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;

.tutorial-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 44px 22px;
}

.footer-skip {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-muted);
  padding: 8px 0;
  font-family: inherit;
  transition: color 150ms ease-out;

  &:hover,
  &:focus-visible {
    color: $color-text-primary;
  }
}

.footer-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.footer-replay {
  color: var(--text-muted) !important;
}

.footer-back {
  color: var(--text-secondary) !important;
  font-family: 'Outfit', $typography-font-primary;
  font-weight: 600;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14);
  border-radius: $border-radius-default;
}

.footer-next {
  border-radius: $border-radius-default;
  font-family: 'Outfit', $typography-font-primary;
  font-weight: 600;
  background: $color-brand-yellow !important;
  color: $color-on-yellow-ink !important;

  &:hover {
    background: $color-brand-yellow-hover !important;
  }
}
</style>
