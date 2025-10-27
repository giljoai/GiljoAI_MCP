# Testing Guide: Single Active Product Architecture

**Handover**: 0050
**Test Coverage Target**: 90%+

## Test Strategy

This handover uses a 3-tier testing approach:
1. **Unit Tests**: Backend validation logic
2. **API Tests**: Endpoint behavior
3. **Manual UAT**: User experience scenarios

---

## Unit Tests

### Test File: `tests/unit/test_single_active_product.py`

**Test Coverage**:

```python
import pytest
from src.giljo_mcp.models import Product, Project
from api.endpoints.products import get_active_product_info

class TestGetActiveProductInfo:
    """Test active product info retrieval."""

    async def test_no_active_product(self, db_session, tenant):
        """Should return None when no product is active."""
        result = await get_active_product_info(db_session, tenant.key)
        assert result is None

    async def test_active_product_no_projects(self, db_session, tenant, product):
        """Should return product info with 0 active projects."""
        product.is_active = True
        await db_session.commit()

        result = await get_active_product_info(db_session, tenant.key)
        assert result is not None
        assert result['id'] == str(product.id)
        assert result['name'] == product.name
        assert result['active_projects_count'] == 0

    async def test_active_product_with_projects(
        self, db_session, tenant, product, projects
    ):
        """Should count active projects correctly."""
        product.is_active = True
        projects[0].status = 'active'
        projects[1].status = 'active'
        projects[2].status = 'completed'
        await db_session.commit()

        result = await get_active_product_info(db_session, tenant.key)
        assert result['active_projects_count'] == 2

    async def test_multi_tenant_isolation(
        self, db_session, tenant1, tenant2, product1, product2
    ):
        """Tenant A cannot see tenant B's active product."""
        product1.tenant_key = tenant1.key
        product1.is_active = True
        product2.tenant_key = tenant2.key
        product2.is_active = True
        await db_session.commit()

        result = await get_active_product_info(db_session, tenant1.key)
        assert result['id'] == str(product1.id)

        result = await get_active_product_info(db_session, tenant2.key)
        assert result['id'] == str(product2.id)
```

### Test File: `tests/unit/test_project_activation_validation.py`

**Test Coverage**:

```python
class TestProjectActivationValidation:
    """Test project activation requires active parent product."""

    async def test_activate_project_with_active_product(
        self, db_session, product, project
    ):
        """Should succeed when parent product is active."""
        product.is_active = True
        await db_session.commit()

        # Activate project (via endpoint logic)
        project.status = 'active'
        await db_session.commit()
        # Should not raise

    async def test_activate_project_with_inactive_product(
        self, db_session, product, project
    ):
        """Should raise 400 error when parent product is inactive."""
        product.is_active = False
        await db_session.commit()

        # Try to activate project - should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            # Call endpoint logic that validates
            pass
        assert exc_info.value.status_code == 400
        assert "parent product" in exc_info.value.detail.lower()

    async def test_activate_project_no_parent(self, db_session, project):
        """Should raise 400 error when parent product not found."""
        project.product_id = "nonexistent-uuid"

        with pytest.raises(HTTPException) as exc_info:
            # Call endpoint logic
            pass
        assert exc_info.value.status_code == 400
```

### Test File: `tests/unit/test_agent_job_product_validation.py`

**Test Coverage**:

