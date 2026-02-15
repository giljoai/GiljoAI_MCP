# Handover 0730a: Design Response Models and Exception Mapping

**Handover ID:** 0730a
**Series:** 0700 Code Cleanup → 0730 Service Response Models
**Phase:** 1 of 4 (Design)
**Priority:** P2 - MEDIUM
**Estimated Effort:** 4-6 hours
**Status:** READY
**Dependencies:** 0480 series (exception hierarchy), 0725b (AST audit)
**Blocks:** 0730b, 0730c, 0730d

---

## 1. Summary

Design Pydantic response models and exception mapping strategy for 122 dict wrapper instances across 12 services. This handover is a **design-only phase** that creates architectural blueprints for the service layer refactoring (0730b), API endpoint updates (0730c), and testing validation (0730d). No code changes will be made—only documentation deliverables.

The 122 instances were validated via AST-based audit in Handover 0725b with <5% false positive rate. These instances span 12 services across 3 tiers by impact level.

---

## 2. Context

### Why This Matters

**Business Value:**
- Provides clear architectural blueprint preventing rework in implementation phases
- Ensures consistency across all 122 service method refactorings
- Documents exception-to-HTTP-status mapping for proper REST API semantics
- Establishes canonical patterns that downstream agents can follow independently

**Technical Context:**
- Current anti-pattern: Services return `{"success": bool, "data": ...}` dicts
- Target pattern: Services return domain models and raise exceptions for errors
- Exception hierarchy exists (Handover 0480 series) but needs mapping documentation
- API endpoints currently check `result["success"]` before returning—will be simplified in 0730c

**Project Impact:**
- Foundation for entire 0730 series (0730b, 0730c, 0730d depend on this)
- Zero ambiguity in execution = faster implementation with fewer questions
- Prevents architectural drift across 12 services

---

## 3. Technical Details

### Scope: 122 Dict Wrapper Instances

**TIER 1 (57%)** - 69 instances:
- OrgService (services/org_service.py): 33 instances
- UserService (services/user_service.py): 19 instances
- ProductService (services/product_service.py): 17 instances

**TIER 2 (26%)** - 31 instances:
- TaskService (services/task_service.py): 14 instances
- ProjectService (services/project_service.py): 9 instances
- MessageService (services/message_service.py): 8 instances

**TIER 3 (18%)** - 22 instances:
- OrchestrationService: 6 instances
- ContextService: 4 instances
- ConsolidationService: 4 instances
- AgentJobManager: 4 instances
- VisionSummarizer: 4 instances
- TemplateService: 4 instances

**GRAND TOTAL:** 122 instances across 12 services

### Pattern Examples

**Current Anti-Pattern:**
```python
async def get_organization(self, org_id: str) -> dict[str, Any]:
    org = await self.session.get(Organization, org_id)
    if not org:
        return {"success": False, "error": "Organization not found"}
    return {"success": True, "data": org}
```

**Target Pattern:**
```python
async def get_organization(self, org_id: str) -> Organization:
    """Get organization by ID.

    Args:
        org_id: Organization ID

    Returns:
        Organization model

    Raises:
        ResourceNotFoundError: Organization not found
    """
    org = await self.session.get(Organization, org_id)
    if not org:
        raise ResourceNotFoundError(
            message="Organization not found",
            context={"org_id": org_id}
        )
    return org
```

### Exception Hierarchy

From Handover 0480 series (`src/giljo_mcp/exceptions.py`):

- `ResourceNotFoundError` → 404
- `ValidationError` → 400
- `AuthenticationError` → 401
- `AuthorizationError` → 403
- `DatabaseError` → 500
- `TemplateNotFoundError` → 404
- `OrchestrationError` → 500
- `ProjectStateError` → 400 (specific to project lifecycle)

**Gap Identified:** `AlreadyExistsError` (409) needed for duplicate resource scenarios (slug exists, username exists, etc.). Will be documented and added in 0730b if not present.

---

## 4. Implementation Plan

### Step 1: Read Exception Hierarchy (30 minutes)

**Objective:** Verify all needed exception types exist

**Actions:**
1. Read `src/giljo_mcp/exceptions.py` completely
2. Read `api/exception_handlers.py` to verify HTTP mapping handlers
3. Document any gaps (e.g., `AlreadyExistsError` for 409 Conflict)
4. Create gap analysis table in `exception_mapping.md`

**Deliverable:** Understanding of existing exception hierarchy and gaps

### Step 2: Service Method Catalog (2-3 hours)

**Objective:** Document all 122 dict wrapper instances with target return types

**Serena MCP Workflow (REQUIRED):**

