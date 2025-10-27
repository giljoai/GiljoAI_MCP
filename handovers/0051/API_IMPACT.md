# API Impact Analysis: Product Form Auto-Save & UX Polish

**Date**: 2025-10-27
**Handover**: 0051

## Summary

**No API changes required** for this handover. Auto-save functionality is implemented entirely on the frontend using LocalStorage. The existing product creation and update endpoints already support the `config_data` field (added in Handover 0042).

## Existing API Endpoints (Used, Not Modified)

### 1. Create Product

**Endpoint**: `POST /api/products/`
**Status**: Already supports all required fields
**Request Format**:
```
Content-Type: multipart/form-data

Fields:
- name: string (required)
- description: string (optional)
- config_data: string (optional, JSON string)
- vision_file: file (optional)
```

**Response**: `ProductResponse` with full product data including `config_data`

**No Changes Needed**: Endpoint already accepts and returns `config_data`.

---

### 2. Update Product

**Endpoint**: `PUT /api/products/{product_id}`
**Status**: Already supports all required fields
**Request Format**:
```
Content-Type: multipart/form-data

Fields:
- name: string (optional)
- description: string (optional)
- config_data: string (optional, JSON string)
```

**Response**: `ProductResponse` with updated product data including `config_data`

**No Changes Needed**: Endpoint already accepts and returns `config_data`.

---

### 3. Get Product

**Endpoint**: `GET /api/products/{product_id}`
**Status**: Returns all product data including `config_data`
**Response**: `ProductResponse` model

**No Changes Needed**: Already returns complete product data.

---

## API Service Layer (Frontend)

### Current Implementation

**File**: `frontend/src/services/api.js` (assumed location)

The API service layer may need a small fix if `config_data` is not being properly stringified before sending to backend.

### Potential Fix (Phase 1 Debugging)

```javascript
export default {
  products: {
    async create(productData) {
      const formData = new FormData()
      formData.append('name', productData.name)

      if (productData.description) {
        formData.append('description', productData.description)
      }

      // IMPORTANT: Backend expects config_data as JSON STRING, not object
      if (productData.configData) {
        formData.append('config_data', JSON.stringify(productData.configData))
      }

      return await axios.post('/api/products/', formData)
    },

    async update(productId, updates) {
      const formData = new FormData()

      if (updates.name !== undefined) {
        formData.append('name', updates.name)
      }

      if (updates.description !== undefined) {
        formData.append('description', updates.description)
      }

      // IMPORTANT: Backend expects config_data as JSON STRING, not object
      if (updates.configData !== undefined) {
        formData.append('config_data', JSON.stringify(updates.configData))
      }

      return await axios.put(`/api/products/${productId}`, formData)
    },
  },
}
```

**Note**: This is NOT a new API change - it's ensuring the existing API contract is followed correctly.

---

## Backend Endpoint Verification

### Current Implementation (Handover 0042)

**File**: `api/endpoints/products.py`

```python
@router.post("/", response_model=ProductResponse)
async def create_product(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    vision_file: Optional[UploadFile] = File(None),
    config_data: Optional[str] = Form(None),  # JSON string
    tenant_key: str = Depends(get_tenant_key),
):
    """Create a new product with optional vision document upload"""
    try:
        # Parse config_data JSON string
        config_dict: Dict[str, Any] = {}
        if config_data:
            config_dict = json.loads(config_data)

        # Create product
        product = Product(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            name=name,
            description=description,
            config_data=config_dict,  # Stored as JSONB
        )

        async with state.db_manager.get_session_async() as db:
            db.add(product)
            await db.commit()
            await db.refresh(product)

        # Return response with config_data
        return ProductResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            config_data=product.config_data,  # Returned as dict
            # ... other fields
        )
```

**Verification Needed** (Phase 1):
- Is `config_data` being saved correctly?
- Is `config_data` being returned correctly?
- Is JSON parsing working as expected?

**No API Changes**: Functionality already implemented, just needs verification.

---

## Database Schema

### Product Model

**File**: `src/giljo_mcp/models.py`

```python
class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True)
    tenant_key = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    vision_path = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Handover 0042: Rich product configuration
    config_data = Column(JSONB)  # JSONB column for flexible configuration

    # Handover 0049: Active product flag
    is_active = Column(Boolean, default=False, nullable=False, server_default=text('false'))
```

