<template>
  <div>
    <!-- Title (above filter bar) -->
    <div class="tab-header mb-4 d-flex align-center">
      <h2 class="text-h6">Agent Template Manager</h2>
      <v-tooltip location="bottom" max-width="360">
        <template #activator="{ props }">
          <v-icon v-bind="props" size="small" class="ml-2" color="medium-emphasis"
            >mdi-information-outline</v-icon
          >
        </template>
        <span
          >Each active agent template consumes context tokens during orchestration. The 8-slot limit
          keeps prompt budgets manageable. 1 slot is reserved for the Orchestrator (managed in Admin
          Settings), leaving 7 for your custom agents.</span
        >
      </v-tooltip>
      <v-chip
        v-if="totalActiveAgents !== null"
        :color="remainingUserSlots === 0 ? 'warning' : 'default'"
        size="small"
        variant="tonal"
        class="ml-4"
      >
        {{ totalActiveAgents }} / {{ totalCapacity }}
      </v-chip>
    </div>

    <!-- Filter bar with New Template button right-aligned -->
    <div class="filter-bar">
      <v-text-field
        v-model="search"
        prepend-inner-icon="mdi-magnify"
        placeholder="Search templates..."
        variant="solo"
        density="compact"
        clearable
        hide-details
        flat
        class="filter-search"
      />
      <v-select
        v-model="filterCategory"
        :items="categories"
        placeholder="Category"
        clearable
        variant="solo"
        flat
        density="compact"
        hide-details
        class="filter-select"
      />
      <v-select
        v-model="filterStatus"
        :items="statusOptions"
        placeholder="Status"
        clearable
        variant="solo"
        flat
        density="compact"
        hide-details
        class="filter-select"
      />
      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        aria-label="Create new template"
        @click="openCreateDialog"
      >
        New Template
      </v-btn>
    </div>

    <v-card class="template-manager smooth-border">
      <v-card-text>
        <!-- Templates Table -->
      <v-data-table
        :headers="headers"
        :items="filteredTemplates"
        :search="search"
        :loading="loading"
        class="elevation-0 templates-table"
        item-key="id"
        :items-per-page="10"
        :item-class="(item) => (item.is_active ? '' : 'inactive-template')"
      >
        <template v-slot:item.name="{ item }">
          <div class="font-weight-medium">{{ item.name }}</div>
        </template>

        <template v-slot:item.role="{ item }">
          <span
            class="template-role-badge"
            :style="{
              backgroundColor: hexToRgba(getCategoryColor(item.role), 0.15),
              color: getCategoryColor(item.role),
              opacity: item.is_active ? 1 : 0.4,
            }"
          >
            {{ item.role }}
          </span>
        </template>

        <template v-slot:item.updated_at="{ item }">
          <span class="text-caption">{{ item._system ? '—' : formatDate(item.updated_at) }}</span>
        </template>

        <template v-slot:item.export_status="{ item }">
          <div class="d-flex flex-column align-center">
            <template v-if="item._system">
              <span class="text-caption text-muted-a11y">System managed</span>
            </template>
            <template v-else>
              <v-chip
                v-if="item.may_be_stale"
                size="small"
                color="warning"
                prepend-icon="mdi-alert"
                class="mb-1"
                aria-label="Template may be outdated"
              >
                May be outdated
              </v-chip>
              <v-tooltip location="top" max-width="300">
                <template v-slot:activator="{ props }">
                  <span
                    v-bind="props"
                    class="text-caption text-muted-a11y"
                    :class="{ 'text-warning': item.may_be_stale }"
                  >
                    {{ item.last_exported_at ? formatDate(item.last_exported_at) : 'Never exported' }}
                  </span>
                </template>
                <span v-if="item.may_be_stale">
                  This template was modified after the last export. Re-export to your AI coding agents to get the
                  latest version.
                </span>
                <span v-else-if="item.last_exported_at">
                  Last exported: {{ formatDate(item.last_exported_at) }}
                </span>
                <span v-else>
                  This template has never been exported to your AI coding agents. Use the export feature to make it
                  available.
                </span>
              </v-tooltip>
            </template>
          </div>
        </template>

        <template v-slot:item.is_active="{ item }">
          <div class="d-flex align-center justify-center">
            <template v-if="item._system">
              <v-icon color="grey" size="small">mdi-lock</v-icon>
            </template>
            <template v-else>
              <v-switch
                :model-value="item.is_active"
                :disabled="!item.is_active && remainingUserSlots === 0"
                color="primary"
                hide-details
                density="compact"
                :aria-label="item.is_active ? 'Deactivate agent' : 'Activate agent'"
                :data-testid="`template-toggle-${item.role}`"
                @update:model-value="handleToggleActive(item, $event)"
              />
              <v-tooltip v-if="!item.is_active && remainingUserSlots === 0" location="top">
                <template v-slot:activator="{ props }">
                  <v-icon v-bind="props" color="warning" size="small" class="ml-1">
                    mdi-information-outline
                  </v-icon>
                </template>
                <span>
                  Maximum {{ userAgentLimit }} user-managed agents allowed (context budget limit).
                  Deactivate another agent first.
                </span>
              </v-tooltip>
            </template>
          </div>
        </template>

        <template v-slot:item.actions="{ item }">
          <div v-if="item._system" />
          <div v-else class="d-flex align-center justify-center">
            <v-menu>
              <template v-slot:activator="{ props }">
                <v-btn
                  icon="mdi-dots-vertical"
                  size="small"
                  variant="text"
                  class="icon-interactive"
                  v-bind="props"
                  aria-label="Template actions"
                ></v-btn>
              </template>

              <v-list density="compact" min-width="180">
                <v-list-item
                  prepend-icon="mdi-pencil"
                  title="Edit"
                  @click="editTemplate(item)"
                ></v-list-item>
                <v-list-item
                  prepend-icon="mdi-content-copy"
                  title="Duplicate"
                  @click="duplicateTemplate(item)"
                ></v-list-item>
                <v-list-item
                  prepend-icon="mdi-refresh"
                  title="Reset to Default"
                  @click="confirmReset(item)"
                ></v-list-item>
                <v-divider class="my-1" />
                <v-list-item
                  prepend-icon="mdi-delete"
                  title="Delete"
                  @click="confirmDelete(item)"
                ></v-list-item>
              </v-list>
            </v-menu>
          </div>
        </template>
      </v-data-table>
    </v-card-text>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="editDialog" max-width="900px" persistent retain-focus scrollable>
      <v-card v-draggable class="smooth-border">
        <div class="dlg-header">
          <span class="dlg-title">{{ editingTemplate.id ? 'Edit' : 'Create' }} Template</span>
          <v-btn icon variant="text" class="dlg-close" aria-label="Close" @click="closeEditDialog">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </div>

        <v-card-text>
          <v-container>
            <v-row>
              <!-- Role / Suffix — single row -->
              <v-col cols="6">
                <v-select
                  v-model="editingTemplate.role"
                  :items="roleOptions"
                  label="Role"
                  :rules="[(v) => !!v || 'Role is required']"
                  variant="outlined"
                  density="compact"
                  aria-label="Select agent role"
                  @update:model-value="onRoleChange"
                >
                  <template v-slot:append-inner>
                    <v-tooltip location="top">
                      <template v-slot:activator="{ props }">
                        <v-icon v-bind="props" size="small" color="primary">mdi-help-circle</v-icon>
                      </template>
                      <span>Required field - Select the agent role</span>
                    </v-tooltip>
                  </template>
                </v-select>
              </v-col>

              <v-col cols="6">
                <v-text-field
                  v-model="editingTemplate.custom_suffix"
                  label="Custom Suffix (optional)"
                  density="compact"
                  aria-label="Custom agent name suffix"
                >
                  <template v-slot:append-inner>
                    <v-tooltip location="top">
                      <template v-slot:activator="{ props }">
                        <v-icon v-bind="props" size="small" color="primary">mdi-help-circle</v-icon>
                      </template>
                      <span>Add a suffix to customize the agent name (e.g., 'implementer-fastapi')</span>
                    </v-tooltip>
                  </template>
                </v-text-field>
                <div v-if="generatedName" class="text-caption text-primary mt-n2">
                  Agent Name: <strong>{{ generatedName }}</strong>
                </div>
              </v-col>

              <!-- Description -->
              <v-col cols="12">
                <v-text-field
                  v-model="editingTemplate.description"
                  label="Description"
                  density="compact"
                  hint="Short description of agent responsibilities (used by all platforms)"
                  persistent-hint
                  aria-label="Agent description"
                >
                  <template v-slot:append-inner>
                    <v-tooltip location="top">
                      <template v-slot:activator="{ props }">
                        <v-icon v-bind="props" size="small" color="primary">mdi-help-circle</v-icon>
                      </template>
                      <span>Brief description of what this agent does</span>
                    </v-tooltip>
                  </template>
                </v-text-field>
              </v-col>

              <!-- Role & Expertise Editor (Handover 0814: replaces System Prompt) -->
              <v-col cols="12">
                <div class="d-flex align-center mb-2">
                  <span class="text-subtitle-2">Role & Expertise</span>
                  <v-tooltip location="top">
                    <template v-slot:activator="{ props }">
                      <v-icon v-bind="props" size="small" color="primary" class="ml-2"
                        >mdi-help-circle</v-icon
                      >
                    </template>
                    <span
                      >Describe this agent's specialization, expertise, and personality.
                      This content defines who the agent is.</span
                    >
                  </v-tooltip>
                </div>
                <v-textarea
                  v-model="editingTemplate.user_instructions"
                  label="Role & Expertise"
                  hint="Describe this agent's specialization, expertise, and personality."
                  persistent-hint
                  rows="12"
                  variant="outlined"
                  density="compact"
                  class="template-editor"
                  aria-label="Agent role and expertise"
                />
              </v-col>

              <!-- Preview (collapsible, Handover 0814) -->
              <v-col v-if="previewContent" cols="12">
                <v-expansion-panels variant="accordion">
                  <v-expansion-panel>
                    <v-expansion-panel-title>
                      <div class="d-flex align-center">
                        <v-icon start size="small" color="primary">mdi-eye</v-icon>
                        <span class="font-weight-medium">Template Preview</span>
                        <span class="text-caption text-muted-a11y ml-2">(includes orchestration protocols)</span>
                      </div>
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <v-card variant="flat" class="preview-card smooth-border">
                        <pre class="preview-content">{{ previewContent }}</pre>
                      </v-card>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>

        <div class="dlg-footer">
          <v-spacer />
          <v-btn variant="text" @click="closeEditDialog"> Cancel </v-btn>
          <v-btn color="primary" variant="flat" :loading="saving" @click="saveTemplateAndPreview">
            Save and Generate Preview
          </v-btn>
        </div>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="500px" persistent retain-focus>
      <v-card v-draggable class="smooth-border">
        <div class="dlg-header dlg-header--danger">
          <v-icon class="dlg-icon">mdi-alert</v-icon>
          <span class="dlg-title">Permanently Delete Template</span>
          <v-btn icon variant="text" class="dlg-close" aria-label="Close" @click="deleteDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </div>
        <v-card-text>
          <v-alert type="error" variant="tonal" class="mb-4">
            <strong>This action cannot be undone.</strong>
          </v-alert>
          <p>
            Are you sure you want to permanently delete the template
            "<strong>{{ deletingTemplate?.name }}</strong>"?
          </p>
          <p class="text-caption text-muted-a11y mt-2">
            This will remove the template and all its version history.
          </p>
        </v-card-text>
        <div class="dlg-footer">
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" variant="flat" :loading="deleting" @click="deleteTemplate">
            Delete Permanently
          </v-btn>
        </div>
      </v-card>
    </v-dialog>

    <!-- Reset Confirmation Dialog -->
    <v-dialog v-model="resetDialog" max-width="600px" persistent retain-focus>
      <v-card v-draggable class="smooth-border">
        <div class="dlg-header dlg-header--warning">
          <v-icon class="dlg-icon">mdi-alert</v-icon>
          <span class="dlg-title">Confirm Reset to Default</span>
          <v-btn icon variant="text" class="dlg-close" aria-label="Close" @click="resetDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </div>
        <v-card-text>
          <p class="mb-4">
            Are you sure you want to reset the template "{{ resettingTemplate?.name }}" to the
            system default?
          </p>
          <v-alert type="warning" variant="tonal" class="mb-4">
            This will overwrite your customizations with the latest system template. Your current
            version will be archived and can be restored later from the version history.
          </v-alert>
          <p class="text-caption text-muted-a11y">
            This action creates a backup in version history before resetting.
          </p>
        </v-card-text>
        <div class="dlg-footer">
          <v-spacer />
          <v-btn variant="text" @click="resetDialog = false">Cancel</v-btn>
          <v-btn color="warning" variant="flat" :loading="resetting" @click="resetTemplate">
            Reset to Default
          </v-btn>
        </div>
      </v-card>
    </v-dialog>

    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, onUnmounted, watch } from 'vue'
