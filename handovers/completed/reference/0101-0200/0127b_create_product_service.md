# Handover 0127b: Create ProductService

**Status:** Ready to Execute
**Priority:** P1 - HIGH
**Estimated Duration:** 1-2 days
**Agent Budget:** 100K tokens
**Depends On:** 0127a (Fix Test Suite) should be complete

---

## Executive Summary

### The Problem

During the modularization effort (Handover 0126), the products endpoints were split into focused modules, but unlike other endpoints (projects, templates), no ProductService was created. This violates the established service layer pattern and means product endpoints have direct database access.

### Current State

```
api/endpoints/products/
├── crud.py          # Direct database access ❌
├── lifecycle.py     # Direct database access ❌
├── vision.py        # Direct database access ❌
├── status.py        # Direct database access ❌
├── dependencies.py  # No service to inject ❌
└── models.py        # Pydantic models ✅
```

### Target State

```
src/giljo_mcp/services/
├── product_service.py  # NEW - Centralized business logic ✅

api/endpoints/products/
├── crud.py          # Delegates to ProductService ✅
├── lifecycle.py     # Delegates to ProductService ✅
├── vision.py        # Delegates to ProductService ✅
├── status.py        # Delegates to ProductService ✅
├── dependencies.py  # Injects ProductService ✅
└── models.py        # Pydantic models (unchanged) ✅
```

---

## Objectives

### Primary Objectives

✅ **Create ProductService** - Following established patterns
✅ **Update All Product Endpoints** - Use service layer
✅ **Maintain API Compatibility** - Zero breaking changes
✅ **Add Comprehensive Tests** - >80% coverage
✅ **Preserve Functionality** - Everything still works

### Success Criteria

- ProductService created with all necessary methods
- All product endpoints delegate to service
- No direct database access in endpoints
- All existing API routes work identically
- Test coverage >80% for ProductService
- Application runs without issues

---

## Implementation Plan

### Phase 1: Analyze Current Implementation (1-2 hours)

**Step 1.1: Study ProjectService Pattern**

Read `src/giljo_mcp/services/project_service.py` to understand:
- Class structure
- Method signatures
- Database session handling
- Error handling patterns
- Tenant isolation approach

**Step 1.2: Inventory Product Endpoints**

List all methods in product endpoints that need service methods:

```python
# From crud.py:
- create_product()
- get_products()
- get_product()
- update_product()
- delete_product()

# From lifecycle.py:
- activate_product()
- deactivate_product()
- archive_product()

# From vision.py:
- update_product_vision()
- get_product_vision()
- validate_vision_format()

# From status.py:
- get_product_status()
- get_product_statistics()
```

**Step 1.3: Identify Database Operations**

Document all database queries currently in endpoints to migrate to service.

### Phase 2: Create ProductService (3-4 hours)

**Step 2.1: Create Service File**

Create `src/giljo_mcp/services/product_service.py`:

```python
"""
Product service for managing products with business logic.
Follows the same pattern as ProjectService and TemplateService.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload

from ..models import Product, Project
from ..database import DatabaseManager

logger = logging.getLogger(__name__)


class ProductService:
    """Service class for product-related operations."""

    def __init__(self, db_manager: DatabaseManager, tenant_key: str):
        """
        Initialize ProductService.

        Args:
            db_manager: Database manager instance
            tenant_key: Tenant key for multi-tenant isolation
        """
        self.db_manager = db_manager
        self.tenant_key = tenant_key

    async def create_product(
        self,
        name: str,
        description: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Product:
        """
        Create a new product.

        Args:
            name: Product name
            description: Product description
            settings: Product settings
            **kwargs: Additional product fields

        Returns:
            Created Product instance

        Raises:
            ValueError: If product with name already exists
        """
        async with self.db_manager.get_session() as session:
            # Check for duplicate name
            existing = await session.execute(
                select(Product).where(
                    and_(
                        Product.name == name,
                        Product.tenant_key == self.tenant_key
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Product with name '{name}' already exists")

            # Create product
            product = Product(
                name=name,
                description=description,
                settings=settings or {},
                tenant_key=self.tenant_key,
                **kwargs
            )

            session.add(product)
            await session.commit()
            await session.refresh(product)

            logger.info(f"Created product: {product.id}")
            return product

    async def get_products(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Product]:
        """
        Get all products for tenant with optional filtering.

        Args:
            status: Filter by status (active, inactive, archived)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Product instances
        """
        async with self.db_manager.get_session() as session:
            query = select(Product).where(
                Product.tenant_key == self.tenant_key
            )

            if status:
                query = query.where(Product.status == status)

            query = query.order_by(Product.created_at.desc())

            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_product(self, product_id: str) -> Optional[Product]:
        """
        Get a specific product by ID.

        Args:
            product_id: Product ID

        Returns:
            Product instance or None if not found
        """
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(Product).where(
                    and_(
                        Product.id == product_id,
                        Product.tenant_key == self.tenant_key
                    )
                )
            )
            return result.scalar_one_or_none()

    async def update_product(
        self,
        product_id: str,
        **updates
    ) -> Optional[Product]:
        """
        Update a product.

        Args:
            product_id: Product ID
            **updates: Fields to update

        Returns:
            Updated Product instance or None if not found
        """
        async with self.db_manager.get_session() as session:
            product = await self.get_product(product_id)
            if not product:
                return None

            # Update fields
            for key, value in updates.items():
                if hasattr(product, key):
                    setattr(product, key, value)

            product.updated_at = datetime.utcnow()

            session.add(product)
            await session.commit()
            await session.refresh(product)

            logger.info(f"Updated product: {product.id}")
            return product

    async def delete_product(self, product_id: str) -> bool:
        """
        Delete a product (soft delete by default).

        Args:
            product_id: Product ID

        Returns:
            True if deleted, False if not found
        """
        async with self.db_manager.get_session() as session:
            product = await self.get_product(product_id)
            if not product:
                return False

            # Soft delete - mark as deleted
            product.status = 'deleted'
            product.deleted_at = datetime.utcnow()

            session.add(product)
            await session.commit()

            logger.info(f"Soft deleted product: {product.id}")
            return True

    async def activate_product(self, product_id: str) -> Optional[Product]:
        """
        Activate a product (make it the single active product).

        Args:
            product_id: Product ID to activate

        Returns:
            Activated Product or None if not found

        Note:
            Only one product can be active at a time per tenant.
            This will deactivate any currently active product.
        """
        async with self.db_manager.get_session() as session:
            # Deactivate current active product
            await session.execute(
                update(Product).where(
                    and_(
                        Product.tenant_key == self.tenant_key,
                        Product.status == 'active'
                    )
                ).values(status='inactive')
            )

            # Activate specified product
            result = await session.execute(
                update(Product).where(
                    and_(
                        Product.id == product_id,
                        Product.tenant_key == self.tenant_key
                    )
                ).values(
                    status='active',
                    activated_at=datetime.utcnow()
                ).returning(Product)
            )

            await session.commit()

            product = result.scalar_one_or_none()
            if product:
                logger.info(f"Activated product: {product.id}")

            return product

    async def get_active_product(self) -> Optional[Product]:
        """
        Get the currently active product for the tenant.

        Returns:
            Active Product or None if no active product
        """
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(Product).where(
                    and_(
                        Product.tenant_key == self.tenant_key,
                        Product.status == 'active'
                    )
                )
            )
            return result.scalar_one_or_none()

    async def get_product_statistics(self, product_id: str) -> Dict[str, Any]:
        """
        Get statistics for a product.

        Args:
            product_id: Product ID

        Returns:
            Dictionary with statistics
        """
        async with self.db_manager.get_session() as session:
            product = await self.get_product(product_id)
            if not product:
                return {}

            # Count projects
            project_count = await session.execute(
                select(func.count(Project.id)).where(
                    and_(
                        Project.product_id == product_id,
                        Project.tenant_key == self.tenant_key
                    )
                )
            )

            # Get active project count
            active_projects = await session.execute(
                select(func.count(Project.id)).where(
                    and_(
                        Project.product_id == product_id,
                        Project.status == 'active',
                        Project.tenant_key == self.tenant_key
                    )
                )
            )

            return {
                'product_id': product_id,
                'total_projects': project_count.scalar() or 0,
                'active_projects': active_projects.scalar() or 0,
                'status': product.status,
                'created_at': product.created_at.isoformat() if product.created_at else None,
                'last_updated': product.updated_at.isoformat() if product.updated_at else None
            }
```

**Step 2.2: Add to Services __init__.py**

Update `src/giljo_mcp/services/__init__.py`:

```python
from .product_service import ProductService

__all__ = [
    # ... existing exports ...
    'ProductService',
]
```

### Phase 3: Update Product Endpoints (3-4 hours)

**Step 3.1: Update dependencies.py**

```python
# api/endpoints/products/dependencies.py

from src.giljo_mcp.services import ProductService
from src.giljo_mcp.database import DatabaseManager


async def get_product_service(
    db_manager: DatabaseManager = Depends(get_db_manager),
    tenant_key: str = Depends(get_tenant_key)
) -> ProductService:
    """Get ProductService instance with tenant isolation."""
    return ProductService(db_manager=db_manager, tenant_key=tenant_key)
```

