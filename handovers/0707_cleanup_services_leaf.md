# Handover 0707: Cleanup Services Leaf

**Date:** 2026-01-27
**From Agent:** orchestrator-coordinator
**To Agent:** tdd-implementor
**Priority:** Medium
**Estimated Complexity:** 3-4 hours
**Status:** Not Started
**Depends On:** 0706 (Models Agents)

---

## Task Summary

Clean up **leaf-level services**: services with few dependents that can be safely modified without widespread impact.

**Risk Level:** Medium (limited dependents)

**Scope:** ~5 files

---

## Files In Scope

| File | Est. Lines | Dependents | Expected Changes |
|------|-----------|------------|------------------|
| `src/giljo_mcp/services/git_service.py` | ~150 | ~5 | Review Git operations |
| `src/giljo_mcp/services/serena_detector.py` | ~100 | ~3 | Review detection logic |
| `src/giljo_mcp/services/template_service.py` | ~200 | ~8 | Check DEPRECATED |
| `src/giljo_mcp/services/task_service.py` | ~150 | ~6 | Review task handling |
| `src/giljo_mcp/services/message_service.py` | ~200 | ~10 | Counter-based cleanup |

---

## Known Issues (CLAUDE.md)

**template_service.py:**
- May have DEPRECATED markers from old template system
- `mission_templates.py` is deprecated - verify no references

**message_service.py:**
- Counter-based architecture (0387i)
- `AgentExecution.messages` JSONB is deprecated
- Must use counter columns only

---

## Cleanup Checklist

### Per Service File

| Check | Action |
|-------|--------|
| DEPRECATED markers | Remove code or document timeline |
| TODO markers | Fix or convert to issues |
| Unused methods | Remove if no callers |
| Error handling | Check for bare except |
| Logging | Remove excessive debug logs |
| Type hints | Add missing hints |
| Docstrings | Add for public methods |

---

## Implementation Plan

### Phase 1: git_service.py (30 min)
1. Lint and format
2. Review Git command invocations
3. Check for hardcoded paths
4. Run git-related tests

### Phase 2: serena_detector.py (30 min)
1. Lint and format
2. Review detection logic
3. Verify no outdated patterns
4. Run detection tests

### Phase 3: template_service.py (45 min)
1. Lint and format
2. Check for references to deprecated `mission_templates.py`
3. Verify template manager usage
4. Run template tests

### Phase 4: task_service.py (30 min)
1. Lint and format
2. Review task lifecycle
3. Check status transitions
4. Run task tests

### Phase 5: message_service.py (45 min)
1. Lint and format
2. **CRITICAL**: Verify no reads/writes to messages JSONB
3. Verify counter-based operations only
4. Run message tests

### Phase 6: Update Index
```sql
UPDATE cleanup_index
SET status = 'cleaned', last_cleaned_at = NOW()
WHERE file_path LIKE 'src/giljo_mcp/services/git%'
   OR file_path LIKE 'src/giljo_mcp/services/serena%'
   OR file_path LIKE 'src/giljo_mcp/services/template%'
   OR file_path LIKE 'src/giljo_mcp/services/task%'
   OR file_path LIKE 'src/giljo_mcp/services/message%';
```

---

## Testing Requirements

```bash
# Service-specific tests
pytest tests/services/test_git_service.py -v
pytest tests/services/test_template_service.py -v
pytest tests/services/test_task_service.py -v
pytest tests/services/test_message_service.py -v

# Integration tests
pytest tests/integration/ -v -k "git or template or task or message"
```

---

## Success Criteria

- [ ] All lint warnings resolved
- [ ] 0 DEPRECATED markers (or documented with timeline)
- [ ] 0 TODO markers
- [ ] No references to deprecated message JSONB
- [ ] All service tests pass
- [ ] cleanup_index updated

---

## Next Handover

**0708_cleanup_services_core.md** - Clean up core services (orchestration_service, project_service).
