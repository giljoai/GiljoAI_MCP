# Kickoff Prompt: 0730a Design Response Models

**Agent Role:** system-architect
**Estimated Time:** 4-6 hours
**Prerequisites:** Read this entire prompt before starting

---

## Your Mission

You are a **system-architect** agent executing **Handover 0730a: Design Response Models and Exception Mapping**.

Your goal is to create architectural design documents for migrating 122 dict wrapper instances to Pydantic models with exception-based error handling across 12 services.

**This is Phase 1 of 4** in the 0730 Service Response Models series. Your deliverables will guide execution agents in 0730b-d.

---

## Critical Context

**Full Handover Specification:**
Read `F:\GiljoAI_MCP\handovers\0730a_DESIGN_RESPONSE_MODELS.md` completely before starting.

**Project:** GiljoAI MCP v1.0 - Multi-tenant agent orchestration server
**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL
**Branch:** feature/0700-code-cleanup-series

**Scope:** 122 dict wrapper instances across 12 services:
- Tier 1 (57%): OrgService (33), UserService (19), ProductService (17)
- Tier 2 (26%): TaskService (14), ProjectService (9), MessageService (8)
- Tier 3 (18%): 6 services with 4-6 instances each

---

## Your Deliverables

Create these 3 documents in `docs/architecture/`:

### 1. service_response_models.md
Document every service method's return type and exceptions:
```markdown
## OrgService Response Models
- get_org(org_id) -> Organization
  - Raises: OrgNotFoundError (404)
- create_org(...) -> Organization
  - Raises: OrgAlreadyExistsError (409)
...
```

### 2. exception_mapping.md
Document exception-to-HTTP-status mapping:
```markdown
## Exception Hierarchy
- NotFoundError → 404
- AlreadyExistsError → 409
- ValidationError → 422
...

## Service-Specific Exceptions
- OrgNotFoundError(NotFoundError) → 404
- UserNotFoundError(NotFoundError) → 404
...
```

### 3. api_exception_handling.md
Document API endpoint migration pattern:
```markdown
## Current Pattern (to remove)
result = await service.get_org(org_id)
if not result["success"]:
    raise HTTPException(...)

## Target Pattern
org = await service.get_org(org_id)  # Raises exception
return org  # Exception handlers catch it
```

---

## Step-by-Step Instructions

### Phase 1: Service Method Audit (2-3 hours)

**Use Serena MCP tools to analyze efficiently:**

```python
# For each service, get symbols overview
mcp__serena__get_symbols_overview(relative_path="src/giljo_mcp/services/org_service.py")

# For critical methods, read body
mcp__serena__find_symbol(
    name_path_pattern="OrgService/get_org",
    relative_path="src/giljo_mcp/services/org_service.py",
    include_body=True
)
```

**Start with OrgService (33 instances)** - provides comprehensive patterns:
1. List all methods returning `{"success": ..., "data": ...}` or `{"success": ..., "error": ...}`
2. For each method, document:
   - Current return pattern (dict wrapper)
   - Success case value
   - Error cases and messages
   - Target return type (Pydantic model or domain object)
   - Required exception type

**Then process UserService, ProductService, and remaining 9 services.**

### Phase 2: Exception Design (1-2 hours)

**Review existing exception hierarchy:**
```python
# Read exception hierarchy
mcp__serena__get_symbols_overview(relative_path="src/giljo_mcp/exceptions.py")

# Read exception handlers
mcp__serena__get_symbols_overview(relative_path="api/exception_handlers.py")
```

**Verify all needed exception types exist:**
- OrgNotFoundError, OrgAlreadyExistsError, OrgValidationError
- UserNotFoundError, UserAlreadyExistsError, AuthenticationError
- ProductNotFoundError, ProductAlreadyExistsError
- TaskNotFoundError, ProjectNotFoundError
- ... (continue for all services)

