# API Changes: Single Active Product Architecture

**Handover**: 0050
**API Version**: v1
**Breaking Changes**: NO

---

## Overview

This handover modifies 3 existing endpoints and adds 1 new endpoint. All changes are backward-compatible - existing API clients will continue to work, but new clients can utilize enhanced response fields for better UX.

---

## Modified Endpoints

### 1. `POST /api/v1/products/{product_id}/activate`

**Purpose**: Activate a product (sets `is_active=True`)

**Authentication**: Required (JWT)

**Changes**: Response now includes `previous_active_product` field

#### Request

**No changes** - remains the same:

```http
POST /api/v1/products/{product_id}/activate
Authorization: Bearer <jwt_token>
```

**Path Parameters**:
- `product_id` (UUID, required): ID of product to activate

**Body**: None

#### Response (Modified)

**Status Code**: 200 OK

**Response Body**:

```json
{
  "id": "uuid",
  "name": "Product Name",
  "description": "Product description",
  "vision_path": "/path/to/vision.md",
  "created_at": "2025-10-27T10:00:00Z",
  "updated_at": "2025-10-27T10:05:00Z",
  "project_count": 5,
  "task_count": 12,
  "has_vision": true,
  "unfinished_projects": 2,
  "unresolved_tasks": 8,
  "vision_documents_count": 3,
  "config_data": { "tech_stack": {...} },
  "has_config_data": true,
  "is_active": true,
  "previous_active_product": {
    "id": "uuid",
    "name": "Previous Product Name",
    "active_projects_count": 2
  }
}
```

**NEW Field**: `previous_active_product`

- **Type**: `object | null`
- **Description**: Information about the product that was deactivated by this activation
- **Null When**: This is the first active product (no previous active)
- **Object Structure**:
  - `id` (string): UUID of previous active product
  - `name` (string): Name of previous active product
  - `active_projects_count` (integer): Number of projects with `status='active'` under that product

**Use Case**: Frontend can show warning dialog with this info before confirming activation.

#### Error Responses

**404 Not Found**:
```json
{
  "detail": "Product not found"
}
```

**403 Forbidden**:
```json
{
  "detail": "Not authorized to activate this product"
}
```

#### Example cURL

```bash
# First activation (no previous)
curl -X POST http://localhost:7272/api/v1/products/abc-123/activate \
  -H "Authorization: Bearer $JWT_TOKEN"

# Response:
# {
#   "id": "abc-123",
#   "name": "Product A",
#   "is_active": true,
#   "previous_active_product": null
# }

# Second activation (with previous)
curl -X POST http://localhost:7272/api/v1/products/def-456/activate \
  -H "Authorization: Bearer $JWT_TOKEN"

# Response:
# {
#   "id": "def-456",
#   "name": "Product B",
#   "is_active": true,
#   "previous_active_product": {
#     "id": "abc-123",
#     "name": "Product A",
#     "active_projects_count": 2
#   }
# }
```

---

### 2. `DELETE /api/v1/products/{product_id}`

**Purpose**: Delete a product

**Authentication**: Required (JWT)

**Changes**: Response now includes `was_active` field

#### Request

**No changes** - remains the same:

```http
DELETE /api/v1/products/{product_id}
Authorization: Bearer <jwt_token>
```

**Path Parameters**:
- `product_id` (UUID, required): ID of product to delete

**Body**: None

#### Response (Modified)

**Status Code**: 200 OK

**Response Body**:

```json
{
  "success": true,
  "message": "Product 'Product Name' deleted successfully",
  "was_active": true
}
```

**NEW Field**: `was_active`

- **Type**: `boolean`
- **Description**: Whether the deleted product was active at time of deletion
- **Use Case**: Frontend knows to refresh active product indicator if `true`

#### Error Responses

**404 Not Found**:
```json
{
  "detail": "Product not found"
}
```

**403 Forbidden**:
```json
{
  "detail": "Not authorized to delete this product"
}
```

**400 Bad Request** (if product has dependencies):
```json
{
  "detail": "Cannot delete product with active projects"
}
```

#### Example cURL

```bash
curl -X DELETE http://localhost:7272/api/v1/products/abc-123 \
  -H "Authorization: Bearer $JWT_TOKEN"

# Response if product was active:
# {
#   "success": true,
#   "message": "Product 'Product A' deleted successfully",
#   "was_active": true
# }

# Response if product was not active:
# {
#   "success": true,
#   "message": "Product 'Product B' deleted successfully",
#   "was_active": false
# }
```

---

### 3. `PATCH /api/v1/projects/{project_id}` (Validation Change)

**Purpose**: Update project fields (including status)

**Authentication**: Required (JWT)

**Changes**: New validation when setting `status='active'`

#### Request

**No changes to request format**:

```http
PATCH /api/v1/projects/{project_id}
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "status": "active"
}
```

**Path Parameters**:
- `project_id` (UUID, required): ID of project to update

