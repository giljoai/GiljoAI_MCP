# Handover 0414: agent_type to agent_display_name Migration

**Status**: ACTIVE
**Created**: 2026-01-11
**Work In**: `master` branch (commit `75b9a4a9`)
**Methodology**: TDD with Subagents

---

## Overview

Rename `agent_type` to `agent_display_name` across the entire application for semantic clarity.

**Current State**: Clean baseline where everything uses `agent_type`
**Target State**: All references use `agent_display_name`

**Field Definitions (Canonical)**:

| Field | Table | Purpose | Example | Set By |
|-------|-------|---------|---------|--------|
| `agent_id` | AgentExecution | Unique instance UUID | `"abc-123-def"` | System |
| `agent_display_name` | AgentExecution | Human-readable UI label | `"Backend API Developer"` | Orchestrator |
| `agent_name` | AgentExecution | Template filename | `"tdd-implementor"` | Orchestrator |
| `job_id` | AgentJob | Work order UUID | `"xyz-789-uvw"` | System |

---

## Phase Structure

| Phase | Description | Deliverable | Subagent |
|-------|-------------|-------------|----------|
| **0414a** | Complete inventory of `agent_type` | Categorized inventory document | `deep-researcher` |
| **0414b** | Write tests FIRST (TDD Red) | Failing test suite | `tdd-implementor` |
| **0414c** | Clean zombie/deprecated code | Leaner codebase | `backend-tester` |
| **0414d** | Test after cleanup | All existing tests pass | `backend-tester` + `frontend-tester` |
| **0414e** | Execute name changes | Full migration | `tdd-implementor` |
| **0414f** | Full application testing | E2E validation | `frontend-tester` + Chrome extension |

---

## Phase 0414a: Complete Inventory (REQUIRED FIRST)

**Goal**: Create exhaustive inventory of ALL `agent_type` occurrences BEFORE making any changes.

**Subagent**: `deep-researcher`

### Inventory Categories

Search for `agent_type` in:

1. **DATABASE** (Priority 1)
   - `src/giljo_mcp/models/` - SQLAlchemy columns
   - `migrations/` - Alembic migration files
   - Actual database column names

2. **API_SCHEMA** (Priority 1)
   - `api/endpoints/*/models.py` - Pydantic response/request models
   - `api/events/schemas.py` - WebSocket event schemas
   - `src/giljo_mcp/models/schemas.py` - Shared schemas

3. **SERVICE_LAYER** (Priority 1)
   - `src/giljo_mcp/services/` - Service constructors and methods
   - `src/giljo_mcp/repositories/` - Repository methods

4. **MCP_TOOLS** (Priority 1)
   - `src/giljo_mcp/tools/` - Tool parameters and responses

5. **WEBSOCKET_EVENTS** (Priority 2)
   - `api/websocket*.py` - Event payloads
   - `api/events/` - Event handlers

6. **FRONTEND** (Priority 2)
   - `frontend/src/components/` - Vue component props/data
   - `frontend/src/composables/` - Composable state
   - `frontend/src/stores/` - Vuex/Pinia stores
   - `frontend/src/services/` - API service calls

7. **FUNCTION_PARAMS** (Priority 2)
   - Function/method parameters named `agent_type`
   - Constructor arguments

8. **DICT_KEYS** (Priority 3)
   - Dictionary/object keys in Python
   - JSON payloads

9. **TEST_FIXTURES** (Priority 3)
   - `tests/` - Test data and assertions
   - `tests/conftest.py` - Shared fixtures

10. **DOCSTRINGS/COMMENTS** (Priority 4)
    - Documentation references
    - Code comments

### Inventory Output Format

```markdown
## Category: API_SCHEMA

| File | Line | Type | Context | Migration Action |
|------|------|------|---------|------------------|
| api/endpoints/agent_jobs/models.py | 45 | Field | `agent_type: str` | RENAME to agent_display_name |
| api/events/schemas.py | 112 | Field | `agent_type: str` | RENAME to agent_display_name |

## Category: ZOMBIE_CODE (Candidates for 0414c removal)

| File | Line | Type | Reason | Action |
|------|------|------|--------|--------|
| api/websocket.py | 234 | Function | `broadcast_agent_spawn()` unused | DELETE |
| src/giljo_mcp/repositories/agent_job_repository.py | 89 | Method | Uses legacy Job model | DELETE |
```

### Commands for Inventory

```bash
# Python files
grep -rn "agent_type" src/giljo_mcp/ api/ --include="*.py" | grep -v "__pycache__" > inventory_python.txt

# Frontend files
grep -rn "agent_type" frontend/src/ --include="*.vue" --include="*.js" --include="*.ts" > inventory_frontend.txt

# Test files
grep -rn "agent_type" tests/ --include="*.py" | grep -v "__pycache__" > inventory_tests.txt

# Database check
PGPASSWORD=$DB_PASSWORD "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -d giljo_mcp -c "\d agent_executions"

# Count totals
wc -l inventory_*.txt
```

### Deliverable

Create: `handovers/0414a_inventory_agent_type.md`

