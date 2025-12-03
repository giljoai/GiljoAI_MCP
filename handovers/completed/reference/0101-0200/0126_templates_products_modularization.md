# Handover 0126: Templates & Products Modularization

**Status:** Ready
**Priority:** High
**Estimated Duration:** 1-2 weeks
**Depends On:** ✅ Handover 0123 (TemplateService extracted)
**Blocks:** Handover 0127 (Deprecated Code Removal)

---

## Executive Summary

Modularize template and product endpoints into focused modules that use TemplateService and ProductService for all operations. **API routes remain IDENTICAL - no breaking changes to frontend.**

### 🚨 CRITICAL REQUIREMENTS

**1. ZERO API Breaking Changes**
- ALL routes stay at `/api/v1/templates/*` and `/api/v1/products/*`
- Same HTTP methods, same request/response formats
- Frontend sees ZERO difference

**2. Aggressive Code Cleanup**
- DELETE `templates.py` after migration (replace with templates/ module)
- DELETE `products.py` after migration (replace with products/ module)
- DELETE all old template/product code and tests
- NO facades, NO "backward compatibility wrappers"

**3. Backend Reorganization Only**
- Split large files into focused modules
- All code uses TemplateService and ProductService
- Clean module structure for maintainability

### Problem Statement

**Current State:**
- Templates in single 700-line file
- Products in single 400-line file
- Mixed concerns in both files
- Some direct database access

**Example of Current Structure:**
```
api/endpoints/
├── templates.py              (~700 lines) - DELETE after migration
├── products.py               (~400 lines) - DELETE after migration
```

### Desired State

**Reorganized Backend (SAME API routes!):**
```
api/endpoints/templates/
├── __init__.py               # Export all routers
├── crud.py                   (~200 lines) - Template CRUD
├── management.py             (~150 lines) - Lifecycle
├── validation.py             (~150 lines) - Validation
└── versions.py               (~200 lines) - Version management

api/endpoints/products/
├── __init__.py               # Export all routers
├── crud.py                   (~200 lines) - Product CRUD
├── settings.py               (~150 lines) - Settings/config
└── integration.py            (~150 lines) - Integrations
```

**API Routes (UNCHANGED!):**
```
# Templates
POST   /api/v1/templates
GET    /api/v1/templates
GET    /api/v1/templates/{template_id}
PUT    /api/v1/templates/{template_id}
DELETE /api/v1/templates/{template_id}
POST   /api/v1/templates/{template_id}/clone
POST   /api/v1/templates/{template_id}/validate
PUT    /api/v1/templates/{template_id}/publish
PUT    /api/v1/templates/{template_id}/archive
GET    /api/v1/templates/{template_id}/versions
POST   /api/v1/templates/{template_id}/versions
GET    /api/v1/templates/{template_id}/versions/{version}

# Products
POST   /api/v1/products
GET    /api/v1/products
GET    /api/v1/products/{product_id}
PUT    /api/v1/products/{product_id}
DELETE /api/v1/products/{product_id}
GET    /api/v1/products/{product_id}/settings
PUT    /api/v1/products/{product_id}/settings
GET    /api/v1/products/{product_id}/context-budget
POST   /api/v1/products/{product_id}/github
POST   /api/v1/products/{product_id}/jira
GET    /api/v1/products/{product_id}/integrations
```

**All endpoints use TemplateService and ProductService** (no direct DB access)

---

## Objectives

### Primary Objectives

✅ **Modularize Template Endpoints** - Split into focused modules by concern
✅ **Modularize Product Endpoints** - Separate product management logic
✅ **Extract ProductService** - Create dedicated service for product operations
✅ **Use TemplateService** - All template endpoints delegate to service layer
✅ **Remove Direct DB Access** - No database operations in endpoint code
✅ **Consistent Patterns** - Same structure as agent_jobs (0124) and projects (0125)
✅ **Reduce File Sizes** - From 400-700 lines to 150-200 lines per file
✅ **Comprehensive Tests** - >80% coverage on all modularized endpoints

