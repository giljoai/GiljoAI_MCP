<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-text>
      <div class="d-flex align-center mb-3">
        <v-avatar size="40" rounded="0" class="mr-2">
          <v-img
            :src="
              theme.global.current.value.dark ? '/giljo_YW_Face.svg' : '/icons/Giljo_BY_Face.svg'
            "
            alt="GiljoAI MCP"
          />
        </v-avatar>
        <h3 class="text-h6 mb-0">GiljoAI MCP Integration</h3>
      </div>
      <p class="text-body-2 text-medium-emphasis mb-4">
        Connect your AI coding tool to GiljoAI orchestration. Supports Claude Code, Codex CLI, and
        Gemini CLI.
      </p>

      <!-- MCP Configuration Tool -->
      <v-card variant="tonal" class="mb-0">
        <v-card-text class="pa-3">
          <div class="d-flex align-center justify-between">
            <div class="flex-grow-1">
              <div class="text-subtitle-2 font-weight-medium">MCP Configuration Tool</div>
              <div class="text-body-2 text-medium-emphasis">
                Creates MCP integration CLI command for your coding agent of choice
              </div>
            </div>
            <AiToolConfigWizard />
          </div>
        </v-card-text>
      </v-card>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { useTheme } from 'vuetify'
import AiToolConfigWizard from '@/components/AiToolConfigWizard.vue'

const theme = useTheme()
</script>
