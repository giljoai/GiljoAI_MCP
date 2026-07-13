<template>
  <div class="empty-state">
    <v-icon :icon="icon" size="48" class="empty-state-icon" />
    <div class="empty-state-title">{{ title }}</div>
    <div v-if="description" class="empty-state-description">{{ description }}</div>
  </div>
</template>

<script setup>
defineProps({
  icon: { type: String, required: true },
  title: { type: String, required: true },
  description: { type: String, default: '' },
})
</script>

<style lang="scss" scoped>
@use '../../styles/design-tokens' as *;

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}
.empty-state-icon {
  color: $color-text-muted;
  margin-bottom: 16px;
  opacity: 0.6;
}
.empty-state-title {
  font-family: 'Outfit', sans-serif;
  font-size: 1rem;
  font-weight: 500;
  color: $color-text-secondary;
  margin-bottom: 8px;
}
.empty-state-description {
  font-size: 0.82rem;
  color: $color-text-muted;
  max-width: 400px;
  margin-bottom: 20px;
}
</style>