import api from '@/services/api'
import { format } from 'date-fns'
import { useWebSocketV2 } from '@/composables/useWebSocket'
import { useUserStore } from '@/stores/user'
import { useToast } from '@/composables/useToast'
import { getAgentColor as getAgentColorConfig } from '@/config/agentColors'
import { hexToRgba } from '@/utils/colorUtils'
import { useTemplateData } from '@/composables/useTemplateData'

// Handover 0335: WebSocket setup for real-time export status updates
const { on, off } = useWebSocketV2()
const userStore = useUserStore()
const { showToast } = useToast()
const currentTenantKey = computed(() => userStore.currentUser?.tenant_key)

// Handover 0335: Inject template export event from parent (UserSettings.vue)
const templateExportEvent = inject('templateExportEvent', ref(null))

// Search and filters (owned here, passed into composable)
const search = ref('')
const filterCategory = ref(null)
const filterStatus = ref(null)

// Template data composable
const {
  templates,
  loading,
  previewContent,
  editingTemplate,
  filteredTemplates,
  generatedName,
  totalActiveAgents,
  totalCapacity,
  remainingUserSlots,
  userAgentLimit,
  loadTemplates,
  loadActiveCount,
  resetEditingTemplate,
} = useTemplateData(search, filterCategory, filterStatus)