**No Schema Changes**: `config_data` column already exists (added in Handover 0042).

---

## API Response Model

### ProductResponse

**File**: `api/endpoints/products.py`

```python
class ProductResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    vision_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    project_count: int = 0
    task_count: int = 0
    has_vision: bool = False
    unfinished_projects: int = 0
    unresolved_tasks: int = 0
    vision_documents_count: int = 0

    # Handover 0042: Rich configuration data
    config_data: Optional[Dict[str, Any]] = None
    has_config_data: bool = False

    # Handover 0049: Active product flag
    is_active: bool = False

    class Config:
        from_attributes = True
```

**No Changes**: Response model already includes `config_data`.

---

## Network Traffic Analysis

### Expected Request (Create Product)

```http
POST /api/products/ HTTP/1.1
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="name"

Test Product
------WebKitFormBoundary
Content-Disposition: form-data; name="description"

Test description
------WebKitFormBoundary
Content-Disposition: form-data; name="config_data"

{"tech_stack":{"languages":"Python","frontend":"Vue 3","backend":"FastAPI","database":"PostgreSQL","infrastructure":"Docker"},"architecture":{"pattern":"Layered","design_patterns":"Repository","api_style":"REST","notes":"MVC"},"features":{"core":"User auth"},"test_config":{"strategy":"TDD","coverage_target":80,"frameworks":"pytest"}}
------WebKitFormBoundary--
```

**Key Points**:
- `config_data` sent as JSON string (not object)
- FormData encoding used
- All nested fields flattened into single JSON string

### Expected Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Test Product",
  "description": "Test description",
  "vision_path": null,
  "created_at": "2025-10-27T10:30:00Z",
  "updated_at": "2025-10-27T10:30:00Z",
  "project_count": 0,
  "task_count": 0,
  "has_vision": false,
  "unfinished_projects": 0,
  "unresolved_tasks": 0,
  "vision_documents_count": 0,
  "config_data": {
    "tech_stack": {
      "languages": "Python",
      "frontend": "Vue 3",
      "backend": "FastAPI",
      "database": "PostgreSQL",
      "infrastructure": "Docker"
    },
    "architecture": {
      "pattern": "Layered",
      "design_patterns": "Repository",
      "api_style": "REST",
      "notes": "MVC"
    },
    "features": {
      "core": "User auth"
    },
    "test_config": {
      "strategy": "TDD",
      "coverage_target": 80,
      "frameworks": "pytest"
    }
  },
  "has_config_data": true,
  "is_active": false
}
```

**Key Points**:
- `config_data` returned as nested object (not string)
- Backend parses JSON string and stores as JSONB
- Response includes all nested fields

---

## Rate Limiting Considerations

### Current Behavior

**No rate limiting** on product create/update endpoints currently.

### Auto-Save Impact

**Question**: Should we implement rate limiting to prevent excessive auto-save calls?

**Answer**: NO, because:
1. Auto-save only writes to LocalStorage (not backend)
2. User still clicks "Save" explicitly to persist to backend
3. Background API saves are disabled by default (`enableBackgroundSave: false`)

**Future Enhancement**: If we enable background API saves, consider:
- Throttling backend saves (e.g., max 1 save per 5 seconds)
- Adding rate limiting to PUT endpoint (e.g., 10 requests per minute)
- Using Redis to track save frequency per user

---

## Authentication & Authorization

### Current Requirements

**All product endpoints require authentication**:
- Valid JWT token in Authorization header
- User belongs to tenant (tenant isolation enforced)

**No Changes**: Auto-save respects existing auth requirements.

### Security Considerations

1. **LocalStorage Security**:
   - Data stored per-origin (isolated by domain)
   - No cross-site access possible
   - XSS mitigation via Vue's automatic escaping

2. **API Security**:
   - Existing authentication unchanged
   - Tenant isolation unchanged
   - Input validation unchanged (JSON schema validation)

3. **Data Exposure**:
   - Product data not sensitive (no passwords, tokens)
   - LocalStorage readable by user (acceptable)
   - No additional security risks introduced

---

## Error Handling

### Current Error Responses

**Validation Error (400)**:
```json
{
  "detail": "Invalid config_data JSON: Expecting property name enclosed in double quotes"
}
```

**Not Found (404)**:
```json
{
  "detail": "Product not found"
}
```

**Unauthorized (401)**:
```json
{
  "detail": "Not authenticated"
}
```

**Server Error (500)**:
```json
{
  "detail": "Internal server error"
}
```

**No Changes**: Error handling remains the same.

### Frontend Error Handling

**Enhanced Error Handling** (Phase 1):

```javascript
async function saveProduct() {
  try {
    // ... save logic ...
  } catch (error) {
    console.error('Failed to save product:', error)

    // Enhanced error messaging
    let errorMessage = 'Failed to save product'

    if (error.response) {
      // API error response
      if (error.response.status === 400) {
        errorMessage = 'Invalid form data: ' + error.response.data.detail
      } else if (error.response.status === 401) {
        errorMessage = 'Session expired. Please login again.'
      } else if (error.response.status === 500) {
        errorMessage = 'Server error. Please try again.'
      }
    } else if (error.request) {
      // Network error
      errorMessage = 'Network error. Please check your connection.'
    }

    showToast({
      message: errorMessage,
      type: 'error',
      duration: 5000,
    })

    // IMPORTANT: Don't close dialog on error
    // Dialog remains open so user can retry
  }
}
```

---

## Testing API Endpoints

### Manual Testing with curl

**Create Product**:
```bash
curl -X POST http://localhost:7272/api/products/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "name=Test Product" \
  -F "description=Test description" \
  -F "config_data={\"tech_stack\":{\"languages\":\"Python\"}}"
