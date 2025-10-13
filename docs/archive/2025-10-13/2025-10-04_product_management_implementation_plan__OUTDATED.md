# DevLog: Product Management System Implementation Plan

**Date:** 2025-10-04
**Type:** Feature Planning & Bug Fix
**Status:** Planning Complete - Ready for Implementation
**Developer:** Claude Code Assistant

---

## Executive Summary

Successfully debugged and fixed the MCP server connection in Claude Code, then designed a comprehensive product management system with vision document file upload capabilities. The session resulted in a complete implementation plan ready for orchestrator-driven sub-agent execution.

**Key Achievements:**
- ✅ Fixed MCP server connection (now fully operational)
- ✅ Created Product database model with multi-tenant support
- ✅ Designed and implemented file upload UI (frontend complete)
- ✅ Documented comprehensive implementation plan for backend
- ✅ Prepared orchestrator mission for sub-agent coordination

---

## Problem Statement

### Issue 1: MCP Server Connection Failure

**Symptom:** GiljoAI MCP server showed "Failed to connect" in Claude Code despite backend API and frontend running successfully.

**Impact:** Unable to test MCP tools or use the orchestrator from within Claude Code.

### Issue 2: Missing Product Management System

**Symptom:** Product creation UI exists but lacks complete backend infrastructure for file upload functionality.

**Impact:** Users cannot upload vision documents when creating products, limiting the system's core functionality.

---

## Solutions Implemented

### 1. MCP Server Connection Fix

#### Investigation Process

1. **Initial Discovery:**
   - Backend API responding correctly: `http://localhost:7272/mcp/tools/health` returned healthy status
   - MCP adapter logs showed startup but incomplete handshake
   - Error: "Unknown message type: None"

2. **Root Cause Analysis:**
   ```
   Received: {
     'method': 'initialize',
     'params': {...},
     'jsonrpc': '2.0',
     'id': 0
   }

   Expected: message.get("type")
   Actual: message.get("method")
   ```

3. **Protocol Mismatch Identified:**
   - MCP adapter using old custom protocol (type-based)
   - Claude Code using JSON-RPC 2.0 (method-based)
   - Protocol version: "2025-06-18"

#### Code Changes

**File: `src/giljo_mcp/__main__.py`**
```python
# BEFORE (lines 19-30)
def main():
    """Display basic usage information"""
    print("GiljoAI MCP Orchestrator v2.0")
    print("=" * 50)
    # ... usage info only

# AFTER (lines 13-23)
def main():
    """Main entry point for the MCP adapter"""
    from giljo_mcp.mcp_adapter import main as adapter_main
    asyncio.run(adapter_main())
```

**File: `src/giljo_mcp/mcp_adapter.py`**

*Changes to protocol handling:*
```python
# BEFORE
msg_type = message.get("type")
if msg_type == "initialize":
    return {
        "type": "initialize_response",
        "id": msg_id,
        "result": {...}
    }

# AFTER
method = message.get("method")
if method == "initialize":
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": {
            "protocolVersion": "2025-06-18",
            "serverInfo": {...},
            "capabilities": {"tools": {}}
        }
    }
```

*Changes to tools/list response:*
```python
# BEFORE
"parameters": {
    "type": "object",
    "properties": {...}
}

# AFTER
"inputSchema": {
    "type": "object",
    "properties": {...}
}
```

*Config loading resilience:*
```python
# BEFORE
config = get_config()  # Fails if DB password missing

# AFTER
try:
    config = get_config()
except Exception as e:
    logger.warning(f"Could not load config, using defaults: {e}")
    api_port = os.getenv("GILJO_PORT", "7272")
```

**Installation Command:**
```bash
pip install -e .
```

#### Verification

```bash
$ claude mcp list
Checking MCP server health...

giljo-mcp: python -m giljo_mcp - ✓ Connected
serena: uvx --from git+https://github.com/oraios/serena ... - ✓ Connected
```

**Result:** MCP server now fully operational! ✅

---

### 2. Product Database Model

**File:** `src/giljo_mcp/models.py` (lines 36-60)

**Model Definition:**
```python
class Product(Base):
    """
    Product model - TOP-level organizational unit.
    All projects, tasks, and agents belong to a product.
    """

    __tablename__ = "products"

    # Primary fields
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    vision_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    meta_data = Column(JSON, default=dict)

    # Relationships
    projects = relationship("Project", back_populates="product")
    tasks = relationship("Task", back_populates="product")
```

