# Handover 0730b: Refactor Service Layer Methods

**Series:** 0700 Code Cleanup → 0730 Service Response Models (Phase 2 of 4)
**Priority:** P2 - MEDIUM
**Estimated Effort:** 16-24 hours
**Prerequisites:** 0730a COMPLETE (design documents)
**Status:** BLOCKED (waiting for 0730a)
**Depends On:** 0730a (response models and exception mapping)
**Blocks:** 0730c, 0730d

MISSION: Refactor 122 service methods using TDD to replace dict wrappers with Pydantic models and exception-based error handling

WHY THIS MATTERS:
- Core architectural improvement - eliminates dict wrapper anti-pattern
- Enables type safety and IDE autocompletion
- Simplifies error handling across entire application
- Required before API layer can be updated (0730c)

CRITICAL: Test-Driven Development (TDD) approach is MANDATORY - update tests FIRST, then implementation

---

## Scope: 122 Service Methods Across 3 Tiers

**TIER 1 (57%)** - 69 instances (8-12 hours):
- OrgService: 33 instances
- UserService: 19 instances
- ProductService: 17 instances

**TIER 2 (26%)** - 31 instances (4-6 hours):
- TaskService: 14 instances
- ProjectService: 9 instances
- MessageService: 8 instances

**TIER 3 (18%)** - 22 instances (4-6 hours):
- OrchestrationService: 6 instances
- ContextService: 4 instances
- ConsolidationService: 4 instances
- AgentJobManager: 4 instances
- VisionSummarizer: 4 instances
- TemplateService: 4 instances

---

## TDD Workflow (MANDATORY)

For each service:

### Step 1: Update Tests FIRST (30-40% of time)

```python
# BEFORE (test expects dict wrapper):
def test_get_org_not_found(self, org_service):
    result = await org_service.get_org("nonexistent")
    assert result["success"] is False
    assert "not found" in result["error"]

# AFTER (test expects exception):
def test_get_org_not_found(self, org_service):
    with pytest.raises(OrgNotFoundError) as exc_info:
        await org_service.get_org("nonexistent")
    assert "nonexistent" in str(exc_info.value)
```

**For each method:**
1. Read existing test in tests/services/test_{service}_*.py
2. Update assertions to expect:
   - Success case: Direct return value (model or list)
   - Error cases: Raised exceptions (pytest.raises)
3. Add new exception import: `from src.giljo_mcp.exceptions import NotFoundError, AlreadyExistsError, ...`

### Step 2: Run Tests to Confirm Failures

```bash
pytest tests/services/test_org_service.py -v
# Should show failures - tests now expect exceptions, code still returns dicts
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

**For each method:**
1. Add type hints (return type annotation)
2. Update docstring with Raises section
3. Replace dict returns with direct model returns
4. Replace error dict returns with raise statements
5. Use exception mapping from 0730a

### Step 4: Run Tests to Confirm Fixes

```bash
pytest tests/services/test_org_service.py -v --cov=src/giljo_mcp/services/org_service.py
# Should pass with maintained/improved coverage
```

### Step 5: Commit Per Service

```bash
git add tests/services/test_org_service.py src/giljo_mcp/services/org_service.py
git commit -m "refactor(0730b): OrgService dict wrappers to exceptions (33 methods)

- Update 33 methods to return models and raise exceptions
- Update all tests to expect exceptions instead of dict wrappers
- Coverage maintained at >80%

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Tier 1: High-Impact Services (8-12 hours)

### OrgService (33 instances) - Start Here

**File:** src/giljo_mcp/services/org_service.py
**Tests:** tests/services/test_org_service.py

**Methods to refactor (example subset):**
- get_org() - Return Organization, raise OrgNotFoundError
- list_orgs() - Return list[Organization]
- create_org() - Return Organization, raise OrgAlreadyExistsError
- update_org() - Return Organization, raise OrgNotFoundError
- delete_org() - Return bool or None, raise OrgNotFoundError
- get_org_by_name() - Return Organization | None (None is valid)
- update_org_settings() - Return Organization, raise OrgNotFoundError
- [... 26 more methods - see 0730a docs for complete list]

**Exceptions needed (from 0730a):**
- OrgNotFoundError (404)
- OrgAlreadyExistsError (409)
- OrgValidationError (422)

**Estimated:** 3-4 hours (largest service, establishes pattern for others)

### UserService (19 instances)

**File:** src/giljo_mcp/services/user_service.py
**Tests:** tests/services/test_user_service.py

