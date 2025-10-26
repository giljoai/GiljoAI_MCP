# Handover 0042: Product Rich Context Fields UI Enhancement

**Date**: 2025-10-23
**Updated**: 2025-10-26
**From Agent**: Research & Planning Agent
**To Agent**: Full-Stack Development Team (UX Designer + TDD Implementor + Frontend Tester)
**Priority**: High (Phase 2 - Ready to Start)
**Estimated Effort**: 3-4 hours
**Status**: Ready - Handover 0047 Complete
**Risk Level**: Low (Backend support exists, frontend-only changes)
**Dependencies**: ✅ **HANDOVER 0047 COMPLETE** (Vision document chunking now operational)

---

## ✅ READY TO IMPLEMENT: Handover 0047 Complete

**This handover is PHASE 2 of the Product Context Management System.**

**HANDOVER 0047 STATUS**: ✅ **COMPLETE** (2025-10-26)
- Vision document chunking fully operational (100% async)
- Product deletion working (CASCADE + await)
- File size tracking implemented (bonus feature)
- 5/5 unit tests passing, 0 async warnings
- Production-ready and merged to master

**WHY THIS IS NOW READY**:
- This handover adds rich metadata fields (tech_stack, architecture, features)
- These fields COMPLEMENT vision document chunks
- Vision chunking now works correctly (Handover 0047 fixed it)
- Complete context = Config fields (0042) + Vision chunks (0047 ✅)
- **Result**: Phase 1 (0047) complete → Phase 2 (0042) ready to proceed

**IMPLEMENTATION SEQUENCE**:
1. ✅ Handover 0047 complete (vision chunking fixed)
2. ✅ Vision documents chunk successfully (verified)
3. ➡️ **NOW READY**: Implement this handover (add rich fields)

---

## Executive Summary

**Objective**: Expose the rich `config_data` JSONB field and additional vision management fields in the Product creation/edit UI to enable agents to receive comprehensive product context.

**Current Problem**:
- Backend `Product` model has extensive `config_data` JSONB field for tech_stack, architecture, features, etc.
- Frontend only exposes 3 basic fields: name, description, vision_path
- Users cannot provide critical context (tech stack, architecture) that agents need
- Inline vision editing option (`vision_document` field) not accessible
- Vision type selector (`vision_type`: 'file', 'inline', 'none') missing

**Proposed Solution**:
- Expand Product creation/edit dialog to multi-step form or tabbed interface
- Add tech_stack configuration (languages, frameworks, databases)
- Add architecture configuration (patterns, boundaries, design decisions)
- Add vision type selector with inline editor option
- Add features and testing configuration
- Store all data in existing `config_data` JSONB field
- Update API endpoints to handle new fields

**Value Delivered**:
- Agents receive 3-5x more context about products
- Enables intelligent agent orchestration with tech-stack awareness
- Reduces token usage through targeted context delivery
- Improves agent decision-making with architecture knowledge
- Professional UX with proper form validation and help text

---

## Research Findings

### 1. Backend Capabilities (Already Implemented)

**Product Model** (`src/giljo_mcp/models.py:57-140`):

```python
class Product(Base):
    # Basic fields
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Vision management (hybrid approach)
    vision_path = Column(String(500), nullable=True)      # File-based
    vision_document = Column(Text, nullable=True)         # Inline text
    vision_type = Column(String(20), default="none")      # 'file', 'inline', 'none'
    chunked = Column(Boolean, default=False)

    # Rich context data (JSONB - PostgreSQL optimized)
    config_data = Column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Rich project configuration: architecture, tech_stack, features, etc."
    )

    # Helper methods
    @property
    def has_config_data(self) -> bool

    def get_config_field(self, field_path: str, default: Any = None) -> Any
```

**Key Features**:
- `config_data` supports nested JSON with dot notation access
- GIN index on `config_data` for fast JSONB queries
- Helper methods for safe field access
- PostgreSQL JSONB type for efficient storage and querying

### 2. Frontend Gap Analysis

**Current Implementation** (`frontend/src/views/ProductsView.vue:251-278`):

