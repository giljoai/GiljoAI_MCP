<template>
  <v-card class="template-manager" elevation="2">
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2" color="primary">
        <img src="/icons/document.svg" width="24" height="24" alt="Templates" />
      </v-icon>
      <span>Agent Template Manager</span>
      <v-spacer />
      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        @click="openCreateDialog"
        aria-label="Create new template"
      >
        New Template
      </v-btn>
    </v-card-title>

    <v-card-text>
      <!-- Active Agent Counter (Handover 0075) -->
      <v-alert
        v-if="activeCount !== null"
        :type="activeCount >= 8 ? 'warning' : 'info'"
        variant="tonal"
        density="compact"
        class="mb-4"
      >
        <div class="d-flex align-center justify-space-between">
          <div>
            <strong>Active Agents:</strong>
            <span :class="activeCount >= 8 ? 'text-warning' : ''">
              {{ activeCount }} / 8
            </span>
            <span class="text-medium-emphasis ml-2">
              ({{ 8 - activeCount }} slots remaining)
            </span>
          </div>
          <v-chip
            v-if="activeCount >= 8"
            size="small"
            color="warning"
            prepend-icon="mdi-alert"
          >
            Limit Reached
          </v-chip>
        </div>
        <div v-if="activeCount >= 8" class="text-body-2 mt-2">
          Maximum active agents reached. Deactivate an agent to enable another.
          <strong>Reason:</strong> Claude Code context budget limit (6-8 agents recommended).
        </div>
      </v-alert>

      <!-- Search and Filters -->
      <v-row class="mb-4">
        <v-col cols="12" md="6">
          <v-text-field
            v-model="search"
            prepend-inner-icon="mdi-magnify"
            label="Search templates"
            single-line
            hide-details
            clearable
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-select
            v-model="filterCategory"
            :items="categories"
            label="Category"
            clearable
            density="compact"
            hide-details
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-select
            v-model="filterStatus"
            :items="statusOptions"
            label="Status"
            clearable
            density="compact"
            hide-details
          />
        </v-col>
      </v-row>

      <!-- Templates Table -->
      <v-data-table
        :headers="headers"
        :items="filteredTemplates"
        :search="search"
        :loading="loading"
        class="elevation-1 templates-table"
        item-key="id"
        :items-per-page="10"
      >
        <template v-slot:item.name="{ item }">
          <div class="font-weight-medium">{{ item.name }}</div>
        </template>

        <template v-slot:item.category="{ item }">
          <v-chip size="small" :color="getCategoryColor(item.category)">
            {{ item.category }}
          </v-chip>
        </template>

        <template v-slot:item.preferred_tool="{ item }">
          <v-chip size="small" variant="outlined">
            <template v-slot:prepend>
              <v-avatar size="18" class="mr-1">
                <v-img
                  :src="getToolLogo(item.preferred_tool || 'claude')"
                  :alt="getToolName(item.preferred_tool || 'claude')"
                />
              </v-avatar>
            </template>
            {{ getToolName(item.preferred_tool || 'claude') }}
          </v-chip>
        </template>

        <template v-slot:item.variables="{ item }">
          <v-tooltip v-if="item.variables && item.variables.length > 0">
            <template v-slot:activator="{ props }">
              <v-chip v-bind="props" size="small" variant="outlined">
                {{ item.variables.length }} vars
              </v-chip>
            </template>
            <div>
              <div v-for="variable in item.variables" :key="variable">
                {{ variable }}
              </div>
            </div>
          </v-tooltip>
          <span v-else class="text-grey">None</span>
        </template>

        <template v-slot:item.updated_at="{ item }">
          <span class="text-caption">{{ formatDate(item.updated_at) }}</span>
        </template>

        <template v-slot:item.is_active="{ item }">
          <div class="d-flex align-center justify-center">
            <v-switch
              :model-value="item.is_active"
              :disabled="!item.is_active && activeCount >= 8"
              color="primary"
              hide-details
              density="compact"
              @update:model-value="handleToggleActive(item, $event)"
              :aria-label="item.is_active ? 'Deactivate agent' : 'Activate agent'"
            />
            <v-tooltip
              v-if="!item.is_active && activeCount >= 8"
              location="top"
            >
              <template v-slot:activator="{ props }">
                <v-icon v-bind="props" color="warning" size="small" class="ml-1">
                  mdi-information-outline
                </v-icon>
              </template>
              <span>
                Maximum 8 active agents allowed (context budget limit).
                Deactivate another agent first.
              </span>
            </v-tooltip>
          </div>
        </template>

        <template v-slot:item.actions="{ item }">
          <v-btn
            icon="mdi-eye"
            size="small"
            variant="text"
            @click="previewTemplate(item)"
            title="Preview"
            aria-label="Preview template"
          />
          <v-btn
            icon="mdi-pencil"
            size="small"
            variant="text"
            @click="editTemplate(item)"
            title="Edit"
            aria-label="Edit template"
          />
          <v-btn
            icon="mdi-content-copy"
            size="small"
            variant="text"
            @click="duplicateTemplate(item)"
            title="Duplicate"
            aria-label="Duplicate template"
          />
          <v-btn
            icon="mdi-history"
            size="small"
            variant="text"
            @click="viewHistory(item)"
            title="Version History"
            aria-label="View template version history"
          />
          <v-btn
            icon="mdi-compare"
            size="small"
            variant="text"
            @click="viewDiff(item)"
            title="Compare with System Default"
            aria-label="Compare template with system default"
          />
          <v-btn
            icon="mdi-refresh"
            size="small"
            variant="text"
            color="warning"
            @click="confirmReset(item)"
            title="Reset to Default"
            aria-label="Reset template to system default"
          />
          <v-btn
            icon="mdi-delete"
            size="small"
            variant="text"
            color="error"
            @click="confirmDelete(item)"
            title="Delete"
            aria-label="Delete template"
          />
        </template>
      </v-data-table>
    </v-card-text>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="editDialog" max-width="900px" persistent retain-focus>
      <v-card>
        <v-card-title class="d-flex align-center">
          <span class="text-h5">{{ editingTemplate.id ? 'Edit' : 'Create' }} Template</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" @click="closeEditDialog" aria-label="Close" />
        </v-card-title>

        <v-card-text>
          <v-container>
            <v-row>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="editingTemplate.name"
                  label="Template Name"
                  :rules="[(v) => !!v || 'Name is required']"
                  density="compact"
                >
                  <template v-slot:append-inner>
                    <v-tooltip location="top">
                      <template v-slot:activator="{ props }">
                        <v-icon v-bind="props" size="small" color="primary">mdi-help-circle</v-icon>
                      </template>
                      <span>Required field - Enter a unique name for this agent template</span>
                    </v-tooltip>
                  </template>
                </v-text-field>
              </v-col>
              <v-col cols="12" md="6">
                <v-select
                  v-model="editingTemplate.category"
                  :items="categories"
                  label="Category"
                  :rules="[(v) => !!v || 'Category is required']"
                  density="compact"
                >
                  <template v-slot:append-inner>
                    <v-tooltip location="top">
                      <template v-slot:activator="{ props }">
                        <v-icon v-bind="props" size="small" color="primary">mdi-help-circle</v-icon>
                      </template>
                      <span>Required field - Select the agent type/category</span>
                    </v-tooltip>
                  </template>
                </v-select>
              </v-col>
              <v-col cols="12" md="6">
                <v-select
                  v-model="editingTemplate.preferred_tool"
                  :items="toolOptions"
                  label="Preferred Tool"
                  :rules="[(v) => !!v || 'Tool is required']"
                  density="compact"
                >
                  <template v-slot:item="{ item, props }">
                    <v-list-item v-bind="props">
                      <template v-slot:prepend>
                        <v-avatar size="24">
                          <v-img :src="item.raw.logo" :alt="item.raw.title" />
                        </v-avatar>
                      </template>
                    </v-list-item>
                  </template>
                  <template v-slot:selection="{ item }">
                    <v-avatar size="20" class="mr-2">
                      <v-img :src="item.raw.logo" :alt="item.raw.title" />
                    </v-avatar>
                    {{ item.raw.title }}
                  </template>
                </v-select>
                <v-tooltip location="top">
                  <template v-slot:activator="{ props }">
                    <v-icon v-bind="props" size="small" color="primary" class="ml-2"
                      >mdi-help-circle</v-icon
                    >
                  </template>
                  <span
                    >Required field - Select the AI tool for this template</span
                  >
                </v-tooltip>
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="editingTemplate.description"
                  label="Description"
                  density="compact"
                />
              </v-col>
              <v-col cols="12">
                <div class="d-flex align-center mb-2">
                  <span class="text-subtitle-2">Template Content</span>
                  <v-tooltip location="top">
                    <template v-slot:activator="{ props }">
                      <v-icon v-bind="props" size="small" color="primary" class="ml-2"
                        >mdi-help-circle</v-icon
                      >
                    </template>
                    <span
                      >Required field - Enter the template content with {variable}
                      placeholders</span
                    >
                  </v-tooltip>
                </div>
                <v-textarea
                  v-model="editingTemplate.template"
                  label="Template (supports {variable} placeholders)"
                  :rules="[(v) => !!v || 'Template content is required']"
                  rows="10"
                  variant="outlined"
                  density="compact"
                  class="template-editor"
                />
              </v-col>
              <v-col cols="12" md="6">
                <div class="text-subtitle-2 mb-2">Variables</div>
                <v-chip
                  v-for="variable in detectedVariables"
                  :key="variable"
                  class="mr-2 mb-2"
                  size="small"
                  color="primary"
                  variant="outlined"
                >
                  {{ variable }}
                </v-chip>
                <div v-if="detectedVariables.length === 0" class="text-caption text-grey">
                  No variables detected. Use {variableName} syntax.
                </div>
              </v-col>
              <v-col cols="12" md="6">
                <div class="text-subtitle-2 mb-2">Augmentation Slots</div>
                <v-textarea
                  v-model="editingTemplate.augmentation_slots"
                  label="Define augmentation points"
                  rows="3"
                  variant="outlined"
                  density="compact"
                  hint="Specify where dynamic augmentations can be inserted"
                />
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="closeEditDialog"> Cancel </v-btn>
          <v-btn color="primary" variant="flat" @click="saveTemplate" :loading="saving">
            {{ editingTemplate.id ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Preview Dialog -->
    <v-dialog v-model="previewDialog" max-width="800px" persistent retain-focus>
      <v-card>
        <v-card-title class="d-flex align-center">
          <span class="text-h5">Template Preview: {{ previewingTemplate.name }}</span>
          <v-spacer />
          <v-btn
            icon="mdi-close"
            variant="text"
            @click="previewDialog = false"
            aria-label="Close"
          />
        </v-card-title>

        <v-card-text>
          <v-container>
            <v-row>
              <v-col cols="12">
                <div class="text-subtitle-2 mb-2">Variable Values</div>
                <v-text-field
                  v-for="variable in previewVariables"
                  :key="variable.name"
                  v-model="variable.value"
                  :label="variable.name"
                  density="compact"
                  class="mb-2"
                />
              </v-col>
              <v-col cols="12">
                <div class="text-subtitle-2 mb-2">Augmentations</div>
                <v-textarea
                  v-model="previewAugmentations"
                  label="Add runtime augmentations"
                  rows="3"
                  variant="outlined"
                  density="compact"
                />
              </v-col>
              <v-col cols="12">
                <v-btn color="primary" @click="generatePreview" :loading="generating">
                  Generate Preview
                </v-btn>
              </v-col>
              <v-col cols="12" v-if="generatedMission">
                <div class="text-subtitle-2 mb-2">Generated Mission</div>
                <v-card variant="outlined" class="pa-4 generated-mission">
                  <pre>{{ generatedMission }}</pre>
                </v-card>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="previewDialog = false"> Close </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="500px" persistent retain-focus>
      <v-card>
        <v-card-title class="d-flex align-center">
          <span class="text-h5">Confirm Delete</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" @click="deleteDialog = false" aria-label="Close" />
        </v-card-title>
        <v-card-text>
          Are you sure you want to delete the template "{{ deletingTemplate?.name }}"? This will
          archive the template and it can be restored from the version history.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" variant="flat" @click="deleteTemplate" :loading="deleting">
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Version History Dialog -->
    <v-dialog v-model="historyDialog" max-width="900px" scrollable persistent retain-focus>
      <TemplateArchive
        v-if="historyDialog"
        :template="historyTemplate"
        @close="historyDialog = false"
        @restore="handleRestore"
      />
    </v-dialog>

    <!-- Reset Confirmation Dialog -->
    <v-dialog v-model="resetDialog" max-width="600px" persistent retain-focus>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="warning" class="mr-2">mdi-alert</v-icon>
          <span class="text-h5">Confirm Reset to Default</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" @click="resetDialog = false" aria-label="Close" />
        </v-card-title>
        <v-card-text>
          <p class="mb-4">
            Are you sure you want to reset the template "{{ resettingTemplate?.name }}" to the
            system default?
          </p>
          <v-alert type="warning" variant="tonal" class="mb-4">
            This will overwrite your customizations with the latest system template. Your current
            version will be archived and can be restored later from the version history.
          </v-alert>
          <p class="text-caption text-grey">
            This action creates a backup in version history before resetting.
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="resetDialog = false">Cancel</v-btn>
          <v-btn color="warning" variant="flat" @click="resetTemplate" :loading="resetting">
            Reset to Default
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Diff Viewer Dialog -->
    <v-dialog v-model="diffDialog" max-width="1200px" scrollable persistent retain-focus>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="primary" class="mr-2">mdi-compare</v-icon>
          <span class="text-h5">Template Comparison</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" @click="diffDialog = false" aria-label="Close" />
        </v-card-title>
        <v-card-text>
          <v-container v-if="diffData">
            <v-row>
              <v-col cols="12">
                <v-alert
                  v-if="!diffData.has_system_template"
                  type="info"
                  variant="tonal"
                  class="mb-4"
                >
                  No system template available for comparison. This is a custom template.
                </v-alert>
                <v-alert
                  v-else-if="diffData.changes_summary.is_identical"
                  type="success"
                  variant="tonal"
                  class="mb-4"
                >
                  This template is identical to the system default.
                </v-alert>
                <v-alert v-else type="info" variant="tonal" class="mb-4">
                  <div class="d-flex justify-space-between">
                    <div>
                      <strong>Changes Summary:</strong>
                      <span class="ml-4"
                        ><v-chip size="small" color="success" class="mr-2"
                          >+{{ diffData.changes_summary.lines_added }} lines</v-chip
                        ></span
                      >
                      <span
                        ><v-chip size="small" color="error"
                          >-{{ diffData.changes_summary.lines_removed }} lines</v-chip
                        ></span
                      >
                    </div>
                    <div>
                      <span class="text-caption"
                        >Tenant: v{{ diffData.tenant_version }} | System: v{{
                          diffData.system_version
                        }}</span
                      >
                    </div>
                  </div>
                </v-alert>
              </v-col>
              <v-col cols="12">
                <v-tabs v-model="diffViewTab" bg-color="transparent">
                  <v-tab value="unified">Unified Diff</v-tab>
                  <v-tab value="side-by-side">Side by Side</v-tab>
                </v-tabs>
                <v-window v-model="diffViewTab" class="mt-4">
                  <v-window-item value="unified">
                    <v-card variant="outlined" class="diff-viewer">
                      <pre class="pa-4">{{ diffData.diff_unified || 'No differences found.' }}</pre>
                    </v-card>
                  </v-window-item>
                  <v-window-item value="side-by-side">
                    <v-card variant="outlined" class="diff-viewer">
                      <div v-html="diffData.diff_html" class="pa-4 diff-html-container"></div>
                    </v-card>
                  </v-window-item>
                </v-window>
              </v-col>
            </v-row>
          </v-container>
          <div v-else class="text-center pa-8">
            <v-progress-circular indeterminate color="primary" />
            <p class="mt-4">Loading comparison...</p>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="diffDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '@/services/api'
import TemplateArchive from './TemplateArchive.vue'
import { format } from 'date-fns'

// Reactive data
const templates = ref([])
const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const generating = ref(false)
const activeCount = ref(null) // Handover 0075: Track active agent count

// Search and filters
const search = ref('')
const filterCategory = ref(null)
const filterStatus = ref(null)

// Dialogs
const editDialog = ref(false)
const previewDialog = ref(false)
const deleteDialog = ref(false)
const historyDialog = ref(false)
const resetDialog = ref(false)
const diffDialog = ref(false)

// Template being edited
const editingTemplate = ref({
  id: null,
  name: '',
  category: '',
  description: '',
  template: '',
  variables: [],
  augmentation_slots: '',
  preferred_tool: 'claude',
})

// Template being previewed
const previewingTemplate = ref({})
const previewVariables = ref([])
const previewAugmentations = ref('')
const generatedMission = ref('')

// Template being deleted
const deletingTemplate = ref(null)

// Template for history view
const historyTemplate = ref(null)

// Template being reset
const resettingTemplate = ref(null)
const resetting = ref(false)

// Diff viewer data
const diffData = ref(null)
const diffViewTab = ref('unified')

// Table configuration
const headers = [
  { title: 'Agent Name', key: 'name', align: 'start' },
  { title: 'Type', key: 'category', align: 'start' },
  { title: 'Tool', key: 'preferred_tool', align: 'start' },
  { title: 'Variables', key: 'variables', align: 'center' },
  { title: 'Active', key: 'is_active', align: 'center' },
  { title: 'Updated', key: 'updated_at', align: 'start' },
  { title: 'Actions', key: 'actions', align: 'center', sortable: false },
]

// Categories
const categories = [
  'orchestrator',
  'analyzer',
  'designer',
  'frontend',
  'backend',
  'implementer',
  'tester',
  'reviewer',
  'documenter',
  'custom',
]

const statusOptions = [
  { title: 'Active', value: 'active' },
  { title: 'Archived', value: 'archived' },
  { title: 'Draft', value: 'draft' },
]

const toolOptions = [
  {
    title: 'Claude',
    value: 'claude',
    logo: '/claude_pix.svg',
    color: '#1976D2',
  },
  {
    title: 'Codex',
    value: 'codex',
    logo: '/icons/codex_mark.svg',
    color: '#4CAF50',
  },
  {
    title: 'Gemini',
    value: 'gemini',
    logo: '/gemini-icon.svg',
    color: '#9C27B0',
  },
]

// Computed
const filteredTemplates = computed(() => {
  let filtered = templates.value

  if (filterCategory.value) {
    filtered = filtered.filter((t) => t.category === filterCategory.value)
  }

  if (filterStatus.value) {
    filtered = filtered.filter((t) => t.status === filterStatus.value)
  }

  return filtered
})

const detectedVariables = computed(() => {
  const regex = /\{([^}]+)\}/g
  const matches = []
  let match

  while ((match = regex.exec(editingTemplate.value.template)) !== null) {
    if (!matches.includes(match[1])) {
      matches.push(match[1])
    }
  }

  return matches
})

// Methods
const loadTemplates = async () => {
  loading.value = true
  try {
    const response = await api.templates.list()
    // Map backend fields to frontend fields
    templates.value = (response.data || []).map((t) => ({
      ...t,
      template: t.template_content, // Map template_content to template for frontend
    }))
  } catch (error) {
    console.error('Failed to load templates:', error)
  } finally {
    loading.value = false
  }
}

// Handover 0075: Load active agent count
const loadActiveCount = async () => {
  try {
    const response = await api.get('/api/templates/stats/active-count')
    activeCount.value = response.data.active_count
  } catch (error) {
    console.error('[TEMPLATE MANAGER] Failed to load active count:', error)
  }
}

// Handover 0075: Handle active toggle with validation
const handleToggleActive = async (template, newValue) => {
  try {
    // Attempt to update
    await api.templates.update(template.id, {
      is_active: newValue
    })

    // Update local template state
    template.is_active = newValue

    // Reload active count
    await loadActiveCount()

    // Show toast notification
    if (newValue) {
      // Activation succeeded - warn about re-export
      console.warn('[TEMPLATE MANAGER] Agent activated - re-export required')
      // TODO: Add toast notification when toast composable is available
      // Mark export as stale (for Option C badge)
      localStorage.setItem('agent_export_stale', 'true')
    } else {
      // Deactivation succeeded
      console.info('[TEMPLATE MANAGER] Agent deactivated')
      localStorage.setItem('agent_export_stale', 'true')
    }

  } catch (error) {
    // Validation failed (8-agent limit)
    const errorMsg = error.response?.data?.detail || 'Failed to update agent'

    console.error('[TEMPLATE MANAGER] Cannot activate agent:', errorMsg)
    // TODO: Add error toast when composable is available

    // Revert toggle (template state not changed on error)
    // No need to revert as we only update on success

    // Reload templates to ensure sync
    await loadTemplates()
  }
}

const openCreateDialog = () => {
  editingTemplate.value = {
    id: null,
    name: '',
    category: '',
    description: '',
    template: '',
    variables: [],
    augmentation_slots: '',
    preferred_tool: 'claude',
  }
  editDialog.value = true
}

const editTemplate = (template) => {
  editingTemplate.value = {
    ...template,
    template: template.template_content || template.template, // Ensure template field is set
  }
  editDialog.value = true
}

const duplicateTemplate = (template) => {
  editingTemplate.value = {
    ...template,
    id: null,
    name: `${template.name} (Copy)`,
    template: template.template_content || template.template, // Ensure template field is set
  }
  editDialog.value = true
}

const closeEditDialog = () => {
  editDialog.value = false
  editingTemplate.value = {
    id: null,
    name: '',
    category: '',
    description: '',
    template: '',
    variables: [],
    augmentation_slots: '',
    preferred_tool: 'claude',
  }
}

const saveTemplate = async () => {
  saving.value = true
  try {
    const data = {
      name: editingTemplate.value.name,
      category: editingTemplate.value.category,
      description: editingTemplate.value.description,
      template_content: editingTemplate.value.template,
      preferred_tool: editingTemplate.value.preferred_tool,
      behavioral_rules: editingTemplate.value.behavioral_rules || [],
      success_criteria: editingTemplate.value.success_criteria || [],
      tags: editingTemplate.value.tags || [],
      is_default: editingTemplate.value.is_default || false,
    }

    if (editingTemplate.value.id) {
      await api.templates.update(editingTemplate.value.id, {
        name: data.name,
        template_content: data.template_content,
        description: data.description,
        preferred_tool: data.preferred_tool,
        behavioral_rules: data.behavioral_rules,
        success_criteria: data.success_criteria,
        tags: data.tags,
        is_default: data.is_default,
      })
    } else {
      await api.templates.create(data)
    }

    await loadTemplates()
    closeEditDialog()
  } catch (error) {
    console.error('Failed to save template:', error)
  } finally {
    saving.value = false
  }
}

const previewTemplate = (template) => {
  previewingTemplate.value = template
  previewVariables.value = (template.variables || []).map((v) => ({
    name: v,
    value: '',
  }))
  previewAugmentations.value = ''
  generatedMission.value = ''
  previewDialog.value = true
}

const generatePreview = async () => {
  generating.value = true
  try {
    const variables = {}
    previewVariables.value.forEach((v) => {
      variables[v.name] = v.value
    })

    const response = await api.templates.preview(previewingTemplate.value.id, {
      variables,
      augmentations: previewAugmentations.value,
    })

    generatedMission.value = response.data.mission
  } catch (error) {
    console.error('Failed to generate preview:', error)
  } finally {
    generating.value = false
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

const viewHistory = (template) => {
  historyTemplate.value = template
  historyDialog.value = true
}

const handleRestore = async (version) => {
  try {
    await api.templates.restore(version.template_id, version.id)
    await loadTemplates()
    historyDialog.value = false
  } catch (error) {
    console.error('Failed to restore template version:', error)
  }
}

const getCategoryColor = (category) => {
  const colors = {
    orchestrator: 'primary',
    analyzer: 'info',
    designer: 'purple',
    frontend: 'success',
    backend: 'orange',
    implementer: 'cyan',
    tester: 'pink',
    reviewer: 'indigo',
    documenter: 'brown',
    custom: 'grey',
  }
  return colors[category] || 'grey'
}

const getToolLogo = (tool) => {
  const logos = {
    claude: '/claude_pix.svg',
    codex: '/icons/codex_mark.svg',
    gemini: '/gemini-icon.svg',
  }
  return logos[tool] || logos.claude
}

const getToolName = (tool) => {
  const names = {
    claude: 'Claude',
    codex: 'Codex',
    gemini: 'Gemini',
  }
  return names[tool] || 'Claude'
}

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
    const response = await api.templates.reset(resettingTemplate.value.id)
    console.log('Template reset response:', response.data)
    await loadTemplates()
    resetDialog.value = false
    resettingTemplate.value = null
    // Show success notification
  } catch (error) {
    console.error('Failed to reset template:', error)
    // Show error notification
  } finally {
    resetting.value = false
  }
}

const viewDiff = async (template) => {
  diffData.value = null
  diffDialog.value = true
  diffViewTab.value = 'unified'

  try {
    const response = await api.templates.diff(template.id)
    diffData.value = response.data
  } catch (error) {
    console.error('Failed to load template diff:', error)
    // Show error notification
  }
}

// Lifecycle
onMounted(() => {
  loadTemplates()
  loadActiveCount() // Handover 0075: Load active agent count
})

// Watch for variable changes
watch(
  () => editingTemplate.value.template,
  () => {
    editingTemplate.value.variables = detectedVariables.value
  },
)
</script>

<style scoped lang="scss">
.template-manager {
  background: var(--v-theme-surface-variant);

  .templates-table {
    background: var(--v-theme-surface);

    :deep(.v-data-table__th) {
      background: var(--v-theme-background) !important;
      color: var(--v-theme-primary) !important;
      font-weight: 600;
    }

    :deep(.v-data-table__td) {
      color: var(--v-theme-on-surface);
    }

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

  .generated-mission {
    background: var(--v-theme-background);
    color: var(--v-theme-on-surface);

    pre {
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
    }
  }

  .diff-viewer {
    background: var(--v-theme-background);
    color: var(--v-theme-on-surface);
    max-height: 600px;
    overflow: auto;

    pre {
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
      font-family: 'Roboto Mono', monospace;
      font-size: 12px;
      line-height: 1.5;
    }

    .diff-html-container {
      :deep(table) {
        background: var(--v-theme-background);
        color: var(--v-theme-on-surface);
        border-collapse: collapse;
        width: 100%;
        font-size: 12px;
        font-family: 'Roboto Mono', monospace;

        td,
        th {
          padding: 2px 10px;
          border: 1px solid var(--v-theme-on-surface-variant);
          vertical-align: top;
        }

        th {
          background: var(--v-theme-surface);
          color: var(--v-theme-primary);
          font-weight: 600;
        }

        .diff_add {
          background-color: rgba(var(--v-theme-success), 0.1);
          color: var(--v-theme-success);
        }

        .diff_sub {
          background-color: rgba(var(--v-theme-error), 0.1);
          color: var(--v-theme-error);
        }

        .diff_chg {
          background-color: rgba(var(--v-theme-warning), 0.1);
          color: var(--v-theme-warning);
        }
      }
    }
  }
}
</style>
