<template>
  <v-card class="template-manager" elevation="2">
    <v-card-title class="d-flex align-center">
      <span>Agent Template Manager</span>
      <v-tooltip location="top" max-width="400">
        <template #activator="{ props }">
          <v-icon v-bind="props" color="warning" size="small" class="ml-2">mdi-alert</v-icon>
        </template>
        <span
          ><strong>Context Budget Recommendation:</strong> Template manager is limiting to 8 agents
          types maximum. Each agent description consumes context budget, reducing available tokens
          for your project during implementation.</span
        >
      </v-tooltip>
      <v-spacer />
      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        aria-label="Create new template"
        @click="openCreateDialog"
      >
        New Template
      </v-btn>
    </v-card-title>

    <v-card-text>
      <!-- Active Agent Counter (Handover 0075) -->
      <v-alert
        v-if="totalActiveAgents !== null"
        :type="remainingUserSlots === 0 ? 'warning' : 'info'"
        variant="tonal"
        density="compact"
        class="mb-4"
      >
        <div class="d-flex align-center justify-space-between">
          <div>
            <strong>Active Agents:</strong>
            <span :class="remainingUserSlots === 0 ? 'text-warning' : ''">
              {{ totalActiveAgents }} / {{ totalCapacity }}
            </span>
            <span class="text-medium-emphasis ml-2">
              ({{ remainingUserSlots }} user slots remaining — {{ systemReservedSlots }} reserved
              for Orchestrator)
            </span>
          </div>
          <v-chip
            v-if="remainingUserSlots === 0"
            size="small"
            color="warning"
            prepend-icon="mdi-alert"
          >
            User Limit Reached
          </v-chip>
        </div>
        <div v-if="remainingUserSlots === 0" class="text-body-2 mt-2">
          Maximum user-managed agents reached ({{ userAgentLimit }}). Orchestrator remains always-on
          and reserved. Deactivate an agent to enable another.
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
        :item-class="(item) => (item.is_active ? '' : 'inactive-template')"
      >
        <template v-slot:item.name="{ item }">
          <div class="font-weight-medium">{{ item.name }}</div>
        </template>

        <template v-slot:item.role="{ item }">
          <v-chip
            size="small"
            :style="{
              backgroundColor: getCategoryColor(item.role),
              color: '#1e3a5f',
              opacity: item.is_active ? 1 : 0.4,
            }"
          >
            {{ item.role }}
          </v-chip>
        </template>

        <template v-slot:item.cli_tool="{ item }">
          <v-chip size="small" variant="outlined">
            <template v-slot:prepend>
              <v-avatar
                size="18"
                class="mr-1"
                :class="{ 'codex-icon': item.cli_tool === 'codex' }"
              >
                <v-img
                  :src="getToolLogo(item.cli_tool || 'claude')"
                  :alt="getToolName(item.cli_tool || 'claude')"
                />
              </v-avatar>
            </template>
            {{ getToolName(item.cli_tool || 'claude') }}
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

        <template v-slot:item.export_status="{ item }">
          <div class="d-flex flex-column align-center">
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
                  class="text-caption text-grey"
                  :class="{ 'text-warning': item.may_be_stale }"
                >
                  {{ item.last_exported_at ? formatDate(item.last_exported_at) : 'Never exported' }}
                </span>
              </template>
              <span v-if="item.may_be_stale">
                This template was modified after the last export. Re-export to CLI tools to get the
                latest version.
              </span>
              <span v-else-if="item.last_exported_at">
                Last exported: {{ formatDate(item.last_exported_at) }}
              </span>
              <span v-else>
                This template has never been exported to CLI tools. Use the export feature to make it
                available.
              </span>
            </v-tooltip>
          </div>
        </template>

        <template v-slot:item.is_active="{ item }">
          <div class="d-flex align-center justify-center">
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
          </div>
        </template>

        <template v-slot:item.actions="{ item }">
          <v-btn
            icon="mdi-eye"
            size="small"
            variant="text"
            title="Preview"
            aria-label="Preview template"
            @click="previewTemplate(item)"
          />
          <v-btn
            icon="mdi-pencil"
            size="small"
            variant="text"
            title="Edit"
            aria-label="Edit template"
            @click="editTemplate(item)"
          />
          <v-btn
            icon="mdi-content-copy"
            size="small"
            variant="text"
            title="Duplicate"
            aria-label="Duplicate template"
            @click="duplicateTemplate(item)"
          />
          <v-btn
            icon="mdi-history"
            size="small"
            variant="text"
            title="Version History"
            aria-label="View template version history"
            @click="viewHistory(item)"
          />
          <v-btn
            icon="mdi-compare"
            size="small"
            variant="text"
            title="Compare with System Default"
            aria-label="Compare template with system default"
            @click="viewDiff(item)"
          />
          <v-btn
            icon="mdi-refresh"
            size="small"
            variant="text"
            title="Reset to Default"
            aria-label="Reset template to system default"
            @click="confirmReset(item)"
          />
          <v-btn
            icon="mdi-delete"
            size="small"
            variant="text"
            color="error"
            title="Delete"
            aria-label="Delete template"
            @click="confirmDelete(item)"
          />
        </template>
      </v-data-table>
    </v-card-text>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="editDialog" max-width="900px" persistent retain-focus>
      <v-card v-draggable>
        <v-card-title class="d-flex align-center">
          <span class="text-h5">{{ editingTemplate.id ? 'Edit' : 'Create' }} Template</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" aria-label="Close" @click="closeEditDialog" />
        </v-card-title>

        <v-card-text>
          <v-container>
            <v-row>
              <!-- CLI Tool Selector (FIRST FIELD) -->
              <v-col cols="12">
                <div class="text-subtitle-2 mb-2">
                  CLI Tool
                  <v-tooltip location="right">
                    <template v-slot:activator="{ props }">
                      <v-icon v-bind="props" size="small" color="primary" class="ml-1"
                        >mdi-help-circle</v-icon
                      >
                    </template>
                    <span>Select the AI coding tool for this agent template</span>
                  </v-tooltip>
                </div>
                <v-radio-group
                  v-model="editingTemplate.cli_tool"
                  inline
                  density="compact"
                  aria-label="Select CLI tool"
                  @update:model-value="onCliToolChange"
                >
                  <v-radio
                    v-for="tool in cliToolOptions"
                    :key="tool.value"
                    :value="tool.value"
                    :label="tool.title"
                  >
                    <template v-slot:label>
                      <div class="d-flex align-center">
                        <v-avatar
                          v-if="tool.logo"
                          size="20"
                          class="mr-2"
                          :class="{ 'codex-icon': tool.value === 'codex' }"
                        >
                          <v-img :src="tool.logo" :alt="tool.title" />
                        </v-avatar>
                        <span>{{ tool.title }}</span>
                      </div>
                    </template>
                  </v-radio>
                </v-radio-group>
              </v-col>

              <!-- Role Selector -->
              <v-col cols="12" md="6">
                <v-select
                  v-model="editingTemplate.role"
                  :items="roleOptions"
                  label="Role"
                  :rules="[(v) => !!v || 'Role is required']"
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

              <!-- Custom Suffix with Live Name Preview -->
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="editingTemplate.custom_suffix"
                  label="Custom Suffix (optional)"
                  density="compact"
                  hint="Letters, numbers, and hyphens only"
                  persistent-hint
                  aria-label="Custom agent name suffix"
                >
                  <template v-slot:append-inner>
                    <v-tooltip location="top">
                      <template v-slot:activator="{ props }">
                        <v-icon v-bind="props" size="small" color="primary">mdi-help-circle</v-icon>
                      </template>
                      <span
                        >Add a suffix to customize the agent name (e.g.,
                        'implementer-fastapi')</span
                      >
                    </v-tooltip>
                  </template>
                </v-text-field>
                <div v-if="generatedName" class="text-caption text-primary mt-1">
                  Agent Name: <strong>{{ generatedName }}</strong>
                </div>
              </v-col>

              <!-- Description (Conditional - Claude only) -->
              <v-col v-if="showDescription" cols="12">
                <v-text-field
                  v-model="editingTemplate.description"
                  label="Description"
                  density="compact"
                  hint="Short description of agent responsibilities (required for Claude)"
                  persistent-hint
                  aria-label="Agent description"
                >
                  <template v-slot:append-inner>
                    <v-tooltip location="top">
                      <template v-slot:activator="{ props }">
                        <v-icon v-bind="props" size="small" color="primary">mdi-help-circle</v-icon>
                      </template>
                      <span>Required for Claude - Brief description of what this agent does</span>
                    </v-tooltip>
                  </template>
                </v-text-field>
              </v-col>

              <!-- Model (Conditional - Claude dropdown, others read-only) -->
              <v-col cols="12" md="6">
                <v-select
                  v-if="modelOptions.length > 0"
                  v-model="editingTemplate.model"
                  :items="modelOptions"
                  label="Model"
                  density="compact"
                  aria-label="Select Claude model"
                >
                  <template v-slot:append-inner>
                    <v-tooltip location="top">
                      <template v-slot:activator="{ props }">
                        <v-icon v-bind="props" size="small" color="primary">mdi-help-circle</v-icon>
                      </template>
                      <span>Select Claude model (sonnet, opus, haiku)</span>
                    </v-tooltip>
                  </template>
                </v-select>
                <v-text-field
                  v-else
                  :model-value="editingTemplate.cli_tool === 'claude' ? 'sonnet' : 'Default'"
                  label="Model"
                  density="compact"
                  readonly
                  aria-label="Model name"
                >
                  <template v-slot:append-inner>
                    <v-tooltip location="top">
                      <template v-slot:activator="{ props }">
                        <v-icon v-bind="props" size="small" color="info"
                          >mdi-information-outline</v-icon
                        >
                      </template>
                      <span
                        >Model determined by {{ editingTemplate.cli_tool }} CLI configuration</span
                      >
                    </v-tooltip>
                  </template>
                </v-text-field>
              </v-col>

              <!-- System Prompt -->
              <v-col cols="12">
                <div class="d-flex align-center mb-2">
                  <span class="text-subtitle-2">System Prompt</span>
                  <v-tooltip location="top">
                    <template v-slot:activator="{ props }">
                      <v-icon v-bind="props" size="small" color="primary" class="ml-2"
                        >mdi-help-circle</v-icon
                      >
                    </template>
                    <span
                      >Required field - Enter the agent's system prompt (minimum 20
                      characters)</span
                    >
                  </v-tooltip>
                </div>
                <v-textarea
                  v-model="editingTemplate.template"
                  label="System Prompt"
                  :rules="[
                    (v) => !!v || 'System prompt is required',
                    (v) => (v && v.length >= 20) || 'Minimum 20 characters required',
                  ]"
                  rows="12"
                  variant="outlined"
                  density="compact"
                  class="template-editor"
                  aria-label="Agent system prompt"
                />
              </v-col>

              <!-- Preview Window (Collapsible) -->
              <v-col v-if="previewContent" cols="12">
                <v-expansion-panels>
                  <v-expansion-panel>
                    <v-expansion-panel-title>
                      <div class="d-flex align-center">
                        <v-icon class="mr-2" color="primary">mdi-eye</v-icon>
                        <span>Preview</span>
                      </div>
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <div class="preview-container">
                        <v-btn
                          size="small"
                          prepend-icon="mdi-content-copy"
                          variant="outlined"
                          class="mb-2"
                          aria-label="Copy preview to clipboard"
                          @click="copyPreview"
                        >
                          Copy to Clipboard
                        </v-btn>
                        <pre class="preview-content">{{ previewContent }}</pre>
                      </div>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="closeEditDialog"> Cancel </v-btn>
          <v-btn color="primary" variant="flat" :loading="saving" @click="saveTemplateAndPreview">
            Save and Generate Preview
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Preview Dialog -->
    <v-dialog v-model="previewDialog" max-width="800px" persistent retain-focus>
      <v-card v-draggable>
        <v-card-title class="d-flex align-center">
          <span class="text-h5">Template Preview: {{ previewingTemplate.name }}</span>
          <v-spacer />
          <v-btn
            icon="mdi-close"
            variant="text"
            aria-label="Close"
            @click="previewDialog = false"
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
                <v-btn color="primary" :loading="generating" @click="generatePreview">
                  Generate Preview
                </v-btn>
              </v-col>
              <v-col v-if="generatedMission" cols="12">
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
      <v-card v-draggable>
        <v-card-title class="d-flex align-center">
          <v-icon color="error" class="mr-2">mdi-alert</v-icon>
          <span class="text-h5">Permanently Delete Template</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" aria-label="Close" @click="deleteDialog = false" />
        </v-card-title>
        <v-card-text>
          <v-alert type="error" variant="tonal" class="mb-4">
            <strong>This action cannot be undone.</strong>
          </v-alert>
          <p>
            Are you sure you want to permanently delete the template
            "<strong>{{ deletingTemplate?.name }}</strong>"?
          </p>
          <p class="text-caption text-grey mt-2">
            This will remove the template and all its version history.
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" variant="flat" :loading="deleting" @click="deleteTemplate">
            Delete Permanently
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
      <v-card v-draggable>
        <v-card-title class="d-flex align-center">
          <v-icon color="warning" class="mr-2">mdi-alert</v-icon>
          <span class="text-h5">Confirm Reset to Default</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" aria-label="Close" @click="resetDialog = false" />
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
          <v-btn color="warning" variant="flat" :loading="resetting" @click="resetTemplate">
            Reset to Default
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Diff Viewer Dialog -->
    <v-dialog v-model="diffDialog" max-width="1200px" scrollable persistent retain-focus>
      <v-card v-draggable>
        <v-card-title class="d-flex align-center">
          <v-icon color="primary" class="mr-2">mdi-compare</v-icon>
          <span class="text-h5">Template Comparison</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" aria-label="Close" @click="diffDialog = false" />
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
                      <div class="pa-4 diff-html-container" v-html="sanitizedDiffHtml"></div>
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

    <!-- Error Snackbar (Red styled error notification) -->
    <v-snackbar
      v-model="errorSnackbar"
      color="error"
      location="top right"
      :timeout="6000"
      multi-line
    >
      <div class="d-flex align-center">
        <v-icon class="mr-3" size="large">mdi-alert-circle</v-icon>
        <div>
          <div class="font-weight-bold mb-1">Error</div>
          <div>{{ errorMessage }}</div>
        </div>
      </div>
      <template v-slot:actions>
        <v-btn variant="text" aria-label="Close error notification" @click="errorSnackbar = false">
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </v-card>
</template>

