<template>
  <div v-if="loading" class="d-flex justify-center align-center" style="height: 100vh">
    <v-progress-circular indeterminate size="64" color="primary"></v-progress-circular>
  </div>

  <div
    v-else-if="!activeProject"
    class="d-flex flex-column justify-center align-center"
    style="height: 100vh"
  >
    <v-icon size="96" color="grey-darken-2">mdi-briefcase-off-outline</v-icon>
    <h2 class="text-h4 mt-4 text-grey-darken-2">No Active Project</h2>
    <p class="text-body-1 mt-2 text-grey">Activate a project to launch the jobs interface</p>
    <v-btn color="primary" class="mt-6" to="/projects"> Go to Projects </v-btn>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'

const router = useRouter()
const loading = ref(true)
const activeProject = ref(null)

onMounted(async () => {
  try {
    const response = await api.projects.getActive()
    if (response.data) {
      // Redirect to the dynamic project route and tag source for sidebar highlighting
      router.replace({
        name: 'ProjectLaunch',
        params: { projectId: response.data.id },
        query: { via: 'jobs' },
      })
    } else {
      // No active project - show the "no active project" page
      activeProject.value = null
      loading.value = false
    }
  } catch (err) {
    console.warn('[LaunchRedirect] Failed to fetch active project:', err)
    activeProject.value = null
    loading.value = false
  }
})
</script>
