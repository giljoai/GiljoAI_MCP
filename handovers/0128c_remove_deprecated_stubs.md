# Handover 0128c: Remove Deprecated Method Stubs

**Status:** Ready to Execute
**Priority:** P1 - MEDIUM
**Estimated Duration:** 1 day (6-8 hours)
**Agent Budget:** 75K tokens
**Depends On:** 0128a (Complete ✅)
**Blocks:** None (independent task)
**Created:** 2025-11-11

---

## Executive Summary

### The Problem

The codebase contains **~15+ deprecated method stubs** that return error messages instead of being removed entirely. These stubs exist in:

1. **tool_accessor.py** - 7 methods returning `{"error": "DEPRECATED"}`
2. **services/context_service.py** - 8 DEPRECATED references
3. **ContextService** (discovered in 0127d) - 5 additional deprecated methods

**Total:** ~20 deprecated method stubs to remove

### Why This Is Bad

**Error-returning stubs are worse than missing methods:**
```python
# BAD - Current state
def deprecated_method(self):
    return {"error": "DEPRECATED", "message": "Use new_method instead"}

# AI agent thinks: "This method exists and returns an error dict"
# Calls it, gets error, handles error gracefully
# Method appears to work, but doesn't do anything useful
```

```python
# GOOD - After removal
# (method doesn't exist)

# AI agent thinks: "Method doesn't exist"
# Gets AttributeError immediately
# Fails fast, forces using correct method
```

### The Goal

**Delete deprecated method stubs entirely** and let Python's AttributeError guide developers to the correct methods.

---

## 🎯 Objectives

### Primary Goals

1. **Remove Dead Code** - Delete all deprecated method stubs
2. **Fail Fast** - Let AttributeError guide developers immediately
3. **Clean Codebase** - No zombie code returning useless errors
4. **Verify No Usage** - Confirm methods aren't being called

### Success Criteria

- ✅ All 7 deprecated stubs removed from tool_accessor.py
- ✅ All 8 deprecated references removed from context_service.py
- ✅ All 5 ContextService stubs removed (if they exist)
- ✅ Zero grep results for deprecated error-returning methods
- ✅ Application starts and runs normally
- ✅ All tests pass (no tests should call deprecated methods)

---

## 📊 Current State Analysis

### File 1: tool_accessor.py (7 deprecated stubs)

**Location:** `src/giljo_mcp/tools/tool_accessor.py`

**Deprecated Methods (line numbers approximate):**

1. **Line 135** - Method returning DEPRECATED error
2. **Line 165** - Method returning DEPRECATED error
3. **Line 221** - Method returning DEPRECATED error
4. **Line 250** - Method returning DEPRECATED error
5. **Line 279** - Method returning DEPRECATED error
6. **Line 314** - Method returning DEPRECATED error
7. **Line 345** - Method returning DEPRECATED error

**Additional deprecated delegates:**
- Line 460-474: Methods delegating to ContextService (marked DEPRECATED)

### File 2: services/context_service.py (8 DEPRECATED references)

**Location:** `src/giljo_mcp/services/context_service.py`

Contains 8 occurrences of "DEPRECATED" markers - need to investigate if these are:
- Method stubs to remove
- Comments only
- Delegate methods

### File 3: ContextService (5 methods from 0127d discovery)

**Location:** TBD - need to locate actual ContextService class

Discovered during 0127d:
- 5 deprecated methods that return error messages
- Similar pattern to tool_accessor.py

---

## 🔧 Implementation Plan

### Phase 1: Discovery & Verification (1-2 hours)

**Step 1.1: List All Deprecated Methods**

```bash
# Find all methods returning DEPRECATED errors
grep -n '"error": "DEPRECATED"' src/giljo_mcp/tools/tool_accessor.py
grep -n "DEPRECATED" src/giljo_mcp/services/context_service.py

# Find the method names
grep -B 5 '"error": "DEPRECATED"' src/giljo_mcp/tools/tool_accessor.py | grep "def "
```

**Step 1.2: Verify No Usage**

For each deprecated method:
```bash
# Example for a method named "deprecated_method"
grep -r "deprecated_method" --include="*.py" src/ api/ tests/

# Should return ONLY the definition, not any calls
```

**Step 1.3: Document Replacement Methods**

For each deprecated method, note what it should be replaced with (usually in the error message or docstring).

