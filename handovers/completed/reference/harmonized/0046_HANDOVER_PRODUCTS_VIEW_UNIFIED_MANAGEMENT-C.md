# Handover 0046: ProductsView Unified Management with Vision Document Integration

**Date**: 2025-01-24
**From Agent**: System Architect + Deep Researcher
**To Agent**: Full-Stack Development Team (UX Designer + TDD Implementor + Frontend Tester)
**Priority**: High
**Estimated Effort**: 4-6 hours
**Status**: Not Started
**Risk Level**: Medium (Major UI refactoring, product-as-context architecture)

---

## Executive Summary

**Objective**: Refactor ProductsView to provide unified product management with integrated vision document upload, proper product-as-context architecture, and clean UI/UX.

**Current Problem**:
- Vision document upload is **completely inaccessible** (trapped in orphaned ProductSwitcher.vue)
- Users cannot upload vision documents anywhere in the application
- Product cards show description (too long, cluttered)
- "Switch" button navigates instead of setting active product context
- ProductSwitcher.vue is orphaned dead code (928 lines) with critical features
- Misleading instructions tell users to use non-existent "Product Switcher (top bar)"
- Product-as-context architecture not properly implemented

**Proposed Solution**:
- Consolidate ALL product management into ProductsView.vue
- Single-step product creation with vision document upload
- Tabbed create/edit dialogs (Details + Vision Documents)
- Clean product cards showing only: Name, Unresolved Tasks, Unfinished Projects, Date Created, Vision Doc Count
- Proper activate/deactivate for product-as-context (products = "sub-tenants")
- Delete ProductSwitcher.vue completely
- Scary double-confirmation delete with cascade impact display

**Value Delivered**:
- Users can finally upload vision documents (currently broken)
- Clean, intuitive product management in one place
- Proper product-as-context implementation (tasks/projects belong to active product)
- Reduced code complexity (delete 928 lines of orphaned code)
- Production-ready UX from day 1

---

## Research Findings

### 1. Current State Analysis

**ProductsView.vue** (`frontend/src/views/ProductsView.vue` - 528 lines):
- Route: `/Products`
- Shows product grid with cards
- Has create/edit dialogs BUT:
  - Vision path field is disabled
  - No way to upload vision documents
  - Instructions say "use Product Switcher (top bar)" - doesn't exist!
- Delete has basic confirmation (no cascade impact shown)

**ProductSwitcher.vue** (`frontend/src/components/ProductSwitcher.vue` - 928 lines):
- **Status**: Orphaned, not imported anywhere
- **Contains**: Full vision document management UI (Handover 0043 implementation)
- Vision Documents tab with:
  - Multi-file upload (browse + drag-drop)
  - File list with chunking status
  - Remove files with chunk deletion
  - Upload progress indicators
- **Problem**: Users cannot access this component at all

**ActiveProductDisplay.vue** (34 lines):
- Simple chip in top bar
- Shows current product name
- Clicks navigate to `/Products`
- Replaced ProductSwitcher but didn't migrate features

**Backend** (Handover 0043 - Already Complete):
- VisionDocument model exists (src/giljo_mcp/models.py)
- API endpoints exist (api/endpoints/vision_documents.py)
- Multi-tenant isolation configured
- Cascading deletes configured
- Auto-chunking implemented (25K token limit)

**Critical Gap**: Frontend has no UI to call the vision documents API!

### 2. Product-as-Context Architecture

**User Requirement**:
> "Products act as 'sub-tenants' - an organizational structure. User logs in → chooses product → tasks belong to product → projects belong to product. Agents/integrations are global."

**Current State**:
- Products exist but context is not enforced
- "Activate" button navigates to dashboard (wrong behavior)
- No visual indicator for active product
- Tasks/projects not filtered by active product

**Required Implementation**:
- Set active product in global state (localStorage + reactive state)
- Filter tasks to show only tasks for active product
- Filter projects to show only projects for active product
- Visual indicator on active product card
- ActiveProductDisplay chip shows current context

### 3. Product Card Display Requirements

**User Specification**:
> "Tasks (unresolved), Projects (unfinished), Date created, only these fields."

**Current State**:
- Shows: Name, Description, Projects, Tasks, Progress bar
- **Problem**: Description makes cards very long

