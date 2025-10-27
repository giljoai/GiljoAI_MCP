# Implementation Plan: Single Active Product Architecture

**Handover**: 0050
**Estimated Duration**: 2-3 days
**Complexity**: LOW
**Risk**: LOW

## Overview

This implementation follows a 5-phase approach, building from backend validation to frontend user experience. Each phase is independently testable and can be deployed incrementally if needed.

---

## Phase 1: Backend - Product Activation Rules

**Duration**: 4 hours
**Files Modified**: 1
**Risk**: LOW

### Objective

Ensure only one product can be active per tenant, with proper deactivation of other products and refresh of active product store state.

### Implementation Steps

#### Step 1.1: Modify Product Activation Endpoint

**File**: `api/endpoints/products.py`
**Function**: `activate_product()` (lines 563-637)

**Current Behavior**:
```python
# Deactivate all other products in the tenant
await db.execute(
    update(Product)
    .where(Product.tenant_key == tenant_key, Product.id != product_id)
    .values(is_active=False)
)

# Activate this product
product.is_active = True
await db.commit()
```

**Issue**: This ALREADY deactivates other products, but frontend doesn't know which product was deactivated or if it had active projects.

**Change Required**:
Add a helper function `get_active_product_info()` that returns:
- Currently active product ID
- Currently active product name
- Count of active projects under that product

**New Code to Add** (before `activate_product` function):

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

**Modify `activate_product` function**:

Add this BEFORE the deactivation query:

```python
# Get currently active product info for warning response
current_active = await get_active_product_info(db, tenant_key)
```

Add this to the RETURN statement (after the existing ProductResponse):

```python
return {
    **ProductResponse(
        id=product.id,
        name=product.name,
        # ... existing fields
    ).dict(),
    "previous_active_product": current_active  # NEW
}
```

**Expected Behavior**:
API response now includes `previous_active_product` field with info about the product that was just deactivated.

#### Step 1.2: Modify Product Deletion Endpoint

**File**: `api/endpoints/products.py`
**Function**: `delete_product()` (find using search)

**Search for the function**:
```python
@router.delete("/{product_id}")
async def delete_product(...)
```

**Change Required**:
After successful deletion, if the deleted product was active, return a flag indicating the active product state was cleared.

**Add to response**:
```python
return {
    "success": True,
    "message": f"Product {product.name} deleted successfully",
    "was_active": product.is_active  # NEW - frontend needs this
}
```

**Expected Behavior**:
Frontend knows if it needs to refresh the active product indicator.

#### Step 1.3: Add Endpoint to Refresh Active Product Store

**File**: `api/endpoints/products.py`

**New Endpoint** (add near the top, after imports):

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

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    async with state.db_manager.get_session_async() as db:
        active_info = await get_active_product_info(db, tenant_key)
        return {
            "active_product": active_info,
            "timestamp": datetime.utcnow().isoformat()
        }
```

**Expected Behavior**:
Frontend can call this endpoint after deletion to get current active product state.

### Testing Phase 1

**Unit Tests** (create `tests/api/test_product_activation_rules.py`):
1. Test `get_active_product_info()` with no active product
2. Test `get_active_product_info()` with active product and 0 projects
3. Test `get_active_product_info()` with active product and 2 active projects
4. Test `activate_product()` returns `previous_active_product`
5. Test `activate_product()` when no previous active product
6. Test multi-tenant isolation (tenant A can't see tenant B's active product)
7. Test `delete_product()` returns `was_active=True` when deleting active product
8. Test `refresh_active_product_store()` endpoint

**Manual Test**:
```bash
# Activate Product A
curl -X POST http://localhost:7272/api/v1/products/{product_a_id}/activate \
  -H "Cookie: access_token=$TOKEN"
# Should return: previous_active_product: null

# Activate Product B
curl -X POST http://localhost:7272/api/v1/products/{product_b_id}/activate \
  -H "Cookie: access_token=$TOKEN"