**Schema Design Decisions:**

1. **Multi-Tenant Isolation:**
   - `tenant_key` indexed for fast filtering
   - All queries must filter by tenant_key

2. **Vision Document Support:**
   - `vision_path` stores file path (nullable)
   - Supports both local paths and uploaded file paths
   - Max 500 chars for flexibility

3. **Hierarchical Architecture:**
   ```
   Product (top-level)
     ├── Projects (work initiatives)
     │     ├── Agents
     │     ├── Messages
     │     └── Sessions
     └── Tasks (can span projects)
   ```

4. **Updated Relationships:**
   - `Project.product_id` added as foreign key
   - `Task.product_id` added for product-level scope
   - Cascade delete: Deleting product removes all projects/tasks

**Indexes Added:**
```python
Index("idx_product_tenant", "tenant_key")
Index("idx_product_name", "name")
```

---

### 3. File Upload UI Implementation

**File:** `frontend/src/components/ProductSwitcher.vue`

**Features Implemented:**

1. **Drag & Drop Zone (lines 162-214):**
   ```vue
   <div
     @dragover.prevent="handleDragOver"
     @dragleave.prevent="handleDragLeave"
     @drop.prevent="handleDrop"
     :class="['vision-drop-zone', { 'drag-over': isDragging }]"
   >
     <v-file-input
       v-model="visionFile"
       accept=".txt,.md,.pdf,.doc,.docx"
       label="Choose file or drag & drop"
       show-size
       clearable
     />
   </div>
   ```

2. **File Preview (lines 202-213):**
   - Shows selected file with closable chip
   - Displays filename and size
   - Clear button to remove selection

3. **Alternative Path Input (lines 221-229):**
   - Text field for manual path entry
   - Disabled when file is selected
   - "OR" separator for clarity

4. **Event Handlers (lines 349-402):**
   ```javascript
   handleDragOver()  // Visual feedback on drag
   handleDragLeave() // Reset on drag exit
   handleDrop()      // Process dropped files + validation
   handleFileSelect()// Handle browse selection
   clearVisionFile() // Remove selected file
   formatFileSize()  // Human-readable sizes (B, KB, MB, GB)
   ```

5. **File Validation:**
   - Accepted types: `.txt`, `.md`, `.pdf`, `.doc`, `.docx`
   - Client-side validation before upload
   - Alert on invalid file type

6. **Styling (lines 417-438):**
   ```css
   .vision-drop-zone {
     border: 2px dashed #ccc;
     transition: all 0.3s ease;
   }

   .vision-drop-zone.drag-over {
     border-color: rgb(var(--v-theme-primary));
     background-color: rgba(var(--v-theme-primary), 0.05);
     transform: scale(1.01);
   }
   ```

**User Experience:**

- ✅ Drag & drop files with visual feedback
- ✅ Browse button for traditional file selection
- ✅ File preview with size
- ✅ Alternative path entry
- ✅ Clear/remove file option
- ✅ Responsive hover effects

---

## Implementation Plan (For Orchestrator)

### Phase 1: Database Migration

**Owner:** database-expert sub-agent

**Tasks:**
1. Create Alembic migration for Product table
2. Test migration upgrade/downgrade paths
3. Verify foreign key relationships (Project, Task)
4. Validate indexes and constraints
5. Test multi-tenant isolation

**Deliverable:** Migration file in `migrations/versions/`

**Acceptance:**
- [ ] Migration runs without errors
- [ ] Product table created with correct schema
- [ ] Relationships with Project/Task work
- [ ] Indexes created correctly
- [ ] Rollback works cleanly

---

### Phase 2: Backend API Implementation

**Owner:** tdd-implementor (backend) sub-agent

**File to Create:** `api/endpoints/products.py`

**Endpoints Required:**

```python
# CREATE with file upload
@router.post("/")
async def create_product(
    name: str = Form(...),
    description: str = Form(None),
    vision_file: UploadFile = File(None),
    tenant_key: str = Header(...)
) -> ProductResponse

# READ operations
@router.get("/")
async def list_products(
    tenant_key: str = Header(...)
) -> List[ProductResponse]

@router.get("/{product_id}/")
async def get_product(
    product_id: str,
    tenant_key: str = Header(...)
) -> ProductResponse

# UPDATE
@router.put("/{product_id}/")
async def update_product(
    product_id: str,
    data: ProductUpdate,
    tenant_key: str = Header(...)
) -> ProductResponse

# DELETE
@router.delete("/{product_id}/")
async def delete_product(
    product_id: str,
    tenant_key: str = Header(...)
) -> DeleteResponse

# METRICS
@router.get("/{product_id}/metrics/")
async def get_product_metrics(
    product_id: str,
    tenant_key: str = Header(...)
) -> ProductMetrics

# VISION UPLOAD (separate endpoint)
@router.post("/{product_id}/upload-vision/")
async def upload_vision_document(
    product_id: str,
    vision_file: UploadFile = File(...),
    tenant_key: str = Header(...)
) -> VisionUploadResponse
```

