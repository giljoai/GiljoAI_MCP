# Handover 0711: Cleanup API MCP (CRITICAL)

**Date:** 2026-01-27
**From Agent:** orchestrator-coordinator
**To Agent:** database-expert / network-security-engineer
**Priority:** Critical
**Estimated Complexity:** 4-6 hours
**Status:** Not Started
**Depends On:** 0710 (API Lifecycle)

---

## Task Summary

**CRITICAL FILE**: Clean up `mcp_http.py` - the MCP-over-HTTP JSON-RPC endpoint that handles all MCP tool calls. This is one of the most critical files in the codebase.

**Risk Level:** CRITICAL (core MCP functionality)

**Scope:** 1-2 files

---

## Files In Scope

| File | Est. Lines | Risk | Function |
|------|-----------|------|----------|
| `api/mcp_http.py` | ~600 | Critical | MCP JSON-RPC handler |
| `api/endpoints/mcp/` | ~300 | High | MCP tool routing |

---

## Known Context (CLAUDE.md)

**HTTP-only MCP (Nov-Dec 2025):**
- MCP-over-HTTP JSON-RPC endpoint (`/mcp`) is authoritative
- Stdio/FastMCP code paths **removed** (Handover 0334)
- All clients use HTTP transport with `X-API-Key` authentication
- `get_agent_mission()` returns `full_protocol` field

---

## Pre-Cleanup: Critical Analysis

**REQUIRED before ANY changes:**

1. **Map all tool registrations:**
```bash
grep -n "register_tool\|@tool" api/mcp_http.py
```

2. **Map all JSON-RPC handlers:**
```bash
grep -n "def handle_\|async def handle_" api/mcp_http.py
```

3. **Verify authentication flow:**
```bash
grep -n "X-API-Key\|authenticate\|verify_token" api/mcp_http.py
```

4. **Check for DEPRECATED patterns:**
```bash
grep -n "DEPRECATED\|TODO\|FIXME\|stdio\|FastMCP" api/mcp_http.py
```

---

## Cleanup Checklist

### mcp_http.py

| Check | Action |
|-------|--------|
| Removed stdio code | Verify no stdio references remain |
| FastMCP references | Remove any remaining FastMCP code |
| DEPRECATED markers | Remove deprecated code paths |
| Error handling | Verify proper JSON-RPC error responses |
| Authentication | Verify X-API-Key validation |
| Tool registration | Verify all tools registered correctly |
| Logging | Remove excessive debug logging |
| Type hints | Add missing hints |

### Security Checks

| Check | Action |
|-------|--------|
| Input validation | Verify JSON-RPC params validated |
| Authentication bypass | Verify no unauthenticated paths |
| Tenant isolation | Verify tenant_key filtering |
| Error leakage | Verify errors don't leak internals |

---

## Implementation Plan

### Phase 1: Comprehensive Analysis (1 hr)
1. Read entire `mcp_http.py`
2. Document all tool registrations
3. Document all JSON-RPC methods
4. List DEPRECATED/TODO markers
5. Map authentication flow

### Phase 2: Dead Code Removal (1 hr)
1. Remove any stdio-related code
2. Remove any FastMCP references
3. Remove unused imports
4. Remove dead code paths

### Phase 3: Code Quality (1 hr)
1. Run ruff with --fix
2. Run black
3. Add type hints to all functions
4. Add docstrings to handlers
5. Improve error messages

### Phase 4: Security Review (1 hr)
1. Verify authentication on all endpoints
2. Verify input validation
3. Verify tenant isolation
4. Review error responses

### Phase 5: Thorough Testing (1 hr)
```bash
# MCP endpoint tests
pytest tests/api/test_mcp*.py -v

# Integration tests
pytest tests/integration/test_mcp*.py -v

# Full API tests
pytest tests/api/ -v

# Full regression
pytest tests/ -x --tb=short
```

### Phase 6: Update Index
```sql
UPDATE cleanup_index
SET status = 'cleaned',
    last_cleaned_at = NOW(),
    notes = 'CRITICAL file cleaned - full security review completed'
WHERE file_path LIKE 'api/mcp%';
```

---

## Testing Requirements

### Mandatory Tests
- All MCP tool calls must work
- Authentication must be enforced
- Tenant isolation must be verified
- JSON-RPC error responses must be correct

### Manual Testing with Chrome Extension
1. Start server
2. Open dashboard in Chrome
3. Test MCP tool calls via extension
4. Verify responses are correct

### Test Commands
```bash
# Specific MCP tests
pytest tests/api/test_mcp_http.py -v

# Tool-specific tests
pytest tests/tools/ -v

# Full API suite
pytest tests/api/ -v
```

---

## Success Criteria

- [ ] No stdio/FastMCP code remaining
- [ ] 0 DEPRECATED markers
- [ ] 0 TODO markers
- [ ] All MCP tools functional
- [ ] Authentication enforced
- [ ] Tenant isolation verified
- [ ] All MCP tests pass
- [ ] All integration tests pass
- [ ] Full test suite passes
- [ ] cleanup_index updated

---

## Rollback Plan

**CRITICAL: Create backup branch:**
```bash
git checkout -b backup/pre-0711-mcp-cleanup
git checkout <working-branch>
```

If issues:
```bash
git checkout backup/pre-0711-mcp-cleanup -- api/mcp_http.py
```

---

## Post-Cleanup Verification

1. Start server: `python startup.py`
2. Open dashboard
3. Test orchestrator launch (uses MCP)
4. Verify agent spawning works
5. Verify message sending works
6. Check no console errors

---

## Next Handover

**0712_cleanup_frontend_common.md** - Begin frontend cleanup with common components.