```vue
<v-form ref="productForm" v-model="formValid">
  <v-text-field v-model="productForm.name" />
  <v-textarea v-model="productForm.description" />
  <v-text-field v-model="productForm.visionPath" />
</v-form>
```

**Missing Fields**:
1. `config_data.tech_stack` - Technology stack configuration
2. `config_data.architecture` - Architecture patterns
3. `config_data.features` - Feature specifications
4. `config_data.test_config` - Testing standards
5. `vision_document` - Inline vision editor
6. `vision_type` - Vision source selector

### 3. API Endpoint Status

**Current Endpoint** (`api/endpoints/products.py:76-175`):

```python
@router.post("/", response_model=ProductResponse)
async def create_product(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    vision_file: Optional[UploadFile] = File(None),
    tenant_key: str = Depends(get_tenant_key),
):
```

**Needs Enhancement**:
- Add `config_data` parameter (JSON string)
- Add `vision_document` parameter
- Add `vision_type` parameter
- Update response model to include new fields

---

## Implementation Plan

### Phase 1: API Endpoint Enhancement (30 minutes)

**Files to Modify**:
- `api/endpoints/products.py`

**Changes Required**:

1. **Update `create_product` endpoint**:
```python
@router.post("/", response_model=ProductResponse)
async def create_product(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    vision_file: Optional[UploadFile] = File(None),
    vision_document: Optional[str] = Form(None),  # NEW
    vision_type: str = Form("none"),               # NEW
    config_data: Optional[str] = Form(None),       # NEW - JSON string
    tenant_key: str = Depends(get_tenant_key),
):
    # Parse config_data JSON
    config_dict = {}
    if config_data:
        try:
            config_dict = json.loads(config_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid config_data JSON")

    # Create product with new fields
    product = Product(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        name=name,
        description=description,
        vision_type=vision_type,
        vision_document=vision_document,
        config_data=config_dict,
    )

    # Handle vision_file if provided (existing logic)
    # ...
```

2. **Update `update_product` endpoint** (similar changes)

3. **Add response fields to `ProductResponse` model**:
```python
class ProductResponse(BaseModel):
    # Existing fields
    id: str
    name: str
    description: Optional[str]
    vision_path: Optional[str]

    # NEW fields
    vision_document: Optional[str]
    vision_type: str
    config_data: Optional[Dict[str, Any]]
    has_config_data: bool

    # Computed fields
    has_vision: bool
    project_count: int
    task_count: int
```

**Testing Requirements**:
- Test with empty config_data
- Test with valid JSON config_data
- Test with invalid JSON (should fail gracefully)
- Test vision_type validation ('file', 'inline', 'none')
- Test both file upload and inline vision

---

### Phase 2: Frontend Form Component (2 hours)

**Files to Modify**:
- `frontend/src/views/ProductsView.vue`

**Design Approach**: Multi-step form with tabs

#### Step 1: Basic Information (Current Fields)
- Product name (required)
- Description
- Project status

#### Step 2: Vision & Documentation
- **Vision Type Selector** (radio buttons):
  - None (default)
  - Upload File
  - Inline Editor
- **Conditional Fields**:
  - If "Upload File": File upload input
  - If "Inline Editor": Rich text editor (v-textarea with markdown support)

#### Step 3: Technology Stack
```vue
<v-card>
  <v-card-title>Technology Stack</v-card-title>
  <v-card-text>
    <!-- Programming Languages -->
    <v-combobox
      v-model="configData.tech_stack.languages"
      label="Programming Languages"
      hint="e.g., Python, JavaScript, TypeScript"
      multiple
      chips
      :items="['Python', 'JavaScript', 'TypeScript', 'Java', 'Go', 'Rust', 'C#']"
    />

    <!-- Frontend Framework -->
    <v-combobox
      v-model="configData.tech_stack.frontend"
      label="Frontend Framework"
      hint="e.g., Vue 3, React, Angular"
      chips
      multiple
      :items="['Vue 3', 'React', 'Angular', 'Svelte', 'Next.js', 'Nuxt']"
    />

    <!-- Backend Framework -->
    <v-combobox
      v-model="configData.tech_stack.backend"
      label="Backend Framework"
      hint="e.g., FastAPI, Express, Django"
      chips
      multiple
      :items="['FastAPI', 'Django', 'Flask', 'Express', 'NestJS', 'Spring Boot']"
    />

    <!-- Database -->
    <v-combobox
      v-model="configData.tech_stack.database"
      label="Database"
      hint="e.g., PostgreSQL, MongoDB"
      chips
      multiple
      :items="['PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'SQLite', 'Elasticsearch']"
    />

    <!-- Infrastructure -->
    <v-combobox
      v-model="configData.tech_stack.infrastructure"
      label="Infrastructure & DevOps"
      hint="e.g., Docker, Kubernetes"
      chips
      multiple
      :items="['Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP', 'Terraform']"
    />
  </v-card-text>
</v-card>
```