// Dialog loading states
const saving = ref(false)
const deleting = ref(false)
const resetting = ref(false)

// Dialogs
const editDialog = ref(false)
const deleteDialog = ref(false)
const resetDialog = ref(false)

// Template being deleted / reset
const deletingTemplate = ref(null)
const resettingTemplate = ref(null)

// Table configuration
const headers = [
  { title: 'Agent Name', key: 'name', align: 'start' },
  { title: 'Role', key: 'role', align: 'start' },
  { title: 'Active', key: 'is_active', align: 'center' },
  { title: 'Export Status', key: 'export_status', align: 'center', sortable: false },
  { title: 'Updated', key: 'updated_at', align: 'start' },
  { title: 'Actions', key: 'actions', sortable: false, width: '4%', align: 'center' },
]

const categories = ['role', 'project_type', 'custom']

const roleOptions = [
  'analyzer',
  'designer',
  'frontend',
  'backend',
  'implementer',
  'tester',
  'reviewer',
  'documenter',
]

const statusOptions = [
  { title: 'Active', value: 'active' },
  { title: 'Archived', value: 'archived' },
  { title: 'Draft', value: 'draft' },
]

// Handover 0075: Handle active toggle with validation
const handleToggleActive = async (template, newValue) => {
  try {
    await api.templates.update(template.id, { is_active: newValue })
    template.is_active = newValue
    await loadActiveCount()
    if (newValue) {
      showToast({ message: 'Agent activated - re-export required', type: 'warning' })
    } else {
      showToast({ message: 'Agent deactivated', type: 'info' })
    }
    localStorage.setItem('agent_export_stale', 'true')
  } catch (error) {
    const errorMsg = error.response?.data?.detail || 'Failed to update agent'
    showToast({ message: errorMsg, type: 'error' })
    await loadTemplates()
  }
}

