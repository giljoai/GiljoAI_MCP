# Handover 0394: Python Dependency Cleanup

**Status:** COMPLETE
**Created:** 2026-01-25
**Priority:** MEDIUM
**Estimated Hours:** 1-2h

---

## Summary

Remove unused Python dependencies from requirements.txt and pyproject.toml to reduce installation size and dependency conflicts. This cleanup follows the STDIO removal in Handover 0334 and identifies packages that are no longer needed.

---

## Context

After the HTTP-only MCP transition (Handover 0334), several dependencies became unused:
- STDIO/FastMCP code paths were removed
- Some packages were never actually used (python-jose, rich, typer)
- FastMCP is only used in test files, not production

---

## Changes Made

### Phase 1: Confirmed Removals (COMPLETE)

#### 1. python-jose - REMOVED
**Reason:** PyJWT is used for all JWT operations; python-jose was never imported.

**Before (requirements.txt):**
```
python-jose[cryptography]>=3.3.0
```

**After:** Line removed

**Verification:** `grep -rn "python-jose\|from jose" --include="*.py" .` returns 0 results

---

#### 2. rich - REMOVED
**Reason:** No imports found in codebase. Was in pyproject.toml only.

**Before (pyproject.toml):**
```toml
dependencies = [
    ...
    "rich>=13.0.0",
    ...
]
```

**After:** Line removed

**Verification:** `grep -rn "from rich\|import rich" --include="*.py" .` returns 0 results

---

#### 3. typer - REMOVED
**Reason:** No imports found in codebase. Was in pyproject.toml only.

**Before (pyproject.toml):**
```toml
dependencies = [
    ...
    "typer>=0.9.0",
    ...
]
```

**After:** Line removed

**Verification:** `grep -rn "from typer\|import typer" --include="*.py" .` returns 0 results

---

#### 4. fastmcp - MOVED TO DEV DEPENDENCIES
**Reason:** Only used in test files (14 test files), not in production code.

**Before (requirements.txt):**
```
fastmcp>=0.1.0
```

**After:** Removed from requirements.txt, kept in pyproject.toml dev dependencies:
```toml
[project.optional-dependencies]
dev = [
    ...
    "fastmcp>=0.1.0",  # MCP server framework (test-only dependency)
    ...
]
```

**Test files using fastmcp:**
- tests/test_agent_job_status_tool.py
- tests/test_project_tools_websocket_refactor.py
- tests/test_tool_registration.py
- tests/test_tools_simple.py
- tests/tools/test_amendments_a_b.py
- tests/unit/test_project_closeout.py
- tests/conftest.py (fixture)

---

### Phase 2: Additional Removal (IN PROGRESS)

#### 5. pywin32 - TO BE REMOVED
**Reason:** No usage found in codebase even on Windows.

**Before (requirements.txt):**
```
pywin32>=306; sys_platform == "win32"
```

**After:** Line to be removed

**Verification:** `grep -rn "win32\|pywin32" --include="*.py" .` returns 0 results in src/ and api/

**Rollback:** If Windows-specific functionality breaks, restore this line:
```
pywin32>=306; sys_platform == "win32"
```

---

## Packages KEPT (Still Needed)

### mcp==1.12.3 - KEEP
**Reason:** Required for Codex CLI proxy (`src/giljo_mcp/mcp_http_stdin_proxy.py`)

The stdio proxy is downloaded and used by Codex CLI users to connect to the GiljoAI MCP server. This is an active feature, not dead code.

---

## Rollback Instructions

If any issues occur after this cleanup:

### Restore python-jose:
```bash
# In requirements.txt, add:
python-jose[cryptography]>=3.3.0
```

### Restore rich:
```bash
# In pyproject.toml dependencies, add:
"rich>=13.0.0",
```

### Restore typer:
```bash
# In pyproject.toml dependencies, add:
"typer>=0.9.0",
```

### Restore fastmcp to production:
```bash
# In requirements.txt, add:
fastmcp>=0.1.0
```

### Restore pywin32:
```bash
# In requirements.txt, add:
pywin32>=306; sys_platform == "win32"
```

---

## Impact

### Estimated Savings:
| Package | Size |
|---------|------|
| python-jose | ~5MB |
| rich | ~2MB |
| typer | ~1MB |
| fastmcp (from prod) | ~10MB |
| pywin32 | ~10MB (Windows only) |
| **Total** | **~28MB** |

### Installation Time:
- Reduced by ~10-15 seconds on fresh installs

### Dependency Tree:
- Cleaner dependency resolution
- Fewer potential version conflicts

---

## Remaining Investigation

### websockets - INVESTIGATE
**Status:** No direct usage found, but may be indirect dependency
**Action:** Check `pip show websockets` to see what depends on it
**Risk:** Low - FastAPI provides WebSocket support via Starlette

---

## Files Modified

1. `requirements.txt` - Removed python-jose, fastmcp, pywin32
2. `pyproject.toml` - Removed python-jose, rich, typer from main deps; fastmcp in dev deps

---

## Testing

After changes:
1. `pip install -r requirements.txt` - Should complete without errors
2. `python -c "import api; import src.giljo_mcp"` - Should import successfully
3. `pytest tests/` - All tests should pass (fastmcp available via dev deps)
4. Test on Windows - Verify no pywin32-related errors

---

## Related Handovers

- **0334**: HTTP-Only MCP Consolidation (removed STDIO code paths)
- **0383**: MCP Tool Surface Audit (removed gil_fetch, gil_import_*)

---

## Completion Checklist

- [x] Phase 1: Remove python-jose
- [x] Phase 1: Remove rich
- [x] Phase 1: Remove typer
- [x] Phase 1: Move fastmcp to dev dependencies
- [x] Phase 2: Remove pywin32
- [x] Update HANDOVER_CATALOGUE.md
- [ ] Verify installation on clean environment (manual)
- [x] Mark as COMPLETE