**Required Changes**:
- Remove description from card
- Show: Name, Unresolved Tasks count, Unfinished Projects count, Date Created
- Add: Vision Document count badge (e.g., "3 docs")
- Add: Visual indicator for active product (border, color, icon)

### 4. Vision Document Integration Points

**API Endpoints** (Already Exist):
```
POST   /api/vision-documents/              # Upload file
GET    /api/vision-documents/product/{id}  # List files
DELETE /api/vision-documents/{id}          # Delete file + chunks
```

**Frontend Integration Needed**:
- Create dialog: Upload files during product creation
- Edit dialog: Show existing files + add/remove capability
- Details dialog: List files (read-only)

**Backend Behavior** (Already Implemented):
- Files auto-chunked on upload (25K token limit)
- Chunks stored in vision_document_chunks table
- Orchestrator uses chunks for mission generation
- Deleting file cascades to chunks

### 5. Delete Cascade Impact

**Database Cascade**:
```
Product (DELETE)
  └─> Projects (CASCADE)
       └─> Tasks (CASCADE)
  └─> VisionDocuments (CASCADE)
       └─> VisionChunks (CASCADE)
```

**Required UI**:
- Show counts before deletion:
  - "Will delete X unfinished projects"
  - "Will delete Y unresolved tasks"
  - "Will delete Z vision documents"
  - "Will delete W context chunks"
- Require typing product name to confirm
- Big warning: "THIS ACTION CANNOT BE UNDONE"

**API Endpoint Needed**:
```
GET /api/products/{id}/cascade-impact
Response: {
  projects_count: int,
  unfinished_projects: int,
  tasks_count: int,
  unresolved_tasks: int,
  vision_documents_count: int,
  total_chunks: int
}
```

---

## Implementation Plan

### Phase 1: Product Card Cleanup (1 hour)

**A. Update ProductCard Display** (`ProductsView.vue` lines 60-235):

Remove description, show only required fields:

```vue
<v-card-text>
  <div class="d-flex justify-space-between align-center mb-2">
    <div class="text-h6">{{ product.name }}</div>
    <v-chip v-if="isActiveProduct(product)" color="primary" size="small">Active</v-chip>
  </div>

  <div class="text-caption text-medium-emphasis mb-1">
    ID: {{ product.id }}
  </div>

  <!-- Statistics -->
  <v-row dense class="mt-3">
    <v-col cols="4">
      <div class="text-caption">Unresolved Tasks</div>
      <div class="text-h6">{{ product.unresolved_tasks || 0 }}</div>
    </v-col>
    <v-col cols="4">
      <div class="text-caption">Unfinished Projects</div>
      <div class="text-h6">{{ product.unfinished_projects || 0 }}</div>
    </v-col>
    <v-col cols="4">
      <div class="text-caption">Vision Docs</div>
      <div class="text-h6">
        {{ product.vision_documents_count || 0 }}
      </div>
    </v-col>
  </v-row>

  <div class="text-caption text-medium-emphasis mt-2">
    Created: {{ formatDate(product.created_at) }}
  </div>
</v-card-text>
```

**B. Fix Activate Button**:

Change from navigation to context setting:

```javascript
async function activateProduct(product) {
  try {
    // Set active product in global state
    await productStore.setActiveProduct(product.id)

    // Update local state
    activeProductId.value = product.id

    // Persist to localStorage
    localStorage.setItem('activeProductId', product.id)

    // Optional: Navigate to dashboard with active context
    // router.push('/dashboard')
  } catch (error) {
    console.error('Failed to activate product:', error)
  }
}
```

**C. Add Visual Indicator**:

```vue
<v-card
  :class="{ 'active-product-card': isActiveProduct(product) }"
  :style="isActiveProduct(product) ? 'border: 2px solid #FFD93D' : ''"
>
```

### Phase 2: Create Product Dialog with Vision Upload (1.5 hours)

**A. Add Tabs to Create Dialog** (`ProductsView.vue` lines 239-300):

