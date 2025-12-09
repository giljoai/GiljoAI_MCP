# Handover 0336: Tech Stack Encoding and Token Estimation Fix

**Status**: READY FOR IMPLEMENTATION
**Priority**: HIGH
**Date**: 2025-12-09
**Related Handovers**: 0335 (CLI Mode), 0260 (CLI Toggle), 0246a-c (Token Optimization), 0302 (Tech Stack Formatting)

---

## Executive Summary

Two critical bugs discovered during prompt quality analysis:

1. **Tech Stack Character-by-Character Encoding (CRITICAL)**: Tech stack displays as comma-separated characters instead of words
2. **Token Estimation Mismatch (HIGH)**: Response shows ~11K tokens but mission contains ~40K tokens of vision content

Both bugs impact orchestrator prompt quality and user trust in token budgeting.

---

## Bug 1: Tech Stack Encoding (CRITICAL)

### Evidence

**Observed Output**:
```
**Languages**: P, y, t, h, o, n,  , 3, ., 1, 1, +
**Backend**: F, a, s, t, A, P, I
```

**Expected Output**:
```
**Languages**: Python 3.11+
**Backend**: FastAPI
```

### Root Cause

**File**: `src/giljo_mcp/mission_planner.py` (~line 1049)

**Problem Code**:
```python
# Line 1030
values = tech_stack.get(category, [])

# ... slicing logic ...

# Line 1049 - THE BUG
values_str = ", ".join(values)
```

**Why It Fails**:
- `tech_stack.get(category, [])` defaults to empty list but can return **string**
- When `values` is a string (e.g., `"Python 3.11+"`), `", ".join(values)` iterates over **characters**
- Python treats strings as iterables: `", ".join("Python")` → `"P, y, t, h, o, n"`

**Data Flow**:
```
Product.config_data (JSONB)
  └─ tech_stack: {
       "languages": "Python 3.11+",   ← STRING instead of LIST
       "backend": ["FastAPI"]          ← LIST (correct)
     }

MissionPlanner._format_tech_stack()
  └─ values = tech_stack.get("languages", [])
     └─ values = "Python 3.11+" (STRING!)
     └─ ", ".join(values)  → "P, y, t, h, o, n,  , 3, ., 1, 1, +"
```

### Fix

**Location**: `src/giljo_mcp/mission_planner.py:1049`

**Before**:
```python
# Join values with commas
values_str = ", ".join(values)
```

**After**:
```python
# Join values with commas - handle both string and list types
if isinstance(values, str):
    # Single string value - use directly
    values_str = values
else:
    # List of values - join with commas
    values_str = ", ".join(str(v) for v in values) if values else ""
```

**Why This Fix Works**:
- Type-safe: Handles both `str` and `list` inputs gracefully
- Backward-compatible: Existing list-based tech stacks still work
- Defensive: Converts list items to strings with `str(v)` for safety
- Zero-impact: No changes to normalization logic at line 1472-1477

---

## Bug 2: Token Estimation Mismatch (HIGH)

### Evidence

**API Response**:
```json
{
  "estimated_tokens": 11790,
  "mission": "... [~40K tokens of vision document content] ..."
}
```

**Actual Measurement**:
- Response `estimated_tokens`: 11,790 tokens
- Actual mission field: ~40,000 tokens (vision content included)
- **Discrepancy**: 3.4x underestimation

### Root Cause Analysis

**Suspected Source**: Token estimation happens **before** vision document expansion

**File**: `src/giljo_mcp/tools/tool_accessor.py:624`

```python
# Line 556 - Mission generation with context prioritization
condensed_mission = await planner._build_context_with_priorities(
    product=product,
    project=project,
    field_priorities=field_priorities,
    user_id=user_id,
    include_serena=include_serena
)

# Line 624 - Token estimation AFTER full mission built
estimated_tokens = len(condensed_mission) // 4
```

