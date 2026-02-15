# Kickoff Prompt: 0730b Refactor Service Layer Methods

**Agent Role:** tdd-implementor
**Estimated Time:** 16-24 hours (3-4 days recommended)
**Prerequisites:** 0730a COMPLETE, read this entire prompt before starting

---

## Your Mission

You are a **tdd-implementor** agent executing **Handover 0730b: Refactor Service Layer Methods**.

Your goal is to refactor 122 service methods using Test-Driven Development (TDD) to replace dict wrappers with Pydantic models and exception-based error handling.

**This is Phase 2 of 4** in the 0730 Service Response Models series. You will implement the designs from 0730a.

**CRITICAL:** TDD approach is MANDATORY - update tests FIRST, then implementation.

---

## Critical Context

**Full Handover Specification:**
Read `F:\GiljoAI_MCP\handovers\0730b_REFACTOR_SERVICES.md` completely before starting.

**Required Design Documents (from 0730a):**
- `docs/architecture/service_response_models.md` - Return type reference
- `docs/architecture/exception_mapping.md` - Exception reference
- `docs/architecture/api_exception_handling.md` - API pattern guide

**Project:** GiljoAI MCP v1.0 - Multi-tenant agent orchestration server
**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL
**Branch:** feature/0700-code-cleanup-series

---

## Scope: 122 Methods in 3 Tiers

**Tier 1 (57%)** - 69 instances, 8-12 hours:
- OrgService: 33 instances (START HERE - 3-4 hours)
- UserService: 19 instances (2-3 hours)
- ProductService: 17 instances (2-3 hours)

**Tier 2 (26%)** - 31 instances, 4-6 hours:
- TaskService: 14 instances
- ProjectService: 9 instances
- MessageService: 8 instances

**Tier 3 (18%)** - 22 instances, 4-6 hours:
- OrchestrationService: 6 instances
- ContextService: 4 instances
- ConsolidationService: 4 instances
- AgentJobManager: 4 instances
- VisionSummarizer: 4 instances
- TemplateService: 4 instances

---

## TDD Workflow (MANDATORY for EVERY Service)

### Step 1: Update Tests FIRST (30-40% of time)

```python
# BEFORE (test expects dict wrapper):
def test_get_org_not_found(org_service):
    result = await org_service.get_org("nonexistent")
    assert result["success"] is False
    assert "not found" in result["error"]

# AFTER (test expects exception):
import pytest
from src.giljo_mcp.exceptions import OrgNotFoundError

def test_get_org_not_found(org_service):
    with pytest.raises(OrgNotFoundError) as exc_info:
        await org_service.get_org("nonexistent")
    assert "nonexistent" in str(exc_info.value)
```

### Step 2: Run Tests to Confirm Failures

```bash
pytest tests/services/test_org_service.py -v
# Expected: FAILURES - tests expect exceptions, code returns dicts
```

### Step 3: Update Service Implementation (60-70% of time)

```python
# BEFORE:
async def get_org(self, org_id: str):
    org = await self.org_repo.get(org_id)
    if not org:
        return {"success": False, "error": "Organization not found"}
    return {"success": True, "data": org}

# AFTER:
from src.giljo_mcp.exceptions import OrgNotFoundError

async def get_org(self, org_id: str) -> Organization:
    """Get organization by ID.

    Args:
        org_id: Organization ID

    Returns:
        Organization model

    Raises:
        OrgNotFoundError: Organization not found
    """
    org = await self.org_repo.get(org_id)
    if not org:
        raise OrgNotFoundError(f"Organization {org_id} not found")
    return org
```

### Step 4: Run Tests to Confirm Fixes

```bash
pytest tests/services/test_org_service.py -v --cov=src/giljo_mcp/services/org_service.py
# Expected: ALL PASSING with >80% coverage maintained
```

### Step 5: Commit Per Service

```bash
git add tests/services/test_org_service.py src/giljo_mcp/services/org_service.py
git commit -m "refactor(0730b): OrgService dict wrappers to exceptions (33 methods)

- Update 33 methods to return models and raise exceptions
- Update all tests to expect exceptions instead of dict wrappers
- Coverage maintained at >80%

```

---

## Day-by-Day Execution Plan

### Day 1: Tier 1 - OrgService (3-4 hours)

