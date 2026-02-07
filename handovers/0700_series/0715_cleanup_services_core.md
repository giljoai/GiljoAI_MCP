# Handover 0715: Cleanup Services Core

**Series:** 0700 Code Cleanup Series
**Date:** 2026-01-27 (Updated: 2026-02-07)
**From Agent:** orchestrator-coordinator
**To Agent:** database-expert / tdd-implementor
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** Pending
**Depends On:** 0714 (Services Leaf)

---

## CRITICAL: Large File Handling

**Files over 20K tokens (~500+ lines) MUST be read in batches.** Do NOT skip large files.

```python
# Read large files in chunks of 200 lines:
Read(file_path, offset=0, limit=200)    # Lines 1-200
Read(file_path, offset=200, limit=200)  # Lines 201-400
```

**Key large files:**
- `project_service.py` (~1500 lines)
- `orchestration_service.py` (~500 lines)

---

## NOTE: Partial Work Already Done

Some items may have been addressed:
- **0707-LINT**: Lint auto-fix and manual cleanup
- **0708-TYPES**: Type hint modernization
- **0700d**: Legacy succession cleanup

Focus on remaining TODO markers (especially 12 in orchestration_service.py).

---

## Task Summary

Clean up **core services**: the heavily-used services that orchestrate major functionality. These have high dependent counts and require careful validation.

**Risk Level:** High (many dependents, critical functionality)

**Scope:** ~5 files

---

## Files In Scope

| File | Est. Lines | Dependents | Known Issues |
|------|-----------|------------|--------------|
| `src/giljo_mcp/services/orchestration_service.py` | ~500 | ~25 | 12 TODO markers |
| `src/giljo_mcp/services/project_service.py` | ~400 | ~20 | Multi-method |
| `src/giljo_mcp/services/product_service.py` | ~300 | ~15 | Vision handling |
| `src/giljo_mcp/services/settings_service.py` | ~200 | ~10 | Config persistence |
| `src/giljo_mcp/services/context_service.py` | ~250 | ~12 | fetch_context |

---

## High-Priority Hotspot

**orchestration_service.py** has 12 TODO markers - highest in codebase.

Pre-cleanup analysis required:
```bash
grep -n "TODO" src/giljo_mcp/services/orchestration_service.py
```

---

## Cleanup Checklist

### orchestration_service.py (PRIORITY)

| Check | Action |
|-------|--------|
| 12 TODO markers | Each must be: fixed, converted to issue, or removed |
| Succession logic | Verify context tracking |
| Job spawning | Verify thin client pattern |
| Error handling | Check exception propagation |

### project_service.py

| Check | Action |
|-------|--------|
| Soft delete | Verify deleted_at pattern |
| Lifecycle methods | activate, deactivate, summary, launch |
| WebSocket events | Verify emission points |

### product_service.py

| Check | Action |
|-------|--------|
| Vision upload | Verify chunking (<25K tokens) |
| Memory management | Use normalized table |
| DEPRECATED JSONB | No direct access |

### settings_service.py

| Check | Action |
|-------|--------|
| Config persistence | Verify YAML handling |
| Default values | Verify sensible defaults |
| Validation | Check input validation |

### context_service.py

| Check | Action |
|-------|--------|
| fetch_context | Verify category handling |
| Depth config | Verify depth options |
| Token budgeting | Verify limits |

---

## Implementation Plan

### Phase 1: orchestration_service.py (2 hrs)
1. List all 12 TODOs with line numbers
2. For each TODO:
   - If <15 min fix: Fix it
   - If larger: Create GitHub issue
   - If obsolete: Remove
3. Review succession logic
4. Run orchestration tests

### Phase 2: project_service.py (1 hr)
1. Lint and format
2. Verify soft delete cascade
3. Review lifecycle methods
4. Run project tests

### Phase 3: product_service.py (45 min)
1. Lint and format
2. Verify vision chunking
3. Verify memory table usage
4. Run product tests

### Phase 4: settings_service.py (30 min)
1. Lint and format
2. Verify config handling
3. Run settings tests

### Phase 5: context_service.py (45 min)
1. Lint and format
2. Verify fetch_context categories
3. Run context tests

### Phase 6: Update Index
```sql
UPDATE cleanup_index
SET status = 'cleaned', last_cleaned_at = NOW()
WHERE file_path LIKE 'src/giljo_mcp/services/orchestration%'
   OR file_path LIKE 'src/giljo_mcp/services/project%'
   OR file_path LIKE 'src/giljo_mcp/services/product%'
   OR file_path LIKE 'src/giljo_mcp/services/settings%'
   OR file_path LIKE 'src/giljo_mcp/services/context%';
```

---

## Testing Requirements

```bash
# Core service tests
pytest tests/services/test_orchestration_service.py -v
pytest tests/services/test_project_service.py -v
pytest tests/services/test_product_service.py -v
pytest tests/services/test_settings_service.py -v
pytest tests/services/test_context_service.py -v

# Integration tests
pytest tests/integration/ -v

# Full regression (critical services)
pytest tests/ -x --tb=short
```

---

## Success Criteria

- [ ] orchestration_service.py: 0 TODO markers (from 12)
- [ ] All services: 0 DEPRECATED markers
- [ ] All services: Lint clean
- [ ] All service tests pass
- [ ] All integration tests pass
- [ ] cleanup_index updated

---

## Rollback Plan

```bash
git checkout HEAD~1 -- src/giljo_mcp/services/orchestration_service.py
git checkout HEAD~1 -- src/giljo_mcp/services/project_service.py
# etc.
```

---

## Next Handover

**0711** - API MCP Cleanup (already in chain).
