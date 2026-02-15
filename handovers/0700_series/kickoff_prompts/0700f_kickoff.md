# Kickoff: Handover 0700f - API Endpoint Deprecation Purge

**Series:** 0700 Code Cleanup Series
**Handover:** 0700f
**Risk Level:** MEDIUM
**Estimated Time:** 1-2 hours
**Date:** 2026-02-04

---

## Mission Statement

Remove deprecated API endpoints and ALL code that supports them. This is a PURGE operation, not a migration. Delete the endpoints from the codebase AND all supporting code (schemas, service methods, frontend API calls).

**Critical Context:** This is a pre-release cleanup. No external API consumers exist. We are shipping a clean v1.0 with NO deprecated endpoints. Delete ruthlessly.

---

## Phase 1: Context Acquisition

### Required Reads

1. **Your Spec**: `handovers/0700_series/0700f_endpoint_deprecation_purge.md`
2. **Communications**: `handovers/0700_series/comms_log.json`
   - No specific blocking entries for 0700f
3. **Conflict Analysis**: `handovers/0700_series/conflict_analysis_0709.md`
   - **CRITICAL**: Confirms 0700f does NOT conflict with 0709's new implementation phase gate
   - Your target: `api/endpoints/prompts.py` (legacy execution endpoint)
   - 0709 created: `api/endpoints/agent_jobs/orchestration.py` (new implementation gate)
   - NO OVERLAP - you're safe to proceed
4. **Protocol**: `handovers/0700_series/WORKER_PROTOCOL.md`
5. **Dependencies**: Depends on 0700c (COMPLETE)

### Key Context from Conflict Analysis

**From conflict_analysis_0709.md:**
> "0700f (Endpoint Deprecation Purge) - Overlap: NO
> Files targeted by 0700f: api/endpoints/prompts.py, api/endpoints/mcp_http.py, src/giljo_mcp/database.py, api/app.py
> 0709's new endpoint location: api/endpoints/agent_jobs/orchestration.py
> Endpoints 0700f wants to remove: GET /api/prompts/execution/{orchestrator_job_id} (DEPRECATED)
> Conflict check: The 0709 endpoint is in a different file, different HTTP method, different purpose
> Action needed: None - no overlap"

**PURGE Authorization (from orchestrator-002):**
> "There is no v4.0. We ARE v1.0. No external users exist. Delete the endpoints AND all code that uses them."

---

## Phase 2: Scope Investigation

### Primary Targets

1. **Deprecated Execution Prompt Endpoint** - `api/endpoints/prompts.py:502, 551`
   ```python
   # Line 502:
   DEPRECATED (Handover 0253): Use /api/prompts/staging/{project_id} instead.

   # Line 551:
   f"[DEPRECATED] /api/prompts/execution called for orchestrator {orchestrator_job_id}. "
   ```
   - ACTION: Identify the deprecated endpoint (likely `GET /api/prompts/execution/{orchestrator_job_id}`)
   - ACTION: Delete the endpoint function
   - ACTION: Remove from router registration
   - ACTION: Search for code calling this endpoint (should be none)
   - ACTION: Update tests that use this endpoint

2. **Legacy Progress Object in MCP** - `api/endpoints/mcp_http.py:428`
   ```python
   "description": "DEPRECATED: Use todo_items instead. Legacy progress object.",
   ```
   - ACTION: Find the response structure with this field
   - ACTION: Remove `progress` field from MCP tool responses
   - ACTION: Ensure `todo_items` is the only progress mechanism
   - ACTION: Verify no clients read `progress` field

3. **Deprecated Database Helper** - `src/giljo_mcp/database.py:337`
   ```python
   DEPRECATED: Use select(model).where() directly with async sessions.
   ```
   - ACTION: Identify the deprecated method
   - ACTION: Search for callers
   - ACTION: Update callers to use `select(model).where()` directly
   - ACTION: Delete the deprecated method

4. **Commented Endpoint Registration** - `api/app.py:246`
   ```python
   # {"name": "agents", "description": "DEPRECATED - Use agent-jobs instead"},
   ```
   - ACTION: Remove the commented-out line
   - ACTION: Clean up any related commented code

### Investigation Tasks

Use Serena MCP tools for efficient searching:

```python
# Find the deprecated execution endpoint
mcp__serena__get_symbols_overview(
    relative_path="api/endpoints/prompts.py"
)

# Find the progress field in MCP responses
mcp__serena__search_for_pattern(
    substring_pattern="DEPRECATED.*progress",
    relative_path="api/endpoints/mcp_http.py",
    output_mode="content"
)

# Find deprecated database helper
mcp__serena__search_for_pattern(
    substring_pattern="DEPRECATED.*Use select",
    relative_path="src/giljo_mcp/database.py",
    output_mode="content",
    context_lines_before=5,
    context_lines_after=5
)

# Check for any code calling the deprecated endpoint
mcp__serena__search_for_pattern(
    substring_pattern="/api/prompts/execution",
    restrict_search_to_code_files=True,
    output_mode="files_with_matches"
)
```