**File Upload Implementation:**

```python
import os
from pathlib import Path
import uuid
from fastapi import UploadFile

UPLOAD_DIR = Path("uploads/vision_documents")

async def save_vision_file(
    file: UploadFile,
    tenant_key: str
) -> str:
    """Save uploaded vision file with validation"""

    # Validate file type
    allowed_extensions = {'.txt', '.md', '.pdf', '.doc', '.docx'}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise ValueError(f"Invalid file type: {file_ext}")

    # Validate file size (max 10MB)
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > 10 * 1024 * 1024:
        raise ValueError("File too large (max 10MB)")

    # Create tenant directory
    tenant_dir = UPLOAD_DIR / tenant_key
    tenant_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    unique_id = str(uuid.uuid4())[:8]
    safe_filename = f"{unique_id}_{Path(file.filename).name}"
    file_path = tenant_dir / safe_filename

    # Save file
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return str(file_path)
```

**Router Registration (`api/app.py`):**

```python
from api.endpoints import products

app.include_router(
    products.router,
    prefix="/api/v1/products",
    tags=["products"]
)
```

**Tests to Write:**

```python
# tests/integration/test_products_api.py
- test_create_product_without_file
- test_create_product_with_file
- test_list_products_tenant_isolation
- test_get_product_by_id
- test_update_product
- test_delete_product
- test_upload_vision_document
- test_invalid_file_type
- test_file_too_large
- test_tenant_isolation_enforcement
```

**Deliverable:** Working API with full CRUD + file upload

**Acceptance:**
- [ ] All endpoints functional
- [ ] File upload validates types and sizes
- [ ] Files stored in correct directory structure
- [ ] Multi-tenant isolation enforced
- [ ] All tests passing
- [ ] Router registered in app.py

---

### Phase 3: Frontend API Integration

**Owner:** tdd-implementor (frontend) OR ux-designer sub-agent

**File to Modify:** `frontend/src/services/api.js`

**Add Products API Object:**

