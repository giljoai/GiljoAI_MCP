# Session Memory: Product Management System with File Upload

**Date:** 2025-10-04
**Session Type:** Feature Implementation Planning
**Status:** Design & Planning Complete - Ready for Sub-Agent Execution

---

## Session Overview

Successfully fixed the GiljoAI MCP server connection in Claude Code and designed a comprehensive product management system with vision document file upload capability. The session transitioned from troubleshooting MCP connectivity to planning a multi-tier implementation strategy using orchestrator-driven sub-agent coordination.

---

## Accomplishments

### 1. MCP Server Connection Fix ✅

**Problem:** GiljoAI MCP server showed "Failed to connect" in Claude Code despite backend/frontend running.

**Root Causes Identified:**
- `__main__.py` only displayed usage info, didn't launch MCP adapter
- Package not installed in editable mode
- MCP protocol format mismatch (old format vs JSON-RPC 2.0)
- Config validation failing in adapter startup

**Solutions Implemented:**

1. **Fixed `src/giljo_mcp/__main__.py`:**
   - Changed from info display to actual MCP adapter launcher
   - Now invokes `asyncio.run(adapter_main())`

2. **Installed Package:**
   ```bash
   pip install -e .
   ```

3. **Updated MCP Protocol Format (`src/giljo_mcp/mcp_adapter.py`):**
   - Changed from `type` field to `method` field (JSON-RPC 2.0)
   - Updated response format to use `jsonrpc: "2.0"`
   - Changed `parameters` to `inputSchema` for tools
   - Updated `initialize` response to match protocol version "2025-06-18"

4. **Made Config Loading Resilient:**
   - Wrapped config loading in try-catch
   - Falls back to environment variables if config invalid
   - No longer requires full database credentials for MCP adapter (HTTP-only client)

**Result:** MCP server now shows `✓ Connected` in Claude Code!

---

### 2. Product Management UI Enhancement ✅

**Implemented Vision Document File Upload UI:**

**Location:** `frontend/src/components/ProductSwitcher.vue`

**Features Added:**
- File upload/browse button with Vuetify `v-file-input`
- Drag & drop zone with visual feedback
- File type validation (.txt, .md, .pdf, .doc, .docx)
- File preview with size display
- Alternative path input (disabled when file selected)
- Styled drop zone with hover effects

**UI Components:**
```vue
- Drop zone with drag-over detection
- File input with browse button
- File preview chip (closable)
- OR separator for path alternative
- Disabled path input when file uploaded
```

**Event Handlers:**
- `handleDragOver()` - Visual feedback on drag
- `handleDragLeave()` - Reset on drag exit
- `handleDrop()` - Process dropped files
- `handleFileSelect()` - Handle browse selection
- `clearVisionFile()` - Remove selected file
- `formatFileSize()` - Human-readable sizes

---

### 3. Database Model Creation ✅

**Product Model Added:** `src/giljo_mcp/models.py` (lines 36-60)

```python
class Product(Base):
    """Product model - TOP-level organizational unit."""

    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    vision_path = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    meta_data = Column(JSON, default=dict)

    # Relationships
    projects = relationship("Project", back_populates="product")
    tasks = relationship("Task", back_populates="product")
```

**Updated Relationships:**
- `Project.product_id` - Foreign key to Product
- `Task.product_id` - Foreign key to Product
- Product is now the top-level organizational unit

---

## Pending Implementation

### Backend API Missing

**Current State:**
- Frontend has `api.products` calls but they're undefined
- No `api/endpoints/products.py` file exists
- No API routes registered for products
- No file upload handling implemented

### Identified Gaps

1. **Products API Endpoint** (`api/endpoints/products.py`) - Not created
2. **File Upload Handler** - Not implemented
3. **Frontend API Integration** (`frontend/src/services/api.js`) - Products API missing
4. **Database Migration** - Product table migration not created
5. **File Storage System** - No uploads directory structure

---

## Orchestrator Mission Created

**Comprehensive implementation plan documented for:**

### Architecture Requirements

**1. Database Layer:**
- Product model ✅ (already exists)
- Alembic migration needed
- Multi-tenant isolation via `tenant_key`

**2. File Upload System:**
- Directory structure: `uploads/vision_documents/{tenant_key}/`
- File validation: types, sizes, sanitization
- Secure storage with unique filenames
- Path return for database storage

**3. Backend API Endpoints:**
```
POST   /api/v1/products/                  - Create product + upload
GET    /api/v1/products/                  - List all (tenant filtered)
GET    /api/v1/products/{id}/             - Get single product
PUT    /api/v1/products/{id}/             - Update product
DELETE /api/v1/products/{id}/             - Delete product
GET    /api/v1/products/{id}/metrics/     - Get metrics
POST   /api/v1/products/{id}/upload-vision/ - Upload vision doc
```

**4. Frontend Integration:**
- Add products API object to `api.js`
- Update `ProductSwitcher.vue` to use FormData
- Implement multipart/form-data uploads
- Error handling and user feedback

### Recommended Sub-Agent Team

1. **database-expert**
   - Create Alembic migration for Product table
   - Test schema and relationships
   - Verify multi-tenant isolation

2. **tdd-implementor (Backend)**
   - Create `api/endpoints/products.py`
   - Implement file upload handling
   - Write endpoint tests
   - Register routes in `api/app.py`