#### Step 4: Architecture Configuration
```vue
<v-card>
  <v-card-title>Architecture & Design</v-card-title>
  <v-card-text>
    <!-- Architecture Pattern -->
    <v-select
      v-model="configData.architecture.pattern"
      label="Architecture Pattern"
      hint="Primary architectural approach"
      :items="[
        'Monolithic',
        'Microservices',
        'Modular Monolith',
        'Serverless',
        'Event-Driven',
        'Layered Architecture'
      ]"
    />

    <!-- Design Patterns -->
    <v-combobox
      v-model="configData.architecture.design_patterns"
      label="Design Patterns"
      hint="e.g., MVC, Repository, Factory"
      chips
      multiple
      :items="[
        'MVC',
        'Repository',
        'Factory',
        'Singleton',
        'Observer',
        'Strategy',
        'Dependency Injection'
      ]"
    />

    <!-- API Style -->
    <v-select
      v-model="configData.architecture.api_style"
      label="API Style"
      :items="['REST', 'GraphQL', 'gRPC', 'WebSocket', 'Mixed']"
    />

    <!-- Architecture Notes -->
    <v-textarea
      v-model="configData.architecture.notes"
      label="Architecture Notes"
      hint="Additional architectural decisions and constraints"
      rows="3"
    />
  </v-card-text>
</v-card>
```

#### Step 5: Features & Testing
```vue
<v-card>
  <v-card-title>Features & Quality Standards</v-card-title>
  <v-card-text>
    <!-- Core Features -->
    <v-textarea
      v-model="configData.features.core"
      label="Core Features"
      hint="Main functionality and capabilities"
      rows="3"
    />

    <!-- Testing Strategy -->
    <v-select
      v-model="configData.test_config.strategy"
      label="Testing Strategy"
      :items="['TDD', 'BDD', 'Manual', 'Mixed']"
    />

    <!-- Test Coverage Target -->
    <v-slider
      v-model="configData.test_config.coverage_target"
      label="Test Coverage Target"
      min="0"
      max="100"
      step="5"
      thumb-label
      suffix="%"
    />

    <!-- Testing Frameworks -->
    <v-combobox
      v-model="configData.test_config.frameworks"
      label="Testing Frameworks"
      hint="e.g., pytest, Jest, Cypress"
      chips
      multiple
      :items="['pytest', 'Jest', 'Mocha', 'Cypress', 'Playwright', 'Vitest']"
    />
  </v-card-text>
</v-card>
```

**Implementation Details**:

1. **Update `productForm` data structure**:
```javascript
const productForm = ref({
  // Basic fields
  name: '',
  description: '',

  // Vision fields
  visionType: 'none',
  visionPath: '',
  visionDocument: '',

  // Config data (nested structure)
  configData: {
    tech_stack: {
      languages: [],
      frontend: [],
      backend: [],
      database: [],
      infrastructure: [],
    },
    architecture: {
      pattern: '',
      design_patterns: [],
      api_style: '',
      notes: '',
    },
    features: {
      core: '',
    },
    test_config: {
      strategy: 'TDD',
      coverage_target: 80,
      frameworks: [],
    },
  },
})
```

