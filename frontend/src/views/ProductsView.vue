<template>
  <v-container fluid class="products-container">
    <!-- Fixed Page Header -->
    <div class="products-header">
      <v-row>
        <v-col cols="12">
          <div class="d-flex align-center mb-6">
            <h1 class="text-h4">Products</h1>
            <v-spacer></v-spacer>
            <v-btn color="primary" prepend-icon="mdi-plus" @click="showDialog = true">
              New Product
            </v-btn>
          </div>
        </v-col>
      </v-row>
    </div>

    <!-- Scrollable Products Grid -->
    <div class="products-content">
      <v-row>
        <v-col cols="12">
        <v-card>
          <v-card-title class="d-flex align-center">
            <span>All Products</span>
            <v-spacer></v-spacer>
            <v-btn
              variant="outlined"
              :color="deletedProductsCount > 0 ? 'warning' : 'grey'"
              prepend-icon="mdi-delete-restore"
              @click="showDeletedProductsDialog = true"
              :disabled="deletedProductsCount === 0"
              class="mr-3"
              style="height: 40px;"
            >
              Deleted ({{ deletedProductsCount }})
            </v-btn>
            <v-select
              v-model="sortBy"
              :items="sortOptions"
              item-title="label"
              item-value="value"
              prepend-inner-icon="mdi-sort"
              label="Sort by"
              variant="outlined"
              density="compact"
              hide-details
              class="mr-3"
              style="max-width: 200px"
            ></v-select>
            <v-text-field
              v-model="search"
              prepend-inner-icon="mdi-magnify"
              label="Search products..."
              single-line
              hide-details
              variant="outlined"
              density="compact"
              style="max-width: 300px"
            ></v-text-field>
          </v-card-title>

          <v-card-text>
            <v-row v-if="loading">
              <v-col cols="12" class="text-center py-8">
                <v-progress-circular indeterminate color="primary"></v-progress-circular>
                <div class="text-medium-emphasis mt-4">Loading products...</div>
              </v-col>
            </v-row>

            <v-row v-else-if="filteredProducts.length === 0">
              <v-col cols="12" class="text-center py-8">
                <v-icon size="64" color="grey-lighten-2">mdi-package-variant-remove</v-icon>
                <div class="text-h6 text-medium-emphasis mt-4">No products found</div>
                <div class="text-body-2 text-medium-emphasis">
                  {{
                    search
                      ? 'Try adjusting your search'
                      : 'Create your first product to get started'
                  }}
                </div>
              </v-col>
            </v-row>

            <v-row v-else>
              <v-col
                v-for="product in filteredProducts"
                :key="product.id"
                cols="12"
                sm="6"
                md="4"
                lg="3"
              >
                <v-card
                  :elevation="0"
                  class="product-card h-100"
                >
                  <v-card-text>
                    <div class="d-flex align-center justify-space-between mb-2">
                      <div
                        class="text-h6"
                        :style="product.is_active ? 'color: #ffc300' : ''"
                      >
                        {{ product.name }}
                      </div>
                      <v-chip
                        v-if="product.is_active"
                      color="success"
                      size="small"
                      variant="flat"
                    >
                      Active
                      </v-chip>
                    </div>

                    <div class="text-caption text-medium-emphasis mb-3">
                      Created: {{ formatDate(product.created_at) }}
                    </div>

                    <div class="mb-3">
                      <div class="text-caption text-medium-emphasis">Product ID:</div>
                      <div class="font-monospace" style="font-size: 0.65rem; word-break: break-all; line-height: 1.3;">
                        {{ product.id }}
                      </div>
                    </div>

                    <!-- Statistics -->
                    <v-divider class="my-3"></v-divider>
                    <v-row dense>
                      <v-col cols="4" class="text-center">
                        <div class="text-caption text-medium-emphasis">Tasks</div>
                        <div class="text-h6" style="color: #ffc300">
                          {{ product.task_count || 0 }}
                        </div>
                      </v-col>
                      <v-col cols="4" class="text-center">
                        <div class="text-caption text-medium-emphasis">Projects</div>
                        <div class="text-h6" style="color: #ffc300">
                          {{ product.project_count || 0 }}
                        </div>
                      </v-col>
                      <v-col cols="4" class="text-center">
                        <div class="text-caption text-medium-emphasis">Completed</div>
                        <div class="text-h6" style="color: #ffc300">
                          {{ getCompletedProjectsCount(product) }}
                        </div>
                      </v-col>
                    </v-row>
                  </v-card-text>

                  <v-card-actions>
                    <v-btn
                      variant="text"
                      size="small"
                      @click="toggleProductActivation(product)"
                    >
                      {{ product.is_active ? 'Deactivate' : 'Activate' }}
                    </v-btn>
                    <v-spacer></v-spacer>
                    <v-btn
                      icon
                      size="small"
                      variant="text"
                      @click="showProductDetails(product)"
                      :style="product.id === productStore.currentProductId ? 'color: #e1e1e1' : ''"
                    >
                      <v-icon>mdi-information-outline</v-icon>
                    </v-btn>
                    <v-btn
                      icon
                      size="small"
                      variant="text"
                      @click="editProduct(product)"
                      :style="product.id === productStore.currentProductId ? 'color: #e1e1e1' : ''"
                    >
                      <v-icon>mdi-pencil</v-icon>
                    </v-btn>
                    <v-btn
                      icon
                      size="small"
                      variant="text"
                      color="error"
                      @click="confirmDelete(product)"
                    >
                      <v-icon>mdi-delete</v-icon>
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    </div><!-- End products-content -->

    <!-- Create/Edit Product Dialog -->
    <v-dialog v-model="showDialog" max-width="700" persistent retain-focus>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">{{ editingProduct ? 'mdi-pencil' : 'mdi-plus' }}</v-icon>
          <span>{{ editingProduct ? 'Edit Product' : 'Create New Product' }}</span>
          <v-spacer />

          <!-- Handover 0051: Save Status Indicator -->
          <v-chip
            v-if="autoSave && autoSave.saveStatus.value === 'saving'"
            color="info"
            size="small"
            variant="flat"
            class="mr-2"
            aria-live="polite"
          >
            <v-icon start size="small" class="mdi-spin">mdi-loading</v-icon>
            Saving...
          </v-chip>

          <v-chip
            v-else-if="autoSave && autoSave.saveStatus.value === 'unsaved'"
            color="warning"
            size="small"
            variant="flat"
            class="mr-2"
            aria-live="polite"
          >
            <v-icon start size="small">mdi-content-save-alert</v-icon>
            Unsaved changes
          </v-chip>

          <v-chip
            v-else-if="autoSave && autoSave.saveStatus.value === 'saved'"
            color="success"
            size="small"
            variant="flat"
            class="mr-2"
            aria-live="polite"
          >
            <v-icon start size="small">mdi-check</v-icon>
            Saved
          </v-chip>

          <v-chip
            v-else-if="autoSave && autoSave.saveStatus.value === 'error'"
            color="error"
            size="small"
            variant="flat"
            class="mr-2"
            aria-live="assertive"
          >
            <v-icon start size="small">mdi-alert-circle</v-icon>
            Error
          </v-chip>

          <v-btn icon="mdi-close" variant="text" @click="closeDialog" aria-label="Close" />
        </v-card-title>

        <v-divider></v-divider>

        <v-card-text style="min-height: 400px; max-height: 600px; overflow-y: auto">
          <!-- Tabbed interface for product configuration (single line tabs, no dots) -->
          <v-tabs
            v-model="dialogTab"
            class="mb-4 tabs-with-arrows"
            color="primary"
            show-arrows
            prev-icon="mdi-chevron-left"
            next-icon="mdi-chevron-right"
          >
            <v-tab value="basic">Basic Info</v-tab>
            <v-tab value="vision">Vision Docs</v-tab>
            <v-tab value="tech">Tech Stack</v-tab>
            <v-tab value="arch">Architecture</v-tab>
            <v-tab value="features">Features & Testing</v-tab>
          </v-tabs>

          <v-form ref="formRef" v-model="formValid">
            <!-- Handover 0042: Tab windows -->
            <v-tabs-window v-model="dialogTab">
              <!-- Basic Info Tab -->
              <v-tabs-window-item value="basic">
            <!-- Basic tab heading -->
            <div class="text-subtitle-1 mb-4">Product Information</div>

            <!-- Product Name -->
            <v-text-field
              v-model="productForm.name"
              label="Product Name"
              :rules="[(v) => !!v || 'Name is required']"
              variant="outlined"
              density="comfortable"
              required
              class="mb-4 mt-2"
            ></v-text-field>

            <!-- Handover 0084: Project Path for Agent Export -->
            <v-text-field
              v-model="productForm.projectPath"
              label="Project Path (optional)"
              variant="outlined"
              density="comfortable"
              placeholder="F:/Projects/MyProduct"
              prepend-inner-icon="mdi-folder-outline"
              hint="File system path to your product folder. Copy from File Explorer/Finder address bar. Required for exporting agents."
              persistent-hint
              class="mb-4"
            ></v-text-field>

            <!-- Description -->
            <v-textarea
              v-model="productForm.description"
              label="Description (Context for Orchestrator)"
              variant="outlined"
              density="comfortable"
              rows="6"
              auto-grow
              hint="This description will be used by the orchestrator for mission generation"
              persistent-hint
              class="mb-4"
            ></v-textarea>
              </v-tabs-window-item>

              <!-- Vision Documents Tab -->
              <v-tabs-window-item value="vision">
            <!-- Vision Documents Section -->

            <div class="text-subtitle-1 mb-4">
              Vision Documents
            </div>

            <!-- Existing Documents (Edit Mode Only) -->
            <div v-if="editingProduct && existingVisionDocuments.length > 0" class="mb-4">
              <div class="text-subtitle-2 mb-2">
                Existing Documents ({{ existingVisionDocuments.length }})
              </div>

              <v-list density="compact" class="mb-3">
                <v-list-item
                  v-for="doc in existingVisionDocuments"
                  :key="doc.id"
                  class="border rounded mb-2"
                >
                  <template v-slot:prepend>
                    <v-icon :color="doc.chunked ? 'success' : 'warning'">
                      {{ doc.chunked ? 'mdi-check-circle' : 'mdi-clock-outline' }}
                    </v-icon>
                  </template>

                  <v-list-item-title>{{ doc.filename || doc.document_name }}</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ doc.chunk_count || 0 }} chunks • {{ formatDate(doc.created_at) }}
                  </v-list-item-subtitle>

                  <template v-slot:append>
                    <v-btn
                      icon
                      size="small"
                      variant="text"
                      color="error"
                      @click="deleteVisionDocument(doc)"
                    >
                      <v-icon size="20">mdi-delete</v-icon>
                    </v-btn>
                  </template>
                </v-list-item>
              </v-list>
            </div>

            <!-- File Upload Component -->
            <div class="text-caption text-medium-emphasis mb-3">
              Upload product requirements, proposals, specifications (.md, .txt files)
            </div>

            <v-file-input
              v-model="visionFiles"
              accept=".txt,.md,.markdown"
              label="Choose files"
              variant="outlined"
              density="comfortable"
              multiple
              show-size
              clearable
              prepend-icon="mdi-folder-open"
              hint="Select multiple files (Ctrl/Cmd + Click)"
              persistent-hint
              class="mb-3"
            ></v-file-input>

            <!-- File List -->
            <div v-if="visionFiles && visionFiles.length > 0">
              <div class="text-subtitle-2 mb-2">
                Files to Upload ({{ visionFiles.length }})
              </div>

              <v-list density="compact" class="mb-3">
                <v-list-item
                  v-for="(file, index) in visionFiles"
                  :key="index"
                  class="border rounded mb-2"
                >
                  <template v-slot:prepend>
                    <v-icon color="primary">mdi-file-document</v-icon>
                  </template>

                  <v-list-item-title>{{ file.name }}</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ formatFileSize(file.size) }}
                  </v-list-item-subtitle>

                  <template v-slot:append>
                    <v-btn
                      icon
                      size="small"
                      variant="text"
                      @click="removeVisionFile(index)"
                    >
                      <v-icon size="20">mdi-close</v-icon>
                    </v-btn>
                  </template>
                </v-list-item>
              </v-list>

              <v-alert type="info" variant="tonal" density="compact">
                Files will be auto-chunked for context (25K token limit)
              </v-alert>
            </div>
              </v-tabs-window-item>

              <!-- Tech Stack Tab (Handover 0042) -->
              <v-tabs-window-item value="tech">
                <div class="text-subtitle-1 mb-4">Technology Stack Configuration</div>

                <v-textarea
                  v-model="productForm.configData.tech_stack.languages"
                  placeholder="Python 3.11, JavaScript ES2023, TypeScript 5.2"
                  hint="List all programming languages used (comma-separated or line-by-line)"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="3"
                  auto-grow
                  class="mb-4"
                >
                  <template #label>
                    <span>Programming Languages</span>
                    <v-chip
                      v-if="hasFieldPriority('tech_stack.languages')"
                      :color="getPriorityColor(getPriorityForField('tech_stack.languages'))"
                      size="x-small"
                      class="ml-2"
                    >
                      {{ getPriorityLabel(getPriorityForField('tech_stack.languages')) }}
                    </v-chip>
                    <v-tooltip
                      v-if="hasFieldPriority('tech_stack.languages')"
                      location="top"
                      max-width="300"
                    >
                      <template #activator="{ props }">
                        <v-icon
                          v-bind="props"
                          size="small"
                          class="ml-1"
                          style="vertical-align: middle"
                        >
                          mdi-information-outline
                        </v-icon>
                      </template>
                      <span style="white-space: pre-line">{{
                        getPriorityTooltip(getPriorityForField('tech_stack.languages'))
                      }}</span>
                    </v-tooltip>
                  </template>
                </v-textarea>

                <v-textarea
                  v-model="productForm.configData.tech_stack.frontend"
                  placeholder="Vue 3, Vuetify 3, Pinia, Vue Router"
                  hint="List frontend technologies (frameworks, libraries, tools)"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="3"
                  auto-grow
                  class="mb-4"
                >
                  <template #label>
                    <span>Frontend Frameworks & Libraries</span>
                    <v-chip
                      v-if="hasFieldPriority('tech_stack.frontend')"
                      :color="getPriorityColor(getPriorityForField('tech_stack.frontend'))"
                      size="x-small"
                      class="ml-2"
                    >
                      {{ getPriorityLabel(getPriorityForField('tech_stack.frontend')) }}
                    </v-chip>
                    <v-tooltip
                      v-if="hasFieldPriority('tech_stack.frontend')"
                      location="top"
                      max-width="300"
                    >
                      <template #activator="{ props }">
                        <v-icon
                          v-bind="props"
                          size="small"
                          class="ml-1"
                          style="vertical-align: middle"
                        >
                          mdi-information-outline
                        </v-icon>
                      </template>
                      <span style="white-space: pre-line">{{
                        getPriorityTooltip(getPriorityForField('tech_stack.frontend'))
                      }}</span>
                    </v-tooltip>
                  </template>
                </v-textarea>

                <v-textarea
                  v-model="productForm.configData.tech_stack.backend"
                  placeholder="FastAPI 0.104, SQLAlchemy 2.0, Alembic, asyncio"
                  hint="List backend technologies (frameworks, ORMs, services)"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="3"
                  auto-grow
                  class="mb-4"
                >
                  <template #label>
                    <span>Backend Frameworks & Services</span>
                    <v-chip
                      v-if="hasFieldPriority('tech_stack.backend')"
                      :color="getPriorityColor(getPriorityForField('tech_stack.backend'))"
                      size="x-small"
                      class="ml-2"
                    >
                      {{ getPriorityLabel(getPriorityForField('tech_stack.backend')) }}
                    </v-chip>
                    <v-tooltip
                      v-if="hasFieldPriority('tech_stack.backend')"
                      location="top"
                      max-width="300"
                    >
                      <template #activator="{ props }">
                        <v-icon
                          v-bind="props"
                          size="small"
                          class="ml-1"
                          style="vertical-align: middle"
                        >
                          mdi-information-outline
                        </v-icon>
                      </template>
                      <span style="white-space: pre-line">{{
                        getPriorityTooltip(getPriorityForField('tech_stack.backend'))
                      }}</span>
                    </v-tooltip>
                  </template>
                </v-textarea>

                <v-textarea
                  v-model="productForm.configData.tech_stack.database"
                  placeholder="PostgreSQL 16, Redis 7, Vector embeddings (pgvector)"
                  hint="List databases and data storage solutions"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="3"
                  auto-grow
                  class="mb-4"
                >
                  <template #label>
                    <span>Databases & Data Storage</span>
                    <v-chip
                      v-if="hasFieldPriority('tech_stack.database')"
                      :color="getPriorityColor(getPriorityForField('tech_stack.database'))"
                      size="x-small"
                      class="ml-2"
                    >
                      {{ getPriorityLabel(getPriorityForField('tech_stack.database')) }}
                    </v-chip>
                    <v-tooltip
                      v-if="hasFieldPriority('tech_stack.database')"
                      location="top"
                      max-width="300"
                    >
                      <template #activator="{ props }">
                        <v-icon
                          v-bind="props"
                          size="small"
                          class="ml-1"
                          style="vertical-align: middle"
                        >
                          mdi-information-outline
                        </v-icon>
                      </template>
                      <span style="white-space: pre-line">{{
                        getPriorityTooltip(getPriorityForField('tech_stack.database'))
                      }}</span>
                    </v-tooltip>
                  </template>
                </v-textarea>

                <v-textarea
                  v-model="productForm.configData.tech_stack.infrastructure"
                  placeholder="Docker, Kubernetes, GitHub Actions CI/CD, AWS (EC2, S3, RDS)"
                  hint="List infrastructure and deployment tools"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="3"
                  auto-grow
                  class="mb-4"
                >
                  <template #label>
                    <span>Infrastructure & DevOps</span>
                    <v-chip
                      v-if="hasFieldPriority('tech_stack.infrastructure')"
                      :color="getPriorityColor(getPriorityForField('tech_stack.infrastructure'))"
                      size="x-small"
                      class="ml-2"
                    >
                      {{ getPriorityLabel(getPriorityForField('tech_stack.infrastructure')) }}
                    </v-chip>
                    <v-tooltip
                      v-if="hasFieldPriority('tech_stack.infrastructure')"
                      location="top"
                      max-width="300"
                    >
                      <template #activator="{ props }">
                        <v-icon
                          v-bind="props"
                          size="small"
                          class="ml-1"
                          style="vertical-align: middle"
                        >
                          mdi-information-outline
                        </v-icon>
                      </template>
                      <span style="white-space: pre-line">{{
                        getPriorityTooltip(getPriorityForField('tech_stack.infrastructure'))
                      }}</span>
                    </v-tooltip>
                  </template>
                </v-textarea>
              </v-tabs-window-item>

              <!-- Architecture Tab (Handover 0042) -->
              <v-tabs-window-item value="arch">
                <div class="text-subtitle-1 mb-4">Architecture & Design Patterns</div>

                <v-textarea
                  v-model="productForm.configData.architecture.pattern"
                  placeholder="Modular Monolith with Event-Driven components, CQRS for high-traffic modules"
                  hint="Describe the overall system architecture approach"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="2"
                  auto-grow
                  class="mb-4"
                >
                  <template #label>
                    <span>Primary Architecture Pattern</span>
                    <v-chip
                      v-if="hasFieldPriority('architecture.pattern')"
                      :color="getPriorityColor(getPriorityForField('architecture.pattern'))"
                      size="x-small"
                      class="ml-2"
                    >
                      {{ getPriorityLabel(getPriorityForField('architecture.pattern')) }}
                    </v-chip>
                    <v-tooltip
                      v-if="hasFieldPriority('architecture.pattern')"
                      location="top"
                      max-width="300"
                    >
                      <template #activator="{ props }">
                        <v-icon
                          v-bind="props"
                          size="small"
                          class="ml-1"
                          style="vertical-align: middle"
                        >
                          mdi-information-outline
                        </v-icon>
                      </template>
                      <span style="white-space: pre-line">{{
                        getPriorityTooltip(getPriorityForField('architecture.pattern'))
                      }}</span>
                    </v-tooltip>
                  </template>
                </v-textarea>

                <v-textarea
                  v-model="productForm.configData.architecture.design_patterns"
                  placeholder="Repository Pattern, Dependency Injection, Factory Pattern, SOLID principles"
                  hint="List design patterns and architectural principles used"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="3"
                  auto-grow
                  class="mb-4"
                >
                  <template #label>
                    <span>Design Patterns & Principles</span>
                    <v-chip
                      v-if="hasFieldPriority('architecture.design_patterns')"
                      :color="getPriorityColor(getPriorityForField('architecture.design_patterns'))"
                      size="x-small"
                      class="ml-2"
                    >
                      {{ getPriorityLabel(getPriorityForField('architecture.design_patterns')) }}
                    </v-chip>
                    <v-tooltip
                      v-if="hasFieldPriority('architecture.design_patterns')"
                      location="top"
                      max-width="300"
                    >
                      <template #activator="{ props }">
                        <v-icon
                          v-bind="props"
                          size="small"
                          class="ml-1"
                          style="vertical-align: middle"
                        >
                          mdi-information-outline
                        </v-icon>
                      </template>
                      <span style="white-space: pre-line">{{
                        getPriorityTooltip(getPriorityForField('architecture.design_patterns'))
                      }}</span>
                    </v-tooltip>
                  </template>
                </v-textarea>

                <v-textarea
                  v-model="productForm.configData.architecture.api_style"
                  placeholder="REST API (OpenAPI 3.0), WebSocket for real-time updates, GraphQL for complex queries"
                  hint="Describe API communication patterns and protocols"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="2"
                  auto-grow
                  class="mb-4"
                >
                  <template #label>
                    <span>API Style & Communication</span>
                    <v-chip
                      v-if="hasFieldPriority('architecture.api_style')"
                      :color="getPriorityColor(getPriorityForField('architecture.api_style'))"
                      size="x-small"
                      class="ml-2"
                    >
                      {{ getPriorityLabel(getPriorityForField('architecture.api_style')) }}
                    </v-chip>
                    <v-tooltip
                      v-if="hasFieldPriority('architecture.api_style')"
                      location="top"
                      max-width="300"
                    >
                      <template #activator="{ props }">
                        <v-icon
                          v-bind="props"
                          size="small"
                          class="ml-1"
                          style="vertical-align: middle"
                        >
                          mdi-information-outline
                        </v-icon>
                      </template>
                      <span style="white-space: pre-line">{{
                        getPriorityTooltip(getPriorityForField('architecture.api_style'))
                      }}</span>
                    </v-tooltip>
                  </template>
                </v-textarea>

                <v-textarea
                  v-model="productForm.configData.architecture.notes"
                  hint="Additional architectural decisions, constraints, or context"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="4"
                  auto-grow
                  class="mb-4"
                >
                  <template #label>
                    <span>Architecture Notes</span>
                    <v-chip
                      v-if="hasFieldPriority('architecture.notes')"
                      :color="getPriorityColor(getPriorityForField('architecture.notes'))"
                      size="x-small"
                      class="ml-2"
                    >
                      {{ getPriorityLabel(getPriorityForField('architecture.notes')) }}
                    </v-chip>
                    <v-tooltip
                      v-if="hasFieldPriority('architecture.notes')"
                      location="top"
                      max-width="300"
                    >
                      <template #activator="{ props }">
                        <v-icon
                          v-bind="props"
                          size="small"
                          class="ml-1"
                          style="vertical-align: middle"
                        >
                          mdi-information-outline
                        </v-icon>
                      </template>
                      <span style="white-space: pre-line">{{
                        getPriorityTooltip(getPriorityForField('architecture.notes'))
                      }}</span>
                    </v-tooltip>
                  </template>
                </v-textarea>
              </v-tabs-window-item>

              <!-- Features & Testing Tab (Handover 0042) -->
              <v-tabs-window-item value="features">
                <div class="text-subtitle-1 mb-4">Features & Quality Standards</div>

                <v-textarea
                  v-model="productForm.configData.features.core"
                  hint="Main functionality and capabilities of this product"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="4"
                  auto-grow
                  class="mb-4"
                >
                  <template #label>
                    <span>Core Features</span>
                    <v-chip
                      v-if="hasFieldPriority('features.core')"
                      :color="getPriorityColor(getPriorityForField('features.core'))"
                      size="x-small"
                      class="ml-2"
                    >
                      {{ getPriorityLabel(getPriorityForField('features.core')) }}
                    </v-chip>
                    <v-tooltip
                      v-if="hasFieldPriority('features.core')"
                      location="top"
                      max-width="300"
                    >
                      <template #activator="{ props }">
                        <v-icon
                          v-bind="props"
                          size="small"
                          class="ml-1"
                          style="vertical-align: middle"
                        >
                          mdi-information-outline
                        </v-icon>
                      </template>
                      <span style="white-space: pre-line">{{
                        getPriorityTooltip(getPriorityForField('features.core'))
                      }}</span>
                    </v-tooltip>
                  </template>
                </v-textarea>

                <!-- Handover 0051: Enhanced testing strategy dropdown -->
                <v-select
                  v-model="productForm.configData.test_config.strategy"
                  :items="testingStrategies"
                  item-title="title"
                  item-value="value"
                  hint="Choose the primary testing methodology for this product"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  class="mb-4"
                >
                  <template #label>
                    <span>Testing Strategy & Approach</span>
                    <v-chip
                      v-if="hasFieldPriority('test_config.strategy')"
                      :color="getPriorityColor(getPriorityForField('test_config.strategy'))"
                      size="x-small"
                      class="ml-2"
                    >
                      {{ getPriorityLabel(getPriorityForField('test_config.strategy')) }}
                    </v-chip>
                    <v-tooltip
                      v-if="hasFieldPriority('test_config.strategy')"
                      location="top"
                      max-width="300"
                    >
                      <template #activator="{ props }">
                        <v-icon
                          v-bind="props"
                          size="small"
                          class="ml-1"
                          style="vertical-align: middle"
                        >
                          mdi-information-outline
                        </v-icon>
                      </template>
                      <span style="white-space: pre-line">{{
                        getPriorityTooltip(getPriorityForField('test_config.strategy'))
                      }}</span>
                    </v-tooltip>
                  </template>

                  <!-- Handover 0051: Enhanced dropdown items with icons and subtitles -->
                  <template #item="{ props, item }">
                    <v-list-item v-bind="props">
                      <template #prepend>
                        <v-icon :icon="item.raw.icon" class="mr-2"></v-icon>
                      </template>
                      <v-list-item-title>{{ item.raw.title }}</v-list-item-title>
                      <v-list-item-subtitle>{{ item.raw.subtitle }}</v-list-item-subtitle>
                    </v-list-item>
                  </template>

                  <!-- Handover 0051: Enhanced selection display with icon -->
                  <template #selection="{ item }">
                    <div class="d-flex align-center">
                      <v-icon :icon="item.raw.icon" size="small" class="mr-2"></v-icon>
                      <span>{{ item.raw.title }}</span>
                    </div>
                  </template>
                </v-select>

                <div class="mb-4">
                  <label class="text-caption text-medium-emphasis">
                    Test Coverage Target: {{ productForm.configData.test_config.coverage_target }}%
                    <v-chip
                      v-if="hasFieldPriority('test_config.coverage_target')"
                      :color="getPriorityColor(getPriorityForField('test_config.coverage_target'))"
                      size="x-small"
                      class="ml-2"
                    >
                      {{ getPriorityLabel(getPriorityForField('test_config.coverage_target')) }}
                    </v-chip>
                    <v-tooltip
                      v-if="hasFieldPriority('test_config.coverage_target')"
                      location="top"
                      max-width="300"
                    >
                      <template #activator="{ props }">
                        <v-icon
                          v-bind="props"
                          size="x-small"
                          class="ml-1"
                          style="vertical-align: middle"
                        >
                          mdi-information-outline
                        </v-icon>
                      </template>
                      <span style="white-space: pre-line">{{
                        getPriorityTooltip(getPriorityForField('test_config.coverage_target'))
                      }}</span>
                    </v-tooltip>
                  </label>
                  <v-slider
                    v-model="productForm.configData.test_config.coverage_target"
                    min="0"
                    max="100"
                    step="5"
                    thumb-label
                    color="primary"
                  ></v-slider>
                </div>

                <v-textarea
                  v-model="productForm.configData.test_config.frameworks"
                  placeholder="pytest, pytest-asyncio, Playwright, coverage.py"
                  hint="List testing frameworks and quality assurance tools"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="3"
                  auto-grow
                  class="mb-4"
                >
                  <template #label>
                    <span>Testing Frameworks & Tools</span>
                    <v-chip
                      v-if="hasFieldPriority('test_config.frameworks')"
                      :color="getPriorityColor(getPriorityForField('test_config.frameworks'))"
                      size="x-small"
                      class="ml-2"
                    >
                      {{ getPriorityLabel(getPriorityForField('test_config.frameworks')) }}
                    </v-chip>
                    <v-tooltip
                      v-if="hasFieldPriority('test_config.frameworks')"
                      location="top"
                      max-width="300"
                    >
                      <template #activator="{ props }">
                        <v-icon
                          v-bind="props"
                          size="small"
                          class="ml-1"
                          style="vertical-align: middle"
                        >
                          mdi-information-outline
                        </v-icon>
                      </template>
                      <span style="white-space: pre-line">{{
                        getPriorityTooltip(getPriorityForField('test_config.frameworks'))
                      }}</span>
                    </v-tooltip>
                  </template>
                </v-textarea>
              </v-tabs-window-item>
            </v-tabs-window>
          </v-form>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="goPrevTab" :disabled="isFirstTab">Back</v-btn>
          <v-btn
            color="primary"
            variant="flat"
            @click="editingProduct ? saveProduct() : (isLastTab ? saveProduct() : goNextTab())"
            :disabled="editingProduct ? (!formValid || saving) : (isLastTab ? (!formValid || saving) : saving)"
            :loading="editingProduct ? saving : (isLastTab ? saving : false)"
          >
            {{ editingProduct ? 'Save Changes' : (isLastTab ? 'Create Product' : 'Next') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Product Details Dialog -->
    <v-dialog v-model="showDetailsDialog" max-width="600">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-information-outline</v-icon>
          Product Details
          <v-spacer></v-spacer>
          <v-btn icon variant="text" @click="showDetailsDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-divider></v-divider>

        <v-card-text v-if="selectedProduct">
          <!-- Product Name -->
          <div class="text-h6 mb-2">{{ selectedProduct.name }}</div>
          <div class="text-caption text-medium-emphasis mb-4">ID: {{ selectedProduct.id }}</div>

          <!-- Description -->
          <div class="mb-4">
            <div class="text-subtitle-2 mb-1">Description</div>
            <div class="text-body-2">
              {{ selectedProduct.description || 'No description provided' }}
            </div>
          </div>

          <!-- Statistics -->
          <div class="mb-4">
            <div class="text-subtitle-2 mb-2">Statistics</div>
            <v-row dense>
              <v-col cols="6">
                <div class="text-caption">Unresolved Tasks</div>
                <div class="text-h6">{{ selectedProduct.unresolved_tasks || 0 }}</div>
              </v-col>
              <v-col cols="6">
                <div class="text-caption">Unfinished Projects</div>
                <div class="text-h6">{{ selectedProduct.unfinished_projects || 0 }}</div>
              </v-col>
            </v-row>
          </div>

          <!-- Vision Documents -->
          <div>
            <div class="text-subtitle-2 mb-2">
              Vision Documents ({{ detailsVisionDocuments.length }})
            </div>

            <v-list v-if="detailsVisionDocuments.length > 0" density="compact">
              <v-list-item
                v-for="doc in detailsVisionDocuments"
                :key="doc.id"
                class="border rounded mb-1"
              >
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
            <v-card
              v-if="detailsVisionDocuments.length > 0"
              variant="tonal"
              color="primary"
              class="mt-3"
            >
              <v-card-text class="py-2">
                <div class="text-caption">
                  <v-icon size="16" class="mr-1">mdi-chart-box-outline</v-icon>
                  <strong>Total chunks:</strong> {{ totalChunks }} @ ~20K tokens each<br>
                  <v-icon size="16" class="mr-1">mdi-folder-outline</v-icon>
                  <strong>Total file sizes:</strong> {{ totalFileSize }} across {{ detailsVisionDocuments.length }} document(s)
                </div>
              </v-card-text>
            </v-card>
          </div>

          <!-- Handover 0042: Configuration Data Display -->
          <div v-if="selectedProduct.has_config_data" class="mt-4">
            <v-divider class="mb-3"></v-divider>
            <div class="text-subtitle-2 mb-2">Configuration Data</div>
            
            <v-expansion-panels variant="accordion">
              <!-- Tech Stack -->
              <v-expansion-panel v-if="selectedProduct.config_data?.tech_stack">
                <v-expansion-panel-title>
                  <v-icon start>mdi-code-tags</v-icon>
                  Tech Stack
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <div v-if="selectedProduct.config_data.tech_stack.languages" class="mb-2">
                    <div class="text-caption font-weight-bold">Languages:</div>
                    <div class="text-body-2">{{ selectedProduct.config_data.tech_stack.languages }}</div>
                  </div>
                  <div v-if="selectedProduct.config_data.tech_stack.frontend" class="mb-2">
                    <div class="text-caption font-weight-bold">Frontend:</div>
                    <div class="text-body-2">{{ selectedProduct.config_data.tech_stack.frontend }}</div>
                  </div>
                  <div v-if="selectedProduct.config_data.tech_stack.backend" class="mb-2">
                    <div class="text-caption font-weight-bold">Backend:</div>
                    <div class="text-body-2">{{ selectedProduct.config_data.tech_stack.backend }}</div>
                  </div>
                  <div v-if="selectedProduct.config_data.tech_stack.database">
                    <div class="text-caption font-weight-bold">Databases:</div>
                    <div class="text-body-2">{{ selectedProduct.config_data.tech_stack.database }}</div>
                  </div>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <!-- Architecture -->
              <v-expansion-panel v-if="selectedProduct.config_data?.architecture">
                <v-expansion-panel-title>
                  <v-icon start>mdi-sitemap</v-icon>
                  Architecture
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <div v-if="selectedProduct.config_data.architecture.pattern" class="mb-2">
                    <div class="text-caption font-weight-bold">Pattern:</div>
                    <div class="text-body-2">{{ selectedProduct.config_data.architecture.pattern }}</div>
                  </div>
                  <div v-if="selectedProduct.config_data.architecture.api_style" class="mb-2">
                    <div class="text-caption font-weight-bold">API Style:</div>
                    <div class="text-body-2">{{ selectedProduct.config_data.architecture.api_style }}</div>
                  </div>
                  <div v-if="selectedProduct.config_data.architecture.design_patterns">
                    <div class="text-caption font-weight-bold">Design Patterns:</div>
                    <div class="text-body-2">{{ selectedProduct.config_data.architecture.design_patterns }}</div>
                  </div>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <!-- Features & Testing -->
              <v-expansion-panel v-if="selectedProduct.config_data?.features || selectedProduct.config_data?.test_config">
                <v-expansion-panel-title>
                  <v-icon start>mdi-star-outline</v-icon>
                  Features & Testing
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <div v-if="selectedProduct.config_data.features?.core" class="mb-2">
                    <div class="text-caption font-weight-bold">Core Features:</div>
                    <div class="text-body-2">{{ selectedProduct.config_data.features.core }}</div>
                  </div>
                  <div v-if="selectedProduct.config_data.test_config?.strategy" class="mb-2">
                    <div class="text-caption font-weight-bold">Testing Strategy:</div>
                    <div class="text-body-2">{{ selectedProduct.config_data.test_config.strategy }}</div>
                  </div>
                  <div v-if="selectedProduct.config_data.test_config?.coverage_target">
                    <div class="text-caption font-weight-bold">Coverage Target:</div>
                    <div class="text-body-2">{{ selectedProduct.config_data.test_config.coverage_target }}%</div>
                  </div>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>

          <!-- Created/Updated -->
          <div class="text-caption text-medium-emphasis mt-4">
            Created: {{ formatDate(selectedProduct.created_at) }}<br />
            Updated: {{ formatDate(selectedProduct.updated_at) }}
          </div>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="showDetailsDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog with Cascade Impact -->
    <v-dialog v-model="showDeleteDialog" max-width="500" persistent>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start color="warning">mdi-delete</v-icon>
          Move Product to Trash?
        </v-card-title>

        <v-divider></v-divider>

        <v-card-text v-if="deletingProduct">
          <!-- Loading State -->
          <div v-if="loadingCascadeImpact" class="text-center py-4">
            <v-progress-circular indeterminate color="error"></v-progress-circular>
            <div class="text-caption mt-2">Calculating impact...</div>
          </div>

          <!-- Warning Content -->
          <div v-else>
            <v-alert type="warning" variant="tonal" density="compact" class="mb-4">
              <div class="text-subtitle-1 font-weight-bold mb-2">Move to Trash?</div>
              <div>
                <strong>{{ deletingProduct.name }}</strong> will be moved to trash and can be recovered for 10 days.
                After 10 days, it will be permanently deleted.
              </div>
            </v-alert>

            <!-- Cascade Impact -->
            <div v-if="cascadeImpact" class="mb-4">
              <div class="text-subtitle-2 mb-2">This will delete:</div>

              <v-list density="compact">
                <v-list-item>
                  <template v-slot:prepend>
                    <v-icon color="error">mdi-folder-multiple</v-icon>
                  </template>
                  <v-list-item-title>
                    <strong>{{ cascadeImpact.unfinished_projects }}</strong> unfinished projects
                  </v-list-item-title>
                  <v-list-item-subtitle>
                    ({{ cascadeImpact.projects_count }} total projects)
                  </v-list-item-subtitle>
                </v-list-item>

                <v-list-item>
                  <template v-slot:prepend>
                    <v-icon color="error">mdi-checkbox-marked-circle</v-icon>
                  </template>
                  <v-list-item-title>
                    <strong>{{ cascadeImpact.unresolved_tasks }}</strong> unresolved tasks
                  </v-list-item-title>
                  <v-list-item-subtitle>
                    ({{ cascadeImpact.tasks_count }} total tasks)
                  </v-list-item-subtitle>
                </v-list-item>

                <v-list-item>
                  <template v-slot:prepend>
                    <v-icon color="error">mdi-file-document-multiple</v-icon>
                  </template>
                  <v-list-item-title>
                    <strong>{{ cascadeImpact.vision_documents_count }}</strong> vision documents
                  </v-list-item-title>
                </v-list-item>

                <v-list-item>
                  <template v-slot:prepend>
                    <v-icon color="error">mdi-database</v-icon>
                  </template>
                  <v-list-item-title>
                    <strong>{{ cascadeImpact.total_chunks }}</strong> context chunks
                  </v-list-item-title>
                </v-list-item>
              </v-list>
            </div>

            <!-- Simplified Confirmation -->
            <v-divider class="my-4"></v-divider>

            <v-checkbox
              v-model="deleteConfirmationCheck"
              density="compact"
              hide-details
            >
              <template #label>
                <span>I understand this product will be recoverable for 10 days</span>
              </template>
            </v-checkbox>
          </div>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="cancelDelete" :disabled="deleting"> Cancel </v-btn>
          <v-btn
            color="warning"
            variant="flat"
            @click="confirmDeleteProduct"
            :disabled="!deleteConfirmationCheck || deleting"
            :loading="deleting"
          >
            Move to Trash
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Handover 0050: Activation Warning Dialog -->
    <ActivationWarningDialog
      v-model="showActivationWarning"
      :new-product="pendingActivation || {}"
      :current-active="currentActiveProduct || {}"
      @confirm="confirmActivation"
      @cancel="cancelActivation"
    />

    <!-- Deleted Products Recovery Dialog -->
    <v-dialog v-model="showDeletedProductsDialog" max-width="800" persistent>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start color="warning">mdi-delete-restore</v-icon>
          Deleted Products
          <v-spacer></v-spacer>
          <v-btn icon variant="text" @click="showDeletedProductsDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-divider></v-divider>

        <v-card-text style="max-height: 500px; overflow-y: auto">
          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
            Products are recoverable for 10 days after deletion. After that, they will be permanently purged.
          </v-alert>

          <div v-if="loadingDeletedProducts" class="text-center py-8">
            <v-progress-circular indeterminate color="warning"></v-progress-circular>
            <div class="text-caption mt-2">Loading deleted products...</div>
          </div>

          <div v-else-if="deletedProducts.length === 0" class="text-center py-8">
            <v-icon size="64" color="grey-lighten-2">mdi-delete-empty</v-icon>
            <div class="text-h6 text-medium-emphasis mt-4">No deleted products</div>
          </div>

          <v-list v-else density="compact">
            <v-list-item
              v-for="product in deletedProducts"
              :key="product.id"
              class="border rounded mb-3 pa-3"
            >
              <div class="d-flex flex-column">
                <div class="d-flex align-center justify-space-between mb-2">
                  <div>
                    <div class="text-h6">{{ product.name }}</div>
                    <div class="text-caption text-medium-emphasis">
                      {{ product.description || 'No description' }}
                    </div>
                  </div>
                  <v-chip
                    :color="product.days_until_purge <= 2 ? 'error' : 'warning'"
                    size="small"
                    variant="flat"
                  >
                    {{ product.days_until_purge }} days left
                  </v-chip>
                </div>

                <v-divider class="my-2"></v-divider>

                <div class="d-flex align-center justify-space-between">
                  <div class="text-caption">
                    <v-icon size="16" class="mr-1">mdi-folder-multiple</v-icon>
                    {{ product.project_count }} projects •
                    <v-icon size="16" class="ml-2 mr-1">mdi-file-document</v-icon>
                    {{ product.vision_documents_count }} vision docs •
                    <v-icon size="16" class="ml-2 mr-1">mdi-clock-outline</v-icon>
                    Deleted {{ formatDate(product.deleted_at) }}
                  </div>
                  <v-btn
                    color="success"
                    variant="flat"
                    size="small"
                    prepend-icon="mdi-restore"
                    @click="restoreProduct(product)"
                    :loading="restoringProductId === product.id"
                    :disabled="restoringProductId !== null"
                  >
                    Restore
                  </v-btn>
                </div>
              </div>
            </v-list-item>
          </v-list>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="showDeletedProductsDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useProductStore } from '@/stores/products'
import { useSettingsStore } from '@/stores/settings'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import { useFieldPriority } from '@/composables/useFieldPriority'
import { useAutoSave } from '@/composables/useAutoSave'
import api from '@/services/api'
import ActivationWarningDialog from '@/components/products/ActivationWarningDialog.vue'

const productStore = useProductStore()
const settingsStore = useSettingsStore()
const router = useRouter()
const { showToast } = useToast()
const { getPriorityForField, getPriorityLabel, getPriorityColor, getPriorityTooltip } =
  useFieldPriority()

// State
const loading = ref(false)
const search = ref('')
const sortBy = ref('name')
const showDialog = ref(false)
const showDeleteDialog = ref(false)
const showDetailsDialog = ref(false)
const editingProduct = ref(null)
const deletingProduct = ref(null)
const selectedProduct = ref(null)
const saving = ref(false)
const deleting = ref(false)
const formValid = ref(false)
const formRef = ref(null)
const visionFiles = ref([])
const existingVisionDocuments = ref([])
const detailsVisionDocuments = ref([])
const cascadeImpact = ref(null)
const loadingCascadeImpact = ref(false)
const deleteConfirmationCheck = ref(false)
const dialogTab = ref('basic')  // Handover 0042: Tab for product dialog (basic, tech, arch, features)
const autoSave = ref(null)  // Handover 0051: Auto-save composable instance

// Handover 0050: Activation warning dialog state
const showActivationWarning = ref(false)
const pendingActivation = ref(null)
const currentActiveProduct = ref(null)

// Soft delete recovery state
const showDeletedProductsDialog = ref(false)
const deletedProducts = ref([])
const loadingDeletedProducts = ref(false)
const restoringProductId = ref(null)

// Wizard tab order and navigation helpers
const tabOrder = ['basic', 'vision', 'tech', 'arch', 'features']
const isFirstTab = computed(() => tabOrder.indexOf(dialogTab.value) === 0)
const isLastTab = computed(() => tabOrder.indexOf(dialogTab.value) === tabOrder.length - 1)

function goNextTab() {
  const idx = tabOrder.indexOf(dialogTab.value)
  if (idx >= 0 && idx < tabOrder.length - 1) {
    dialogTab.value = tabOrder[idx + 1]
  }
}

function goPrevTab() {
  const idx = tabOrder.indexOf(dialogTab.value)
  if (idx > 0) {
    dialogTab.value = tabOrder[idx - 1]
  }
}

const productForm = ref({
  name: '',
  description: '',
  visionPath: '',
  projectPath: '', // Handover 0084: Project path for agent export
  // Handover 0042: Rich configuration data
  configData: {
    tech_stack: {
      languages: '',
      frontend: '',
      backend: '',
      database: '',
      infrastructure: '',
    },
    architecture: {
      pattern: '',
      design_patterns: '',
      api_style: '',
      notes: '',
    },
    features: {
      core: '',
    },
    test_config: {
      strategy: 'TDD',
      coverage_target: 80,
      frameworks: '',
    },
  },
})

// Sort options
const sortOptions = [
  { label: 'Name (A-Z)', value: 'name' },
  { label: 'Date Created (Newest)', value: 'date-newest' },
  { label: 'Date Created (Oldest)', value: 'date-oldest' },
]

// Handover 0051: Testing strategies with enhanced dropdown
const testingStrategies = [
  {
    value: 'TDD',
    title: 'TDD (Test-Driven Development)',
    subtitle: 'Write tests before implementation code',
    icon: 'mdi-test-tube',
  },
  {
    value: 'BDD',
    title: 'BDD (Behavior-Driven Development)',
    subtitle: 'Tests based on user stories and behavior specs',
    icon: 'mdi-comment-text-multiple',
  },
  {
    value: 'Integration-First',
    title: 'Integration-First',
    subtitle: 'Focus on testing component interactions',
    icon: 'mdi-connection',
  },
  {
    value: 'E2E-First',
    title: 'E2E-First',
    subtitle: 'Prioritize end-to-end user workflow tests',
    icon: 'mdi-path',
  },
  {
    value: 'Manual',
    title: 'Manual Testing',
    subtitle: 'Human-driven QA and exploratory testing',
    icon: 'mdi-human-male',
  },
  {
    value: 'Hybrid',
    title: 'Hybrid Approach',
    subtitle: 'Combination of multiple testing strategies',
    icon: 'mdi-view-grid-plus',
  },
]

// Handover 0051: Unsaved changes computed
const hasUnsavedChanges = computed(() => {
  return autoSave.value?.hasUnsavedChanges.value || false
})

// Handover 0051: Tab validation indicators
const tabValidation = computed(() => {
  return {
    basic: {
      valid: !!productForm.value.name,
      hasError: !productForm.value.name,
      hasWarning: false,
    },
    vision: {
      valid: true,
      hasError: false,
      hasWarning: visionFiles.value.length === 0 && existingVisionDocuments.value.length === 0,
    },
    tech: {
      valid: true,
      hasError: false,
      hasWarning: !productForm.value.configData.tech_stack.languages,
    },
    arch: {
      valid: true,
      hasError: false,
      hasWarning: !productForm.value.configData.architecture.pattern,
    },
    features: {
      valid: true,
      hasError: false,
      hasWarning: !productForm.value.configData.features.core,
    },
  }
})

// Computed
const filteredProducts = computed(() => {
  // Filter by search
  let products = productStore.products
  if (search.value) {
    const searchLower = search.value.toLowerCase()
    products = products.filter(
      (product) =>
        product.name.toLowerCase().includes(searchLower) ||
        product.description?.toLowerCase().includes(searchLower),
    )
  }

  // Sort products - ACTIVE PRODUCTS FIRST (leftmost/top)
  const sorted = [...products]

  // Primary sort: Active products first
  sorted.sort((a, b) => {
    // If one is active and the other isn't, active comes first
    if (a.is_active && !b.is_active) return -1
    if (!a.is_active && b.is_active) return 1

    // Both active or both inactive - apply secondary sort
    switch (sortBy.value) {
      case 'name':
        return a.name.localeCompare(b.name)
      case 'date-newest':
        return new Date(b.created_at) - new Date(a.created_at)
      case 'date-oldest':
        return new Date(a.created_at) - new Date(b.created_at)
      default:
        return 0
    }
  })

  return sorted
})

const totalProducts = computed(() => productStore.productCount)
const activeProducts = computed(
  () => productStore.products.filter((p) => p.status === 'active').length,
)

const totalTasks = computed(() => {
  return Object.values(productStore.productMetrics).reduce(
    (sum, metrics) => sum + (metrics.totalTasks || 0),
    0,
  )
})

const totalAgents = computed(() => {
  return Object.values(productStore.productMetrics).reduce(
    (sum, metrics) => sum + (metrics.activeAgents || 0),
    0,
  )
})

// Vision document aggregate stats for product details
const totalChunks = computed(() => {
  return detailsVisionDocuments.value.reduce((sum, doc) => sum + (doc.chunk_count || 0), 0)
})

const totalFileSize = computed(() => {
  const bytes = detailsVisionDocuments.value.reduce((sum, doc) => sum + (doc.file_size || 0), 0)
  return formatFileSize(bytes)
})

const deletedProductsCount = computed(() => {
  return deletedProducts.value.length
})

// Methods
function getProductInitial(product) {
  return product.name?.charAt(0).toUpperCase() || '?'
}

function getCompletedProjectsCount(product) {
  // Calculate completed projects: total - unfinished
  const totalProjects = product.project_count || 0
  const unfinishedProjects = product.unfinished_projects || 0
  return Math.max(0, totalProjects - unfinishedProjects)
}

function getProductMetric(productId, metric) {
  return productStore.productMetrics[productId]?.[metric] || 0
}

function getTaskProgress(productId) {
  const metrics = productStore.productMetrics[productId]
  if (!metrics || !metrics.totalTasks) return 0
  return (metrics.completedTasks / metrics.totalTasks) * 100
}

// Handover 0050: Enhanced activation with warning dialog
async function toggleProductActivation(product) {
  try {
    if (product.is_active) {
      // Deactivating - no warning needed
      await api.products.deactivate(product.id)
      await productStore.fetchActiveProduct()

      showToast({
        message: `${product.name} deactivated`,
        type: 'info',
        duration: 3000,
      })

      await loadProducts()
    } else {
      // Activating - check if there's currently an active product FIRST
      const currentActive = productStore.products.find(p => p.is_active)

      if (currentActive && currentActive.id !== product.id) {
        // There's already an active product - show warning BEFORE activating
        currentActiveProduct.value = currentActive
        pendingActivation.value = product
        showActivationWarning.value = true
        // Don't proceed yet - wait for user confirmation via confirmActivation()
        return
      }

      // No active product - proceed with activation
      await api.products.activate(product.id)
      await productStore.fetchActiveProduct()

      showToast({
        message: `${product.name} activated`,
        type: 'success',
        duration: 3000,
      })

      await loadProducts()
    }
  } catch (error) {
    console.error('Failed to toggle product activation:', error)
    showToast({
      message: 'Failed to change product status',
      type: 'error',
      duration: 5000,
    })
  }
}

// Handover 0050: Confirm activation after warning
async function confirmActivation(productId) {
  try {
    // User confirmed - NOW actually activate the product
    await api.products.activate(pendingActivation.value.id)
    await productStore.fetchActiveProduct()

    showToast({
      message: `${pendingActivation.value?.name} activated`,
      type: 'success',
      duration: 3000,
    })

    await loadProducts()

    // Close dialog
    showActivationWarning.value = false
    pendingActivation.value = null
    currentActiveProduct.value = null
  } catch (error) {
    console.error('Failed to confirm activation:', error)
    showToast({
      message: 'Failed to activate product',
      type: 'error',
      duration: 5000,
    })
  }
}

// Handover 0050: Cancel activation
function cancelActivation() {
  // User cancelled - just close dialog, activation never happened
  showActivationWarning.value = false
  pendingActivation.value = null
  currentActiveProduct.value = null
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

function removeVisionFile(index) {
  visionFiles.value.splice(index, 1)
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function showProductDetails(product) {
  selectedProduct.value = product

  // Fetch vision documents
  try {
    const response = await api.visionDocuments.listByProduct(product.id)
    detailsVisionDocuments.value = response.data || []
  } catch (error) {
    console.error('Failed to load vision documents:', error)
    detailsVisionDocuments.value = []
  }

  showDetailsDialog.value = true
}

async function editProduct(product) {
  editingProduct.value = product
  
  // Handover 0042: Default config structure
  const defaultConfig = {
    tech_stack: {
      languages: '',
      frontend: '',
      backend: '',
      database: '',
      infrastructure: '',
    },
    architecture: {
      pattern: '',
      design_patterns: '',
      api_style: '',
      notes: '',
    },
    features: {
      core: '',
    },
    test_config: {
      strategy: 'TDD',
      coverage_target: 80,
      frameworks: '',
    },
  }
  
  productForm.value = {
    name: product.name,
    description: product.description || '',
    visionPath: product.vision_path || '',
    projectPath: product.project_path || '', // Handover 0084: Project path for agent export
    // Handover 0042: Merge with existing config_data
    configData: product.config_data ? { ...defaultConfig, ...product.config_data } : defaultConfig,
  }

  // Fetch existing vision documents
  await loadExistingVisionDocuments(product.id)

  showDialog.value = true
}

async function loadExistingVisionDocuments(productId) {
  try {
    const response = await api.visionDocuments.listByProduct(productId)
    existingVisionDocuments.value = response.data || []
  } catch (error) {
    console.error('Failed to load vision documents:', error)
    existingVisionDocuments.value = []
  }
}

async function deleteVisionDocument(doc) {
  try {
    await api.visionDocuments.delete(doc.id)

    // Remove from list
    existingVisionDocuments.value = existingVisionDocuments.value.filter((d) => d.id !== doc.id)

    showToast({
      message: `${doc.filename} deleted`,
      type: 'success',
      duration: 3000,
    })
  } catch (error) {
    console.error('Failed to delete vision document:', error)
    showToast({
      message: 'Failed to delete vision document',
      type: 'error',
      duration: 5000,
    })
  }
}

async function confirmDelete(product) {
  deletingProduct.value = product
  deleteConfirmationCheck.value = false
  showDeleteDialog.value = true

  // Fetch cascade impact
  loadingCascadeImpact.value = true
  try {
    const response = await api.products.getCascadeImpact(product.id)
    cascadeImpact.value = response.data
  } catch (error) {
    console.error('Failed to get cascade impact:', error)
    showToast({
      message: 'Failed to load deletion impact',
      type: 'error',
      duration: 5000,
    })
  } finally {
    loadingCascadeImpact.value = false
  }
}

async function saveProduct() {
  if (!formValid.value) return

  saving.value = true
  try {
    // Step 1: Create/Update product
    let product
    if (editingProduct.value) {
      product = await productStore.updateProduct(editingProduct.value.id, {
        name: productForm.value.name,
        description: productForm.value.description,
        projectPath: productForm.value.projectPath,  // Handover 0084: Project path for agent export
        configData: productForm.value.configData,  // Handover 0042
      })
    } else {
      product = await productStore.createProduct({
        name: productForm.value.name,
        description: productForm.value.description,
        projectPath: productForm.value.projectPath,  // Handover 0084: Project path for agent export
        configData: productForm.value.configData,  // Handover 0042
      })
    }

    // Step 2: Upload vision files (if any)
    if (visionFiles.value && visionFiles.value.length > 0) {
      const productId = product?.id || editingProduct.value.id

      for (let i = 0; i < visionFiles.value.length; i++) {
        const file = visionFiles.value[i]

        try {
          const formData = new FormData()
          formData.append('product_id', productId)
          formData.append('document_name', file.name.replace(/\.[^/.]+$/, ''))
          formData.append('document_type', 'vision')
          formData.append('vision_file', file)
          formData.append('auto_chunk', 'true')

          await api.visionDocuments.upload(formData)
        } catch (uploadError) {
          console.error(`Failed to upload ${file.name}:`, uploadError)
          // Continue uploading other files
        }
      }
    }

    // Step 3: Clear auto-save cache (Handover 0051)
    if (autoSave.value) {
      autoSave.value.clearCache()
    }

    // Step 4: Refresh products
    await loadProducts()

    // Step 5: Close dialog
    closeDialog()

    // Step 6: Show success message
    showToast({
      message: editingProduct.value
        ? 'Product updated successfully'
        : 'Product created successfully',
      type: 'success',
      duration: 3000,
    })
  } catch (error) {
    console.error('Failed to save product:', error)
    showToast({
      message: 'Failed to save product',
      type: 'error',
      duration: 5000,
    })
    // Handover 0051: Do NOT close dialog on error - keep form data visible
  } finally {
    saving.value = false
  }
}

async function confirmDeleteProduct() {
  deleting.value = true
  try {
    await productStore.deleteProduct(deletingProduct.value.id)

    // If was active product, clear active state
    if (productStore.currentProductId === deletingProduct.value.id) {
      productStore.currentProductId = null
      productStore.currentProduct = null
      localStorage.removeItem('currentProductId')
    }

    // Close dialog
    showDeleteDialog.value = false
    const productName = deletingProduct.value.name
    deletingProduct.value = null

    // Refresh products (includes deleted products list)
    await loadProducts()

    // Show success message
    showToast({
      message: `${productName} moved to trash. Recoverable for 10 days.`,
      type: 'info',
      duration: 4000,
    })
  } catch (error) {
    console.error('Failed to delete product:', error)
    showToast({
      message: 'Failed to move product to trash',
      type: 'error',
      duration: 5000,
    })
  } finally {
    deleting.value = false
  }
}

function cancelDelete() {
  showDeleteDialog.value = false
  deletingProduct.value = null
  cascadeImpact.value = null
  deleteConfirmationCheck.value = false
}

function closeDialog() {
  // Handover 0051: Check for unsaved changes before closing
  if (hasUnsavedChanges.value) {
    const confirmed = confirm('You have unsaved changes. Close anyway?')
    if (!confirmed) {
      return // User cancelled - keep dialog open
    }
  }

  // Handover 0051: Clear auto-save cache
  if (autoSave.value) {
    autoSave.value.clearCache()
  }

  showDialog.value = false
  editingProduct.value = null
  visionFiles.value = []
  existingVisionDocuments.value = []
  dialogTab.value = 'basic'  // Handover 0042: Reset tab
  productForm.value = {
    name: '',
    description: '',
    visionPath: '',
    projectPath: '', // Handover 0084: Project path for agent export
    // Handover 0042: Reset config_data
    configData: {
      tech_stack: {
      languages: '',
      frontend: '',
      backend: '',
      database: '',
      infrastructure: '',
    },
    architecture: {
      pattern: '',
      design_patterns: '',
        api_style: '',
        notes: '',
      },
      features: {
        core: '',
      },
      test_config: {
      strategy: 'TDD',
      coverage_target: 80,
      frameworks: '',
      },
    },
  }
}

async function loadProducts() {
  loading.value = true
  try {
    await productStore.fetchProducts()
    // Fetch metrics for all products
    for (const product of productStore.products) {
      await productStore.fetchProductMetrics(product.id)
    }
    // Also load deleted products count
    await loadDeletedProducts()
  } finally {
    loading.value = false
  }
}

async function loadDeletedProducts() {
  try {
    const response = await api.products.getDeletedProducts()
    deletedProducts.value = response.data || []
  } catch (error) {
    console.error('Failed to load deleted products:', error)
    deletedProducts.value = []
  }
}

async function restoreProduct(product) {
  if (restoringProductId.value) return // Prevent double-click

  restoringProductId.value = product.id
  try {
    await api.products.restoreProduct(product.id)

    showToast({
      message: `${product.name} restored successfully`,
      type: 'success',
      duration: 3000,
    })

    // Reload both lists
    await loadProducts()
    await loadDeletedProducts()

    // Close dialog if no more deleted products
    if (deletedProducts.value.length === 0) {
      showDeletedProductsDialog.value = false
    }
  } catch (error) {
    console.error('Failed to restore product:', error)
    showToast({
      message: 'Failed to restore product',
      type: 'error',
      duration: 5000,
    })
  } finally {
    restoringProductId.value = null
  }
}

// Handover 0049: Helper to check if a field has priority
function hasFieldPriority(fieldPath) {
  return getPriorityForField(fieldPath) !== null
}

// Handover 0051: Watch for dialog open/close to initialize auto-save
watch(showDialog, (isOpen) => {
  if (isOpen) {
    // Generate unique cache key based on edit mode
    const cacheKey = editingProduct.value
      ? `product_form_draft_${editingProduct.value.id}`
      : 'product_form_draft_new'

    // Initialize auto-save composable
    autoSave.value = useAutoSave({
      key: cacheKey,
      data: productForm,
      debounceMs: 500,
      enableBackgroundSave: false, // LocalStorage only (no API saves during typing)
    })

    // Check for existing cache
    const cached = autoSave.value.restoreFromCache()
    if (cached) {
      const metadata = autoSave.value.getCacheMetadata()
      const ageMinutes = metadata?.ageMinutes ?? 0
      const TTL_MINUTES = 15
      // Snapshot current initial state for comparison
      const initialSnapshot = JSON.parse(JSON.stringify(productForm.value))
      const differs = JSON.stringify(cached) !== JSON.stringify(initialSnapshot)

      // Disable modal prompts. Silent policy:
      // - Editing existing product: auto-restore only if draft differs and is fresh (<= TTL)
      // - New product: do not auto-restore; clear any existing cached draft
      if (editingProduct.value) {
        if (differs && ageMinutes <= TTL_MINUTES) {
          // Handover 0084: Preserve current productForm values, only restore cached changes
          // This ensures new fields like projectPath don't get lost from old caches
          // Merge strategy: Only restore cached values if they are defined and not empty
          const mergedForm = { ...productForm.value }

          // Restore cached values, but preserve current values if cached is undefined/empty
          Object.keys(cached).forEach(key => {
            if (cached[key] !== undefined && cached[key] !== '') {
              mergedForm[key] = cached[key]
            }
          })

          // Explicitly preserve projectPath if not in cache or empty in cache
          if (!cached.projectPath && productForm.value.projectPath) {
            mergedForm.projectPath = productForm.value.projectPath
          }

          productForm.value = mergedForm
          showToast({ message: 'Draft restored', type: 'info', duration: 2000 })
        } else {
          autoSave.value.clearCache()
        }
      } else {
        // New product flow: never restore cached drafts
        autoSave.value.clearCache()
      }
    }
  } else {
    // Dialog closed - cleanup auto-save
    if (autoSave.value) {
      autoSave.value = null
    }
  }
})

// Handover 0051: Browser beforeunload handler (warn on refresh/close with unsaved changes)
function handleBeforeUnload(event) {
  if (showDialog.value && hasUnsavedChanges.value) {
    event.preventDefault()
    event.returnValue = '' // Required for Chrome
  }
}

onMounted(async () => {
  await loadProducts()
  // Load field priority configuration for badge display (Handover 0049)
  try {
    await settingsStore.fetchFieldPriorityConfig()
  } catch (error) {
    console.log('Field priority config not available:', error)
  }
  // Handover 0051: Add beforeunload listener
  window.addEventListener('beforeunload', handleBeforeUnload)
  // Product metrics updates via WebSocket (product:updated events)
})

onUnmounted(() => {
  // Handover 0051: Remove beforeunload listener
  window.removeEventListener('beforeunload', handleBeforeUnload)
})
</script>

<style scoped>
/* Fixed header and scrollable content layout */
.products-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.products-header {
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 10;
  background-color: inherit;
  padding-top: 16px;
}

.products-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding-bottom: 24px;
}

.product-card {
  transition: all 0.3s ease;
  border: 2px solid white;
  border-radius: 12px;
}

.product-card:hover {
  transform: translateY(-2px);
}

/* Handover 0051: Spinning icon animation for save status */
.mdi-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Bright (white) when enabled, dim when disabled; arrows no longer overlay tabs */
.tabs-with-arrows :deep(.v-slide-group__prev .v-btn .v-icon),
.tabs-with-arrows :deep(.v-slide-group__next .v-btn .v-icon) {
  color: white;
}
.tabs-with-arrows :deep(.v-slide-group__prev .v-btn.v-btn--disabled .v-icon),
.tabs-with-arrows :deep(.v-slide-group__next .v-btn.v-btn--disabled .v-icon) {
  opacity: 0.4;
}
</style>
