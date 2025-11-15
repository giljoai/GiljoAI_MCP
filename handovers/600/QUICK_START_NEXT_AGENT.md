# Quick Start Guide for Next Agent
**Read this FIRST** - Then read full `SESSION_HANDOVER_2025-11-15.md`

---

## 🎯 Your Mission (3.5 hours)
Fix **4 P0 blockers** to reach **82%+ test pass rate**

**Current**: 286/463 tests (61.8%)
**Target**: 380/463 tests (82.1%) ✅

---

## ⚡ Quick Context

You're picking up after:
- ✅ Phase 2 complete (10 API test files created)
- ✅ Cleanup complete (11 zombie files removed)
- ✅ Infrastructure fixed (cookies, slash commands)
- ✅ 2 P0 blockers already fixed

**Service layer**: 108/108 (100%) - SOLID foundation
**API layer**: 178/355 (50.1%) - 4 blockers remaining

---

## 🔧 The 4 P0 Blockers (In Order)

### 1. TaskRequest.status Field (1 hour) 🔥 HIGHEST IMPACT
**+34 tests (+9.6%)**

**File**: `tests/api/test_tasks_api.py`
**Problem**: Missing `"status"` field in task creation dicts
**Fix**: Add `"status": "pending"` to all task_data dicts

```python
# Find all instances like this:
task_data = {
    "title": "Test",
    "description": "Test desc",
    "product_id": str(product_id)
}

# Change to:
task_data = {
    "title": "Test",
    "description": "Test desc",
    "product_id": str(product_id),
    "status": "pending"  # ADD THIS
}
```

**Test**: `pytest tests/api/test_tasks_api.py -v`
**Expected**: 9/43 → 43/43 tests

---

### 2. complete_project() Signature (30 min)
**+13 tests (+3.7%)**

**File**: `src/giljo_mcp/services/project_service.py`
**Problem**: Method doesn't accept `db_session` parameter but endpoint passes it
**Fix**: Add optional `db_session` parameter

```python
# Current (line ~450):
async def complete_project(self, project_id: str, summary: str = None) -> dict:

# Change to:
async def complete_project(
    self,
    project_id: str,
    summary: str = None,
    db_session: AsyncSession = None  # ADD THIS
) -> dict:
    if db_session:
        session = db_session
    else:
        async with self.db_manager.get_session_async() as session:
            # ... existing logic
```

**Test**: `pytest tests/api/test_projects_api.py -k complete -v`
**Expected**: 30/54 → 43/54 tests

---

### 3. mission Field Constraint (45 min)
**+17 tests (+4.8%)**

**File**: `tests/api/test_agent_jobs_api.py`
**Problem**: MCPAgentJob created without required `mission` field
**Fix**: Add `mission="Test mission"` to all MCPAgentJob() creations

```python
# Find all instances like this:
agent_job = MCPAgentJob(
    agent_type="implementer",
    status="pending",
    project_id=project.id,
    tenant_key=tenant_key
)

# Change to:
agent_job = MCPAgentJob(
    agent_type="implementer",
    status="pending",
    project_id=project.id,
    tenant_key=tenant_key,
    mission="Test mission for agent"  # ADD THIS
)
```

**Test**: `pytest tests/api/test_agent_jobs_api.py -v`
**Expected**: 7/33 → 24/33 tests

---

### 4. admin_user Fixture (15 min)
**+10 tests (+2.8%)**

**File**: `tests/api/conftest.py`
**Problem**: admin_user fixture doesn't exist
**Fix**: Add admin_user and admin_token fixtures

```python
@pytest_asyncio.fixture
async def admin_user(db_manager):
    """Admin user for testing admin-only endpoints"""
    from passlib.hash import bcrypt
    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager
    from uuid import uuid4

    unique_id = uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key(f"admin_{unique_id}")

    async with db_manager.get_session_async() as session:
        user = User(
            username=f"admin_{unique_id}",
            password_hash=bcrypt.hash("admin_password"),
            email=f"admin_{unique_id}@test.com",
            tenant_key=tenant_key,
            role="admin",  # ADMIN ROLE
            is_active=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

@pytest_asyncio.fixture
async def admin_token(admin_user):
    """Admin JWT token"""
    from src.giljo_mcp.auth.jwt_manager import JWTManager
    jwt_manager = JWTManager()
    return jwt_manager.create_access_token(data={"sub": admin_user.username})
```

