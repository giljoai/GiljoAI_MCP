# Handover 0730b: Refactor Service Layer Methods

**Handover ID:** 0730b
**Series:** 0700 Code Cleanup → 0730 Service Response Models
**Phase:** 2 of 4 (Implementation)
**Priority:** P2 - MEDIUM
**Estimated Effort:** 16-24 hours
**Status:** BLOCKED (waiting for 0730a)
**Dependencies:** 0730a COMPLETE (design documents must exist)
**Blocks:** 0730c, 0730d

---

## 1. Summary

Refactor 122 service methods across 12 services using **Test-Driven Development (TDD)** to replace dict wrappers with Pydantic models and exception-based error handling. This is the core implementation phase of the 0730 series—all service layer code changes happen here.

The migration transforms services from returning `{"success": bool, "data": ...}` dicts to returning domain models directly and raising exceptions for error cases. TDD workflow is MANDATORY: tests are updated FIRST, then implementation code is updated to make tests pass.

**CRITICAL:** API endpoints are NOT updated in this phase—that happens in 0730c. Services will be fully refactored while endpoints temporarily remain unchanged.

---

## 2. Context

### Why This Matters

**Business Value:**
- Eliminates dict wrapper anti-pattern across entire service layer
- Enables type safety and IDE autocompletion for all service consumers
- Simplifies error handling—no more `if result["success"]` checks
- Provides foundation for API simplification in 0730c

**Technical Context:**
- Design blueprints created in 0730a (response models, exception mapping)
- Exception hierarchy exists from Handover 0480 series
- Service layer has 122 dict wrapper instances across 12 services
- TDD approach ensures zero regressions during migration

**Project Impact:**
- Core architectural improvement affecting all API endpoints
- Required before 0730c can simplify endpoint error handling
- Test suite ensures backward compatibility during transition
- ~16-24 hours of focused implementation work

---

## 3. Technical Details

### Scope: 122 Service Methods Across 3 Tiers

**TIER 1 (57%)** - 69 instances (8-12 hours):
- **OrgService:** 33 instances (largest, establishes pattern)
- **UserService:** 19 instances
- **ProductService:** 17 instances

**TIER 2 (26%)** - 31 instances (4-6 hours):
- **TaskService:** 14 instances
- **ProjectService:** 9 instances
- **MessageService:** 8 instances

**TIER 3 (18%)** - 22 instances (4-6 hours):
- **OrchestrationService:** 6 instances
- **ContextService:** 4 instances
- **ConsolidationService:** 4 instances
- **AgentJobManager:** 4 instances
- **VisionSummarizer:** 4 instances
- **TemplateService:** 4 instances

### Migration Pattern

**BEFORE (Current Anti-Pattern):**
```python
async def get_organization(self, org_id: str) -> dict[str, Any]:
    try:
        org = await self.session.get(Organization, org_id)
        if not org:
            return {"success": False, "error": "Organization not found"}
        return {"success": True, "data": org}
    except SQLAlchemyError as e:
        return {"success": False, "error": str(e)}
```

**AFTER (Target Exception-Based Pattern):**
```python
async def get_organization(self, org_id: str) -> Organization:
    """Get organization by ID.

    Args:
        org_id: Organization ID

    Returns:
        Organization model

    Raises:
        ResourceNotFoundError: Organization not found
        DatabaseError: Database operation failed
    """
    try:
        org = await self.session.get(Organization, org_id)
        if not org:
            raise ResourceNotFoundError(
                message="Organization not found",
                context={"org_id": org_id}
            )
        return org
    except SQLAlchemyError as e:
        raise DatabaseError(
            message=f"Failed to get organization: {e}",
            context={"org_id": org_id}
        ) from e
```

### Exception Usage (from 0730a docs)

- `ResourceNotFoundError` → 404 (entity not found)
- `AlreadyExistsError` → 409 (duplicate resource - ADD TO exceptions.py if missing)
- `ValidationError` → 400 (invalid input)
- `AuthenticationError` → 401 (wrong credentials)
- `AuthorizationError` → 403 (insufficient permissions)
- `DatabaseError` → 500 (database operation failed)
- `ProjectStateError` → 400 (invalid project state transition)