```vue
<v-dialog v-model="showDialog" max-width="700" persistent>
  <v-card>
    <v-card-title>
      {{ editingProduct ? 'Edit Product' : 'Create New Product' }}
    </v-card-title>

    <v-divider></v-divider>

    <!-- Tabs -->
    <v-tabs v-model="createTab" color="primary">
      <v-tab value="details">
        <v-icon start>mdi-text-box-outline</v-icon>
        Details
      </v-tab>
      <v-tab value="vision">
        <v-icon start>mdi-file-document-multiple-outline</v-icon>
        Vision Documents
      </v-tab>
    </v-tabs>

    <v-divider></v-divider>

    <v-card-text style="min-height: 400px; max-height: 600px; overflow-y: auto;">
      <v-window v-model="createTab">
        <!-- Details Tab -->
        <v-window-item value="details">
          <v-form ref="productForm" v-model="formValid">
            <v-text-field
              v-model="productForm.name"
              label="Product Name"
              :rules="[(v) => !!v || 'Name is required']"
              variant="outlined"
              density="comfortable"
              required
            ></v-text-field>

            <v-textarea
              v-model="productForm.description"
              label="Description (Context for Orchestrator)"
              variant="outlined"
              density="comfortable"
              rows="8"
              auto-grow
              hint="This description will be used by the orchestrator for mission generation"
              persistent-hint
            ></v-textarea>
          </v-form>
        </v-window-item>

        <!-- Vision Documents Tab -->
        <v-window-item value="vision">
          <!-- File Upload Component -->
          <div class="mb-3">
            <div class="text-subtitle-2 mb-2">Upload Vision Documents</div>
            <div class="text-caption text-medium-emphasis mb-3">
              Product requirements, proposals, specifications (.md, .txt files)
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
              prepend-icon="mdi-file-document-outline"
              hint="Select multiple files (Ctrl/Cmd + Click)"
              persistent-hint
            >
              <template v-slot:append>
                <v-icon>mdi-upload</v-icon>
              </template>
            </v-file-input>
          </div>

          <!-- File List -->
          <div v-if="visionFiles && visionFiles.length > 0">
            <v-divider class="my-3"></v-divider>
            <div class="text-subtitle-2 mb-2">
              Files to Upload ({{ visionFiles.length }})
            </div>

            <v-list density="compact">
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

            <v-alert type="info" variant="tonal" density="compact" class="mt-3">
              Files will be auto-chunked for context (25K token limit)
            </v-alert>
          </div>

          <div v-else>
            <v-alert type="info" variant="tonal" density="compact">
              No files selected. You can upload vision documents now or add them later.
            </v-alert>
          </div>
        </v-window-item>
      </v-window>
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
```

**B. Add Save Logic with Vision Upload**:

```javascript
const visionFiles = ref([])
const uploadProgress = ref({})

async function saveProduct() {
  if (!formValid.value) return

  saving.value = true

  try {
    // Step 1: Create/Update product
    let product
    if (editingProduct.value) {
      product = await productsApi.update(editingProduct.value.id, {
        name: productForm.value.name,
        description: productForm.value.description
      })
    } else {
      product = await productsApi.create({
        name: productForm.value.name,
        description: productForm.value.description
      })
    }

    // Step 2: Upload vision files (if any)
    if (visionFiles.value && visionFiles.value.length > 0) {
      for (let i = 0; i < visionFiles.value.length; i++) {
        const file = visionFiles.value[i]

        // Show progress
        uploadProgress.value[i] = {
          filename: file.name,
          progress: 0
        }

        const formData = new FormData()
        formData.append('file', file)
        formData.append('product_id', product.id)

        await api.visionDocuments.upload(formData, (progressEvent) => {
          uploadProgress.value[i].progress =
            Math.round((progressEvent.loaded * 100) / progressEvent.total)
        })
      }
    }

    // Step 3: Refresh products
    await productStore.fetchProducts()

    // Step 4: Close dialog
    closeDialog()

    // Step 5: Show success
    // Toast notification: "Product created successfully"

  } catch (error) {
    console.error('Failed to save product:', error)
    // Show error toast
  } finally {
    saving.value = false
  }
}

function removeVisionFile(index) {
  visionFiles.value.splice(index, 1)
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
```

### Phase 3: Edit Product with Vision Management (1 hour)

**A. Pre-populate Edit Dialog**:

```javascript
async function editProduct(product) {
  editingProduct.value = product
  productForm.value = {
    name: product.name,
    description: product.description || ''
  }

  // Fetch existing vision documents
  await loadExistingVisionDocuments(product.id)

  showDialog.value = true
  createTab.value = 'details' // Start on details tab
}

const existingVisionDocuments = ref([])

async function loadExistingVisionDocuments(productId) {
  try {
    const response = await api.visionDocuments.listByProduct(productId)
    existingVisionDocuments.value = response.data || []
  } catch (error) {
    console.error('Failed to load vision documents:', error)
    existingVisionDocuments.value = []
  }
}
```

**B. Update Vision Documents Tab for Edit Mode**:

```vue
<!-- Vision Documents Tab - Edit Mode -->
<v-window-item value="vision">
  <!-- Existing Documents (Edit Mode Only) -->
  <div v-if="editingProduct && existingVisionDocuments.length > 0">
    <div class="text-subtitle-2 mb-2">
      Existing Documents ({{ existingVisionDocuments.length }})
    </div>

    <v-list density="compact" class="mb-4">
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

        <v-list-item-title>{{ doc.filename }}</v-list-item-title>
        <v-list-item-subtitle>
          {{ doc.chunk_count || 0 }} chunks • {{ formatDate(doc.created_at) }}
        </v-list-item-subtitle>

        <template v-slot:append>
          <v-btn
            icon
            size="small"
            variant="text"
            color="error"
            @click="confirmRemoveVisionDocument(doc)"
          >
            <v-icon size="20">mdi-delete</v-icon>
          </v-btn>
        </template>
      </v-list-item>
    </v-list>

    <v-divider class="my-3"></v-divider>
  </div>

  <!-- Add New Documents Section -->
  <div class="text-subtitle-2 mb-2">
    {{ editingProduct ? 'Add More Documents' : 'Upload Documents' }}
  </div>

  <!-- File Input (same as create) -->
  <v-file-input ...></v-file-input>
</v-window-item>
```

**C. Remove Vision Document with Confirmation**:

```javascript
const documentToDelete = ref(null)
const showDeleteDocumentDialog = ref(false)

function confirmRemoveVisionDocument(doc) {
  documentToDelete.value = doc
  showDeleteDocumentDialog.value = true
}

async function deleteVisionDocument() {
  if (!documentToDelete.value) return

  try {
    await api.visionDocuments.delete(documentToDelete.value.id)

    // Remove from list
    existingVisionDocuments.value = existingVisionDocuments.value.filter(
      d => d.id !== documentToDelete.value.id
    )

    // Close dialog
    showDeleteDocumentDialog.value = false
    documentToDelete.value = null

    // Show success toast
  } catch (error) {
    console.error('Failed to delete vision document:', error)
  }
}
```

### Phase 4: Details/Info Dialog (30 minutes)

**A. Add Details Dialog** (`ProductsView.vue`):

```vue
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
      <div class="text-caption text-medium-emphasis mb-4">
        ID: {{ selectedProduct.id }}
      </div>

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

            <v-list-item-title>{{ doc.filename }}</v-list-item-title>
            <v-list-item-subtitle>
              {{ doc.chunk_count }} chunks • {{ formatFileSize(doc.file_size) }}
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>

        <v-alert v-else type="info" variant="tonal" density="compact">
          No vision documents attached
        </v-alert>
      </div>

      <!-- Created/Updated -->
      <div class="text-caption text-medium-emphasis mt-4">
        Created: {{ formatDate(selectedProduct.created_at) }}<br>
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
```

**B. Add Method to Show Details**:

```javascript
const showDetailsDialog = ref(false)
const selectedProduct = ref(null)
const detailsVisionDocuments = ref([])

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
```

### Phase 5: Cascade Delete Warning (45 minutes)

**A. Add Backend Endpoint** (`api/endpoints/products.py`):