# Should return: previous_active_product: {id: product_a_id, name: "Product A", active_projects_count: 0}
```

**Success Criteria**:
- [x] `get_active_product_info()` returns correct data
- [x] `activate_product()` includes `previous_active_product` in response
- [x] `delete_product()` includes `was_active` flag
- [x] `refresh_active_product_store()` endpoint works
- [x] All unit tests pass

---

## Phase 2: Frontend - Activation Warnings

**Duration**: 4-6 hours
**Files Modified**: 2 (new component + ProductsView update)
**Risk**: LOW

### Objective

Warn users before activating a product that will deactivate another product, showing impact on active projects.

### Implementation Steps

#### Step 2.1: Create Warning Dialog Component

**File**: `frontend/src/components/products/ActivationWarningDialog.vue` (NEW)

**Full Component**:

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

#### Step 2.2: Update ProductsView to Use Warning Dialog

**File**: `frontend/src/views/ProductsView.vue`

**Add Import**:
```javascript
import ActivationWarningDialog from '@/components/products/ActivationWarningDialog.vue'
```

**Add Component Registration**:
```javascript
// In <script setup>
// (Component auto-registered in Vue 3 with <script setup>)
```

**Add State Variables**:
```javascript
const showActivationWarning = ref(false)
const pendingActivation = ref(null)  // Product to be activated
const previousActiveProduct = ref(null)  // Product that will be deactivated
```

**Replace Existing `activateProduct` Function**:

**Find**:
```javascript
async function activateProduct(product) {
  // ... existing code
}
```

**Replace With**:
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

      // Revert optimistic update (user needs to confirm)
      product.is_active = false
      loading.value = false
      return
    }

    // No previous active product - activation succeeded
    product.is_active = true

    // Refresh active product in store
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

async function confirmActivation() {
  // User confirmed - proceed with activation
  const product = pendingActivation.value

  loading.value = true
  try {
    // Call API again to actually activate
    await api.products.activateProduct(product.id)

    // Update UI state
    product.is_active = true

    // Deactivate previous product in UI
    const prevProduct = products.value.find(
      p => p.id === previousActiveProduct.value.id
    )
    if (prevProduct) {
      prevProduct.is_active = false
    }

    // Refresh active product in store
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
  // User cancelled - reset state
  pendingActivation.value = null
  previousActiveProduct.value = null
}
```

**Add Component to Template**:
```vue
<template>
  <!-- Existing template content -->

  <!-- Add Warning Dialog -->
  <ActivationWarningDialog
    v-model="showActivationWarning"
    :new-product-name="pendingActivation?.name || ''"
    :previous-product="previousActiveProduct || { name: '', active_projects_count: 0 }"
    @confirm="confirmActivation"
    @cancel="cancelActivation"
  />
</template>
```

#### Step 2.3: Handle Product Deletion State Refresh

**File**: `frontend/src/views/ProductsView.vue`

**Modify `deleteProduct` Function**:

**Find**:
```javascript
async function deleteProduct(product) {
  // ... existing deletion code
  await api.products.deleteProduct(product.id)
  // ...
}
```

**Add After Successful Deletion**:
```javascript
const response = await api.products.deleteProduct(product.id)

// If deleted product was active, refresh store
if (response.data.was_active) {
  await productsStore.fetchActiveProduct()
  await api.products.refreshActiveProductStore()
}
```

### Testing Phase 2

**Manual Tests**:
1. **Test Warning Dialog Appears**:
   - Activate Product A
   - Try to activate Product B
   - Verify warning dialog shows with Product A info
   - Click "Cancel" - Product A remains active
   - Click "Activate Product B" - Product B becomes active

2. **Test Active Projects Count**:
   - Activate Product A
   - Create 2 projects under Product A, mark both as active
   - Activate Product B
   - Verify warning shows "Product A has 2 active projects"

3. **Test Delete Active Product**:
   - Activate Product A
   - Delete Product A
   - Verify top bar updates to "No Active Product"

**Success Criteria**:
- [x] Warning dialog appears when activating product that deactivates another
- [x] Active projects count shown in warning
- [x] Confirming activation updates UI correctly
- [x] Cancelling activation leaves state unchanged
- [x] Deleting active product refreshes store

---

## Phase 3: Project Validation

**Duration**: 3 hours
**Files Modified**: 2 (projects.py backend + ProjectsView.vue frontend)
**Risk**: LOW

### Objective

Ensure projects can only be activated if their parent product is active.

### Implementation Steps

#### Step 3.1: Add Backend Validation