**Why It Might Fail**:
1. `_build_context_with_priorities()` may be including full vision chunks
2. Vision priority level causes large document inclusion
3. Token estimation is character-based (`len(condensed_mission) // 4`) which is inaccurate
4. Vision chunking in `context_fetcher.py` may not be respecting depth limits

**Data Flow to Investigate**:
```
get_orchestrator_instructions(orchestrator_id, tenant_key)
  └─ MissionPlanner._build_context_with_priorities()
     └─ Vision Documents section (field_priorities["vision_documents"])
        └─ ContextFetcher.fetch_vision_documents()  ← SUSPECT #1
           └─ Chunking logic may return full content
     └─ Token counting via _count_tokens()  ← SUSPECT #2
        └─ May not be used for final estimated_tokens
  └─ estimated_tokens = len(condensed_mission) // 4  ← SUSPECT #3
     └─ Character-based estimation vs actual token counting
```

### Investigation Required

**Files to Check**:
1. `src/giljo_mcp/mission_planner.py`
   - `_build_context_with_priorities()` method
   - Vision document section assembly (~line 1300-1400)
   - Token counting logic (`_count_tokens()` method)

2. `src/giljo_mcp/context/context_fetcher.py`
   - Vision document chunking logic
   - Depth level interpretation (none/light/moderate/heavy)
   - Token budget enforcement

3. `src/giljo_mcp/tools/tool_accessor.py`
   - Token estimation calculation (line 624)
   - Should use `planner._count_tokens()` instead of `len() // 4`

**Questions to Answer**:
- [ ] Does `_build_context_with_priorities()` include full vision content despite depth settings?
- [ ] Is `_count_tokens()` method accurate (tiktoken-based vs character-based)?
- [ ] Why does final `estimated_tokens` use `len() // 4` instead of tracked `total_tokens`?
- [ ] Does vision "moderate" depth level accidentally include ~30K tokens?

---

## Tasks Breakdown

### Task 1: Fix Tech Stack Character Encoding ✅ READY

**File**: `src/giljo_mcp/mission_planner.py`

**Changes**:
```python
# Line 1048-1049
# BEFORE:
# Join values with commas
values_str = ", ".join(values)

# AFTER:
# Join values with commas - handle both string and list types
if isinstance(values, str):
    # Single string value - use directly
    values_str = values
else:
    # List of values - join with commas
    values_str = ", ".join(str(v) for v in values) if values else ""
```

**Testing**:
```python
# Test case 1: String value (BUG SCENARIO)
tech_stack = {"languages": "Python 3.11+"}
result = planner._format_tech_stack(tech_stack, "full")
assert "**Languages**: Python 3.11+" in result
assert "P, y, t, h, o, n" not in result  # Should NOT split characters

# Test case 2: List value (EXISTING SCENARIO)
tech_stack = {"languages": ["Python", "TypeScript"]}
result = planner._format_tech_stack(tech_stack, "full")
assert "**Languages**: Python, TypeScript" in result

# Test case 3: Mixed types
tech_stack = {
    "languages": "Python 3.11+",           # String
    "backend": ["FastAPI", "PostgreSQL"]   # List
}
result = planner._format_tech_stack(tech_stack, "full")
assert "**Languages**: Python 3.11+" in result
assert "**Backend**: FastAPI, PostgreSQL" in result
```

**Success Criteria**:
- ✅ String values display without character splitting
- ✅ List values join with commas as before
- ✅ Mixed string/list tech stacks format correctly
- ✅ No regression in existing list-based tech stacks

---

### Task 2: Investigate Token Estimation Discrepancy

**Objective**: Find why `estimated_tokens: 11790` but mission has ~40K tokens

**Investigation Steps**:

1. **Measure actual token count of `condensed_mission` field**
   ```python
   # In tool_accessor.py after line 558
   import tiktoken

   encoder = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
   actual_tokens = len(encoder.encode(condensed_mission))

   logger.info(
       f"[TOKEN_AUDIT] Orchestrator {orchestrator_id}",
       extra={
           "condensed_mission_chars": len(condensed_mission),
           "estimated_tokens": len(condensed_mission) // 4,
           "actual_tokens": actual_tokens,
           "discrepancy_ratio": actual_tokens / (len(condensed_mission) // 4)
       }
   )
   ```