<script setup>
import { ref, computed, inject, onMounted, onUnmounted, watch } from 'vue'
import api from '@/services/api'
import TemplateArchive from './TemplateArchive.vue'
import { format } from 'date-fns'
import { useWebSocketV2 } from '@/composables/useWebSocket'
import { useUserStore } from '@/stores/user'
import { useToast } from '@/composables/useToast'
import DOMPurify from 'dompurify'

// Handover 0335: WebSocket setup for real-time export status updates
const { on, off } = useWebSocketV2()
const userStore = useUserStore()
const { showToast } = useToast()
const currentTenantKey = computed(() => userStore.currentUser?.tenant_key)

// Handover 0335: Inject template export event from parent (UserSettings.vue)
// This allows receiving export events even when this component is not mounted
// (v-window-item lazy loads components)
const templateExportEvent = inject('templateExportEvent', ref(null))

// Utility functions (inline to avoid external dependency)
function generatePersonalAgentsInstructions(downloadUrl) {
  return `Download from: ${downloadUrl}

Once downloaded:
1. Extract the ZIP file
2. For macOS/Linux: Extract to ~/.claude/agents/
3. For Windows: Extract to %USERPROFILE%\\.claude\\agents\\
4. Restart your AI coding tool

This download link expires in 15 minutes but can be used multiple times.`
}

