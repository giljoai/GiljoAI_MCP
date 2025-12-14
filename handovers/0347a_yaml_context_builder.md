# Handover 0347a: YAML Context Builder Utility Class

---

## Metadata

**Date**: 2025-12-14
**From Agent**: Documentation Manager (handover preparation)
**To Agent**: TDD Implementor
**Priority**: HIGH
**Complexity**: MEDIUM
**Estimated Effort**: 2 hours
**Status**: READY FOR EXECUTION

**Related Handovers**:
- Parent: `0347_mission_response_yaml_restructuring.md` (Mission YAML restructuring initiative)
- Siblings: 0347b (ProductService migration), 0347c (Orchestrator integration)

**Dependencies**:
- PyYAML library (already in requirements.txt)
- Python 3.11+ type hints
- pytest for testing

---

## Task Summary

Create a YAML Context Builder utility class (`YAMLContextBuilder`) that generates structured YAML
output with explicit priority framing for GiljoAI MCP orchestrator missions. This builder replaces
markdown blob context with prioritized sections (CRITICAL/IMPORTANT/REFERENCE), reducing mission
tokens from ~21,000 to ~1,500 (93% reduction) while improving Claude Code parsing efficiency.

**Core Goal**: Provide a clean, testable API for building priority-framed YAML context that enables
fetch-on-demand patterns for reference content.

---

## Context and Background

### Problem Statement

Current orchestrator missions use markdown blob format with ~21,000 tokens of inline context:
- All context fields embedded regardless of user priority settings
- No clear visual priority hierarchy for Claude Code
- Reference content (vision docs, 360 memory) inlined when summaries would suffice
- Poor parsing efficiency due to freeform markdown structure

### Solution Overview

The YAML Context Builder introduces a structured approach:

1. **Priority Map** (read-first): Declares which fields are CRITICAL/IMPORTANT/REFERENCE
2. **Tiered Sections**: Organizes content by priority with visual separators
3. **Fetch Pointers**: Reference sections include summary + fetch tool name
4. **Token Estimation**: Built-in method to validate mission stays under budget

### Architecture Pattern

This utility follows the **Builder Pattern**:
- Fluent interface for adding fields and content
- Separation of construction (builder) and representation (YAML output)
- Supports incremental assembly of complex structure

### Integration Context

YAMLContextBuilder will be consumed by:
- `ProductService.fetch_orchestrator_mission()` (Handover 0347b)
- `OrchestrationService` for mission generation
- Future context-fetching services (architecture, testing, etc.)

---

## Technical Details

### Files to Create

1. **`src/giljo_mcp/yaml_context_builder.py`**
   - Location: Core utility module (alongside `thin_client_prompt_generator.py`)
   - Purpose: YAMLContextBuilder class implementation
   - Dependencies: `yaml` (PyYAML), `typing` (Dict, List, Any)

2. **`tests/services/test_yaml_context_builder.py`**
   - Location: Service-layer tests
   - Purpose: Comprehensive unit tests for YAML builder
   - Dependencies: `pytest`, `yaml`

### Class API Design

```python
class YAMLContextBuilder:
    """
    Builds structured YAML context with priority framing.

    Organizes context into three priority tiers:
    - CRITICAL (Priority 1): Always inline, always read (~350 tokens)
    - IMPORTANT (Priority 2): Condensed guidance (~200 tokens)
    - REFERENCE (Priority 3): Summaries with fetch pointers (~150 tokens)
    """

    # Priority Declaration Methods (no content, just field names)
    def add_critical(self, field_name: str) -> None
    def add_important(self, field_name: str) -> None
    def add_reference(self, field_name: str) -> None

    # Content Addition Methods (with actual data)
    def add_critical_content(self, field_name: str, content: Any) -> None
    def add_important_content(self, field_name: str, content: Any) -> None
    def add_reference_content(self, field_name: str, content: Any) -> None

    # Output Methods
    def to_yaml(self) -> str
    def estimate_tokens(self) -> int
```

### YAML Output Structure

