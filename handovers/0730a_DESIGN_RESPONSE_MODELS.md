# Handover 0730a: Design Response Models and Exception Mapping

**Series:** 0700 Code Cleanup → 0730 Service Response Models (Phase 1 of 4)
**Priority:** P2 - MEDIUM
**Estimated Effort:** 4-6 hours
**Prerequisites:** Handover 0725b Complete, 0727 Complete
**Status:** READY
**Depends On:** 0480 series (exception hierarchy)
**Blocks:** 0730b, 0730c, 0730d

MISSION: Design Pydantic response models and exception mapping strategy for 122 dict wrapper instances across 12 services

WHY THIS MATTERS:
- Provides architectural blueprint for 0730b-d execution
- Ensures consistency across all service refactoring
- Documents exception-to-HTTP-status mapping
- Prevents rework by establishing patterns upfront

VALIDATION SOURCE: AST-based audit in 0725b (122 instances validated with under 5% false positive rate)

---

## Scope: 122 Dict Wrapper Instances

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

---

## Phase 1 Deliverables

### 1. Response Model Audit (docs/architecture/service_response_models.md)

**Content Required:**
```markdown
# Service Layer Response Models

## OrgService Response Models
- get_org() -> Organization (from models)
- list_orgs() -> list[Organization]
- create_org() -> Organization
  - Raises: OrgAlreadyExistsError (409)
- update_org() -> Organization
  - Raises: OrgNotFoundError (404)
...

## UserService Response Models
- get_user() -> User (from models)
- create_user() -> User
  - Raises: UserAlreadyExistsError (409)
...

[Continue for all 12 services]
```

**Success Criteria:**
- Every method documented with return type
- Every exception documented with HTTP status code
- Clear mapping from current dict wrapper to target model
- Consistent patterns across similar operations (get, list, create, update, delete)

### 2. Exception Mapping Strategy (docs/architecture/exception_mapping.md)

**Content Required:**
```markdown
# Exception Mapping for Service Layer

## Exception Hierarchy (from 0480 series)
- BaseGiljoError (base class)
  - NotFoundError → 404
  - AlreadyExistsError → 409
  - ValidationError → 422
  - UnauthorizedError → 403
  - InternalServerError → 500

## Service-Specific Exceptions

### OrgService
- OrgNotFoundError(NotFoundError) → 404
- OrgAlreadyExistsError(AlreadyExistsError) → 409
...

[Map all service exceptions]

## Migration Pattern

Current:
```python
if not org:
    return {"success": False, "error": "Organization not found"}
return {"success": True, "data": org}
```

Target:
```python
if not org:
    raise OrgNotFoundError(f"Organization {org_id} not found")
return org
```
```

**Success Criteria:**
- All exception types documented
- HTTP status codes mapped correctly
- Migration pattern clear and consistent
- Examples provided for common cases

### 3. API Layer Updates (docs/architecture/api_exception_handling.md)

**Content Required:**
```markdown
# API Endpoint Exception Handling

## Current Pattern (to remove)
```python
result = await org_service.get_org(org_id)
if not result["success"]:
    raise HTTPException(status_code=400, detail=result["error"])
return result["data"]
```

## Target Pattern
```python
# Service raises exceptions, API lets them propagate
org = await org_service.get_org(org_id)
return org  # Exception handlers in api/exception_handlers.py catch raised exceptions
```

## Exception Handler Verification
Verify these handlers exist in api/exception_handlers.py:
- NotFoundError → 404
- AlreadyExistsError → 409
- ValidationError → 422
- UnauthorizedError → 403
...

[List all required handlers]
```

**Success Criteria:**
- API pattern clearly documented
- Exception handlers verified to exist
- No gaps in exception-to-HTTP-status mapping
- Clear guidance for 0730c (API update phase)

---

## Implementation Instructions

### Step 1: Service Method Audit (2-3 hours)

Use Serena MCP tools to analyze service methods:

```bash
# For each service, get symbols overview
mcp__serena__get_symbols_overview(relative_path="src/giljo_mcp/services/org_service.py")

# For each method, analyze return statements
mcp__serena__find_symbol(
    name_path_pattern="OrgService/get_org",
    include_body=True
)
```

**For each of 122 methods, document:**
1. Current return type (dict wrapper)
2. Success case return value
3. Error cases and messages
4. Target Pydantic model or domain object
5. Required exceptions

### Step 2: Exception Design (1-2 hours)

**Review existing exception hierarchy:**
- Read src/giljo_mcp/exceptions.py
- Read api/exception_handlers.py
- Verify all needed exception types exist