function generateProductAgentsInstructions(downloadUrl) {
  return `Download from: ${downloadUrl}

Once downloaded:
1. Extract the ZIP file
2. Extract to .claude/agents/ in your current project root
3. Restart your AI coding tool

This download link expires in 15 minutes but can be used multiple times.`
}

async function copyToClipboardSafe(text, onSuccess, onError) {
  try {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      await navigator.clipboard.writeText(text)
      if (onSuccess) onSuccess()
    } else {
      // Fallback for older browsers
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      if (onSuccess) onSuccess()
    }
  } catch (error) {
    if (onError) onError(error)
  }
}

function downloadBlob(response, filename) {
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

// Reactive data
const templates = ref([])
const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const generating = ref(false)
const activeStats = ref({
  totalActive: null,
  totalCapacity: null,
  userActive: 0,
  userLimit: 7,
  remainingUserSlots: 7,
  systemReserved: 1,
}) // Tracks system reservation + user slots
const previewContent = ref('') // Handover 0103: Preview window content

// Error snackbar state
const errorSnackbar = ref(false)
const errorMessage = ref('')

// Export state

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
  role: '',
  cli_tool: 'claude', // NEW
  custom_suffix: '', // NEW
  background_color: '', // NEW
  description: '',
  template: '',
  model: 'sonnet', // NEW
  tools: null, // NEW
  variables: [],
  augmentation_slots: '',
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
  { title: 'Role', key: 'role', align: 'start' },
  { title: 'Tool', key: 'cli_tool', align: 'start' },
  { title: 'Variables', key: 'variables', align: 'center' },
  { title: 'Active', key: 'is_active', align: 'center' },
  { title: 'Export Status', key: 'export_status', align: 'center', sortable: false },
  { title: 'Updated', key: 'updated_at', align: 'start' },
  { title: 'Actions', key: 'actions', align: 'center', sortable: false },
]

