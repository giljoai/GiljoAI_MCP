<template>
  <v-container fluid>
    <!-- Page Header -->
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center mb-6">
          <v-icon size="32" color="primary" class="mr-3">mdi-package-variant</v-icon>
          <h1 class="text-h4 font-weight-bold">Products</h1>
          <v-spacer></v-spacer>
          <v-btn color="primary" prepend-icon="mdi-plus" @click="showDialog = true">
            New Product
          </v-btn>
        </div>
      </v-col>
    </v-row>

    <!-- Products Grid -->
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="d-flex align-center">
            <span>All Products</span>
            <v-spacer></v-spacer>
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
                  :elevation="product.id === productStore.currentProductId ? 8 : 2"
                  class="product-card h-100"
                >
                  <v-card-text>
                    <div class="d-flex align-center justify-space-between mb-2">
                      <div
                        class="text-h6"
                        :style="product.id === productStore.currentProductId ? 'color: #ffc300' : ''"
                      >
                        {{ product.name }}
                      </div>
                      <v-chip
                        v-if="product.id === productStore.currentProductId"
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
                      <v-col cols="6" class="text-center">
                        <div class="text-caption text-medium-emphasis">Tasks</div>
                        <div class="text-h6" style="color: #ffc300">
                          {{ product.unresolved_tasks || 0 }}/{{ product.task_count || 0 }}
                        </div>
                      </v-col>
                      <v-col cols="6" class="text-center">
                        <div class="text-caption text-medium-emphasis">Projects</div>
                        <div class="text-h6" style="color: #ffc300">
                          {{ product.unfinished_projects || 0 }}/{{ product.project_count || 0 }}
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
                      {{ product.id === productStore.currentProductId ? 'Deactivate' : 'Activate' }}
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

    <!-- Create/Edit Product Dialog -->
    <v-dialog v-model="showDialog" max-width="700" persistent retain-focus>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">{{ editingProduct ? 'mdi-pencil' : 'mdi-plus' }}</v-icon>
          <span>{{ editingProduct ? 'Edit Product' : 'Create New Product' }}</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" @click="closeDialog" aria-label="Close" />
        </v-card-title>

        <v-divider></v-divider>

        <v-card-text style="min-height: 400px; max-height: 600px; overflow-y: auto">
          <!-- Handover 0042: Tabbed interface for product configuration -->
          <v-tabs v-model="dialogTab" class="mb-4" color="primary">
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
            <!-- Product Name -->
            <v-text-field
              v-model="productForm.name"
              label="Product Name"
              :rules="[(v) => !!v || 'Name is required']"
              variant="outlined"
              density="comfortable"
              required
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

            <div class="text-h6 mb-3">
              <v-icon start>mdi-file-document-multiple-outline</v-icon>
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
                  label="Programming Languages"
                  placeholder="Python 3.11, JavaScript ES2023, TypeScript 5.2"
                  hint="List all programming languages used (comma-separated or line-by-line)"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="3"
                  auto-grow
                  class="mb-4"
                ></v-textarea>

                <v-textarea
                  v-model="productForm.configData.tech_stack.frontend"
                  label="Frontend Frameworks & Libraries"
                  placeholder="Vue 3, Vuetify 3, Pinia, Vue Router"
                  hint="List frontend technologies (frameworks, libraries, tools)"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="3"
                  auto-grow
                  class="mb-4"
                ></v-textarea>

                <v-textarea
                  v-model="productForm.configData.tech_stack.backend"
                  label="Backend Frameworks & Services"
                  placeholder="FastAPI 0.104, SQLAlchemy 2.0, Alembic, asyncio"
                  hint="List backend technologies (frameworks, ORMs, services)"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="3"
                  auto-grow
                  class="mb-4"
                ></v-textarea>

                <v-textarea
                  v-model="productForm.configData.tech_stack.database"
                  label="Databases & Data Storage"
                  placeholder="PostgreSQL 16, Redis 7, Vector embeddings (pgvector)"
                  hint="List databases and data storage solutions"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="3"
                  auto-grow
                  class="mb-4"
                ></v-textarea>

                <v-textarea
                  v-model="productForm.configData.tech_stack.infrastructure"
                  label="Infrastructure & DevOps"
                  placeholder="Docker, Kubernetes, GitHub Actions CI/CD, AWS (EC2, S3, RDS)"
                  hint="List infrastructure and deployment tools"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="3"
                  auto-grow
                  class="mb-4"
                ></v-textarea>
              </v-tabs-window-item>

              <!-- Architecture Tab (Handover 0042) -->
              <v-tabs-window-item value="arch">
                <div class="text-subtitle-1 mb-4">Architecture & Design Patterns</div>

                <v-textarea
                  v-model="productForm.configData.architecture.pattern"
                  label="Primary Architecture Pattern"
                  placeholder="Modular Monolith with Event-Driven components, CQRS for high-traffic modules"
                  hint="Describe the overall system architecture approach"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="2"
                  auto-grow
                  class="mb-4"
                ></v-textarea>

                <v-textarea
                  v-model="productForm.configData.architecture.design_patterns"
                  label="Design Patterns & Principles"
                  placeholder="Repository Pattern, Dependency Injection, Factory Pattern, SOLID principles"
                  hint="List design patterns and architectural principles used"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="3"
                  auto-grow
                  class="mb-4"
                ></v-textarea>

                <v-textarea
                  v-model="productForm.configData.architecture.api_style"
                  label="API Style & Communication"
                  placeholder="REST API (OpenAPI 3.0), WebSocket for real-time updates, GraphQL for complex queries"
                  hint="Describe API communication patterns and protocols"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="2"
                  auto-grow
                  class="mb-4"
                ></v-textarea>

                <v-textarea
                  v-model="productForm.configData.architecture.notes"
                  label="Architecture Notes"
                  hint="Additional architectural decisions, constraints, or context"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="4"
                  auto-grow
                  class="mb-4"
                ></v-textarea>
              </v-tabs-window-item>

              <!-- Features & Testing Tab (Handover 0042) -->
              <v-tabs-window-item value="features">
                <div class="text-subtitle-1 mb-4">Features & Quality Standards</div>

                <v-textarea
                  v-model="productForm.configData.features.core"
                  label="Core Features"
                  hint="Main functionality and capabilities of this product"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="4"
                  auto-grow
                  class="mb-4"
                ></v-textarea>

                <v-textarea
                  v-model="productForm.configData.test_config.strategy"
                  label="Testing Strategy & Approach"
                  placeholder="TDD for core business logic, Integration tests for API endpoints, E2E with Playwright"
                  hint="Describe testing methodology and quality assurance approach"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="2"
                  auto-grow
                  class="mb-4"
                ></v-textarea>

                <div class="mb-4">
                  <label class="text-caption text-medium-emphasis">Test Coverage Target: {{ productForm.configData.test_config.coverage_target }}%</label>
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
                  label="Testing Frameworks & Tools"
                  placeholder="pytest, pytest-asyncio, Playwright, coverage.py"
                  hint="List testing frameworks and quality assurance tools"
                  persistent-hint
                  variant="outlined"
                  density="comfortable"
                  rows="3"
                  auto-grow
                  class="mb-4"
                ></v-textarea>
              </v-tabs-window-item>
            </v-tabs-window>
          </v-form>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="closeDialog">Cancel</v-btn>
          <v-btn
            color="primary"
            variant="flat"
            @click="saveProduct"
            :disabled="!formValid || saving"
            :loading="saving"
          >
            {{ editingProduct ? 'Save Changes' : 'Create Product' }}
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
        <v-card-title class="d-flex align-center text-error">
          <v-icon start color="error">mdi-alert-circle</v-icon>
          Delete Product?
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
            <v-alert type="error" variant="tonal" density="compact" class="mb-4">
              <div class="text-h6 mb-2">THIS ACTION CANNOT BE UNDONE</div>
              <div>
                You are about to permanently delete <strong>{{ deletingProduct.name }}</strong>
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

            <!-- Confirmation Input -->
            <v-divider class="my-4"></v-divider>

            <div class="mb-3">
              <div class="text-subtitle-2 mb-2">Type the product name to confirm:</div>
              <v-text-field
                v-model="deleteConfirmationName"
                :placeholder="deletingProduct.name"
                variant="outlined"
                density="comfortable"
                :error="deleteConfirmationError"
                :error-messages="
                  deleteConfirmationError ? 'Product name does not match' : ''
                "
              ></v-text-field>
            </div>

            <v-checkbox
              v-model="deleteConfirmationCheck"
              label="I understand this action is permanent and cannot be undone"
              density="compact"
              hide-details
            ></v-checkbox>
          </div>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="cancelDelete" :disabled="deleting"> Cancel </v-btn>
          <v-btn
            color="error"
            variant="flat"
            @click="confirmDeleteProduct"
            :disabled="!isDeleteConfirmed || deleting"
            :loading="deleting"
          >
            Delete Forever
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useProductStore } from '@/stores/products'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import api from '@/services/api'

