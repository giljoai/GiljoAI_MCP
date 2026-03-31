<template>
  <v-container fluid class="pa-6">
    <!-- Page Header -->
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between mb-6">
          <div>
            <h1 class="text-h4 font-weight-bold mb-2">
              <v-icon icon="mdi-message-text" size="32" class="mr-2" />
              Messages
            </h1>
            <p class="text-body-1 text-muted-a11y">
              View agent communications and send broadcast messages
            </p>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Tabs for Message Panel and Broadcast -->
    <v-row>
      <v-col cols="12">
        <v-tabs v-model="activeTab" color="primary" class="mb-4">
          <v-tab value="timeline">
            <v-icon icon="mdi-timeline-text" start />
            Message Timeline
          </v-tab>
          <v-tab value="broadcast">
            <v-icon icon="mdi-bullhorn" start />
            Send Broadcast
          </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
          <!-- Message Timeline Tab -->
          <v-window-item value="timeline">
            <MessagePanel :project-id="selectedProjectId" />
          </v-window-item>

          <!-- Broadcast Tab -->
          <v-window-item value="broadcast">
            <BroadcastPanel />
          </v-window-item>
        </v-window>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import MessagePanel from '@/components/messages/MessagePanel.vue'
import BroadcastPanel from '@/components/messages/BroadcastPanel.vue'

// State
const activeTab = ref('timeline')

// Route
const route = useRoute()

// Project filtering (optional - can be set from route params)
const selectedProjectId = computed(() => {
  return route.query.projectId
})

// Lifecycle
onMounted(() => {
  // Set active tab from route query
  if (route.query.tab) {
    activeTab.value = route.query.tab
  }
})
</script>

<style scoped>
</style>
