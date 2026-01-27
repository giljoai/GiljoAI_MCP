# Handover 0480i: Integration Testing & E2E Verification

**Date:** 2026-01-26
**From Agent:** Documentation Manager
**To Agent:** Backend Integration Tester + Frontend Tester
**Priority:** CRITICAL
**Estimated Complexity:** 12-14 hours
**Status:** Ready for Implementation
**Series:** 0480 (Exception Handling Architecture Remediation)
**Dependencies:** Handovers 0480g (Endpoints), 0480h (Frontend)

---

## Executive Summary

### What
Comprehensive integration testing to verify exception handling architecture works end-to-end:
- Backend: Services → Endpoints → HTTP responses
- Frontend: API calls → Error handling → UI updates
- E2E: User actions → Errors → Recovery flows

### Why
**Validation Required:**
- 205 endpoints migrated (need regression testing)
- 7 services migrated (need integration verification)
- Frontend error handling updated (need UX testing)
- Exception framework is new (need confidence)

**Risk Mitigation:**
- Catch breaking changes before production
- Verify HTTP status codes unchanged
- Ensure frontend handles all error scenarios
- Test error recovery workflows

### Impact
- **Test Coverage**: 54+ integration tests, 20+ E2E tests
- **Confidence**: 95%+ (comprehensive error path coverage)
- **Time**: 12-14 hours (can run in parallel)

---

## Test Strategy

### Layer 1: Service Integration Tests (4 hours)

Verify services raise correct exceptions when called from endpoints.

**Test File**: `tests/integration/test_service_exception_integration.py`

```python
"""
Integration tests for service-layer exception handling.
Verify exceptions propagate correctly through service → endpoint → HTTP.
"""
import pytest
from httpx import AsyncClient


class TestProjectServiceIntegration:
    """Test ProjectService exception handling in API context."""

    @pytest.mark.asyncio
    async def test_get_project_404(self, client: AsyncClient, auth_headers):
        """GET /projects/{id} returns 404 when project not found."""
        response = await client.get("/api/projects/nonexistent", headers=auth_headers)

        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "PROJECT_NOT_FOUND"
        assert "nonexistent" in data["message"]
        assert data["metadata"]["project_id"] == "nonexistent"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_create_project_409(self, client: AsyncClient, auth_headers, test_project):
        """POST /projects returns 409 when alias conflicts."""
        response = await client.post(
            "/api/projects/",
            json={
                "name": "Duplicate",
                "alias": test_project.alias,
                "description": "Test",
                "product_id": test_project.product_id
            },
            headers=auth_headers
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error_code"] == "PROJECT_ALREADY_EXISTS"
        assert test_project.alias in data["message"]

    @pytest.mark.asyncio
    async def test_update_project_400(self, client: AsyncClient, auth_headers, test_project):
        """PUT /projects/{id} returns 400 for invalid status transition."""
        # First set status to 'deleted'
        test_project.status = "deleted"
        await test_project.save()

        # Try to activate (invalid transition)
        response = await client.post(
            f"/api/projects/{test_project.id}/activate",
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "INVALID_PROJECT_STATUS"
        assert "deleted" in data["message"]

    @pytest.mark.asyncio
    async def test_delete_project_409_active_jobs(
        self,
        client: AsyncClient,
        auth_headers,
        test_project,
        test_agent_job
    ):
        """DELETE /projects/{id} returns 409 when project has active jobs."""
        test_agent_job.project_id = test_project.id
        test_agent_job.status = "active"
        await test_agent_job.save()

        response = await client.delete(
            f"/api/projects/{test_project.id}",
            headers=auth_headers
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error_code"] == "PROJECT_HAS_ACTIVE_JOBS"
        assert data["metadata"]["active_jobs"] > 0


class TestProductServiceIntegration:
    """Similar tests for ProductService..."""
    # 10+ tests following same pattern


class TestMessageServiceIntegration:
    """Similar tests for MessageService..."""
    # 10+ tests following same pattern
```

**Coverage**: 54 tests across 7 services

---

### Layer 2: API Error Response Tests (3 hours)

Verify all endpoints return correct HTTP status codes and error structures.

