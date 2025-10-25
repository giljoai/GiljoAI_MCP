<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-text>
      <div class="d-flex align-center mb-3">
        <v-icon color="primary" size="large" class="mr-2">mdi-download</v-icon>
        <h3 class="text-h6 mb-0">Claude Code Agent Export</h3>
      </div>

      <!-- Info Alert -->
      <v-alert type="info" variant="tonal" class="mb-4">
        <div class="text-body-2">
          Export your agent templates as Claude Code agent definition files. This creates
          <code>.md</code> files in your <code>.claude/agents/</code> directory with YAML
          frontmatter for seamless integration with Claude Code.
        </div>
      </v-alert>

      <!-- Export Path Selection -->
      <div class="mb-4">
        <h4 class="text-subtitle-1 font-weight-medium mb-2">Export Location</h4>
        <v-radio-group
          v-model="exportPath"
          hide-details
          :disabled="loading"
          aria-label="Select export location"
        >
          <v-radio value="project" class="mb-2">
            <template #label>
              <div>
                <strong>Project Directory</strong>
                <span class="text-medium-emphasis d-block text-body-2">
                  <code>.claude/agents/</code> (current project only - recommended)
                </span>
              </div>
            </template>
          </v-radio>
          <v-radio value="personal">
            <template #label>
              <div>
                <strong>Personal Directory</strong>
                <span class="text-medium-emphasis d-block text-body-2">
                  <code>~/.claude/agents/</code> (available to all projects)
                </span>
              </div>
            </template>
          </v-radio>
        </v-radio-group>
      </div>

      <!-- Template Summary -->
      <div v-if="activeTemplates.length > 0" class="mb-4">
        <h4 class="text-subtitle-1 font-weight-medium mb-2">
          Active Templates ({{ activeTemplates.length }})
        </h4>
        <v-chip-group column>
          <v-chip
            v-for="template in activeTemplates"
            :key="template.id"
            size="small"
            label
            :prepend-icon="getTemplateIcon(template.role)"
          >
            {{ template.name }}
          </v-chip>
        </v-chip-group>
      </div>

      <!-- No Templates Message -->
      <v-alert v-else type="warning" variant="tonal" class="mb-4">
        No active templates available for export. Please activate at least one template in the
        Agent Templates tab.
      </v-alert>

      <!-- Warning Alert -->
      <v-alert type="warning" variant="tonal" class="mb-4" icon="mdi-backup-restore">
        <div class="text-body-2">
          Existing files will be backed up with extension
          <code>.old.YYYYMMDD_HHMMSS</code> before being overwritten.
        </div>
      </v-alert>

      <!-- Export Button -->
      <v-btn
        color="primary"
        size="large"
        block
        :disabled="activeTemplates.length === 0 || loading"
        :loading="loading"
        @click="handleExport"
        aria-label="Export agent templates to Claude Code format"
        prepend-icon="mdi-download"
      >
        Export {{ activeTemplates.length }} Template{{ activeTemplates.length !== 1 ? 's' : '' }} to
        Claude Code
      </v-btn>

      <!-- Result Display -->
      <div v-if="exportResult" class="mt-4">
        <v-alert
          :type="exportResult.success ? 'success' : 'error'"
          variant="tonal"
          closable
          @click:close="exportResult = null"
        >
          <div class="text-subtitle-2 mb-2">{{ exportResult.message }}</div>

          <!-- Files Created -->
          <div v-if="exportResult.files && exportResult.files.length > 0" class="mt-2">
            <div class="text-body-2 font-weight-medium mb-1">Files Created:</div>
            <ul class="text-body-2 mb-0">
              <li v-for="file in exportResult.files" :key="file.path" class="text-truncate">
                <code>{{ file.name }}.md</code>
                <span class="text-medium-emphasis ml-1">({{ formatPath(file.path) }})</span>
              </li>
            </ul>
          </div>

          <!-- Error Details -->
          <div v-if="exportResult.error" class="mt-2">
            <div class="text-body-2 font-weight-medium mb-1">Error Details:</div>
            <code class="text-body-2">{{ exportResult.error }}</code>
          </div>
        </v-alert>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

// State
const exportPath = ref('project')
const activeTemplates = ref([])
const loading = ref(false)
const exportResult = ref(null)

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

function formatPath(fullPath) {
  // Extract relative path for display (show .claude/agents/... part)
  const parts = fullPath.replace(/\\/g, '/').split('/')
  const claudeIndex = parts.findIndex((p) => p === '.claude')
  if (claudeIndex >= 0) {
    return parts.slice(claudeIndex).join('/')
  }
  return fullPath
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

async function handleExport() {
  if (activeTemplates.value.length === 0) {
    return
  }

  loading.value = true
  exportResult.value = null

  try {
    // Determine export path
    const targetPath =
      exportPath.value === 'project' ? './.claude/agents' : '~/.claude/agents'

    console.log('[CLAUDE EXPORT] Exporting to:', targetPath)

    // Call API
    const response = await api.templates.exportClaudeCode({
      export_path: targetPath,
    })

    console.log('[CLAUDE EXPORT] Export successful:', response.data)

    // Display success result
    exportResult.value = {
      success: true,
      message: response.data.message || `Successfully exported ${response.data.exported_count} template(s)`,
      files: response.data.files || [],
    }
  } catch (error) {
    console.error('[CLAUDE EXPORT] Export failed:', error)

    // Extract error message
    const errorMessage =
      error.response?.data?.detail || error.message || 'Unknown error occurred'

    // Display error result
    exportResult.value = {
      success: false,
      message: 'Export Failed',
      error: errorMessage,
    }
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

ul {
  padding-left: 20px;
}

li {
  margin-bottom: 4px;
}
</style>
