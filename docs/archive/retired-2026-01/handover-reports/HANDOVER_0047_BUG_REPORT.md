# Product Deletion Bug - Diagnostic Report

## Summary
**Issue**: Product deletion returns HTTP 200 OK but fails to actually delete the product from the database.

**Root Cause**: Missing `CASCADE` on foreign key constraints in database schema.

## Evidence

### 1. API Logs Show Misleading Success
```
DELETE /api/v1/products/ce4dd3d7-f477-4794-a67f-fbf4135f897c/ - 307 Temporary Redirect
DELETE /api/v1/products/ce4dd3d7-f477-4794-a67f-fbf4135f897c - 200 OK
GET /api/v1/products/ - 200 OK  (product still appears!)
```

### 2. Code Analysis: Inconsistent CASCADE Configuration

Location: `F:\GiljoAI_MCP\src\giljo_mcp\models.py`

#### Tables WITH Proper CASCADE (working correctly):

**VisionDocument (Line 199)**:
```python
product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
```

**MCPContextIndex.vision_document_id (Line 1803)**:
```python
vision_document_id = Column(String(36), ForeignKey("vision_documents.id", ondelete="CASCADE"), nullable=True)
```

#### Tables WITHOUT CASCADE (causing the bug):

**Project (Line 389)** - MISSING CASCADE:
```python
product_id = Column(String(36), ForeignKey("products.id"), nullable=True)
```
Should be:
```python
product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
```

**Task (Line 524)** - MISSING CASCADE:
```python
product_id = Column(String(36), ForeignKey("products.id"), nullable=True)
```
Should be:
```python
product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
```

**MCPContextIndex.product_id (Line 1800)** - MISSING CASCADE:
```python
product_id = Column(String(36), ForeignKey("products.id"), nullable=True)
```
Should be:
```python
product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
```

### 3. Delete Endpoint Issue

Location: `F:\GiljoAI_MCP\api\endpoints\products.py` (lines 496-534)

```python
@router.delete("/{product_id}")
async def delete_product(product_id: str, tenant_key: str = Depends(get_tenant_key)):
    """Delete a product and all related data"""
    # ... code omitted ...

    try:
        async with state.db_manager.get_session_async() as db:
            # Get product
            stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
            result = await db.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            # Delete product (cascade will handle related records)
            db.delete(product)
            await db.commit()  # <-- This FAILS silently due to FK constraint

            return {"message": "Product deleted successfully"}  # <-- Returns success even though commit failed!

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Problem**: When `db.commit()` fails due to foreign key constraint violations, the exception is NOT being caught properly. The endpoint returns 200 OK even though the deletion didn't happen.

## Why It Happens

1. **Foreign Key Constraint Violation**: When trying to delete a product that has related projects/tasks/chunks:
   - PostgreSQL REJECTS the deletion because child records exist
   - Without CASCADE, PostgreSQL protects data integrity

2. **Silent Rollback**: SQLAlchemy rolls back the transaction but doesn't raise an exception that gets caught

3. **False Success**: The endpoint returns 200 OK because:
   - No HTTPException was raised
   - The generic `except Exception` didn't catch the specific constraint violation
   - The context manager (`async with`) closed cleanly

4. **Frontend Confusion**: Frontend receives 200 OK, refreshes the product list (GET /api/v1/products/), and still sees the product because it was never deleted

## The Fix

### Step 1: Update Database Models (REQUIRED)

File: `F:\GiljoAI_MCP\src\giljo_mcp\models.py`

```python
# Line 389 - Project model
product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=True)

# Line 524 - Task model
product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=True)

# Line 1800 - MCPContextIndex model
product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
```

### Step 2: Update Database Schema

After changing models.py, the database schema must be updated:

**Option A: Drop and recreate tables (DEV ONLY - loses data)**:
```bash
python install.py --recreate-db
```

**Option B: Manual ALTER TABLE (preserves data)**:
```sql
-- Connect to database
psql -U postgres -d giljo_mcp

-- Add CASCADE to existing foreign keys
ALTER TABLE projects
  DROP CONSTRAINT IF EXISTS projects_product_id_fkey,
  ADD CONSTRAINT projects_product_id_fkey
    FOREIGN KEY (product_id)
    REFERENCES products(id)
    ON DELETE CASCADE;

ALTER TABLE tasks
  DROP CONSTRAINT IF EXISTS tasks_product_id_fkey,
  ADD CONSTRAINT tasks_product_id_fkey
    FOREIGN KEY (product_id)
    REFERENCES products(id)
    ON DELETE CASCADE;