### Secondary Objectives

✅ **API Documentation** - Complete OpenAPI/Swagger docs
✅ **Error Handling** - Consistent error responses
✅ **Validation** - Pydantic models for all requests/responses
✅ **Template Versioning** - Support for template version management
✅ **Product Configuration** - Structured product settings management

---

## Current State Analysis

### Existing Template Endpoints

**File:** `api/endpoints/templates.py` (~700 lines)
```python
# Template CRUD operations
POST   /api/v1/templates                      # create_template
GET    /api/v1/templates                      # list_templates
GET    /api/v1/templates/{template_id}        # get_template
PUT    /api/v1/templates/{template_id}        # update_template
DELETE /api/v1/templates/{template_id}        # delete_template (soft delete)

# Template management
POST   /api/v1/templates/{template_id}/clone
POST   /api/v1/templates/{template_id}/validate
PUT    /api/v1/templates/{template_id}/publish
PUT    /api/v1/templates/{template_id}/archive

# Version management
GET    /api/v1/templates/{template_id}/versions
POST   /api/v1/templates/{template_id}/versions
GET    /api/v1/templates/{template_id}/versions/{version}
```

### Existing Product Endpoints

**File:** `api/endpoints/products.py` (~400 lines)
```python
# Product CRUD operations
POST   /api/v1/products                       # create_product
GET    /api/v1/products                       # list_products
GET    /api/v1/products/{product_id}          # get_product
PUT    /api/v1/products/{product_id}          # update_product
DELETE /api/v1/products/{product_id}          # delete_product

# Product settings
GET    /api/v1/products/{product_id}/settings
PUT    /api/v1/products/{product_id}/settings
GET    /api/v1/products/{product_id}/context-budget

# Product integrations
POST   /api/v1/products/{product_id}/github
POST   /api/v1/products/{product_id}/jira
GET    /api/v1/products/{product_id}/integrations
```

### Issues with Current Structure

1. **Large Files** - 400-700 lines makes navigation difficult
2. **Mixed Concerns** - CRUD + validation + versioning in same file
3. **Direct DB Access** - Some endpoints bypass TemplateService
4. **No ProductService** - Product logic scattered in endpoints and ToolAccessor
5. **Inconsistent Patterns** - Different error handling across files
6. **Poor Modularity** - Hard to test and maintain

---

## Proposed Architecture

### New Template Endpoint Structure

```
api/endpoints/templates/
├── __init__.py                    # Module exports and router setup
│
├── crud.py                        # Template CRUD operations (~200 lines)
│   ├── POST   /api/v1/templates
│   ├── GET    /api/v1/templates
│   ├── GET    /api/v1/templates/{template_id}
│   ├── PUT    /api/v1/templates/{template_id}
│   └── DELETE /api/v1/templates/{template_id}
│
├── management.py                  # Template lifecycle (~150 lines)
│   ├── POST   /api/v1/templates/{template_id}/clone
│   ├── PUT    /api/v1/templates/{template_id}/publish
│   └── PUT    /api/v1/templates/{template_id}/archive
│
├── validation.py                  # Template validation (~150 lines)
│   ├── POST   /api/v1/templates/{template_id}/validate
│   └── POST   /api/v1/templates/validate-schema
│
└── versions.py                    # Version management (~200 lines)
    ├── GET    /api/v1/templates/{template_id}/versions
    ├── POST   /api/v1/templates/{template_id}/versions
    └── GET    /api/v1/templates/{template_id}/versions/{version}
```

### New Product Endpoint Structure