**Body**:
```json
{
  "name": "string (optional)",
  "description": "string (optional)",
  "status": "planning | active | completed | on_hold (optional)",
  "alias": "string (optional)"
}
```

#### Response

**Status Code**: 200 OK (if validation passes)

**Response Body**: (unchanged)
```json
{
  "id": "uuid",
  "name": "Project Name",
  "status": "active",
  "product_id": "uuid",
  // ... other project fields
}
```

#### NEW Error Response

**Status Code**: 400 Bad Request

**Condition**: Attempting to activate a project whose parent product is not active

**Response Body**:
```json
{
  "detail": "Cannot activate project - parent product 'Product Name' is not active. Please activate the product first."
}
```

#### Validation Logic

When `status='active'` is in the request:
1. Backend fetches parent product (via `project.product_id`)
2. Checks if `parent_product.is_active == True`
3. If `False`, returns 400 error with message
4. If `True`, allows status update to proceed

#### Example cURL

```bash
# Attempt to activate project with inactive parent
curl -X PATCH http://localhost:7272/api/v1/projects/proj-123 \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "active"}'

# Response (if parent product inactive):
# Status: 400 Bad Request
# {
#   "detail": "Cannot activate project - parent product 'Product A' is not active. Please activate the product first."
# }

# After activating parent product:
curl -X POST http://localhost:7272/api/v1/products/prod-abc/activate \
  -H "Authorization: Bearer $JWT_TOKEN"

# Retry project activation:
curl -X PATCH http://localhost:7272/api/v1/projects/proj-123 \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "active"}'

# Response (now succeeds):
# Status: 200 OK
# {
#   "id": "proj-123",
#   "status": "active",
#   ...
# }
```

---

## New Endpoints

### 4. `POST /api/v1/products/refresh-active` (NEW)

**Purpose**: Get current active product info (for store refresh after deletions)

**Authentication**: Required (JWT)

**Status**: NEW in Handover 0050

#### Request

```http
POST /api/v1/products/refresh-active
Authorization: Bearer <jwt_token>
```

**Path Parameters**: None

**Query Parameters**: None

**Body**: None

#### Response

**Status Code**: 200 OK

**Response Body**:

```json
{
  "active_product": {
    "id": "uuid",
    "name": "Product Name",
    "active_projects_count": 3
  },
  "timestamp": "2025-10-27T10:30:00Z"
}
```

**Response When No Active Product**:
```json
{
  "active_product": null,
  "timestamp": "2025-10-27T10:30:00Z"
}
```

**Fields**:
- `active_product` (object | null): Current active product info, or null if none
  - `id` (string): UUID of active product
  - `name` (string): Name of active product
  - `active_projects_count` (integer): Number of active projects
- `timestamp` (string): ISO 8601 timestamp of when data was fetched

**Use Case**: Frontend calls this after deleting a product to ensure store state is synchronized with backend.

#### Error Responses

**503 Service Unavailable**:
```json
{
  "detail": "Database not available"
}
```

**401 Unauthorized**:
```json
{
  "detail": "Not authenticated"
}
```

#### Example cURL

```bash
curl -X POST http://localhost:7272/api/v1/products/refresh-active \
  -H "Authorization: Bearer $JWT_TOKEN"

# Response (with active product):
# {
#   "active_product": {
#     "id": "abc-123",
#     "name": "Product A",
#     "active_projects_count": 2
#   },
#   "timestamp": "2025-10-27T10:30:00.123456Z"
# }

# Response (no active product):
# {
#   "active_product": null,
#   "timestamp": "2025-10-27T10:30:00.123456Z"
# }
```

---

## Multi-Tenant Isolation

**ALL ENDPOINTS** enforce multi-tenant isolation:

1. Active product info is scoped to `current_user.tenant_key`
2. Product activation only affects products within user's tenant
3. Project validation checks parent product within same tenant
4. No cross-tenant data leakage

**Test**: Two tenants can each have one active product independently.

---

## Backward Compatibility

### Existing Clients

**Will Continue to Work**: Existing API clients that don't expect new fields will continue to function normally. New fields are additive.

### New Clients

**Can Utilize**:
- `previous_active_product` for warning UX
- `was_active` for store refresh logic
- `refresh-active` endpoint for explicit state sync
- Enhanced error messages for better UX

### Migration Path

**Phase 1** (Immediate): Deploy with new fields
**Phase 2** (2 weeks): Update frontend to utilize new fields
**Phase 3** (Optional): Deprecate old behavior (if needed)

**No Breaking Changes**: Old API clients never break.

---

## Performance Impact

### Activation Endpoint

**Additional Query**: 1 extra query to fetch active product info
**Performance**: +5-10ms (negligible)
**Optimization**: Active product info query uses indexed `tenant_key` + `is_active`

### Deletion Endpoint

**No Additional Query**: `was_active` read from product object already fetched
**Performance**: <1ms overhead