### Expected Files to Modify

Based on spec:
- `api/endpoints/prompts.py` - Remove deprecated endpoint
- `api/endpoints/mcp_http.py` - Remove progress field
- `src/giljo_mcp/database.py` - Remove deprecated helper
- `api/app.py` - Remove commented endpoint registration
- `api/endpoints/__init__.py` or router files - Remove endpoint registration
- **Tests** - Update or remove tests for deprecated endpoints
- **Frontend** (if applicable) - Remove any API calls to deprecated endpoints

---

## Phase 3: Execution Plan

### Recommended Subagents

- **deep-researcher** - Find all deprecated endpoints and their callers
- **backend-integration-tester** - Verify API still works after removal

### Execution Order

**Step 1: Discovery**
- Read prompts.py to identify the deprecated endpoint
- Read mcp_http.py to find the progress field structure
- Read database.py to find the deprecated helper method
- Use Serena to find ALL callers of deprecated items

**Step 2: Execution Prompt Endpoint Removal**
- Locate the endpoint function in `api/endpoints/prompts.py`
- Find where it's registered in the router
- Delete the endpoint function
- Remove from router registration
- Search for any code calling `/api/prompts/execution/...`
- Update or delete tests using this endpoint
- Verify replacement endpoint exists: `/api/prompts/staging/{project_id}`

**Step 3: MCP Progress Field Removal**
- Find the response model/schema with `progress` field
- Remove the field from the response structure
- Verify `todo_items` field is present and working
- Ensure no MCP tools return `progress` field
- Check frontend: does it read `progress` from MCP responses?

**Step 4: Database Helper Removal**
- Identify the deprecated method in `database.py`
- Find all callers using Serena
- Update each caller to use `select(model).where()` directly
- Delete the deprecated method
- Verify tests pass

**Step 5: Commented Code Cleanup**
- Remove commented endpoint registration from `api/app.py`
- Search for related commented code
- Clean up any other commented deprecations nearby

**Step 6: Verification**
```bash
# Should return ZERO results for deprecated items
grep -r "DEPRECATED" api/endpoints/prompts.py
grep -r "progress.*DEPRECATED" api/endpoints/mcp_http.py
grep -r "DEPRECATED.*select" src/giljo_mcp/database.py

# API should start
python api/run_api.py --port 7272
# Visit http://localhost:7272/docs
# Verify deprecated endpoints are gone

# Replacement endpoint should work
curl -X GET "http://localhost:7272/api/prompts/staging/{project_id}"

# Tests should pass
pytest tests/endpoints/ -v
pytest tests/integration/ -v
```

---

## Phase 4: Documentation

### Files to Check

Based on spec:
- API documentation (if any)
- OpenAPI schema/Swagger docs
- MCP tools documentation (if progress field was documented)

### Updates Needed

- Remove deprecated endpoint from API docs
- Update any examples using deprecated endpoints
- Remove mentions of `progress` field in MCP tool docs
- Update any architecture docs mentioning removed helpers

---

## Phase 5: Communication

### Write to comms_log.json

After completion, write an entry for downstream handovers:

```json
{
  "id": "0700f-complete-001",
  "timestamp": "[ISO timestamp]",
  "from_handover": "0700f",
  "to_handovers": ["0700g", "orchestrator"],
  "type": "info",
  "subject": "API endpoint deprecation purge complete",
  "message": "Removed deprecated API endpoints and supporting code. Deleted GET /api/prompts/execution/{orchestrator_job_id} endpoint (X lines). Removed progress field from MCP responses (Y lines). Removed deprecated database helper [METHOD_NAME] (Z callers updated). API starts successfully, all tests passing. Lines removed: ~[ESTIMATE].",
  "files_affected": [
    "[list all modified files]"
  ],
  "action_required": false,
  "context": {
    "lines_removed": "[ESTIMATE]",
    "endpoints_removed": ["GET /api/prompts/execution/{orchestrator_job_id}"],
    "response_fields_removed": ["progress"],
    "database_helpers_removed": ["[method name]"],
    "replacement_endpoint": "/api/prompts/staging/{project_id}"
  }
}
```

**Who needs to know:**
- **0700g** - Might need to know about schema removals
- **orchestrator** - Track progress

---

## Phase 6: Commit & Report

### Update orchestrator_state.json

```json
{
  "id": "0700f",
  "status": "complete",
  "started_at": "[ISO timestamp]",
  "completed_at": "[ISO timestamp]",
  "worker_session_id": "[your session]",
  "docs_updated": ["[list docs you updated]"],
  "endpoints_removed": ["GET /api/prompts/execution/{orchestrator_job_id}"],
  "response_fields_removed": ["progress"],
  "lines_removed": "[ESTIMATE]"
}
```

### Commit Message