```bash
# For each service, get overview of methods
mcp__serena__get_symbols_overview(
    relative_path="src/giljo_mcp/services/org_service.py"
)

# For each method, analyze return statements
mcp__serena__find_symbol(
    name_path_pattern="OrgService/get_organization",
    include_body=True
)

# Find all dict wrapper patterns
mcp__serena__search_for_pattern(
    substring_pattern='\\{"success":',
    relative_path="src/giljo_mcp/services",
    restrict_search_to_code_files=True
)
```

**For each of 122 methods, document:**
1. Current return type (dict wrapper structure)
2. Success case return value (what's in `data` key)
3. Error cases and error messages
4. Target Pydantic model or domain object
5. Required exceptions with HTTP status codes

**Start with OrgService (33 instances)** - Largest service, establishes pattern for others

**Deliverable:** Complete catalog table in `service_response_models.md`

### Step 3: Exception Mapping Documentation (1-2 hours)

**Objective:** Map every error case to specific exception type

**Actions:**
1. Create exception usage matrix (service × error condition → exception)
2. Document HTTP status code for each exception type
3. Provide migration pattern examples (before/after code snippets)
4. Document any service-specific exceptions needed

**Key Patterns:**
- Not found errors: `ResourceNotFoundError` (404)
- Duplicate creation: `AlreadyExistsError` (409) - **TO BE ADDED**
- Invalid input: `ValidationError` (400)
- Permission denied: `AuthorizationError` (403)
- Wrong credentials: `AuthenticationError` (401)
- DB failures: `DatabaseError` (500)

**Deliverable:** Complete exception mapping in `exception_mapping.md`

### Step 4: API Pattern Documentation (1 hour)

**Objective:** Document how API endpoints will be simplified in 0730c

**Current API Pattern:**
```python
result = await org_service.get_organization(org_id)
if not result["success"]:
    raise HTTPException(status_code=400, detail=result["error"])
return result["data"]
```

**Target API Pattern:**
```python
# Service raises exceptions, exception handlers catch them
org = await org_service.get_organization(org_id)
return org  # Exception handlers in api/exception_handlers.py handle errors
```

**Actions:**
1. Document current API dict-checking pattern
2. Document target pattern (simplified, let exceptions propagate)
3. Verify all exception handlers exist in `api/exception_handlers.py`
4. Document any handler gaps

**Deliverable:** API pattern guide in `api_exception_handling.md`

### Step 5: Quality Review (30 minutes)

**Objective:** Validate completeness and consistency

**Checklist:**
- [ ] All 122 instances documented with return types
- [ ] All error cases mapped to exceptions
- [ ] HTTP status codes correct for all exceptions
- [ ] Migration patterns clear with code examples
- [ ] No ambiguity - executor can proceed independently
- [ ] Cross-references between documents accurate

**Deliverable:** Three approved architecture documents ready for 0730b

---

## 5. Coding Principles (from handover_instructions.md)

**You MUST follow these principles:**

1. ✅ **Use Serena MCP Tools:** Do NOT read entire files. Use `find_symbol`, `get_symbols_overview`, `search_for_pattern` for code exploration
2. ✅ **Cross-Platform Paths:** Use `pathlib.Path()` for all file operations (NEVER hardcoded `F:\`)
3. ✅ **Multi-Tenant Isolation:** All database queries filtered by `tenant_key` (note for service analysis)
4. ✅ **Chef's Kiss Quality:** Production-grade documentation only—no shortcuts, no "good enough"
5. ✅ **Clean Documentation:** Maximum 1000 words per section unless code examples require more
6. ✅ **No Emojis:** Professional tone only (exception: 🛑 for STOP boundaries)
7. ✅ **Link Properly:** Use relative paths for all internal documentation links

**CRITICAL FOR THIS PHASE:**
- This is DESIGN ONLY. Do NOT modify any service code.
- Do NOT update tests. Testing updates happen in 0730b.
- Do NOT update API endpoints. API updates happen in 0730c.
- Focus: Documentation deliverables only.

---

## 6. Testing Requirements

**This phase has NO code changes, therefore NO tests to write.**

Testing requirements will be documented IN the design deliverables for use by 0730b executor:

**In `service_response_models.md`, document for each service:**
- What tests currently expect (dict wrappers with `["success"]` key)
- What tests should expect after refactoring (direct models and exceptions)
- Example test transformation (before/after snippets)

**In `exception_mapping.md`, document:**
- How to test exception raising (`pytest.raises` pattern)
- How to verify exception context contains entity IDs
- How to validate HTTP status codes via exception handlers

---

## 7. Dependencies & Integration

### Dependencies (Upstream)

**MUST BE COMPLETE:**
- ✅ Handover 0480 series (exception hierarchy exists)
- ✅ Handover 0725b (122 instances validated via AST audit)

**MUST EXIST:**
- `src/giljo_mcp/exceptions.py` (exception definitions)
- `api/exception_handlers.py` (HTTP status mapping)

### Blocks (Downstream)

**This handover blocks:**
- 0730b (Service Refactoring) - Requires design docs as blueprint
- 0730c (API Updates) - Requires exception mapping for endpoint simplification
- 0730d (Testing Validation) - Requires response models for test assertions

**Integration Points:**
- Design docs will be authoritative reference for all 0730b-d work
- Exception mapping table will be used for API endpoint error handling
- Response model catalog will guide Pydantic schema creation

---

## 8. Success Criteria

### Documentation Completeness

- [ ] `docs/architecture/service_response_models.md` created
  - [ ] All 122 instances cataloged in tables
  - [ ] Return types documented (current → target)
  - [ ] Error cases documented with required exceptions
  - [ ] HTTP status codes mapped
  - [ ] Migration pattern examples included

- [ ] `docs/architecture/exception_mapping.md` created
  - [ ] Exception hierarchy visualized
  - [ ] HTTP status code mapping table complete
  - [ ] Service-specific exception usage documented
  - [ ] Before/after code examples included
  - [ ] Gap analysis (e.g., `AlreadyExistsError` needed)

- [ ] `docs/architecture/api_exception_handling.md` created
  - [ ] Current API pattern documented
  - [ ] Target API pattern documented
  - [ ] Exception handler verification complete
  - [ ] Migration guide for 0730c included

### Quality Standards

- [ ] Maximum 1000 words per section (exception: code examples can exceed)
- [ ] All code examples are complete and syntactically correct
- [ ] Consistent formatting across all three documents
- [ ] Cross-references between documents use relative paths
- [ ] No ambiguity—0730b executor can proceed independently
- [ ] Professional tone, no emojis (except in STOP section)

### Architectural Consistency

- [ ] Same operations across services use same patterns (e.g., all `get_x` methods)
- [ ] Exception hierarchy sufficient for all 122 cases
- [ ] No gaps in exception-to-HTTP-status mapping
- [ ] Pydantic response types align with existing schemas in `api/schemas/`

### Handoff Readiness

- [ ] Clear blueprint for 0730b (service refactoring)
- [ ] Clear blueprint for 0730c (API updates)
- [ ] Zero ambiguity in execution approach
- [ ] All 122 instances have documented migration path

---

## 9. Rollback Plan

**Scenario:** Design documents contain errors or gaps discovered during 0730b execution.

**Rollback Actions:**
1. Archive flawed documents to `F:\GiljoAI_MCP\docs\architecture\archive\0730a_v1\`
2. Update this handover with lessons learned
3. Re-execute design phase with corrections
4. Increment document version numbers (v1 → v2)

**Prevention:**
- Thorough review in Step 5 before marking complete
- Validate against actual code (use Serena MCP to spot-check)
- Cross-check exception handlers exist for all documented exceptions

**Recovery Time:** 1-2 hours to fix gaps and regenerate documents

---

## 10. Resources

### Related Handovers

- **0480 Series:** Exception handling remediation (establishes exception hierarchy)
- **0725b:** Code health re-audit (validates 122 instances via AST analysis)
- **0322:** Service layer architecture patterns (context for design decisions)
- **0500-0515:** Remediation series (background on service layer improvements)
- **0730b:** Service refactoring (NEXT PHASE - consumes these design docs)
- **0730c:** API endpoint updates (depends on exception mapping)
- **0730d:** Testing validation (depends on response models)

### Documentation References

- `docs/SERVICES.md` - Service layer patterns (will be updated in 0730d)
- `docs/SERVER_ARCHITECTURE_TECH_STACK.md` - Overall system architecture
- `docs/TESTING.md` - Testing patterns for TDD workflow in 0730b
- `handovers/handover_instructions.md` - Authoritative handover structure and coding principles
- `CLAUDE.md` - Project coding standards and cross-platform requirements

### Code References

- `src/giljo_mcp/exceptions.py` - Exception hierarchy (BaseGiljoError and subclasses)
- `api/exception_handlers.py` - HTTP exception mapping (from 0480 series)
- `src/giljo_mcp/services/` - All 12 service implementations
- `api/endpoints/` - All API endpoint implementations
- `api/schemas/` - Existing Pydantic response schemas

### External Resources

- Pydantic Documentation: https://docs.pydantic.dev/latest/
- FastAPI Exception Handling: https://fastapi.tiangolo.com/tutorial/handling-errors/

---

## 🛑 CRITICAL: STOP AFTER COMPLETION

**DO NOT PROCEED TO HANDOVER 0730b WITHOUT EXPLICIT USER APPROVAL**

After completing this handover:

1. ✅ **Create all deliverables** listed in Success Criteria section:
   - `docs/architecture/service_response_models.md`
   - `docs/architecture/exception_mapping.md`
   - `docs/architecture/api_exception_handling.md`

2. ✅ **Update comms_log.json** with completion message:
   ```json
   {
     "from": "0730a",
     "to": "orchestrator",
     "status": "complete",
     "deliverables": [
       "docs/architecture/service_response_models.md",
       "docs/architecture/exception_mapping.md",
       "docs/architecture/api_exception_handling.md"
     ],
     "key_decisions": [
       "Exception hierarchy sufficient - only AlreadyExistsError (409) needed",
       "Canonical pattern established for all get/list/create/update/delete operations",
       "API exception handlers verified - no gaps found"
     ]
   }
   ```

3. ✅ **Mark handover status** as COMPLETE in `handovers/0700_series/orchestrator_state.json`

4. ✅ **Commit deliverables** with proper message format:
   ```bash
   git add docs/architecture/service_response_models.md \
           docs/architecture/exception_mapping.md \
           docs/architecture/api_exception_handling.md \
           handovers/0700_series/comms_log.json \
           handovers/0700_series/orchestrator_state.json

   git commit -m "docs(0730a): Complete response model design and exception mapping

   - Document 122 dict wrapper instances across 12 services
   - Map all error cases to domain exceptions with HTTP status codes
   - Establish canonical migration patterns for 0730b execution
   - Identify AlreadyExistsError (409) gap for duplicate resources

   Deliverables:
   - service_response_models.md (complete catalog)
   - exception_mapping.md (exception hierarchy and HTTP mapping)
   - api_exception_handling.md (API simplification patterns)

   ```

5. 🛑 **STOP IMMEDIATELY AND REPORT TO USER:**
   - "Handover 0730a COMPLETE. All design documents created."
   - "Cataloged all 122 dict wrapper instances with target return types."
   - "Exception mapping complete with HTTP status codes."
   - "Ready for user review before proceeding to 0730b."

6. ❌ **DO NOT start Handover 0730b** (Service Layer Refactoring)
7. ❌ **DO NOT read** `handovers/0730b_REFACTOR_SERVICES.md`
8. ❌ **DO NOT read** `handovers/0700_series/kickoff_prompts/0730b_REFACTOR_kickoff.md`
9. ❌ **DO NOT modify any service code** (this is design phase only)
10. ❌ **DO NOT proceed** to implementation without user approval

**This is a hard phase boundary. Proceeding without user approval violates project workflow.**

User will review design documents and provide NEW kickoff prompt if approved to proceed to 0730b.

---

## Definition of Done

**Code Quality:**
- [ ] N/A - This is a design phase with no code changes

**Functionality:**
- [ ] All 122 dict wrapper instances cataloged in service_response_models.md
- [ ] Exception mapping complete in exception_mapping.md
- [ ] API pattern documentation complete in api_exception_handling.md
- [ ] Gap analysis documented (AlreadyExistsError needed)
- [ ] Cross-references between documents accurate

**Documentation:**
- [ ] Three architecture documents created in `docs/architecture/`
- [ ] Each document follows professional formatting standards
- [ ] Code examples are complete and syntactically correct
- [ ] Maximum 1000 words per section (except code examples)
- [ ] comms_log.json updated with completion message

**Integration:**
- [ ] Design docs provide clear blueprint for 0730b
- [ ] Exception mapping provides clear guide for 0730c
- [ ] Response models provide clear guide for 0730d
- [ ] No ambiguity in migration approach

**Git Commit Standards:**
- [ ] Commit message follows conventional format (see STOP section)
- [ ] All deliverables staged and committed together
- [ ] Co-Authored-By tag included

**CRITICAL:**
- [ ] Stopped at phase boundary - did NOT proceed to 0730b
- [ ] Reported completion to user with deliverables summary
- [ ] Awaiting user approval before next phase

---

## Executor Notes

**Agent Profile:** system-architect (architectural decision-making, pattern consistency)

**Time Estimates:**
- Step 1 (Exception Hierarchy): 30 minutes
- Step 2 (Service Catalog): 2-3 hours
- Step 3 (Exception Mapping): 1-2 hours
- Step 4 (API Patterns): 1 hour
- Step 5 (Quality Review): 30 minutes
- **TOTAL:** 4-6 hours

**Critical Reminders:**
1. **Use Serena MCP Tools** - Do NOT read entire files with `Read` tool
2. **Design Only** - Do NOT modify any service code
3. **Start with OrgService** - 33 instances establish pattern for others
4. **Think Consistency** - Same operations across services should use same exceptions
5. **Document Gaps** - If exception hierarchy missing types, document clearly
6. **Quality Over Speed** - This blueprint prevents rework in 0730b-d
7. **Validate Coverage** - All 122 instances must be documented
8. **STOP at Boundary** - Do NOT proceed to 0730b without user approval

This design phase is critical infrastructure. Invest the time to get it right.

---

**Created:** 2026-02-08
**Version:** 2.0 (Complete Rewrite)
**Status:** READY
**Blocks:** 0730b, 0730c, 0730d