```
api/endpoints/products/
├── __init__.py                    # Module exports and router setup
│
├── crud.py                        # Product CRUD operations (~200 lines)
│   ├── POST   /api/v1/products
│   ├── GET    /api/v1/products
│   ├── GET    /api/v1/products/{product_id}
│   ├── PUT    /api/v1/products/{product_id}
│   └── DELETE /api/v1/products/{product_id}
│
├── settings.py                    # Product settings (~150 lines)
│   ├── GET    /api/v1/products/{product_id}/settings
│   ├── PUT    /api/v1/products/{product_id}/settings
│   └── GET    /api/v1/products/{product_id}/context-budget
│
└── integration.py                 # Product integrations (~150 lines)
    ├── POST   /api/v1/products/{product_id}/github
    ├── POST   /api/v1/products/{product_id}/jira
    └── GET    /api/v1/products/{product_id}/integrations
```

### New Service Layer

**ProductService** (to be created, ~350 lines)
```python
# src/giljo_mcp/services/product_service.py

class ProductService:
    """
    Service for product management operations.

    Handles:
    - Product CRUD operations
    - Product settings and configuration
    - Context budget management
    - Product-tenant isolation
    - Integration management
    """

    async def create_product(self, name: str, description: str, ...) -> dict[str, Any]
    async def get_product(self, product_id: str, tenant_key: str) -> dict[str, Any]
    async def list_products(self, tenant_key: str, ...) -> dict[str, Any]
    async def update_product(self, product_id: str, updates: dict, ...) -> dict[str, Any]
    async def delete_product(self, product_id: str, tenant_key: str) -> dict[str, Any]
    async def get_product_settings(self, product_id: str, ...) -> dict[str, Any]
    async def update_product_settings(self, product_id: str, settings: dict, ...) -> dict[str, Any]
    async def get_context_budget(self, product_id: str, ...) -> dict[str, Any]
```

### Design Principles

1. **Service Layer Only** - All endpoints use TemplateService and ProductService
2. **Single Responsibility** - Each module handles one concern
3. **Thin Endpoints** - Minimal logic, delegate to service
4. **Consistent Patterns** - Same structure as agent_jobs (0124) and projects (0125)
5. **Proper Validation** - Pydantic models throughout
6. **Tenant Isolation** - All operations respect tenant boundaries

---

## Implementation Plan

### Phase 1: Extract ProductService (2-3 days)

**Step 1.1: Create ProductService**
```python
# src/giljo_mcp/services/product_service.py
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database.manager import DatabaseManager
from giljo_mcp.core.tenant_manager import TenantManager
from giljo_mcp.models import Product

class ProductService:
    """Product management service (extracted from ToolAccessor)"""

    def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def create_product(
        self,
        name: str,
        description: str,
        tenant_key: str,
        context_budget: int = 150000,
        settings: Optional[dict] = None
    ) -> dict[str, Any]:
        """Create a new product with tenant isolation"""
        try:
            async with self.db_manager.get_session_async() as session:
                product = Product(
                    name=name,
                    description=description,
                    tenant_key=tenant_key,
                    context_budget=context_budget,
                    settings=settings or {}
                )
                session.add(product)
                await session.commit()
                await session.refresh(product)

                return {
                    "success": True,
                    "product_id": product.id,
                    "name": product.name,
                    "tenant_key": product.tenant_key
                }
        except Exception as e:
            self._logger.error(f"Failed to create product: {e}")
            return {"error": f"INTERNAL_ERROR: {str(e)}"}

    # ... other methods
```

**Step 1.2: Write ProductService Tests**
```python
# tests/unit/test_product_service.py
import pytest
from unittest.mock import AsyncMock, Mock

from giljo_mcp.services.product_service import ProductService

class TestProductServiceCRUD:
    """Test product CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_product_success(self):
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        service = ProductService(db_manager, tenant_manager)

        # Act
        result = await service.create_product(
            name="Test Product",
            description="Test Description",
            tenant_key="test-tenant"
        )

        # Assert
        assert result["success"] is True
        assert "product_id" in result
        session.commit.assert_awaited_once()
```

