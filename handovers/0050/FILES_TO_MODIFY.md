# Files to Modify: Single Active Product Architecture

**Handover**: 0050
**Total Files**: 8 (6 modified, 2 new)

---

## Backend Files (4 files)

### 1. `api/endpoints/products.py`

**Current Line Count**: ~700 lines
**Changes**: Add helper function + modify 2 endpoints
**Estimated LOC Change**: +80 lines

#### Change 1: Add Helper Function (Insert before line 563)

**Location**: Before `activate_product()` function
**Action**: INSERT NEW FUNCTION

```python
async def get_active_product_info(
    db: AsyncSession,
    tenant_key: str
) -> dict | None:
    """
    Get information about the currently active product.

    Returns dict with:
      - id: product UUID
      - name: product name
      - active_projects_count: number of projects with status='active'

    Returns None if no active product.
    """
    from sqlalchemy import func, select
    from src.giljo_mcp.models import Product, Project

    # Find currently active product
    result = await db.execute(
        select(Product)
        .where(
            Product.tenant_key == tenant_key,
            Product.is_active == True
        )
    )
    active_product = result.scalar_one_or_none()

    if not active_product:
        return None

    # Count active projects
    count_result = await db.execute(
        select(func.count(Project.id))
        .where(
            Project.product_id == active_product.id,
            Project.status == 'active'
        )
    )
    active_projects_count = count_result.scalar() or 0

    return {
        "id": str(active_product.id),
        "name": active_product.name,
        "active_projects_count": active_projects_count
    }
```

#### Change 2: Modify `activate_product()` (Lines 563-637)

**Location**: Line 583 (before deactivation query)
**Action**: INSERT CODE

```python
# Get currently active product info for warning response
current_active = await get_active_product_info(db, tenant_key)
```

**Location**: Line 617 (in return statement)
**Action**: MODIFY RETURN

**Find**:
```python
return ProductResponse(
    id=product.id,
    name=product.name,
    # ... existing fields
)
```

**Replace With**:
```python
return {
    **ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        vision_path=product.vision_path,
        created_at=product.created_at,
        updated_at=product.updated_at,
        project_count=len(projects),
        task_count=len(tasks),
        has_vision=bool(product.vision_path),
        unfinished_projects=unfinished_projects,
        unresolved_tasks=unresolved_tasks,
        vision_documents_count=vision_doc_count,
        config_data=product.config_data,
        has_config_data=product.has_config_data,
        is_active=product.is_active,
    ).dict(),
    "previous_active_product": current_active  # NEW FIELD
}
```

#### Change 3: Modify `delete_product()` (Find via search)

**Search For**: `@router.delete("/{product_id}")`
**Action**: MODIFY RETURN

**Find**:
```python
return {
    "success": True,
    "message": f"Product {product.name} deleted successfully"
}
```

**Replace With**:
```python
return {
    "success": True,
    "message": f"Product {product.name} deleted successfully",
    "was_active": product.is_active  # NEW FIELD
}
```

#### Change 4: Add New Endpoint (Insert after `delete_product()`)

**Location**: After `delete_product()` function
**Action**: INSERT NEW ENDPOINT

```python
@router.post("/refresh-active", response_model=dict)
async def refresh_active_product_store(
    tenant_key: str = Depends(get_tenant_key),
    current_user: User = Depends(get_current_active_user)
):
    """
    Force refresh of active product in frontend store.

    Called after product deletion to ensure store state is current.
    Returns currently active product or None.
    """
    from api.app import state
    from datetime import datetime

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    async with state.db_manager.get_session_async() as db:
        active_info = await get_active_product_info(db, tenant_key)
        return {
            "active_product": active_info,
            "timestamp": datetime.utcnow().isoformat()
        }
```

---

### 2. `api/endpoints/projects.py`

**Current Line Count**: ~600 lines
**Changes**: Add validation in project update
**Estimated LOC Change**: +20 lines

#### Change 1: Add Validation in Project Status Update

**Search For**: Function that handles project status updates (likely `update_project`)
**Location**: Where `status` field is being updated
**Action**: INSERT VALIDATION

