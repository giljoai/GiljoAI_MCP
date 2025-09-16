<template>
  <v-card class="template-manager" elevation="2">
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2" color="primary">
        <img src="/icons/document.svg" width="24" height="24" alt="Templates" />
      </v-icon>
      <span>Template Manager</span>
      <v-spacer />
      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        @click="openCreateDialog"
      >
        New Template
      </v-btn>
    </v-card-title>

    <v-card-text>
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

        <template v-slot:item.variables="{ item }">
          <v-tooltip v-if="item.variables && item.variables.length > 0">
            <template v-slot:activator="{ props }">
              <v-chip
                v-bind="props"
                size="small"
                variant="outlined"
              >
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

        <template v-slot:item.actions="{ item }">
          <v-btn
            icon="mdi-eye"
            size="small"
            variant="text"
            @click="previewTemplate(item)"
            title="Preview"
          />
          <v-btn
            icon="mdi-pencil"
            size="small"
            variant="text"
            @click="editTemplate(item)"
            title="Edit"
          />
          <v-btn
            icon="mdi-content-copy"
            size="small"
            variant="text"
            @click="duplicateTemplate(item)"
            title="Duplicate"
          />
          <v-btn
            icon="mdi-history"
            size="small"
            variant="text"
            @click="viewHistory(item)"
            title="Version History"
          />
          <v-btn
            icon="mdi-delete"
            size="small"
            variant="text"
            color="error"
            @click="confirmDelete(item)"
            title="Delete"
          />
        </template>
      </v-data-table>
    </v-card-text>

    <!-- Create/Edit Dialog -->
    <v-dialog
      v-model="editDialog"
      max-width="900px"
      persistent
    >
      <v-card @click.stop>
        <v-card-title>
          <span class="text-h5">{{ editingTemplate.id ? 'Edit' : 'Create' }} Template</span>
        </v-card-title>

        <v-card-text>
          <v-container>
            <v-row>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="editingTemplate.name"
                  label="Template Name*"
                  :rules="[v => !!v || 'Name is required']"
                  density="compact"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-select
                  v-model="editingTemplate.category"
                  :items="categories"
                  label="Category*"
                  :rules="[v => !!v || 'Category is required']"
                  density="compact"
                />
              </v-col>
              <v-col cols="12">
                <v-text-field
                  v-model="editingTemplate.description"
                  label="Description"
                  density="compact"
                />
              </v-col>
              <v-col cols="12">
                <div class="text-subtitle-2 mb-2">Template Content*</div>
                <v-textarea
                  v-model="editingTemplate.template"
                  label="Template (supports {variable} placeholders)"
                  :rules="[v => !!v || 'Template content is required']"
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
          <v-btn
            variant="text"
            @click="closeEditDialog"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            variant="flat"
            @click="saveTemplate"
            :loading="saving"
          >
            {{ editingTemplate.id ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Preview Dialog -->
    <v-dialog
      v-model="previewDialog"
      max-width="800px"
    >
      <v-card @click.stop>
        <v-card-title>
          <span class="text-h5">Template Preview: {{ previewingTemplate.name }}</span>
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
                <v-btn
                  color="primary"
                  @click="generatePreview"
                  :loading="generating"
                >
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
          <v-btn
            variant="text"
            @click="previewDialog = false"
          >
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog
      v-model="deleteDialog"
      max-width="500px"
    >
      <v-card @click.stop>
        <v-card-title class="text-h5">Confirm Delete</v-card-title>
        <v-card-text>
          Are you sure you want to delete the template "{{ deletingTemplate?.name }}"?
          This will archive the template and it can be restored from the version history.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false">Cancel</v-btn>
          <v-btn
            color="error"
            variant="flat"
            @click="deleteTemplate"
            :loading="deleting"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Version History Dialog -->
    <v-dialog
      v-model="historyDialog"
      max-width="900px"
      scrollable
    >
      <TemplateArchive
        v-if="historyDialog"
        :template="historyTemplate"
        @close="historyDialog = false"
        @restore="handleRestore"
      />
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

// Search and filters
const search = ref('')
const filterCategory = ref(null)
const filterStatus = ref(null)

// Dialogs
const editDialog = ref(false)
const previewDialog = ref(false)
const deleteDialog = ref(false)
const historyDialog = ref(false)

// Template being edited
const editingTemplate = ref({
  id: null,
  name: '',
  category: '',
  description: '',
  template: '',
  variables: [],
  augmentation_slots: ''
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

// Table configuration
const headers = [
  { title: 'Name', key: 'name', align: 'start' },
  { title: 'Category', key: 'category', align: 'start' },
  { title: 'Description', key: 'description', align: 'start' },
  { title: 'Variables', key: 'variables', align: 'center' },
  { title: 'Updated', key: 'updated_at', align: 'start' },
  { title: 'Actions', key: 'actions', align: 'center', sortable: false }
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
  'custom'
]

const statusOptions = [
  { title: 'Active', value: 'active' },
  { title: 'Archived', value: 'archived' },
  { title: 'Draft', value: 'draft' }
]

// Computed
const filteredTemplates = computed(() => {
  let filtered = templates.value

  if (filterCategory.value) {
    filtered = filtered.filter(t => t.category === filterCategory.value)
  }

  if (filterStatus.value) {
    filtered = filtered.filter(t => t.status === filterStatus.value)
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
    const response = await api.get('/api/templates')
    templates.value = response.data.templates || []
  } catch (error) {
    console.error('Failed to load templates:', error)
  } finally {
    loading.value = false
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
    augmentation_slots: ''
  }
  editDialog.value = true
}

const editTemplate = (template) => {
  editingTemplate.value = { ...template }
  editDialog.value = true
}

const duplicateTemplate = (template) => {
  editingTemplate.value = {
    ...template,
    id: null,
    name: `${template.name} (Copy)`
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
    augmentation_slots: ''
  }
}

const saveTemplate = async () => {
  saving.value = true
  try {
    const data = {
      ...editingTemplate.value,
      variables: detectedVariables.value
    }

    if (editingTemplate.value.id) {
      await api.put(`/api/templates/${editingTemplate.value.id}`, data)
    } else {
      await api.post('/api/templates', data)
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
  previewVariables.value = (template.variables || []).map(v => ({
    name: v,
    value: ''
  }))
  previewAugmentations.value = ''
  generatedMission.value = ''
  previewDialog.value = true
}

const generatePreview = async () => {
  generating.value = true
  try {
    const variables = {}
    previewVariables.value.forEach(v => {
      variables[v.name] = v.value
    })

    const response = await api.post(`/api/templates/${previewingTemplate.value.id}/preview`, {
      variables,
      augmentations: previewAugmentations.value
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
    await api.delete(`/api/templates/${deletingTemplate.value.id}`)
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
    await api.post(`/api/templates/${version.template_id}/restore`, {
      version_id: version.id
    })
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
    custom: 'grey'
  }
  return colors[category] || 'grey'
}

const formatDate = (date) => {
  if (!date) return 'N/A'
  return format(new Date(date), 'MMM dd, yyyy HH:mm')
}

// Lifecycle
onMounted(() => {
  loadTemplates()
})

// Watch for variable changes
watch(() => editingTemplate.value.template, () => {
  editingTemplate.value.variables = detectedVariables.value
})
</script>

<style scoped lang="scss">
.template-manager {
  background: #1e3147;

  .templates-table {
    background: #182739;

    :deep(.v-data-table__th) {
      background: #0e1c2d !important;
      color: #ffc300 !important;
      font-weight: 600;
    }

    :deep(.v-data-table__td) {
      color: #e1e1e1;
    }

    :deep(.v-data-table-footer) {
      background: #182739;
      color: #e1e1e1;
    }
  }

  .template-editor {
    font-family: 'Roboto Mono', monospace;
    background: #0e1c2d;

    :deep(.v-field__input) {
      color: #e1e1e1;
    }
  }

  .generated-mission {
    background: #0e1c2d;
    color: #e1e1e1;

    pre {
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
    }
  }
}
</style>