### Phase 2: Remove from tool_accessor.py (2-3 hours)

**Step 2.1: Identify Each Method**

Read tool_accessor.py and identify the 7 methods completely:
- Method name
- Line range (where method starts/ends)
- What it's been replaced with

**Step 2.2: Remove Methods One by One**

For each method:

```python
# BEFORE - Example deprecated method:
async def spawn_workflow(self, ...):
    """
    Spawn workflow.

    DEPRECATED: Use spawn_agent_job() instead.
    """
    return {
        "error": "DEPRECATED",
        "message": "Use spawn_agent_job() instead",
        "replacement": "spawn_agent_job"
    }

# AFTER:
# (method removed entirely - just delete the whole method)
```

**Step 2.3: Update Method Counts**

After each removal, verify file still has valid Python syntax:
```bash
python -m py_compile src/giljo_mcp/tools/tool_accessor.py
```

### Phase 3: Clean context_service.py (1-2 hours)

**Step 3.1: Investigate DEPRECATED References**

```bash
# View the context
grep -B 3 -A 3 "DEPRECATED" src/giljo_mcp/services/context_service.py
```

**Possible scenarios:**
1. **Error-returning stubs** → Delete entirely
2. **Delegate methods with DEPRECATED marker** → Remove if not used
3. **Just comments** → Update or remove comments

**Step 3.2: Remove Stubs or Clean Comments**

Depending on what's found:
- If stubs: Delete methods entirely
- If delegates not used: Delete
- If just comments: Clean up or remove

### Phase 4: Locate and Clean ContextService (1-2 hours)

**Step 4.1: Find ContextService**

```bash
# Find where ContextService is defined
find . -name "*.py" -exec grep -l "class ContextService" {} \;
```

**Step 4.2: Remove 5 Deprecated Methods**

Same pattern as tool_accessor.py - remove methods entirely.

### Phase 5: Verification (1-2 hours)

**Step 5.1: Syntax Check**

```bash
# Verify all Python files compile
python -m py_compile src/giljo_mcp/tools/tool_accessor.py
python -m py_compile src/giljo_mcp/services/context_service.py

# Or check all
find src/ -name "*.py" -exec python -m py_compile {} \;
```

**Step 5.2: Search for Remaining Deprecated Stubs**

```bash
# Should return zero results
grep -r '"error": "DEPRECATED"' --include="*.py" src/ api/
grep -r 'return.*DEPRECATED' --include="*.py" src/ api/
```

**Step 5.3: Run Application**

```bash
# Application should start normally
python startup.py --dev

# Check logs for any AttributeErrors (expected if code was calling deprecated methods)
```

**Step 5.4: Run Tests**

```bash
# Full test suite
pytest tests/

# If any failures, they're tests calling deprecated methods
# Update those tests to use replacement methods
```

### Phase 6: Test Cleanup (if needed) (1-2 hours)

**If tests fail because they call deprecated methods:**

```python
# Example test fix:
# BEFORE:
result = tool_accessor.spawn_workflow(...)
assert result["error"] == "DEPRECATED"

# AFTER:
# Test deleted (was testing deprecated method)
# Or updated to test replacement method:
result = await tool_accessor.spawn_agent_job(...)
assert result["success"] is True
```

### Phase 7: Documentation (30 minutes)

**Step 7.1: Update CHANGELOG.md**

```markdown
## [Unreleased] - Handover 0128c

### Removed
- 7 deprecated method stubs from tool_accessor.py
- 8 deprecated references from context_service.py
- 5 deprecated methods from ContextService
- Total: ~20 error-returning stubs removed

### Changed
- Methods now fail fast with AttributeError instead of returning error dicts
- Cleaner codebase without zombie code

### Note
Any code calling these deprecated methods will now get AttributeError immediately,
guiding developers to use the correct replacement methods.
```

---

## 📋 Validation Checklist

- [ ] All deprecated methods identified and listed
- [ ] Verified no code calls these methods
- [ ] Removed 7 stubs from tool_accessor.py
- [ ] Cleaned 8 references from context_service.py
- [ ] Removed 5 ContextService methods
- [ ] Zero grep results for deprecated error-returning stubs
- [ ] All Python files compile successfully
- [ ] Application starts normally
- [ ] Test suite passes (or deprecated tests removed/updated)
- [ ] CHANGELOG.md updated

---

## ⚠️ Risk Assessment

