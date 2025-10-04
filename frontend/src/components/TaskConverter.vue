<template>
  <v-dialog :model-value="show" max-width="900" persistent @update:model-value="$emit('close')" @click:outside="false">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2" color="primary">mdi-arrow-right-bold-circle</v-icon>
        Convert Tasks to Project{{ selectedTasks.length > 1 ? 's' : '' }}
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" size="small" @click="$emit('close')" />
      </v-card-title>
      <v-divider />
      <!-- Wizard Steps -->
      <v-stepper v-model="currentStep" :items="stepperItems" class="elevation-0">
        <!-- Step 1: Review Tasks -->
        <template v-slot:item.1>
          <div class="pa-6">
            <h3 class="text-h6 mb-3">Review Selected Tasks</h3>
            <p class="text-body-2 text-medium-emphasis mb-4">
              Review the {{ tasksToConvert.length }} task{{ tasksToConvert.length > 1 ? 's' : '' }}
              selected for conversion. You can modify the selection or proceed to configure project
              details.
            </p>
            <!-- Task Selection Summary -->
            <v-row class="mb-4">
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="text-center pa-4">
                  <v-icon color="primary" size="large" class="mb-2">mdi-clipboard-list</v-icon>
                  <div class="text-h6">{{ tasksToConvert.length }}</div>
                  <div class="text-caption">Total Tasks</div>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="text-center pa-4">
                  <v-icon color="success" size="large" class="mb-2">mdi-tag-multiple</v-icon>
                  <div class="text-h6">{{ uniqueCategories.length }}</div>
                  <div class="text-caption">Categories</div>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="text-center pa-4">
                  <v-icon color="warning" size="large" class="mb-2">mdi-priority-high</v-icon>
                  <div class="text-h6">{{ highPriorityCount }}</div>
                  <div class="text-caption">High Priority</div>
                </v-card>
              </v-col>
            </v-row>
            <!-- Selected Tasks List -->
            <v-card variant="outlined">
              <v-card-title class="text-subtitle-1 py-3">
                <v-icon class="mr-2">mdi-format-list-checks</v-icon>
                Selected Tasks
              </v-card-title>
              <v-divider />
              <v-list density="compact" class="py-0">
                <v-list-item
                  v-for="(task, index) in tasksToConvert"
                  :key="task.id"
                  class="px-4"
                  :class="{ 'border-b': index < tasksToConvert.length - 1 }"
                >
                  <template v-slot:prepend>
                    <v-chip :color="getPriorityColor(task.priority)" size="x-small" class="mr-3">
                      {{ task.priority }}
                    </v-chip>
                  </template>

                  <v-list-item-title class="font-weight-medium">{{ task.title }}</v-list-item-title>
                  <v-list-item-subtitle v-if="task.description">{{
                    task.description
                  }}</v-list-item-subtitle>

                  <template v-slot:append>
                    <v-chip size="x-small" variant="outlined" class="mr-2">
                      {{ task.category }}
                    </v-chip>
                    <v-btn
                      icon="mdi-close"
                      size="x-small"
                      variant="text"
                      @click="removeTaskFromSelection(task.id)"
                      aria-label="Remove from selection"
                    />
                  </template>
                </v-list-item>
              </v-list>
            </v-card>
            <!-- Conversion Strategy Selection -->
            <v-row class="mt-6">
              <v-col>
                <h4 class="text-subtitle-1 mb-3">Conversion Strategy</h4>
                <v-btn-toggle
                  v-model="conversionStrategy"
                  color="primary"
                  variant="outlined"
                  mandatory
                  class="mb-4"
                >
                  <v-btn value="single" :disabled="tasksToConvert.length === 1">
                    <v-icon class="mr-2">mdi-file-document</v-icon>
                    Single Project
                  </v-btn>
                  <v-btn value="individual" :disabled="tasksToConvert.length === 1">
                    <v-icon class="mr-2">mdi-file-document-multiple</v-icon>
                    Individual Projects
                  </v-btn>
                  <v-btn value="grouped">
                    <v-icon class="mr-2">mdi-folder</v-icon>
                    Group by Category
                  </v-btn>
                </v-btn-toggle>
              </v-col>
            </v-row>
          </div>
        </template>
        <!-- Step 2: Project Details -->
        <template v-slot:item.2>
          <div class="pa-6">
            <h3 class="text-h6 mb-3">Project Configuration</h3>
            <p class="text-body-2 text-medium-emphasis mb-4">
              Configure the project details based on your conversion strategy. The form will
              auto-populate with intelligent suggestions based on your selected tasks.
            </p>
            <!-- Single Project Configuration -->
            <div v-if="conversionStrategy === 'single'">
              <v-text-field
                v-model="projectConfig.name"
                label="Project Name"
                variant="outlined"
                :rules="[(v) => !!v || 'Project name is required']"
                prepend-inner-icon="mdi-folder"
                hint="Auto-generated from task analysis"
                persistent-hint
                class="mb-4"
              />

              <v-textarea
                v-model="projectConfig.mission"
                label="Project Mission"
                variant="outlined"
                rows="4"
                :rules="[(v) => !!v || 'Project mission is required']"
                prepend-inner-icon="mdi-target"
                hint="Describe the overall goal and scope of this project"
                persistent-hint
                class="mb-4"
              />
              <v-row>
                <v-col cols="6">
                  <v-select
                    v-model="projectConfig.priority"
                    :items="priorityOptions"
                    label="Project Priority"
                    variant="outlined"
                    prepend-inner-icon="mdi-priority-high"
                    hint="Based on highest task priority"
                    persistent-hint
                  />
                </v-col>
                <v-col cols="6">
                  <v-select
                    v-model="projectConfig.category"
                    :items="categoryOptions"
                    label="Primary Category"
                    variant="outlined"
                    prepend-inner-icon="mdi-tag"
                    hint="Based on task categories"
                    persistent-hint
                  />
                </v-col>
              </v-row>
            </div>
            <!-- Multiple Projects Preview -->
            <div v-else>
              <v-alert type="info" variant="outlined" class="mb-4">
                <template v-slot:title> Multiple Projects Configuration </template>
                <div v-if="conversionStrategy === 'individual'">
                  {{ tasksToConvert.length }} individual projects will be created, one for each
                  task.
                </div>
                <div v-else-if="conversionStrategy === 'grouped'">
                  {{ Object.keys(taskGroups).length }} projects will be created, grouped by
                  category.
                </div>
              </v-alert>
              <!-- Project Preview Cards -->
              <v-row>
                <v-col v-for="(preview, index) in projectPreviews" :key="index" cols="12" md="6">
                  <v-card variant="outlined" class="mb-3">
                    <v-card-title class="text-subtitle-1 py-3">
                      <v-icon class="mr-2">mdi-folder</v-icon>
                      {{ preview.name }}
                    </v-card-title>
                    <v-card-text class="pt-0">
                      <div class="text-body-2 mb-2">{{ preview.mission }}</div>
                      <v-chip-group>
                        <v-chip
                          v-for="task in preview.tasks"
                          :key="task.id"
                          size="x-small"
                          variant="outlined"
                        >
                          {{ task.title }}
                        </v-chip>
                      </v-chip-group>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
            </div>
          </div>
        </template>
        <!-- Step 3: Dependencies -->
        <template v-slot:item.3>
          <div class="pa-6">
            <h3 class="text-h6 mb-3">Task Dependencies & Relationships</h3>
            <p class="text-body-2 text-medium-emphasis mb-4">
              Define relationships between tasks and how they should be handled during conversion.
            </p>
            <!-- Enhanced Dependency Analysis -->
            <v-card variant="outlined" class="mb-4">
              <v-card-title class="text-subtitle-1 py-3 d-flex align-center">
                <v-icon class="mr-2">mdi-source-branch</v-icon>
                Dependency Analysis
                <v-spacer />
                <v-btn-toggle
                  v-model="dependencyViewMode"
                  size="small"
                  density="compact"
                  variant="outlined"
                >
                  <v-btn value="list" icon="mdi-format-list-bulleted" />
                  <v-btn value="graph" icon="mdi-graph" />
                </v-btn-toggle>
              </v-card-title>
              <v-card-text>
                <!-- List View -->
                <div v-if="dependencyViewMode === 'list'">
                  <div v-if="taskDependencies.length === 0" class="text-center py-4">
                    <v-icon color="success" size="large" class="mb-2">mdi-check-circle</v-icon>
                    <div class="text-subtitle-2">No Dependencies Detected</div>
                    <div class="text-body-2 text-medium-emphasis">
                      All selected tasks appear to be independent
                    </div>
                  </div>
                  <div v-else>
                    <v-expansion-panels variant="accordion" class="mb-4">
                      <v-expansion-panel>
                        <v-expansion-panel-title>
                          <v-icon class="mr-2" color="error">mdi-link-variant</v-icon>
                          Strong Dependencies ({{ strongDependencies.length }})
                        </v-expansion-panel-title>
                        <v-expansion-panel-text>
                          <v-list density="compact">
                            <v-list-item
                              v-for="dep in strongDependencies"
                              :key="`${dep.from}-${dep.to}`"
                            >
                              <template v-slot:prepend>
                                <v-icon color="error" size="small">mdi-arrow-right-thick</v-icon>
                              </template>
                              <v-list-item-title>
                                {{ getTaskTitle(dep.from) }} → {{ getTaskTitle(dep.to) }}
                              </v-list-item-title>
                              <v-list-item-subtitle>{{ dep.type }} dependency</v-list-item-subtitle>
                            </v-list-item>
                          </v-list>
                        </v-expansion-panel-text>
                      </v-expansion-panel>

                      <v-expansion-panel v-if="mediumDependencies.length > 0">
                        <v-expansion-panel-title>
                          <v-icon class="mr-2" color="warning">mdi-link</v-icon>
                          Medium Dependencies ({{ mediumDependencies.length }})
                        </v-expansion-panel-title>
                        <v-expansion-panel-text>
                          <v-list density="compact">
                            <v-list-item
                              v-for="dep in mediumDependencies"
                              :key="`${dep.from}-${dep.to}`"
                            >
                              <template v-slot:prepend>
                                <v-icon color="warning" size="small">mdi-arrow-right</v-icon>
                              </template>
                              <v-list-item-title>
                                {{ getTaskTitle(dep.from) }} → {{ getTaskTitle(dep.to) }}
                              </v-list-item-title>
                              <v-list-item-subtitle>{{ dep.type }} dependency</v-list-item-subtitle>
                            </v-list-item>
                          </v-list>
                        </v-expansion-panel-text>
                      </v-expansion-panel>

                      <v-expansion-panel v-if="weakDependencies.length > 0">
                        <v-expansion-panel-title>
                          <v-icon class="mr-2" color="info">mdi-link-variant-off</v-icon>
                          Weak Dependencies ({{ weakDependencies.length }})
                        </v-expansion-panel-title>
                        <v-expansion-panel-text>
                          <v-list density="compact">
                            <v-list-item
                              v-for="dep in weakDependencies"
                              :key="`${dep.from}-${dep.to}`"
                            >
                              <template v-slot:prepend>
                                <v-icon color="info" size="small">mdi-arrow-right</v-icon>
                              </template>
                              <v-list-item-title>
                                {{ getTaskTitle(dep.from) }} → {{ getTaskTitle(dep.to) }}
                              </v-list-item-title>
                              <v-list-item-subtitle>{{ dep.type }} dependency</v-list-item-subtitle>
                            </v-list-item>
                          </v-list>
                        </v-expansion-panel-text>
                      </v-expansion-panel>
                    </v-expansion-panels>
                  </div>
                </div>
                <!-- Graph View -->
                <div v-else-if="dependencyViewMode === 'graph'" class="dependency-graph-container">
                  <div v-if="taskDependencies.length === 0" class="text-center py-8">
                    <v-icon color="success" size="x-large" class="mb-4">mdi-check-circle</v-icon>
                    <div class="text-h6">Independent Tasks</div>
                    <div class="text-body-2 text-medium-emphasis">
                      No dependencies detected between selected tasks
                    </div>
                  </div>
                  <div v-else class="dependency-graph" ref="dependencyGraph">
                    <!-- Interactive Dependency Graph -->
                    <svg
                      :width="graphDimensions.width"
                      :height="graphDimensions.height"
                      class="dependency-svg"
                    >
                      <!-- Task Nodes -->
                      <g v-for="(task, index) in tasksToConvert" :key="task.id">
                        <circle
                          :cx="getTaskPosition(task.id).x"
                          :cy="getTaskPosition(task.id).y"
                          :r="getTaskRadius(task)"
                          :fill="getPriorityColor(task.priority)"
                          :stroke="selectedDependencyTask === task.id ? '#1976d2' : '#666'"
                          :stroke-width="selectedDependencyTask === task.id ? 3 : 1"
                          class="task-node"
                          @click="selectDependencyTask(task.id)"
                        />
                        <text
                          :x="getTaskPosition(task.id).x"
                          :y="getTaskPosition(task.id).y + 5"
                          text-anchor="middle"
                          class="task-label"
                          font-size="12"
                          fill="white"
                        >
                          {{
                            task.title.length > 10
                              ? task.title.substring(0, 10) + '...'
                              : task.title
                          }}
                        </text>
                      </g>
                      <!-- Dependency Lines -->
                      <g v-for="dep in taskDependencies" :key="`${dep.from}-${dep.to}`">
                        <line
                          :x1="getTaskPosition(dep.from).x"
                          :y1="getTaskPosition(dep.from).y"
                          :x2="getTaskPosition(dep.to).x"
                          :y2="getTaskPosition(dep.to).y"
                          :stroke="getDependencyColor(dep.strength)"
                          :stroke-width="getDependencyWidth(dep.strength)"
                          :stroke-dasharray="dep.strength === 'weak' ? '5,5' : 'none'"
                          marker-end="url(#arrowhead)"
                        />
                      </g>
                      <!-- Arrow marker definition -->
                      <defs>
                        <marker
                          id="arrowhead"
                          markerWidth="10"
                          markerHeight="7"
                          refX="9"
                          refY="3.5"
                          orient="auto"
                        >
                          <polygon points="0 0, 10 3.5, 0 7" fill="#666" />
                        </marker>
                      </defs>
                    </svg>
                    <!-- Graph Legend -->
                    <div class="graph-legend mt-4">
                      <v-row>
                        <v-col cols="4">
                          <div class="d-flex align-center mb-2">
                            <div class="legend-line strong mr-2"></div>
                            <span class="text-caption">Strong Dependencies</span>
                          </div>
                          <div class="d-flex align-center mb-2">
                            <div class="legend-line medium mr-2"></div>
                            <span class="text-caption">Medium Dependencies</span>
                          </div>
                          <div class="d-flex align-center">
                            <div class="legend-line weak mr-2"></div>
                            <span class="text-caption">Weak Dependencies</span>
                          </div>
                        </v-col>
                        <v-col cols="8">
                          <div class="text-caption text-medium-emphasis">
                            Click on tasks to highlight their dependencies. Node size indicates task
                            complexity.
                          </div>
                        </v-col>
                      </v-row>
                    </div>
                  </div>
                </div>
              </v-card-text>
            </v-card>
            <!-- Relationship Handling Options -->
            <v-card variant="outlined">
              <v-card-title class="text-subtitle-1 py-3">
                <v-icon class="mr-2">mdi-cog</v-icon>
                Relationship Handling
              </v-card-title>
              <v-card-text>
                <v-radio-group v-model="dependencyHandling" density="compact">
                  <v-radio
                    value="preserve"
                    label="Preserve task relationships in project structure"
                  />
                  <v-radio value="merge" label="Merge dependent tasks into single project" />
                  <v-radio value="ignore" label="Ignore dependencies and proceed independently" />
                </v-radio-group>
              </v-card-text>
            </v-card>
          </div>
        </template>
        <!-- Step 4: Confirm -->
        <template v-slot:item.4>
          <div class="pa-6">
            <h3 class="text-h6 mb-3">Conversion Summary</h3>
            <p class="text-body-2 text-medium-emphasis mb-4">
              Review the final conversion plan before proceeding. All projects will be created with
              the specified configuration.
            </p>
            <!-- Summary Stats -->
            <v-row class="mb-4">
              <v-col cols="12" md="3">
                <v-card variant="outlined" class="text-center pa-4">
                  <v-icon color="primary" size="large" class="mb-2">mdi-folder-multiple</v-icon>
                  <div class="text-h6">{{ finalConversionPreview.length }}</div>
                  <div class="text-caption">Projects to Create</div>
                </v-card>
              </v-col>
              <v-col cols="12" md="3">
                <v-card variant="outlined" class="text-center pa-4">
                  <v-icon color="info" size="large" class="mb-2">mdi-clipboard-list</v-icon>
                  <div class="text-h6">{{ tasksToConvert.length }}</div>
                  <div class="text-caption">Tasks to Convert</div>
                </v-card>
              </v-col>
              <v-col cols="12" md="3">
                <v-card variant="outlined" class="text-center pa-4">
                  <v-icon color="success" size="large" class="mb-2">mdi-link</v-icon>
                  <div class="text-h6">{{ options.preserveTaskLinks ? 'Yes' : 'No' }}</div>
                  <div class="text-caption">Task Links</div>
                </v-card>
              </v-col>
              <v-col cols="12" md="3">
                <v-card variant="outlined" class="text-center pa-4">
                  <v-icon color="warning" size="large" class="mb-2">mdi-source-branch</v-icon>
                  <div class="text-h6">{{ taskDependencies.length }}</div>
                  <div class="text-caption">Dependencies</div>
                </v-card>
              </v-col>
            </v-row>
            <!-- Conversion Preview -->
            <v-expansion-panels variant="accordion" multiple>
              <v-expansion-panel
                v-for="(project, index) in finalConversionPreview"
                :key="index"
                :value="index"
              >
                <v-expansion-panel-title>
                  <div class="d-flex align-center w-100">
                    <v-icon class="mr-3" color="primary">mdi-folder</v-icon>
                    <div class="flex-grow-1">
                      <div class="text-subtitle-1">{{ project.name }}</div>
                      <div class="text-caption text-medium-emphasis">
                        {{ project.tasks.length }} task{{ project.tasks.length > 1 ? 's' : '' }}
                      </div>
                    </div>
                    <v-chip size="small" :color="getPriorityColor(project.priority)" class="mr-2">
                      {{ project.priority }}
                    </v-chip>
                  </div>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <div class="mb-3">
                    <strong>Mission:</strong>
                    <div class="mt-1 text-body-2">{{ project.mission }}</div>
                  </div>
                  <div class="mb-3"><strong>Category:</strong> {{ project.category }}</div>
                  <div>
                    <strong>Tasks to convert:</strong>
                    <div class="mt-2">
                      <v-chip
                        v-for="task in project.tasks"
                        :key="task.id"
                        size="small"
                        class="ma-1"
                        variant="outlined"
                        :color="getPriorityColor(task.priority)"
                      >
                        {{ task.title }}
                      </v-chip>
                    </div>
                  </div>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
            <!-- Conversion Options Summary -->
            <v-card variant="outlined" class="mt-4">
              <v-card-title class="text-subtitle-1 py-3">
                <v-icon class="mr-2">mdi-cog</v-icon>
                Conversion Options
              </v-card-title>
              <v-card-text>
                <v-row>
                  <v-col cols="6">
                    <div class="d-flex align-center mb-2">
                      <v-icon :color="options.preserveTaskLinks ? 'success' : 'grey'" class="mr-2">
                        {{ options.preserveTaskLinks ? 'mdi-check' : 'mdi-close' }}
                      </v-icon>
                      <span>Preserve task links</span>
                    </div>
                    <div class="d-flex align-center mb-2">
                      <v-icon :color="options.markTasksConverted ? 'success' : 'grey'" class="mr-2">
                        {{ options.markTasksConverted ? 'mdi-check' : 'mdi-close' }}
                      </v-icon>
                      <span>Mark tasks as converted</span>
                    </div>
                  </v-col>
                  <v-col cols="6">
                    <div class="d-flex align-center mb-2">
                      <v-icon
                        :color="options.assignToCurrentAgent ? 'success' : 'grey'"
                        class="mr-2"
                      >
                        {{ options.assignToCurrentAgent ? 'mdi-check' : 'mdi-close' }}
                      </v-icon>
                      <span>Assign to current agent</span>
                    </div>
                    <div class="d-flex align-center mb-2">
                      <v-icon
                        :color="options.inheritTaskPriority ? 'success' : 'grey'"
                        class="mr-2"
                      >
                        {{ options.inheritTaskPriority ? 'mdi-check' : 'mdi-close' }}
                      </v-icon>
                      <span>Inherit task priority</span>
                    </div>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </div>
        </template>
      </v-stepper>
      <!-- Wizard Navigation -->
      <v-divider />
      <v-card-actions class="pa-4">
        <v-btn v-if="currentStep > 1" variant="outlined" @click="previousStep">
          <v-icon class="mr-2">mdi-chevron-left</v-icon>
          Previous
        </v-btn>
        <v-spacer />
        <v-btn variant="text" @click="$emit('close')"> Cancel </v-btn>
        <v-btn
          v-if="currentStep < 4"
          color="primary"
          variant="flat"
          :disabled="!canProceedToNextStep"
          @click="nextStep"
        >
          Next
          <v-icon class="ml-2">mdi-chevron-right</v-icon>
        </v-btn>
        <v-btn
          v-else
          color="primary"
          variant="flat"
          :loading="converting"
          :disabled="!canConvert"
          @click="performConversion"
        >
          <v-icon class="mr-2">mdi-arrow-right-bold-circle</v-icon>
          Convert {{ finalConversionPreview.length }} Project{{
            finalConversionPreview.length > 1 ? 's' : ''
          }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
<style scoped>
.dependency-graph-container {
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
}
.dependency-svg {
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background: white;
}
.task-node {
  cursor: pointer;
  transition: all 0.2s ease;
}
.task-node:hover {
  stroke-width: 2 !important;
  filter: brightness(1.1);
}
.task-label {
  pointer-events: none;
  font-weight: 500;
}
.graph-legend {
  border-top: 1px solid #e0e0e0;
  padding-top: 16px;
}
.legend-line {
  width: 20px;
  height: 3px;
  border-radius: 2px;
}
.legend-line.strong {
  background-color: #f44336;
}
.legend-line.medium {
  background-color: #ff9800;
}
.legend-line.weak {
  background-color: #2196f3;
  background-image: repeating-linear-gradient(
    to right,
    #2196f3,
    #2196f3 5px,
    transparent 5px,
    transparent 10px
  );
}
</style>
<script setup>
import { ref, computed, watch } from 'vue'
import { useTaskStore } from '@/stores/tasks'
import { useProjectStore } from '@/stores/projects'
import { useProductStore } from '@/stores/products'
// Props
const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
  selectedTaskIds: {
    type: Array,
    default: () => [],
  },
})
// Emits
const emit = defineEmits(['close', 'converted'])
// Stores
const taskStore = useTaskStore()
const projectStore = useProjectStore()
const productStore = useProductStore()
// State
const currentStep = ref(1)
const conversionStrategy = ref('single')
const converting = ref(false)
const dependencyHandling = ref('preserve')
const dependencyViewMode = ref('list')
const selectedDependencyTask = ref(null)
// Graph dimensions for dependency visualization
const graphDimensions = ref({
  width: 600,
  height: 400,
})
const projectConfig = ref({
  name: '',
  mission: '',
  priority: 'medium',
  category: 'general',
})
// Wizard step configuration
const stepperItems = ref([
  { title: 'Review Tasks', value: 1 },
  { title: 'Project Details', value: 2 },
  { title: 'Dependencies', value: 3 },
  { title: 'Confirm', value: 4 },
])
const options = ref({
  preserveTaskLinks: true,
  markTasksConverted: true,
  assignToCurrentAgent: false,
  inheritTaskPriority: true,
})
// Computed
const tasksToConvert = computed(() => {
  return taskStore.tasks.filter((task) => props.selectedTaskIds.includes(task.id))
})
// Wizard-specific computed properties
const uniqueCategories = computed(() => {
  return [...new Set(tasksToConvert.value.map((t) => t.category))]
})
const highPriorityCount = computed(() => {
  return tasksToConvert.value.filter((t) => ['high', 'critical'].includes(t.priority)).length
})
const taskDependencies = computed(() => {
  // Enhanced dependency detection based on task relationships
  const dependencies = []

  tasksToConvert.value.forEach((task) => {
    // Check for parent_task_id relationships
    if (task.parent_task_id) {
      const parentTask = tasksToConvert.value.find((t) => t.id === task.parent_task_id)
      if (parentTask) {
        dependencies.push({
          from: task.parent_task_id,
          to: task.id,
          type: 'parent-child',
          strength: 'strong',
        })
      }
    }

    // Check for keyword-based dependencies in descriptions
    if (task.description) {
      const keywords = task.description.toLowerCase()
      tasksToConvert.value.forEach((otherTask) => {
        if (otherTask.id !== task.id && otherTask.title) {
          const titleWords = otherTask.title.toLowerCase().split(' ')
          if (titleWords.some((word) => word.length > 3 && keywords.includes(word))) {
            dependencies.push({
              from: otherTask.id,
              to: task.id,
              type: 'content-reference',
              strength: 'weak',
            })
          }
        }
      })
    }

    // Check for category-based relationships
    tasksToConvert.value.forEach((otherTask) => {
      if (
        otherTask.id !== task.id &&
        otherTask.category === task.category &&
        otherTask.priority === 'high' &&
        task.priority !== 'high'
      ) {
        dependencies.push({
          from: otherTask.id,
          to: task.id,
          type: 'category-priority',
          strength: 'medium',
        })
      }
    })
  })

  // Remove duplicates
  return dependencies.filter(
    (dep, index, self) => index === self.findIndex((d) => d.from === dep.from && d.to === dep.to),
  )
})
const taskGroups = computed(() => {
  const groups = {}
  tasksToConvert.value.forEach((task) => {
    const category = task.category || 'general'
    if (!groups[category]) {
      groups[category] = []
    }
    groups[category].push(task)
  })
  return groups
})
const projectPreviews = computed(() => {
  switch (conversionStrategy.value) {
    case 'individual':
      return tasksToConvert.value.map((task) => ({
        name: `Project: ${task.title}`,
        mission: `Individual project for: ${task.description || task.title}`,
        tasks: [task],
        priority: task.priority,
        category: task.category,
      }))

    case 'grouped':
      return Object.entries(taskGroups.value).map(([category, tasks]) => ({
        name: `${category.charAt(0).toUpperCase() + category.slice(1)} Tasks Project`,
        mission: `Project for ${category} related tasks`,
        tasks,
        priority: tasks.reduce((highest, task) => {
          const priorities = ['low', 'medium', 'high', 'critical']
          return priorities.indexOf(task.priority) > priorities.indexOf(highest)
            ? task.priority
            : highest
        }, 'low'),
        category,
      }))

    default:
      return []
  }
})
const finalConversionPreview = computed(() => {
  if (conversionStrategy.value === 'single') {
    return [
      {
        name: projectConfig.value.name || 'Converted Tasks Project',
        mission: projectConfig.value.mission || 'Project created from converted tasks',
        tasks: tasksToConvert.value,
        priority: projectConfig.value.priority,
        category: projectConfig.value.category,
      },
    ]
  }
  return projectPreviews.value
})
const canProceedToNextStep = computed(() => {
  switch (currentStep.value) {
    case 1:
      return tasksToConvert.value.length > 0
    case 2:
      if (conversionStrategy.value === 'single') {
        return projectConfig.value.name && projectConfig.value.mission
      }
      return true
    case 3:
      return true
    default:
      return true
  }
})
// Dependency categorization
const strongDependencies = computed(() =>
  taskDependencies.value.filter((dep) => dep.strength === 'strong'),
)
const mediumDependencies = computed(() =>
  taskDependencies.value.filter((dep) => dep.strength === 'medium'),
)
const weakDependencies = computed(() =>
  taskDependencies.value.filter((dep) => dep.strength === 'weak'),
)
const canConvert = computed(() => {
  return finalConversionPreview.value.length > 0 && canProceedToNextStep.value
})
// Options
const priorityOptions = ['low', 'medium', 'high', 'critical']
const categoryOptions = ['general', 'feature', 'bug', 'improvement', 'documentation', 'testing']
const conversionPreview = computed(() => {
  if (!tasksToConvert.value.length) return []
  switch (conversionStrategy.value) {
    case 'single':
      return [
        {
          name: projectConfig.value.name || 'Converted Tasks Project',
          mission: projectConfig.value.mission || 'Project created from converted tasks',
          tasks: tasksToConvert.value,
          taskCount: tasksToConvert.value.length,
        },
      ]

    case 'individual':
      return tasksToConvert.value.map((task) => ({
        name: `Project: ${task.title}`,
        mission: `Individual project for: ${task.description || task.title}`,
        tasks: [task],
        taskCount: 1,
      }))

    case 'grouped':
      const groups = {}
      tasksToConvert.value.forEach((task) => {
        const category = task.category || 'general'
        if (!groups[category]) {
          groups[category] = []
        }
        groups[category].push(task)
      })

      return Object.entries(groups).map(([category, tasks]) => ({
        name: `${category.charAt(0).toUpperCase() + category.slice(1)} Tasks Project`,
        mission: `Project for ${category} related tasks`,
        tasks,
        taskCount: tasks.length,
      }))

    default:
      return []
  }
})
// Methods
function getPriorityColor(priority) {
  const colors = {
    low: 'grey',
    medium: 'info',
    high: 'warning',
    critical: 'error',
  }
  return colors[priority] || 'grey'
}
// Wizard navigation methods
function nextStep() {
  if (currentStep.value < 4 && canProceedToNextStep.value) {
    currentStep.value++
  }
}
function previousStep() {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}
function removeTaskFromSelection(taskId) {
  const updatedSelection = props.selectedTaskIds.filter((id) => id !== taskId)
  // We would need to emit this change back to parent
  // For now, this is a placeholder
  console.log('Remove task:', taskId)
}
function getTaskTitle(taskId) {
  const task = tasksToConvert.value.find((t) => t.id === taskId)
  return task ? task.title : 'Unknown Task'
}
// Graph visualization methods
function getTaskPosition(taskId) {
  const taskIndex = tasksToConvert.value.findIndex((t) => t.id === taskId)
  const totalTasks = tasksToConvert.value.length

  if (totalTasks <= 3) {
    // Linear layout for small numbers
    const spacing = graphDimensions.value.width / (totalTasks + 1)
    return {
      x: spacing * (taskIndex + 1),
      y: graphDimensions.value.height / 2,
    }
  } else {
    // Circular layout for larger numbers
    const centerX = graphDimensions.value.width / 2
    const centerY = graphDimensions.value.height / 2
    const radius = Math.min(centerX, centerY) - 60
    const angle = (2 * Math.PI * taskIndex) / totalTasks

    return {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    }
  }
}
function getTaskRadius(task) {
  // Base radius on task complexity (description length + priority)
  const baseRadius = 25
  const complexityFactor = task.description ? Math.min(task.description.length / 50, 2) : 1
  const priorityFactor = { low: 1, medium: 1.2, high: 1.4, critical: 1.6 }[task.priority] || 1

  return baseRadius + complexityFactor * priorityFactor * 5
}
function getDependencyColor(strength) {
  const colors = {
    strong: '#f44336', // red
    medium: '#ff9800', // orange
    weak: '#2196f3', // blue
  }
  return colors[strength] || '#666'
}
function getDependencyWidth(strength) {
  const widths = {
    strong: 3,
    medium: 2,
    weak: 1,
  }
  return widths[strength] || 1
}
function selectDependencyTask(taskId) {
  selectedDependencyTask.value = selectedDependencyTask.value === taskId ? null : taskId
}
async function performConversion() {
  if (!canConvert.value) return

  converting.value = true
  try {
    const convertedProjects = []
    const conversionId = `conv_${Date.now()}`

    // Track conversion start
    const conversionRecord = {
      id: conversionId,
      created_at: new Date().toISOString(),
      status: 'in_progress',
      strategy: conversionStrategy.value,
      task_count: tasksToConvert.value.length,
      project_count: finalConversionPreview.value.length,
      tasks: tasksToConvert.value.map((t) => ({
        id: t.id,
        title: t.title,
        priority: t.priority,
      })),
      projects: [],
      options: { ...options.value },
      has_dependencies: taskDependencies.value.length > 0,
    }

    for (const projectPreview of finalConversionPreview.value) {
      // Create project via MCP
      const projectData = {
        name: projectPreview.name,
        mission: projectPreview.mission,
        product_id: productStore.currentProductId,
        priority: projectPreview.priority,
        category: projectPreview.category,
        conversion_id: conversionId,
      }

      const project = await projectStore.createProject(projectData)
      convertedProjects.push(project)

      // Add to conversion record
      conversionRecord.projects.push({
        id: project.id,
        name: project.name,
      })

      // Update tasks with conversion metadata
      if (options.value.markTasksConverted) {
        for (const task of projectPreview.tasks) {
          await taskStore.updateTask(task.id, {
            converted_project_id: project.id,
            conversion_date: new Date().toISOString(),
            conversion_id: conversionId,
            ...(options.value.preserveTaskLinks && { original_task_id: task.id }),
          })
        }
      }
    }

    // Mark conversion as completed
    conversionRecord.status = 'completed'

    // Store conversion record (would normally be via API)
    localStorage.setItem(`conversion_${conversionId}`, JSON.stringify(conversionRecord))

    emit('converted', convertedProjects)
    emit('close')
  } catch (error) {
    console.error('Conversion failed:', error)

    // Mark conversion as failed
    const failedRecord = {
      id: conversionId,
      created_at: new Date().toISOString(),
      status: 'failed',
      error: error.message,
      strategy: conversionStrategy.value,
      task_count: tasksToConvert.value.length,
      project_count: finalConversionPreview.value.length,
      tasks: tasksToConvert.value.map((t) => ({
        id: t.id,
        title: t.title,
        priority: t.priority,
      })),
      projects: [],
      options: { ...options.value },
    }

    localStorage.setItem(`conversion_${conversionId}`, JSON.stringify(failedRecord))
  } finally {
    converting.value = false
  }
}
// Auto-generate project name for single conversion
watch(
  [tasksToConvert, conversionStrategy],
  () => {
    if (conversionStrategy.value === 'single' && tasksToConvert.value.length > 0) {
      if (!projectConfig.value.name) {
        const categories = [...new Set(tasksToConvert.value.map((t) => t.category))]
        const categoryText =
          categories.length === 1
            ? categories[0].charAt(0).toUpperCase() + categories[0].slice(1)
            : 'Mixed'

        projectConfig.value.name = `${categoryText} Tasks Project`
      }

      if (!projectConfig.value.mission) {
        const taskTitles = tasksToConvert.value.map((t) => t.title).join(', ')
        projectConfig.value.mission = `Project created from tasks: ${taskTitles}`
      }
    }
  },
  { immediate: true },
)
// Reset form when dialog closes
watch(
  () => props.show,
  (newVal) => {
    if (!newVal) {
      currentStep.value = 1
      conversionStrategy.value = 'single'
      dependencyHandling.value = 'preserve'
      projectConfig.value = {
        name: '',
        mission: '',
        priority: 'medium',
        category: 'general',
      }
      options.value = {
        preserveTaskLinks: true,
        markTasksConverted: true,
        assignToCurrentAgent: false,
        inheritTaskPriority: true,
      }
    }
  },
)
</script>