**Step 3.2: Update crud.py**

```python
# api/endpoints/products/crud.py

from .dependencies import get_product_service

@router.post("/products")
async def create_product(
    product_data: ProductCreate,
    service: ProductService = Depends(get_product_service)
):
    """Create a new product."""
    try:
        product = await service.create_product(
            name=product_data.name,
            description=product_data.description,
            settings=product_data.settings
        )
        return product
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/products")
async def get_products(
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    service: ProductService = Depends(get_product_service)
):
    """Get all products."""
    products = await service.get_products(
        status=status,
        limit=limit,
        offset=offset
    )
    return products

# Continue updating all endpoints to use service...
```

**Step 3.3: Update lifecycle.py**

```python
# api/endpoints/products/lifecycle.py

@router.post("/products/{product_id}/activate")
async def activate_product(
    product_id: str,
    service: ProductService = Depends(get_product_service)
):
    """Activate a product."""
    product = await service.activate_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
```

**Step 3.4: Update Other Endpoints**

Continue pattern for vision.py, status.py, etc.

### Phase 4: Create Tests (2-3 hours)

**Step 4.1: Create Service Tests**

Create `tests/unit/test_product_service.py`:

```python
import pytest
from unittest.mock import Mock, AsyncMock
from src.giljo_mcp.services import ProductService


@pytest.mark.asyncio
async def test_create_product():
    """Test product creation."""
    # Setup
    db_manager = Mock()
    service = ProductService(db_manager, "test_tenant")

    # Test
    product = await service.create_product(
        name="Test Product",
        description="Test Description"
    )

    # Assertions
    assert product.name == "Test Product"
    assert product.tenant_key == "test_tenant"


@pytest.mark.asyncio
async def test_activate_product_single_active():
    """Test that only one product can be active."""
    # Test single active product constraint
    pass

# Add more comprehensive tests...
```

**Step 4.2: Create Integration Tests**

```python
# tests/integration/test_product_endpoints.py

@pytest.mark.asyncio
async def test_product_crud_flow(client, auth_headers):
    """Test complete CRUD flow through endpoints."""
    # Create
    response = await client.post(
        "/api/v1/products",
        json={"name": "Test Product"},
        headers=auth_headers
    )
    assert response.status_code == 200
    product_id = response.json()["id"]

    # Read
    response = await client.get(
        f"/api/v1/products/{product_id}",
        headers=auth_headers
    )
    assert response.status_code == 200

    # Update
    response = await client.put(
        f"/api/v1/products/{product_id}",
        json={"description": "Updated"},
        headers=auth_headers
    )
    assert response.status_code == 200

    # Delete
    response = await client.delete(
        f"/api/v1/products/{product_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
```

### Phase 5: Validation (1-2 hours)

**Step 5.1: Run Tests**

```bash
# Run new service tests
pytest tests/unit/test_product_service.py -v

# Run integration tests
pytest tests/integration/test_product_endpoints.py -v

# Run full test suite
pytest tests/ -v
```

**Step 5.2: Test Application**

```bash
# Start application
python startup.py --dev

# Test product endpoints manually
curl -X GET http://localhost:7272/api/v1/products
curl -X POST http://localhost:7272/api/v1/products -d '{"name": "Test"}'
```

**Step 5.3: Verify Service Pattern**

Ensure ProductService follows same patterns as:
- ProjectService
- TemplateService
- TaskService

---

## Validation Checklist

- [ ] ProductService created with all methods
- [ ] All product endpoints updated
- [ ] No direct database access in endpoints
- [ ] Dependencies.py updated with get_product_service
- [ ] All existing API routes work
- [ ] Tests created with >80% coverage
- [ ] Application starts successfully
- [ ] Manual testing completed

---

## Risk Assessment

**Risk 1: Breaking Working Endpoints**
- **Impact:** HIGH
- **Mitigation:** Test each endpoint after modification

**Risk 2: Missing Functionality**
- **Impact:** MEDIUM
- **Mitigation:** Inventory all methods before starting

**Risk 3: Inconsistent Pattern**
- **Impact:** LOW
- **Mitigation:** Follow ProjectService exactly

---

## Tips for Success

### Do's
✅ Follow ProjectService pattern exactly
✅ Test incrementally after each endpoint
✅ Maintain tenant isolation
✅ Keep API routes unchanged
✅ Add comprehensive logging

### Don'ts
❌ Don't change API contracts
❌ Don't skip testing
❌ Don't modify database schema
❌ Don't remove functionality

---

**Created:** 2025-11-10
**Priority:** P1 - HIGH
**Complete After:** 0127a (Test Suite Fix)