```python
@router.get("/{product_id}/cascade-impact")
async def get_cascade_impact(
    product_id: str,
    db: Session = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key)
):
    """Get cascade impact for deleting a product"""

    # Verify product exists and belongs to tenant
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_key == tenant_key
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Count projects
    projects_count = db.query(Project).filter(
        Project.product_id == product_id,
        Project.tenant_key == tenant_key
    ).count()

    # Count unfinished projects
    unfinished_projects = db.query(Project).filter(
        Project.product_id == product_id,
        Project.tenant_key == tenant_key,
        Project.status != 'completed'
    ).count()

    # Count tasks
    tasks_count = db.query(Task).filter(
        Task.product_id == product_id,
        Task.tenant_key == tenant_key
    ).count()

    # Count unresolved tasks
    unresolved_tasks = db.query(Task).filter(
        Task.product_id == product_id,
        Task.tenant_key == tenant_key,
        Task.status != 'completed'
    ).count()

    # Count vision documents
    vision_docs_count = db.query(VisionDocument).filter(
        VisionDocument.product_id == product_id,
        VisionDocument.tenant_key == tenant_key
    ).count()

    # Count total chunks
    total_chunks = db.query(MCPContextIndex).filter(
        MCPContextIndex.product_id == product_id,
        MCPContextIndex.tenant_key == tenant_key
    ).count()

    return {
        "product_id": product_id,
        "projects_count": projects_count,
        "unfinished_projects": unfinished_projects,
        "tasks_count": tasks_count,
        "unresolved_tasks": unresolved_tasks,
        "vision_documents_count": vision_docs_count,
        "total_chunks": total_chunks
    }
```

**B. Add Delete Confirmation Dialog** (`ProductsView.vue`):

```vue
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
          <div class="text-h6 mb-2">⚠️ THIS ACTION CANNOT BE UNDONE</div>
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
          <div class="text-subtitle-2 mb-2">
            Type the product name to confirm:
          </div>
          <v-text-field
            v-model="deleteConfirmationName"
            :placeholder="deletingProduct.name"
            variant="outlined"
            density="comfortable"
            :error="deleteConfirmationError"
            :error-messages="deleteConfirmationError ? 'Product name does not match' : ''"
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
      <v-btn
        variant="text"
        @click="cancelDelete"
        :disabled="deleting"
      >
        Cancel
      </v-btn>
      <v-btn
        color="error"
        variant="flat"
        @click="confirmDelete"
        :disabled="!isDeleteConfirmed || deleting"
        :loading="deleting"
      >
        Delete Forever
      </v-btn>
    </v-card-actions>
  </v-card>
</v-dialog>
```

**C. Add Delete Logic**:

```javascript
const showDeleteDialog = ref(false)
const deletingProduct = ref(null)
const cascadeImpact = ref(null)
const loadingCascadeImpact = ref(false)
const deleteConfirmationName = ref('')
const deleteConfirmationCheck = ref(false)
const deleteConfirmationError = ref(false)
const deleting = ref(false)

const isDeleteConfirmed = computed(() => {
  return deleteConfirmationName.value === deletingProduct.value?.name &&
         deleteConfirmationCheck.value
})

async function showDeleteConfirmation(product) {
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
  } finally {
    loadingCascadeImpact.value = false
  }
}

async function confirmDelete() {
  // Validate name match
  if (deleteConfirmationName.value !== deletingProduct.value.name) {
    deleteConfirmationError.value = true
    return
  }

  deleting.value = true
  try {
    await api.products.delete(deletingProduct.value.id)

    // Refresh products
    await productStore.fetchProducts()

    // If was active product, clear active state
    if (activeProductId.value === deletingProduct.value.id) {
      await productStore.clearActiveProduct()
      activeProductId.value = null
    }

    // Close dialog
    showDeleteDialog.value = false

    // Show success toast
  } catch (error) {
    console.error('Failed to delete product:', error)
    // Show error toast
  } finally {
    deleting.value = false
  }
}

function cancelDelete() {
  showDeleteDialog.value = false
  deletingProduct.value = null
  cascadeImpact.value = null
}
```

### Phase 6: Product-as-Context Implementation (1 hour)

**A. Update Product Store** (`frontend/src/stores/product.js`):