```
cleanup(0700f): Remove deprecated API endpoints and legacy code

Removed deprecated endpoints and supporting code as part of v1.0 cleanup.
No backward compatibility needed - shipping clean.

Changes:
- Deleted GET /api/prompts/execution/{orchestrator_job_id} endpoint
- Removed from router registration in api/endpoints/prompts.py
- Removed progress field from MCP tool responses
- Deleted deprecated database helper [METHOD_NAME] from database.py
- Updated X callers to use select(model).where() directly
- Removed commented endpoint registration from api/app.py
- Updated/deleted Y tests referencing deprecated endpoints

Verification:
- API starts successfully: python api/run_api.py
- Replacement endpoint works: /api/prompts/staging/{project_id}
- MCP responses use todo_items exclusively
- All endpoint tests pass

Docs Updated:
- [list docs]

```

---

## Risk Mitigation

**MEDIUM RISK** - API changes could affect consumers

### Why Medium Risk?
- API surface change (endpoint removal)
- MCP response structure change (progress field)
- Database helper removal requires updating callers

### Mitigations
- Pre-release: no external API consumers
- All deprecated endpoints have documented replacements
- Test coverage should catch breaking changes

### Rollback Plan
- Git revert if something breaks
- API is versioned - old clients don't exist

### Pre-Flight Checks
- [ ] Verify replacement endpoint exists and works: `/api/prompts/staging/{project_id}`
- [ ] Verify `todo_items` field is working in MCP responses
- [ ] Identify all callers of deprecated database helper before deletion

### Parallel Execution Note

**0700e is running in PARALLEL** - Do NOT modify these files:
- `src/giljo_mcp/template_manager.py` (0700e target)
- `src/giljo_mcp/models/templates.py` (0700e target)
- `src/giljo_mcp/template_seeder.py` (0700e target)

If you discover overlap, STOP and write to comms_log immediately.

---

## Success Criteria

- [ ] Deprecated execution prompt endpoint removed
- [ ] Endpoint removed from router registration
- [ ] No code calling deprecated endpoint remains
- [ ] Progress field removed from MCP responses
- [ ] todo_items confirmed as only progress mechanism
- [ ] Deprecated database helper removed
- [ ] All callers updated to use select(model).where()
- [ ] Commented endpoint registration removed from api/app.py
- [ ] API starts successfully: `python api/run_api.py`
- [ ] Replacement endpoint works: `/api/prompts/staging/{project_id}`
- [ ] All endpoint tests pass: `pytest tests/endpoints/ -v`
- [ ] No DEPRECATED markers remain in target files
- [ ] Documentation updated
- [ ] comms_log entry written
- [ ] orchestrator_state.json updated
- [ ] Changes committed with proper message

---

## Detailed Target Locations (From Spec)

### Target 1: Deprecated Execution Endpoint
**Location:** `api/endpoints/prompts.py:502, 551`
```python
# Line 502:
DEPRECATED (Handover 0253): Use /api/prompts/staging/{project_id} instead.

# Line 551:
f"[DEPRECATED] /api/prompts/execution called for orchestrator {orchestrator_job_id}. "
```

**What to do:**
- Find the endpoint function (search for `@router.get` or `@router.post` with `/execution/` path)
- Delete the entire function
- Find router registration (in `__init__.py` or router file)
- Remove registration
- Search for any calls to `/api/prompts/execution/`
- Update tests

**Replacement:**
- `/api/prompts/staging/{project_id}` is the active endpoint

---

### Target 2: Legacy Progress Object
**Location:** `api/endpoints/mcp_http.py:428`
```python
"description": "DEPRECATED: Use todo_items instead. Legacy progress object.",
```

**What to do:**
- Find the response schema/model containing `progress` field
- Remove the `progress` field
- Ensure `todo_items` field exists and is working
- Check if any clients read `progress` (grep frontend code)

**Replacement:**
- `todo_items` is the active progress mechanism

---

### Target 3: Deprecated Database Helper
**Location:** `src/giljo_mcp/database.py:337`
```python
DEPRECATED: Use select(model).where() directly with async sessions.
```

**What to do:**
- Identify the method (likely a query helper)
- Find all callers using Serena
- Update each caller to use SQLAlchemy 2.0 pattern: `select(model).where(...)`
- Delete the method

**Pattern to replace with:**
```python
# Old (deprecated):
result = await deprecated_helper(session, Model, filters)

# New (SQLAlchemy 2.0):
from sqlalchemy import select
result = await session.execute(select(Model).where(Model.field == value))
```

---

### Target 4: Commented Endpoint
**Location:** `api/app.py:246`
```python
# {"name": "agents", "description": "DEPRECATED - Use agent-jobs instead"},
```

**What to do:**
- Delete this line entirely
- Clean up any surrounding commented code

---

**Remember:** This is a PURGE, not a migration. Delete the deprecated endpoints ruthlessly. If something breaks, we can git revert. The replacement endpoints already exist and work.

**When in doubt:** Write to comms_log and ask the orchestrator.

**Start time:** When you begin Phase 2 (Scope Investigation)
