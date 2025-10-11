<template>
  <v-card-text class="pa-8">
    <div class="text-center mb-6">
      <v-icon size="80" color="success" class="mb-4">mdi-check-circle</v-icon>
      <h2 class="text-h4 mb-2">Setup Complete!</h2>
      <p class="text-body-1 text-medium-emphasis">
        Your GiljoAI MCP Orchestrator is ready to use
      </p>
    </div>

    <!-- Configuration Summary -->
    <v-card variant="outlined" class="mb-4">
      <v-card-title class="text-h6">
        <v-icon start>mdi-clipboard-check</v-icon>
        Configuration Summary
      </v-card-title>
      <v-card-text>
        <v-list density="compact">
          <v-list-item>
            <template #prepend>
              <v-icon :color="config.mcpConfigured ? 'success' : 'default'">
                {{ config.mcpConfigured ? 'mdi-check-circle' : 'mdi-minus-circle' }}
              </v-icon>
            </template>
            <v-list-item-title>MCP Integration</v-list-item-title>
            <v-list-item-subtitle>
              {{ config.mcpConfigured ? 'Configured' : 'Not configured (can be enabled later)' }}
            </v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <template #prepend>
              <v-icon :color="config.serenaEnabled ? 'success' : 'default'">
                {{ config.serenaEnabled ? 'mdi-check-circle' : 'mdi-minus-circle' }}
              </v-icon>
            </template>
            <v-list-item-title>Serena MCP Server</v-list-item-title>
            <v-list-item-subtitle>
              {{ config.serenaEnabled ? 'Enabled' : 'Disabled (can be enabled later)' }}
            </v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <template #prepend>
              <v-icon color="success">mdi-check-circle</v-icon>
            </template>
            <v-list-item-title>Database</v-list-item-title>
            <v-list-item-subtitle>PostgreSQL configured and ready</v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <template #prepend>
              <v-icon color="success">mdi-check-circle</v-icon>
            </template>
            <v-list-item-title>Authentication</v-list-item-title>
            <v-list-item-subtitle>Auto-login enabled for localhost</v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <!-- Next Steps -->
    <v-card variant="outlined" class="mb-4">
      <v-card-title class="text-h6">
        <v-icon start>mdi-rocket-launch</v-icon>
        Next Steps
      </v-card-title>
      <v-card-text>
        <v-list density="compact">
          <v-list-item>
            <template #prepend>
              <v-icon>mdi-numeric-1-circle</v-icon>
            </template>
            <v-list-item-title>Explore the Dashboard</v-list-item-title>
            <v-list-item-subtitle>
              View your projects, agents, and tasks in the main dashboard
            </v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <template #prepend>
              <v-icon>mdi-numeric-2-circle</v-icon>
            </template>
            <v-list-item-title>Create Your First Project</v-list-item-title>
            <v-list-item-subtitle>
              Use the Projects page to create and manage coding projects
            </v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <template #prepend>
              <v-icon>mdi-numeric-3-circle</v-icon>
            </template>
            <v-list-item-title>Configure Additional Tools</v-list-item-title>
            <v-list-item-subtitle>
              Visit Settings to add more AI tools and customize your setup
            </v-list-item-subtitle>
          </v-list-item>

          <v-list-item v-if="!config.mcpConfigured || !config.serenaEnabled">
            <template #prepend>
              <v-icon>mdi-information</v-icon>
            </template>
            <v-list-item-title>Optional: Configure Skipped Features</v-list-item-title>
            <v-list-item-subtitle>
              You can enable MCP integration and Serena later in Settings
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <!-- Documentation Links -->
    <v-card variant="outlined" class="mb-6">
      <v-card-title class="text-h6">
        <v-icon start>mdi-book-open-variant</v-icon>
        Learn More
      </v-card-title>
      <v-card-text>
        <div class="d-flex flex-wrap gap-2">
          <v-btn
            href="https://github.com/patrik-giljoai/GiljoAI-MCP"
            target="_blank"
            variant="outlined"
            size="small"
          >
            <v-icon start>mdi-github</v-icon>
            Documentation
          </v-btn>
          <v-btn
            href="https://github.com/patrik-giljoai/GiljoAI-MCP/tree/master/docs"
            target="_blank"
            variant="outlined"
            size="small"
          >
            <v-icon start>mdi-file-document</v-icon>
            User Guides
          </v-btn>
          <v-btn
            href="https://github.com/patrik-giljoai/GiljoAI-MCP/tree/master/docs/manuals"
            target="_blank"
            variant="outlined"
            size="small"
          >
            <v-icon start>mdi-wrench</v-icon>
            MCP Tools Manual
          </v-btn>
        </div>
      </v-card-text>
    </v-card>

    <!-- Progress -->
    <v-card variant="outlined" class="mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 3 of 3</span>
          <span class="text-caption">100%</span>
        </div>
        <v-progress-linear :model-value="100" color="success" />
      </v-card-text>
    </v-card>

    <!-- Navigation -->
    <div class="d-flex justify-space-between">
      <v-btn variant="outlined" @click="$emit('back')" aria-label="Go back">
        <v-icon start>mdi-arrow-left</v-icon>
        Back
      </v-btn>
      <v-btn color="primary" size="large" :loading="completing" @click="handleFinish">
        <v-icon start>mdi-check</v-icon>
        Go to Dashboard
      </v-btn>
    </div>
  </v-card-text>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  config: {
    type: Object,
    required: true,
    default: () => ({
      mcpConfigured: false,
      serenaEnabled: false,
    }),
  },
})

const emit = defineEmits(['finish', 'back'])

const completing = ref(false)

const handleFinish = () => {
  completing.value = true
  emit('finish')
}
</script>

<style scoped>
h2 {
  color: rgb(var(--v-theme-primary));
}

.v-list-item {
  min-height: 48px;
}
</style>