**Methods to refactor (example subset):**
- get_user() - Return User, raise UserNotFoundError
- create_user() - Return User, raise UserAlreadyExistsError
- update_user() - Return User, raise UserNotFoundError
- delete_user() - Return bool, raise UserNotFoundError
- authenticate_user() - Return User, raise AuthenticationError
- [... 14 more methods]

**Exceptions needed:**
- UserNotFoundError (404)
- UserAlreadyExistsError (409)
- AuthenticationError (401)
- UserValidationError (422)

**Estimated:** 2-3 hours

### ProductService (17 instances)

**File:** src/giljo_mcp/services/product_service.py
**Tests:** tests/services/test_product_service.py

**Methods to refactor (example subset):**
- get_product() - Return Product, raise ProductNotFoundError
- create_product() - Return Product, raise ProductAlreadyExistsError
- update_product() - Return Product, raise ProductNotFoundError
- delete_product() - Return bool, raise ProductNotFoundError
- activate_product() - Return Product, raise ProductNotFoundError
- [... 12 more methods]

**Exceptions needed:**
- ProductNotFoundError (404)
- ProductAlreadyExistsError (409)
- ProductValidationError (422)

**Estimated:** 2-3 hours

---

## Tier 2: Medium-Impact Services (4-6 hours)

### TaskService (14 instances)

**File:** src/giljo_mcp/services/task_service.py
**Tests:** tests/services/test_task_service.py

**Estimated:** 1.5-2 hours

### ProjectService (9 instances)

**File:** src/giljo_mcp/services/project_service.py
**Tests:** tests/services/test_project_service.py

**Estimated:** 1-1.5 hours

### MessageService (8 instances)

**File:** src/giljo_mcp/services/message_service.py
**Tests:** tests/services/test_message_service.py

**Estimated:** 1-1.5 hours

---

## Tier 3: Low-Impact Services (4-6 hours)

Each service has 4-6 instances:
- OrchestrationService (6 instances) - 1 hour
- ContextService (4 instances) - 45 min
- ConsolidationService (4 instances) - 45 min
- AgentJobManager (4 instances) - 45 min
- VisionSummarizer (4 instances) - 45 min
- TemplateService (4 instances) - 45 min

**Strategy:** Process in batch, commit together if patterns are identical

---

## Implementation Instructions

### Before Starting

1. **Read 0730a deliverables:**
   - docs/architecture/service_response_models.md (return type reference)
   - docs/architecture/exception_mapping.md (exception reference)

2. **Verify exception hierarchy:**
   - Read src/giljo_mcp/exceptions.py
   - Ensure all needed exceptions exist
   - If gaps found, add exceptions first

3. **Set up test environment:**
   ```bash
   cd F:/GiljoAI_MCP
   source venv/Scripts/activate
   pytest tests/ --collect-only  # Verify tests can be collected
   ```

### Tier 1 Execution (Start Here)

**Day 1: OrgService (3-4 hours)**
1. Read test file: tests/services/test_org_service.py
2. Update all tests to expect exceptions
3. Run tests to confirm failures: `pytest tests/services/test_org_service.py -v`
4. Read service file: src/giljo_mcp/services/org_service.py
5. Refactor all 33 methods following pattern
6. Run tests to confirm fixes with coverage
7. Commit with descriptive message

**Day 2: UserService + ProductService (4-6 hours)**
1. Follow same TDD workflow for UserService (19 instances)
2. Commit UserService changes
3. Follow same TDD workflow for ProductService (17 instances)
4. Commit ProductService changes
5. Run full test suite to check for regressions: `pytest tests/services/ -v`

### Tier 2 Execution

**Day 3: TaskService, ProjectService, MessageService (4-6 hours)**
1. Process each service following same TDD workflow
2. Commit after each service
3. Run full test suite after tier complete

### Tier 3 Execution

**Day 4: Remaining 6 Services (4-6 hours)**
1. Process each service following same TDD workflow
2. Can batch similar services (e.g., ContextService + ConsolidationService)
3. Run full test suite after all complete

---

## Success Criteria

**CODE QUALITY:**
- ✅ All 122 methods refactored to return models and raise exceptions
- ✅ Zero dict wrapper patterns remaining in service methods
- ✅ Type hints added to all method signatures
- ✅ Docstrings updated with Raises sections
- ✅ Consistent exception usage across similar operations

**TESTING:**
- ✅ All service tests updated to expect exceptions
- ✅ All tests passing: `pytest tests/services/ -v`
- ✅ Coverage maintained >80%: `pytest tests/services/ --cov=src/giljo_mcp/services/`
- ✅ No regressions in other test suites