**Step 1.3: Update ToolAccessor**
```python
# src/giljo_mcp/tools/tool_accessor.py

def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
    # ... existing services
    self._product_service = ProductService(db_manager, tenant_manager)

async def create_product(self, name: str, description: str, ...) -> dict[str, Any]:
    """Create a new product (delegates to ProductService)"""
    return await self._product_service.create_product(...)
```

### Phase 2: Modularize Template Endpoints (2-3 days)

**Step 2.1: Create Template Module Structure**
```bash
mkdir -p api/endpoints/templates
touch api/endpoints/templates/__init__.py
touch api/endpoints/templates/crud.py
touch api/endpoints/templates/management.py
touch api/endpoints/templates/validation.py
touch api/endpoints/templates/versions.py
touch api/endpoints/templates/models.py
```

**Step 2.2: Create Template Pydantic Models**
```python
# api/endpoints/templates/models.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class CreateTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("", max_length=1000)
    template_type: str = Field(..., pattern="^(agent|project|workflow)$")
    content: Dict[str, Any] = Field(...)
    version: str = Field("1.0.0")

class CreateTemplateResponse(BaseModel):
    success: bool
    template_id: str
    name: str
    version: str
    tenant_key: str

class ListTemplatesResponse(BaseModel):
    success: bool
    templates: list[dict]
    count: int

class ValidateTemplateRequest(BaseModel):
    content: Dict[str, Any] = Field(...)
    template_type: str = Field(..., pattern="^(agent|project|workflow)$")

class ValidateTemplateResponse(BaseModel):
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []
```

**Step 2.3: Implement templates/crud.py**
```python
# api/endpoints/templates/crud.py
from fastapi import APIRouter, Depends, HTTPException
from giljo_mcp.services.template_service import TemplateService
from .models import CreateTemplateRequest, CreateTemplateResponse

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])

@router.post("", response_model=CreateTemplateResponse)
async def create_template(
    request: CreateTemplateRequest,
    template_service: TemplateService = Depends(get_template_service),
    tenant_key: str = Depends(get_tenant_key)
):
    """Create a new template."""
    result = await template_service.create_template(
        name=request.name,
        description=request.description,
        template_type=request.template_type,
        content=request.content,
        version=request.version,
        tenant_key=tenant_key
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result

@router.get("", response_model=ListTemplatesResponse)
async def list_templates(
    template_type: Optional[str] = None,
    template_service: TemplateService = Depends(get_template_service),
    tenant_key: str = Depends(get_tenant_key)
):
    """List all templates with optional type filter."""
    result = await template_service.list_templates(
        tenant_key=tenant_key,
        template_type=template_type
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result

# ... get_template, update_template, delete_template
```

**Step 2.4: Implement templates/management.py**
```python
# api/endpoints/templates/management.py
from fastapi import APIRouter, Depends, HTTPException
from giljo_mcp.services.template_service import TemplateService

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])

@router.post("/{template_id}/clone")
async def clone_template(
    template_id: str,
    new_name: str,
    template_service: TemplateService = Depends(get_template_service),
    tenant_key: str = Depends(get_tenant_key)
):
    """Clone an existing template."""
    result = await template_service.clone_template(
        template_id=template_id,
        new_name=new_name,
        tenant_key=tenant_key
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result

@router.put("/{template_id}/publish")
async def publish_template(
    template_id: str,
    template_service: TemplateService = Depends(get_template_service),
    tenant_key: str = Depends(get_tenant_key)
):
    """Publish a template (make it available)."""
    result = await template_service.publish_template(
        template_id=template_id,
        tenant_key=tenant_key
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result

# ... archive_template
```

**Step 2.5: Implement templates/validation.py and templates/versions.py**
- Follow same pattern as above
- All delegate to TemplateService
- Consistent error handling

### Phase 3: Modularize Product Endpoints (2-3 days)