const openCreateDialog = () => {
  resetEditingTemplate()
  previewContent.value = ''
  editDialog.value = true
}

const editTemplate = async (template) => {
  editingTemplate.value = {
    ...template,
    user_instructions: template.user_instructions || '',
    cli_tool: template.cli_tool || 'claude',
    custom_suffix: '',
    background_color: template.background_color || '',
    model: template.model || 'sonnet',
    tools: template.tools || null,
  }
  previewContent.value = ''
  editDialog.value = true

  if (template.id) {
    try {
      const previewResponse = await api.templates.preview(template.id, {})
      previewContent.value = previewResponse.data.preview
    } catch (error) {
      console.error('Failed to load preview:', error)
    }
  }
}

const duplicateTemplate = (template) => {
  editingTemplate.value = {
    ...template,
    id: null,
    name: `${template.name} (Copy)`,
    user_instructions: template.user_instructions || '',
    cli_tool: template.cli_tool || 'claude',
    custom_suffix: '-copy',
    background_color: template.background_color || '',
    model: template.model || 'sonnet',
    tools: template.tools || null,
  }
  previewContent.value = ''
  editDialog.value = true
}

const closeEditDialog = () => {
  editDialog.value = false
  previewContent.value = ''
  resetEditingTemplate()
}

// Handover 0103: Handle role change (auto-set background_color)
const onRoleChange = (newRole) => {
  editingTemplate.value.background_color = getCategoryColor(newRole)
}