```javascript
export const useProductStore = defineStore('product', {
  state: () => ({
    products: [],
    currentProduct: null,
    currentProductId: null,
    loading: false
  }),

  actions: {
    async setActiveProduct(productId) {
      // Set in local state
      this.currentProductId = productId
      this.currentProduct = this.products.find(p => p.id === productId)

      // Persist to localStorage
      localStorage.setItem('activeProductId', productId)

      // Optional: POST to backend to save user preference
      // await api.post('/api/user/active-product', { product_id: productId })

      // Trigger reactive updates across app
      this.refreshActiveProductContext()
    },

    async clearActiveProduct() {
      this.currentProductId = null
      this.currentProduct = null
      localStorage.removeItem('activeProductId')
      this.refreshActiveProductContext()
    },

    async loadActiveProduct() {
      const savedId = localStorage.getItem('activeProductId')
      if (savedId) {
        await this.setActiveProduct(savedId)
      }
    },

    refreshActiveProductContext() {
      // Emit event for other components to listen
      window.dispatchEvent(new CustomEvent('active-product-changed', {
        detail: { productId: this.currentProductId }
      }))
    }
  },

  getters: {
    activeProductId: (state) => state.currentProductId,
    activeProduct: (state) => state.currentProduct,
    isProductActive: (state) => (productId) => {
      return state.currentProductId === productId
    }
  }
})
```

**B. Update Tasks View** (to filter by active product):

```javascript
// In TasksView.vue or similar
import { useProductStore } from '@/stores/product'

const productStore = useProductStore()

const filteredTasks = computed(() => {
  if (!productStore.activeProductId) {
    return tasks.value // Show all if no active product
  }

  return tasks.value.filter(task =>
    task.product_id === productStore.activeProductId
  )
})
```

**C. Update Projects View** (to filter by active product):

```javascript
// In ProjectsView.vue or similar
const filteredProjects = computed(() => {
  if (!productStore.activeProductId) {
    return projects.value
  }

  return projects.value.filter(project =>
    project.product_id === productStore.activeProductId
  )
})
```

### Phase 7: Delete Orphaned Code (15 minutes)

**A. Delete ProductSwitcher.vue**:

```bash
rm frontend/src/components/ProductSwitcher.vue
```

**B. Remove Imports**:

Search codebase for any remaining imports:
```bash
grep -r "ProductSwitcher" frontend/src/
```

Remove any found imports.

**C. Verify ActiveProductDisplay**:

Ensure `ActiveProductDisplay.vue` is properly integrated in `AppBar.vue`.

---

## Success Criteria

**Phase 1-2 (Product Creation)**:
- [ ] Product cards show only: Name, Unresolved Tasks, Unfinished Projects, Date Created, Vision Doc Count
- [ ] Active product has visual indicator (border/chip)
- [ ] Create dialog has Details + Vision Documents tabs
- [ ] Can upload multiple vision files during creation
- [ ] Files auto-chunk on backend
- [ ] Product appears in grid after creation

**Phase 3 (Product Editing)**:
- [ ] Edit dialog pre-populates name and description
- [ ] Shows existing vision documents
- [ ] Can add more vision documents
- [ ] Can remove existing documents (with confirmation)
- [ ] Removing file deletes chunks

**Phase 4 (Product Details)**:
- [ ] Info dialog shows all product details
- [ ] Lists all vision documents
- [ ] Shows statistics

**Phase 5 (Cascade Delete)**:
- [ ] Delete shows cascade impact counts
- [ ] Requires typing product name
- [ ] Requires checkbox confirmation
- [ ] Shows scary warning
- [ ] Deletes product + all related data

**Phase 6 (Product-as-Context)**:
- [ ] Activating product sets global context
- [ ] Tasks filtered to active product
- [ ] Projects filtered to active product
- [ ] ActiveProductDisplay shows current context
- [ ] Active product persists across sessions

**Phase 7 (Cleanup)**:
- [ ] ProductSwitcher.vue deleted
- [ ] No broken imports
- [ ] ActiveProductDisplay working

---

## Testing Checklist

### Manual Testing

**Product Creation**:
1. Click "+ New Product"
2. Fill name and description
3. Upload 2-3 vision documents
4. Click "Create Product"
5. Verify product appears in grid
6. Verify vision documents uploaded (check backend)

**Product Editing**:
1. Click "Edit" on product
2. Modify name/description
3. Remove one vision document
4. Add one new vision document
5. Save changes
6. Verify changes reflected