2. **Update dialog to use v-stepper**:
```vue
<v-dialog v-model="showDialog" max-width="800" persistent>
  <v-card>
    <v-card-title>
      {{ editingProduct ? 'Edit Product' : 'Create New Product' }}
    </v-card-title>

    <v-stepper v-model="currentStep" alt-labels>
      <v-stepper-header>
        <v-stepper-item value="1" title="Basic Info" />
        <v-divider />
        <v-stepper-item value="2" title="Vision" />
        <v-divider />
        <v-stepper-item value="3" title="Tech Stack" />
        <v-divider />
        <v-stepper-item value="4" title="Architecture" />
        <v-divider />
        <v-stepper-item value="5" title="Features" />
      </v-stepper-header>

      <v-stepper-window>
        <v-stepper-window-item value="1">
          <!-- Basic info fields -->
        </v-stepper-window-item>

        <v-stepper-window-item value="2">
          <!-- Vision fields -->
        </v-stepper-window-item>

        <v-stepper-window-item value="3">
          <!-- Tech stack fields -->
        </v-stepper-window-item>

        <v-stepper-window-item value="4">
          <!-- Architecture fields -->
        </v-stepper-window-item>

        <v-stepper-window-item value="5">
          <!-- Features & testing fields -->
        </v-stepper-window-item>
      </v-stepper-window>

      <v-card-actions>
        <v-btn v-if="currentStep > 1" @click="currentStep--">
          Back
        </v-btn>
        <v-spacer />
        <v-btn variant="text" @click="closeDialog">Cancel</v-btn>
        <v-btn
          v-if="currentStep < 5"
          color="primary"
          @click="currentStep++"
        >
          Next
        </v-btn>
        <v-btn
          v-else
          color="primary"
          @click="saveProduct"
          :loading="saving"
        >
          {{ editingProduct ? 'Update' : 'Create' }}
        </v-btn>
      </v-card-actions>
    </v-stepper-window>
  </v-card>
</v-dialog>
```

3. **Update `saveProduct` method**:
```javascript
async function saveProduct() {
  if (!formValid.value) return

  saving.value = true
  try {
    const formData = new FormData()
    formData.append('name', productForm.value.name)
    formData.append('description', productForm.value.description || '')
    formData.append('vision_type', productForm.value.visionType)

    // Handle vision based on type
    if (productForm.value.visionType === 'file' && productForm.value.visionFile) {
      formData.append('vision_file', productForm.value.visionFile)
    } else if (productForm.value.visionType === 'inline') {
      formData.append('vision_document', productForm.value.visionDocument)
    }

    // Add config_data as JSON string
    formData.append('config_data', JSON.stringify(productForm.value.configData))

    if (editingProduct.value) {
      await productStore.updateProduct(editingProduct.value.id, formData)
    } else {
      await productStore.createProduct(formData)
    }

    closeDialog()
    await loadProducts()
  } catch (error) {
    console.error('Failed to save product:', error)
  } finally {
    saving.value = false
  }
}
```

4. **Update `editProduct` method** to populate form:
```javascript
function editProduct(product) {
  editingProduct.value = product

  // Populate basic fields
  productForm.value.name = product.name
  productForm.value.description = product.description || ''
  productForm.value.visionType = product.vision_type || 'none'
  productForm.value.visionPath = product.vision_path || ''
  productForm.value.visionDocument = product.vision_document || ''

  // Populate config_data with defaults
  const defaultConfig = {
    tech_stack: {
      languages: [],
      frontend: [],
      backend: [],
      database: [],
      infrastructure: [],
    },
    architecture: {
      pattern: '',
      design_patterns: [],
      api_style: '',
      notes: '',
    },
    features: {
      core: '',
    },
    test_config: {
      strategy: 'TDD',
      coverage_target: 80,
      frameworks: [],
    },
  }

  // Merge with existing config_data
  productForm.value.configData = {
    ...defaultConfig,
    ...(product.config_data || {}),
  }

  showDialog.value = true
}
```

**UX Considerations**:
- Step indicators show progress
- Each step validates independently
- "Back" button allows revision
- All fields optional except product name
- Help text explains each field's purpose
- Preset options reduce typing
- Allow custom entries in comboboxes
- Auto-save progress to localStorage (optional enhancement)

---

### Phase 3: Product Store Enhancement (30 minutes)

