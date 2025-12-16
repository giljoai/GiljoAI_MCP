<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-text>
      <div class="d-flex align-center mb-3">
        <v-avatar size="40" rounded="0" class="mr-2">
          <v-img src="/icons/codex_mark_white.svg" alt="Codex CLI" />
        </v-avatar>
        <h3 class="text-h6 mb-0">Codex CLI Integration</h3>
      </div>

      <p class="text-body-2 text-medium-emphasis mb-4">
        Step 1 of 2: Install the GiljoAI MCP proxy package so Codex can talk to the GiljoAI MCP
        server. Run the pip command from your local terminal, not inside Codex.
      </p>

      <v-card variant="tonal" class="mb-3">
        <v-card-text class="pa-3">
          <div class="text-subtitle-2 font-weight-medium mb-2">Install via pip</div>
          <p class="text-body-2 text-medium-emphasis mb-2">
            From your terminal, run:
          </p>
          <v-textarea
            v-model="pipCommand"
            label="pip install command"
            readonly
            rows="2"
            variant="outlined"
            class="font-monospace no-resize mb-2"
          />
          <v-btn
            :href="pipPackageUrl"
            target="_blank"
            rel="noopener noreferrer"
            color="primary"
            variant="text"
            size="small"
          >
            Open giljo-mcp package page
          </v-btn>
        </v-card-text>
      </v-card>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref } from 'vue'

// For now, install directly from the public GitHub repo.
// This keeps the flow working even before a PyPI release.
const pipCommand = ref('python -m pip install --upgrade git+https://github.com/giljoai/giljo-mcp.git')
const pipPackageUrl = 'https://github.com/giljoai/giljo-mcp'
</script>

<style scoped>
</style>
After the installer finishes, ask the user to restart Codex so it picks up the GiljoAI MCP server configuration.`