2. **Check vision document inclusion**
   ```python
   # In mission_planner.py _build_context_with_priorities()
   # After vision document section assembly

   if "vision_documents" in effective_priorities:
       vision_priority = effective_priorities["vision_documents"]
       vision_tokens = self._count_tokens(vision_section_content)

       logger.info(
           f"[VISION_AUDIT] Vision section included",
           extra={
               "priority": vision_priority,
               "depth_level": self._get_detail_level(vision_priority),
               "vision_tokens": vision_tokens,
               "vision_chars": len(vision_section_content)
           }
       )
   ```

3. **Verify `_count_tokens()` accuracy**
   ```python
   # Check if MissionPlanner._count_tokens() uses tiktoken or len() // 4
   # File: src/giljo_mcp/mission_planner.py

   # Search for _count_tokens definition
   # Verify it uses tiktoken encoder, not character-based estimation
   ```

4. **Compare tracked vs returned token count**
   ```python
   # In _build_context_with_priorities()
   # Check if total_tokens is tracked but not returned

   # Look for:
   # - total_tokens variable accumulation
   # - Whether it's included in return value
   # - Why tool_accessor.py doesn't use tracked total
   ```

**Files to Inspect**:
- `src/giljo_mcp/mission_planner.py:1300-1600` (vision section)
- `src/giljo_mcp/mission_planner.py:_count_tokens()` method
- `src/giljo_mcp/context/context_fetcher.py` (vision chunking)
- `src/giljo_mcp/tools/tool_accessor.py:624` (estimation logic)

**Success Criteria**:
- ✅ Identify exact source of 3.4x token discrepancy
- ✅ Understand why vision content inflates mission field
- ✅ Document correct token estimation approach

---

### Task 3: Fix Token Estimation Logic

**Depends on**: Task 2 findings

**Objective**: Make `estimated_tokens` match actual token count

**Potential Fixes** (based on investigation):

**Option A: Use tracked total_tokens**
```python
# File: src/giljo_mcp/tools/tool_accessor.py:624

# BEFORE:
estimated_tokens = len(condensed_mission) // 4

# AFTER:
# If planner tracks total_tokens, use that
estimated_tokens = total_tokens_from_planner  # From method return value
```

**Option B: Use accurate tiktoken counting**
```python
# File: src/giljo_mcp/tools/tool_accessor.py:624

# BEFORE:
estimated_tokens = len(condensed_mission) // 4

# AFTER:
import tiktoken
encoder = tiktoken.get_encoding("cl100k_base")
estimated_tokens = len(encoder.encode(condensed_mission))
```

**Option C: Fix vision depth interpretation**
```python
# File: src/giljo_mcp/mission_planner.py (vision section)

# Ensure "moderate" depth doesn't include 30K tokens
# Check depth → token budget mapping:
# - none: 0 tokens
# - light: ~5K tokens
# - moderate: ~10K tokens (NOT 30K!)
# - heavy: ~30K tokens
```

**Testing**:
```python
# Test case: Verify token estimation accuracy
orchestrator_id = create_test_orchestrator()
response = await tool_accessor.get_orchestrator_instructions(
    orchestrator_id=orchestrator_id,
    tenant_key=test_tenant
)

# Measure actual tokens
import tiktoken
encoder = tiktoken.get_encoding("cl100k_base")
actual_tokens = len(encoder.encode(response["mission"]))
estimated_tokens = response["estimated_tokens"]

# Verify accuracy within 10% margin
discrepancy_ratio = abs(actual_tokens - estimated_tokens) / actual_tokens
assert discrepancy_ratio < 0.1, f"Token estimation off by {discrepancy_ratio:.1%}"
```

**Success Criteria**:
- ✅ `estimated_tokens` accurate within ±10% of actual token count
- ✅ Vision depth levels enforce correct token budgets
- ✅ No performance regression from accurate token counting
- ✅ Logged token counts match API response