// Handover 0103: Save template and generate preview
const saveTemplateAndPreview = async () => {
  saving.value = true
  try {
    const data = {
      name: generatedName.value || editingTemplate.value.role,
      category: 'role',
      role: editingTemplate.value.role || null,
      cli_tool: editingTemplate.value.cli_tool,
      custom_suffix: editingTemplate.value.custom_suffix || null,
      background_color: editingTemplate.value.background_color,
      description: editingTemplate.value.description,
      user_instructions: editingTemplate.value.user_instructions,
      model: editingTemplate.value.model || null,
      tools: editingTemplate.value.tools,
      behavioral_rules: editingTemplate.value.behavioral_rules || [],
      success_criteria: editingTemplate.value.success_criteria || [],
      tags: editingTemplate.value.tags || [],
      is_default: editingTemplate.value.is_default || false,
    }

    let templateId = editingTemplate.value.id

    if (editingTemplate.value.id) {
      await api.templates.update(editingTemplate.value.id, {
        name: data.name,
        role: data.role,
        cli_tool: data.cli_tool,
        background_color: data.background_color,
        user_instructions: data.user_instructions,
        description: data.description,
        model: data.model,
        tools: data.tools,
        behavioral_rules: data.behavioral_rules,
        success_criteria: data.success_criteria,
        tags: data.tags,
        is_default: data.is_default,
      })
    } else {
      const response = await api.templates.create(data)
      templateId = response.data.id
    }

    const previewResponse = await api.templates.preview(templateId, {})
    previewContent.value = previewResponse.data.preview
    await loadTemplates()
  } catch (error) {
    console.error('Failed to save template:', error)
    previewContent.value = ''
    showToast({
      message: error.response?.data?.detail || 'Failed to save template. Check your connection and try again.',
      type: 'error',
      title: 'Error',
    })
  } finally {
    saving.value = false
  }
}

const confirmDelete = (template) => {
  deletingTemplate.value = template
  deleteDialog.value = true
}

const deleteTemplate = async () => {
  deleting.value = true
  try {
    await api.templates.delete(deletingTemplate.value.id)
    await loadTemplates()
    deleteDialog.value = false
    deletingTemplate.value = null
  } catch (error) {
    console.error('Failed to delete template:', error)
  } finally {
    deleting.value = false
  }
}

const getCategoryColor = (role) => getAgentColorConfig(role).hex

const formatDate = (date) => {
  if (!date) return 'N/A'
  return format(new Date(date), 'MMM dd, yyyy HH:mm')
}

const confirmReset = (template) => {
  resettingTemplate.value = template
  resetDialog.value = true
}

const resetTemplate = async () => {
  resetting.value = true
  try {
    await api.templates.reset(resettingTemplate.value.id)
    await loadTemplates()
    resetDialog.value = false
    resettingTemplate.value = null
  } catch (error) {
    console.error('Failed to reset template:', error)
  } finally {
    resetting.value = false
  }
}

// Handover 0335: Handle template export WebSocket event
const handleTemplateExported = (data) => {
  const { tenant_key: tenantKey, template_ids: templateIds, exported_at: exportedAt } = data
  if (!tenantKey || !templateIds || !exportedAt) return
  if (tenantKey !== currentTenantKey.value) return

  const templateIdSet = new Set(templateIds)
  templates.value.forEach((template) => {
    if (templateIdSet.has(template.id)) {
      template.last_exported_at = exportedAt
      template.may_be_stale = false
    }
  })
}