**File**: `api/endpoints/projects.py`

**Find Project Update/Activation Endpoint**:
Search for function that updates project status.

**Add Validation Before Status Change**:

```python
# When changing status to 'active', validate parent product is active
if new_status == 'active':
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

#### Step 3.2: Update Frontend Projects View

**File**: `frontend/src/views/ProjectsView.vue`

**Add Computed Property for Button State**:

```javascript
const canActivateProject = computed(() => {
  return (project) => {
    // Find parent product
    const parentProduct = products.value.find(p => p.id === project.product_id)

    // Can activate if parent product is active
    return parentProduct?.is_active === true
  }
})
```

**Update Activate Button in Template**:

**Find**:
```vue
<v-btn
  @click="activateProject(project)"
  variant="elevated"
  color="primary"
>
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

**Add Products State**:
```javascript
import { useProductsStore } from '@/stores/products'

const productsStore = useProductsStore()
const products = computed(() => productsStore.products)

// Load products on mount
onMounted(async () => {
  await productsStore.fetchProducts()
  await projectsStore.fetchProjects()
})
```

### Testing Phase 3

**Unit Tests** (`tests/api/test_project_activation_validation.py`):
1. Test activating project with active parent product (SUCCESS)
2. Test activating project with inactive parent product (400 error)
3. Test activating project with no parent product (400 error)
4. Test multi-tenant isolation

**Manual Tests**:
1. **Test Button Disabled**:
   - Create Product A (not active)
   - Create Project X under Product A
   - Go to Projects view
   - Verify "Activate" button is disabled for Project X
   - Hover over button - verify tooltip appears

2. **Test Button Enabled**:
   - Activate Product A
   - Refresh Projects view
   - Verify "Activate" button is enabled for Project X
   - Click activate - should succeed

3. **Test API Validation**:
   - Deactivate Product A
   - Use API directly to try activating Project X
   - Verify 400 error with message about inactive parent

**Success Criteria**:
- [x] Backend validates parent product is active
- [x] Frontend disables button when parent inactive
- [x] Tooltip explains why button is disabled
- [x] Button enables when parent activated
- [x] All tests pass

---

## Phase 4: Agent Job Safety

**Duration**: 2 hours
**Files Modified**: 2 (agent_job_manager.py + orchestrator.py)
**Risk**: LOW

### Objective

Ensure agent jobs validate product is active before creation and mission assignment.

### Implementation Steps

#### Step 4.1: Add Validation to Agent Job Manager

**File**: `src/giljo_mcp/agent_job_manager.py`

**Find Job Creation Method**:
Search for `create_job` or similar method.

**Add Validation**:

```python
async def create_job(
    self,
    agent_id: str,
    mission: str,
    product_id: str,  # ENSURE THIS PARAMETER EXISTS
    tenant_key: str,
    **kwargs
) -> MCPAgentJob:
    """
    Create a new agent job.

    Validates that the product is active before creating job.
    """
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

        # Proceed with job creation
        job = MCPAgentJob(
            agent_id=agent_id,
            mission=mission,
            product_id=product_id,
            tenant_key=tenant_key,
            status='pending',
            **kwargs
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job
```

#### Step 4.2: Add Validation to Orchestrator

**File**: `src/giljo_mcp/orchestrator.py`

**Find Mission Assignment Method**:
Search for methods that assign missions to agents.

**Add Validation Before Mission Assignment**:

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

    # Proceed with mission assignment
    # ... existing code
```

### Testing Phase 4

**Unit Tests** (`tests/unit/test_agent_job_product_validation.py`):
1. Test job creation with active product (SUCCESS)
2. Test job creation with inactive product (ValueError)
3. Test mission assignment with active product (SUCCESS)
4. Test mission assignment with inactive product (ValueError)
5. Test multi-tenant isolation

**Manual Test**:
```python
# In Python shell or test script
from src.giljo_mcp.agent_job_manager import AgentJobManager

manager = AgentJobManager(db_manager)

# Create product, don't activate
product = await create_product(name="Test", tenant_key="tenant1")

# Try to create job - should raise ValueError
try:
    await manager.create_job(
        agent_id="agent1",
        mission="Test mission",
        product_id=str(product.id),
        tenant_key="tenant1"
    )
    print("ERROR: Should have raised ValueError")