3. **tdd-implementor (Frontend)** or **ux-designer**
   - Add products API to `frontend/src/services/api.js`
   - Update `ProductSwitcher.vue` createProduct function
   - Implement FormData multipart requests
   - Add error handling UI

4. **system-architect** (Consultation)
   - Review architecture decisions
   - Validate multi-tenant isolation
   - Security review for file uploads

---

## Technical Specifications

### File Upload Implementation Pattern

```python
@router.post("/")
async def create_product(
    name: str = Form(...),
    description: str = Form(None),
    vision_file: UploadFile = File(None),
    tenant_key: str = Header(...)
):
    # Validate file type
    # Save to uploads/vision_documents/{tenant_key}/
    # Create product with vision_path
    # Return product data
```

### Frontend Upload Pattern

```javascript
async function createProduct() {
  const formData = new FormData()
  formData.append('name', newProduct.value.name)
  formData.append('description', newProduct.value.description)
  if (visionFile.value) {
    formData.append('vision_file', visionFile.value[0])
  }

  await productStore.createProduct(formData)
}
```

---

## Acceptance Criteria

- [ ] User can create product via UI
- [ ] User can upload vision document (drag/drop or browse)
- [ ] File stored securely on server
- [ ] Product saved to database with tenant_key
- [ ] Product appears in ProductSwitcher dropdown
- [ ] User can switch between products
- [ ] File path stored and retrievable
- [ ] Error messages for invalid files
- [ ] Endpoints follow existing API patterns
- [ ] Database migration runs successfully

---

## Security Considerations

1. **File Validation:**
   - Server-side type checking (don't trust client)
   - File size limits (max 10MB recommended)
   - Filename sanitization (prevent directory traversal)

2. **Storage Security:**
   - Store files outside web root
   - Tenant-key based isolation
   - Unique filenames to prevent overwrites

3. **Access Control:**
   - Validate tenant_key on all operations
   - Ensure multi-tenant isolation
   - Authenticate file access requests

---

## File Paths Reference

### Backend
- Models: `src/giljo_mcp/models.py` (Product model lines 36-60)
- API Endpoint: `api/endpoints/products.py` (TO CREATE)
- API Router: `api/app.py` (register products router)
- Migrations: `migrations/versions/` (need to create)
- Uploads: `uploads/vision_documents/{tenant_key}/` (TO CREATE)

### Frontend
- Component: `frontend/src/components/ProductSwitcher.vue` (UI complete)
- Store: `frontend/src/stores/products.js` (skeleton exists)
- API Service: `frontend/src/services/api.js` (needs products API)

---

## Dependencies & Integration Points

**Existing Patterns to Follow:**
- API structure: Reference `api/endpoints/projects.py`
- Database filtering: Use tenant_key like other models
- File uploads: FastAPI `UploadFile` and `Form`
- Error handling: Consistent with existing endpoints
- Session management: Use existing database patterns

**Tech Stack:**
- Backend: FastAPI, SQLAlchemy, Alembic
- Frontend: Vue 3, Vuetify, Pinia
- Database: PostgreSQL 18 (required)
- Protocol: MCP via JSON-RPC 2.0

---

## Next Steps

### Immediate Actions (For Orchestrator Sub-Agent)

1. **Launch database-expert:**
   - Create Alembic migration for Product table
   - Test migration upgrade/downgrade
   - Verify relationships with Project and Task

2. **Launch tdd-implementor (Backend):**
   - Create `api/endpoints/products.py` with all CRUD endpoints
   - Implement file upload handling with validation
   - Write comprehensive tests
   - Register router in `api/app.py`

3. **Launch tdd-implementor (Frontend):**
   - Add products API object to `frontend/src/services/api.js`
   - Update `ProductSwitcher.vue` createProduct function
   - Implement FormData multipart upload
   - Add loading states and error handling

4. **Integration Testing:**
   - Test end-to-end file upload flow
   - Verify multi-tenant isolation
   - Test error scenarios
   - Validate file storage and retrieval

### Future Enhancements

- Vision document viewing/preview in UI
- Vision document versioning
- Bulk product import
- Product templates
- Advanced search/filtering
- Product analytics dashboard

---

## Session Learnings

### MCP Protocol Evolution
- MCP protocol uses JSON-RPC 2.0 (not custom message format)
- Protocol version "2025-06-18" is current
- Response format requires `jsonrpc: "2.0"` field
- Tools use `inputSchema` not `parameters`

### Multi-Tenant Architecture
- Product is now top-level organizational unit
- Projects belong to Products
- Tasks can belong to both Product and Project
- All entities require `tenant_key` for isolation

### File Upload Best Practices
- Use FastAPI `UploadFile` for streaming
- Validate on server (never trust client)
- Sanitize filenames before storage
- Store outside web root for security
- Use tenant-based directory structure

---

## Related Documentation

- MCP Tools Manual: `docs/manuals/MCP_TOOLS_MANUAL.md`
- Technical Architecture: `docs/TECHNICAL_ARCHITECTURE.md`
- Installation Guide: `INSTALL.md`
- Project README: `docs/README_FIRST.md`

---

## Session Metadata

**Duration:** ~1 hour
**Complexity:** Medium-High
**Components Modified:** 2
**Components Designed:** 5
**Lines Changed:** ~150
**Sub-Agents Recommended:** 3-4
**Status:** Ready for Implementation