```yaml
# ===================================================================
# CONTEXT PRIORITY MAP - Read this first
# ===================================================================
priorities:
  CRITICAL:
    - product_core
    - tech_stack
  IMPORTANT:
    - architecture
  REFERENCE:
    - vision_documents

# ===================================================================
# CRITICAL (Priority 1) - Always inline, always read
# ===================================================================
product_core:
  name: "TinyContacts"
  type: "Contact management"
  features:
    - photos
    - dates
    - tags

tech_stack:
  languages:
    - Python 3.11+
  frameworks:
    - FastAPI
    - Vue 3

# ===================================================================
# IMPORTANT (Priority 2) - Inline but condensed
# ===================================================================
architecture:
  pattern: "Modular monolith"
  api: "REST + OpenAPI"
  fetch_details: fetch_architecture()

# ===================================================================
# REFERENCE (Priority 3) - Summary only, fetch on-demand
# ===================================================================
vision_documents:
  available: true
  depth_setting: "moderate"
  estimated_tokens: 12500
  summary: "40K word product vision"
  fetch_tool: fetch_vision_document(page=N)
```

### Token Estimation Formula

```python
def estimate_tokens(self) -> int:
    """
    Uses 1 token ≈ 4 characters heuristic.

    This approximation is used by Claude and OpenAI for quick estimates.
    For precise counting, would need tiktoken library, but adds dependency.
    """
    yaml_output = self.to_yaml()
    return len(yaml_output) // 4
```

---

## Implementation Plan

### Phase 1: RED (Write Failing Tests) - 30 minutes

**Step 1.1**: Create test file structure
- Create `tests/services/test_yaml_context_builder.py`
- Add module docstring: "Handover 0347a: YAML Context Builder Tests"
- Import necessary modules: `pytest`, `yaml`, `YAMLContextBuilder`

**Step 1.2**: Write behavioral tests (in order of execution)

1. **`test_priority_map_section`**
   - BEHAVIOR: Priority map should list fields in correct tiers
   - SETUP: Add fields to critical/important/reference
   - ASSERT: YAML contains priority map with correct field names

2. **`test_critical_section_inline_content`**
   - BEHAVIOR: Critical fields should have full inline content
   - SETUP: Add critical content with nested dict
   - ASSERT: YAML contains all key-value pairs fully expanded

3. **`test_important_section_condensed_content`**
   - BEHAVIOR: Important fields should have condensed content with fetch pointers
   - SETUP: Add important content with fetch_details key
   - ASSERT: YAML contains condensed info + fetch tool reference

4. **`test_reference_section_summary_only`**
   - BEHAVIOR: Reference fields should only show summary + fetch tool
   - SETUP: Add reference content with summary/fetch_tool keys
   - ASSERT: YAML contains metadata but not full content

5. **`test_yaml_is_valid_parseable`**
   - BEHAVIOR: Generated YAML should be valid and parseable by PyYAML
   - SETUP: Build YAML with mixed content
   - ASSERT: `yaml.safe_load()` succeeds, parsed structure matches

6. **`test_token_count_estimate`**
   - BEHAVIOR: Token estimate should be within 10% of actual (1 token ≈ 4 chars)
   - SETUP: Build YAML, call estimate_tokens()
   - ASSERT: Estimated tokens == len(yaml_output) // 4

**Step 1.3**: Run tests and verify they fail
```bash
pytest tests/services/test_yaml_context_builder.py -v
```
Expected: 6 failures (ImportError: cannot import 'YAMLContextBuilder')

### Phase 2: GREEN (Implement Minimal Code) - 60 minutes

**Step 2.1**: Create module skeleton
- Create `src/giljo_mcp/yaml_context_builder.py`
- Add comprehensive module docstring (purpose, usage example)
- Import dependencies: `yaml`, `typing.Any`, `typing.Dict`, `typing.List`

**Step 2.2**: Implement YAMLContextBuilder class

```python
class YAMLContextBuilder:
    """Builds structured YAML context with priority framing."""

    def __init__(self):
        # Priority field lists (field names only)
        self.critical_fields: List[str] = []
        self.important_fields: List[str] = []
        self.reference_fields: List[str] = []

        # Content dictionaries (field_name -> data)
        self.critical_content: Dict[str, Any] = {}
        self.important_content: Dict[str, Any] = {}
        self.reference_content: Dict[str, Any] = {}
```

**Step 2.3**: Implement priority declaration methods
- `add_critical()`: Append to critical_fields (if not duplicate)
- `add_important()`: Append to important_fields (if not duplicate)
- `add_reference()`: Append to reference_fields (if not duplicate)