**Insert Before Status Update**:
```python
# When changing status to 'active', validate parent product is active
if "status" in update_data and update_data["status"] == "active":
    from src.giljo_mcp.models import Product

    # Fetch parent product
    product_result = await db.execute(
        select(Product)
        .where(Product.id == project.product_id)
    )
    parent_product = product_result.scalar_one_or_none()

    if not parent_product:
        raise HTTPException(
            status_code=400,
            detail="Cannot activate project - parent product not found"
        )

    if not parent_product.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot activate project - parent product '{parent_product.name}' is not active. Please activate the product first."
        )
```

---

### 3. `src/giljo_mcp/agent_job_manager.py`

**Current Line Count**: ~500 lines
**Changes**: Add validation in job creation
**Estimated LOC Change**: +25 lines

#### Change 1: Validate Product Active Before Job Creation

**Search For**: `create_job` method (or similar)
**Location**: Beginning of method, after parameter validation
**Action**: INSERT VALIDATION

```python
async def create_job(
    self,
    agent_id: str,
    mission: str,
    product_id: str,
    tenant_key: str,
    **kwargs
) -> MCPAgentJob:
    """
    Create a new agent job.

    Validates that the product is active before creating job.
    """
    from src.giljo_mcp.models import Product
    from sqlalchemy import select

    async with self.db_manager.get_session_async() as db:
        # Validate product is active
        result = await db.execute(
            select(Product)
            .where(
                Product.id == product_id,
                Product.tenant_key == tenant_key
            )
        )
        product = result.scalar_one_or_none()

        if not product:
            raise ValueError(f"Product {product_id} not found")

        if not product.is_active:
            raise ValueError(
                f"Cannot create agent job - product '{product.name}' is not active. "
                f"Please activate the product before creating missions."
            )

        # ... existing job creation code
```

---

### 4. `src/giljo_mcp/orchestrator.py`

**Current Line Count**: ~1200 lines
**Changes**: Add validation in mission assignment
**Estimated LOC Change**: +20 lines

#### Change 1: Validate Product Before Mission Assignment

**Search For**: Method that assigns missions to agents (e.g., `assign_mission`, `spawn_agent`, etc.)
**Location**: Beginning of method
**Action**: INSERT VALIDATION

```python
async def assign_mission_to_agent(
    self,
    agent_id: str,
    mission: str,
    product_id: str,
    **kwargs
):
    """
    Assign a mission to an agent.

    Validates product is active before mission assignment.
    """
    from src.giljo_mcp.models import Product
    from sqlalchemy import select

    # Validate product is active
    async with self.db_manager.get_session_async() as db:
        result = await db.execute(
            select(Product)
            .where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()

        if not product or not product.is_active:
            raise ValueError(
                f"Cannot assign mission - product is not active. "
                f"Activate the product before creating agent missions."
            )

    # ... existing mission assignment code
```

---

## Frontend Files (4 files)

### 5. `frontend/src/components/products/ActivationWarningDialog.vue` (NEW FILE)

**Location**: Create new file
**Estimated LOC**: 120 lines
**Action**: CREATE NEW COMPONENT

**Full File Content**:
```vue
<template>
  <v-dialog v-model="isOpen" max-width="600" persistent>
    <v-card>
      <v-card-title class="text-h5 bg-warning">
        <v-icon class="mr-2">mdi-alert</v-icon>
        Confirm Product Activation
      </v-card-title>

      <v-card-text class="pt-4">
        <v-alert type="info" variant="tonal" class="mb-4">
          Activating <strong>{{ newProductName }}</strong> will deactivate
          <strong>{{ previousProduct.name }}</strong>.
        </v-alert>

        <div v-if="previousProduct.active_projects_count > 0" class="mb-4">
          <v-alert type="warning" variant="tonal">
            <strong>{{ previousProduct.name }}</strong> has
            <strong>{{ previousProduct.active_projects_count }}</strong>
            active project{{ previousProduct.active_projects_count > 1 ? 's' : '' }}.
            These projects will remain active but cannot be worked on until you
            reactivate their parent product.
          </v-alert>
        </div>

        <div class="text-body-2 grey--text">
          Only one product can be active at a time. This ensures AI agents
          receive focused context and optimal token budget allocation.
        </div>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="handleCancel" variant="text">
          Cancel
        </v-btn>
        <v-btn
          @click="handleConfirm"
          color="primary"
          variant="elevated"
        >
          Activate {{ newProductName }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  },
  newProductName: {
    type: String,
    required: true
  },
  previousProduct: {
    type: Object,
    required: true,
    validator: (val) => {
      return val && typeof val.name === 'string' &&
             typeof val.active_projects_count === 'number'
    }
  }
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const handleConfirm = () => {
  emit('confirm')
  isOpen.value = false
}

const handleCancel = () => {
  emit('cancel')
  isOpen.value = false
}
</script>
```