---

## 4. Implementation Plan

### Pre-Work: Add Missing Exception (30 minutes)

**Check if `AlreadyExistsError` exists in `src/giljo_mcp/exceptions.py`:**

```python
# If missing, add to exceptions.py:
class AlreadyExistsError(BaseGiljoError):
    """Raised when attempting to create a resource that already exists."""
    default_status_code: int = 409
```

**Use Cases:**
- OrgService: `create_organization` (slug exists)
- OrgService: `invite_member` (user already member)
- UserService: `create_user` (username/email exists)
- ProductService: `create_product` (name exists)

**Commit immediately if added:**
```bash
git add src/giljo_mcp/exceptions.py
git commit -m "feat(0730b): Add AlreadyExistsError for 409 Conflict responses

Supports duplicate resource detection in service layer refactoring.

```

### Tier 1 Execution (8-12 hours)

#### Service 1: OrgService (3-4 hours) - START HERE

**Files:**
- Service: `src/giljo_mcp/services/org_service.py`
- Tests: `tests/services/test_org_service.py`

**TDD Workflow:**

1. **Use Serena MCP to explore code structure:**
   ```python
   # Get overview of OrgService methods
   mcp__serena__get_symbols_overview(
       relative_path="src/giljo_mcp/services/org_service.py"
   )

   # Find specific method to analyze
   mcp__serena__find_symbol(
       name_path_pattern="OrgService/create_organization",
       include_body=True
   )
   ```

2. **Update tests FIRST (write failing tests):**
   ```python
   # BEFORE (test expects dict wrapper):
   def test_get_org_not_found(self, org_service):
       result = await org_service.get_organization("nonexistent")
       assert result["success"] is False
       assert "not found" in result["error"]

   # AFTER (test expects exception):
   def test_get_org_not_found(self, org_service):
       with pytest.raises(ResourceNotFoundError) as exc_info:
           await org_service.get_organization("nonexistent")
       assert "nonexistent" in str(exc_info.value)
   ```

   **Update ALL 33 test methods in `test_org_service.py`**

3. **Run tests to confirm failures:**
   ```bash
   pytest tests/services/test_org_service.py -v
   # Should show failures - tests expect exceptions, code returns dicts
   ```

4. **Update service implementation (make tests pass):**
   - Add type hints to all 33 methods
   - Update docstrings with `Raises` sections
   - Replace `return {"success": True, "data": ...}` with `return value`
   - Replace `return {"success": False, "error": ...}` with `raise Exception(...)`
   - Use exception mapping from `docs/architecture/exception_mapping.md`

5. **Run tests to confirm fixes:**
   ```bash
   pytest tests/services/test_org_service.py -v --cov=src/giljo_mcp/services/org_service.py
   # Should pass with >80% coverage
   ```

6. **Commit:**
   ```bash
   git add tests/services/test_org_service.py \
           src/giljo_mcp/services/org_service.py
   git commit -m "refactor(0730b): OrgService dict wrappers to exceptions (33 methods)

   - Replace all dict wrapper returns with direct model returns
   - Add AlreadyExistsError for duplicate slug/member scenarios
   - Update all tests to expect exceptions via pytest.raises
   - Coverage maintained at >80%

   Refactored methods:
   - create_organization, get_organization, update_organization
   - invite_member, remove_member, change_member_role
   - transfer_ownership, list_members, get_user_organizations
   - [... 24 more methods - see 0730a docs]

   ```

**Repeat for UserService (2-3 hours) and ProductService (2-3 hours) using same TDD workflow.**

### Tier 2 Execution (4-6 hours)

Process TaskService (1.5-2h), ProjectService (1-1.5h), MessageService (1-1.5h) using same TDD workflow. Commit after each service.

### Tier 3 Execution (4-6 hours)

