# Problem Analysis: Product Form Data Loss

**Date**: 2025-10-27
**Handover**: 0051

## Current Behavior

### Multi-Tab Product Form Structure

The product creation/editing form is spread across 5 tabs:

1. **Basic Info** (dialogTab = 'basic')
   - Product Name (required)
   - Product Description (optional)

2. **Vision Docs** (dialogTab = 'vision')
   - File upload for vision documents
   - Auto-chunking option
   - Display of existing vision documents

3. **Tech Stack** (dialogTab = 'tech')
   - Programming Languages
   - Frontend Frameworks & Libraries
   - Backend Frameworks & Services
   - Databases & Data Storage
   - Infrastructure & DevOps

4. **Architecture** (dialogTab = 'arch')
   - Architecture Pattern (e.g., MVC, Microservices, Event-Driven)
   - Design Patterns (e.g., Repository, Factory, Observer)
   - API Style (e.g., REST, GraphQL, gRPC)
   - Architecture Notes

5. **Features & Testing** (dialogTab = 'features')
   - Core Features
   - Testing Strategy (default: "TDD")
   - Coverage Target (default: 80, slider 0-100)
   - Testing Frameworks

### Form State Management

**Current Implementation**:
```javascript
// Reactive form object (lines 1269-1297)
const productForm = ref({
  name: '',
  description: '',
  visionPath: '',
  configData: {
    tech_stack: { ... },
    architecture: { ... },
    features: { ... },
    test_config: { ... },
  },
})

// Single save point (lines 1561-1629)
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
        configData: productForm.value.configData,
      })
    } else {
      product = await productStore.createProduct({
        name: productForm.value.name,
        description: productForm.value.description,
        configData: productForm.value.configData,
      })
    }

    // Step 2: Upload vision files...
    // Step 3: Refresh products...
    // Step 4: Close dialog
    // Step 5: Show success message
  } catch (error) {
    console.error('Failed to save product:', error)
    showToast({ message: 'Failed to save product', type: 'error' })
  } finally {
    saving.value = false
  }
}
```

**Key Issues**:
1. **Single Save Point**: Only saves when user clicks "Save" button
2. **No Intermediate Persistence**: If user navigates tabs, data remains in reactive object but isn't persisted
3. **No LocalStorage Cache**: If browser crashes or user refreshes, data is lost
4. **Silent Failures**: Error handling is minimal - only console.error and generic toast

## User Pain Points

### Pain Point 1: Complete Data Loss on Save Failure

**Scenario**:
```
1. User spends 10 minutes filling out all 5 tabs
2. User clicks "Save"
3. API call fails (network error, validation error, server error)
4. Dialog closes (line 1609: closeDialog())
5. ALL DATA LOST - form is reset on dialog close
```

**Why This Happens**:
- `closeDialog()` is called before verifying save success
- Form is reset on dialog close: `productForm.value = { ... }` (likely in closeDialog function)
- No cache/backup of form data

**Impact**: CRITICAL - Users lose 10+ minutes of work

### Pain Point 2: Accidental Dialog Close

**Scenario**:
```
1. User fills out multiple tabs
2. User accidentally clicks outside dialog or presses ESC
3. Dialog closes with no warning
4. All data lost
```

**Why This Happens**:
- No `beforeunload` handler
- No "unsaved changes" detection
- Dialog has standard Vuetify close behavior (click outside = close)

**Impact**: HIGH - Users lose work and trust the system

### Pain Point 3: Tab Navigation Confusion

**Scenario**:
```
1. User fills out "Tech Stack" tab (5 fields)
2. User navigates to "Architecture" tab
3. User navigates back to "Tech Stack" tab
4. User unsure if data was saved or still present
```

**Why This Happens**:
- No visual feedback about save status
- No "saved" indicator
- Data IS preserved (in reactive object) but user doesn't know

**Impact**: MEDIUM - User anxiety and confusion

### Pain Point 4: Poor Placeholder for Testing Strategy

**Current Implementation**:
```vue
<v-select
  v-model="productForm.configData.test_config.strategy"
  :items="['TDD', 'BDD', 'Integration-First', 'E2E-First', 'Manual', 'Hybrid']"
  label="Testing Strategy"
  variant="outlined"
  density="comfortable"
  class="mb-4"
></v-select>
```

