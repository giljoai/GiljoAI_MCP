# Handover 0710: Cleanup Models Agents (CRITICAL)

**Series:** 0700 Code Cleanup Series
**Date:** 2026-01-27 (Updated: 2026-02-07)
**From Agent:** orchestrator-coordinator
**To Agent:** database-expert
**Priority:** Critical
**Estimated Complexity:** 4-6 hours
**Status:** Pending
**Depends On:** 0709-SECURITY

---

## CRITICAL: Large File Handling

**Files over 20K tokens (~500+ lines) MUST be read in batches.** Do NOT skip large files.

```python
# Read large files in chunks of 200 lines:
Read(file_path, offset=0, limit=200)    # Lines 1-200
Read(file_path, offset=200, limit=200)  # Lines 201-400
```

---

## NOTE: Partial Work Already Done

Some items in this spec may have been addressed by earlier handovers:
- **0700c**: JSONB Field Cleanup (messages JSONB marked deprecated)
- **0706b**: agent_identity.py investigation (verdict: HEALTHY architecture)

Focus on remaining DEPRECATED/TODO markers not yet addressed.

---

## Task Summary

**CRITICAL FILE**: Clean up `agent_identity.py` - the most heavily imported model in the codebase with 8 DEPRECATED markers and 5 TODO markers.

**Risk Level:** CRITICAL (50+ dependents)

**Scope:** 2 files

---

## Files In Scope

| File | Est. Lines | Risk | Known Issues |
|------|-----------|------|--------------|
| `src/giljo_mcp/models/agent_identity.py` | ~400 | Critical | 8 DEPRECATED, 5 TODO |
| `src/giljo_mcp/models/agents.py` | ~150 | High | Related agent models |

---

## Known Issues (CLAUDE.md)

**AgentExecution Model:**
- `messages` JSONB column is DEPRECATED
- Counter columns are authoritative:
  - `messages_sent_count`
  - `messages_waiting_count`
  - `messages_read_count`
- Do NOT read/write to `messages` JSONB

---

## Pre-Cleanup: Full Dependency Analysis

**REQUIRED before ANY changes:**

```bash
# Find all files importing from agent_identity
grep -r "from.*agent_identity import" src/ api/ --include="*.py" | wc -l

# Find all files importing AgentExecution
grep -r "AgentExecution" src/ api/ --include="*.py" | wc -l

# Find all usages of deprecated messages field
grep -r "\.messages" src/ api/ --include="*.py" | grep -v "messages_.*_count"
```

Document exact count of usages before proceeding.

---

## Cleanup Checklist

### agent_identity.py

| Marker Type | Current Count | Target |
|-------------|---------------|--------|
| DEPRECATED | 8 | 0 (documented or removed) |
| TODO | 5 | 0 (converted to issues or resolved) |

**Known DEPRECATED items to address:**
1. `messages` JSONB field - Add removal timeline (v4.0)
2. Any legacy methods - Remove or migrate

**Known TODO items to address:**
1. Each TODO → Create GitHub issue OR resolve inline

### agents.py

| Check | Action |
|-------|--------|
| AgentTemplate model | Verify structure |
| AgentJob model | Verify status enum |
| Relationships | Verify cascades |

---

## Implementation Plan

### Phase 1: Comprehensive Analysis (1 hr)
1. Read entire `agent_identity.py`
2. List every DEPRECATED marker with line numbers
3. List every TODO marker with line numbers
4. Map all dependents
5. Create impact assessment

### Phase 2: Safe Removals (1 hr)
1. Remove code that is:
   - Clearly unused (no grep matches)
   - Behind DEPRECATED markers for >6 months
2. Each removal must have test verification

### Phase 3: Deprecation Documentation (1 hr)
1. For fields that CAN'T be removed yet:
   - Add clear docstring deprecation notice
   - Add removal version (v4.0)
   - Add migration guide reference
2. Update CLAUDE.md if needed

### Phase 4: TODO Resolution (1 hr)
1. For each TODO:
   - If quick fix (<15 min): Fix it
   - If larger: Create GitHub issue, remove TODO
   - If obsolete: Remove

### Phase 5: Thorough Testing (1 hr)
```bash
# Agent model tests
pytest tests/models/test_agent*.py -v

# Service tests that use agents
pytest tests/services/test_orchestration*.py -v
pytest tests/services/test_job*.py -v

# API endpoint tests
pytest tests/api/test_job*.py -v

# Full regression
pytest tests/ -x --tb=short
```

### Phase 6: Update Index
```sql
UPDATE cleanup_index
SET status = 'cleaned',
    last_cleaned_at = NOW(),
    deprecation_markers = <new_count>,
    todo_markers = 0,
    notes = 'CRITICAL file cleaned - verified with full test suite'
WHERE file_path LIKE 'src/giljo_mcp/models/agent%';
```

---

## Testing Requirements

### Mandatory Tests
- All agent-related tests must pass
- All orchestration tests must pass
- Full test suite must pass (no regressions)

### Verification Queries
```sql
-- Verify no code references deprecated messages JSONB
SELECT COUNT(*) FROM grep_results
WHERE pattern = '.messages' AND NOT pattern LIKE 'messages_%_count';
```

---

## Success Criteria

- [ ] All 8 DEPRECATED markers resolved (removed or documented with timeline)
- [ ] All 5 TODO markers resolved (fixed or converted to issues)
- [ ] Zero new lint warnings
- [ ] All agent tests pass
- [ ] All orchestration tests pass
- [ ] Full test suite passes
- [ ] cleanup_index updated
- [ ] CLAUDE.md updated if needed

---

## Rollback Plan

**CRITICAL: Create backup branch before starting:**

```bash
git checkout -b backup/pre-0706-cleanup
git checkout 0480-exception-handling-remediation
```

If issues arise:
```bash
git checkout backup/pre-0706-cleanup -- src/giljo_mcp/models/agent_identity.py src/giljo_mcp/models/agents.py
```

---

## Post-Cleanup Documentation

**Removed Code:**
- List each removed function/field with reason

**Documented Deprecations:**
- `messages` JSONB - Removal planned for v4.0
- [Add others]

**GitHub Issues Created:**
- #XXX - [TODO description]
- [Add others]

---

## Next Handover

**0714_cleanup_services_leaf.md** - Begin service layer cleanup with leaf services.