---

### 6. `frontend/src/views/ProductsView.vue`

**Current Line Count**: ~800 lines
**Changes**: Add warning dialog + modify activation logic
**Estimated LOC Change**: +100 lines

#### Change 1: Add Import

**Location**: Top of `<script setup>` section
**Action**: ADD IMPORT

```javascript
import ActivationWarningDialog from '@/components/products/ActivationWarningDialog.vue'
```

#### Change 2: Add State Variables

**Location**: After existing state declarations
**Action**: ADD STATE

```javascript
const showActivationWarning = ref(false)
const pendingActivation = ref(null)
const previousActiveProduct = ref(null)
```

#### Change 3: Replace `activateProduct` Function

**Search For**: `async function activateProduct(product)`
**Action**: REPLACE ENTIRE FUNCTION

```javascript
async function activateProduct(product) {
  loading.value = true
  error.value = null

  try {
    const response = await api.products.activateProduct(product.id)

    // Check if there was a previous active product
    if (response.data.previous_active_product) {
      // Show warning dialog
      pendingActivation.value = product
      previousActiveProduct.value = response.data.previous_active_product
      showActivationWarning.value = true

      // Revert optimistic update
      product.is_active = false
      loading.value = false
      return
    }

    // No previous active product - activation succeeded
    product.is_active = true
    await productsStore.fetchActiveProduct()
    success.value = `Product "${product.name}" activated successfully`
  } catch (err) {
    console.error('[PRODUCTS] Activation error:', err)
    error.value = err.response?.data?.detail || 'Failed to activate product'
    product.is_active = false
  } finally {
    loading.value = false
  }
}
```

#### Change 4: Add Confirmation Function

**Location**: After `activateProduct` function
**Action**: ADD NEW FUNCTIONS

```javascript
async function confirmActivation() {
  const product = pendingActivation.value
  loading.value = true

  try {
    await api.products.activateProduct(product.id)
    product.is_active = true

    // Deactivate previous product in UI
    const prevProduct = products.value.find(
      p => p.id === previousActiveProduct.value.id
    )
    if (prevProduct) {
      prevProduct.is_active = false
    }

    await productsStore.fetchActiveProduct()
    success.value = `Product "${product.name}" activated successfully`
  } catch (err) {
    console.error('[PRODUCTS] Activation confirmation error:', err)
    error.value = err.response?.data?.detail || 'Failed to activate product'
  } finally {
    loading.value = false
    pendingActivation.value = null
    previousActiveProduct.value = null
  }
}

function cancelActivation() {
  pendingActivation.value = null
  previousActiveProduct.value = null
}
```

#### Change 5: Modify `deleteProduct` Function

**Search For**: `async function deleteProduct(product)`
**Location**: After successful deletion
**Action**: ADD CODE

```javascript
const response = await api.products.deleteProduct(product.id)

// NEW: If deleted product was active, refresh store
if (response.data.was_active) {
  await productsStore.fetchActiveProduct()
  await api.products.refreshActiveProductStore()
}
```

#### Change 6: Add Component to Template

**Location**: Before closing `</template>` tag
**Action**: ADD COMPONENT

```vue
<!-- Add Warning Dialog -->
<ActivationWarningDialog
  v-model="showActivationWarning"
  :new-product-name="pendingActivation?.name || ''"
  :previous-product="previousActiveProduct || { name: '', active_projects_count: 0 }"
  @confirm="confirmActivation"
  @cancel="cancelActivation"
/>
```