**Test File**: `tests/integration/test_api_error_responses.py`

```python
"""
Test that all API endpoints return proper error responses.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.parametrize("endpoint,method,expected_404", [
    ("/api/projects/{id}", "GET", "PROJECT_NOT_FOUND"),
    ("/api/products/{id}", "GET", "PRODUCT_NOT_FOUND"),
    ("/api/agent-jobs/{id}", "GET", "AGENT_JOB_NOT_FOUND"),
    ("/api/templates/{name}", "GET", "TEMPLATE_NOT_FOUND"),
    ("/api/messages/{id}", "GET", "MESSAGE_NOT_FOUND"),
])
@pytest.mark.asyncio
async def test_endpoints_return_404(
    client: AsyncClient,
    auth_headers,
    endpoint,
    method,
    expected_404
):
    """All GET endpoints return 404 with correct error_code."""
    url = endpoint.format(id="nonexistent", name="nonexistent")

    response = await client.request(method, url, headers=auth_headers)

    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == expected_404
    assert "timestamp" in data


@pytest.mark.parametrize("endpoint,method,payload,expected_409", [
    ("/api/projects/", "POST", {"name": "Dup", "alias": "DUP"}, "PROJECT_ALREADY_EXISTS"),
    ("/api/products/", "POST", {"name": "Dup"}, "PRODUCT_ALREADY_EXISTS"),
])
@pytest.mark.asyncio
async def test_endpoints_return_409_conflict(
    client: AsyncClient,
    auth_headers,
    endpoint,
    method,
    payload,
    expected_409
):
    """Create endpoints return 409 on duplicate."""
    # Create first resource
    await client.request(method, endpoint, json=payload, headers=auth_headers)

    # Try to create duplicate
    response = await client.request(method, endpoint, json=payload, headers=auth_headers)

    assert response.status_code == 409
    data = response.json()
    assert data["error_code"] == expected_409
```

**Coverage**: 20+ parameterized tests covering all error codes

---

### Layer 3: Frontend Integration Tests (3 hours)

Verify frontend correctly handles backend error responses.

**Test File**: `frontend/tests/integration/errorHandling.spec.js`

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import ProjectCreateForm from '@/components/projects/ProjectCreateForm.vue'
import { useToast } from '@/composables/useToast'

describe('Frontend Error Handling', () => {
  let wrapper
  let mockApi

  beforeEach(() => {
    mockApi = vi.fn()
    wrapper = mount(ProjectCreateForm, {
      global: {
        plugins: [createTestingPinia()],
        mocks: { $api: mockApi }
      }
    })
  })

  it('shows warning toast for 400 validation error', async () => {
    mockApi.mockRejectedValue({
      response: {
        status: 400,
        data: {
          error_code: 'INVALID_PROJECT_STATUS',
          message: 'Cannot transition from active to deleted',
          metadata: { current: 'active', attempted: 'deleted' },
          timestamp: '2026-01-26T10:00:00Z'
        }
      }
    })

    await wrapper.find('form').trigger('submit')

    // Verify toast shown
    const { showError } = useToast()
    expect(showError).toHaveBeenCalled()

    // Verify toast properties
    const errorInfo = showError.mock.results[0].value
    expect(errorInfo.type).toBe('user_error')
    expect(errorInfo.title).toBe('Invalid Input')
    expect(errorInfo.message).toContain('Cannot transition')
  })

  it('redirects on 404 not found error', async () => {
    const mockRouter = { push: vi.fn() }

    mockApi.mockRejectedValue({
      response: {
        status: 404,
        data: {
          error_code: 'PROJECT_NOT_FOUND',
          message: 'Project abc123 not found',
          metadata: { project_id: 'abc123' },
          timestamp: '2026-01-26T10:00:00Z'
        }
      }
    })

    await wrapper.find('form').trigger('submit')

    // Verify redirect scheduled
    await vi.runAllTimers()
    expect(mockRouter.push).toHaveBeenCalledWith('/projects')
  })

  it('highlights fields on 422 validation error', async () => {
    mockApi.mockRejectedValue({
      response: {
        status: 422,
        data: {
          error_code: 'VALIDATION_ERROR',
          message: 'Request validation failed',
          errors: [
            { loc: ['body', 'name'], msg: 'Field required' },
            { loc: ['body', 'alias'], msg: 'String should have at least 3 characters' }
          ],
          timestamp: '2026-01-26T10:00:00Z'
        }
      }
    })

    await wrapper.find('form').trigger('submit')

    // Verify field errors set
    const nameField = wrapper.find('input[label="Project Name"]')
    expect(nameField.props('error-messages')).toBe('Field required')

    const aliasField = wrapper.find('input[label="Project Alias"]')
    expect(aliasField.props('error-messages')).toBe('String should have at least 3 characters')
  })

  it('shows error code copy button for 500 errors', async () => {
    mockApi.mockRejectedValue({
      response: {
        status: 500,
        data: {
          error_code: 'INTERNAL_SERVER_ERROR',
          message: 'An unexpected error occurred',
          timestamp: '2026-01-26T10:00:00Z'
        }
      }
    })

    await wrapper.find('form').trigger('submit')

    // Verify toast has copy button
    const toast = wrapper.findComponent({ name: 'VToast' })
    expect(toast.find('button').text()).toBe('Copy Error Code')
  })
})
```

**Coverage**: 15+ tests covering all error scenarios

---

### Layer 4: E2E Workflow Tests (4 hours)

Test complete user workflows with error recovery.

**Test File**: `tests/e2e/error_workflows.spec.js`

```javascript
import { test, expect } from '@playwright/test'

