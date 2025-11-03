<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-text>
      <div class="d-flex align-center mb-3">
        <v-avatar size="40" rounded="0" class="mr-2">
          <v-img src="/claude_pix.svg" alt="Claude Code" />
        </v-avatar>
        <h3 class="text-h6 mb-0">Claude Code Agent Export</h3>
      </div>

      <!-- Export Commands Section -->
      <div class="export-commands mb-4">
        <div class="d-flex align-center mb-3">
          <h4 class="text-subtitle-1 font-weight-medium mb-0 mr-2">Export Commands</h4>
          <v-tooltip location="top" max-width="400">
            <template #activator="{ props }">
              <v-icon v-bind="props" size="small" color="medium-emphasis">mdi-help-circle-outline</v-icon>
            </template>
            <span>Old agents will be backed up in the .claude/agents folder and replaced with the active agents from the Agent Template Manager.</span>
          </v-tooltip>
        </div>
        <p class="text-body-2 text-medium-emphasis mb-3">
          Copy and paste agent import command into your AI coding tool (Claude Code, Codex CLI, or Gemini).
        </p>

        <!-- Product Agents Command -->
        <v-card variant="tonal" class="mb-3">
          <v-card-text class="pa-3">
            <div class="d-flex align-center justify-between">
              <div class="flex-grow-1">
                <div class="text-subtitle-2 font-weight-medium">Product Agents</div>
                <div class="text-body-2 text-medium-emphasis">
                  Install agents in your product's .claude/agents folder
                </div>
              </div>
              <v-btn
                color="primary"
                variant="flat"
                size="small"
                width="120"
                @click="copyProductCommand"
              >
                Copy Command
              </v-btn>
            </div>
          </v-card-text>
        </v-card>

        <!-- Personal Agents Command -->
        <v-card variant="tonal" class="mb-3">
          <v-card-text class="pa-3">
            <div class="d-flex align-center justify-between">
              <div class="flex-grow-1">
                <div class="text-subtitle-2 font-weight-medium">Personal Agents</div>
                <div class="text-body-2 text-medium-emphasis">
                  Install agents in your user profile (~/.claude/agents)
                </div>
              </div>
              <v-btn
                color="primary"
                variant="flat"
                size="small"
                width="120"
                @click="copyPersonalCommand"
              >
                Copy Command
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </div>

      <!-- Copy Feedback -->
      <v-snackbar v-model="showCopyFeedback" timeout="3000" color="success">
        <v-icon class="mr-2">mdi-check-circle</v-icon>
        {{ copyFeedbackMessage }}
      </v-snackbar>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '@/services/api'

// State
const activeTemplates = ref([])
const loading = ref(false)
const showCopyFeedback = ref(false)
const copyFeedbackMessage = ref('')

// Template role icon mapping
const roleIcons = {
  orchestrator: 'mdi-connection',
  analyzer: 'mdi-magnify',
  implementor: 'mdi-code-braces',
  tester: 'mdi-test-tube',
  documenter: 'mdi-file-document-edit',
  reviewer: 'mdi-eye-check',
  default: 'mdi-robot',
}

// Methods
function getTemplateIcon(role) {
  return roleIcons[role?.toLowerCase()] || roleIcons.default
}

function generateProductCommand() {
  return '/gil_import_productagents'
}

function generatePersonalCommand() {
  return '/gil_import_personalagents'
}

// Production-grade cross-platform clipboard copy
function fallbackCopyToClipboard(text) {
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    ta.style.position = 'absolute'
    ta.style.left = '-9999px'
    ta.style.top = '0'
    document.body.appendChild(ta)

    // Select and copy
    ta.focus()
    ta.select()

    // For iOS compatibility
    if (navigator.userAgent.match(/ipad|iphone/i)) {
      const range = document.createRange()
      range.selectNodeContents(ta)
      const selection = window.getSelection()
      selection.removeAllRanges()
      selection.addRange(range)
      ta.setSelectionRange(0, text.length)
    }

    const success = document.execCommand('copy')
    document.body.removeChild(ta)
    return success
  } catch (err) {
    console.error('[CLAUDE EXPORT] Fallback copy failed:', err)
    return false
  }
}

async function copyProductCommand() {
  const command = generateProductCommand()

  // Try Clipboard API first, fallback to execCommand
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    try {
      await navigator.clipboard.writeText(command)
      showCopyFeedback.value = true
      copyFeedbackMessage.value = 'Product slash command copied to clipboard!'
      console.log('[CLAUDE EXPORT] Product slash command copied via Clipboard API')
      return
    } catch (error) {
      console.warn('[CLAUDE EXPORT] Clipboard API failed, using fallback:', error)
    }
  }

  // Fallback method
  const success = fallbackCopyToClipboard(command)
  showCopyFeedback.value = true
  if (success) {
    copyFeedbackMessage.value = 'Product slash command copied to clipboard!'
    console.log('[CLAUDE EXPORT] Product slash command copied via fallback')
  } else {
    copyFeedbackMessage.value = 'Failed to copy. Please copy manually.'
    console.error('[CLAUDE EXPORT] All copy methods failed')
  }
}

async function copyPersonalCommand() {
  const command = generatePersonalCommand()

  // Try Clipboard API first, fallback to execCommand
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    try {
      await navigator.clipboard.writeText(command)
      showCopyFeedback.value = true
      copyFeedbackMessage.value = 'Personal slash command copied to clipboard!'
      console.log('[CLAUDE EXPORT] Personal slash command copied via Clipboard API')
      return
    } catch (error) {
      console.warn('[CLAUDE EXPORT] Clipboard API failed, using fallback:', error)
    }
  }

  // Fallback method
  const success = fallbackCopyToClipboard(command)
  showCopyFeedback.value = true
  if (success) {
    copyFeedbackMessage.value = 'Personal slash command copied to clipboard!'
    console.log('[CLAUDE EXPORT] Personal slash command copied via fallback')
  } else {
    copyFeedbackMessage.value = 'Failed to copy. Please copy manually.'
    console.error('[CLAUDE EXPORT] All copy methods failed')
  }
}

async function loadActiveTemplates() {
  try {
    loading.value = true
    const response = await api.templates.list({ is_active: true })
    activeTemplates.value = response.data || []
    console.log('[CLAUDE EXPORT] Loaded active templates:', activeTemplates.value.length)
  } catch (error) {
    console.error('[CLAUDE EXPORT] Failed to load templates:', error)
    activeTemplates.value = []
  } finally {
    loading.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadActiveTemplates()
})
</script>

<style scoped>
code {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.875em;
}

.export-commands {
  border-radius: 8px;
}

ol {
  padding-left: 20px;
}

li {
  margin-bottom: 4px;
}
</style>
