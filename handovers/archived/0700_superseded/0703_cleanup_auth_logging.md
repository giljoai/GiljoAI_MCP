# Handover 0703: Cleanup Auth & Logging

**Date:** 2026-01-27
**From Agent:** orchestrator-coordinator
**To Agent:** tdd-implementor
**Priority:** Medium
**Estimated Complexity:** 2-3 hours
**Status:** Not Started
**Depends On:** 0700 (Index Creation)

---

## Task Summary

Continue cleanup with **low-risk utility layers**: authentication utilities and logging infrastructure. These are leaf-level modules with limited dependents.

**Scope:** 6 files (auth + logging)

---

## Files In Scope

### Auth Layer

| File | Est. Lines | Expected Changes |
|------|-----------|------------------|
| `src/giljo_mcp/auth/jwt_handler.py` | ~150 | Review token logic |
| `src/giljo_mcp/auth/__init__.py` | ~20 | Lint |

### Logging Layer

| File | Est. Lines | Expected Changes |
|------|-----------|------------------|
| `src/giljo_mcp/logging/error_codes.py` | ~100 | Review codes |
| `src/giljo_mcp/logging/__init__.py` | ~50 | Lint |

### Related Tests

| File | Purpose |
|------|---------|
| `tests/auth/test_jwt_handler.py` | JWT tests |
| `tests/logging/test_error_codes.py` | Error code tests |

---

## Cleanup Checklist (Per File)

### 1. Automated Linting
```bash
ruff check src/giljo_mcp/auth/ src/giljo_mcp/logging/ --fix
black src/giljo_mcp/auth/ src/giljo_mcp/logging/
```

### 2. Manual Review Checklist

**jwt_handler.py:**
| Check | Action |
|-------|--------|
| Hardcoded secrets | Must use env vars |
| Deprecated algorithms | Update to current standards |
| Expiry handling | Verify proper token lifetime |
| Error handling | Check for bare except clauses |

**error_codes.py:**
| Check | Action |
|-------|--------|
| Unused error codes | Remove if never referenced |
| Duplicate codes | Consolidate |
| Missing codes | Add if referenced but missing |
| Documentation | Ensure each code has description |

### 3. Verification Steps

```bash
# 1. Lint passes
ruff check src/giljo_mcp/auth/ src/giljo_mcp/logging/

# 2. Tests pass
pytest tests/auth/ tests/logging/ -v

# 3. Import check
python -c "from giljo_mcp.auth import *; from giljo_mcp.logging import *"
```

---

## Implementation Plan

### Phase 1: Automated Fixes (15 min)
1. Run ruff with `--fix`
2. Run black
3. Commit separately

### Phase 2: auth/ Manual Review (45 min)
1. Review `jwt_handler.py`
   - Verify no hardcoded secrets
   - Check algorithm is current (HS256 minimum)
   - Review token expiry logic
   - Check for DEPRECATED markers
2. Run auth tests

### Phase 3: logging/ Manual Review (45 min)
1. Review `error_codes.py`
   - Identify unused error codes
   - Verify all codes are documented
   - Check for duplicates
2. Run logging tests

### Phase 4: Update Index (15 min)
```sql
UPDATE cleanup_index
SET status = 'cleaned',
    last_cleaned_at = NOW(),
    deprecation_markers = 0,
    todo_markers = 0
WHERE file_path IN (
    'src/giljo_mcp/auth/jwt_handler.py',
    'src/giljo_mcp/auth/__init__.py',
    'src/giljo_mcp/logging/error_codes.py',
    'src/giljo_mcp/logging/__init__.py'
);
```

---

## Testing Requirements

### Existing Tests
- All tests in `tests/auth/` must pass
- All tests in `tests/logging/` must pass

### Security Regression
- Verify JWT creation/validation still works
- Verify error codes still map correctly

---

## Success Criteria

- [ ] ruff check passes with 0 warnings
- [ ] black produces no changes
- [ ] 0 DEPRECATED markers in scope
- [ ] 0 TODO markers in scope
- [ ] No hardcoded secrets
- [ ] All auth tests pass
- [ ] All logging tests pass
- [ ] cleanup_index updated

---

## Rollback Plan

```bash
git checkout HEAD~1 -- src/giljo_mcp/auth/ src/giljo_mcp/logging/
```

---

## Next Handover

**0704_cleanup_models_base.md** - Begin model layer cleanup with foundation files.