except ValueError as e:
    print(f"SUCCESS: {e}")
```

**Success Criteria**:
- [x] Agent job creation validates product is active
- [x] Mission assignment validates product is active
- [x] ValueError raised with clear message when product inactive
- [x] All tests pass

---

## Phase 5: Testing & Documentation

**Duration**: 4 hours
**Files Modified**: Multiple (docs, tests)
**Risk**: LOW

### Objective

Comprehensive testing and documentation of single active product architecture.

### Implementation Steps

#### Step 5.1: Integration Testing

**Create**: `tests/integration/test_single_active_product_flow.py`

**Test Scenarios** (see TESTING.md for details):
1. Activate Product A → Verify top bar
2. Activate Product B → Verify warning → Confirm → Verify A deactivated
3. Create Project under A → Activate A → Activate Project → Success
4. Deactivate A → Try activate Project → Should fail
5. Delete active Product → Verify top bar clears
6. Multi-tenant isolation

#### Step 5.2: Update Documentation

**Files to Update**:

1. **CLAUDE.md**:
   ```markdown
   ## v3.0 Unified Architecture

   - ✅ Single Active Product (Handover 0050) - Only one product active per tenant
   - ✅ Product activation with warning dialogs
   - ✅ Project validation (parent product must be active)
   - ✅ Agent job validation (product must be active)
   ```

2. **docs/TECHNICAL_ARCHITECTURE.md**:
   Add section:
   ```markdown
   ## Single Active Product Architecture

   Only ONE product can be active per tenant at any time. This ensures:
   - Focused agent context (70% token reduction)
   - Clear user mental model
   - Token budget consistency (2000 tokens per product)
   - MCP tool simplicity

   See: handovers/0050/ARCHITECTURE_DECISION.md
   ```

3. **User Guide** (create `docs/guides/ACTIVE_PRODUCT_GUIDE.md`):
   - What is an active product?
   - How to activate/deactivate products
   - What happens when you switch?
   - Why only one can be active

4. **API Documentation**:
   Update endpoint docs for:
   - `POST /api/v1/products/{id}/activate` (new response fields)
   - `DELETE /api/v1/products/{id}` (new `was_active` field)
   - `POST /api/v1/products/refresh-active` (new endpoint)

#### Step 5.3: Create Handover Completion Summary

**Create**: `handovers/completed/0050_COMPLETION_SUMMARY.md`

Follow format from Handover 0048 completion summary (see handovers/completed/0048_COMPLETION_SUMMARY.md).

Include:
- Implementation summary
- Files modified/created
- Testing results
- Known issues
- Lessons learned

### Testing Phase 5

**Full System Test**:
1. Run all unit tests: `pytest tests/unit/`
2. Run all API tests: `pytest tests/api/`
3. Run integration tests: `pytest tests/integration/`
4. Manual UAT (see TESTING.md)

**Success Criteria**:
- [x] All tests pass (unit, API, integration)
- [x] Manual UAT scenarios complete
- [x] Documentation updated
- [x] Completion summary created
- [x] Handover moved to completed/

---

## Rollback Plan

If issues arise during implementation:

### Phase 1 Rollback
```bash
git revert <commit-hash>
```
No database changes, simple code revert.

### Phase 2 Rollback
```bash
git revert <commit-hash>
rm frontend/src/components/products/ActivationWarningDialog.vue
```

### Phase 3 Rollback
Remove validation checks, restore original button state.

### Phase 4 Rollback
Remove validation from agent job manager and orchestrator.

### Phase 5 Rollback
Revert documentation changes.

**Risk**: LOW - All changes are additive, no schema changes, no data migration.

---

## Dependencies

**Before Starting**:
- Handover 0049 complete (active product indicator exists)
- Product activation endpoint exists
- Projects view exists

**External Dependencies**:
None (all work internal to codebase)

---

## Sign-Off Checklist

After completing all 5 phases:
- [ ] All code changes committed
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Manual UAT complete
- [ ] Completion summary written
- [ ] Handover moved to `handovers/completed/0050_HANDOVER_SINGLE_ACTIVE_PRODUCT_ARCHITECTURE-C.md`

---

**End of Implementation Plan**