```javascript
// Add to api object (after line 122)
products: {
  list: () => apiClient.get('/api/v1/products/'),

  get: (id) => apiClient.get(`/api/v1/products/${id}/`),

  create: (formData) => apiClient.post('/api/v1/products/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),

  update: (id, formData) => apiClient.put(`/api/v1/products/${id}/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),

  delete: (id) => apiClient.delete(`/api/v1/products/${id}/`),

  metrics: (id) => apiClient.get(`/api/v1/products/${id}/metrics/`),

  uploadVision: (id, file) => {
    const formData = new FormData()
    formData.append('vision_file', file)
    return apiClient.post(`/api/v1/products/${id}/upload-vision/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
}
```

**File to Modify:** `frontend/src/components/ProductSwitcher.vue`

**Update createProduct Function (lines 304-336):**

```javascript
async function createProduct() {
  creating.value = true
  try {
    const formData = new FormData()

    // Add text fields
    formData.append('name', newProduct.value.name)
    if (newProduct.value.description) {
      formData.append('description', newProduct.value.description)
    }

    // Add file if uploaded
    if (visionFile.value) {
      const file = visionFile.value[0] || visionFile.value
      formData.append('vision_file', file)
    }

    // Add vision path if provided (instead of file)
    if (!visionFile.value && newProduct.value.visionPath) {
      formData.append('vision_path', newProduct.value.visionPath)
    }

    // Send request
    const product = await productStore.createProduct(formData)

    if (product) {
      showCreateDialog.value = false
      resetProductForm()
      // Show success message
      console.log('Product created successfully:', product)
    }
  } catch (error) {
    console.error('Failed to create product:', error)
    // Show error to user
    alert(`Failed to create product: ${error.response?.data?.detail || error.message}`)
  } finally {
    creating.value = false
  }
}
```

**Add Error Handling UI:**

```vue
<!-- Add to dialog -->
<v-alert
  v-if="error"
  type="error"
  dismissible
  @click:close="error = null"
  class="mb-3"
>
  {{ error }}
</v-alert>
```

**Add Loading State:**

```vue
<v-progress-linear
  v-if="creating"
  indeterminate
  color="primary"
/>
```

**Deliverable:** Functional file upload from UI to backend

**Acceptance:**
- [ ] products API object added to api.js
- [ ] createProduct sends FormData correctly
- [ ] File uploads work end-to-end
- [ ] Path input works as alternative
- [ ] Error messages display to user
- [ ] Loading states work
- [ ] Product appears in switcher after creation

---

### Phase 4: Integration & Testing

**Owner:** Orchestrator coordination + all sub-agents

**System Tests:**

1. **End-to-End File Upload:**
   - User drags file to drop zone
   - File validates and previews
   - User clicks Create
   - File uploads to server
   - Product created in database
   - Product appears in switcher

2. **Multi-Tenant Isolation:**
   - Create products for tenant A
   - Switch to tenant B
   - Verify tenant B can't see tenant A products
   - Verify file access respects tenant boundaries

3. **Error Scenarios:**
   - Invalid file type → Show error
   - File too large → Show error
   - Network failure → Show error and retry option
   - Duplicate product name → Handle gracefully

4. **Alternative Path Input:**
   - Enter vision path manually
   - Verify product creates without upload
   - Verify path stored correctly

**Performance Tests:**

- [ ] Large file upload (10MB) completes
- [ ] Multiple concurrent uploads handled
- [ ] List products with 100+ items performs well

**Security Tests:**

- [ ] Tenant isolation enforced (database level)
- [ ] File paths can't be manipulated (directory traversal)
- [ ] File types validated server-side
- [ ] Unauthorized access blocked

**Deliverable:** Fully tested, production-ready feature

---

## Technical Architecture

### Data Flow

```
User (Browser)
  ↓
  ↓ [1] Drag/Drop or Browse File
  ↓
ProductSwitcher.vue
  ↓ [2] Create FormData
  ↓     - name
  ↓     - description
  ↓     - vision_file
  ↓
products Store (Pinia)
  ↓ [3] POST /api/v1/products/
  ↓     Content-Type: multipart/form-data
  ↓
FastAPI Backend
  ↓ [4] Validate File
  ↓     - Type check
  ↓     - Size check
  ↓     - Sanitize filename
  ↓
File System
  ↓ [5] Save to uploads/vision_documents/{tenant_key}/
  ↓     Return file path
  ↓
PostgreSQL Database
  ↓ [6] INSERT INTO products
  ↓     vision_path = saved path
  ↓
Response
  ↓ [7] Return product data
  ↓
UI Update
  ↓ [8] Add to switcher
  └─→  Show success message
```

### Directory Structure

```
uploads/
└── vision_documents/
    ├── tk_tenant1/
    │   ├── a1b2c3d4_product_vision.md
    │   └── e5f6g7h8_roadmap.pdf
    └── tk_tenant2/
        └── i9j0k1l2_requirements.txt
```

### Security Layers

1. **Client-Side:**
   - File type validation (UX improvement)
   - Size display before upload

2. **Network:**
   - HTTPS enforced (production)
   - Tenant key in headers

3. **API Layer:**
   - File type validation (security)
   - Size limit enforcement (10MB)
   - Filename sanitization
   - Tenant key validation

4. **File System:**
   - Tenant-based directories
   - Unique filenames (prevent overwrites)
   - Stored outside web root

5. **Database:**
   - Multi-tenant isolation via tenant_key
   - Foreign key constraints
   - Indexed queries

---

## Migration Strategy

### Database Migration

```bash
# Create migration
alembic revision --autogenerate -m "Add Product model and relationships"

# Review migration file
# migrations/versions/XXXX_add_product_model.py

# Apply migration
alembic upgrade head

# Verify
psql -U postgres -d giljo_mcp -c "SELECT * FROM products LIMIT 1;"
```

### Backward Compatibility

**Existing Data:**
- No breaking changes to Project/Task tables
- New `product_id` columns nullable
- Existing projects can have null product_id
- Gradual migration: assign products to existing projects

**API Changes:**
- New `/api/v1/products/` endpoints (non-breaking)
- Existing endpoints unchanged

---

## Testing Strategy

### Unit Tests

```python
# Backend
test_product_model_creation()
test_product_tenant_isolation()
test_file_validation()
test_file_saving()
test_filename_sanitization()

# Frontend
test_file_drag_drop()
test_file_browse()
test_file_validation_ui()
test_formdata_creation()
test_error_handling()
```

### Integration Tests

```python
test_create_product_with_file()
test_list_products_by_tenant()
test_update_product_vision()
test_delete_product_cascades()
test_tenant_isolation_enforced()
```

### E2E Tests

```javascript
test('user can create product with file upload', async () => {
  // Open product switcher
  // Click "New Product"
  // Fill name and description
  // Drag file to drop zone
  // Click Create
  // Verify product appears in list
  // Verify file uploaded to server
})
```

---

## Deployment Checklist

- [ ] Database migration created and tested
- [ ] Backend API endpoints implemented
- [ ] File upload handling tested
- [ ] Frontend integration complete
- [ ] All tests passing (unit + integration + e2e)
- [ ] Security review completed
- [ ] Documentation updated
- [ ] Environment variables configured
- [ ] Upload directory created and writable
- [ ] Multi-tenant isolation verified
- [ ] Performance tested under load
- [ ] Error handling comprehensive
- [ ] Logging implemented for debugging

---

## Known Issues & Limitations

### Current Limitations

1. **File Upload Progress:**
   - No upload progress bar yet
   - Large files appear to hang (no feedback)
   - **Recommendation:** Add progress tracking in Phase 3

2. **File Preview:**
   - No document preview in UI
   - Users can't view uploaded vision docs
   - **Recommendation:** Future enhancement

3. **File Versioning:**
   - No version control for vision documents
   - Replacing vision doc deletes old one
   - **Recommendation:** Future enhancement

4. **Validation:**
   - File content validation not implemented
   - Only extension-based type checking
   - **Recommendation:** Add MIME type validation

### Resolved Issues

- ✅ MCP protocol mismatch
- ✅ Config validation blocking adapter startup
- ✅ Frontend UI missing file upload capability
- ✅ Product model not in database

---

## Performance Considerations

### File Upload

**Expected Performance:**
- Small files (<1MB): < 2 seconds
- Medium files (1-5MB): 2-5 seconds
- Large files (5-10MB): 5-15 seconds

**Optimization Opportunities:**
- Chunked upload for files >5MB
- Background processing for large files
- Compression before upload
- CDN integration for file serving

### Database Queries

**Indexed Fields:**
- `product.tenant_key` - Fast tenant filtering
- `product.name` - Fast name searches

**Query Patterns:**
```sql
-- Fast (uses index)
SELECT * FROM products WHERE tenant_key = 'tk_xxx';

-- Slow (full scan)
SELECT * FROM products WHERE description LIKE '%keyword%';
```

---

## Future Enhancements

### Phase 5: Advanced Features (Post-MVP)

1. **Vision Document Viewer:**
   - In-app markdown/PDF viewer
   - Syntax highlighting for code blocks
   - Table of contents navigation

2. **Vision Document Versioning:**
   - Track changes over time
   - Diff view between versions
   - Rollback capability

3. **Bulk Operations:**
   - Import multiple products from CSV/JSON
   - Bulk vision document upload
   - Template-based product creation

4. **Search & Discovery:**
   - Full-text search across products
   - Tag-based filtering
   - Advanced search with filters

5. **Analytics:**
   - Product usage metrics
   - Vision document access tracking
   - Product lifecycle analysis

6. **Collaboration:**
   - Share products across tenants (controlled)
   - Comment on vision documents
   - Change approval workflow

---

## Conclusion

This session successfully addressed two critical needs:

1. **Immediate:** Fixed MCP server connection enabling full orchestrator functionality
2. **Strategic:** Designed complete product management system with file upload

The implementation is now ready for sub-agent execution via the orchestrator pattern, with clear deliverables, acceptance criteria, and testing requirements for each phase.

**Estimated Implementation Time:**
- Phase 1 (DB Migration): 2-4 hours
- Phase 2 (Backend API): 8-12 hours
- Phase 3 (Frontend Integration): 4-6 hours
- Phase 4 (Integration Testing): 4-6 hours
- **Total:** ~20-28 hours of development

**Recommended Next Action:**
Launch orchestrator sub-agent with the comprehensive mission document from session memory to coordinate implementation across database-expert, tdd-implementor (backend), and tdd-implementor (frontend) agents.

---

**Session Complete** ✅