```python
class TestAgentJobProductValidation:
    """Test agent jobs validate product is active."""

    async def test_create_job_with_active_product(
        self, agent_job_manager, product, agent
    ):
        """Should succeed when product is active."""
        product.is_active = True
        await db_session.commit()

        job = await agent_job_manager.create_job(
            agent_id=str(agent.id),
            mission="Test mission",
            product_id=str(product.id),
            tenant_key=product.tenant_key
        )
        assert job is not None
        assert job.status == 'pending'

    async def test_create_job_with_inactive_product(
        self, agent_job_manager, product, agent
    ):
        """Should raise ValueError when product is inactive."""
        product.is_active = False
        await db_session.commit()

        with pytest.raises(ValueError) as exc_info:
            await agent_job_manager.create_job(
                agent_id=str(agent.id),
                mission="Test mission",
                product_id=str(product.id),
                tenant_key=product.tenant_key
            )
        assert "not active" in str(exc_info.value)

    async def test_mission_assignment_validation(
        self, orchestrator, product, agent
    ):
        """Should validate product before mission assignment."""
        product.is_active = False

        with pytest.raises(ValueError):
            await orchestrator.assign_mission_to_agent(
                agent_id=str(agent.id),
                mission="Test",
                product_id=str(product.id)
            )
```

---

## API Tests

### Test File: `tests/api/test_product_activation_api.py`

**Test Coverage**:

```python
class TestProductActivationAPI:
    """Test product activation endpoint behavior."""

    async def test_activate_first_product(self, client, auth_headers, product):
        """Activating first product should return no previous_active_product."""
        response = await client.post(
            f"/api/v1/products/{product.id}/activate",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data['is_active'] is True
        assert data['previous_active_product'] is None

    async def test_activate_second_product(
        self, client, auth_headers, product_a, product_b
    ):
        """Activating second product should return previous product info."""
        # Activate Product A first
        await client.post(
            f"/api/v1/products/{product_a.id}/activate",
            headers=auth_headers
        )

        # Activate Product B
        response = await client.post(
            f"/api/v1/products/{product_b.id}/activate",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data['is_active'] is True
        assert data['previous_active_product'] is not None
        assert data['previous_active_product']['id'] == str(product_a.id)
        assert data['previous_active_product']['name'] == product_a.name

    async def test_delete_active_product(self, client, auth_headers, product):
        """Deleting active product should return was_active=True."""
        # Activate product
        await client.post(
            f"/api/v1/products/{product.id}/activate",
            headers=auth_headers
        )

        # Delete product
        response = await client.delete(
            f"/api/v1/products/{product.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data['was_active'] is True

    async def test_refresh_active_product_store(
        self, client, auth_headers, product
    ):
        """Refresh endpoint should return current active product."""
        # Activate product
        await client.post(
            f"/api/v1/products/{product.id}/activate",
            headers=auth_headers
        )

        # Refresh store
        response = await client.post(
            "/api/v1/products/refresh-active",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data['active_product'] is not None
        assert data['active_product']['id'] == str(product.id)

    async def test_multi_tenant_isolation(
        self, client, auth_headers_tenant_a, auth_headers_tenant_b,
        product_tenant_a, product_tenant_b
    ):
        """Tenant A activation should not affect tenant B."""
        # Tenant A activates their product
        await client.post(
            f"/api/v1/products/{product_tenant_a.id}/activate",
            headers=auth_headers_tenant_a
        )

        # Tenant B activates their product
        response = await client.post(
            f"/api/v1/products/{product_tenant_b.id}/activate",
            headers=auth_headers_tenant_b
        )
        data = response.json()
        # Should not see tenant A's product as previous
        assert data['previous_active_product'] is None
```

---

## Integration Tests

### Test File: `tests/integration/test_single_active_product_flow.py`

**Full Flow Test**:

```python
class TestSingleActiveProductFlow:
    """End-to-end test of single active product architecture."""

    async def test_complete_activation_flow(
        self, client, auth_headers, product_a, product_b, project_a1, project_a2
    ):
        """Test complete flow from activation to project validation."""

        # Step 1: Activate Product A
        response = await client.post(
            f"/api/v1/products/{product_a.id}/activate",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()['previous_active_product'] is None

        # Step 2: Activate Project A1 (should succeed)
        response = await client.patch(
            f"/api/v1/projects/{project_a1.id}",
            json={"status": "active"},
            headers=auth_headers
        )
        assert response.status_code == 200

        # Step 3: Create active projects under Product A
        await client.patch(
            f"/api/v1/projects/{project_a2.id}",
            json={"status": "active"},
            headers=auth_headers
        )

        # Step 4: Activate Product B (should warn about Product A)
        response = await client.post(
            f"/api/v1/products/{product_b.id}/activate",
            headers=auth_headers
        )
        data = response.json()
        assert data['previous_active_product'] is not None
        assert data['previous_active_product']['name'] == product_a.name
        assert data['previous_active_product']['active_projects_count'] == 2

        # Step 5: Verify Product A is now inactive
        response = await client.get(
            f"/api/v1/products/{product_a.id}",
            headers=auth_headers
        )
        assert response.json()['is_active'] is False

        # Step 6: Verify Product B is active
        response = await client.get(
            f"/api/v1/products/{product_b.id}",
            headers=auth_headers
        )
        assert response.json()['is_active'] is True

        # Step 7: Try to activate Project A1 (should fail - parent inactive)
        response = await client.patch(
            f"/api/v1/projects/{project_a1.id}",
            json={"status": "active"},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "parent product" in response.json()['detail'].lower()

        # Step 8: Delete Product B (was active)
        response = await client.delete(
            f"/api/v1/products/{product_b.id}",
            headers=auth_headers
        )
        assert response.json()['was_active'] is True

        # Step 9: Refresh store (should show no active product)
        response = await client.post(
            "/api/v1/products/refresh-active",
            headers=auth_headers
        )
        assert response.json()['active_product'] is None
```

---

## Manual UAT Scenarios

### Scenario 1: First Product Activation

**Steps**:
1. Log into dashboard
2. Navigate to Products page
3. Create a new product "Product A"
4. Click "Activate" on Product A
5. Verify top bar shows "Active: Product A"
6. Verify no warning dialog appeared

**Expected Results**:
- ✅ Product activates immediately (no warning)
- ✅ Top bar updates to show Product A
- ✅ Product card shows "Active" badge

### Scenario 2: Second Product Activation with Warning

**Steps**:
1. Ensure Product A is active
2. Create a new product "Product B"
3. Click "Activate" on Product B
4. Verify warning dialog appears
5. Check warning message mentions Product A
6. Click "Cancel"
7. Verify Product A remains active
8. Click "Activate" on Product B again
9. Click "Activate Product B" in dialog
10. Verify top bar updates to "Active: Product B"

**Expected Results**:
- ✅ Warning dialog shows before activation
- ✅ Dialog mentions Product A by name
- ✅ Cancel keeps Product A active
- ✅ Confirm switches to Product B
- ✅ Top bar updates immediately
- ✅ Product A card no longer shows "Active"
- ✅ Product B card shows "Active"

### Scenario 3: Active Projects Warning

**Steps**:
1. Activate Product A
2. Create Project X under Product A
3. Create Project Y under Product A
4. Activate both projects (set status to "active")
5. Create Product B
6. Click "Activate" on Product B
7. Check warning dialog text

**Expected Results**:
- ✅ Warning shows "Product A has 2 active projects"
- ✅ Warning explains projects will remain but can't be worked on
- ✅ Confirming activation switches products
- ✅ Projects X and Y remain in database with status="active"

### Scenario 4: Project Activation Validation

**Steps**:
1. Create Product A (not active)
2. Create Project X under Product A
3. Go to Projects page
4. Find Project X
5. Try to activate Project X
6. Hover over "Activate" button
7. Activate Product A
8. Refresh Projects page
9. Try to activate Project X again

**Expected Results**:
- ✅ "Activate" button is disabled (step 5)
- ✅ Tooltip shows "Activate parent product first" (step 6)
- ✅ Button becomes enabled after Product A activation (step 9)
- ✅ Activation succeeds

### Scenario 5: Delete Active Product

**Steps**:
1. Activate Product A
2. Verify top bar shows "Active: Product A"
3. Delete Product A
4. Check top bar

