# Product Fixes Session - Post-Refactoring Bug Fixes

**Date**: 2025-11-12
**Context**: Fixed product creation and display issues introduced during Handover 0126 (Products Modularization)
**Branch**: `master` (backup branch: `prior_to_major_refactor_november`)

---

## Summary

During the major refactoring project (Handovers 0120-0130), product creation and display functionality was broken. This session identified and fixed three critical issues:

1. **422 Error** - Frontend sending FormData instead of JSON
2. **500 Error** - SQLAlchemy lazy-loading issue with vision_documents relationship
3. **Products Not Displaying** - Backend filtering out inactive products by default

---

## Issues Fixed

### 1. Product Creation - 422 Unprocessable Entity

**Symptom**: `POST /api/v1/products/` returned 422 error
**Root Cause**: Frontend/backend content-type mismatch after Handover 0126 refactoring

**Before Refactoring**:
- Frontend sent `multipart/form-data` (FormData)
- Backend accepted FormData (legacy approach)

**After Refactoring** (broken):
- Frontend still sent `multipart/form-data` ❌
- Backend expected `application/json` (Pydantic models) ❌
- **Mismatch**: FastAPI couldn't deserialize FormData to `ProductCreate` BaseModel

**Fix**: Updated frontend to send JSON payloads

**File**: `frontend/src/services/api.js`

**Changes**:
```javascript
// BEFORE (broken - sent FormData)
create: (data) => {
  const formData = new FormData()
  formData.append('name', data.name)
  formData.append('description', data.description)
  formData.append('project_path', data.projectPath)
  return apiClient.post('/api/v1/products/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// AFTER (fixed - sends JSON)
create: (data) => {
  const payload = {
    name: data.name,
    description: data.description || null,
    project_path: data.projectPath || null,
  }
  return apiClient.post('/api/v1/products/', payload)
}
```

**Same fix applied to**:
- `api.products.create()` (lines 108-117)
- `api.products.update()` (lines 118-127)

---

### 2. Product Retrieval - 500 Internal Server Error

**Symptom**: Product created successfully, but fetching it returned 500 error
**Root Cause**: SQLAlchemy lazy-loading `vision_documents` relationship outside async context

**Error Message**:
```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called;
can't call await_only() here. Was IO attempted in an unexpected place?
```

**Stack Trace**:
```
File "src/giljo_mcp/services/product_service.py", line 185
  "vision_path": product.primary_vision_path
File "src/giljo_mcp/models/products.py", line 187
  if not self.vision_documents:  # Lazy load triggered!
```

**Problem**: The `primary_vision_path` property accessed `self.vision_documents`, which triggered lazy-loading. The SQLAlchemy async session was no longer available at this point.

**Fix**: Eager-load `vision_documents` relationship in the query

**File**: `src/giljo_mcp/services/product_service.py`

**Changes**:
```python
# BEFORE (broken - lazy loading)
async def get_product(self, product_id: str, include_metrics: bool = True):
    stmt = select(Product).where(
        and_(
            Product.id == product_id,
            Product.tenant_key == self.tenant_key,
            Product.deleted_at.is_(None)
        )
    )
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()

# AFTER (fixed - eager loading)
async def get_product(self, product_id: str, include_metrics: bool = True):
    # Eagerly load vision_documents to prevent lazy-loading issues
    stmt = select(Product).options(
        selectinload(Product.vision_documents)  # ← Added this!
    ).where(
        and_(
            Product.id == product_id,
            Product.tenant_key == self.tenant_key,
            Product.deleted_at.is_(None)
        )
    )
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
```

**Location**: Lines 165-176

---

### 3. Products Not Showing in GUI

**Symptom**: Created products not visible on Products page (`http://10.1.0.164:7274/Products`)
**Root Cause**: Backend endpoint defaulted to hiding inactive products after refactoring

**Investigation**:
- Verified product existed in database: ✅ (ID: `25bb2e7e-b983-4f33-83a7-b7045f9d9e48`)
- Product `is_active` status: `false` (default for new products)
- Frontend request: `GET /api/v1/products/` (no params)
- Backend behavior: Only returned `is_active=true` products ❌

**Before Refactoring**:
- Products page showed ALL products (active + inactive)
- Users could activate/deactivate as needed

**After Refactoring** (broken):
- Backend filtered out inactive products by default
- Parameter `include_inactive` defaulted to `False`

**Fix 1**: Change backend default to show all products

**File**: `api/endpoints/products/crud.py`

```python
# BEFORE (broken)
@router.get("/", response_model=List[ProductResponse])
async def list_products(
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
    include_inactive: bool = Query(False, description="Include inactive products"),
) -> List[ProductResponse]:

# AFTER (fixed)
@router.get("/", response_model=List[ProductResponse])
async def list_products(
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
    include_inactive: bool = Query(True, description="Include inactive products (default: True, always show all)"),
) -> List[ProductResponse]:
```

**Location**: Line 90

**Fix 2**: Sort products with active first

**File**: `src/giljo_mcp/services/product_service.py`

```python
# BEFORE (sorted by creation date only)
stmt = (
    select(Product)
    .where(and_(*conditions))
    .options(selectinload(Product.vision_documents))
    .order_by(Product.created_at.desc())
)

# AFTER (active products first, then by creation date)
stmt = (
    select(Product)
    .where(and_(*conditions))
    .options(selectinload(Product.vision_documents))
    .order_by(Product.is_active.desc(), Product.created_at.desc())
)
```