---

### Task 4: Add Integration Tests

**Objective**: Prevent regression of both bugs

**File**: `tests/integration/test_orchestrator_prompt_quality.py` (new)

**Test Cases**:

```python
import pytest
import tiktoken
from giljo_mcp.mission_planner import MissionPlanner


class TestTechStackFormatting:
    """Bug fix verification: Tech stack character encoding (0336)"""

    async def test_string_tech_stack_no_character_split(self, db_session):
        """Verify string tech stack values don't split into characters"""
        planner = MissionPlanner(db_manager)

        # Bug scenario: String value in tech stack
        tech_stack = {"languages": "Python 3.11+"}
        result = planner._format_tech_stack(tech_stack, "full")

        # Should NOT split into characters
        assert "P, y, t, h, o, n" not in result
        assert "**Languages**: Python 3.11+" in result

    async def test_list_tech_stack_joins_correctly(self, db_session):
        """Verify list tech stack values join with commas"""
        planner = MissionPlanner(db_manager)

        tech_stack = {"languages": ["Python", "TypeScript"]}
        result = planner._format_tech_stack(tech_stack, "full")

        assert "**Languages**: Python, TypeScript" in result

    async def test_mixed_string_list_tech_stack(self, db_session):
        """Verify mixed string/list tech stacks format correctly"""
        planner = MissionPlanner(db_manager)

        tech_stack = {
            "languages": "Python 3.11+",           # String
            "backend": ["FastAPI", "PostgreSQL"],  # List
            "frontend": "Vue 3"                    # String
        }
        result = planner._format_tech_stack(tech_stack, "full")

        # Check all formats correctly
        assert "**Languages**: Python 3.11+" in result
        assert "**Backend**: FastAPI, PostgreSQL" in result
        assert "**Frontend**: Vue 3" in result


class TestTokenEstimation:
    """Bug fix verification: Token estimation accuracy (0336)"""

    async def test_token_estimation_accuracy(self, db_session, test_product):
        """Verify estimated_tokens matches actual token count within 10%"""
        # Create orchestrator job
        orchestrator = create_test_orchestrator(
            product_id=test_product.id,
            field_priorities={"vision_documents": 2}  # Moderate vision
        )

        # Get instructions
        tool_accessor = ToolAccessor(db_manager, tenant_manager)
        response = await tool_accessor.get_orchestrator_instructions(
            orchestrator_id=orchestrator.job_id,
            tenant_key=test_product.tenant_key
        )

        # Measure actual tokens
        encoder = tiktoken.get_encoding("cl100k_base")
        actual_tokens = len(encoder.encode(response["mission"]))
        estimated_tokens = response["estimated_tokens"]

        # Verify accuracy within 10%
        discrepancy = abs(actual_tokens - estimated_tokens)
        discrepancy_ratio = discrepancy / actual_tokens

        assert discrepancy_ratio < 0.1, (
            f"Token estimation off by {discrepancy_ratio:.1%}: "
            f"estimated={estimated_tokens}, actual={actual_tokens}"
        )

    async def test_vision_depth_token_budgets(self, db_session, test_product):
        """Verify vision depth levels enforce correct token budgets"""
        depth_budgets = {
            1: (0, 100),          # none: ~0 tokens
            2: (3000, 7000),      # light: ~5K tokens
            3: (8000, 12000),     # moderate: ~10K tokens
            4: (25000, 35000),    # heavy: ~30K tokens
        }

        for priority, (min_tokens, max_tokens) in depth_budgets.items():
            orchestrator = create_test_orchestrator(
                product_id=test_product.id,
                field_priorities={"vision_documents": priority}
            )

            tool_accessor = ToolAccessor(db_manager, tenant_manager)
            response = await tool_accessor.get_orchestrator_instructions(
                orchestrator_id=orchestrator.job_id,
                tenant_key=test_product.tenant_key
            )

            # Extract vision section token count from logged metrics
            vision_tokens = extract_vision_tokens_from_logs()

            assert min_tokens <= vision_tokens <= max_tokens, (
                f"Priority {priority} vision tokens {vision_tokens} "
                f"outside expected range [{min_tokens}, {max_tokens}]"
            )
```