**Morning:**
1. Read `docs/architecture/service_response_models.md` - OrgService section
2. Read `tests/services/test_org_service.py` completely
3. Update ALL test methods to expect exceptions (not dicts)
4. Add exception imports to test file
5. Run tests to confirm failures: `pytest tests/services/test_org_service.py -v`

**Afternoon:**
1. Read `src/giljo_mcp/services/org_service.py` using Serena MCP:
   ```python
   mcp__serena__get_symbols_overview(relative_path="src/giljo_mcp/services/org_service.py")
   ```
2. Refactor all 33 methods following pattern from 0730a
3. Add type hints to all methods
4. Add exception imports to service file
5. Update docstrings with Raises sections
6. Run tests to confirm fixes: `pytest tests/services/test_org_service.py -v --cov=src/giljo_mcp/services/org_service.py`
7. Commit with descriptive message

### Day 2: Tier 1 - UserService + ProductService (4-6 hours)

**Morning - UserService (2-3 hours):**
1. Follow same TDD workflow
2. Update tests first, run to confirm failures
3. Refactor 19 methods
4. Run tests to confirm fixes
5. Commit

**Afternoon - ProductService (2-3 hours):**
1. Follow same TDD workflow
2. Update tests first, run to confirm failures
3. Refactor 17 methods
4. Run tests to confirm fixes
5. Commit
6. **Milestone:** Run full service test suite: `pytest tests/services/ -v`

### Day 3: Tier 2 - TaskService, ProjectService, MessageService (4-6 hours)

Process each service:
- TaskService (14 instances) - 1.5-2 hours
- ProjectService (9 instances) - 1-1.5 hours
- MessageService (8 instances) - 1-1.5 hours

Follow TDD workflow for each, commit after each service.

### Day 4: Tier 3 - Remaining 6 Services (4-6 hours)

Process each service (4-6 instances each):
- OrchestrationService - 1 hour
- ContextService - 45 min
- ConsolidationService - 45 min
- AgentJobManager - 45 min
- VisionSummarizer - 45 min
- TemplateService - 45 min

Can batch similar services if patterns identical. Commit after each or in logical groups.

---

## Critical Requirements

**TDD DISCIPLINE:**
- ✅ ALWAYS update tests first, then implementation
- ✅ ALWAYS run tests after test updates to confirm failures
- ✅ ALWAYS run tests after code updates to confirm fixes
- ✅ NEVER skip this cycle - it prevents regressions

**CODE QUALITY:**
- ✅ Add type hints to all method signatures (-> ReturnType)
- ✅ Update docstrings with Raises sections
- ✅ Use exceptions from src/giljo_mcp/exceptions.py
- ✅ Maintain >80% test coverage

**SERENA MCP USAGE:**
- ✅ Use symbolic navigation, not full file reads
- ✅ `mcp__serena__get_symbols_overview` for file overview
- ✅ `mcp__serena__find_symbol` for method bodies
- ✅ `mcp__serena__replace_symbol_body` for refactoring

**COMMITS:**
- ✅ One commit per service
- ✅ Descriptive commit messages with method counts
- ✅ Pre-commit hooks must pass (NO --no-verify)
- ✅ Co-authored by Claude Sonnet 4.5