**Risk 1: Code Still Calls Deprecated Methods**
- **Impact:** HIGH (application breaks)
- **Probability:** LOW (we verify with grep first)
- **Mitigation:** Thorough grep search before removal

**Risk 2: Tests Call Deprecated Methods**
- **Impact:** MEDIUM (tests fail)
- **Probability:** MEDIUM (some tests might)
- **Mitigation:** Run tests, update as needed

**Risk 3: Missing a Deprecated Method**
- **Impact:** LOW (just means more cleanup later)
- **Probability:** LOW (comprehensive grep)
- **Mitigation:** Search with multiple patterns

**Overall Risk: LOW-MEDIUM**

This is straightforward code deletion with good verification steps.

---

## 🔄 Rollback Plan

```bash
# If issues discovered after removal:

# 1. Revert git changes
git reset --hard <commit-before-0128c>

# 2. Restart application
python startup.py --dev

# 3. Fix broken code that was calling deprecated methods
# (This is actually the RIGHT thing to do - update to use correct methods)
```

**Better approach if code breaks:**
Fix the calling code to use replacement methods instead of rolling back.

---

## 📊 Expected Outcomes

### Before 0128c
```
Deprecated stubs: ~20 methods
Code clarity: Cluttered with zombie code
Fail fast: NO (returns error dicts)
AI agent confusion: HIGH (methods "work" but do nothing)
Codebase health: 70%
```

### After 0128c
```
Deprecated stubs: 0 methods
Code clarity: Clean, no dead code
Fail fast: YES (AttributeError immediately)
AI agent confusion: ELIMINATED (methods don't exist)
Codebase health: 95%
```

### Quantitative Impact
- **Methods removed:** ~20 deprecated stubs
- **Lines removed:** ~200-300 lines of dead code
- **Files cleaned:** 3 files (tool_accessor.py, context_service.py, ContextService)
- **Clarity improvement:** Immediate

---

## 🎯 Success Metrics

**Code Metrics:**
- Zero methods returning `{"error": "DEPRECATED"}`
- ~200-300 lines of dead code removed
- 3 files cleaned

**Operational Metrics:**
- Application starts normally
- Tests pass (or deprecated tests removed)
- No zombie code remains

**Quality Metrics:**
- Fail fast principle enforced
- AI agents can't call non-existent methods
- Codebase is cleaner and more maintainable

---

## 📝 Notes for Implementers

### Why Removing Is Better Than Marking

**Marking as deprecated but keeping method:**
```python
def old_method(self):
    return {"error": "DEPRECATED"}
```
- Method exists in code
- AI agents may call it
- Returns error that might be handled
- Clutters codebase

**Removing entirely:**
```python
# old_method removed
```
- Method doesn't exist
- Raises AttributeError immediately
- Forces correct method usage
- Clean codebase

### Testing Strategy

1. **Before removal:** Grep to verify no usage
2. **After removal:** Run tests to catch any missed calls
3. **Fix calling code:** Update to use replacement methods
4. **Document removals:** CHANGELOG.md

### Common Replacement Patterns

From tool_accessor.py stubs:
- `spawn_workflow()` → `spawn_agent_job()`
- `get_job_status()` → `get_workflow_status()`
- `retire_agent()` → Handled automatically in job lifecycle

---

## 🔗 Related Handovers

- **0128a:** Split models.py (COMPLETE) - No dependency
- **0128b:** Rename auth_legacy.py - No dependency, can run in parallel
- **0128e:** Vision field migration - No dependency, can run in parallel
- **0128d:** Drop database fields - No dependency

**This task is completely independent and can run in parallel with 0128b or 0128e.**

---

## 🏁 Ready to Execute

**Next Steps:**
1. Execute Phase 1 (discovery & verification)
2. Execute Phase 2 (clean tool_accessor.py)
3. Execute Phase 3 (clean context_service.py)
4. Execute Phase 4 (clean ContextService)
5. Execute Phase 5 (verification)
6. Execute Phase 6 (test cleanup if needed)
7. Execute Phase 7 (documentation)

**Remember:** Removing dead code is a **quality improvement** that makes the codebase cleaner and enforces fail-fast principles.

---

**Document Version:** 1.0
**Created:** 2025-11-11
**Priority:** P1 - MEDIUM
**Status:** Ready for Execution
**Estimated Completion:** 6-8 hours with thorough testing