**Step 2.4**: Implement content addition methods
- `add_critical_content()`: Store in critical_content dict
- `add_important_content()`: Store in important_content dict
- `add_reference_content()`: Store in reference_content dict

**Step 2.5**: Implement `to_yaml()` method
- Build priority map section with header banner
- Build CRITICAL section (if content exists)
- Build IMPORTANT section (if content exists)
- Build REFERENCE section (if content exists)
- Use `yaml.dump()` with `default_flow_style=False`, `sort_keys=False`
- Join sections with newlines

**Step 2.6**: Implement `estimate_tokens()` method
- Generate YAML output via `to_yaml()`
- Return `len(yaml_output) // 4`

**Step 2.7**: Run tests and verify they pass
```bash
pytest tests/services/test_yaml_context_builder.py -v
```
Expected: 6 passes (all tests green)

### Phase 3: REFACTOR (Code Quality) - 30 minutes

**Step 3.1**: Code quality checks
- Run `ruff src/giljo_mcp/yaml_context_builder.py` (linting)
- Run `black src/giljo_mcp/yaml_context_builder.py` (formatting)
- Fix any linting issues

**Step 3.2**: Review docstrings
- Verify all public methods have docstrings
- Add type hints to return values
- Document return value format for `to_yaml()`

**Step 3.3**: Edge case testing (optional, if time permits)
- Test empty builder (no fields, no content)
- Test duplicate field names (should not create duplicates)
- Test None content values
- Test very large content (ensure token estimate is reasonable)

**Step 3.4**: Integration verification
- Manually test builder with realistic orchestrator data
- Generate YAML output and verify it looks correct
- Estimate tokens and verify it's under 2000 (target budget)

---

## Testing Requirements

### Unit Tests (TDD - Write Tests FIRST)

**Test File**: `tests/services/test_yaml_context_builder.py`

**Required Tests** (6 total):

1. **Priority Map Generation**
   - Test: `test_priority_map_section`
   - Verifies: Priority map lists correct fields in CRITICAL/IMPORTANT/REFERENCE tiers

2. **Critical Content Inline**
   - Test: `test_critical_section_inline_content`
   - Verifies: Full nested content appears in CRITICAL section

3. **Important Content Condensed**
   - Test: `test_important_section_condensed_content`
   - Verifies: Condensed content with fetch_details pointer

4. **Reference Content Summary**
   - Test: `test_reference_section_summary_only`
   - Verifies: Only summary + fetch_tool in REFERENCE section

5. **YAML Validity**
   - Test: `test_yaml_is_valid_parseable`
   - Verifies: PyYAML can parse generated output without errors

6. **Token Estimation**
   - Test: `test_token_count_estimate`
   - Verifies: Token estimate uses 1 token ≈ 4 characters formula

### Test Execution

```bash
# Run all tests
pytest tests/services/test_yaml_context_builder.py -v

# Run with coverage
pytest tests/services/test_yaml_context_builder.py -v --cov=src.giljo_mcp.yaml_context_builder --cov-report=term-missing

# Expected coverage: >95% (only edge cases should be uncovered)
```

### TDD Workflow

```
1. Write test (RED) → 2. Implement code (GREEN) → 3. Refactor (CLEAN)
        ↓                        ↓                          ↓
   Tests FAIL            Tests PASS                 Tests STILL PASS
```

**CRITICAL**: Do NOT write implementation code before tests exist and fail.

---

## Dependencies and Blockers

### Dependencies

**Required Libraries**:
- ✅ PyYAML (already in `requirements.txt`)
- ✅ Python 3.11+ (project standard)
- ✅ pytest (already in dev dependencies)

**Codebase Dependencies**:
- None (this is a standalone utility)
- Does NOT depend on database, services, or MCP tools
- Pure utility class (no async, no I/O)

### Blockers

**None Identified** - This handover is fully self-contained.

**Future Blockers** (for dependent handovers):
- 0347b: ProductService migration depends on this builder
- 0347c: Orchestrator integration depends on 0347b

---

## Success Criteria

### Functional Requirements

- ✅ **All 6 unit tests pass** (test_yaml_context_builder.py)
- ✅ **Valid YAML output** parseable by `yaml.safe_load()`
- ✅ **Token estimation accuracy** within 10% (1 token ≈ 4 chars)
- ✅ **Priority map section** lists all declared fields
- ✅ **Tiered content sections** render correctly (CRITICAL/IMPORTANT/REFERENCE)