**Files to Modify**:
- `frontend/src/stores/products.js`

**Changes Required**:

1. **Update `createProduct` method**:
```javascript
async createProduct(formData) {
  const response = await fetch(`${API_BASE_URL}/products/`, {
    method: 'POST',
    credentials: 'include',
    body: formData, // FormData with config_data JSON string
  })

  if (!response.ok) {
    throw new Error('Failed to create product')
  }

  const product = await response.json()
  this.products.push(product)
  return product
}
```

2. **Update `updateProduct` method** (similar changes)

3. **Add config_data to product interface/type**

---

### Phase 4: Display Config Data in Product Details (30 minutes)

**Files to Modify**:
- `frontend/src/views/ProductDetailView.vue` (if exists)
- OR add config data display to product cards

**Display Options**:

1. **Expandable sections** in product cards:
```vue
<v-expansion-panels>
  <v-expansion-panel title="Technology Stack">
    <v-expansion-panel-text>
      <v-chip-group>
        <v-chip v-for="lang in product.config_data?.tech_stack?.languages">
          {{ lang }}
        </v-chip>
      </v-chip-group>
    </v-expansion-panel-text>
  </v-expansion-panel>

  <v-expansion-panel title="Architecture">
    <v-expansion-panel-text>
      <p><strong>Pattern:</strong> {{ product.config_data?.architecture?.pattern }}</p>
      <p><strong>API Style:</strong> {{ product.config_data?.architecture?.api_style }}</p>
    </v-expansion-panel-text>
  </v-expansion-panel>
</v-expansion-panels>
```

2. **Tooltip previews** on hover
3. **Full detail view** in dedicated product detail page

---

### Phase 5: Testing (30 minutes)

**Test Scenarios**:

1. **API Endpoint Tests** (`tests/api/test_products.py`):
```python
def test_create_product_with_config_data(client, auth_headers):
    """Test creating product with rich config_data"""
    config_data = {
        "tech_stack": {
            "languages": ["Python", "JavaScript"],
            "backend": ["FastAPI"],
            "database": ["PostgreSQL"],
        },
        "architecture": {
            "pattern": "Modular Monolith",
            "api_style": "REST",
        },
    }

    response = client.post(
        "/products/",
        data={
            "name": "Test Product",
            "description": "Test description",
            "vision_type": "inline",
            "vision_document": "Test vision",
            "config_data": json.dumps(config_data),
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["config_data"]["tech_stack"]["languages"] == ["Python", "JavaScript"]

def test_create_product_with_invalid_json(client, auth_headers):
    """Test that invalid JSON in config_data fails gracefully"""
    response = client.post(
        "/products/",
        data={
            "name": "Test Product",
            "config_data": "{invalid json}",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "Invalid config_data JSON" in response.json()["detail"]
```

2. **Frontend Component Tests** (Vitest):
```javascript
describe('ProductsView - Create Product Form', () => {
  it('should navigate through all form steps', async () => {
    const wrapper = mount(ProductsView)

    await wrapper.find('[data-test="create-button"]').trigger('click')

    // Step 1: Basic info
    expect(wrapper.find('[data-test="step-1"]').exists()).toBe(true)
    await wrapper.find('[data-test="next-button"]').trigger('click')

    // Step 2: Vision
    expect(wrapper.find('[data-test="step-2"]').exists()).toBe(true)
    await wrapper.find('[data-test="next-button"]').trigger('click')

    // ... test remaining steps
  })

  it('should save product with config_data', async () => {
    const wrapper = mount(ProductsView)
    const productStore = useProductStore()

    // Fill form
    await fillProductForm(wrapper, {
      name: 'Test Product',
      configData: {
        tech_stack: {
          languages: ['Python'],
        },
      },
    })

    await wrapper.find('[data-test="save-button"]').trigger('click')

    expect(productStore.createProduct).toHaveBeenCalledWith(
      expect.objectContaining({
        config_data: expect.stringContaining('Python'),
      })
    )
  })
})
```

