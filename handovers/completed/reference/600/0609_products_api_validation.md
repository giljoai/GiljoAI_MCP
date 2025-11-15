# Handover 0609: Products API Validation

**Phase**: 2
**Tool**: CCW (Cloud)
**Agent Type**: api-tester
**Duration**: 4 hours
**Parallel Group**: Group B (APIs)
**Depends On**: 0603-0608

---

## Context

**Read First**: `handovers/600/AGENT_REFERENCE_GUIDE.md` for universal project context.

**Previous Handovers**: Phase 1 completed - all 6 services validated with 80%+ coverage. ProductService tests passing.

**This Handover**: Create comprehensive API integration tests for all 12 product endpoints, validating authentication, multi-tenant isolation, request/response schemas, and error handling.

---

## Specific Objectives

- **Objective 1**: Create API integration tests for all 12 product endpoints
- **Objective 2**: Validate authentication (401 on missing token, 403 on wrong tenant)
- **Objective 3**: Test request/response schemas (Pydantic model validation)
- **Objective 4**: Verify multi-tenant isolation at API layer
- **Objective 5**: Test error responses (400, 404, 500 handling)
- **Objective 6**: Validate vision upload and config_data endpoints

---

## Tasks

### Task 1: Analyze Products API Endpoints
**What**: Read products API implementation
**Files**: `api/endpoints/products.py`

**Endpoints to Test** (12 total):
1. `GET /api/v1/products` - List products
2. `POST /api/v1/products` - Create product
3. `GET /api/v1/products/{id}` - Get product
4. `PUT /api/v1/products/{id}` - Update product
5. `DELETE /api/v1/products/{id}` - Soft delete
6. `POST /api/v1/products/{id}/activate` - Activate product
7. `POST /api/v1/products/{id}/deactivate` - Deactivate product
8. `POST /api/v1/products/{id}/vision/upload` - Upload vision file
9. `GET /api/v1/products/{id}/vision` - Get vision
10. `GET /api/v1/products/{id}/config` - Get config_data
11. `PUT /api/v1/products/{id}/config` - Update config_data
12. `GET /api/v1/products/active` - Get active product
13. `POST /api/v1/products/{id}/recover` - Recover deleted product

### Task 2: Create API Test Structure
**What**: Create API test file with fixtures
**Files**: `tests/api/test_products_api.py`

**Test Structure**:
```python
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def api_client(db_session):
    """Fixture providing FastAPI test client"""
    from api.app import app
    return TestClient(app)

@pytest.fixture
def auth_headers(test_user_token):
    """Fixture providing authentication headers"""
    return {"Authorization": f"Bearer {test_user_token}"}

@pytest.fixture
def test_product(api_client, auth_headers):
    """Fixture providing a test product"""
    response = api_client.post(
        "/api/v1/products",
        json={"name": "Test Product", "description": "Test"},
        headers=auth_headers
    )
    return response.json()
```

### Task 3: Implement CRUD Endpoint Tests
**What**: Test create, read, update, delete endpoints
**Files**: `tests/api/test_products_api.py`

**Test Coverage** (26 tests):

**Create (POST /api/v1/products)** (6 tests):
- `test_create_product_success_201`
- `test_create_product_missing_auth_401`
- `test_create_product_invalid_data_400`
- `test_create_product_duplicate_name_409`
- `test_create_product_response_schema`
- `test_create_product_returns_id`

**Read (GET /api/v1/products)** (5 tests):
- `test_list_products_success_200`
- `test_list_products_missing_auth_401`
- `test_list_products_tenant_isolation`
- `test_list_products_pagination`
- `test_list_products_filtering`

**Get (GET /api/v1/products/{id})** (4 tests):
- `test_get_product_success_200`
- `test_get_product_not_found_404`
- `test_get_product_wrong_tenant_403`
- `test_get_product_response_schema`

**Update (PUT /api/v1/products/{id})** (5 tests):
- `test_update_product_success_200`
- `test_update_product_not_found_404`
- `test_update_product_wrong_tenant_403`
- `test_update_product_invalid_data_400`
- `test_update_product_response_schema`