### Code Quality Requirements

- ✅ **Linting**: No ruff errors
- ✅ **Formatting**: Black-compliant
- ✅ **Type hints**: All public methods have type annotations
- ✅ **Docstrings**: Module, class, and all public methods documented
- ✅ **Test coverage**: >95% line coverage

### Performance Requirements

- ✅ **Token budget**: Generated YAML < 2000 tokens (realistic orchestrator mission)
- ✅ **Execution speed**: `to_yaml()` completes in <10ms (no heavy computation)

### Integration Requirements

- ✅ **Import path**: `from src.giljo_mcp.yaml_context_builder import YAMLContextBuilder`
- ✅ **No side effects**: Pure utility, no global state
- ✅ **Thread-safe**: No shared mutable state between instances

---

## Rollback Plan

### If Tests Fail to Pass (Phase 2)

1. **Review test expectations**: Ensure tests are testing BEHAVIOR, not implementation
2. **Debug implementation**: Use `print(builder.to_yaml())` to inspect output
3. **Incremental fixes**: Fix one test at a time (don't try to fix all 6 at once)
4. **Seek help**: If stuck for >30 minutes, escalate to orchestrator

### If YAML Parsing Fails

**Symptom**: `yaml.safe_load()` raises exception

**Diagnosis**:
- Check for invalid YAML syntax (indentation, quotes, special characters)
- Verify `yaml.dump()` parameters (default_flow_style, sort_keys)
- Test with minimal example (one field, one value)

**Fix**:
- Use `yaml.safe_dump()` instead of `yaml.dump()` for strict validation
- Add explicit quoting for string values: `yaml.dump(data, default_style='"')`

### If Token Estimation is Inaccurate

**Symptom**: Estimate differs from actual by >10%

**Diagnosis**:
- 1 token ≈ 4 characters is a heuristic, not exact
- Special characters (emojis, unicode) may skew estimate
- YAML formatting adds overhead (indentation, colons)

**Fix**:
- Adjust formula: `len(yaml_output) // 3.5` (more conservative)
- Document known variance in docstring
- Consider adding tiktoken library for exact counting (adds dependency)

### Nuclear Option

If implementation is fundamentally broken:

1. **Delete implementation file**: `rm src/giljo_mcp/yaml_context_builder.py`
2. **Keep test file**: Tests define the contract
3. **Re-read specification**: Review lines 819-1073 of parent handover
4. **Start fresh**: Begin Phase 2 again with clear head

**DO NOT**:
- Delete tests (they define what success looks like)
- Skip TDD workflow (writing tests first catches design issues early)
- Copy-paste code without understanding (builds technical debt)

---

## Verification Steps

### Manual Testing (After All Tests Pass)

```python
# Open Python REPL
from src.giljo_mcp.yaml_context_builder import YAMLContextBuilder

# Build realistic orchestrator mission
builder = YAMLContextBuilder()

# Add priority declarations
builder.add_critical("product_core")
builder.add_critical("tech_stack")
builder.add_important("architecture")
builder.add_reference("vision_documents")

# Add critical content (full inline)
builder.add_critical_content("product_core", {
    "name": "TinyContacts",
    "type": "Contact management app",
    "features": ["photos", "birthdays", "tags"]
})

builder.add_critical_content("tech_stack", {
    "languages": ["Python 3.11+"],
    "frameworks": ["FastAPI", "Vue 3"],
    "database": "PostgreSQL 18"
})

# Add important content (condensed)
builder.add_important_content("architecture", {
    "pattern": "Modular monolith",
    "api": "REST + OpenAPI",
    "fetch_details": "fetch_architecture()"
})

# Add reference content (summary only)
builder.add_reference_content("vision_documents", {
    "available": True,
    "depth_setting": "moderate",
    "estimated_tokens": 12500,
    "summary": "40K word product vision covering UX, features, roadmap",
    "fetch_tool": "fetch_vision_document(page=N)"
})

# Generate YAML
yaml_output = builder.to_yaml()
print(yaml_output)

# Check token estimate
tokens = builder.estimate_tokens()
print(f"\nEstimated tokens: {tokens}")
print(f"Target budget: 2000")
print(f"Under budget: {tokens < 2000}")

# Validate parseability
import yaml
parsed = yaml.safe_load(yaml_output)
print(f"\nParsed structure keys: {list(parsed.keys())}")
```

**Expected Output**:
- YAML with clear priority map at top
- Three tiered sections with visual separators
- Token estimate ~700-900 (well under 2000)
- Parsed structure contains: priorities, product_core, tech_stack, architecture, vision_documents

---

## Notes for Implementor

### TDD Best Practices

1. **Write tests FIRST** - Don't write implementation until tests exist and fail
2. **Test behavior, not implementation** - Tests should verify WHAT the code does, not HOW
3. **Use descriptive test names** - `test_critical_section_inline_content` is self-documenting
4. **Avoid testing internals** - Don't assert on `builder.critical_fields` (internal state)
5. **Assert on observable behavior** - Assert on YAML output (public API)

### Common TDD Mistakes to Avoid

❌ **Mistake**: Writing implementation before tests
✅ **Correct**: Write test, see it fail (RED), then implement

❌ **Mistake**: Testing internal state (`assert len(builder.critical_fields) == 2`)
✅ **Correct**: Test observable output (`assert "product_core" in yaml_output`)

❌ **Mistake**: One giant test that tests everything
✅ **Correct**: Focused tests, each verifying one behavior

❌ **Mistake**: Tests that pass even when implementation is broken
✅ **Correct**: Tests that fail when expected behavior is missing

### YAML Gotchas

1. **Indentation**: YAML is whitespace-sensitive (like Python)
2. **Quotes**: Strings with special chars need quotes (`"value: with: colons"`)
3. **Booleans**: `true`/`false` (lowercase) not `True`/`False`
4. **Lists**: Two formats allowed (flow: `[a, b]` or block: `\n- a\n- b`)
5. **Null**: `null` or empty (not `None`)

Use `default_flow_style=False` for readable block-style YAML.

### Token Estimation Philosophy

The 1 token ≈ 4 characters heuristic is:
- **Fast**: No external library needed
- **Approximate**: Within 10-20% of actual
- **Conservative**: Tends to overestimate (safe for budgeting)

For exact counting, would need:
```python
import tiktoken
encoder = tiktoken.encoding_for_model("claude-opus-4")
tokens = len(encoder.encode(yaml_output))
```

But this adds heavy dependency (tiktoken + model files). Heuristic is sufficient for MVP.

---

## Completion Checklist

Before marking handover complete, verify:

- [ ] Test file created: `tests/services/test_yaml_context_builder.py`
- [ ] Implementation file created: `src/giljo_mcp/yaml_context_builder.py`
- [ ] All 6 unit tests pass
- [ ] Test coverage >95%
- [ ] Linting clean (`ruff src/giljo_mcp/yaml_context_builder.py`)
- [ ] Formatting clean (`black src/giljo_mcp/yaml_context_builder.py`)
- [ ] Manual testing completed (REPL example above)
- [ ] Token estimate verified under 2000 for realistic mission
- [ ] YAML parseability verified (`yaml.safe_load()` succeeds)
- [ ] Git commit created with message: "feat: Add YAML context builder (Handover 0347a)"

---

## Example Git Commit Message

```
feat: Add YAML context builder for orchestrator missions (Handover 0347a)

Implements YAMLContextBuilder utility class to generate structured YAML
missions with explicit priority framing (CRITICAL/IMPORTANT/REFERENCE).

Key features:
- Priority map section (read-first declaration)
- Tiered content sections (full inline → condensed → summary)
- Token estimation method (1 token ≈ 4 chars)
- PyYAML validation and parseability

Testing:
- 6 comprehensive unit tests (100% behavioral coverage)
- >95% line coverage
- Manual integration testing

Part of mission YAML restructuring initiative (reduces tokens from
~21,000 to ~1,500, 93% reduction).

Related: Handover 0347 (parent), 0347b (ProductService migration)
```

---

## File Paths Summary

**Files to Create**:
- `F:\GiljoAI_MCP\src\giljo_mcp\yaml_context_builder.py`
- `F:\GiljoAI_MCP\tests\services\test_yaml_context_builder.py`

**Files to Reference** (read-only):
- `F:\GiljoAI_MCP\handovers\0347_mission_response_yaml_restructuring.md` (lines 819-1073)
- `F:\GiljoAI_MCP\requirements.txt` (verify PyYAML present)

**No Files Modified** (this is greenfield development)

---

**END OF HANDOVER 0347a**