// Lifecycle
onMounted(() => {
  loadTemplates()
  loadActiveCount()
  on('template:exported', handleTemplateExported)
})

onUnmounted(() => {
  off('template:exported', handleTemplateExported)
})

// Handover 0335: Watch for export events from parent (UserSettings.vue)
watch(
  templateExportEvent,
  (newEvent) => {
    if (!newEvent) return
    if (newEvent.tenant_key !== currentTenantKey.value) return
    handleTemplateExported(newEvent)
  },
  { deep: true }
)
</script>

<style scoped lang="scss">
@use '../styles/design-tokens' as *;

/* 0873: filter bar layout (matches TasksView pattern) */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.filter-search {
  flex: 1;
}

.filter-search :deep(.v-field) {
  box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255, 255, 255, 0.10));
  border-radius: $border-radius-default;
}

.filter-search :deep(.v-field:focus-within) {
  box-shadow: inset 0 0 0 1px rgba($color-brand-yellow, 0.3);
}

.filter-select {
  flex: 0 0 160px;
}

.filter-select :deep(.v-field) {
  box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255, 255, 255, 0.10));
  border-radius: $border-radius-default;
}

.filter-clear-btn {
  color: $color-text-muted !important;
  font-size: 0.72rem;
  text-transform: none;
  letter-spacing: 0;
}

@media (max-width: 960px) {
  .filter-bar {
    flex-wrap: wrap;
  }
  .filter-search {
    max-width: 100%;
  }
}

.template-role-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: $border-radius-default;
  font-size: 0.75rem;
  font-weight: 600;
}

.template-manager {
  border: none !important;
  border-radius: $border-radius-rounded !important;
  overflow: hidden;
  background: $elevation-raised;

  :deep(.v-table) {
    background: transparent;
  }

  .templates-table {
    :deep(.v-data-table-footer) {
      background: var(--v-theme-surface);
      color: var(--v-theme-on-surface);
    }
  }

  .template-editor {
    font-family: 'Roboto Mono', monospace;
    background: var(--v-theme-background);

    :deep(.v-field__input) {
      color: var(--v-theme-on-surface);
    }
  }

}

// Handover 0814: Preview styling (harmonized with AgentDetailsModal)
// Outside .template-manager — v-dialog teleports to <body>, so nested selectors don't reach it
:deep(.preview-card) {
  max-height: 500px;
  overflow-y: auto;
  background-color: rgb(var(--v-theme-surface-variant));

  pre.preview-content {
    font-family: 'Courier New', Courier, monospace;
    font-size: 12px;
    line-height: 1.6;
    padding: 16px;
    margin: 0;
    white-space: pre-wrap !important;
    word-wrap: break-word;
    overflow-wrap: break-word;
    color: rgb(var(--v-theme-on-surface-variant));
  }
}

// Custom toggle colors: green when ON, faded blue when OFF
// Global switch styling is defined in App.vue; scoped overrides reinforce specificity
.v-switch {
  :deep(.v-switch__thumb) {
    background-color: rgba(33, 150, 243, 0.4); // Faded blue when OFF
  }

  :deep(.v-switch__track) {
    background-color: rgba(33, 150, 243, 0.2); // Faded blue track when OFF
  }
}

.v-switch :deep(.v-selection-control--dirty) {
  .v-switch__thumb {
    background-color: rgb(var(--v-theme-success));
  }

  .v-switch__track {
    background-color: rgba(76, 175, 80, 0.3); // Green track when ON
  }
}

// Handover 0814: CLI tool radio — centered, selected label turns yellow (matches ProjectTabs execution mode radios)
:deep(.v-radio-group) {
  .v-selection-control-group {
    justify-content: center;
  }

  .v-selection-control--dirty .v-label {
    color: rgb(var(--v-theme-primary));
    font-weight: 500;
  }
}

// Inactive template row styling
:deep(.inactive-template) {
  opacity: 0.5;

  td {
    color: var(--v-theme-on-surface);
  }
}

</style>
