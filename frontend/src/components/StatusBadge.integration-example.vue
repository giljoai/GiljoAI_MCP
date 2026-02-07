<!--
  INTEGRATION EXAMPLE: How to use StatusBadge in ProjectsView

  This file demonstrates the integration pattern for StatusBadge.
  Copy this code into your ProjectsView.vue component.
-->

<template>
  <v-container fluid>
    <!-- Projects Table -->
    <v-data-table :items="projects" :headers="headers" :loading="loading" class="elevation-1">
      <!-- Status Column with StatusBadge -->
      <template #item.status="{ item }">
        <StatusBadge
          :status="item.status"
          :project-id="item.id"
          :project-name="item.name"
          @action="handleStatusAction"
        />
      </template>

      <!-- Other columns as needed -->
      <template #item.name="{ item }">
        <router-link :to="{ name: 'ProjectDetail', params: { id: item.id } }">
          {{ item.name }}
        </router-link>
      </template>

      <template #item.created_at="{ item }">
        {{ formatDate(item.created_at) }}
      </template>
    </v-data-table>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useToast } from '@/composables/useToast'
import api from '@/services/api'

const { showToast } = useToast()

// State
const projects = ref([])
const loading = ref(false)

// Table headers
const headers = [
  { title: 'Name', key: 'name', sortable: true },
  { title: 'Status', key: 'status', sortable: true },
  { title: 'Alias', key: 'alias', sortable: false },
  { title: 'Created', key: 'created_at', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false },
]

// Methods
const loadProjects = async () => {
  loading.value = true
  try {
    const response = await api.projects.list()
    projects.value = response.data
  } catch (error) {
    console.error('Failed to load projects:', error)
    showToast({
      message: 'Failed to load projects',
      type: 'error',
      duration: 5000,
    })
  } finally {
    loading.value = false
  }
}

const handleStatusAction = async ({ action, newStatus, projectId }) => {
  try {
    // Handle delete action separately
    if (action === 'delete') {
      await api.projects.delete(projectId)

      showToast({
        message: 'Project deleted successfully',
        type: 'success',
        duration: 3000,
      })

      // Remove project from list
      projects.value = projects.value.filter((p) => p.id !== projectId)
      return
    }

    // Handle status updates
    const response = await api.projects.update(projectId, { status: newStatus })

    // Update project in list
    const projectIndex = projects.value.findIndex((p) => p.id === projectId)
    if (projectIndex !== -1) {
      projects.value[projectIndex] = {
        ...projects.value[projectIndex],
        status: newStatus,
        updated_at: new Date().toISOString(),
      }
    }

    // Show success message
    const actionLabels = {
      activate: 'activated',
      deactivate: 'deactivated',
      complete: 'completed',
      cancel: 'cancelled',
      restore: 'restored',
    }

    const actionLabel = actionLabels[action] || 'updated'

    showToast({
      message: `Project ${actionLabel} successfully`,
      type: 'success',
      duration: 3000,
    })
  } catch (error) {
    console.error('Failed to update project status:', error)

    showToast({
      message: error.response?.data?.detail || 'Failed to update project status',
      type: 'error',
      duration: 5000,
    })
  }
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

// Lifecycle
onMounted(() => {
  loadProjects()
})
</script>

<style scoped>
/* Add any view-specific styles here */
</style>

<!--
  ALTERNATIVE INTEGRATION: Card Grid Layout

  If you're using a card grid instead of a table:
-->

<!--
<template>
  <v-container fluid>
    <v-row>
      <v-col
        v-for="project in projects"
        :key="project.id"
        cols="12"
        sm="6"
        md="4"
        lg="3"
      >
        <v-card class="project-card">
          <v-card-title>
            <div class="d-flex align-center justify-space-between">
              <span>{{ project.name }}</span>
              <StatusBadge
                :status="project.status"
                :project-id="project.id"
                :project-name="project.name"
                @action="handleStatusAction"
              />
            </div>
          </v-card-title>

          <v-card-subtitle>
            {{ project.alias }}
          </v-card-subtitle>

          <v-card-text>
            <div class="text-caption">
              Created: {{ formatDate(project.created_at) }}
            </div>
          </v-card-text>

          <v-card-actions>
            <v-btn
              variant="text"
              size="small"
              :to="{ name: 'ProjectDetail', params: { id: project.id } }"
            >
              View Details
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
-->