3. **E2E Tests** (Playwright):
```javascript
test('create product with full configuration', async ({ page }) => {
  await page.goto('/products')
  await page.click('button:has-text("New Product")')

  // Step 1: Basic info
  await page.fill('[data-test="product-name"]', 'E2E Test Product')
  await page.click('button:has-text("Next")')

  // Step 2: Vision type
  await page.click('[data-test="vision-type-inline"]')
  await page.fill('[data-test="vision-document"]', 'Test vision document')
  await page.click('button:has-text("Next")')

  // Step 3: Tech stack
  await page.click('[data-test="languages-combobox"]')
  await page.click('text=Python')
  await page.click('text=JavaScript')
  await page.click('button:has-text("Next")')

  // Step 4: Architecture
  await page.selectOption('[data-test="architecture-pattern"]', 'Microservices')
  await page.click('button:has-text("Next")')

  // Step 5: Features & save
  await page.fill('[data-test="core-features"]', 'Test features')
  await page.click('button:has-text("Create")')

  // Verify product appears
  await expect(page.locator('text=E2E Test Product')).toBeVisible()
})
```

**Accessibility Tests**:
- Keyboard navigation through steps
- Screen reader compatibility
- WCAG 2.1 AA compliance
- Focus management
- Proper ARIA labels

---

## Files to Modify

### Backend
1. **`api/endpoints/products.py`** (lines 76-175, 177-220)
   - Add `config_data`, `vision_document`, `vision_type` parameters
   - Update create/update logic
   - Add JSON parsing with error handling

### Frontend
2. **`frontend/src/views/ProductsView.vue`** (lines 239-295)
   - Replace single-form dialog with v-stepper multi-step form
   - Add all new form fields with proper validation
   - Update save/edit methods to handle new data structure

3. **`frontend/src/stores/products.js`**
   - Update product type/interface to include new fields
   - Ensure FormData properly sent to API

### Testing
4. **`tests/api/test_products.py`**
   - Add tests for new endpoint parameters
   - Test JSON validation
   - Test vision_type validation

5. **`frontend/src/views/__tests__/ProductsView.spec.js`** (create if needed)
   - Component tests for multi-step form
   - Form validation tests
   - Save/cancel behavior tests

---

## Dependencies and Blockers

**Dependencies**:
- None - backend support already exists
- PostgreSQL database with Product table (already deployed)
- Vuetify 3 components (already in use)

**Potential Blockers**:
- None identified

**Related Handovers**:
- Handover 0041 (Agent Template Database Integration) - May want to reference product config_data
- Handover 0020 (Orchestrator Enhancement) - Will consume product config_data for agent context

---

## Success Criteria

### Functional Requirements
- [ ] Users can configure tech stack with multiple languages, frameworks, databases
- [ ] Users can specify architecture pattern and design patterns
- [ ] Users can choose vision type (none/file/inline) and provide vision content
- [ ] Users can set features and testing configuration
- [ ] All data stored correctly in `config_data` JSONB field
- [ ] Edit product loads existing config_data correctly
- [ ] Form validates required fields (product name only)
- [ ] Multi-step form allows forward/backward navigation

### Technical Requirements
- [ ] API endpoints accept and validate new parameters
- [ ] Invalid JSON in config_data returns 400 error
- [ ] Vision type constrained to valid values
- [ ] Frontend sends FormData with JSON-stringified config_data
- [ ] Product store updated to handle new fields
- [ ] Database queries use JSONB operators efficiently (if filtering)

### Quality Requirements
- [ ] All API tests pass (95%+ coverage for new code)
- [ ] All frontend component tests pass
- [ ] E2E test covers full workflow
- [ ] WCAG 2.1 AA accessibility compliance
- [ ] Keyboard navigation works correctly
- [ ] Screen reader announces steps and field labels
- [ ] Form performs well with large config_data (< 100ms)
- [ ] No console errors or warnings

### UX Requirements
- [ ] Multi-step form is intuitive and easy to navigate
- [ ] Help text explains purpose of each field
- [ ] Preset options reduce typing burden
- [ ] Custom entries allowed in all comboboxes
- [ ] Form auto-saves state (optional, nice-to-have)
- [ ] Loading states shown during save
- [ ] Success/error messages clear and actionable
- [ ] Mobile-responsive design works on tablet/phone

