<template>
  <v-dialog v-model="isOpen" max-width="600">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-information-outline</v-icon>
        Product Details
        <v-spacer></v-spacer>
        <v-btn icon variant="text" @click="handleClose">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-divider></v-divider>

      <v-card-text v-if="product">
        <!-- Product Name -->
        <div class="text-h6 mb-2">{{ product.name }}</div>
        <div class="text-caption text-medium-emphasis mb-4">ID: {{ product.id }}</div>

        <!-- Description -->
        <div class="mb-4">
          <div class="text-subtitle-2 mb-1">Description</div>
          <div class="text-body-2">
            {{ product.description || 'No description provided' }}
          </div>
        </div>

        <!-- Statistics -->
        <div class="mb-4">
          <div class="text-subtitle-2 mb-2">Statistics</div>
          <v-row dense>
            <v-col cols="6">
              <div class="text-caption">Unresolved Tasks</div>
              <div class="text-h6">{{ product.unresolved_tasks || 0 }}</div>
            </v-col>
            <v-col cols="6">
              <div class="text-caption">Unfinished Projects</div>
              <div class="text-h6">{{ product.unfinished_projects || 0 }}</div>
            </v-col>
          </v-row>
        </div>

        <!-- Vision Documents -->
        <div>
          <div class="text-subtitle-2 mb-2">Vision Documents ({{ visionDocuments.length }})</div>

          <v-list v-if="visionDocuments.length > 0" density="compact">
            <v-list-item v-for="doc in visionDocuments" :key="doc.id" class="border rounded mb-1">
              <template v-slot:prepend>
                <v-icon color="primary">mdi-file-document</v-icon>
              </template>

              <v-list-item-title>{{ doc.filename || doc.document_name }}</v-list-item-title>
              <v-list-item-subtitle>
                {{ doc.chunk_count || 0 }} chunks •
                {{ formatFileSize(doc.file_size || 0) }}
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>

          <v-alert v-else type="info" variant="tonal" density="compact">
            No vision documents attached
          </v-alert>

          <!-- Aggregate Stats (only show if documents exist) -->
          <v-card v-if="visionDocuments.length > 0" variant="tonal" color="primary" class="mt-3">
            <v-card-text class="py-2">
              <div class="text-caption">
                <v-icon size="16" class="mr-1">mdi-chart-box-outline</v-icon>
                <strong>Total chunks:</strong> {{ totalChunks }} @ ~20K tokens each<br />
                <v-icon size="16" class="mr-1">mdi-folder-outline</v-icon>
                <strong>Total file sizes:</strong> {{ totalFileSize }} across
                {{ visionDocuments.length }} document(s)
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- Configuration Data Display -->
        <div v-if="product.has_config_data" class="mt-4">
          <v-divider class="mb-3"></v-divider>
          <div class="text-subtitle-2 mb-2">Configuration Data</div>

          <v-expansion-panels variant="accordion">
            <!-- Tech Stack -->
            <v-expansion-panel v-if="product.config_data?.tech_stack">
              <v-expansion-panel-title>
                <v-icon start>mdi-code-tags</v-icon>
                Tech Stack
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div v-if="product.config_data.tech_stack.languages" class="mb-2">
                  <div class="text-caption font-weight-bold">Languages:</div>
                  <div class="text-body-2">{{ product.config_data.tech_stack.languages }}</div>
                </div>
                <div v-if="product.config_data.tech_stack.frontend" class="mb-2">
                  <div class="text-caption font-weight-bold">Frontend:</div>
                  <div class="text-body-2">{{ product.config_data.tech_stack.frontend }}</div>
                </div>
                <div v-if="product.config_data.tech_stack.backend" class="mb-2">
                  <div class="text-caption font-weight-bold">Backend:</div>
                  <div class="text-body-2">{{ product.config_data.tech_stack.backend }}</div>
                </div>
                <div v-if="product.config_data.tech_stack.database">
                  <div class="text-caption font-weight-bold">Databases:</div>
                  <div class="text-body-2">{{ product.config_data.tech_stack.database }}</div>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Architecture -->
            <v-expansion-panel v-if="product.config_data?.architecture">
              <v-expansion-panel-title>
                <v-icon start>mdi-sitemap</v-icon>
                Architecture
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div v-if="product.config_data.architecture.pattern" class="mb-2">
                  <div class="text-caption font-weight-bold">Pattern:</div>
                  <div class="text-body-2">{{ product.config_data.architecture.pattern }}</div>
                </div>
                <div v-if="product.config_data.architecture.api_style" class="mb-2">
                  <div class="text-caption font-weight-bold">API Style:</div>
                  <div class="text-body-2">{{ product.config_data.architecture.api_style }}</div>
                </div>
                <div v-if="product.config_data.architecture.design_patterns">
                  <div class="text-caption font-weight-bold">Design Patterns:</div>
                  <div class="text-body-2">
                    {{ product.config_data.architecture.design_patterns }}
                  </div>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Features & Testing -->
            <v-expansion-panel
              v-if="product.config_data?.features || product.config_data?.test_config"
            >
              <v-expansion-panel-title>
                <v-icon start>mdi-star-outline</v-icon>
                Features & Testing
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div v-if="product.config_data.features?.core" class="mb-2">
                  <div class="text-caption font-weight-bold">Core Features:</div>
                  <div class="text-body-2">{{ product.config_data.features.core }}</div>
                </div>
                <div v-if="product.config_data.test_config?.strategy" class="mb-2">
                  <div class="text-caption font-weight-bold">Testing Strategy:</div>
                  <div class="text-body-2">{{ product.config_data.test_config.strategy }}</div>
                </div>
                <div v-if="product.config_data.test_config?.coverage_target">
                  <div class="text-caption font-weight-bold">Coverage Target:</div>
                  <div class="text-body-2">
                    {{ product.config_data.test_config.coverage_target }}%
                  </div>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </div>

        <!-- Created/Updated -->
        <div class="text-caption text-medium-emphasis mt-4">
          Created: {{ formatDate(product.created_at) }}<br />
          Updated: {{ formatDate(product.updated_at) }}
        </div>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="handleClose">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true,
  },
  product: {
    type: Object,
    default: () => ({}),
  },
  visionDocuments: {
    type: Array,
    default: () => [],
  },
  stats: {
    type: Object,
    default: () => ({ unresolved_tasks: 0, unfinished_projects: 0 }),
  },
})

const emit = defineEmits(['update:modelValue'])

const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const handleClose = () => {
  emit('update:modelValue', false)
}

// Computed properties for aggregate stats
const totalChunks = computed(() => {
  return props.visionDocuments.reduce((sum, doc) => sum + (doc.chunk_count || 0), 0)
})

const totalFileSize = computed(() => {
  const bytes = props.visionDocuments.reduce((sum, doc) => sum + (doc.file_size || 0), 0)
  return formatFileSize(bytes)
})

// Helper functions
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}
</script>
