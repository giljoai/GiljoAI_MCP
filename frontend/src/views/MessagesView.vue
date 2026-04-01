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

    <!-- Tab Pills for Message Panel and Broadcast -->
    <v-row>
      <v-col cols="12">
        <div class="tab-pills mb-4">
          <button
            class="pill-btn"
            :class="{ active: activeTab === 'timeline' }"
            @click="activeTab = 'timeline'"
          >
            <v-icon size="18">mdi-timeline-text</v-icon>
            Message Timeline
          </button>
          <button
            class="pill-btn"
            :class="{ active: activeTab === 'broadcast' }"
            @click="activeTab = 'broadcast'"
          >
            <v-icon size="18">mdi-bullhorn</v-icon>
            Send Broadcast
          </button>
        </div>

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

<style scoped lang="scss">
@use '../styles/design-tokens' as *;
.tab-pills {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pill-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: $border-radius-pill;
  padding: 8px 18px;
  font-size: 0.78rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  background: transparent;
  color: #8895a8;
  border: none;
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-on-surface), 0.15);

  &:hover {
    color: #a3aac4;
    box-shadow: inset 0 0 0 1px rgba(var(--v-theme-on-surface), 0.25);
  }

  &.active {
    background: rgba(255, 195, 0, 0.12);
    color: #ffc300;
    box-shadow: none;
  }
}
</style>
