# Handover 0619: Core Workflows E2E Testing

**Phase**: 3
**Tool**: CLI (Local)
**Agent Type**: integration-tester
**Duration**: 1 day
**Parallel Group**: Sequential
**Depends On**: 0609-0618

---

## Context

**Read First**: `handovers/600/AGENT_REFERENCE_GUIDE.md` for universal project context.

**Previous Handovers**: Phase 2 complete - all 84+ endpoints tested and validated. All service tests passing.

**This Handover**: Create automated E2E tests for 3 core workflows: Fresh Install & Onboarding, Product Lifecycle, and Project Lifecycle. Verify end-to-end functionality through user journeys.

---

## Specific Objectives

- **Objective 1**: Create automated E2E test for fresh install workflow (<5 min validation)
- **Objective 2**: Create automated E2E test for product lifecycle (create → activate → delete)
- **Objective 3**: Create automated E2E test for project lifecycle (create → tasks → complete)
- **Objective 4**: Add manual validation steps with screenshots/recordings (optional)
- **Objective 5**: Verify all 3 workflows pass end-to-end without errors
- **Objective 6**: Document test results and performance metrics

---

## Workflows to Test

### Workflow 1: Fresh Install & Onboarding
**User Journey**: New user installing GiljoAI MCP for first time

**Steps**:
1. Clean database (drop/recreate)
2. Run install.py (measure time)
3. Navigate to /welcome endpoint
4. Create first user (admin role)
5. Login with credentials
6. Verify dashboard loads correctly
7. Verify default tenant created

**Success Criteria**:
- Install completes in <5 minutes
- All 31 tables created
- First user created successfully
- Dashboard accessible after login

### Workflow 2: Product Lifecycle
**User Journey**: User creates product, uploads vision, activates, then deletes

**Steps**:
1. Create product via POST /api/v1/products
2. Upload vision document via POST /api/v1/products/{id}/vision/upload
3. Save config_data via PUT /api/v1/products/{id}/config
4. Activate product via POST /api/v1/products/{id}/activate
5. Verify single active product constraint (create second, activate, verify first deactivated)
6. Deactivate product via POST /api/v1/products/{id}/deactivate
7. Delete product via DELETE /api/v1/products/{id} (soft delete)
8. Verify deleted_at timestamp set

**Success Criteria**:
- All CRUD operations work
- Vision upload successful
- Config data persisted
- Single active product enforced
- Soft delete working (deleted_at timestamp)

### Workflow 3: Project Lifecycle
**User Journey**: User creates project under active product, manages tasks, completes project

**Steps**:
1. Create project under active product via POST /api/v1/projects
2. Assign tasks to project via POST /api/v1/tasks
3. Update project status to 'active' via POST /api/v1/projects/{id}/activate
4. Complete individual tasks via POST /api/v1/tasks/{id}/complete
5. Complete project via POST /api/v1/projects/{id}/complete
6. Verify cascade: project completion → tasks verified complete

**Success Criteria**:
- Project created successfully
- Tasks assigned to project
- Status transitions work (pending → active → completed)
- Project cannot complete until all tasks complete
- Cascade behavior verified

---

## Test Implementation

### File Structure
**Create**: `tests/e2e/test_core_workflows.py`

### Test Coverage (15+ tests)

**Fresh Install Tests** (5 tests):
```python
def test_fresh_install_workflow():
    """Test complete fresh install workflow"""
    # Clean database, run install, verify success

def test_fresh_install_time_under_5_min():
    """Performance validation"""
    # Measure install time, assert <5 min

def test_fresh_install_creates_all_tables():
    """Verify all 31 tables created"""
    # Query information_schema, count tables

def test_first_user_creation():
    """Test first user creation via /welcome"""
    # Navigate to /welcome, create user, verify admin role

def test_dashboard_loads_after_login():
    """Test login and dashboard access"""
    # Login, verify 200 response, check dashboard elements
```

