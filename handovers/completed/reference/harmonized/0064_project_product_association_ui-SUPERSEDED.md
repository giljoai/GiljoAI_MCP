---
Handover 0064: Project-Product Association UI
Date: 2025-10-27
Status: SUPERSEDED (see Superseded Notice)
Priority: HIGH
Complexity: LOW
Duration: 3-4 hours
---

Superseded Notice

This handover is superseded by the current Projects View flow which uses Active Product gating instead of an explicit product selector in the project form.

- Current behavior: project creation implicitly associates to the active product; no selector in dialog.
- Rationale: simplifies UX and aligns with Single Active Product and Projects View v2 patterns.
- See: docs/features/projects_view_v2.md and docs/api/projects_endpoints.md.

# Executive Summary

The GiljoAI MCP Server currently requires projects to be created manually with product_id passed explicitly. This handover adds a product selector dropdown to the project creation UI, making it intuitive and explicit which product a project belongs to.

**Key Principle**: Project-product relationships should be established at creation time through clear UI controls, not inferred or set later.

The system will add a product dropdown to the project creation form, validate the selected product is active, and provide clear visual feedback about the product-project relationship.

---

# Problem Statement

## Current State

Project creation lacks explicit product selection:
- No product selector in project creation form
- Product ID passed implicitly or requires manual input
- Users unclear which product a project will belong to
- No validation that selected product is active
- Poor discoverability of project-product relationship

## Gaps Without This Implementation

1. **No Product Selection**: Can't choose product when creating project
2. **Confusing UX**: Unclear which product project belongs to
3. **No Validation**: Can create project under inactive product
4. **Manual Workarounds**: Users must track product IDs manually
5. **Error-Prone**: Easy to associate project with wrong product

---

# Implementation Plan

## Overview

This implementation adds a product selector dropdown to the project creation form, with validation and clear visual feedback. Simple UI enhancement with minimal backend changes.

**Total Estimated Lines of Code**: ~150 lines across 3 files

## Phase 1: Backend - Validation Enhancement (1 hour)

**File**: `api/endpoints/projects.py`

**Enhance Create Project Validation**:

```python
from pydantic import BaseModel, validator
from typing import Optional

class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None
    product_id: str  # REQUIRED - no longer optional

    @validator('product_id')
    def validate_product_id(cls, v):
        """Ensure product_id is provided."""
        if not v or v.strip() == '':
            raise ValueError('product_id is required')
        return v


@router.post("/", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    tenant_key: str = Depends(get_tenant_key),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new project under a specific product.

    Validates:
    - Product exists
    - Product belongs to tenant
    - Product is active (warning if not)
    """
    from sqlalchemy import select
    from src.giljo_mcp.models import Product, Project

    # Validate product exists and belongs to tenant
    result = await db.execute(
        select(Product).where(
            Product.id == request.product_id,
            Product.tenant_key == tenant_key
        )
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product not found or does not belong to your tenant"
        )

    # Warning if product is not active (but allow creation)
    product_active_warning = None
    if not product.is_active:
        product_active_warning = (
            f"Warning: Product '{product.name}' is not currently active. "
            f"Projects under inactive products cannot be activated until the product is activated."
        )

    # Create project
    project = Project(
        name=request.name,
        description=request.description,
        product_id=request.product_id,
        tenant_key=tenant_key,
        status='pending'
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    response_data = {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "product_id": str(project.product_id),
        "product_name": product.name,
        "status": project.status,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat()
    }

    if product_active_warning:
        response_data["warning"] = product_active_warning

    return response_data
```

## Phase 2: Frontend - Product Selector Component (1-2 hours)

**File**: `frontend/src/components/projects/ProjectFormDialog.vue`

**Enhance Form with Product Selector**:

```vue
<template>
  <v-dialog v-model="isOpen" max-width="600" persistent>
    <v-card>
      <v-card-title class="text-h5">
        {{ isEditing ? 'Edit Project' : 'Create New Project' }}
      </v-card-title>

      <v-card-text>
        <v-form ref="form" v-model="valid">
          <!-- Project Name -->
          <v-text-field
            v-model="formData.name"
            label="Project Name"
            :rules="[rules.required]"
            prepend-icon="mdi-folder"
            class="mb-4"
          />

          <!-- Project Description -->
          <v-textarea
            v-model="formData.description"
            label="Description"
            rows="3"
            prepend-icon="mdi-text"
            class="mb-4"
          />

          <!-- NEW: Product Selector -->
          <v-select
            v-model="formData.product_id"
            :items="products"
            item-title="name"
            item-value="id"
            label="Product"
            :rules="[rules.required]"
            prepend-icon="mdi-package"
            :loading="loadingProducts"
            :disabled="isEditing"
            hint="Projects belong to a product and inherit its context"
            persistent-hint
            class="mb-4"
          >
            <template v-slot:item="{ props, item }">
              <v-list-item v-bind="props">
                <template v-slot:append>
                  <v-chip
                    v-if="item.raw.is_active"
                    size="small"
                    color="success"
                  >
                    Active
                  </v-chip>
                  <v-chip
                    v-else
                    size="small"
                    color="grey"
                  >
                    Inactive
                  </v-chip>
                </template>

                <v-list-item-subtitle v-if="!item.raw.is_active">
                  Product must be active to activate projects
                </v-list-item-subtitle>
              </v-list-item>
            </template>

            <template v-slot:selection="{ item }">
              <v-chip
                :color="item.raw.is_active ? 'success' : 'grey'"
                :prepend-icon="item.raw.is_active ? 'mdi-check-circle' : 'mdi-alert-circle'"
              >
                {{ item.raw.name }}
              </v-chip>
            </template>
          </v-select>

          <!-- Warning for inactive product -->
          <v-alert
            v-if="selectedProduct && !selectedProduct.is_active"
            type="warning"
            variant="tonal"
            density="compact"
            class="mb-4"
          >
            <strong>{{ selectedProduct.name }}</strong> is not currently active.
            You can create the project, but it cannot be activated until you activate the product.
          </v-alert>

          <!-- No products warning -->
          <v-alert
            v-if="!loadingProducts && products.length === 0"
            type="info"
            variant="tonal"
            density="compact"
            class="mb-4"
          >
            No products found. Please create a product first.
            <router-link to="/products" class="ml-2">
              Go to Products
            </router-link>
          </v-alert>

          <!-- Error message -->
          <v-alert
            v-if="errorMessage"
            type="error"
            variant="tonal"
            density="compact"
            class="mb-4"
          >
            {{ errorMessage }}
          </v-alert>
        </v-form>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          @click="closeDialog"
          variant="text"
          :disabled="loading"
        >
          Cancel
        </v-btn>
        <v-btn
          @click="saveProject"
          color="primary"
          variant="elevated"
          :loading="loading"
          :disabled="!valid || products.length === 0"
        >
          {{ isEditing ? 'Save' : 'Create' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import api from '@/services/api'
import { useProductsStore } from '@/stores/products'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  },
  project: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'saved'])

const productsStore = useProductsStore()

const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const isEditing = computed(() => !!props.project)

const form = ref(null)
const valid = ref(false)
const loading = ref(false)
const loadingProducts = ref(false)
const errorMessage = ref('')

const formData = ref({
  name: '',
  description: '',
  product_id: null
})

const products = ref([])

const selectedProduct = computed(() => {
  if (!formData.value.product_id) return null
  return products.value.find(p => p.id === formData.value.product_id)
})

const rules = {
  required: (v) => !!v || 'This field is required'
}

watch(isOpen, (newVal) => {
  if (newVal) {
    resetForm()
    fetchProducts()
    if (props.project) {
      loadProjectData()
    }
  }
})

function resetForm() {
  formData.value = {
    name: '',
    description: '',
    product_id: null
  }
  errorMessage.value = ''
}

function loadProjectData() {
  formData.value = {
    name: props.project.name,
    description: props.project.description,
    product_id: props.project.product_id
  }
}

async function fetchProducts() {
  loadingProducts.value = true
  try {
    await productsStore.fetchProducts()
    products.value = productsStore.products
  } catch (error) {
    console.error('[PROJECT FORM] Error fetching products:', error)
    errorMessage.value = 'Failed to load products'
  } finally {
    loadingProducts.value = false
  }
}

async function saveProject() {
  if (!valid.value) return

  loading.value = true
  errorMessage.value = ''

  try {
    let response
    if (isEditing.value) {
      response = await api.projects.updateProject(props.project.id, formData.value)
    } else {
      response = await api.projects.createProject(formData.value)
    }

    // Show warning if product is inactive
    if (response.data.warning) {
      // Could show a separate warning dialog or snackbar
      console.warn('[PROJECT FORM]', response.data.warning)
    }

    emit('saved', response.data)
    closeDialog()
  } catch (error) {
    console.error('[PROJECT FORM] Save error:', error)
    errorMessage.value = error.response?.data?.detail || 'Failed to save project'
  } finally {
    loading.value = false
  }
}

function closeDialog() {
  isOpen.value = false
}

onMounted(() => {
  fetchProducts()
})
</script>
```