With:
- Complete categorized inventory (all 10 categories)
- Zombie code candidates identified
- Migration action for each occurrence
- Estimated scope (file count, line count per category)

---

## Phase 0414b: Write Tests FIRST (TDD Red)

**Goal**: Write failing tests that define expected behavior BEFORE any implementation.

**Subagent**: `tdd-implementor`

### TDD Discipline (from QUICK_LAUNCH.txt)

```
1. Write the test FIRST (it should fail initially)
2. Implement minimal code to make test pass
3. Refactor if needed
4. Test should focus on BEHAVIOR (what the code does),
   not IMPLEMENTATION (how it does it)
5. Use descriptive test names like 'test_agent_display_name_appears_in_api_response'
6. Avoid testing internal implementation details
```

### Tests to Write

#### Backend Service Tests
```python
# tests/services/test_agent_display_name_migration.py

@pytest.mark.asyncio
async def test_agent_execution_has_display_name_field(db_session):
    """AgentExecution model should have agent_display_name, not agent_type"""
    from src.giljo_mcp.models.agent_identity import AgentExecution

    # This should work after migration
    execution = AgentExecution(
        agent_id="test-123",
        job_id="job-456",
        tenant_key="tenant_abc",
        agent_display_name="Backend API Developer",  # New field name
        agent_name="tdd-implementor",
        status="waiting"
    )
    assert execution.agent_display_name == "Backend API Developer"

@pytest.mark.asyncio
async def test_spawn_agent_uses_display_name_parameter():
    """spawn_agent_job should accept agent_display_name parameter"""
    # Test the function signature accepts agent_display_name
    ...

@pytest.mark.asyncio
async def test_api_response_returns_agent_display_name():
    """API endpoints should return agent_display_name in JSON response"""
    ...
```

#### API Schema Tests
```python
# tests/api/test_agent_display_name_schemas.py

def test_job_response_has_agent_display_name_field():
    """JobResponse schema should have agent_display_name field"""
    from api.endpoints.agent_jobs.models import JobResponse

    response = JobResponse(
        job_id="job-123",
        agent_display_name="Backend API Developer",
        ...
    )
    assert response.agent_display_name == "Backend API Developer"
```

#### Frontend Tests
```javascript
// frontend/tests/unit/components/StatusBoard/AgentCard.spec.js

describe('AgentCard', () => {
  it('displays agent_display_name in card header', () => {
    const wrapper = mount(AgentCard, {
      props: {
        agent: {
          agent_display_name: 'Backend API Developer',
          agent_name: 'tdd-implementor'
        }
      }
    })
    expect(wrapper.text()).toContain('Backend API Developer')
  })
})
```

### Run Tests (Should ALL FAIL - RED)

```bash
# Backend tests
pytest tests/services/test_agent_display_name_migration.py -v
# Expected: FAILED (RED)

pytest tests/api/test_agent_display_name_schemas.py -v
# Expected: FAILED (RED)

# Frontend tests
cd frontend && npm run test:unit -- --grep "agent_display_name"
# Expected: FAILED (RED)
```

### Deliverable

- `tests/services/test_agent_display_name_migration.py`
- `tests/api/test_agent_display_name_schemas.py`
- `frontend/tests/unit/components/StatusBoard/AgentDisplayName.spec.js`
- All tests RED (failing)

---

## Phase 0414c: Clean Zombie Code

**Goal**: Remove deprecated/dead code identified in 0414a inventory BEFORE renaming.

**Subagent**: `backend-tester`

### Zombie Code Targets (from previous analysis)

Based on the 0415 cleanup plan that was lost in rollback:

1. **Dead WebSocket Functions** (~82 lines)
   - `api/websocket.py`: `broadcast_agent_spawn()`, `broadcast_agent_complete()`
   - `api/websocket_service.py`: `notify_sub_agent_spawned()`, `notify_sub_agent_completed()`

2. **Deprecated MCP Tool** (~384 lines)
   - `src/giljo_mcp/tools/orchestration.py`: stdio `get_orchestrator_instructions` (if marked deprecated)

3. **Broken API Endpoints** (~480 lines)
   - `api/endpoints/agent_management.py` (if uses wrong Job model)

4. **Broken Repository Methods** (~250 lines)
   - `src/giljo_mcp/repositories/agent_job_repository.py`: Methods using legacy Job model

### Verification Before Removal

```bash
# Verify functions are truly unused
grep -rn "broadcast_agent_spawn\|broadcast_agent_complete" src/ api/ --include="*.py"
grep -rn "notify_sub_agent_spawned\|notify_sub_agent_completed" src/ api/ --include="*.py"

# If no callers found, safe to remove
```

### Deliverable

- Commits removing each category of zombie code
- Each commit tested independently
- No `agent_type` renames in this phase (cleanup only)

---

## Phase 0414d: Test After Cleanup

**Goal**: Ensure all existing tests still pass after zombie code removal.

**Subagents**: `backend-tester` + `frontend-tester`

### Test Commands

```bash
# Full backend test suite
pytest tests/ -v --tb=short

# Coverage report
pytest tests/ --cov=src/giljo_mcp --cov-report=html

# Frontend tests
cd frontend && npm run test:unit

# Integration tests
pytest tests/integration/ -v
```