**Success Criteria**:
- ✅ All tests pass for tech stack encoding fix
- ✅ Token estimation accuracy verified
- ✅ Vision depth budgets enforced correctly
- ✅ Tests integrated into CI/CD pipeline

---

## Implementation Order

```
1. Task 1: Fix Tech Stack Character Encoding (IMMEDIATE - 10 min)
   └─ Single line change, high impact, no dependencies

2. Task 2: Investigate Token Estimation (RESEARCH - 1 hour)
   └─ Add logging, measure discrepancies, identify root cause

3. Task 3: Fix Token Estimation Logic (DEPENDS ON TASK 2 - 30 min)
   └─ Apply fix based on investigation findings

4. Task 4: Add Integration Tests (VALIDATION - 1 hour)
   └─ Prevent regression of both fixes
```

**Total Estimated Time**: 2.5 - 3 hours

---

## Files to Modify

### Primary Changes
- `src/giljo_mcp/mission_planner.py` (Task 1: line 1049 fix)
- `src/giljo_mcp/tools/tool_accessor.py` (Task 3: line 624 token estimation)

### Investigation (Task 2)
- `src/giljo_mcp/mission_planner.py` (`_build_context_with_priorities`, `_count_tokens`)
- `src/giljo_mcp/context/context_fetcher.py` (vision chunking)

### Testing (Task 4)
- `tests/integration/test_orchestrator_prompt_quality.py` (new file)

---

## Success Criteria

### Bug 1: Tech Stack Encoding
- ✅ Tech stack displays as `"Python 3.11+"` not `"P, y, t, h, o, n, ..."`
- ✅ Both string and list tech stack values format correctly
- ✅ No regression in existing list-based tech stacks
- ✅ Integration tests verify fix

### Bug 2: Token Estimation
- ✅ Root cause identified and documented
- ✅ `estimated_tokens` accurate within ±10% of actual count
- ✅ Vision depth levels enforce documented token budgets
- ✅ Token counting uses tiktoken (not character-based estimation)
- ✅ Integration tests verify accuracy

### Overall
- ✅ User trust restored in token budget reporting
- ✅ Orchestrator prompts display tech stack correctly
- ✅ No performance regression from accurate token counting
- ✅ Comprehensive test coverage prevents future regressions

---

## Related Documentation

**Reference Handovers**:
- **0246a-c**: Token Optimization Series (orchestrator workflow, thin prompts)
- **0302**: Tech Stack Formatting (normalization logic)
- **0335**: CLI Mode (template export, execution mode)
- **0260**: CLI Toggle (agent spawning constraints)

**Relevant Code Sections**:
- Tech stack normalization: `mission_planner.py:1472-1477`
- Tech stack formatting: `mission_planner.py:979-1053`
- Token estimation: `tool_accessor.py:624`
- Vision chunking: `context/context_fetcher.py`

**Testing Strategy**:
- Unit tests: `_format_tech_stack()` method with string/list inputs
- Integration tests: End-to-end token estimation accuracy
- Regression tests: Verify existing list-based tech stacks still work

---

## Notes

**Why This Matters**:
- **Tech Stack Bug**: Breaks user experience - looks like data corruption
- **Token Estimation Bug**: Undermines user trust in context budgeting system
- **Combined Impact**: Poor prompt quality affects orchestrator performance

**Migration Considerations**:
- Tech stack fix is backward-compatible (no data migration needed)
- Token estimation fix may reveal existing over-budget scenarios
- Should audit existing products for string vs list tech stack formats

**Future Enhancements**:
- Add validation to prevent string tech stack values at data entry
- Use tiktoken for all token counting (not just estimation)
- Add real-time token budget monitoring in UI

---

**END OF HANDOVER 0336**