const productStore = useProductStore()
const router = useRouter()
const { showToast } = useToast()

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
const deleteConfirmationName = ref('')
const deleteConfirmationCheck = ref(false)
const deleteConfirmationError = ref(false)
const dialogTab = ref('basic')  // Handover 0042: Tab for product dialog (basic, tech, arch, features)

const productForm = ref({
  name: '',
  description: '',
  visionPath: '',
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

// Computed
const isDeleteConfirmed = computed(() => {
  return (
    deleteConfirmationName.value === deletingProduct.value?.name &&
    deleteConfirmationCheck.value
  )
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

  // Sort products
  const sorted = [...products]
  switch (sortBy.value) {
    case 'name':
      sorted.sort((a, b) => a.name.localeCompare(b.name))
      break
    case 'date-newest':
      sorted.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      break
    case 'date-oldest':
      sorted.sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
      break
  }

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

// Methods
function getProductInitial(product) {
  return product.name?.charAt(0).toUpperCase() || '?'
}

function getProductMetric(productId, metric) {
  return productStore.productMetrics[productId]?.[metric] || 0
}

function getTaskProgress(productId) {
  const metrics = productStore.productMetrics[productId]
  if (!metrics || !metrics.totalTasks) return 0
  return (metrics.completedTasks / metrics.totalTasks) * 100
}

async function toggleProductActivation(product) {
  try {
    if (product.id === productStore.currentProductId) {
      // Deactivate - clear current product
      productStore.currentProductId = null
      productStore.currentProduct = null
      localStorage.removeItem('currentProductId')
      showToast({
        message: `${product.name} deactivated`,
        type: 'info',
        duration: 3000,
      })
    } else {
      // Activate product
      await productStore.setCurrentProduct(product.id)
      showToast({
        message: `${product.name} activated`,
        type: 'success',
        duration: 3000,
      })
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
  deleteConfirmationName.value = ''
  deleteConfirmationCheck.value = false
  deleteConfirmationError.value = false
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
        configData: productForm.value.configData,  // Handover 0042
      })
    } else {
      product = await productStore.createProduct({
        name: productForm.value.name,
        description: productForm.value.description,
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

    // Step 3: Refresh products
    await loadProducts()

    // Step 4: Close dialog
    closeDialog()

    // Step 5: Show success message
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
  } finally {
    saving.value = false
  }
}

async function confirmDeleteProduct() {
  // Validate name match
  if (deleteConfirmationName.value !== deletingProduct.value.name) {
    deleteConfirmationError.value = true
    return
  }

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

    // Refresh products
    await loadProducts()

    // Show success message
    showToast({
      message: `${productName} deleted successfully`,
      type: 'success',
      duration: 3000,
    })
  } catch (error) {
    console.error('Failed to delete product:', error)
    showToast({
      message: 'Failed to delete product',
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
  deleteConfirmationName.value = ''
  deleteConfirmationCheck.value = false
  deleteConfirmationError.value = false
}

function closeDialog() {
  showDialog.value = false
  editingProduct.value = null
  visionFiles.value = []
  existingVisionDocuments.value = []
  dialogTab.value = 'basic'  // Handover 0042: Reset tab
  productForm.value = {
    name: '',
    description: '',
    visionPath: '',
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
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadProducts()
  // Product metrics updates via WebSocket (product:updated events)
})
</script>

<style scoped>
.product-card {
  transition: all 0.3s ease;
}

.product-card:hover {
  transform: translateY(-2px);
}
</style>
