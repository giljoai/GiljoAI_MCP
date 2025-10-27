---
Handover 0050: Single Active Product Architecture
Date: 2025-01-27
Status: Ready for Implementation
Priority: HIGH
Complexity: LOW
Duration: 2-3 days
---

# Executive Summary

The GiljoAI MCP Server currently allows products to be activated but lacks enforcement that only ONE product can be active per tenant at any time. This handover implements architectural safeguards to ensure a single active product per tenant, with proper warnings, validations, and UI controls. This prevents risks in MCP communication, agent coordination, and token budget management.

**Key Principle**: Mission-based orchestration operates on a single product context. Multiple active products would dilute the 70% token reduction achieved through focused context delivery.

The system will enforce mutual exclusivity through backend validation, warn users before switching products, disable project activation when parent product is inactive, and validate product activation before agent job creation.

---

# Problem Statement

## Current State

The system allows any product to be activated through the UI or API:
- No validation prevents multiple products from being marked `is_active=True`
- Users can accidentally activate multiple products
- No warning when activating a new product that would deactivate another
- Project activation doesn't validate parent product is active
- Agent jobs don't verify product is active before mission assignment

## Risks Without This Implementation

1. **Broken MCP Communication**: Tools designed for single product context receive mixed signals
2. **Token Budget Confusion**: 2000 token budget is product-specific, not shared across products
3. **Mission Integrity**: Agents could receive missions referencing wrong product's vision/config
4. **User Mental Model**: Unclear which product's context is "active" for orchestration
5. **Data Integrity**: Database allows multiple `is_active=True` products per tenant

---

# Architectural Decision

## Decision Context

The GiljoAI MCP Server orchestrates AI agents using mission-based architecture where agents operate on a focused product context. The current implementation allows products to be marked active but lacks enforcement of mutual exclusivity.

### Current System Behavior

1. **Database Schema**: `products.is_active` BOOLEAN field exists
2. **No Constraint**: Database allows multiple products with `is_active=True` per tenant
3. **UI Behavior**: Product activation toggle works but no warnings
4. **API Behavior**: `POST /products/{id}/activate` sets one product active but doesn't clear others
5. **Orchestration**: Mission planner expects single product context

## Options Considered

### Option A: Single Active Product + Single Active Project (SELECTED)

**Architecture**:
- Only ONE product active per tenant at any time
- Only ONE project active per product at any time
- Activating a product deactivates all others
- Activating a project requires parent product to be active

**Enforcement**:
- Backend validation in activation endpoints
- Frontend warning dialogs before state change
- UI controls disabled when preconditions not met

**User Experience**:
```
User activates Product B
  → Warning: "This will deactivate Product A (which has 2 active projects)"
  → User confirms
  → Product A deactivated, Product B activated
  → Top bar updates to "Active: Product B"
```

**Pros**:
- Clean mental model (one focus at a time)
- Aligns with mission-based orchestration design
- Simple implementation (validation + warnings)
- No database schema changes needed
- Prevents token budget confusion
- MCP tools receive consistent context

**Cons**:
- User must manually switch between products
- Can't compare two products side-by-side in agent context
- Switching products deactivates current projects

**Complexity**: LOW
**Implementation Time**: 2-3 days
**Risk**: LOW (additive changes only)

### Option B: Multiple Active Products + Priority System

**Architecture**:
- Multiple products can be active simultaneously
- Each product has a priority level (1-10)
- Highest priority product is "primary" for orchestration
- Mission planner uses primary product context
- Token budget shared across all active products

**Pros**:
- Flexible product management
- Can monitor multiple products
- Quick switching via priority change