Process remaining 6 services (6 instances × 45-60 min each). Can batch similar services if patterns identical.

**TOTAL ESTIMATED TIME:** 16-24 hours across 3-4 days

---

## 5. Coding Principles (from handover_instructions.md)

**You MUST follow these principles:**

### Code Quality Standards

1. ✅ **Chef's Kiss Production Grade:** No shortcuts, no bandaids, no "good enough"
2. ✅ **TDD Workflow (MANDATORY):**
   - Write tests FIRST (they should fail initially - red phase)
   - Write minimal code to make tests pass (green phase)
   - Refactor for quality (refactor phase)
   - Commit test + implementation together
3. ✅ **Use Serena MCP Tools:** Do NOT read entire files—use symbolic navigation:
   - `mcp__serena__get_symbols_overview` for file structure
   - `mcp__serena__find_symbol` for specific methods
   - `mcp__serena__search_for_pattern` for finding dict wrappers
   - `mcp__serena__find_referencing_symbols` for finding usages
4. ✅ **Cross-Platform Paths:** Use `pathlib.Path()` (NEVER hardcoded `F:\`)
5. ✅ **Multi-Tenant Isolation:** All database queries filtered by `tenant_key`
6. ✅ **Type Hints:** Add return type annotations to ALL method signatures
7. ✅ **Docstrings:** Update with `Raises` section for all error cases
8. ✅ **Exception Context:** Always include entity IDs in exception context dict

### Code Standards

**Type Hints (Required):**
```python
async def get_organization(self, org_id: str) -> Organization:
    # Return type MUST match target from 0730a design docs
```

**Docstrings (Required):**
```python
"""Get organization by ID.

Args:
    org_id: Organization ID

Returns:
    Organization model

Raises:
    ResourceNotFoundError: Organization not found
    DatabaseError: Database operation failed
"""
```

**Exception Context (Required):**
```python
raise ResourceNotFoundError(
    message="Organization not found",
    context={"org_id": org_id}  # Always include entity identifiers
)
```

---

## 6. Testing Requirements

### TDD Workflow (MANDATORY)

**For each service:**

1. **Red Phase:** Update ALL test methods to expect exceptions
   - Replace assertions on `result["success"]`
   - Add `pytest.raises(ExceptionType)` context managers
   - Verify exception messages contain relevant context
   - Run tests to confirm failures

2. **Green Phase:** Update service implementation
   - Add type hints to method signatures
   - Replace dict returns with direct model returns
   - Replace error dicts with raise statements
   - Run tests to confirm all pass

3. **Refactor Phase:** Improve code quality
   - Extract common exception handling patterns
   - Ensure consistent error messages
   - Verify docstrings are complete

4. **Commit:** Test + implementation together with descriptive message

### Test Pattern Examples

**Success Case Test:**
```python
# BEFORE
async def test_create_org_success(self, org_service):
    result = await org_service.create_organization("Test Org", "user-123", "tenant-abc")
    assert result["success"] is True
    assert result["data"].name == "Test Org"

# AFTER
async def test_create_org_success(self, org_service):
    org = await org_service.create_organization("Test Org", "user-123", "tenant-abc")
    assert org.name == "Test Org"
    assert org.slug == "test-org"
```

**Error Case Test:**
```python
# BEFORE
async def test_create_org_duplicate_slug(self, org_service):
    result = await org_service.create_organization("Duplicate", "user-123", "tenant-abc")
    assert result["success"] is False
    assert "already exists" in result["error"]

# AFTER
async def test_create_org_duplicate_slug(self, org_service):
    with pytest.raises(AlreadyExistsError) as exc_info:
        await org_service.create_organization("Duplicate", "user-123", "tenant-abc")
    assert "slug" in str(exc_info.value).lower()
    assert exc_info.value.default_status_code == 409
```

### Coverage Requirements

- [ ] All service tests passing: `pytest tests/services/ -v`
- [ ] Coverage >80%: `pytest tests/services/ --cov=src/giljo_mcp/services/`
- [ ] No regressions in other test suites: `pytest tests/ -v`

---

## 7. Dependencies & Integration

### Dependencies (Upstream)

**MUST BE COMPLETE BEFORE STARTING:**
- ✅ Handover 0730a (design documents exist):
  - `docs/architecture/service_response_models.md`
  - `docs/architecture/exception_mapping.md`
  - `docs/architecture/api_exception_handling.md`
- ✅ Exception hierarchy in `src/giljo_mcp/exceptions.py`
- ✅ Exception handlers in `api/exception_handlers.py`

### Blocks (Downstream)

**This handover blocks:**
- 0730c (API Endpoint Updates) - Endpoints will break until updated to use new service signatures
- 0730d (Testing Validation) - Cannot validate until all phases complete

### Integration Impact

**CRITICAL UNDERSTANDING:**
- **API endpoints will temporarily fail** after service refactoring completes
- This is expected behavior—endpoints still check `result["success"]` but services now raise exceptions
- 0730c will fix endpoints to let exceptions propagate
- **DO NOT attempt to fix endpoints in this phase**—that violates phase isolation

**WebSocket Considerations:**
- WebSocket event emission in services unaffected (separate concern)
- Services can still emit events: `await emit_event("org.created", {...})`

---

## 8. Success Criteria

### Code Quality

- [ ] All 122 service methods refactored to return models and raise exceptions
- [ ] Zero dict wrapper patterns remaining: `grep -r '"success":' src/giljo_mcp/services/ | wc -l` returns 0
- [ ] Type hints added to all method signatures
- [ ] Docstrings updated with `Raises` sections
- [ ] Consistent exception usage across similar operations
- [ ] Exception context includes entity IDs in all cases

### Testing

- [ ] All service tests updated to expect exceptions (pytest.raises pattern)
- [ ] All tests passing: `pytest tests/services/ -v`
- [ ] Coverage maintained >80%: `pytest tests/services/ --cov=src/giljo_mcp/services/`
- [ ] No regressions in other test suites: `pytest tests/ -v`

### Process

- [ ] TDD workflow followed for every service (tests first, then code)
- [ ] One commit per service for easy rollback
- [ ] Commit messages follow conventional format (see Implementation Plan examples)
- [ ] Pre-commit hooks passing (no `--no-verify` used)
- [ ] Serena MCP tools used for code navigation (not `Read` tool for entire files)

### Integration

- [ ] AlreadyExistsError added to exceptions.py if missing (committed separately)
- [ ] All 12 services refactored and committed
- [ ] comms_log.json updated with completion status
- [ ] orchestrator_state.json marks 0730b as COMPLETE
- [ ] User notified of completion—STOPPED at phase boundary

---

## 9. Rollback Plan

### Scenario 1: Test Failures During Green Phase

**Problem:** Updated service code breaks tests unexpectedly.

**Rollback:**
1. Discard uncommitted service changes: `git checkout -- src/giljo_mcp/services/{service}.py`
2. Review test expectations—may need adjustment
3. Re-attempt implementation with corrected understanding

**Prevention:** Run tests frequently during implementation (after each method update)

### Scenario 2: Regression in Other Test Suites

**Problem:** Service changes break integration tests or endpoint tests.

**Rollback:**
1. Identify which service commit introduced regression
2. Revert specific commit: `git revert <commit-hash>`
3. Document regression in GitHub issue
4. Fix underlying issue before re-applying changes

**Prevention:** Run full test suite before final commit: `pytest tests/ -v`

### Scenario 3: Critical Exception Missing from Hierarchy

**Problem:** Design docs reference exception not in `exceptions.py`.

**Rollback:**
1. Pause service refactoring
2. Add missing exception to `exceptions.py`
3. Commit exception addition separately
4. Resume service refactoring
5. Update 0730a design docs if gap was missed

**Prevention:** Verify exception hierarchy completeness in Pre-Work step

---

## 10. Resources

### Required Reading (from 0730a)

**MUST READ BEFORE STARTING:**
- `docs/architecture/service_response_models.md` - Return type reference for all 122 methods
- `docs/architecture/exception_mapping.md` - Exception-to-HTTP-status mapping

### Code References

- `src/giljo_mcp/exceptions.py` - Exception hierarchy (BaseGiljoError and subclasses)
- `tests/services/` - All service test files (TDD reference)
- `src/giljo_mcp/services/` - All 12 service implementations
- `api/exception_handlers.py` - Exception-to-HTTP mapping handlers

### Documentation

- `docs/SERVICES.md` - Service layer patterns (will be updated in 0730d)
- `docs/TESTING.md` - Testing patterns and coverage requirements
- `docs/HANDOVERS.md` - Handover format and execution workflow
- `handovers/handover_instructions.md` - Authoritative handover structure and coding principles
- `CLAUDE.md` - Project coding standards, pre-commit hook policy, cross-platform requirements

### Related Handovers

- **0730a:** Design Response Models (PREREQUISITE - must be complete)
- **0480 Series:** Exception handling remediation (established exception hierarchy)
- **0725b:** Code health re-audit (validated 122 instances via AST)
- **0322:** Service layer architecture patterns (background context)
- **0730c:** API Endpoint Updates (NEXT PHASE - depends on this)
- **0730d:** Testing Validation (depends on all phases complete)

---

## 🛑 CRITICAL: STOP AFTER COMPLETION

**DO NOT PROCEED TO HANDOVER 0730c WITHOUT EXPLICIT USER APPROVAL**

After completing this handover:

1. ✅ **Verify all deliverables complete:**
   - [ ] All 122 service methods refactored
   - [ ] All service tests updated and passing
   - [ ] Coverage >80% maintained
   - [ ] Pre-commit hooks passing
   - [ ] All commits follow conventional format

2. ✅ **Run final validation commands:**
   ```bash
   # Verify no dict wrappers remain
   grep -r '"success":' src/giljo_mcp/services/ --include="*.py" | grep -v "#" | wc -l
   # Should return 0

   # All service tests pass
   pytest tests/services/ -v

   # Coverage check
   pytest tests/services/ --cov=src/giljo_mcp/services/ --cov-report=term-missing

   # Full test suite (check for regressions)
   pytest tests/ -v
   ```

3. ✅ **Update comms_log.json:**
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
       "TDD workflow followed - zero regressions detected",
       "All tests passing with maintained coverage"
     ],
     "integration_notes": [
       "API endpoints temporarily broken - 0730c will fix",
       "AlreadyExistsError added to exception hierarchy",
       "Service signatures changed - endpoints must be updated"
     ]
   }
   ```

4. ✅ **Update orchestrator_state.json:**
   - Mark 0730b as COMPLETE
   - Update progress tracking

5. 🛑 **STOP IMMEDIATELY AND REPORT TO USER:**
   - "Handover 0730b COMPLETE. All 122 service methods refactored."
   - "Service layer now uses exception-based error handling."
   - "All tests passing with >80% coverage maintained."
   - "⚠️ WARNING: API endpoints temporarily broken—0730c will fix."
   - "Ready for user review before proceeding to 0730c."

6. ❌ **DO NOT start Handover 0730c** (API Endpoint Updates)
7. ❌ **DO NOT read** `handovers/0730c_UPDATE_API_ENDPOINTS.md`
8. ❌ **DO NOT read** `handovers/0700_series/kickoff_prompts/0730c_ENDPOINTS_kickoff.md`
9. ❌ **DO NOT attempt to fix API endpoints** (that's 0730c's responsibility)
10. ❌ **DO NOT modify exception handlers** (they're already correct from 0480 series)

**This is a hard phase boundary. Proceeding without user approval violates project workflow.**

User will review refactored services, test results, and coverage reports before approving 0730c.

**EXPECTED STATE AFTER THIS PHASE:**
- ✅ Services refactored and tested
- ⚠️ API endpoints broken (expected—fixed in 0730c)
- ⚠️ Integration tests may fail (expected—fixed in 0730c)
- ✅ Service layer tests all passing

---

## Definition of Done

**Code Quality:**
- [ ] All code follows TDD (tests written first, then implementation)
- [ ] >80% test coverage verified: `pytest --cov`
- [ ] No hardcoded paths (all use `pathlib.Path`)
- [ ] All methods have type hints with correct return types
- [ ] Docstrings for all methods with `Raises` sections
- [ ] Exception context includes entity IDs

**Functionality:**
- [ ] All 122 service methods refactored to return models
- [ ] All error cases raise appropriate exceptions
- [ ] Zero dict wrapper patterns remain in service layer
- [ ] AlreadyExistsError added to exceptions.py (if missing)
- [ ] Consistent exception usage across similar operations

**Documentation:**
- [ ] Code comments for complex logic only (not obvious code)
- [ ] comms_log.json updated with completion message
- [ ] orchestrator_state.json marks 0730b as COMPLETE

**Integration:**
- [ ] All service tests pass: `pytest tests/services/`
- [ ] Coverage maintained: `pytest tests/services/ --cov`
- [ ] No lint errors: `ruff src/; black src/`
- [ ] Pre-commit hooks pass (no `--no-verify` used)
- [ ] All commits follow conventional format

**CRITICAL:**
- [ ] Stopped at phase boundary - did NOT proceed to 0730c
- [ ] Reported completion to user with summary
- [ ] User acknowledges API endpoints temporarily broken
- [ ] Awaiting user approval before 0730c

---

## Git Commit Standards

**Commit message format:**
```
<type>(<scope>): <subject>

<body - optional>

```

**Types:** feat, refactor, test, docs, chore
**Scope:** Handover ID (0730b) or service name
**Subject:** Imperative mood, <50 chars

**Example for service refactoring:**
```bash
git commit -m "refactor(0730b): OrgService dict wrappers to exceptions (33 methods)

- Replace all dict wrapper returns with direct model returns
- Add AlreadyExistsError for duplicate slug/member scenarios
- Update all tests to expect exceptions via pytest.raises
- Coverage maintained at >80%

Refactored methods:
- create_organization, get_organization, update_organization
- invite_member, remove_member, change_member_role
- transfer_ownership, list_members, get_user_organizations
- [... 24 more methods]

```

---

## Executor Notes

**Agent Profile:** tdd-implementor (Test-Driven Development expertise, systematic refactoring)

**Time Estimates:**
- Pre-Work (AlreadyExistsError): 30 minutes
- Tier 1 Services: 8-12 hours (OrgService 3-4h, UserService 2-3h, ProductService 2-3h)
- Tier 2 Services: 4-6 hours (TaskService 1.5-2h, ProjectService 1-1.5h, MessageService 1-1.5h)
- Tier 3 Services: 4-6 hours (6 services × 45-60 min each)
- **TOTAL:** 16-24 hours across 3-4 days

**Critical Reminders:**
1. **TDD is Non-Negotiable:** Always update tests FIRST, then implementation
2. **Use Serena MCP:** Avoid reading entire files—use symbolic navigation
3. **Start with OrgService:** Largest service establishes pattern for others
4. **Commit Frequently:** One commit per service for easier rollback
5. **Run Tests Often:** After each method update, run affected tests
6. **Check Coverage:** Maintain >80% throughout refactoring
7. **Don't Touch Endpoints:** API updates happen in 0730c, not this phase
8. **Follow Design Docs:** Refer to 0730a docs for return types and exception mapping
9. **Exception Context:** Always include entity IDs in exception context
10. **STOP at Boundary:** Do NOT proceed to 0730c without user approval

**Quality Over Speed:** Better to take 24 hours and get it right than rush in 16 hours with bugs.

This is core architectural work. TDD ensures zero regressions. Follow the workflow religiously.

---

**Created:** 2026-02-08
**Version:** 2.0 (Complete Rewrite)
**Status:** BLOCKED (waiting for 0730a)
**Blocks:** 0730c, 0730d