## Phase 3: Display Product in Project Lists (30 minutes)

**File**: `frontend/src/views/ProjectsView.vue`

**Enhance Project Cards/List to Show Product**:

```vue
<!-- In project card/list item -->
<v-list-item-subtitle>
  <v-icon size="small" class="mr-1">mdi-package</v-icon>
  Product: <strong>{{ project.product_name }}</strong>
  <v-chip
    v-if="getProductStatus(project.product_id)"
    size="x-small"
    :color="getProductStatus(project.product_id).is_active ? 'success' : 'grey'"
    class="ml-2"
  >
    {{ getProductStatus(project.product_id).is_active ? 'Active' : 'Inactive' }}
  </v-chip>
</v-list-item-subtitle>
```

**Add Helper**:

```javascript
import { useProductsStore } from '@/stores/products'

const productsStore = useProductsStore()

function getProductStatus(productId) {
  return productsStore.products.find(p => p.id === productId) || null
}

onMounted(async () => {
  await productsStore.fetchProducts()  // Ensure products loaded
  await projectsStore.fetchProjects()
})
```

---

# Files to Modify

1. **api/endpoints/projects.py** (+40 lines)
   - Enhance create_project validation
   - Add product active warning
   - Include product_name in response

2. **frontend/src/components/projects/ProjectFormDialog.vue** (+80 lines)
   - Add product selector dropdown
   - Add product status indicators
   - Add inactive product warning
   - Add no products warning

3. **frontend/src/views/ProjectsView.vue** (+30 lines)
   - Display product name and status in project lists
   - Add getProductStatus helper
   - Fetch products on mount

**Total**: ~150 lines across 3 files

---

# Success Criteria

## Functional Requirements
- Product selector dropdown in project creation form
- Products listed with active/inactive status
- Cannot edit product association after creation
- Validation ensures product exists and belongs to tenant
- Warning shown when selecting inactive product (but allows creation)
- Project lists show product name and status
- Empty state when no products exist

## User Experience Requirements
- Clear visual distinction between active/inactive products
- Helpful hint text explaining product-project relationship
- Warning for inactive products is informative but not blocking
- Link to products view when no products exist
- Smooth form validation

## Technical Requirements
- Multi-tenant isolation enforced
- Product validation on backend
- Proper error handling
- Product selector disabled when editing (product immutable)
- Efficient product loading (reuse store)

---

# Related Handovers

- **Handover 0050**: Single Active Product Architecture (RELATES TO)
  - Projects can only be activated if parent product is active

- **Handover 0062**: Enhanced Agent Cards with Project Context (RELATES TO)
  - Agent cards show project-product relationships

---

# Risk Assessment

**Complexity**: LOW (simple UI enhancement)
**Risk**: LOW (validation only, no schema changes)
**Breaking Changes**: None (product_id already required)
**Performance Impact**: None

---

# Timeline Estimate

**Phase 1**: 1 hour (Backend validation)
**Phase 2**: 1-2 hours (Product selector UI)
**Phase 3**: 30 minutes (Display in lists)

**Total**: 3-4 hours for experienced developer

---

**Decision Recorded By**: System Architect
**Date**: 2025-10-27
**Priority**: HIGH (improves UX and data integrity)

---

**End of Handover 0064**
