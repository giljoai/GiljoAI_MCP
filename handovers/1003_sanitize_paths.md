# Handover 1003: Sanitize Filesystem Paths

**Date**: 2025-12-18
**Status**: Pending
**Parent**: 1000 (Greptile Remediation)
**Risk**: LOW
**Tier**: 1 (Auto-Execute)
**Effort**: 2 hours

## Overview

Remove internal filesystem paths from API error messages to prevent information disclosure. This addresses a security finding where path validation errors expose server-side directory structures to clients.

## Mission

Sanitize all HTTP error responses that currently include filesystem paths by:
1. Removing path information from user-facing error messages
2. Preserving path details in server-side logs for debugging
3. Maintaining clear, actionable error messages for users

## Scope

### Files to Modify
- `src/giljo_mcp/services/product_service.py` (lines 1330-1348)

### Research Required
1. Use `mcp__serena__find_symbol` to locate `validate_project_path` function with body
2. Use `mcp__serena__search_for_pattern` to find all `HTTPException` instances that include path variables in detail messages
3. Check frontend code (Vue components) to verify no parsing dependencies on path-containing error messages

## Current Implementation

**Vulnerable Code Example** (product_service.py):
```python
raise HTTPException(status_code=400, detail=f"Project path does not exist: {path}")
raise HTTPException(status_code=400, detail=f"Project path is not a directory: {path}")
raise HTTPException(status_code=400, detail=f"Project path is not writable: {path}")
```

**Security Issue**: Exposes internal filesystem structure (e.g., `F:\GiljoAI_MCP\projects\xyz`) to API clients.

## Fixed Implementation

**Sanitized Code**:
```python
# Log path internally for debugging
logger.warning(f"Project path validation failed - does not exist: {path}")
# Return generic message to client
raise HTTPException(status_code=400, detail="Project path does not exist")

logger.warning(f"Project path validation failed - not a directory: {path}")
raise HTTPException(status_code=400, detail="Project path is not a directory")

logger.warning(f"Project path validation failed - not writable: {path}")
raise HTTPException(status_code=400, detail="Project path is not writable")
```

**Key Changes**:
- User-facing error messages contain no path information
- Server logs retain full path context via `logger.warning()`
- Error messages remain clear and actionable

## Implementation Steps

1. **Research Phase**
   - Locate all instances of path-containing HTTPException messages
   - Verify frontend components don't parse error message strings for paths
   - Identify any other services with similar patterns

2. **Code Changes**
   - Update `validate_project_path()` in `product_service.py`
   - Add `logger.warning()` calls before each HTTPException
   - Remove path interpolation from HTTPException detail strings

3. **Testing**
   - Run existing test suite: `pytest tests/services/test_product_service.py`
   - Manual verification: Trigger path validation errors and inspect HTTP responses
   - Verify server logs contain actual paths for debugging

## Verification Checklist

- [ ] No filesystem paths appear in HTTP error response bodies
- [ ] Server logs contain full path details for debugging
- [ ] All existing unit tests pass without modification
- [ ] Manual testing confirms user-facing error messages remain clear
- [ ] Frontend components handle sanitized error messages correctly

## Cascade Risk Assessment

**Risk Level**: LOW

**Rationale**:
- Changes only affect error message strings
- No API contract changes (status codes remain the same)
- Error semantics unchanged (same error types, just sanitized messages)

**Potential Impact**:
- Frontend error handling may need verification if it parses error message content
- Developer experience improved (cleaner logs via logger.warning)
- Security posture improved (no information disclosure)

## Success Criteria

- [ ] Zero filesystem paths exposed in API error responses
- [ ] Paths logged internally via Python logging framework
- [ ] All existing tests pass without modification
- [ ] Manual testing confirms no regression in error handling
- [ ] Frontend components handle errors correctly

## Related Handovers

- **Parent**: 1000 (Greptile Remediation Master Tracker)
- **Related**: 1001 (Secrets Management), 1002 (Auth Rate Limiting)

## Notes

- This is a Tier 1 auto-execute task (low risk, clear scope)
- Estimated effort: 2 hours (research, implementation, testing)
- No database schema changes required
- No frontend changes required (verified during research phase)