**PROCESS:**
- ✅ TDD workflow followed for every service (tests first, then code)
- ✅ One commit per service for easy rollback
- ✅ Commit messages follow conventional format
- ✅ Pre-commit hooks passing (no --no-verify)

**HANDOFF READINESS:**
- ✅ All services refactored and tested
- ✅ Documentation updated in comms_log.json
- ✅ Ready for 0730c (API endpoint updates)

---

## Validation Commands

```bash
# Run all service tests
pytest tests/services/ -v

# Check coverage
pytest tests/services/ --cov=src/giljo_mcp/services/ --cov-report=term-missing

# Verify no dict wrappers remain in services
grep -r "\"success\":" src/giljo_mcp/services/ --include="*.py" | grep -v "#" | wc -l
# Should return 0

# Run full test suite (check for regressions)
pytest tests/ -v

# Verify pre-commit hooks pass
git add -A
pre-commit run --all-files
```

---

## Risks and Considerations

**BREAKING CHANGES:**
Risk: API endpoints still expect dict wrappers
Mitigation: This is expected - 0730c will update endpoints. DO NOT update endpoints in this phase.

**TEST ISOLATION:**
Risk: Existing tests may have transaction isolation issues (known issue from Handover 0322)
Mitigation: If isolation issues found, fix in separate commit and document

**EXCEPTION HIERARCHY GAPS:**
Risk: May discover needed exceptions not in hierarchy
Mitigation: Add exceptions to src/giljo_mcp/exceptions.py before using

**REGRESSION RISK:**
Risk: Changes to services may break dependent code
Mitigation: Comprehensive test coverage and careful review before each commit

---

## Reference Materials

**REQUIRED READING (from 0730a):**
- docs/architecture/service_response_models.md
- docs/architecture/exception_mapping.md

**CODE REFERENCES:**
- src/giljo_mcp/exceptions.py: Exception hierarchy
- tests/services/: All service test files
- src/giljo_mcp/services/: All service implementations

**DOCUMENTATION:**
- SERVICES.md: Service layer patterns
- TESTING.md: Testing patterns and coverage
- CLAUDE.md: Pre-commit hook policy

---

## Recommended Sub-Agent

**Agent:** tdd-implementor

**Why this agent:**
- Test-Driven Development expertise
- Systematic refactoring experience
- Regression prevention through testing
- High code quality standards

---

## Definition of Done

1. ✅ All 122 service methods refactored
2. ✅ All service tests updated and passing
3. ✅ Coverage >80% maintained
4. ✅ No dict wrapper patterns remaining in services
5. ✅ All commits successful with pre-commit hooks passing
6. ✅ Validation commands all pass
7. ✅ Comms log updated with completion status
8. ✅ Ready for 0730c (API updates)

---

## Timeline Estimate

- Tier 1 Services: 8-12 hours (OrgService, UserService, ProductService)
- Tier 2 Services: 4-6 hours (TaskService, ProjectService, MessageService)
- Tier 3 Services: 4-6 hours (6 remaining services)

**TOTAL:** 16-24 hours (tdd-implementor agent)

**Recommended:** 3-4 days with regular commits

---

## Next Steps After Completion

**Handoff to 0730c (API Updates):**
- All services now return models and raise exceptions
- API endpoints can be simplified (remove dict checking logic)
- Update comms_log.json with completion status
- Mark 0730b as COMPLETE in orchestrator_state.json
- Unblock 0730c for execution

**Communication to Orchestrator:**
```json
{
  "from": "0730b",
  "to": "orchestrator",
  "status": "complete",
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

---

**Created:** 2026-02-07
**Status:** BLOCKED (waiting for 0730a)
**Priority:** P2 - MEDIUM
**Blocks:** 0730c, 0730d

---

## Notes for Executor

1. **TDD is Non-Negotiable** - Always update tests first, then implementation
2. **Start with OrgService** - Largest service, establishes pattern for others
3. **Commit Frequently** - One commit per service for easier rollback
4. **Run Tests Often** - After each method update, run affected tests
5. **Check Coverage** - Maintain >80% throughout
6. **Don't Touch Endpoints** - API updates happen in 0730c, not this phase
7. **Use Serena MCP** - Avoid reading entire files; use symbolic navigation
8. **Follow Patterns** - Refer to 0730a docs for consistent exception usage
9. **Ask Questions** - If unclear on exception type, consult 0730a documentation
10. **Quality Over Speed** - Better to take extra time and get it right

This is the core refactoring work - invest the time to do it properly.
