# Handover 0258: ThinClientPromptGenerator Async/Await Bug Fix

**Date**: 2025-11-29
**Status**: READY FOR IMPLEMENTATION
**Priority**: MEDIUM
**Type**: Bug Fix / Testing
**Estimated Time**: 1-2 hours
**Discovered During**: Handover 0255 test validation

---

## Executive Summary

**Problem**: Tests in `test_prompt_injection_git.py` are calling async method `ThinClientPromptGenerator._build_thin_prompt_with_memory()` without awaiting it, causing coroutine-not-awaited errors.

**Impact**: 5 tests failing with `TypeError: argument of type 'coroutine' is not iterable` and runtime warnings about unawaited coroutines.

**Root Cause**: Test code not properly handling async method calls - either tests need `await` or the method should not be async.

---

## Problem Statement

During test validation of Handover 0255 (Git MCP Tools Cleanup), 5 tests failed in `test_prompt_injection_git.py`:

### Failed Tests

1. `TestMemoryInjection::test_inject_360_memory_with_learnings`
2. `TestCombinedInjection::test_orchestrator_prompt_includes_both_when_git_enabled`
3. `TestCombinedInjection::test_orchestrator_prompt_only_memory_when_git_disabled`
4. `TestCombinedInjection::test_prompt_injection_preserves_existing_sections`
5. `TestPromptIntegration::test_full_prompt_generation_with_git_enabled`

### Error Pattern

```python
RuntimeWarning: coroutine 'ThinClientPromptGenerator._build_thin_prompt_with_memory' was never awaited
```

```python
# Test code
prompt = generator._build_thin_prompt_with_memory(...)  # Missing await!

# Error
assert "360 Memory" in prompt  # TypeError: argument of type 'coroutine' is not iterable
```

---

## Investigation Required

### 1. Check Method Signature

**File**: `src/giljo_mcp/thin_prompt_generator.py`

Questions:
- Is `_build_thin_prompt_with_memory()` defined as `async def`?
- Does it need to be async? (database calls, I/O operations)
- Are there sync wrapper methods available?

### 2. Review Test Patterns

**File**: `tests/unit/test_prompt_injection_git.py`

Check:
- Are tests marked with `@pytest.mark.asyncio`?
- Are generator method calls using `await`?
- Are there examples of correctly calling async generator methods?

### 3. Check Similar Tests

Search for other tests that call `ThinClientPromptGenerator` methods:
- `tests/services/test_thin_client_prompt_generator_agent_templates.py`
- `tests/services/test_thin_prompt_generator_deprecation.py`
- `tests/thin_prompt/test_thin_prompt_unit.py`

Pattern check: How do they handle async methods?

---

## Possible Solutions

### Option A: Add `await` to Test Calls (Recommended)

If the method genuinely needs to be async (e.g., database queries):

```python
# Before (broken)
prompt = generator._build_thin_prompt_with_memory(...)

# After (fixed)
prompt = await generator._build_thin_prompt_with_memory(...)
```

**Requirements**:
- Tests must be marked `@pytest.mark.asyncio`
- Test fixtures must support async context

### Option B: Create Sync Wrapper Method

If tests need synchronous access:

```python
# In ThinClientPromptGenerator
def _build_thin_prompt_with_memory_sync(self, ...):
    """Synchronous wrapper for testing."""
    return asyncio.run(self._build_thin_prompt_with_memory(...))
```

### Option C: Make Method Synchronous

If the method doesn't actually need async (no I/O, no DB calls):

```python
# Change from:
async def _build_thin_prompt_with_memory(self, ...):
    ...

# To:
def _build_thin_prompt_with_memory(self, ...):
    ...
```

**Risk**: May break other code if method is called with `await` elsewhere.

---

## Implementation Plan

### Phase 1 - Investigation

1. Read `src/giljo_mcp/thin_prompt_generator.py`
2. Find `_build_thin_prompt_with_memory()` method
3. Check if it contains async operations:
   - Database queries (`await session.execute(...)`)
   - Async I/O (`await file.read()`)
   - Other async method calls
4. Identify why it's async (genuine need vs. legacy pattern)

### Phase 2 - Review Test Structure

1. Read `tests/unit/test_prompt_injection_git.py`
2. Check test decorators and fixtures
3. Compare with working thin prompt generator tests
4. Identify pattern to follow

### Phase 3 - Implement Fix

**If method needs to be async** (Option A):
1. Add `await` to all test calls
2. Ensure tests are marked `@pytest.mark.asyncio`
3. Verify fixtures support async context

**If method can be sync** (Option C):
1. Remove `async` from method definition
2. Remove any `await` calls inside method
3. Update any callers that use `await` on this method

**If sync wrapper needed** (Option B):
1. Create `_build_thin_prompt_with_memory_sync()` wrapper
2. Update tests to use sync wrapper
3. Keep async method for production use

### Phase 4 - Test Validation

1. Run failing tests:
   ```bash
   pytest tests/unit/test_prompt_injection_git.py -v
   ```

2. Expected: 20 passed, 0 failed (currently 15 passed, 5 failed)

3. Run all thin prompt generator tests:
   ```bash
   pytest tests/services/test_thin_client_prompt_generator_agent_templates.py -v
   pytest tests/services/test_thin_prompt_generator_deprecation.py -v
   pytest tests/thin_prompt/ -v
   ```

4. Check for coroutine warnings:
   ```bash
   pytest tests/unit/test_prompt_injection_git.py -W error::RuntimeWarning
   ```

---

## Related Files

**Source Code**:
- `src/giljo_mcp/thin_prompt_generator.py`
- `src/giljo_mcp/services/context_service.py` (if called from there)

**Tests**:
- `tests/unit/test_prompt_injection_git.py` (failing tests)
- `tests/services/test_thin_client_prompt_generator_agent_templates.py`
- `tests/services/test_thin_prompt_generator_deprecation.py`
- `tests/thin_prompt/test_thin_prompt_unit.py`

**Documentation**:
- `docs/TESTING.md`
- `docs/guides/thin_client_migration_guide.md`

---

## Test Failure Details

### Test 1: `test_inject_360_memory_with_learnings`

```python
# Expected: Memory section shows "2" learnings
# Actual: Memory section says "No previous project history yet"
assert "2" in memory_section or "two" in memory_section.lower()
# AssertionError
```

**Note**: This might be related to Handover 0257 (ProductService learning bug).

### Tests 2-5: Coroutine Not Awaited

```python
prompt = generator._build_thin_prompt_with_memory(...)  # Returns coroutine
assert "360 Memory" in prompt  # TypeError: can't check 'in' on coroutine
```

**Clear fix**: Add `await` before method call.

---

## Acceptance Criteria

1. ✅ All 20 tests in `test_prompt_injection_git.py` pass (currently 15/20)
2. ✅ No coroutine-not-awaited runtime warnings
3. ✅ Async/sync pattern is consistent across all prompt generator tests
4. ✅ No regressions in other thin prompt generator tests
5. ✅ Code follows pytest async best practices

---

## Notes

- This bug is **unrelated** to the git MCP tools cleanup (Handover 0255)
- Bug was discovered during test validation phase
- Likely a pre-existing test issue, not a production bug
- May reveal patterns to fix in other test files
- Related to Handover 0257 (ProductService learning bug) - some assertions may depend on that fix