### Refresh Endpoint

**Query Count**: 2 queries (find active product + count active projects)
**Performance**: <20ms typical
**Caching**: Not needed (called infrequently, only after deletions)

---

## API Documentation Updates

### OpenAPI/Swagger

Update `api/openapi.yaml` (if exists) or Swagger UI with:

1. **New Response Field**: `previous_active_product` in `POST /products/{id}/activate`
2. **New Response Field**: `was_active` in `DELETE /products/{id}`
3. **New Endpoint**: `POST /products/refresh-active`
4. **Enhanced Error**: 400 response in `PATCH /projects/{id}` for inactive parent

### Postman Collection

Update Postman collection with:
- Example responses showing new fields
- Test case for activating second product (previous_active_product populated)
- Test case for project activation validation error

---

## Security Considerations

### Authorization

**All endpoints** require authentication:
- JWT token in `Authorization: Bearer` header
- Tenant isolation via `current_user.tenant_key`

### Validation

- Product IDs validated (must exist, must belong to tenant)
- Project IDs validated (must exist, must belong to tenant)
- Parent product existence validated before project activation

### Rate Limiting

**Recommendation**: Apply rate limiting to activation endpoints:
- `POST /products/{id}/activate`: 10 requests/minute per tenant
- `POST /products/refresh-active`: 60 requests/minute per tenant

**Rationale**: Prevent rapid activation/deactivation abuse.

---

## Error Code Reference

| Status Code | Endpoint | Condition |
|-------------|----------|-----------|
| 200 | All | Success |
| 400 | `PATCH /projects/{id}` | Parent product not active |
| 400 | `DELETE /products/{id}` | Product has dependencies |
| 401 | All | Not authenticated |
| 403 | `POST /activate`, `DELETE` | Not authorized |
| 404 | `POST /activate`, `DELETE` | Product not found |
| 503 | `POST /refresh-active` | Database unavailable |

---

## Testing API Changes

### Unit Tests

Create `tests/api/test_product_activation_api.py`:
- Test activation returns `previous_active_product`
- Test deletion returns `was_active`
- Test project activation validation
- Test refresh endpoint
- Test multi-tenant isolation

### Integration Tests

Create `tests/integration/test_single_active_product_flow.py`:
- Full flow: activate A → activate B → verify A deactivated
- Delete active product → verify refresh returns null
- Activate project with inactive parent → verify 400 error

### Manual Testing

**Postman/Insomnia**:
1. Activate Product A → Verify `previous_active_product: null`
2. Activate Product B → Verify `previous_active_product` shows Product A
3. Delete Product B → Verify `was_active: true`
4. Call refresh → Verify `active_product: null`

---

## Client Implementation Examples

### JavaScript (Axios)

```javascript
// Activate product with warning handling
async function activateProductWithWarning(productId) {
  try {
    const response = await axios.post(
      `/api/v1/products/${productId}/activate`
    )

    if (response.data.previous_active_product) {
      // Show warning dialog
      const confirmed = await showWarningDialog(
        response.data.previous_active_product
      )
      if (!confirmed) {
        return // User cancelled
      }
    }

    // Update UI state
    updateActiveProduct(response.data)
  } catch (error) {
    console.error('Activation failed:', error.response?.data?.detail)
  }
}

// Delete product with store refresh
async function deleteProductWithRefresh(productId) {
  try {
    const response = await axios.delete(
      `/api/v1/products/${productId}`
    )

    if (response.data.was_active) {
      // Refresh active product in store
      await axios.post('/api/v1/products/refresh-active')
    }
  } catch (error) {
    console.error('Deletion failed:', error.response?.data?.detail)
  }
}
```

### Python (httpx)

```python
async def activate_product_with_warning(product_id: str, client: httpx.AsyncClient):
    """Activate product with warning handling."""
    response = await client.post(
        f"/api/v1/products/{product_id}/activate"
    )
    response.raise_for_status()
    data = response.json()

    if data.get("previous_active_product"):
        # Show warning to user
        previous = data["previous_active_product"]
        print(f"Warning: This will deactivate {previous['name']}")
        print(f"Active projects: {previous['active_projects_count']}")

        confirm = input("Proceed? (y/n): ")
        if confirm.lower() != 'y':
            return None

    return data
```

---

## Summary of Changes

| Endpoint | Change Type | Breaking? | New Field/Validation |
|----------|-------------|-----------|----------------------|
| `POST /products/{id}/activate` | Response Enhanced | NO | `previous_active_product` |
| `DELETE /products/{id}` | Response Enhanced | NO | `was_active` |
| `PATCH /projects/{id}` | Validation Added | NO | 400 error for inactive parent |
| `POST /products/refresh-active` | New Endpoint | N/A | New endpoint |

**Total Changes**: 3 modified endpoints, 1 new endpoint
**Breaking Changes**: NONE
**Backward Compatible**: YES

---

**End of API Changes Documentation**