ALTER TABLE mcp_context_index
  DROP CONSTRAINT IF EXISTS mcp_context_index_product_id_fkey,
  ADD CONSTRAINT mcp_context_index_product_id_fkey
    FOREIGN KEY (product_id)
    REFERENCES products(id)
    ON DELETE CASCADE;
```

### Step 3: Improve Error Handling (RECOMMENDED)

File: `F:\GiljoAI_MCP\api\endpoints\products.py` (lines 496-534)

```python
@router.delete("/{product_id}")
async def delete_product(product_id: str, tenant_key: str = Depends(get_tenant_key)):
    """Delete a product and all related data"""
    from api.app import state
    from sqlalchemy.exc import IntegrityError

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # Get product
            stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
            result = await db.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            # Delete vision document files if they exist
            if product.vision_path and os.path.exists(product.vision_path):
                try:
                    os.remove(product.vision_path)
                    vision_dir = Path(product.vision_path).parent
                    if vision_dir.exists() and not any(vision_dir.iterdir()):
                        vision_dir.rmdir()
                except Exception:
                    pass  # Don't fail deletion if file cleanup fails

            # Delete product (cascade will handle related records)
            db.delete(product)

            try:
                await db.commit()
            except IntegrityError as e:
                await db.rollback()
                # This should NOT happen after adding CASCADE, but keep as safety net
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot delete product due to database constraints: {str(e)}"
                )

            return {"message": "Product deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Testing

### Integration Test

A comprehensive integration test has been created:
- File: `F:\GiljoAI_MCP\tests\integration\test_product_deletion_cascade.py`
- Tests deletion with related projects, tasks, vision documents, and context chunks
- Verifies CASCADE behavior works correctly

Run with:
```bash
pytest tests/integration/test_product_deletion_cascade.py -v
```

### Manual API Test

After applying the fix:

```bash
# 1. Get list of products
curl -X GET http://10.1.0.164:7272/api/v1/products/ \
  -H "Cookie: <auth-cookie>"

# 2. Delete a product (copy ID from step 1)
curl -X DELETE http://10.1.0.164:7272/api/v1/products/<product-id> \
  -H "Cookie: <auth-cookie>" \
  -v

# 3. Verify deletion
curl -X GET http://10.1.0.164:7272/api/v1/products/ \
  -H "Cookie: <auth-cookie>"
# Product should NOT appear in list

# 4. Verify 404 on deleted product
curl -X GET http://10.1.0.164:7272/api/v1/products/<product-id> \
  -H "Cookie: <auth-cookie>"
# Should return 404 Not Found
```

### Database Verification

```sql
-- Check CASCADE constraints are in place
SELECT
    tc.table_name,
    kcu.column_name,
    rc.delete_rule
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
JOIN information_schema.referential_constraints AS rc
  ON rc.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND ccu.table_name = 'products'
ORDER BY tc.table_name;

-- Expected output:
-- table_name           | column_name | delete_rule
-- --------------------|-------------|-------------
-- projects            | product_id  | CASCADE
-- tasks               | product_id  | CASCADE
-- vision_documents    | product_id  | CASCADE
-- mcp_context_index   | product_id  | CASCADE
```

## Impact Analysis

### What Gets Deleted (CASCADE chain):

When a product is deleted:
1. **Product** record (primary deletion)
2. **Projects** → triggers CASCADE deletion of:
   - Project's **Agents**
   - Project's **Messages**
   - Project's **Tasks** (via project_id FK)
   - Project's **Sessions**
   - Project's **Visions**
   - Project's **ContextIndex**
3. **Tasks** (via product_id FK - direct deletion)
4. **VisionDocuments** → triggers CASCADE deletion of:
   - VisionDocument's **MCPContextIndex chunks** (via vision_document_id FK)
5. **MCPContextIndex** (via product_id FK - direct deletion)

### Data Safety

- **Multi-tenant isolation preserved**: CASCADE only affects records with matching `tenant_key`
- **No cross-tenant data deletion**: Foreign keys combined with WHERE clauses ensure safety
- **Intentional cascades only**: Only relationships that SHOULD be deleted are configured with CASCADE

## Rollout Plan

1. **Commit model changes** to models.py
2. **Update database schema** using ALTER TABLE commands (preserves data)
3. **Deploy API error handling improvements**
4. **Run integration tests** to verify behavior
5. **Test manually** in dashboard UI
6. **Monitor logs** for any constraint violation errors (should be zero after fix)

## Priority: HIGH

**Severity**: User-facing bug causing data inconsistency and confusion

**User Impact**: Users cannot delete products from dashboard, leading to cluttered product lists

**Effort**: Low (3 model changes + 3 ALTER TABLE commands + error handling improvement)

**Risk**: Low (CASCADE is the correct behavior; extensively tested in SQLAlchemy applications)