**Delete (DELETE /api/v1/products/{id})** (4 tests):
- `test_delete_product_success_204`
- `test_delete_product_not_found_404`
- `test_delete_product_wrong_tenant_403`
- `test_delete_product_soft_delete_verified`

**Recover (POST /api/v1/products/{id}/recover)** (2 tests):
- `test_recover_product_success_200`
- `test_recover_product_not_deleted_400`

### Task 4: Implement Activation Endpoint Tests
**What**: Test activate/deactivate/get active endpoints
**Files**: `tests/api/test_products_api.py`

**Test Coverage** (7 tests):
- `test_activate_product_success_200`
- `test_activate_product_deactivates_others`
- `test_activate_product_not_found_404`
- `test_deactivate_product_success_200`
- `test_get_active_product_success_200`
- `test_get_active_product_none_active_204`
- `test_get_active_product_tenant_isolation`

### Task 5: Implement Vision Upload Endpoint Tests
**What**: Test vision upload and retrieval endpoints
**Files**: `tests/api/test_products_api.py`

**Test Coverage** (6 tests):
- `test_upload_vision_text_success_200`
- `test_upload_vision_file_success_200`
- `test_upload_vision_replaces_existing`
- `test_upload_vision_not_found_404`
- `test_get_vision_success_200`
- `test_get_vision_not_found_404`

### Task 6: Implement Config Data Endpoint Tests
**What**: Test config_data get/update endpoints
**Files**: `tests/api/test_products_api.py`

**Test Coverage** (5 tests):
- `test_get_config_success_200`
- `test_get_config_empty_config`
- `test_update_config_success_200`
- `test_update_config_merge_jsonb`
- `test_update_config_not_found_404`

### Task 7: Implement Authentication and Security Tests
**What**: Test authentication and multi-tenant isolation
**Files**: `tests/api/test_products_api.py`

**Test Coverage** (6 tests):
- `test_missing_token_returns_401`
- `test_invalid_token_returns_401`
- `test_expired_token_returns_401`
- `test_wrong_tenant_returns_403`
- `test_tenant_cannot_see_other_products`
- `test_tenant_cannot_modify_other_products`

### Task 8: Run Tests and Verify Coverage
**Commands**:
```bash
# Run API tests
pytest tests/api/test_products_api.py -v

# Verify all endpoints tested
pytest tests/api/test_products_api.py --collect-only | grep "test_" | wc -l
# Expected: 55+ tests
```

---

## Success Criteria

- [ ] **All 12 Endpoints**: Every endpoint has tests (happy path + error cases)
- [ ] **Authentication**: 401/403 responses verified
- [ ] **Multi-Tenant**: Zero tenant leakage verified
- [ ] **Response Schemas**: Pydantic models validated
- [ ] **All Tests Pass**: 100% pass rate
- [ ] **PR Created**: Branch `0609-products-api-tests`

---

## Validation Steps

```bash
# Run all product API tests
pytest tests/api/test_products_api.py -v

# Verify test count
pytest tests/api/test_products_api.py --collect-only
# Expected: 55+ tests collected

# Verify no failures
pytest tests/api/test_products_api.py --tb=short
# Expected: 0 failures, 0 errors
```

---

## Deliverables

### Code
- **Created**: `tests/api/test_products_api.py` (55+ tests)

### Git Commit
- **Message**: `test: Add comprehensive Products API tests (Handover 0609)`
- **Branch**: `0609-products-api-tests`

---

## Dependencies

### Requires
- **Handovers 0603-0608**: Service tests passing
- **Files**: `api/endpoints/products.py`

### Blocks
- **Handover 0619**: Core workflows E2E testing

---

## Notes for Agent

### CCW (Cloud) Execution
- Create branch: `0609-products-api-tests`
- Use FastAPI TestClient for API testing
- Mock database if needed

### Common Patterns
- Authentication: See AGENT_REFERENCE_GUIDE.md "API Authentication Pattern"
- API testing: See "API Endpoint Pattern"

---

**Document Control**:
- **Handover**: 0609
- **Created**: 2025-11-14
- **Status**: Ready for execution