---

### 7. `frontend/src/views/ProjectsView.vue`

**Current Line Count**: ~700 lines
**Changes**: Add validation for project activation
**Estimated LOC Change**: +50 lines

#### Change 1: Add Import

**Location**: Top of `<script setup>`
**Action**: ADD IMPORT

```javascript
import { useProductsStore } from '@/stores/products'
```

#### Change 2: Add Store and Computed

**Location**: After existing state
**Action**: ADD CODE

```javascript
const productsStore = useProductsStore()
const products = computed(() => productsStore.products)

const canActivateProject = computed(() => {
  return (project) => {
    const parentProduct = products.value.find(p => p.id === project.product_id)
    return parentProduct?.is_active === true
  }
})
```

#### Change 3: Modify `onMounted`

**Search For**: `onMounted(async () => {`
**Action**: ADD CODE

```javascript
onMounted(async () => {
  await productsStore.fetchProducts()  // NEW
  await projectsStore.fetchProjects()
  // ... existing code
})
```

#### Change 4: Update Activate Button in Template

**Search For**: Activate project button
**Action**: REPLACE BUTTON

**Find**:
```vue
<v-btn @click="activateProject(project)">
  Activate
</v-btn>
```

**Replace With**:
```vue
<v-btn
  @click="activateProject(project)"
  variant="elevated"
  color="primary"
  :disabled="!canActivateProject(project)"
>
  Activate
</v-btn>

<v-tooltip
  v-if="!canActivateProject(project)"
  activator="parent"
  location="top"
>
  Cannot activate project - parent product is not active.
  Activate the product first.
</v-tooltip>
```

---

### 8. `frontend/src/services/api.js`

**Current Line Count**: ~400 lines
**Changes**: Add new API method
**Estimated LOC Change**: +5 lines

#### Change 1: Add New Method to Products API

**Search For**: `products: {` section
**Location**: Inside products object
**Action**: ADD METHOD

```javascript
products: {
  // ... existing methods
  activateProduct: (id) => apiClient.post(`/api/v1/products/${id}/activate`),
  deleteProduct: (id) => apiClient.delete(`/api/v1/products/${id}`),
  refreshActiveProductStore: () => apiClient.post('/api/v1/products/refresh-active'),  // NEW
}
```

---

## Summary of Changes

### Backend (Python)
- **api/endpoints/products.py**: +80 lines (helper + 3 modifications)
- **api/endpoints/projects.py**: +20 lines (validation)
- **src/giljo_mcp/agent_job_manager.py**: +25 lines (validation)
- **src/giljo_mcp/orchestrator.py**: +20 lines (validation)

**Total Backend**: ~145 lines added

### Frontend (Vue/JavaScript)
- **ActivationWarningDialog.vue**: +120 lines (new file)
- **ProductsView.vue**: +100 lines (dialog integration)
- **ProjectsView.vue**: +50 lines (validation)
- **api.js**: +5 lines (new method)

**Total Frontend**: ~275 lines added

### Grand Total
**~420 lines of code** across 8 files (6 modified, 2 new)

---

## File Modification Checklist

**Phase 1 (Backend)**:
- [ ] `api/endpoints/products.py` - Add helper + modify endpoints
- [ ] Test helper function works

**Phase 2 (Frontend Warning)**:
- [ ] Create `ActivationWarningDialog.vue`
- [ ] Update `ProductsView.vue` - Import + state + functions
- [ ] Update `api.js` - Add refresh method
- [ ] Test warning dialog appears

**Phase 3 (Project Validation)**:
- [ ] `api/endpoints/projects.py` - Add validation
- [ ] `ProjectsView.vue` - Disable button + tooltip
- [ ] Test button disables correctly

**Phase 4 (Agent Safety)**:
- [ ] `src/giljo_mcp/agent_job_manager.py` - Add validation
- [ ] `src/giljo_mcp/orchestrator.py` - Add validation
- [ ] Test validations trigger

**Phase 5 (Testing)**:
- [ ] All files reviewed and tested
- [ ] Integration tests pass

---

**End of Files to Modify**
