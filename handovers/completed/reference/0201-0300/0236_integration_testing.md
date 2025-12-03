# Handover 0236: Integration Testing

**Status**: Ready for Implementation
**Priority**: High
**Estimated Effort**: 6 hours
**Dependencies**: Handovers 0225-0235 (all previous refactor handovers)
**Part of**: Visual Refactor Series (0225-0237)

---

## Before You Begin

**REQUIRED READING** (Critical for TDD discipline and architectural alignment):

1. **F:\GiljoAI_MCP\handovers\QUICK_LAUNCH.txt**
   - TDD discipline (Red → Green → Refactor)
   - Write tests FIRST (behavior, not implementation)
   - No zombie code policy (delete, don't comment)

2. **F:\GiljoAI_MCP\handovers\013A_code_review_architecture_status.md**
   - Service layer patterns
   - Multi-tenant isolation
   - Component reuse principles

3. **F:\GiljoAI_MCP\handovers\code_review_nov18.md**
   - Past mistakes to avoid (ProductsView 2,582 lines)
   - Success patterns to follow (ProjectsView componentization)

**Execute in order**: Red (failing tests) → Green (minimal implementation) → Refactor (cleanup)

---

## Objective

Implement comprehensive E2E integration tests for the complete status board workflow, covering table data loading, WebSocket real-time updates, user interactions, multi-tenant isolation, and cross-browser compatibility. Achieve >80% test coverage for new components.

---

## Current State Analysis

### Existing Test Infrastructure

**Location**: `tests/`

**Backend Testing** (pytest):
- `tests/api/` - API endpoint tests
- `tests/services/` - Service layer tests
- `tests/integration/` - Integration tests
- `tests/models/` - Database model tests

**Frontend Testing** (Jest/Vitest):
- `frontend/tests/unit/` - Component unit tests
- `frontend/tests/e2e/` - End-to-end tests (Playwright/Cypress)

**Coverage Tools**:
- Backend: `pytest-cov`
- Frontend: `vitest --coverage` or `jest --coverage`

### Test Scenarios from Vision Document

**Slides 10-27** show complete workflow:
1. Initial table load (waiting state)
2. Toggle Claude Code CLI mode on/off
3. Copy and launch orchestrator prompt
4. Orchestrator starts working
5. Messages sent/received
6. Status changes (working → complete)
7. Health indicators update
8. Staleness warnings appear
9. Real-time WebSocket updates

---

## Implementation Plan

### 1. Backend Integration Tests

**File**: `tests/integration/test_status_board_table.py` (NEW)

Comprehensive backend integration tests:

```python
"""
Integration tests for status board table view endpoint
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta


@pytest.mark.asyncio
class TestStatusBoardTableView:
    """Test /api/agent-jobs/table-view endpoint"""

    async def test_table_view_basic_load(
        self,
        async_client: AsyncClient,
        test_project,
        auth_headers
    ):
        """Test basic table view data retrieval"""

        response = await async_client.get(
            "/api/agent-jobs/table-view",
            params={"project_id": test_project.project_id},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "rows" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["project_id"] == test_project.project_id

    async def test_table_view_message_counts(
        self,
        async_client: AsyncClient,
        test_project,
        test_agent_job,
        auth_headers,
        db_session
    ):
        """Test message count aggregation"""

        # Send messages to agent
        from src.giljo_mcp.tools.agent_messaging import send_mcp_message

        # Send 3 unread messages
        for i in range(3):
            await send_mcp_message(
                db_session=db_session,
                from_job_id="user",
                to_job_id=test_agent_job.job_id,
                content=f"Test message {i}",
                tenant_key=test_project.tenant_key,
                message_type="user"
            )

        await db_session.commit()

        # Fetch table view
        response = await async_client.get(
            "/api/agent-jobs/table-view",
            params={"project_id": test_project.project_id},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Find our job
        job_row = next(r for r in data["rows"] if r["job_id"] == test_agent_job.job_id)

        # Verify counts
        assert job_row["unread_count"] == 3
        assert job_row["acknowledged_count"] == 0
        assert job_row["total_messages"] == 3

    async def test_table_view_filtering_by_status(
        self,
        async_client: AsyncClient,
        test_project,
        auth_headers
    ):
        """Test filtering jobs by status"""

        response = await async_client.get(
            "/api/agent-jobs/table-view",
            params={
                "project_id": test_project.project_id,
                "status": ["working", "waiting"]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all rows match filter
        for row in data["rows"]:
            assert row["status"] in ["working", "waiting"]

        # Verify filters applied
        assert "status" in data["filters_applied"]
        assert data["filters_applied"]["status"] == ["working", "waiting"]

    async def test_table_view_filtering_by_health(
        self,
        async_client: AsyncClient,
        test_project,
        auth_headers
    ):
        """Test filtering jobs by health status"""

        response = await async_client.get(
            "/api/agent-jobs/table-view",
            params={
                "project_id": test_project.project_id,
                "health_status": ["warning", "critical"]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all rows match filter
        for row in data["rows"]:
            assert row["health_status"] in ["warning", "critical"]

    async def test_table_view_sorting_by_last_progress(
        self,
        async_client: AsyncClient,
        test_project,
        auth_headers
    ):
        """Test sorting by last progress time"""

        response = await async_client.get(
            "/api/agent-jobs/table-view",
            params={
                "project_id": test_project.project_id,
                "sort_by": "last_progress",
                "sort_order": "desc"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify descending order (most recent first)
        rows = data["rows"]
        if len(rows) > 1:
            for i in range(len(rows) - 1):
                if rows[i]["last_progress_at"] and rows[i + 1]["last_progress_at"]:
                    date_i = datetime.fromisoformat(rows[i]["last_progress_at"].replace('Z', '+00:00'))
                    date_next = datetime.fromisoformat(rows[i + 1]["last_progress_at"].replace('Z', '+00:00'))
                    assert date_i >= date_next

    async def test_table_view_pagination(
        self,
        async_client: AsyncClient,
        test_project,
        auth_headers
    ):
        """Test pagination with limit and offset"""

        # Page 1
        response1 = await async_client.get(
            "/api/agent-jobs/table-view",
            params={
                "project_id": test_project.project_id,
                "limit": 10,
                "offset": 0
            },
            headers=auth_headers
        )

        # Page 2
        response2 = await async_client.get(
            "/api/agent-jobs/table-view",
            params={
                "project_id": test_project.project_id,
                "limit": 10,
                "offset": 10
            },
            headers=auth_headers
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Verify different rows returned
        ids1 = {row["job_id"] for row in data1["rows"]}
        ids2 = {row["job_id"] for row in data2["rows"]}
        assert ids1.isdisjoint(ids2)  # No overlap

    async def test_table_view_staleness_calculation(
        self,
        async_client: AsyncClient,
        test_project,
        test_agent_job,
        auth_headers,
        db_session
    ):
        """Test staleness flag for inactive jobs"""

        # Set last_progress_at to 11 minutes ago
        eleven_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=11)
        test_agent_job.last_progress_at = eleven_minutes_ago
        test_agent_job.status = "working"  # Not a terminal state
        await db_session.commit()

        response = await async_client.get(
            "/api/agent-jobs/table-view",
            params={"project_id": test_project.project_id},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        job_row = next(r for r in data["rows"] if r["job_id"] == test_agent_job.job_id)

        # Verify staleness
        assert job_row["is_stale"] is True
        assert job_row["minutes_since_progress"] >= 11

    async def test_multi_tenant_isolation(
        self,
        async_client: AsyncClient,
        test_project,
        other_tenant_project,
        auth_headers
    ):
        """Test that tenant A cannot see tenant B's jobs"""

        response = await async_client.get(
            "/api/agent-jobs/table-view",
            params={"project_id": test_project.project_id},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify no jobs from other tenant
        other_tenant_ids = {row["job_id"] for row in data["rows"]}
        # Query other tenant's jobs and ensure they're not in result
        # (implementation depends on test fixtures)


@pytest.mark.asyncio
class TestWebSocketTableUpdates:
    """Test WebSocket events for table updates"""

    async def test_message_new_event_updates_table(
        self,
        websocket_client,
        test_agent_job,
        db_session
    ):
        """Test that message:new event triggers table update"""

        # Connect WebSocket
        async with websocket_client as ws:
            # Send message
            from src.giljo_mcp.tools.agent_messaging import send_mcp_message

            await send_mcp_message(
                db_session=db_session,
                from_job_id="user",
                to_job_id=test_agent_job.job_id,
                content="Test message",
                tenant_key=test_agent_job.tenant_key,
                message_type="user"
            )

            # Wait for WebSocket event
            message = await ws.receive_json(timeout=2)

            # Verify event
            assert message["event"] == "message:new"
            assert message["job_id"] == test_agent_job.job_id

    async def test_job_table_update_batch_event(
        self,
        websocket_client,
        test_project
    ):
        """Test batch job:table_update event"""

        from api.websocket import broadcast_table_update

        async with websocket_client as ws:
            # Broadcast batch update
            await broadcast_table_update(
                tenant_key=test_project.tenant_key,
                project_id=test_project.project_id,
                job_updates=[
                    {"job_id": "job-1", "status": "complete"},
                    {"job_id": "job-2", "status": "failed"}
                ],
                event_type="status_change"
            )

            # Wait for event
            message = await ws.receive_json(timeout=2)

            # Verify batch update
            assert message["event"] == "job:table_update"
            assert len(message["updates"]) == 2
```

### 2. Frontend E2E Tests

**File**: `frontend/tests/e2e/status-board.spec.js` (NEW)

End-to-end tests using Playwright/Cypress:

```javascript
/**
 * E2E tests for status board table
 */

describe('Status Board Table', () => {
  beforeEach(() => {
    cy.login();
    cy.visit('/dashboard');
  });

  it('loads table with job data', () => {
    cy.get('.status-board-table').should('be.visible');
    cy.get('.v-data-table__wrapper').should('exist');

    // Verify headers
    cy.contains('Agent Type').should('be.visible');
    cy.contains('Agent Status').should('be.visible');
    cy.contains('Job Read').should('be.visible');
    cy.contains('Actions').should('be.visible');
  });

  it('displays correct status chips with icons', () => {
    cy.get('.status-chip').first().within(() => {
      // Verify chip has status text and icon
      cy.get('.v-icon').should('exist');
      cy.contains(/waiting|working|blocked|complete|failed/i).should('exist');
    });
  });

  it('shows message badges with counts', () => {
    // Find job with unread messages
    cy.get('.v-chip.error').first().within(() => {
      cy.get('.v-icon').should('have.text', 'mdi-message-alert');
      // Verify count is numeric
      cy.get('.v-chip__content').invoke('text').should('match', /\d+/);
    });
  });

  it('opens message modal when clicking message badge', () => {
    cy.get('[data-action="viewMessages"]').first().click();

    // Verify modal opens
    cy.get('.message-transcript-modal').should('be.visible');
    cy.contains('Message History').should('be.visible');

    // Verify message list
    cy.get('.message-item').should('exist');
  });

  it('sends message from modal composer', () => {
    // Open message modal
    cy.get('[data-action="viewMessages"]').first().click();

    // Type message
    cy.get('.message-composer textarea').type('Test message from E2E');

    // Send message
    cy.get('.message-composer .v-btn[icon]').click();

    // Verify success snackbar
    cy.get('.v-snackbar.success').should('be.visible');
    cy.contains('Message sent successfully').should('be.visible');

    // Verify input cleared
    cy.get('.message-composer textarea').should('have.value', '');
  });

  it('copies prompt to clipboard on copy action', () => {
    cy.get('[data-action="copyPrompt"]').first().click();

    // Verify success snackbar
    cy.get('.v-snackbar.success').should('be.visible');
    cy.contains('Prompt copied to clipboard').should('be.visible');

    // Verify clipboard contents
    cy.window().then((win) => {
      win.navigator.clipboard.readText().then((text) => {
        expect(text).to.contain('You are');  // Prompt starts with "You are..."
      });
    });
  });

  it('shows confirmation dialog for cancel action', () => {
    // Find working job
    cy.contains('.status-chip', 'working')
      .closest('tr')
      .within(() => {
        cy.get('[data-action="cancel"]').click();
      });

    // Verify confirmation dialog
    cy.get('.v-dialog').should('be.visible');
    cy.contains('Cancel Agent Job?').should('be.visible');
    cy.contains('This action cannot be undone').should('be.visible');
  });

  it('cancels job when confirmation accepted', () => {
    // Trigger cancel
    cy.contains('.status-chip', 'working')
      .closest('tr')
      .within(() => {
        cy.get('[data-action="cancel"]').click();
      });

    // Accept confirmation
    cy.contains('button', 'Cancel Job').click();

    // Verify job status updated
    cy.contains('.status-chip', 'cancelled').should('be.visible');
  });

  it('toggles Claude Code CLI mode', () => {
    // Find toggle
    cy.get('[data-toggle="claudeCodeCli"]').click();

    // Verify only orchestrator has launch button
    cy.get('tr').each(($row) => {
      cy.wrap($row).within(() => {
        cy.get('[data-agent-type]').invoke('text').then((agentType) => {
          if (agentType === 'orchestrator') {
            cy.get('[data-action="launch"]').should('exist');
          } else {
            cy.get('[data-action="launch"]').should('not.exist');
          }
        });
      });
    });
  });

  it('filters table by status', () => {
    // Open filter menu
    cy.get('[data-filter="status"]').click();

    // Select "working" status
    cy.contains('working').click();

    // Apply filter
    cy.contains('button', 'Apply').click();

    // Verify all rows show "working" status
    cy.get('.status-chip').each(($chip) => {
      cy.wrap($chip).should('contain.text', 'working');
    });
  });

  it('sorts table by last activity', () => {
    // Click last activity header
    cy.contains('th', 'Last Activity').click();

    // Verify descending order
    cy.get('[data-last-progress]')
      .then(($elements) => {
        const dates = [...$elements].map(el => new Date(el.dataset.lastProgress));
        const sorted = [...dates].sort((a, b) => b - a);
        expect(dates).to.deep.equal(sorted);
      });
  });

  it('updates table in real-time via WebSocket', () => {
    // Get initial job count
    cy.get('.status-chip').its('length').then((initialCount) => {
      // Trigger backend job creation (via API or test harness)
      cy.request('POST', '/api/agent-jobs', {
        project_id: 'test-project',
        agent_type: 'analyzer'
      });

      // Wait for WebSocket update
      cy.wait(500);

      // Verify new row appeared
      cy.get('.status-chip').should('have.length', initialCount + 1);
    });
  });

  it('shows staleness warning for inactive jobs', () => {
    // Wait for staleness check (runs every 30s)
    cy.wait(31000);

    // Verify warning snackbar
    cy.get('.v-snackbar.warning').should('be.visible');
    cy.contains('has been inactive for over 10 minutes').should('be.visible');
  });
});


/**
 * Cross-browser compatibility tests
 */
describe('Cross-Browser Compatibility', () => {
  ['chrome', 'firefox', 'edge'].forEach((browser) => {
    it(`works correctly in ${browser}`, () => {
      cy.visit('/dashboard', { browser });

      // Verify table loads
      cy.get('.status-board-table').should('be.visible');

      // Verify actions work
      cy.get('[data-action="copyPrompt"]').first().click();
      cy.get('.v-snackbar.success').should('be.visible');
    });
  });
});
```

### 3. Component Integration Tests

**File**: `frontend/tests/integration/status-board-components.spec.js` (NEW)

Test component interactions:

```javascript
import { mount } from '@vue/test-utils';
import { createStore } from 'vuex';
import StatusBoardTable from '@/components/StatusBoard/StatusBoardTable.vue';

describe('Status Board Component Integration', () => {
  let store;
  let wrapper;

  beforeEach(() => {
    store = createStore({
      state: {
        currentProject: { project_id: 'test-123' }
      }
    });

    wrapper = mount(StatusBoardTable, {
      global: {
        plugins: [store]
      }
    });
  });

  it('loads table data on mount', async () => {
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.loading).toBe(false);
    expect(wrapper.vm.tableRows.length).toBeGreaterThan(0);
  });

  it('updates table when WebSocket event received', async () => {
    const initialCount = wrapper.vm.tableRows[0].unread_count;

    // Simulate WebSocket message
    wrapper.vm.handleWebSocketMessage({
      event: 'message:new',
      job_id: wrapper.vm.tableRows[0].job_id,
      status: 'pending'
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.vm.tableRows[0].unread_count).toBe(initialCount + 1);
  });

  it('opens message modal on badge click', async () => {
    await wrapper.find('.job-message-badge').trigger('click');

    expect(wrapper.vm.showMessageModal).toBe(true);
    expect(wrapper.vm.selectedJob).toBeTruthy();
  });
});
```

---

## Cleanup Checklist

**Old Code Removed**:
- [ ] No commented-out blocks remaining
- [ ] No orphaned imports (check with linter)
- [ ] No unused functions or variables
- [ ] No `// TODO` or `// FIXME` comments without tickets

**Integration Verified**:
- [ ] Existing components reused where possible
- [ ] No duplicate functionality created
- [ ] Shared logic extracted to composables (if applicable)
- [ ] No zombie code (per QUICK_LAUNCH.txt line 28)

**Testing**:
- [ ] All imports resolved correctly
- [ ] No linting errors (eslint/ruff)
- [ ] Coverage maintained (>80%)

---

## Testing Criteria

### Coverage Targets

- **Backend**: >80% line coverage for new endpoints and services
- **Frontend**: >80% branch coverage for new components
- **E2E**: 100% coverage of user workflows (happy paths)

### Test Execution

```bash
# Backend tests
pytest tests/integration/test_status_board_table.py -v --cov=api/endpoints/agent_jobs --cov-report=html

# Frontend unit tests
cd frontend && npm run test:unit -- --coverage

# Frontend E2E tests
cd frontend && npm run test:e2e

# All tests
npm run test:all
```

---

## Success Criteria

- ✅ Table loads with correct data structure
- ✅ Message counts aggregate correctly (unread/acknowledged)
- ✅ Filtering works (status, health, unread messages)
- ✅ Sorting works (last_progress, created_at, status)
- ✅ Pagination returns correct subsets
- ✅ WebSocket events update table in real-time
- ✅ Multi-tenant isolation verified (no cross-tenant data)
- ✅ Message modal opens/closes correctly
- ✅ Message composer sends messages successfully
- ✅ Action icons trigger correct behaviors
- ✅ Confirmation dialogs prevent accidental actions
- ✅ Staleness warnings appear for inactive jobs
- ✅ Claude Code CLI toggle affects launch button visibility
- ✅ Cross-browser compatibility (Chrome, Firefox, Edge)
- ✅ >80% test coverage achieved
- ✅ All tests pass in CI/CD pipeline

---

## Next Steps

→ **Handover 0237**: Documentation
- Component usage documentation
- User guide updates with new screenshots
- API reference for new endpoints
- Developer guide for extending status board

---

## References

- **Vision Document**: All slides (1-27) showing complete workflow
- **Backend Endpoint**: Handover 0226 (table view API)
- **Frontend Components**: Handovers 0232-0235 (all components)
- **WebSocket Events**: `api/websocket.py`
- **Test Patterns**: `tests/api/` and `frontend/tests/`
- **Coverage Tools**: pytest-cov, vitest --coverage