**Step 3.1: Create Product Module Structure**
```bash
mkdir -p api/endpoints/products
touch api/endpoints/products/__init__.py
touch api/endpoints/products/crud.py
touch api/endpoints/products/settings.py
touch api/endpoints/products/integration.py
touch api/endpoints/products/models.py
```

**Step 3.2: Create Product Pydantic Models**
```python
# api/endpoints/products/models.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class CreateProductRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("", max_length=1000)
    context_budget: int = Field(150000, ge=1000, le=1000000)
    settings: Optional[Dict[str, Any]] = None

class CreateProductResponse(BaseModel):
    success: bool
    product_id: str
    name: str
    tenant_key: str

class ProductSettingsRequest(BaseModel):
    settings: Dict[str, Any] = Field(...)

class ProductSettingsResponse(BaseModel):
    success: bool
    product_id: str
    settings: Dict[str, Any]
```

**Step 3.3: Implement products/crud.py**
```python
# api/endpoints/products/crud.py
from fastapi import APIRouter, Depends, HTTPException
from giljo_mcp.services.product_service import ProductService
from .models import CreateProductRequest, CreateProductResponse

router = APIRouter(prefix="/api/v1/products", tags=["products"])

@router.post("", response_model=CreateProductResponse)
async def create_product(
    request: CreateProductRequest,
    product_service: ProductService = Depends(get_product_service),
    tenant_key: str = Depends(get_tenant_key)
):
    """Create a new product."""
    result = await product_service.create_product(
        name=request.name,
        description=request.description,
        context_budget=request.context_budget,
        settings=request.settings,
        tenant_key=tenant_key
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result

# ... list_products, get_product, update_product, delete_product
```

**Step 3.4: Implement products/settings.py and products/integration.py**
- Follow same pattern as templates
- All delegate to ProductService
- Consistent error handling

### Phase 4: Enhance TemplateService (1-2 days)

**Step 4.1: Add Missing Template Methods**
```python
# src/giljo_mcp/services/template_service.py

async def clone_template(
    self,
    template_id: str,
    new_name: str,
    tenant_key: str
) -> dict[str, Any]:
    """Clone an existing template"""
    try:
        async with self.db_manager.get_session_async() as session:
            # Get original template
            stmt = select(Template).where(
                Template.id == template_id,
                Template.tenant_key == tenant_key
            )
            result = await session.execute(stmt)
            original = result.scalar_one_or_none()

            if not original:
                return {"error": "TEMPLATE_NOT_FOUND"}

            # Create clone
            clone = Template(
                name=new_name,
                description=f"Clone of {original.name}",
                template_type=original.template_type,
                content=original.content.copy(),
                version="1.0.0",
                tenant_key=tenant_key
            )
            session.add(clone)
            await session.commit()
            await session.refresh(clone)

            return {
                "success": True,
                "template_id": clone.id,
                "name": clone.name
            }
    except Exception as e:
        self._logger.error(f"Failed to clone template: {e}")
        return {"error": f"INTERNAL_ERROR: {str(e)}"}

async def publish_template(self, template_id: str, tenant_key: str) -> dict[str, Any]:
    """Publish a template (make it available)"""
    # Implementation...

async def archive_template(self, template_id: str, tenant_key: str) -> dict[str, Any]:
    """Archive a template (soft delete)"""
    # Implementation...

async def validate_template(
    self,
    content: dict,
    template_type: str
) -> dict[str, Any]:
    """Validate template content against schema"""
    # Implementation...
```

**Step 4.2: Add Template Versioning Support**
```python
async def create_template_version(
    self,
    template_id: str,
    version: str,
    content: dict,
    tenant_key: str
) -> dict[str, Any]:
    """Create a new version of an existing template"""
    # Implementation...

async def list_template_versions(
    self,
    template_id: str,
    tenant_key: str
) -> dict[str, Any]:
    """List all versions of a template"""
    # Implementation...

async def get_template_version(
    self,
    template_id: str,
    version: str,
    tenant_key: str
) -> dict[str, Any]:
    """Get a specific version of a template"""
    # Implementation...
```