**Expected Results**:
- ✅ Delete succeeds
- ✅ Top bar updates to "No Active Product"
- ✅ No errors in console

### Scenario 6: Multi-Tenant Isolation

**Steps**:
1. Log in as Tenant A user
2. Create and activate Product A
3. Log out
4. Log in as Tenant B user
5. Create and activate Product B
6. Verify top bar shows only Product B

**Expected Results**:
- ✅ Tenant B sees only their products
- ✅ Activating Product B shows no previous active product warning
- ✅ Multi-tenant data completely isolated

### Scenario 7: Agent Job Creation

**Steps**:
1. Create Product A (not active)
2. Create Project X under Product A
3. Try to create an agent job via orchestrator
4. Verify error message
5. Activate Product A
6. Try again

**Expected Results**:
- ✅ Job creation fails with clear error (step 3)
- ✅ Error mentions product must be active
- ✅ Job creation succeeds after activation (step 6)

---

## Performance Testing

### Load Test: Rapid Activation Switching

**Scenario**: User rapidly switches between 10 products

**Setup**:
```python
products = [create_product(f"Product {i}") for i in range(10)]

for product in products:
    activate_product(product.id)
    time.sleep(0.1)  # 100ms between activations
```

**Success Criteria**:
- All activations complete without error
- No race conditions
- Final active product is correct
- Database consistent (only one is_active=True)

### Concurrent Activation Test

**Scenario**: Multiple users (different tenants) activate products simultaneously

**Setup**:
```python
import asyncio

async def tenant_activates(tenant_id, product_id):
    return await api.products.activateProduct(product_id, tenant_key=tenant_id)

# 10 tenants activate simultaneously
await asyncio.gather(*[
    tenant_activates(f"tenant_{i}", product_ids[i])
    for i in range(10)
])
```

**Success Criteria**:
- All activations succeed
- No cross-tenant interference
- Each tenant has exactly one active product

---

## Accessibility Testing

### Keyboard Navigation

**Test**:
1. Tab to "Activate" button on product card
2. Press Enter
3. Tab through warning dialog
4. Press Space on "Activate Product B" button

**Expected**:
- All interactive elements keyboard-accessible
- Focus visible throughout
- Dialog can be cancelled with Escape

### Screen Reader Testing

**Test**: Use screen reader (NVDA/JAWS) to navigate product activation flow

**Expected**:
- Warning dialog content announced clearly
- Active projects count announced
- Button states announced ("disabled")
- Tooltip content accessible

---

## Test Coverage Requirements

### Backend Coverage Target: 90%+

**Covered Areas**:
- Product activation logic
- Project validation
- Agent job validation
- Multi-tenant isolation
- Error handling

### Frontend Coverage Target: 80%+

**Covered Areas**:
- Warning dialog component
- Product activation flow
- Store state management
- Button disable logic

---

## Test Execution Checklist

**Before Deployment**:
- [ ] All unit tests pass (90%+ coverage)
- [ ] All API tests pass
- [ ] Integration test passes
- [ ] All 7 manual UAT scenarios completed
- [ ] Performance tests pass
- [ ] Accessibility tests pass
- [ ] Multi-tenant isolation verified
- [ ] No console errors in any scenario
- [ ] Documentation reviewed

---

## Bug Reporting Template

If issues found during testing:

```markdown
### Bug Report: [Title]

**Scenario**: [Which test scenario]
**Steps to Reproduce**:
1. Step 1
2. Step 2
3. ...

**Expected**: [What should happen]
**Actual**: [What actually happened]
**Severity**: [Critical/High/Medium/Low]

**Console Errors**: [Any errors in browser/server console]
**Screenshot**: [If applicable]

**Environment**:
- Browser: [Chrome 120 / Firefox 121 / etc]
- OS: [Windows 11 / macOS 14 / Ubuntu 22.04]
- Server Version: [git commit hash]
```

---

**End of Testing Guide**