**Test**: `pytest tests/api/test_settings_api.py -v`
**Expected**: 21/31 → 31/31 tests

---

## 📋 Execution Checklist

### Before You Start
- [ ] Read full `SESSION_HANDOVER_2025-11-15.md`
- [ ] Verify service tests pass: `pytest tests/unit/ -v` (should be 108/108)
- [ ] Git status clean: `git status`
- [ ] Database accessible: `PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT 1"`

### For Each Fix
- [ ] Make the code change
- [ ] Run specific test: `pytest tests/api/test_X_api.py -v`
- [ ] Verify improvement
- [ ] Commit with format below
- [ ] Move to next fix

### Commit Message Format
```
fix: Brief description (P0 Blocker #X)

Detailed description of what was changed and why.

Impact: +X tests, +Y% overall pass rate
Expected: A/B tests → C/B tests

Ref: handovers/600/SESSION_HANDOVER_2025-11-15.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### After All Fixes
- [ ] Run full suite: `pytest tests/api/ -v --tb=no -q`
- [ ] Verify 380+ passing (82%+)
- [ ] Service tests still 108/108
- [ ] Create completion report (template in handover doc)
- [ ] Git log shows 4 separate commits

---

## 🚨 Common Mistakes to Avoid

❌ Don't batch all fixes into one commit
❌ Don't skip testing after each fix
❌ Don't modify frontend code
❌ Don't create new test files
❌ Don't forget `await session.refresh(project)` after commit
❌ Don't forget cookie clearing in fixtures

---

## ✅ Expected Results

### After Fix #1 (TaskRequest.status)
```
tests/api/test_tasks_api.py: 43/43 PASSED (was 9/43)
Overall: 320/463 (69.1%)
```

### After Fix #2 (complete_project)
```
tests/api/test_projects_api.py: 43/54 PASSED (was 30/54)
Overall: 333/463 (71.9%)
```

### After Fix #3 (mission field)
```
tests/api/test_agent_jobs_api.py: 24/33 PASSED (was 7/33)
Overall: 350/463 (75.6%)
```

### After Fix #4 (admin_user)
```
tests/api/test_settings_api.py: 31/31 PASSED (was 21/31)
Overall: 360/463 (77.8%)
```

### After Auth Cleanup
```
Overall: 380/463 (82.1%) ✅ TARGET ACHIEVED
```

---

## 🆘 If You Get Stuck

### Troubleshooting Commands
```bash
# Clear cache and retry
rm -rf .pytest_cache __pycache__ tests/__pycache__
pytest tests/api/test_tasks_api.py -v --cache-clear

# Check database schema
export PGPASSWORD=$DB_PASSWORD
/f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d mcp_agent_jobs"

# Run single test with full trace
pytest tests/api/test_tasks_api.py::TestTaskCRUD::test_create_task -vv --tb=short

# Check fixture availability
pytest tests/api/ --fixtures | grep admin_user
```

### Read These Sections in Full Handover
- "CRITICAL: 4 Remaining P0 Blockers" (detailed fix instructions)
- "Testing Patterns & Best Practices" (code examples)
- "Troubleshooting Guide" (if tests still fail)

---

## 📊 Success Metrics

**You succeeded when**:
- ✅ All 4 fixes committed (4 separate commits)
- ✅ Overall pass rate ≥ 82%
- ✅ Service tests still 108/108 (no regressions)
- ✅ Completion report created
- ✅ All commits follow message format

---

## 🎯 Time Estimate

- **Fix #1**: 1 hour (high impact)
- **Fix #2**: 30 minutes (medium impact)
- **Fix #3**: 45 minutes (medium impact)
- **Fix #4**: 15 minutes (quick win)
- **Total**: 2.5 hours of fixes + 1 hour testing/documentation = **3.5 hours**

---

## 📁 Key Files

**To Modify**:
- `tests/api/test_tasks_api.py` (Fix #1)
- `src/giljo_mcp/services/project_service.py` (Fix #2)
- `tests/api/test_agent_jobs_api.py` (Fix #3)
- `tests/api/conftest.py` (Fix #4)

**To Reference**:
- `handovers/600/SESSION_HANDOVER_2025-11-15.md` (FULL CONTEXT)
- `handovers/600/FINAL_TEST_RESULTS.md` (Current test analysis)
- `handovers/600/P0_BLOCKER_IMPACT_SUMMARY.md` (Quick reference)

---

**Ready? Read the full handover doc, then execute the 4 fixes!**

**Good luck! 🚀**