### Phase 5: Testing & Validation (2-3 days)

**Step 5.1: Unit Tests for ProductService**
```python
# tests/unit/test_product_service.py
@pytest.mark.asyncio
async def test_create_product_success():
    # Test product creation
    ...

@pytest.mark.asyncio
async def test_get_product_settings_success():
    # Test settings retrieval
    ...

@pytest.mark.asyncio
async def test_update_product_settings_success():
    # Test settings update
    ...

# Target: >80% coverage
```

**Step 5.2: Unit Tests for Enhanced TemplateService**
```python
# tests/unit/test_template_service.py (enhance existing)
@pytest.mark.asyncio
async def test_clone_template_success():
    # Test template cloning
    ...

@pytest.mark.asyncio
async def test_validate_template_success():
    # Test template validation
    ...

# Target: >80% coverage on new methods
```

**Step 5.3: Endpoint Integration Tests**
```python
# tests/integration/test_template_endpoints.py
@pytest.mark.asyncio
async def test_template_lifecycle():
    # Create -> Validate -> Publish -> Clone -> Archive
    ...

# tests/integration/test_product_endpoints.py
@pytest.mark.asyncio
async def test_product_lifecycle():
    # Create -> Update Settings -> Add Integration -> Delete
    ...
```

**Step 5.4: Performance Testing**
- Validate response times
- Check database query counts
- Monitor memory usage

### Phase 6: Migrate and DELETE Old Files (1 day)

**Step 6.1: Update Main Router**
```python
# api/main.py or api/router.py
# BEFORE:
from api.endpoints import templates, products

# AFTER (only modules):
from api.endpoints.templates import crud as template_crud, management as template_mgmt
from api.endpoints.templates import validation as template_valid, versions as template_vers
from api.endpoints.products import crud as product_crud, settings as product_settings
from api.endpoints.products import integration as product_integ

app.include_router(template_crud.router)
app.include_router(template_mgmt.router)
app.include_router(template_valid.router)
app.include_router(template_vers.router)
app.include_router(product_crud.router)
app.include_router(product_settings.router)
app.include_router(product_integ.router)
```

**Step 6.2: DELETE templates.py**
```bash
rm api/endpoints/templates.py
rm tests/unit/test_templates_endpoint.py
rm tests/integration/test_templates.py
```

**Step 6.3: DELETE products.py**
```bash
rm api/endpoints/products.py
rm tests/unit/test_products_endpoint.py
rm tests/integration/test_products.py
```

**Step 6.4: Clean Up Imports**
- Remove all imports of deleted files
- Update any code that referenced old endpoints
- Verify no references remain using grep

**Step 6.5: Search for Zombie References**
```bash
# Search for any references to deleted files
grep -r "from.*endpoints.templates import" .
grep -r "from.*endpoints.products import" .

# Delete or update ANY files that reference old code
```

---

## Technical Specifications

### Service Patterns

**Pattern 1: TemplateService Enhancement**
```python
# Add new methods to existing TemplateService
class TemplateService:
    # Existing methods from 0123
    async def list_templates(self, ...) -> dict[str, Any]
    async def get_template(self, ...) -> dict[str, Any]
    async def create_template(self, ...) -> dict[str, Any]
    async def update_template(self, ...) -> dict[str, Any]

    # New methods for 0126
    async def clone_template(self, ...) -> dict[str, Any]
    async def publish_template(self, ...) -> dict[str, Any]
    async def archive_template(self, ...) -> dict[str, Any]
    async def validate_template(self, ...) -> dict[str, Any]
    async def create_template_version(self, ...) -> dict[str, Any]
    async def list_template_versions(self, ...) -> dict[str, Any]
    async def get_template_version(self, ...) -> dict[str, Any]
```