**Product Lifecycle Tests** (5 tests):
```python
def test_product_creation_workflow():
    """Test full product creation"""
    # Create, verify response, check database

def test_product_vision_upload():
    """Test vision document upload"""
    # Upload markdown file, verify storage

def test_product_config_data_persistence():
    """Test config_data save/retrieve"""
    # Save JSONB config, retrieve, verify match

def test_product_single_active_constraint():
    """Test only one active product"""
    # Activate product1, activate product2, verify product1 inactive

def test_product_soft_delete():
    """Test product soft deletion"""
    # Delete, verify status='deleted', deleted_at set
```

**Project Lifecycle Tests** (5 tests):
```python
def test_project_creation_workflow():
    """Test project creation under product"""
    # Create product, activate, create project, verify

def test_project_task_cascade():
    """Test task assignment"""
    # Create project, add tasks, verify project-task relationship

def test_project_status_transitions():
    """Test project status changes"""
    # pending → active → paused → active → completed

def test_project_completion_requirements():
    """Test cannot complete until all tasks done"""
    # Try complete with incomplete tasks, verify error

def test_project_completion_cascade():
    """Test project completion updates tasks"""
    # Complete all tasks, complete project, verify cascade
```

---

## Success Criteria

- [ ] **All 3 Workflows**: Automated tests pass for fresh install, product lifecycle, project lifecycle
- [ ] **Fresh Install <5 min**: Performance validated and documented
- [ ] **Manual Validation**: Optional screenshots or screen recording captured
- [ ] **15+ Tests Passing**: All E2E tests pass (100% pass rate)
- [ ] **Test Results**: Documented in handover completion report
- [ ] **Commit**: Created with descriptive message

---

## Validation Steps

```bash
# Step 1: Run all E2E core workflow tests
cd /f/GiljoAI_MCP
pytest tests/e2e/test_core_workflows.py -v

# Step 2: Run with detailed output
pytest tests/e2e/test_core_workflows.py -v --tb=long

# Step 3: Verify test count
pytest tests/e2e/test_core_workflows.py --collect-only
# Expected: 15+ tests collected

# Step 4: Manual validation (optional)
# - Run fresh install on clean VM
# - Record screen for product lifecycle
# - Capture screenshots for project workflow
```

---

## Deliverables

### Code
- **Created**: `tests/e2e/test_core_workflows.py` (15+ E2E tests)

### Documentation
- **Created**: `handovers/600/0619_workflow_test_results.md` - Test run results:
  - Workflow 1: Fresh Install (pass/fail, time taken)
  - Workflow 2: Product Lifecycle (pass/fail, steps verified)
  - Workflow 3: Project Lifecycle (pass/fail, cascade verified)
  - Screenshots (optional)

### Git Commit
- **Message**: `test: Add E2E tests for core workflows (Handover 0619)`
- **Branch**: master (CLI execution)

---

## Dependencies

### Requires
- **Handovers 0609-0618**: All API endpoints tested and working
- **Database**: PostgreSQL running, ability to drop/recreate test DB
- **Backend**: FastAPI server can be started for E2E tests

### Blocks
- **Handover 0620**: Orchestration workflows E2E testing

---

## Notes for Agent

### CLI (Local) Execution
This is a CLI handover requiring local execution:

- You have database access - drop/recreate test databases
- You can run FastAPI server for E2E tests
- Selenium/Playwright available for browser automation (optional)
- Commit directly to master after validation

### E2E Testing Strategy

**Tools**:
- pytest for test framework
- FastAPI TestClient for API testing
- psycopg2 for direct database queries
- Selenium (optional) for browser automation

**Test Data Management**:
- Use fixtures to create clean test data
- Clean up after each test (or use transaction rollback)
- Isolate tests (no dependencies between tests)

---

**Document Control**:
- **Handover**: 0619
- **Created**: 2025-11-14
- **Status**: Ready for execution