**Location**: Lines 240-247

**Rationale**: Users should always see all products. Active products appear at the top for easy access. Users can delete products if they don't want to see them.

---

## Files Modified

| File | Lines Changed | Purpose |
|------|---------------|---------|
| `frontend/src/services/api.js` | 108-127 | Change FormData → JSON for create/update |
| `src/giljo_mcp/services/product_service.py` | 165-176 | Add eager loading for vision_documents (get_product) |
| `src/giljo_mcp/services/product_service.py` | 240-247 | Sort: active first, then by creation date (list_products) |
| `api/endpoints/products/crud.py` | 90 | Default `include_inactive=True` |

---

## Testing Results

### Test 1: Product Creation
- **Before**: 422 Unprocessable Entity
- **After**: ✅ 200 OK - Product created successfully
- **Verification**: Product ID `25bb2e7e-b983-4f33-83a7-b7045f9d9e48` created in database

### Test 2: Product Retrieval
- **Before**: 500 Internal Server Error (lazy-loading issue)
- **After**: ✅ 200 OK - Product fetched without errors
- **Verification**: No `MissingGreenlet` exception

### Test 3: Products List Display
- **Before**: Inactive products hidden (empty Products page)
- **After**: ✅ All products visible, active products at top
- **Verification**: Database query returns 5 products, all visible in UI

---

## Database State

**Before Fix**:
```sql
SELECT id, name, is_active FROM products ORDER BY created_at DESC LIMIT 5;

25bb2e7e-b983-4f33-83a7-b7045f9d9e48 | silly test         | f  ← Not showing in UI
e2bd194b-3bbd-446a-b082-7f4ffe0a829a | asdf               | f
831660f0-fe41-4dd6-bcff-f5e52bddb0b7 | silly test         | f
ad0550a2-5e0a-40d7-ae34-7f9c1cd0f8f1 | Silly product test | f
06d3d4c0-f864-4bad-afce-a56d07456c76 | fiddli             | f
```

**After Fix**: All 5 products visible in Products page

---

## API Behavior Changes

### Before (broken)
```
GET /api/v1/products/             → Returns ONLY active products
GET /api/v1/products/?include_inactive=true  → Returns all products
```

### After (fixed)
```
GET /api/v1/products/             → Returns ALL products (active first)
GET /api/v1/products/?include_inactive=false → Returns only active products
```

**Rationale**: Default behavior should be inclusive, not restrictive. Users expect to see all their data.

---

## Related Issues (Not Fixed in This Session)

### Vision Document Upload Error
**Status**: Identified but not fixed
**Error**: 500 - Unique constraint violation
**Message**: `duplicate key value violates unique constraint "uq_vision_doc_product_name"`

**Cause**: Attempting to upload vision document with duplicate name for same product

**Decision**: Deferred to separate fix (not part of product creation regression)

---

## Lessons Learned

### 1. API Contract Changes Require Full-Stack Updates
When changing backend request/response formats, **always update the frontend simultaneously**. The refactoring changed backend to expect JSON but forgot to update the frontend.

### 2. Eager Loading for Async SQLAlchemy
When accessing relationships in Pydantic models or property getters, **always eager-load** to avoid lazy-loading in async context:
```python
# Good
stmt = select(Model).options(selectinload(Model.relationship))

# Bad (causes MissingGreenlet errors)
stmt = select(Model)  # relationship lazy-loaded later
```

### 3. Default Behavior Should Be Inclusive
Filtering/hiding data should be **opt-in**, not opt-out. Users expect to see all their data unless they explicitly choose to filter.

### 4. Breaking Changes Need Testing
The refactoring introduced breaking changes but lacked integration tests to catch them. Consider adding:
- Frontend/backend contract tests
- E2E tests for critical workflows (product creation, listing)

---

## Commit Message (Suggested)

```
fix(products): restore product creation and display after refactoring

Three critical regressions from Handover 0126 Products Modularization:

1. 422 Error - Frontend sending FormData instead of JSON
   - Updated api.js to send JSON payloads for create/update
   - Backend expects Pydantic models (JSON), not multipart/form-data

2. 500 Error - SQLAlchemy lazy-loading vision_documents
   - Added selectinload() to eager-load vision_documents relationship
   - Prevents MissingGreenlet error in async context

3. Products not showing - Backend filtered inactive by default
   - Changed include_inactive default from False → True
   - Products sorted: active first, then by creation date DESC
   - Users can delete products if unwanted (vs hiding them)

Files changed:
- frontend/src/services/api.js (JSON payloads)
- src/giljo_mcp/services/product_service.py (eager loading, sorting)
- api/endpoints/products/crud.py (include_inactive default)

Fixes restore pre-refactoring behavior where all products are visible.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## References

- **Refactoring Project**: `handovers/REFACTORING_ROADMAP_0120-0130.md`
- **Backup Branch**: `prior_to_major_refactor_november`
- **Related Handover**: Handover 0126 - Products Modularization
- **SQLAlchemy Async Docs**: https://sqlalche.me/e/20/xd2s

---

**Session Duration**: ~45 minutes
**Status**: ✅ All critical product creation/display issues resolved
**Next Steps**: Commit fixes, test vision document upload separately
