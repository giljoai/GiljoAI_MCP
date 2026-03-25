<template>
  <div class="recent-projects-list">
    <div v-if="projects.length === 0" class="text-caption text-disabled pa-3 text-center">
      No recent projects
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
          <v-chip
            v-if="project.taxonomy_alias"
            size="x-small"
            variant="flat"
            :color="project.project_type_color || '#9e9e9e'"
            class="mr-2 taxonomy-chip"
            :aria-label="`Taxonomy: ${project.taxonomy_alias}`"
          >
            {{ project.taxonomy_alias }}
          </v-chip>
        </template>

        <v-list-item-title class="text-body-2 project-name">
          {{ project.name }}
        </v-list-item-title>

        <template v-slot:append>
          <div class="d-flex align-center ga-2">
            <StatusBadge :status="project.status" />
            <span
              v-if="durationText(project)"
              class="text-caption text-medium-emphasis duration-text"
            >
              {{ durationText(project) }}
            </span>
          </div>
        </template>
      </v-list-item>
    </v-list>
  </div>
</template>

<script setup>
import StatusBadge from '@/components/StatusBadge.vue'

defineProps({
  projects: {
    type: Array,
    default: () => [],
  },
})

function durationText(project) {
  if (!project.completed_at || !project.created_at) return null
  const start = new Date(project.created_at)
  const end = new Date(project.completed_at)
  const diffMs = end - start
  if (diffMs < 0) return null

  const totalMinutes = Math.floor(diffMs / 60000)
  const totalHours = Math.floor(totalMinutes / 60)
  const totalDays = Math.floor(totalHours / 24)

  if (totalMinutes < 60) return '< 1h'
  if (totalHours < 24) return `${totalHours}h`
  const remainingHours = totalHours % 24
  if (remainingHours === 0) return `${totalDays}d`
  return `${totalDays}d ${remainingHours}h`
}
</script>

<style scoped>
.projects-scroll {
  max-height: 340px;
  overflow-y: auto;
}

.project-row {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  min-height: 36px;
}

.project-row:last-child {
  border-bottom: none;
}

.project-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 220px;
}

.taxonomy-chip {
  font-size: 0.65rem;
  font-weight: 600;
  min-width: 40px;
  justify-content: center;
}

.duration-text {
  white-space: nowrap;
  min-width: 40px;
  text-align: right;
}
</style>