**If gaps found:**
- Document in exception_mapping.md
- Propose exception hierarchy additions
- Map to HTTP status codes (404, 409, 422, etc.)

### Phase 3: Documentation Creation (1-2 hours)

**Write service_response_models.md:**
- Organize by service (OrgService, UserService, etc.)
- For each method: return type + exceptions raised
- Consistent formatting
- Clear migration path from dict to model

**Write exception_mapping.md:**
- Exception hierarchy diagram
- HTTP status code mapping
- Service-specific exception types
- Migration pattern examples

**Write api_exception_handling.md:**
- Current pattern vs target pattern
- Exception handler verification checklist
- API endpoint update guidelines

---

## Critical Requirements

**SERENA MCP USAGE:**
- ✅ Use `mcp__serena__get_symbols_overview` for file overviews
- ✅ Use `mcp__serena__find_symbol` for specific method bodies
- ✅ AVOID reading entire files - use symbolic navigation
- ✅ Use `mcp__serena__search_for_pattern` for pattern matching

**COMPLETENESS:**
- ✅ All 122 instances must be documented
- ✅ No ambiguity in migration path
- ✅ Exception types verified or proposed
- ✅ HTTP status codes mapped correctly

**CONSISTENCY:**
- ✅ Same operations across services use same patterns
- ✅ get_x() methods follow same pattern
- ✅ create_x() methods follow same pattern
- ✅ Exception naming consistent (ServiceNameNotFoundError)

**QUALITY:**
- ✅ Clear examples for each pattern
- ✅ Rationale documented for design decisions
- ✅ Ready for 0730b execution agents to use

---

## Success Criteria

You are COMPLETE when:
1. ✅ All 3 deliverable documents created
2. ✅ All 122 instances cataloged in service_response_models.md
3. ✅ Exception mapping complete with HTTP codes
4. ✅ API handling pattern documented
5. ✅ No ambiguity - execution agents can proceed independently
6. ✅ Review complete - no gaps in exception hierarchy

---

## Handoff Protocol

When complete, update tracking documents:

**Update `handovers/0700_series/comms_log.json`:**
```json
{
  "timestamp": "2026-02-07T[TIME]Z",
  "from": "0730a",
  "to": "orchestrator",
  "type": "phase_complete",
  "phase": "design",
  "deliverables": [
    "docs/architecture/service_response_models.md",
    "docs/architecture/exception_mapping.md",
    "docs/architecture/api_exception_handling.md"
  ],
  "key_decisions": [
    "Exception hierarchy sufficient - no additions needed",
    "Canonical pattern established for all CRUD operations",
    "HTTP status code mapping verified complete"
  ],
  "ready_for": ["0730b"]
}
```

**Mark ready:** Update `handovers/0700_series/orchestrator_state.json` to mark 0730a COMPLETE.

---

## Resources

**Critical Files:**
- `handovers/0730a_DESIGN_RESPONSE_MODELS.md` - Full specification
- `src/giljo_mcp/exceptions.py` - Exception hierarchy (review first)
- `api/exception_handlers.py` - HTTP exception mapping (verify complete)
- `src/giljo_mcp/services/*.py` - All 12 service files to audit

**Documentation:**
- `docs/SERVICES.md` - Service layer patterns
- `docs/TESTING.md` - Testing patterns
- `CLAUDE.md` - Project coding standards

---

## Important Notes

1. **Use Serena MCP** - Don't read entire files, use symbolic navigation
2. **Start with OrgService** - 33 instances provide comprehensive patterns
3. **Document Exceptions** - Every error case needs exception type
4. **Think Consistency** - Same operations should use same patterns
5. **Quality Over Speed** - This blueprint prevents rework in 0730b-d
6. **Ask Questions** - If unclear on patterns, consult existing code
7. **Validate Coverage** - All 122 instances must be in documentation

---

**Ready to start?** Read the full handover specification first, then begin Phase 1: Service Method Audit.

Good luck! Your design work is critical for the success of 0730b-d.