**Cons**:
- Confusing mental model (which is "really" active?)
- Token budget sharing requires complex allocation logic
- MCP tools must handle multi-product context
- Field priority config unclear (which product's settings?)
- Requires database migration (priority column)
- UI complexity (priority management interface)

**Complexity**: HIGH
**Implementation Time**: 2-3 weeks
**Risk**: MEDIUM

### Option C: Product Workspaces (Multi-Context)

**Architecture**:
- Each product is a separate "workspace"
- User explicitly switches workspace (like IDE tabs)
- All orchestration scoped to current workspace
- No "active" flag - workspace selection is transient state
- Session state tracks current workspace

**Pros**:
- Natural isolation between products
- No database changes needed
- Aligns with modern IDE patterns
- Clean separation of concerns

**Cons**:
- Requires significant UI refactoring (workspace context everywhere)
- Session state management complexity
- Existing `is_active` flag becomes unused
- All views need workspace-aware filtering
- URL routing needs workspace parameter
- WebSocket events need workspace scoping

**Complexity**: VERY HIGH
**Implementation Time**: 4-6 weeks
**Risk**: HIGH

## Selected Option: A (Single Active Product)

**Decision**: Implement single active product architecture with validation and warnings.

### Rationale

#### 1. Architecture Alignment

The mission-based orchestration architecture is fundamentally designed for focused context:
- **MissionPlanner** generates missions from ONE product's vision + config
- **AgentSelector** chooses agents based on ONE product's requirements
- **WorkflowEngine** coordinates agents working on ONE product's tasks
- **Token Budget** (2000 tokens) is product-specific, not shared

**Verdict**: Multi-product active state contradicts core architecture.

#### 2. Token Efficiency

The 70% token reduction was achieved through:
- Condensed mission generation (single product focus)
- Field priority configuration (per-product settings)
- Targeted context delivery (one product's vision chunks)

**Verdict**: Multiple active products dilutes token efficiency.

#### 3. MCP Server Design

MCP tools are designed for single product context:
- `get_active_product()` returns ONE product
- `get_product_context()` builds context for ONE product
- Agent jobs reference ONE product_id
- Mission templates assume ONE product's config_data

**Verdict**: MCP tools not designed for multi-product context.

#### 4. User Mental Model

User interviews and testing revealed:
- Users think in terms of "what am I working on right now?" (singular)
- Multiple active products created confusion: "Which one is really active?"
- Switching products is rare (typically once per day/session)
- Clear focus improves productivity

**Verdict**: Single active product matches user expectations.

#### 5. Implementation Simplicity

Option A requires:
- 4 validation checks in backend (activate product, activate project, create job, delete product)
- 1 warning dialog in frontend
- 1 disabled state for project activation button
- No database changes, no migrations, no refactoring

**Verdict**: Lowest risk, fastest delivery, immediate value.

### Trade-offs Acknowledged

**What We Gain**:
- Clear focus and mental model
- Architecture consistency
- Token efficiency maintained
- Simple implementation (2-3 days)
- No breaking changes
- Prevents data integrity issues

**What We Give Up**:
- Cannot have multiple products active simultaneously
- Switching products requires explicit user action
- Cannot compare two products in real-time agent context

### Mitigation Strategies

For users who need to work on multiple products:
1. **Quick Switch**: Add keyboard shortcut for product switching (future enhancement)
2. **Recent Products**: Show recently active products in dropdown (future enhancement)
3. **Product Tabs**: Implement workspace tabs if demand grows (Option C, future)

---

# Implementation Plan

## Overview

This implementation follows a 5-phase approach, building from backend validation to frontend user experience. Each phase is independently testable and can be deployed incrementally if needed.

**Total Estimated Lines of Code**: ~420 lines across 8 files (6 modified, 2 new)

## Phase 1: Backend - Product Activation Rules (Day 1)

**Duration**: 4 hours
**Files Modified**: 1
**Risk**: LOW

### Objective

Ensure only one product can be active per tenant, with proper deactivation of other products and refresh of active product store state.

### Implementation Steps

#### Step 1.1: Add Helper Function

**File**: `api/endpoints/products.py`
**Location**: Before `activate_product()` function (before line 563)
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

#### Step 1.2: Modify Product Activation Endpoint

**File**: `api/endpoints/products.py`
**Function**: `activate_product()` (lines 563-637)

**Change 1** - Add at line 583 (before deactivation query):
```python
# Get currently active product info for warning response
current_active = await get_active_product_info(db, tenant_key)
```

**Change 2** - Modify return statement at line 617:

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

#### Step 1.3: Modify Product Deletion Endpoint

**File**: `api/endpoints/products.py`
**Function**: `delete_product()`

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

#### Step 1.4: Add Endpoint to Refresh Active Product Store

**File**: `api/endpoints/products.py`
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

## Phase 2: Frontend - Activation Warnings (Day 1-2)

**Duration**: 4-6 hours
**Files Modified**: 2 (new component + ProductsView update)
**Risk**: LOW

### Objective

Warn users before activating a product that will deactivate another product, showing impact on active projects.

### Implementation Steps

#### Step 2.1: Create Warning Dialog Component

**File**: `frontend/src/components/products/ActivationWarningDialog.vue` (NEW)

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

**Add State Variables**:
```javascript
const showActivationWarning = ref(false)
const pendingActivation = ref(null)
const previousActiveProduct = ref(null)
```

**Replace `activateProduct` Function**:
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

**Modify `deleteProduct` Function**:

Add after successful deletion:
```javascript
const response = await api.products.deleteProduct(product.id)

// If deleted product was active, refresh store
if (response.data.was_active) {
  await productsStore.fetchActiveProduct()
  await api.products.refreshActiveProductStore()
}
```

**Add Component to Template** (before closing `</template>` tag):
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

#### Step 2.3: Update API Service

**File**: `frontend/src/services/api.js`

**Add Method**:
```javascript
products: {
  // ... existing methods
  refreshActiveProductStore: () => apiClient.post('/api/v1/products/refresh-active'),  // NEW
}
```

## Phase 3: Project Validation (Day 2)

**Duration**: 3 hours
**Files Modified**: 2
**Risk**: LOW

### Objective

Ensure projects can only be activated if their parent product is active.

### Implementation Steps

#### Step 3.1: Add Backend Validation

**File**: `api/endpoints/projects.py`

**Find**: Function that handles project status updates (likely `update_project`)

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

#### Step 3.2: Update Frontend Projects View

**File**: `frontend/src/views/ProjectsView.vue`

**Add Import**:
```javascript
import { useProductsStore } from '@/stores/products'
```

**Add State and Computed**:
```javascript
const productsStore = useProductsStore()
const products = computed(() => productsStore.products)

const canActivateProject = computed(() => {
  return (project) => {
    // Find parent product
    const parentProduct = products.value.find(p => p.id === project.product_id)

    // Can activate if parent product is active
    return parentProduct?.is_active === true
  }
})
```

**Update `onMounted`**:
```javascript
onMounted(async () => {
  await productsStore.fetchProducts()  // NEW
  await projectsStore.fetchProjects()
  // ... existing code
})
```

**Update Activate Button in Template**:

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

## Phase 4: Agent Job Safety (Day 3)

**Duration**: 2 hours
**Files Modified**: 2
**Risk**: LOW

### Objective

Ensure agent jobs validate product is active before creation and mission assignment.

### Implementation Steps

#### Step 4.1: Add Validation to Agent Job Manager

**File**: `src/giljo_mcp/agent_job_manager.py`

**Find**: `create_job` method

**Add Validation**:
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

#### Step 4.2: Add Validation to Orchestrator

**File**: `src/giljo_mcp/orchestrator.py`

**Find**: Method that assigns missions to agents

**Add Validation**:
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

## Phase 5: Testing & Documentation (Day 3)

**Duration**: 4 hours
**Files Modified**: Multiple (docs, tests)
**Risk**: LOW

### Objective

Comprehensive testing and documentation of single active product architecture.

### Testing Scope

**Unit Tests**:
1. Test `get_active_product_info()` with various scenarios
2. Test `activate_product()` returns `previous_active_product`
3. Test `delete_product()` returns `was_active` flag
4. Test project activation validation
5. Test agent job validation
6. Test multi-tenant isolation

**Integration Tests**:
1. Complete activation flow (A → B → verify A deactivated)
2. Project validation flow
3. Agent job validation flow
4. Delete active product flow

**Manual UAT Scenarios**:
1. First product activation (no warning)
2. Second product activation (warning dialog)
3. Active projects count in warning
4. Project activation button disabled/enabled
5. Delete active product refreshes top bar
6. Multi-tenant isolation

### Documentation Updates

**Files to Update**:

1. **CLAUDE.md**:
```markdown
## v3.0 Unified Architecture

- Single Active Product (Handover 0050) - Only one product active per tenant
- Product activation with warning dialogs
- Project validation (parent product must be active)
- Agent job validation (product must be active)
```

2. **docs/TECHNICAL_ARCHITECTURE.md**:
```markdown
## Single Active Product Architecture

Only ONE product can be active per tenant at any time. This ensures:
- Focused agent context (70% token reduction)
- Clear user mental model
- Token budget consistency (2000 tokens per product)
- MCP tool simplicity

See: handovers/0050_single_active_product_architecture.md
```

3. **User Guide** (create `docs/guides/ACTIVE_PRODUCT_GUIDE.md`):
- What is an active product?
- How to activate/deactivate products
- What happens when you switch?
- Why only one can be active

4. **API Documentation**:
- Update endpoint docs for modified endpoints
- Document new `refresh-active` endpoint
- Update error response codes

---

# Files to Modify

## Backend (Python)

1. **api/endpoints/products.py** (+80 lines)
   - Add `get_active_product_info()` helper function
   - Modify `activate_product()` to include `previous_active_product` in response
   - Modify `delete_product()` to include `was_active` flag
   - Add new `refresh_active_product_store()` endpoint

2. **api/endpoints/projects.py** (+20 lines)
   - Add validation in project status update function
   - Check parent product is active before allowing status='active'

3. **src/giljo_mcp/agent_job_manager.py** (+25 lines)
   - Add product validation in `create_job()` method
   - Raise ValueError if product not active

4. **src/giljo_mcp/orchestrator.py** (+20 lines)
   - Add product validation in mission assignment methods
   - Raise ValueError if product not active

## Frontend (Vue/JavaScript)

5. **frontend/src/components/products/ActivationWarningDialog.vue** (+120 lines, NEW FILE)
   - Complete warning dialog component with props validation
   - Shows previous product info and active projects count
   - Confirm/cancel actions

6. **frontend/src/views/ProductsView.vue** (+100 lines)
   - Import and integrate ActivationWarningDialog
   - Add state variables for warning dialog
   - Replace `activateProduct()` function with two-step flow
   - Add `confirmActivation()` and `cancelActivation()` functions
   - Modify `deleteProduct()` to refresh store

7. **frontend/src/views/ProjectsView.vue** (+50 lines)
   - Import products store
   - Add `canActivateProject()` computed property
   - Update activate button with disabled state
   - Add tooltip for disabled state

8. **frontend/src/services/api.js** (+5 lines)
   - Add `refreshActiveProductStore()` method to products API

**Total**: ~420 lines of code across 8 files (6 modified, 2 new)

---

# API Changes

## Modified Endpoints

### 1. POST /api/v1/products/{product_id}/activate

**Change**: Response now includes `previous_active_product` field

**Response Body**:
```json
{
  "id": "uuid",
  "name": "Product Name",
  "is_active": true,
  "previous_active_product": {
    "id": "uuid",
    "name": "Previous Product Name",
    "active_projects_count": 2
  }
}
```

**NEW Field**: `previous_active_product` (object | null)
- Null when this is the first active product
- Object with previous product info when deactivating another product

### 2. DELETE /api/v1/products/{product_id}

**Change**: Response now includes `was_active` field

**Response Body**:
```json
{
  "success": true,
  "message": "Product 'Product Name' deleted successfully",
  "was_active": true
}
```

**NEW Field**: `was_active` (boolean)
- Indicates if deleted product was active
- Frontend uses this to refresh active product indicator

### 3. PATCH /api/v1/projects/{project_id}

**Change**: New validation when setting status='active'

**New Error Response** (400 Bad Request):
```json
{
  "detail": "Cannot activate project - parent product 'Product Name' is not active. Please activate the product first."
}
```

**Validation**: Backend checks parent product is active before allowing project activation

## New Endpoints

### 4. POST /api/v1/products/refresh-active

**Purpose**: Get current active product info (for store refresh after deletions)

**Request**:
```http
POST /api/v1/products/refresh-active
Authorization: Bearer <jwt_token>
```

**Response**:
```json
{
  "active_product": {
    "id": "uuid",
    "name": "Product Name",
    "active_projects_count": 3
  },
  "timestamp": "2025-01-27T10:30:00Z"
}
```

**Response When No Active Product**:
```json
{
  "active_product": null,
  "timestamp": "2025-01-27T10:30:00Z"
}
```

## Backward Compatibility

**Breaking Changes**: NONE

All changes are additive - existing API clients will continue to work. New clients can utilize enhanced response fields for better UX.

---

# Testing Strategy

## Unit Tests

**Test File**: `tests/unit/test_single_active_product.py`

Coverage:
- `get_active_product_info()` with no active product
- `get_active_product_info()` with active product and projects
- `activate_product()` returns `previous_active_product`
- `delete_product()` returns `was_active`
- Multi-tenant isolation

**Test File**: `tests/unit/test_project_activation_validation.py`

Coverage:
- Activate project with active parent (success)
- Activate project with inactive parent (400 error)
- Activate project with no parent (400 error)

**Test File**: `tests/unit/test_agent_job_product_validation.py`

Coverage:
- Create job with active product (success)
- Create job with inactive product (ValueError)
- Mission assignment validation

## API Tests

**Test File**: `tests/api/test_product_activation_api.py`

Coverage:
- Activate first product (no previous)
- Activate second product (returns previous info)
- Delete active product (returns was_active=true)
- Refresh endpoint returns current active product
- Multi-tenant isolation

## Integration Tests

**Test File**: `tests/integration/test_single_active_product_flow.py`

Full flow test:
1. Activate Product A
2. Activate projects under A
3. Activate Product B (gets previous info)
4. Verify A deactivated
5. Try to activate project under A (fails)
6. Delete Product B
7. Refresh store (returns null)

## Manual UAT Scenarios

1. **First Product Activation**: Activate Product A → No warning → Top bar updates
2. **Second Product Activation**: Activate Product B → Warning appears → Cancel/Confirm flow
3. **Active Projects Warning**: Create 2 active projects under A → Activate B → Warning shows count
4. **Project Activation Validation**: Deactivate parent → Button disabled → Tooltip shows
5. **Delete Active Product**: Delete active product → Top bar clears
6. **Multi-Tenant Isolation**: Two tenants can each have one active product independently

**Test Coverage Target**: 90%+ backend, 80%+ frontend

---

# Success Criteria

## Functional Requirements
- Only one product can be active per tenant (enforced in backend)
- Activating a product shows warning if another is active
- Warning dialog lists active product's active projects
- Deactivating current product clears top bar active product indicator
- Deleting active product clears active state
- Project activation validates parent product is active
- Project activation button disabled if product not active
- Agent jobs validate product is active before creation

## User Experience Requirements
- Warning dialog shows clear before/after state
- Activation change refreshes top bar immediately
- Project activation tooltip explains why button is disabled
- Delete product refreshes store state immediately

## Technical Requirements
- Multi-tenant isolation maintained
- All validations async-safe
- No breaking changes to existing API contracts
- WebSocket events fire on state changes (reuse existing)

---

# Related Handovers

- **Handover 0048**: Field Priority Configuration (COMPLETE)
  - Establishes field priority system this handover protects
  - Single active product ensures correct token budget application

- **Handover 0049**: Active Product Token Visualization (COMPLETE)
  - Top bar active product indicator (this handover ensures only one can be active)
  - Token visualization tied to active product

- **Handover 0051**: Multi-Product Management Enhancements (FUTURE)
  - May introduce "quick switch" between products
  - Builds on single active product architecture

---

# Risk Assessment

**Complexity**: LOW
- Simple validation logic
- No database schema changes
- No complex refactoring

**Risk**: LOW
- Additive changes only
- No breaking changes
- Independent phase deployment possible

**Breaking Changes**: None (backward compatible)

**Performance Impact**: Minimal (+5-10ms per activation for additional query)

---

# Implementation Notes

## Rollback Plan

If issues arise during implementation:

**Phase 1 Rollback**: `git revert <commit-hash>` (no database changes)
**Phase 2 Rollback**: `git revert <commit-hash>` + delete ActivationWarningDialog.vue
**Phase 3 Rollback**: Remove validation checks, restore original button state
**Phase 4 Rollback**: Remove validation from agent job manager and orchestrator
**Phase 5 Rollback**: Revert documentation changes

**Risk**: LOW - All changes are additive, no schema changes, no data migration.

## Dependencies

**Required Before Starting**:
- Handover 0049 complete (active product indicator exists)
- Product activation endpoint exists (`POST /api/v1/products/{product_id}/activate`)
- Project activation logic exists

**Blocks Future Work**:
- Agent mission generation (needs stable active product context)
- Multi-agent orchestration (needs clear product scope)

## Future Considerations

### When to Revisit This Decision

Consider Option C (Workspaces) if:
- 50%+ of users request multi-product workflows
- Mission architecture evolves to support multi-product context
- Token budgets can be safely shared across products
- MCP tools are redesigned for workspace isolation

### Evolution Path

1. **Phase 1 (Now)**: Single active product (Option A)
2. **Phase 2 (3-6 months)**: Quick switch enhancements
3. **Phase 3 (6-12 months)**: Evaluate workspace demand
4. **Phase 4 (12+ months)**: Consider workspace architecture if needed

---

# Timeline Estimate

**Day 1**: Phase 1 (Backend) + Phase 2 (Frontend warning dialog)
**Day 2**: Phase 3 (Project validation) + Phase 4 (Agent job safety)
**Day 3**: Phase 5 (Testing) + Documentation + Close handover

**Total**: 2-3 days for experienced developer

---

# Sign-Off Checklist

Before marking this handover complete:
- All 5 phases implemented
- All test scenarios pass
- Code committed with descriptive messages
- Documentation updated (User Guide, CLAUDE.md, API docs)
- Handover moved to `handovers/completed/` with completion summary
- No console errors in any scenario
- Multi-tenant isolation verified
- All success criteria met

---

**Decision Recorded By**: System Architect
**Date**: 2025-01-27
**Review Date**: 2026-07-27 (6 months)

---

**End of Handover 0050**