**DO NOT:**
- ❌ Update API endpoints (that's 0730c, not this phase)
- ❌ Skip tests or commit untested code
- ❌ Bypass pre-commit hooks
- ❌ Batch all services into one commit

---

## Validation Commands

**After each service:**
```bash
# Run service-specific tests
pytest tests/services/test_{service}_*.py -v --cov=src/giljo_mcp/services/{service}.py

# Check coverage maintained
pytest tests/services/test_{service}_*.py --cov=src/giljo_mcp/services/{service}.py --cov-report=term-missing

# Verify pre-commit hooks pass
git add -A
pre-commit run --files tests/services/test_{service}_*.py src/giljo_mcp/services/{service}.py
```

**After each tier:**
```bash
# Run all service tests
pytest tests/services/ -v

# Check overall coverage
pytest tests/services/ --cov=src/giljo_mcp/services/ --cov-report=html
```

**After all complete:**
```bash
# Verify no dict wrappers remain
grep -r "\"success\":" src/giljo_mcp/services/ --include="*.py" | grep -v "#" | wc -l
# Expected: 0

# Run full test suite (check for regressions)
pytest tests/ -v
```

---

## Success Criteria

You are COMPLETE when:
1. ✅ All 122 service methods refactored
2. ✅ All service tests updated and passing
3. ✅ Coverage >80% maintained
4. ✅ No dict wrapper patterns remaining
5. ✅ All commits successful with pre-commit hooks passing
6. ✅ Validation commands all pass
7. ✅ Ready for 0730c (API updates)

---

## Common Patterns

### Pattern 1: GET operations (return model, raise NotFoundError)
```python
async def get_item(self, item_id: str) -> Item:
    """Get item by ID.

    Raises:
        ItemNotFoundError: Item not found
    """
    item = await self.repo.get(item_id)
    if not item:
        raise ItemNotFoundError(f"Item {item_id} not found")
    return item
```

### Pattern 2: CREATE operations (return model, raise AlreadyExistsError)
```python
async def create_item(self, data: ItemCreate) -> Item:
    """Create new item.

    Raises:
        ItemAlreadyExistsError: Item already exists
    """
    existing = await self.repo.get_by_name(data.name)
    if existing:
        raise ItemAlreadyExistsError(f"Item '{data.name}' already exists")

    item = Item(**data.dict())
    await self.db.add(item)
    await self.db.commit()
    await self.db.refresh(item)
    return item
```

### Pattern 3: LIST operations (return list)
```python
async def list_items(self) -> list[Item]:
    """List all items.

    Returns:
        List of items (empty list if none found)
    """
    items = await self.repo.list()
    return items
```

---

## Troubleshooting

**If tests fail after service update:**
- Check exception type matches what test expects
- Verify exception message includes expected details
- Ensure exception is raised, not returned
- Check imports are correct

**If coverage drops:**
- Identify uncovered lines with `--cov-report=term-missing`
- Add tests for edge cases
- Ensure all error paths tested

**If pre-commit hooks fail:**
- Fix lint issues: `ruff check src/ --fix`
- Fix formatting: `black src/`
- Never use `--no-verify`

**If confused on pattern:**
- Refer to `docs/architecture/service_response_models.md`
- Check OrgService as reference implementation
- Ask questions before proceeding

---

## Handoff Protocol

When complete, update tracking:

**Update `handovers/0700_series/comms_log.json`:**
```json
{
  "timestamp": "2026-02-07T[TIME]Z",
  "from": "0730b",
  "to": "orchestrator",
  "type": "phase_complete",
  "phase": "refactoring",
  "summary": {
    "methods_refactored": 122,
    "services_updated": 12,
    "tests_passing": "100%",
    "coverage": ">80%",
    "commits": 12
  },
  "key_outcomes": [
    "All services return Pydantic models or domain objects",
    "Exception-based error handling implemented throughout",
    "TDD workflow followed - zero regressions",
    "All tests passing with maintained coverage"
  ],
  "ready_for": ["0730c"]
}
```

**Mark ready:** Update `handovers/0700_series/orchestrator_state.json` to mark 0730b COMPLETE.

---

## Resources

**Critical Files:**
- `handovers/0730b_REFACTOR_SERVICES.md` - Full specification
- `docs/architecture/service_response_models.md` - Return type reference (from 0730a)
- `docs/architecture/exception_mapping.md` - Exception reference (from 0730a)
- `src/giljo_mcp/exceptions.py` - Exception hierarchy
- `src/giljo_mcp/services/*.py` - All service files to refactor
- `tests/services/` - All test files to update

**Documentation:**
- `docs/SERVICES.md` - Service layer patterns
- `docs/TESTING.md` - Testing patterns
- `CLAUDE.md` - Project standards and pre-commit policy

---

## Important Notes

1. **TDD is Non-Negotiable** - Tests first, always
2. **Start with OrgService** - Establishes pattern
3. **Commit Frequently** - One per service
4. **Run Tests Often** - After each method
5. **Check Coverage** - Maintain >80%
6. **Don't Touch Endpoints** - That's 0730c
7. **Use Serena MCP** - Symbolic navigation only
8. **Quality Over Speed** - 3-4 days is fine
9. **Ask Questions** - If unclear, check 0730a docs
10. **Celebrate Progress** - This is significant work

---

**Ready to start?**

1. Read full handover specification
2. Read all 3 design documents from 0730a
3. Begin Day 1: OrgService refactoring

Good luck! Your TDD discipline will ensure zero regressions.