test.describe('Error Recovery Workflows', () => {
  test('user creates project with duplicate alias, corrects, succeeds', async ({ page }) => {
    await page.goto('/projects/new')

    // Fill form
    await page.fill('[label="Project Name"]', 'Test Project')
    await page.fill('[label="Project Alias"]', 'EXISTING')
    await page.click('button[type="submit"]')

    // Verify 409 error shown
    await expect(page.locator('.v-toast')).toContainText('Conflict')
    await expect(page.locator('.v-toast')).toContainText('already exists')

    // Verify alias field highlighted
    await expect(page.locator('[label="Project Alias"]')).toHaveClass(/error/)

    // Correct alias
    await page.fill('[label="Project Alias"]', 'UNIQUE')
    await page.click('button[type="submit"]')

    // Verify success
    await expect(page.locator('.v-toast')).toContainText('Success')
    await expect(page).toHaveURL('/projects')
  })

  test('user accesses deleted project, redirected to list', async ({ page }) => {
    // Navigate to project that was just deleted
    await page.goto('/projects/deleted-project-id')

    // Verify 404 toast shown
    await expect(page.locator('.v-toast')).toContainText('Not Found')
    await expect(page.locator('.v-toast')).toContainText('Redirecting')

    // Verify redirect happens
    await page.waitForURL('/projects', { timeout: 5000 })
  })

  test('user attempts invalid status transition, sees guidance', async ({ page }) => {
    await page.goto('/projects/test-project-id')

    // Try to delete active project with jobs
    await page.click('button[aria-label="Delete Project"]')

    // Verify 409 error with guidance
    await expect(page.locator('.v-toast')).toContainText('Conflict')
    await expect(page.locator('.v-toast')).toContainText('active job')
    await expect(page.locator('.v-toast')).toContainText('Complete or cancel')

    // Verify "Copy Error Code" button available
    await expect(page.locator('.v-toast button:has-text("Copy Error Code")')).toBeVisible()
  })

  test('user encounters server error, sees support contact', async ({ page }) => {
    // Mock 500 error
    await page.route('/api/projects/', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({
          error_code: 'INTERNAL_SERVER_ERROR',
          message: 'Unexpected database error',
          timestamp: new Date().toISOString()
        })
      })
    })

    await page.goto('/projects/new')
    await page.fill('[label="Project Name"]', 'Test')
    await page.click('button[type="submit"]')

    // Verify error toast
    await expect(page.locator('.v-toast')).toContainText('System Error')
    await expect(page.locator('.v-toast')).toContainText('contact support')

    // Verify error persists longer (10 seconds)
    await page.waitForTimeout(8000)
    await expect(page.locator('.v-toast')).toBeVisible()
  })
})
```

**Coverage**: 20+ E2E tests for error workflows

---

## Fresh Install Testing

### Test Scenario: Clean Database

Verify exception handling works on fresh installation:

```bash
# Drop and recreate database
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp_test;"
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "CREATE DATABASE giljo_mcp_test;"