**Product Details**:
1. Click "Info (i)" on product
2. Verify all details shown
3. Verify vision documents listed

**Product Deletion**:
1. Click "Delete" on product with tasks/projects
2. Verify cascade impact shown correctly
3. Type wrong name → Verify "Delete" button disabled
4. Type correct name + check box → Verify button enabled
5. Click "Delete Forever"
6. Verify product deleted
7. Verify tasks/projects/docs deleted (check backend)

**Product-as-Context**:
1. Activate Product A
2. Go to Tasks → Verify only Product A tasks shown
3. Go to Projects → Verify only Product A projects shown
4. Activate Product B
5. Verify tasks/projects switch to Product B
6. Refresh page → Verify active product persists

### Integration Testing

**Backend Integration**:
- [ ] POST /api/products/ creates product
- [ ] POST /api/vision-documents/ uploads files
- [ ] Files auto-chunk (check vision_document_chunks table)
- [ ] GET /api/vision-documents/product/{id} lists files
- [ ] DELETE /api/vision-documents/{id} deletes file + chunks
- [ ] GET /api/products/{id}/cascade-impact returns correct counts
- [ ] DELETE /api/products/{id} cascades correctly

**Multi-Tenant Isolation**:
- [ ] Tenant A cannot see Tenant B's products
- [ ] Tenant A cannot delete Tenant B's products
- [ ] Vision documents isolated by tenant

---

## Rollback Strategy

**If Issues Arise**:

1. **Git Revert**:
   ```bash
   git log --oneline | head -10  # Find commit hash
   git revert <commit-hash>
   ```

2. **Restore ProductSwitcher**:
   ```bash
   git checkout HEAD~1 frontend/src/components/ProductSwitcher.vue
   ```

3. **Database Cleanup**:
   - No database changes in this handover
   - Safe to revert frontend only

---

## Dependencies and Blockers

**Prerequisites**:
- ✅ VisionDocument model exists (Handover 0043)
- ✅ Vision documents API exists (Handover 0043)
- ✅ Backend auto-chunking implemented
- ✅ Multi-tenant isolation configured
- ⚠️ Need to add GET /api/products/{id}/cascade-impact endpoint

**Blockers**:
- Need cascade impact API endpoint (15 minutes to implement)

---

## References

**Code Locations**:
- ProductsView: `F:\GiljoAI_MCP\frontend\src\views\ProductsView.vue`
- ProductSwitcher (orphaned): `F:\GiljoAI_MCP\frontend\src\components\ProductSwitcher.vue`
- ActiveProductDisplay: `F:\GiljoAI_MCP\frontend\src\components\ActiveProductDisplay.vue`
- Product Store: `F:\GiljoAI_MCP\frontend\src\stores\product.js`
- Vision API: `F:\GiljoAI_MCP\api\endpoints\vision_documents.py`
- Products API: `F:\GiljoAI_MCP\api\endpoints\products.py`

**Related Handovers**:
- 0043: Multi-Vision Document Support (backend foundation)
- 0041: Agent Template Management (similar modal patterns)

---

## Notes

**Why This Refactoring is Critical**:
- Users currently **cannot upload vision documents at all** (completely broken)
- Vision documents are essential for orchestrator context generation
- Product-as-context is core to the application architecture
- 928 lines of orphaned code causing confusion

**Design Decisions**:
- Single-step creation (better UX than two-step)
- Tabs for organization (Details vs Vision Docs)
- Scary delete confirmations (prevent accidents)
- Visual active product indicator (clear context)
- Products as "sub-tenants" (organizational structure)

---

## Acceptance Criteria

**Definition of Done**:
1. Users can create products with vision documents in single step
2. Users can edit products and manage vision documents
3. Users can view product details including vision files
4. Delete shows cascade impact and requires double confirmation
5. Activating product sets application-wide context
6. Tasks/projects filtered by active product
7. ProductSwitcher.vue deleted
8. All tests passing
9. No console errors
10. Multi-tenant isolation verified

**Ready for Production**:
- Clean, intuitive UI
- No orphaned code
- Proper context management
- Scary but safe delete flow
- Mobile responsive (Vuetify default)

---

**Last Updated**: 2025-01-24
**Next Steps**: Assign to Full-Stack Development Team for implementation