// Categories
const categories = ['role', 'project_type', 'custom']

// Role options (for category = 'role')
const roleOptions = [
  'orchestrator',
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

// CLI tool options for create/edit modal (Handover 0103)
const cliToolOptions = [
  { title: 'Claude Code', value: 'claude', logo: '/claude_pix.svg' },
  { title: 'Codex CLI', value: 'codex', logo: '/icons/codex_mark.svg' },
  { title: 'Gemini CLI', value: 'gemini', logo: '/gemini-icon.svg' },
  { title: 'Generic', value: 'generic', logo: null },
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

// Computed properties for Handover 0103 modal
const generatedName = computed(() => {
  const role = editingTemplate.value.role
  const suffix = editingTemplate.value.custom_suffix
  if (!role) return ''
  if (!suffix) return role
  // Slugify: lowercase, hyphens only
  const cleanSuffix = suffix
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, '')
    .replace(/\s+/g, '-')
  return `${role}-${cleanSuffix}`
})

const showDescription = computed(() => {
  return editingTemplate.value.cli_tool === 'claude'
})

const modelOptions = computed(() => {
  if (editingTemplate.value.cli_tool === 'claude') {
    return ['sonnet', 'opus', 'haiku']
  }
  return [] // Read-only for non-Claude
})

const totalActiveAgents = computed(() => activeStats.value.totalActive)
const totalCapacity = computed(() => {
  if (activeStats.value.totalCapacity !== null) {
    return activeStats.value.totalCapacity
  }
  return (activeStats.value.userLimit || 7) + (activeStats.value.systemReserved || 1)
})
const remainingUserSlots = computed(() => {
  if (typeof activeStats.value.remainingUserSlots === 'number') {
    return Math.max(0, activeStats.value.remainingUserSlots)
  }
  return Math.max(0, (activeStats.value.userLimit || 7) - (activeStats.value.userActive || 0))
})
const systemReservedSlots = computed(() => activeStats.value.systemReserved ?? 1)
const userAgentLimit = computed(() => activeStats.value.userLimit ?? 7)

// Sanitized diff HTML for safe rendering
const sanitizedDiffHtml = computed(() => {
  return diffData.value?.diff_html ? DOMPurify.sanitize(diffData.value.diff_html) : ''
})

// Methods
const loadTemplates = async () => {
  loading.value = true
  try {
    // Load ALL templates (active and inactive) - no filter to get both
    const response = await api.templates.list()
    // Map backend fields to frontend fields
    templates.value = (response.data || [])
      .filter((t) => !t.is_system_role)
      .map((t) => ({
        ...t,
        template: t.system_instructions, // Map system_instructions to template for frontend
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
    const response = await api.templates.activeCount()
    const data = response.data || {}
    activeStats.value = {
      totalActive: data.total_active ?? (data.active_count || 0) + (data.system_reserved || 1),
      totalCapacity: data.total_capacity ?? (data.max_allowed || 7) + (data.system_reserved || 1),
      userActive: data.active_count ?? 0,
      userLimit: data.max_allowed ?? 7,
      remainingUserSlots:
        data.remaining_slots ?? Math.max(0, (data.max_allowed || 7) - (data.active_count || 0)),
      systemReserved: data.system_reserved ?? 1,
    }
  } catch (error) {
    console.error('[TEMPLATE MANAGER] Failed to load active count:', error)
    activeStats.value = {
      ...activeStats.value,
      totalActive: activeStats.value.totalActive ?? activeStats.value.systemReserved,
    }
  }
}

// Handover 0075: Handle active toggle with validation
const handleToggleActive = async (template, newValue) => {
  try {
    // Attempt to update
    await api.templates.update(template.id, {
      is_active: newValue,
    })

    // Update local template state
    template.is_active = newValue

    // Reload active count
    await loadActiveCount()

    // Show toast notification
    if (newValue) {
      // Activation succeeded - warn about re-export
      showToast({ message: 'Agent activated - re-export required', color: 'warning' })
      // Mark export as stale (for Option C badge)
      localStorage.setItem('agent_export_stale', 'true')
    } else {
      // Deactivation succeeded
      showToast({ message: 'Agent deactivated', color: 'info' })
      localStorage.setItem('agent_export_stale', 'true')
    }
  } catch (error) {
    // Validation failed (8-agent limit)
    const errorMsg = error.response?.data?.detail || 'Failed to update agent'
    showToast({ message: errorMsg, color: 'error' })

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
    role: '',
    cli_tool: 'claude',
    custom_suffix: '',
    background_color: '',
    description: '',
    template: '',
    model: 'sonnet',
    tools: null,
    variables: [],
    augmentation_slots: '',
  }
  previewContent.value = ''
  editDialog.value = true
}

const editTemplate = (template) => {
  editingTemplate.value = {
    ...template,
    template: template.system_instructions || template.template, // Ensure template field is set
    cli_tool: template.cli_tool || 'claude',
    custom_suffix: '',
    background_color: template.background_color || '',
    model: template.model || 'sonnet',
    tools: template.tools || null,
  }
  previewContent.value = ''
  editDialog.value = true
}

const duplicateTemplate = (template) => {
  editingTemplate.value = {
    ...template,
    id: null,
    name: `${template.name} (Copy)`,
    template: template.system_instructions || template.template, // Ensure template field is set
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
  editingTemplate.value = {
    id: null,
    name: '',
    role: '',
    cli_tool: 'claude',
    custom_suffix: '',
    background_color: '',
    description: '',
    template: '',
    model: 'sonnet',
    tools: null,
    variables: [],
    augmentation_slots: '',
  }
}

// Handover 0103: Handle role change (auto-set background_color)
const onRoleChange = (newRole) => {
  editingTemplate.value.background_color = getCategoryColor(newRole)
}

// Handover 0103: Handle CLI tool change (clear preview)
const onCliToolChange = () => {
  previewContent.value = ''
  // Set default model for Claude
  if (editingTemplate.value.cli_tool === 'claude') {
    editingTemplate.value.model = 'sonnet'
  }
}

// Handover 0103: Save template and generate preview
const saveTemplateAndPreview = async () => {
  saving.value = true
  try {
    const data = {
      name: generatedName.value || editingTemplate.value.role,
      category: 'role', // Automatically set to 'role' for all templates
      role: editingTemplate.value.role || null,
      cli_tool: editingTemplate.value.cli_tool,
      custom_suffix: editingTemplate.value.custom_suffix || null,
      background_color: editingTemplate.value.background_color,
      description: editingTemplate.value.description,
      system_instructions: editingTemplate.value.template,
      model: editingTemplate.value.cli_tool === 'claude' ? editingTemplate.value.model : null,
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
        system_instructions: data.system_instructions,
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

    // Generate preview
    const previewResponse = await api.templates.preview(templateId, {})
    previewContent.value = previewResponse.data.preview

    await loadTemplates()
    // Don't close dialog - show preview instead
  } catch (error) {
    console.error('Failed to save template:', error)
    previewContent.value = ''
    // Show error notification to user
    errorMessage.value = error.response?.data?.detail || 'Failed to save template'
    errorSnackbar.value = true
  } finally {
    saving.value = false
  }
}

// Handover 0103: Copy preview to clipboard
const copyPreview = async () => {
  await copyToClipboardSafe(
    previewContent.value,
    () => {
      showToast({ message: 'Preview copied to clipboard', color: 'success' })
    },
    (error) => {
      // Error - show error toast
      console.error('Failed to copy preview:', error)
      errorMessage.value = 'Failed to copy to clipboard'
      errorSnackbar.value = true
    },
  )
}

const saveTemplate = async () => {
  saving.value = true
  try {
    const data = {
      name: editingTemplate.value.name,
      category: 'role', // Automatically set to 'role' for all templates
      role: editingTemplate.value.role || null,
      description: editingTemplate.value.description,
      system_instructions: editingTemplate.value.template,
      cli_tool: editingTemplate.value.cli_tool,
      behavioral_rules: editingTemplate.value.behavioral_rules || [],
      success_criteria: editingTemplate.value.success_criteria || [],
      tags: editingTemplate.value.tags || [],
      is_default: editingTemplate.value.is_default || false,
    }

    if (editingTemplate.value.id) {
      await api.templates.update(editingTemplate.value.id, {
        name: data.name,
        system_instructions: data.system_instructions,
        description: data.description,
        cli_tool: data.cli_tool,
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

const getCategoryColor = (role) => {
  // Colors synced with frontend/src/styles/agent-colors.scss
  const colors = {
    orchestrator: '#D4A574', // Tan/Beige
    analyzer: '#E74C3C', // Red
    researcher: '#E74C3C', // Red (alias → analyzer)
    implementer: '#3498DB', // Blue
    implementor: '#3498DB', // Blue (alias)
    tester: '#FFC300', // Yellow
    reviewer: '#9B59B6', // Purple
    documenter: '#27AE60', // Green
    custom: '#90A4AE', // Gray
  }
  return colors[role] || '#90A4AE'
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
    await api.templates.reset(resettingTemplate.value.id)
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

// Handover 0335: Handle template export WebSocket event (Enhanced with debugging)
const handleTemplateExported = (data) => {
  // Normalize payload - WebSocket store flattens nested data structure
  // Backend sends: { type, data: { tenant_key, template_ids, ... }, timestamp }
  // Store normalizes to: { type, tenant_key, template_ids, ..., timestamp }
  const tenantKey = data.tenant_key
  const templateIds = data.template_ids
  const exportedAt = data.exported_at
  const exportType = data.export_type

  // Validate required fields
  if (!tenantKey || !templateIds || !exportedAt) {
    return
  }

  // Multi-tenant isolation check
  if (tenantKey !== currentTenantKey.value) {
    return
  }

  // Update local template state with new export timestamp
  const templateIdSet = new Set(templateIds)
  let updateCount = 0

  templates.value.forEach((template) => {
    if (templateIdSet.has(template.id)) {
      template.last_exported_at = exportedAt
      template.may_be_stale = false // Clear staleness indicator
      updateCount++
    }
  })

}


// Lifecycle
onMounted(() => {
  loadTemplates()
  loadActiveCount() // Handover 0075: Load active agent count

  // Handover 0335: Subscribe to template export WebSocket events
  // Pattern matches JobsTab and LaunchTab (working components)
  on('template:exported', handleTemplateExported)
})

onUnmounted(() => {
  // Handover 0335: Cleanup WebSocket subscription
  off('template:exported', handleTemplateExported)
})

// Watch for variable changes
watch(
  () => editingTemplate.value.template,
  () => {
    editingTemplate.value.variables = detectedVariables.value
  },
)

// Handover 0335: Watch for export events from parent (UserSettings.vue)
// This handles the case where export happens on a different tab and this component
// was not mounted at the time of the WebSocket event
watch(
  templateExportEvent,
  (newEvent) => {
    if (!newEvent) return

    // Validate tenant_key matches current user
    if (newEvent.tenant_key !== currentTenantKey.value) {
      return
    }

    // Process the event just like the direct WebSocket handler
    handleTemplateExported(newEvent)
  },
  { deep: true }
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

  // Handover 0103: Preview content styling
  .preview-container {
    background: var(--v-theme-background);
    border-radius: 4px;

    .preview-content {
      background: var(--v-theme-surface);
      color: var(--v-theme-on-surface);
      font-family: 'Roboto Mono', monospace;
      font-size: 13px;
      line-height: 1.6;
      padding: 16px;
      border-radius: 4px;
      overflow-x: auto;
      max-height: 400px;
      overflow-y: auto;
      white-space: pre;
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

// Custom toggle colors: green when ON, faded blue when OFF
.v-switch {
  :deep(.v-switch__thumb) {
    background-color: rgba(33, 150, 243, 0.4) !important; // Faded blue when OFF
  }

  :deep(.v-switch__track) {
    background-color: rgba(33, 150, 243, 0.2) !important; // Faded blue track when OFF
  }
}

.v-switch :deep(.v-selection-control--dirty) {
  .v-switch__thumb {
    background-color: #4caf50 !important; // Green when ON
  }

  .v-switch__track {
    background-color: rgba(76, 175, 80, 0.3) !important; // Green track when ON
  }
}

// Inactive template row styling
:deep(.inactive-template) {
  opacity: 0.5;

  td {
    color: var(--v-theme-on-surface) !important;
  }
}

// Codex icon theme-aware coloring
.codex-icon {
  :deep(img) {
    filter: brightness(0) invert(1); // White in dark mode
  }
}
</style>
