<template>
  <div class="recent-projects-list">
    <div v-if="projects.length === 0" class="text-caption text-disabled pa-3 text-center">
      No completed projects yet
    </div>
    <v-list
      v-else
      density="compact"
      bg-color="transparent"
      class="pa-0 projects-scroll"
    >
      <v-list-item
        v-for="project in projects"
        :key="project.id"
        class="px-2 py-1 project-row"
      >
        <template v-slot:prepend>
          <!-- project_type_color fallback: design-token-exempt (Vuetify color prop, $color-text-muted) -->
          <v-chip
            v-if="project.taxonomy_alias"
            size="x-small"
            variant="flat"
            :color="project.project_type_color || '#9e9e9e'"
            class="mr-2 taxonomy-chip"
          >
            {{ project.taxonomy_alias }}
          </v-chip>
        </template>

        <v-list-item-title class="text-body-2">
          {{ project.name }}
          <span v-if="project.product_name" class="text-caption text-medium-emphasis ml-2">({{ project.product_name }})</span>
        </v-list-item-title>

        <template v-slot:append>
          <span class="text-caption text-medium-emphasis completion-date">
            {{ formatDateTime(project.completed_at) }}
          </span>
        </template>
      </v-list-item>
    </v-list>
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

</script>

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;

.projects-scroll {
  max-height: 340px;
  overflow-y: auto;
}

.project-row {
  border-bottom: 1px solid $color-border-tertiary;
  min-height: 36px;
}

.project-row:last-child {
  border-bottom: none;
}

.taxonomy-chip {
  font-size: 0.65rem;
  font-weight: 600;
  min-width: 40px;
  justify-content: center;
}

.completion-date {
  white-space: nowrap;
}
</style>