### Verification

- All existing tests GREEN
- No regressions from cleanup
- Coverage maintained or improved

### Deliverable

- Test results showing 100% pass rate
- Coverage report saved

---

## Phase 0414e: Execute Name Changes

**Goal**: Rename `agent_type` to `agent_display_name` everywhere identified in 0414a inventory.

**Subagent**: `tdd-implementor`

### Execution Order

1. **Database Migration**
   ```python
   # migrations/versions/0414e_rename_agent_type.py
   def upgrade():
       op.alter_column(
           'agent_executions',
           'agent_type',
           new_column_name='agent_display_name',
           existing_type=sa.String(100),
           existing_nullable=False
       )
   ```

2. **SQLAlchemy Model**
   ```python
   # src/giljo_mcp/models/agent_identity.py
   agent_display_name = Column(
       String(100),
       nullable=False,
       comment="UI display label assigned by orchestrator (e.g., 'Backend API Developer')",
   )
   ```

3. **Service Layer** (in order of dependency)
   - Repositories
   - Services
   - Job managers

4. **API Layer**
   - Pydantic schemas
   - Endpoint handlers
   - WebSocket events

5. **MCP Tools**
   - Tool parameters
   - Tool responses

6. **Frontend**
   - Composables
   - Components
   - Stores

7. **Test Fixtures**
   - Update all test data to use `agent_display_name`

### Run TDD Tests (Should Now PASS - GREEN)

```bash
# The tests written in 0414b should now pass
pytest tests/services/test_agent_display_name_migration.py -v
# Expected: PASSED (GREEN)

pytest tests/api/test_agent_display_name_schemas.py -v
# Expected: PASSED (GREEN)

cd frontend && npm run test:unit -- --grep "agent_display_name"
# Expected: PASSED (GREEN)
```

### Deliverable

- All inventory items from 0414a migrated
- All 0414b tests GREEN
- All existing tests GREEN
- Commit per logical unit (model, services, API, frontend)

---

## Phase 0414f: Full Application Testing

**Goal**: Validate entire application works end-to-end, including Chrome extension UI testing.

**Subagents**: `frontend-tester` + Chrome extension

### Manual Testing with Chrome Extension

**REQUIRED**: Use Chrome extension to visually verify:

1. **Agent Cards Display**
   - Navigate to project page
   - Verify agent cards show correct `agent_display_name`
   - No "??" or undefined values

2. **Status Board Table**
   - Open JobsTab
   - Verify table column shows agent_display_name
   - Sort by agent type works

3. **WebSocket Events**
   - Spawn a new agent
   - Verify real-time updates show correct name
   - Check browser console for event payloads

4. **Orchestrator Launch**
   - Launch new orchestrator
   - Verify orchestrator card shows "orchestrator" as display name

### Automated E2E Tests

```bash
# Full test suite
pytest tests/ -v

# Integration tests specifically
pytest tests/integration/ -v

# Frontend build test
cd frontend && npm run build
```

### Database Verification

```bash
PGPASSWORD=$DB_PASSWORD "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -d giljo_mcp -c "\d agent_executions" | grep -E "agent_display_name|agent_type"
# Should show: agent_display_name ONLY (no agent_type)

PGPASSWORD=$DB_PASSWORD "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -d giljo_mcp -c "SELECT agent_display_name FROM agent_executions LIMIT 5;"
# Should return valid values
```

### Final Verification Checklist

- [ ] All backend tests pass
- [ ] All frontend tests pass
- [ ] All integration tests pass
- [ ] Chrome extension shows correct agent names
- [ ] WebSocket events contain `agent_display_name`
- [ ] Database column is `agent_display_name`
- [ ] No `agent_type` references remain (except docs/history)

### Deliverable

- E2E test results
- Chrome extension screenshot verification
- Final commit with all changes
- CLAUDE.md updated with new field definitions

---

## What NOT to Change

1. **`AgentTemplate.role`** - This is the template category (implementer, tester, etc.)
2. **Message `role`** - Chat message sender (system, agent, user)
3. **User `role`** - Authorization (admin, user)
4. **`AgentJob.job_type`** - Work order type

---

## Rollback Instructions

If issues arise at any phase:

```bash
# Return to clean baseline
git reset --hard 75b9a4a9

# Restore database column if changed
PGPASSWORD=$DB_PASSWORD "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -d giljo_mcp -c "ALTER TABLE agent_executions RENAME COLUMN agent_display_name TO agent_type;"
```

---

## Principles (Non-Negotiable)

From QUICK_LAUNCH.txt:

1. **TDD Discipline**: RED -> GREEN -> REFACTOR
2. **Inventory First**: Know ALL occurrences before changing ANY
3. **Use Subagents**: Specialized agents for specialized tasks
4. **No Bandaids**: Production-grade from the start
5. **Chrome Extension Testing**: Visual verification required
6. **Clean Code**: Delete zombie code, don't comment it out

---

**START WITH PHASE 0414a. DO NOT SKIP PHASES.**
