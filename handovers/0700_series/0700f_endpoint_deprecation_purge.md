# Handover 0700f: API Endpoint Deprecation Purge

## Context

**Pre-release cleanup decision (2026-02-04):** Remove deprecated API endpoints before v1.0 release. No backwards compatibility needed for endpoints that have replacements.

**Reference:** `handovers/0700_series/dead_code_audit.md` - Strategic Direction Change section

## Scope

Remove deprecated API endpoints and their supporting code:
1. Legacy execution prompt endpoint
2. Legacy progress object in MCP responses
3. Deprecated database helper method

**Files Affected:**
- `api/endpoints/prompts.py` - Deprecated endpoint
- `api/endpoints/mcp_http.py` - Legacy progress object
- `src/giljo_mcp/database.py` - Deprecated query method

## Tasks

### 1. Remove Deprecated Execution Prompt Endpoint

Location: `api/endpoints/prompts.py:502`

```python
DEPRECATED (Handover 0253): Use /api/prompts/staging/{project_id} instead.
```

And line 551:
```python
f"[DEPRECATED] /api/prompts/execution called for orchestrator {orchestrator_job_id}. "
```

- [ ] Identify the deprecated endpoint (likely `GET /api/prompts/execution/{orchestrator_job_id}`)
- [ ] Remove the endpoint function
- [ ] Remove from router registration
- [ ] Search for any code calling this endpoint
- [ ] Update any tests that use this endpoint

### 2. Remove Legacy Progress Object from MCP

Location: `api/endpoints/mcp_http.py:428`

```python
"description": "DEPRECATED: Use todo_items instead. Legacy progress object.",
```

- [ ] Find the response structure containing this field
- [ ] Remove the `progress` field from MCP tool responses
- [ ] Ensure `todo_items` is the only progress mechanism
- [ ] Update any clients that read `progress` (should be none pre-release)

### 3. Remove Deprecated Database Helper

Location: `src/giljo_mcp/database.py:337`

```python
DEPRECATED: Use select(model).where() directly with async sessions.
```

- [ ] Identify the deprecated method
- [ ] Search for any callers of this method
- [ ] Update callers to use `select(model).where()` directly
- [ ] Remove the deprecated method

### 4. Remove Commented Endpoint Registration

Location: `api/app.py:246`

```python
# {"name": "agents", "description": "DEPRECATED - Use agent-jobs instead"},
```

- [ ] Remove the commented-out line entirely
- [ ] Clean up any related commented code nearby

### 5. Update API Documentation

- [ ] Remove deprecated endpoints from OpenAPI schema
- [ ] Update any API documentation files
- [ ] Ensure Swagger UI doesn't show deprecated endpoints

## Verification

- [ ] All tests pass: `pytest tests/`
- [ ] API starts without errors: `python api/run_api.py`
- [ ] `/api/prompts/staging/{project_id}` works (replacement endpoint)
- [ ] MCP responses use `todo_items` not `progress`
- [ ] No DEPRECATED comments remain in endpoint files

## Risk Assessment

**MEDIUM** - API changes could affect any API consumers

**Mitigation:**
- Pre-release: no external API consumers
- All deprecated endpoints have documented replacements
- Test coverage should catch breaking changes

## Dependencies

- **Depends on:** None
- **Blocks:** None

## Estimated Impact

- **Lines removed:** ~100-150 (endpoint functions + related code)
- **Files modified:** 4-5
- **Endpoints removed:** 1-2
- **Response fields removed:** 1 (progress)