# Run install
python install.py --test

# Start server
python startup.py --test

# Run full test suite
pytest tests/integration/ -v
pytest frontend/tests/integration/ -v
npx playwright test tests/e2e/
```

**Expected Results:**
- All migrations apply cleanly
- All integration tests pass
- All E2E tests pass
- No error in logs

---

## Regression Testing

### Test Matrix: All Error Codes

Ensure all error codes return correct HTTP status:

| Error Code | HTTP Status | Service | Endpoint | Test Status |
|------------|-------------|---------|----------|-------------|
| PROJECT_NOT_FOUND | 404 | ProjectService | GET /projects/{id} | [ ] |
| PROJECT_ALREADY_EXISTS | 409 | ProjectService | POST /projects/ | [ ] |
| INVALID_PROJECT_STATUS | 400 | ProjectService | PUT /projects/{id} | [ ] |
| PROJECT_HAS_ACTIVE_JOBS | 409 | ProjectService | DELETE /projects/{id} | [ ] |
| PRODUCT_NOT_FOUND | 404 | ProductService | GET /products/{id} | [ ] |
| PRODUCT_HAS_ACTIVE_PROJECTS | 409 | ProductService | DELETE /products/{id} | [ ] |
| AGENT_JOB_NOT_FOUND | 404 | AgentJobManager | GET /agent-jobs/{id} | [ ] |
| INVALID_JOB_STATUS_TRANSITION | 400 | AgentJobManager | PUT /agent-jobs/{id} | [ ] |
| MESSAGE_NOT_FOUND | 404 | MessageService | GET /messages/{id} | [ ] |
| MESSAGE_ALREADY_ACKNOWLEDGED | 409 | MessageService | POST /messages/{id}/ack | [ ] |
| TEMPLATE_NOT_FOUND | 404 | TemplateService | GET /templates/{name} | [ ] |
| CONTEXT_FIELD_NOT_FOUND | 404 | ContextService | GET /context/{field} | [ ] |
| INVALID_CONTEXT_PRIORITY | 400 | ContextService | PUT /context/{field} | [ ] |
| SETTING_NOT_FOUND | 404 | SettingsService | GET /settings/{key} | [ ] |
| VALIDATION_ERROR | 422 | (Pydantic) | Any POST/PUT | [ ] |
| INTERNAL_SERVER_ERROR | 500 | (Unexpected) | Any endpoint | [ ] |

**Test Command:**
```bash
pytest tests/integration/test_api_error_responses.py::test_all_error_codes -v
```

---

## Performance Testing

### Verify No Performance Degradation

Exception handling should not slow down happy paths:

```python
import pytest
import time


@pytest.mark.benchmark
async def test_exception_handling_performance(client, auth_headers):
    """Verify exception handling doesn't impact happy path performance."""

    # Baseline: Successful request
    start = time.time()
    for _ in range(100):
        await client.get("/api/projects/", headers=auth_headers)
    baseline_time = time.time() - start

    # Error path: 404 requests
    start = time.time()
    for _ in range(100):
        await client.get("/api/projects/nonexistent", headers=auth_headers)
    error_time = time.time() - start

    # Error path should not be >20% slower
    assert error_time < baseline_time * 1.2
```

---

## Success Criteria

- [ ] 54 service integration tests pass
- [ ] 20 API error response tests pass
- [ ] 15 frontend integration tests pass
- [ ] 20 E2E workflow tests pass
- [ ] Fresh install test passes
- [ ] All error codes in matrix verified
- [ ] No performance degradation (<20% slower)
- [ ] Zero test failures in CI pipeline

---

**Document Version**: 1.0
**Created**: 2026-01-26
**Author**: Claude (Sonnet 4.5)
**Status**: Ready for Implementation