**Problem**: Only shows "TDD" as default value with no helpful hint about what each strategy means.

**Better Approach**:
```javascript
const testingStrategies = [
  { value: 'TDD', title: 'TDD (Test-Driven Development)', description: 'Write tests before code' },
  { value: 'BDD', title: 'BDD (Behavior-Driven Development)', description: 'Tests from user stories' },
  { value: 'Integration-First', title: 'Integration-First', description: 'Focus on integration tests' },
  { value: 'E2E-First', title: 'E2E-First', description: 'Focus on end-to-end tests' },
  { value: 'Manual', title: 'Manual Testing', description: 'Manual QA process' },
  { value: 'Hybrid', title: 'Hybrid Approach', description: 'Mix of strategies' },
]
```

**Impact**: LOW - Minor UX improvement

### Pain Point 5: No Validation Feedback During Navigation

**Scenario**:
```
1. User leaves "Product Name" empty (required field)
2. User fills out other 4 tabs
3. User clicks "Save"
4. Validation fails: "Product Name is required"
5. User must navigate back to Basic Info tab to fix
```

**Why This Happens**:
- Validation only runs on save attempt (`if (!formValid.value) return`)
- No per-tab validation indicators
- No visual feedback on which tab has errors

**Impact**: MEDIUM - User frustration, wasted time

## Root Cause Analysis

### Potential Save Bug Investigation

**Hypothesis 1: Form Binding Issue**
```javascript
// Check if v-model bindings are correct
// File: ProductsView.vue, lines 340-750 (form fields)

// Tech Stack fields bind to:
v-model="productForm.configData.tech_stack.languages"
v-model="productForm.configData.tech_stack.frontend"
// etc.

// Question: Are these nested v-models working correctly?
// Test: Console.log productForm.value before save
```

**Hypothesis 2: API Serialization Issue**
```javascript
// Store passes configData as-is (products.js, lines 132-148)
const response = await api.products?.create(productData)

// API expects configData as JSON string (products.py, line 120)
config_data: Optional[str] = Form(None)

// Question: Is api.products.create serializing configData correctly?
// Test: Check Network tab to see if configData is sent as string or object
```

**Hypothesis 3: Backend Not Saving configData**
```python
# File: api/endpoints/products.py, lines 131-139
config_dict: Dict[str, Any] = {}
if config_data:
    try:
        config_dict = json.loads(config_data)
        if not isinstance(config_dict, dict):
            raise HTTPException(status_code=400, detail="config_data must be a JSON object")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid config_data JSON: {str(e)}")

# Question: Is config_dict being saved to database?
# Test: Query database after save to verify config_data column
```

**Hypothesis 4: Response Not Returning configData**
```python
# File: api/endpoints/products.py, lines 225-243
return ProductResponse(
    id=product.id,
    name=product.name,
    description=product.description,
    # ...
    config_data=product.config_data,  # Is this set correctly?
    has_config_data=product.has_config_data,
)

# Question: Is product.config_data being loaded from database?
# Test: Check API response in Network tab
```

### Debugging Checklist

- [ ] Add console.log in `saveProduct()` before API call
- [ ] Add console.log in `productStore.createProduct()` to see what's sent
- [ ] Check Network tab to verify request payload
- [ ] Check Network tab to verify response payload
- [ ] Query database directly after save to verify data persistence
- [ ] Add backend logging in `create_product()` endpoint
- [ ] Test with minimal data (just name + one configData field)
- [ ] Test with full data (all 5 tabs filled)
- [ ] Test create vs. update (different code paths)

## Current Save Flow Breakdown

### Frontend Save Flow

```
User clicks "Save"
   ↓
formValid.value checked (validation)
   ↓
saving.value = true (loading state)
   ↓
IF editingProduct.value exists:
   → productStore.updateProduct(id, data)
ELSE:
   → productStore.createProduct(data)
   ↓
API response returns product object
   ↓
Upload vision files (if visionFiles.value.length > 0)
   ↓
FOR EACH file:
   → api.visionDocuments.upload(formData)
   ↓
await loadProducts() (refresh list)
   ↓
closeDialog() (reset form and close)
   ↓
showToast('Product created/updated successfully')
   ↓
saving.value = false
```