**If new exceptions needed:**
- Document in exception_mapping.md
- Propose additions to exception hierarchy
- Map to HTTP status codes

### Step 3: Documentation Creation (1-2 hours)

Create 3 deliverable documents:
1. docs/architecture/service_response_models.md
2. docs/architecture/exception_mapping.md
3. docs/architecture/api_exception_handling.md

**Quality standards:**
- Clear examples for each pattern
- Consistent formatting
- Complete coverage (all 122 instances)
- Validation checklist for 0730b

---

## Success Criteria

**CODE AUDIT:**
- ✅ All 122 dict wrapper instances cataloged
- ✅ Return types documented for all methods
- ✅ Exception types documented for all error cases

**DOCUMENTATION:**
- ✅ service_response_models.md complete and accurate
- ✅ exception_mapping.md complete with HTTP status codes
- ✅ api_exception_handling.md complete with examples

**ARCHITECTURAL CONSISTENCY:**
- ✅ Same operations across services use same patterns (e.g., all get_x methods)
- ✅ Exception hierarchy sufficient for all cases
- ✅ No gaps in exception-to-HTTP-status mapping

**HANDOFF READINESS:**
- ✅ Clear blueprint for 0730b (service refactoring)
- ✅ Clear blueprint for 0730c (API updates)
- ✅ Zero ambiguity - execution agents can proceed independently

---

## Risks and Considerations

**INCOMPLETE EXCEPTION HIERARCHY:**
Risk: 0480 series may not have created all needed exception types
Mitigation: Document any new exceptions needed; can be added during 0730b

**INCONSISTENT PATTERNS:**
Risk: Different services may have evolved different patterns
Mitigation: Establish canonical pattern in documentation; enforce in 0730b review

**API HANDLER GAPS:**
Risk: api/exception_handlers.py may not handle all exception types
Mitigation: Audit handlers explicitly; document any additions needed

---

## Reference Materials

**RELATED HANDOVERS:**
- 0480 Series: Exception handling remediation (establishes exception hierarchy)
- 0725b: Code health re-audit (validates 122 instances via AST analysis)
- 0322: Service layer architecture patterns
- 0500-0515: Remediation series

**DOCUMENTATION:**
- SERVICES.md: Service layer patterns (will be updated in 0730d)
- SERVER_ARCHITECTURE_TECH_STACK.md: Overall architecture
- TESTING.md: Testing patterns

**CODE REFERENCES:**
- src/giljo_mcp/exceptions.py: Exception hierarchy (BaseGiljoError and subclasses)
- api/exception_handlers.py: HTTP exception mapping (from 0480 series)
- src/giljo_mcp/services/: All service implementations
- api/endpoints/: All API endpoint implementations

---

## Recommended Sub-Agent

**Agent:** system-architect

**Why this agent:**
- Architectural decision-making expertise
- Pattern consistency enforcement
- API design review experience
- Exception hierarchy design

---

## Definition of Done

1. ✅ All 122 instances documented in service_response_models.md
2. ✅ Exception mapping complete with HTTP status codes
3. ✅ API handling pattern documented with examples
4. ✅ No ambiguity in migration path
5. ✅ Review complete - ready for 0730b execution

---

## Timeline Estimate

- Service Method Audit: 2-3 hours
- Exception Design: 1-2 hours
- Documentation Creation: 1-2 hours

**TOTAL:** 4-6 hours (system-architect agent)

---

## Next Steps After Completion

**Handoff to 0730b (Service Refactoring):**
- Provide all 3 deliverable documents
- Update comms_log.json with design decisions
- Mark 0730a as COMPLETE in orchestrator_state.json
- Unblock 0730b for execution

**Communication to Orchestrator:**
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
    "Exception hierarchy sufficient - no additions needed",
    "Canonical pattern established for all get/list/create/update/delete operations",
    "API exception handlers verified - no gaps found"
  ],
  "ready_for": ["0730b"]
}
```

---

**Created:** 2026-02-07
**Status:** READY (Awaiting execution)
**Priority:** P2 - MEDIUM
**Blocks:** 0730b, 0730c, 0730d (must complete first)

---

## Notes for Executor

1. **Use Serena MCP Tools** - Avoid reading entire files; use symbolic navigation
2. **Start with OrgService** - 33 instances provides comprehensive pattern examples
3. **Document Exceptions** - Every error case needs an exception type
4. **Think Consistency** - Same operations across services should use same patterns
5. **Ask Questions** - If exception hierarchy gaps found, document and consult
6. **Quality Over Speed** - This blueprint prevents rework in 0730b-d
7. **Validate Coverage** - All 122 instances must be documented

This design phase is critical - invest the time to get it right.