---

## Rollback Strategy

**If issues arise during implementation**:

1. **API Changes**:
   - New parameters are optional - existing API calls still work
   - Can deploy API changes independently
   - Rollback: Remove new parameters from endpoint

2. **Frontend Changes**:
   - Keep old form as fallback component
   - Feature flag: `USE_RICH_PRODUCT_FORM` environment variable
   - Rollback: Toggle feature flag, redeploy frontend

3. **Database**:
   - No schema changes required
   - `config_data` field already exists
   - No rollback needed

**Testing in Development**:
- Test with real PostgreSQL database
- Test with large config_data payloads
- Test browser compatibility (Chrome, Firefox, Safari)
- Test mobile responsiveness

---

## Documentation Requirements

**User Documentation**:
- [ ] Update user guide with screenshots of new form
- [ ] Document each config field and its purpose
- [ ] Provide examples of well-configured products

**Developer Documentation**:
- [ ] Document `config_data` schema structure
- [ ] Add API examples with config_data
- [ ] Document dot notation access patterns
- [ ] Update CLAUDE.md with new product capabilities

**Code Documentation**:
- [ ] JSDoc comments on new frontend functions
- [ ] Python docstrings on updated endpoint functions
- [ ] Inline comments explaining config_data structure

---

## Post-Implementation Tasks

1. **Handover to Orchestrator Team**:
   - Notify that rich product context now available
   - Provide examples of accessing config_data
   - Update agent prompts to use new context

2. **Database Optimization** (if needed):
   - Monitor query performance on config_data
   - Add specific GIN indexes if filtering on nested fields
   - Consider materialized views for common queries

3. **Future Enhancements** (not in scope):
   - Import/export product configurations
   - Product templates with pre-filled config_data
   - Validation rules for specific tech stack combinations
   - Integration with external tech stack databases
   - AI-powered tech stack recommendations

---

## References

**Code Locations**:
- Backend Product model: `src/giljo_mcp/models.py:57-140`
- API endpoints: `api/endpoints/products.py:76-175`
- Frontend view: `frontend/src/views/ProductsView.vue:239-295`
- Product store: `frontend/src/stores/products.js`

**Documentation**:
- [CLAUDE.md](../CLAUDE.md) - Development guidelines
- [Server Architecture](../docs/SERVER_ARCHITECTURE_TECH_STACK.md) - System architecture
- [Vuetify Stepper Component](https://vuetifyjs.com/en/components/steppers/) - UI component docs

**Related Handovers**:
- Handover 0017: Database Schema Enhancement (introduced config_data field)
- Handover 0020: Orchestrator Enhancement (consumes product context)
- Handover 0041: Agent Template Database Integration (related context system)

---

## Notes for Implementation Agent

**Recommended Sub-Agents**:
1. **TDD-Implementor**: API endpoint changes with tests
2. **UX-Designer**: Multi-step form design and accessibility
3. **Frontend-Tester**: Component and E2E tests

**Implementation Order**:
1. Start with API endpoints (backend-first approach)
2. Test API changes with curl/Postman
3. Implement frontend form step-by-step
4. Test each step independently
5. Add E2E tests last
6. Update documentation

**Common Pitfalls to Avoid**:
- Don't forget to JSON.stringify config_data before sending
- Don't forget to JSON.parse config_data when receiving
- Validate vision_type on backend (not just frontend)
- Handle missing config_data gracefully (default to empty dict)
- Test with malformed JSON in config_data
- Ensure backward compatibility (old products without config_data)

**Performance Considerations**:
- config_data should stay < 10KB (reasonable limit)
- Validate array lengths in tech_stack (max 20 items per field)
- Consider debouncing combobox inputs
- Lazy-load form steps if performance issues

**Questions for User**:
- Should we add product templates for common tech stacks?
- Should we validate tech stack combinations (e.g., Vue + FastAPI only)?
- Should we add import/export functionality?
- Should we add AI suggestions based on product description?

---

**Status**: Ready for implementation
**Next Agent**: Assign to TDD-Implementor + UX-Designer + Frontend-Tester team