### Backend Save Flow (Create)

```
POST /api/products/
   ↓
Extract form fields: name, description, config_data (as JSON string)
   ↓
Parse config_data JSON string → config_dict
   ↓
Create Product object:
   - id = uuid4()
   - tenant_key = from auth
   - name = name
   - description = description
   - config_data = config_dict (JSONB column)
   ↓
db.add(product)
db.commit()
db.refresh(product)
   ↓
Return ProductResponse with config_data
```

### Backend Save Flow (Update)

```
PUT /api/products/{product_id}
   ↓
Extract form fields: name, description, config_data (as JSON string)
   ↓
Fetch existing product from database
   ↓
IF name provided: product.name = name
IF description provided: product.description = description
IF config_data provided:
   → Parse JSON string → config_dict
   → product.config_data = config_dict
   ↓
product.updated_at = utcnow()
   ↓
db.commit()
db.refresh(product)
   ↓
Return ProductResponse with config_data
```

## Data Flow Diagram

```
[ProductsView.vue]
    productForm.value (reactive)
        ↓
    saveProduct()
        ↓
    productStore.createProduct(data)
        ↓
    [products.js store]
        api.products.create(productData)
            ↓
        [api service - axios]
            POST /api/products/
            Body: FormData with name, description, config_data (JSON string)
                ↓
            [products.py endpoint]
                create_product(name, description, config_data)
                    ↓
                Parse config_data JSON
                    ↓
                Create Product model instance
                    ↓
                db.add(product)
                db.commit()
                    ↓
                [PostgreSQL database]
                    products table
                    config_data column (JSONB)
```

## Expected vs. Actual Behavior

### Expected Behavior
1. User fills out all 5 tabs
2. User clicks "Save"
3. Frontend sends complete productForm data to API
4. Backend saves all fields including configData to database
5. Backend returns complete product object with configData
6. Frontend updates store and shows success message
7. If user reopens product, all fields are populated correctly

### Actual Behavior (Reported)
1. User fills out all 5 tabs
2. User clicks "Save"
3. ??? (Unknown - need to investigate)
4. Dialog closes
5. Data not persisted
6. If user reopens product, fields are empty

### Critical Questions

1. **Is the save API call even being made?** (Check Network tab)
2. **Is the request payload correct?** (Check request body in Network tab)
3. **Is the backend receiving the data?** (Add logging in products.py)
4. **Is the backend saving the data?** (Query database after save)
5. **Is the backend returning the saved data?** (Check response body in Network tab)
6. **Is the frontend updating the store?** (Check productStore.products array)
7. **Is the dialog closing too early?** (Check if success callback awaited)

## Next Steps for Debugging

1. **Add Comprehensive Logging**:
   ```javascript
   async function saveProduct() {
     console.log('[SAVE] Starting save with data:', {
       name: productForm.value.name,
       description: productForm.value.description,
       configData: productForm.value.configData,
     })

     // ... existing save logic ...

     console.log('[SAVE] API response:', product)
   }
   ```

2. **Add Network Monitoring**:
   - Open DevTools Network tab
   - Filter by "products"
   - Save product
   - Check request payload
   - Check response payload

3. **Add Backend Logging**:
   ```python
   @router.post("/", response_model=ProductResponse)
   async def create_product(...):
       print(f"[PRODUCTS] Received create request: name={name}, config_data={config_data}")
       # ... existing logic ...
       print(f"[PRODUCTS] Saved product: {product.id}, config_data={product.config_data}")
   ```

4. **Query Database Directly**:
   ```sql
   SELECT id, name, config_data FROM products ORDER BY created_at DESC LIMIT 1;
   ```

5. **Test Minimal Case**:
   - Fill ONLY "Product Name"
   - Click Save
   - Verify it saves successfully
   - Then incrementally add more fields

---

**Conclusion**: We need to debug the current save flow FIRST before implementing auto-save. If save is broken, auto-save won't help.