**Pattern 2: ProductService Creation**
```python
# New service following TemplateService pattern
class ProductService:
    def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def create_product(self, ...) -> dict[str, Any]
    async def get_product(self, ...) -> dict[str, Any]
    async def list_products(self, ...) -> dict[str, Any]
    async def update_product(self, ...) -> dict[str, Any]
    async def delete_product(self, ...) -> dict[str, Any]
    async def get_product_settings(self, ...) -> dict[str, Any]
    async def update_product_settings(self, ...) -> dict[str, Any]
    async def get_context_budget(self, ...) -> dict[str, Any]
```

**Pattern 3: Endpoint Delegation**
```python
# All endpoints follow this thin delegation pattern
@router.post("/{template_id}/clone")
async def clone_template(
    template_id: str,
    new_name: str,
    service: TemplateService = Depends(get_template_service),
    tenant_key: str = Depends(get_tenant_key)
):
    result = await service.clone_template(template_id, new_name, tenant_key)
    return handle_service_result(result)
```

### Testing Strategy

**Coverage Targets:**
- ProductService unit tests: >80% code coverage
- Enhanced TemplateService tests: >80% code coverage
- Endpoint integration tests: Full workflow coverage
- Performance tests: < 5% degradation

---

## Success Criteria

### Functional Requirements

✅ All template operations accessible via `/api/v1/templates/*`
✅ All product operations accessible via `/api/v1/products/*`
✅ All endpoints use TemplateService/ProductService (no direct DB access)
✅ File sizes reduced to 150-200 lines per module
✅ Backward compatibility maintained
✅ All endpoints validated with Pydantic
✅ ProductService created and tested

### Quality Requirements

✅ >80% test coverage on ProductService
✅ >80% test coverage on enhanced TemplateService methods
✅ >80% test coverage on endpoint code
✅ All tests passing (unit + integration)
✅ API documentation complete
✅ No performance degradation (< 5% increase)
✅ Code linting passes

### Documentation Requirements

✅ API reference updated
✅ ProductService documentation complete
✅ Migration guide created (if needed)
✅ Architecture diagram updated
✅ Completion document written

---

## Dependencies

### Required Before Start

✅ **Handover 0121 Complete** - ProjectService pattern established (already done)
✅ **Handover 0123 Complete** - TemplateService available (already done)
✅ **Testing Infrastructure** - FastAPI test client

### Concurrent Work

✅ **Can run parallel to 0124** - Different endpoint families
✅ **Can run parallel to 0125** - Different endpoint families
⚠️ **Coordinate with 0127** - May affect deprecated code removal

---

## Risk Assessment

### Risks & Mitigations

**Risk 1: TemplateService Enhancement Complexity**
- **Impact:** Medium
- **Mitigation:** TemplateService already exists from 0123, only adding methods

**Risk 2: Template Versioning Complexity**
- **Impact:** Medium
- **Mitigation:** Design simple version storage using JSON column or separate table

**Risk 3: Product Integration Endpoints**
- **Impact:** Medium
- **Mitigation:** Keep integration logic simple, delegate complex operations to external services

**Risk 4: API Changes**
- **Impact:** High
- **Mitigation:** Maintain backward compatibility, no route changes

---

## Rollback Plan

**Full backup exists before refactoring begins.**

If critical issues arise that cannot be fixed within 1 day:
1. **Revert entire commit** - Use git to rollback all changes
2. **Restore from backup** - Project is fully backed up before starting
3. **Fix issues offline** - Debug in separate branch
4. **Re-attempt refactoring** - Once issues understood

**No partial rollbacks** - Either commit works completely or revert everything.

No data loss risk - only code organization changes, database untouched.

---

## Next Steps After Completion

1. **Handover 0127**: Deprecated Code Removal (unblocked by 0124/0125/0126)
2. **Handover 0128**: API Versioning Strategy
3. **Handover 0129**: Integration Testing

---

**Created:** 2025-11-10
**Author:** Claude (Sonnet 4.5)
**Ready to Execute:** Yes (depends on 0123 ✅)