```

**Update Product**:
```bash
curl -X PUT http://localhost:7272/api/products/PRODUCT_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "name=Updated Product" \
  -F "config_data={\"tech_stack\":{\"languages\":\"Python, JavaScript\"}}"
```

**Get Product**:
```bash
curl -X GET http://localhost:7272/api/products/PRODUCT_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## API Versioning

**Current Version**: v1 (implicit, no version in URL)

**Future Consideration**: If API changes are needed in future:
- Version endpoints: `/api/v2/products/`
- Maintain backward compatibility with v1
- Auto-save composable supports both versions

**For Now**: No versioning needed, existing API sufficient.

---

## WebSocket Events

**Question**: Should auto-save trigger WebSocket events for real-time sync?

**Answer**: NO, because:
1. Auto-save only writes to LocalStorage (local only)
2. Explicit "Save" button persists to backend
3. WebSocket overhead unnecessary for draft data
4. No multi-user concurrent editing (yet)

**Future Enhancement**: If we add real-time collaboration:
- Emit `product:draft_changed` event
- Other users see "User X is editing..."
- Conflict resolution on final save

---

## Performance Impact

### API Load

**No impact** because:
- Auto-save writes to LocalStorage only
- No additional API calls during typing
- Same number of API calls as before (only on "Save" click)

### Database Load

**No impact** because:
- No additional database writes during typing
- Same number of writes as before (only on "Save" click)
- JSONB column efficient for structured data

### Network Traffic

**No impact** because:
- No additional network requests during typing
- Same payload size as before (configData already supported)

---

## Monitoring & Logging

### Recommended Metrics

**No new metrics needed**, but useful for debugging:

1. **Product Save Success Rate**:
   - Track successful vs. failed saves
   - Alert if failure rate > 5%

2. **Save Response Time**:
   - P50, P95, P99 latencies
   - Alert if P95 > 1 second

3. **Config Data Size**:
   - Average size of config_data field
   - Alert if > 100KB (potential abuse)

**Implementation**: Add to existing monitoring (Prometheus, DataDog, etc.)

---

## Rollback Plan

### API Rollback

**Not needed** - no API changes made.

### Frontend Rollback

If issues arise:
1. Disable auto-save composable
2. Revert to previous save behavior
3. No API changes needed

**Database Rollback**: Not needed - schema unchanged.

---

## Documentation Updates

### API Documentation

**No updates needed** - existing API documentation (Handover 0042) already covers `config_data` field.

### User Guide

**Update required**: Add section on auto-save behavior (see IMPLEMENTATION_PLAN.md).

---

## Conclusion

**Zero API impact** for this handover. All changes are frontend-only, leveraging existing API capabilities. The only potential fix is ensuring `config_data` is properly stringified before sending to backend (not an API change, just ensuring contract is followed).

---

**Next**: Proceed with implementation following IMPLEMENTATION_PLAN.md.
