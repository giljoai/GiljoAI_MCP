<template>
  <div class="recent-projects-list">
    <div v-if="projects.length === 0" class="no-data-text">
      No completed projects yet
    </div>
    <div v-else class="projects-scroll">
      <div
        v-for="project in projects"
        :key="project.id"
        class="project-row"
        @click="emit('review-project', project)"
      >
        <span v-if="project.taxonomy_alias" class="project-taxonomy" :style="taxonomyStyle(project)">
          {{ project.taxonomy_alias }}
        </span>
        <span class="project-name">
          {{ project.name }}
          <span v-if="project.product_name" class="project-product">({{ project.product_name }})</span>
        </span>
        <span class="project-time">{{ formatDateTime(project.completed_at) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useFormatDate } from '@/composables/useFormatDate'

const { formatDateTime } = useFormatDate()

defineProps({
  projects: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['review-project'])

function hexToRgb(hex) {
  const h = hex.replace('#', '')
  return `${parseInt(h.substring(0, 2), 16)}, ${parseInt(h.substring(2, 4), 16)}, ${parseInt(h.substring(4, 6), 16)}`
}

function taxonomyStyle(project) {
  const color = project.project_type_color || '#9e9e9e' /* design-token-exempt: dynamic taxonomy color */
  return {
    background: `rgba(${hexToRgb(color)}, 0.15)`,
    color,
  }
}

function statusClass(status) {
  return status ? status.toLowerCase() : ''
}

function capitalize(str) {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1)
}
</script>

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;

.projects-scroll {
  max-height: 340px;
  overflow-y: auto;
}

.project-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid $color-border-tertiary;
  transition: background $transition-fast;
  cursor: pointer;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.02);
    margin: 0 -18px;
    padding: 10px 18px;
  }
}

.project-taxonomy {
  padding: 2px 8px;
  border-radius: $border-radius-sharp;
  font-size: 0.6rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  flex-shrink: 0;
  min-width: 48px;
  text-align: center;
}

.project-name {
  flex: 1;
  font-size: 0.78rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: $color-text-primary;
}

.project-product {
  font-size: 0.68rem;
  color: var(--text-muted);
  margin-left: 4px;
}

.project-time {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.58rem;
  color: var(--text-muted);
  flex-shrink: 0;
  min-width: 56px;
  text-align: right;
}

.project-status {
  padding: 2px 8px;
  border-radius: $border-radius-pill;
  font-size: 0.58rem;
  font-weight: 700;
  text-transform: capitalize;
  flex-shrink: 0;
  min-width: 68px;
  text-align: center;

  /* design-token-exempt: status chip colors — functional semantic colors */
  &.active { background: #ffffff; color: #333333; }
  &.inactive { background: #9e9e9e; color: #1a237e; }
  &.completed { background: #67bd6d; color: $color-background-primary; }
  &.cancelled { background: $color-brand-yellow; color: $color-background-primary; }
  &.terminated { background: #c6298c; color: $color-text-primary; }
  &.staged { background: #ffc107; color: $color-background-primary; }
}

.no-data-text {
  font-size: 0.75rem;
  color: var(--text-muted);
  padding: 8px 0;
  text-align: center;
}
</style>
