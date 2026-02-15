# Handover: 0347f - Integration & E2E Testing for JSON Mission Restructuring

---
**Handover**: 0347f - Integration & E2E Testing
**Type**: Backend Testing
**Effort**: 3 hours
**Priority**: P0
**Status**: Ready for Implementation
**Parent**: 0347 - Mission Response JSON Restructuring
**Dependencies**: 0347a, 0347b, 0347c, 0347d, 0347e (ALL must be complete)
---

## Problem Statement

The JSON mission restructuring (handovers 0347a-e) introduces significant changes to the orchestrator instruction pipeline:
- New JSON context builder utility
- Refactored MissionPlanner with JSON output
- Enhanced response fields
- Depth toggles for agent templates and vision documents

**Risk**: These changes modify critical orchestration paths. Without comprehensive integration and E2E testing, we risk:
1. Broken orchestrator workflows (agents cannot fetch missions)
2. Invalid JSON generation (parsing failures in production)
3. Token budget violations (>2,000 tokens defeats the purpose)
4. Incomplete priority mapping (CRITICAL/IMPORTANT/REFERENCE sections missing)
5. Regression in existing MCP tool behaviors

**Goal**: Verify the complete JSON mission generation pipeline works end-to-end with >80% test coverage.

---

## Scope

### ✅ In Scope
- Integration tests for complete JSON mission generation workflow
- E2E tests via MCP tool calls (`get_orchestrator_instructions`)
- JSON structure validation (stdlib json parsing)
- Token count verification (<2,000 tokens per mission)
- Priority mapping validation (CRITICAL/IMPORTANT/REFERENCE sections)
- Vision document summarization testing
- Agent template depth toggle testing
- Coverage reporting (pytest-cov)

### ❌ Out of Scope
- Unit tests for individual components (covered in 0347a-e)
- Frontend UI testing for depth configuration
- Performance benchmarking
- Load testing with concurrent orchestrator requests

---

## Dependencies

**CRITICAL**: This handover CANNOT proceed until ALL previous handovers are complete:

| Handover | Component | Status Required |
|----------|-----------|-----------------|
| 0347a | JSON Context Builder | ✅ Complete + Unit Tests Passing |
| 0347b | MissionPlanner JSON Refactor | ✅ Complete + Unit Tests Passing |
| 0347c | Response Fields Enhancement | ✅ Complete + Unit Tests Passing |
| 0347d | Agent Templates Depth Toggle | ✅ Complete + Unit Tests Passing |
| 0347e | Vision Document 4-Level Depth | ✅ Complete + Unit Tests Passing |

**Verification Command**:
```bash
# All previous unit tests must pass
pytest tests/services/test_json_context_builder.py -v
pytest tests/services/test_mission_planner.py -v
pytest tests/tools/test_orchestration.py -v
```

---

## Test-Driven Development Workflow

**CRITICAL**: Follow TDD principles strictly.

### TDD Cycle

1. **Write Test First** - Test should initially FAIL (red)
2. **Implement Code** - Write minimal code to make test PASS (green)
3. **Refactor** - Improve code without breaking tests
4. **Commit** - Commit tests separately from implementation

### Test Naming Convention

```python
# ✅ GOOD - Describes behavior
def test_full_json_mission_generation():
    """Test complete JSON mission generation workflow."""

# ✅ GOOD - Specific outcome
def test_json_token_count_under_2000():
    """JSON mission should be <2,000 tokens."""

# ❌ BAD - Tests implementation detail
def test_json_context_builder_called():
    """JSONContextBuilder instance created."""
```

### Test Focus

Tests should verify **BEHAVIOR**, not **IMPLEMENTATION**:
- ✅ Test: "JSON mission parses correctly"
- ❌ Test: "JSONContextBuilder._build_section() was called"

---

## Tasks

### Phase 1: Integration Test Suite (1.5 hours)

- [ ] **Task 1.1**: Create `tests/integration/test_json_mission_generation.py`
  - TDD: Write failing test for complete workflow
  - Verify: JSON structure, token count, priority sections
  - Coverage: >80% for JSONContextBuilder + MissionPlanner

- [ ] **Task 1.2**: Test JSON mission with vision document summarization
  - TDD: Write test for vision depth=moderate
  - Verify: Summary present, full content NOT inlined
  - Expected: Mission <5,000 tokens (much smaller than 21K)

- [ ] **Task 1.3**: Test agent templates depth toggle
  - TDD: Test Type Only mode (~50 tokens/agent)
  - TDD: Test Full mode (~2000-3000 tokens/agent)
  - Verify: Conditional content inclusion works

- [ ] **Task 1.4**: Test priority mapping structure
  - TDD: Verify CRITICAL/IMPORTANT/REFERENCE sections
  - Verify: Correct fields in each priority level
  - Verify: Fetch tool pointers in REFERENCE section

### Phase 2: E2E Testing via MCP Tools (1 hour)

- [ ] **Task 2.1**: Test `get_orchestrator_instructions` E2E
  - TDD: Test MCP tool returns valid JSON
  - Verify: `mission_format` field = "json"
  - Verify: Mission field parseable by stdlib json
  - Verify: Estimated tokens <2,000

- [ ] **Task 2.2**: Test orchestrator workflow integration
  - TDD: Test orchestrator can fetch and parse JSON mission
  - Verify: Priority sections accessible
  - Verify: Fetch tool references work (e.g., fetch_vision_document)

- [ ] **Task 2.3**: Test enhanced response fields
  - TDD: Verify all 6 new fields present (0347c)
  - Verify: Mode-aware conditional logic (cli_mode=false)
  - Verify: ~175 token addition as expected

### Phase 3: Coverage & Validation (0.5 hours)

- [ ] **Task 3.1**: Generate coverage report
  - Command: `pytest tests/ --cov=src/giljo_mcp --cov-report=html`
  - Target: >80% coverage for affected modules
  - Review: `htmlcov/index.html`

- [ ] **Task 3.2**: Manual E2E validation
  - Launch project with vision document via UI
  - Fetch orchestrator instructions via MCP
  - Verify YAML structure manually
  - Confirm token count in response
  - Test fetch_vision_document() for full content

- [ ] **Task 3.3**: Documentation updates
  - Update CLAUDE.md with testing commands
  - Add integration test examples to TESTING.md
  - Document manual E2E testing steps

---

## Success Criteria

### ✅ Automated Tests

1. **All integration tests pass**
   ```bash
   pytest tests/integration/test_json_mission_generation.py -v
   # Expected: 6+ tests, all passing
   ```

2. **JSON parsing validation**
   - Every generated mission parseable by `json.loads()`
   - No parsing exceptions

3. **Token budget compliance**
   - All missions <2,000 tokens (93% reduction from 21K)
   - Estimated tokens within 10% of actual

4. **Priority structure validation**
   - CRITICAL section contains: product_core, tech_stack
   - IMPORTANT section contains: architecture, testing, agent_templates
   - REFERENCE section contains: vision_documents, memory_360, git_history

5. **Coverage target met**
   - >80% coverage for:
     - `src/giljo_mcp/json_context_builder.py`
     - `src/giljo_mcp/mission_planner.py` (JSON paths)
     - MCP tool integration (orchestrator instructions)

### ✅ Manual E2E Tests

6. **End-to-end workflow validation**
   - Create project → Upload vision → Launch orchestrator → Fetch instructions
   - JSON mission received and parseable
   - Vision document summary present (not full content)
   - Fetch tool references work (fetch_vision_document, fetch_architecture, etc.)

7. **Depth toggle verification**
   - Agent templates: Type Only mode shows ~50 tokens/agent
   - Agent templates: Full mode shows ~2000-3000 tokens/agent
   - Vision documents: Optional/Light/Medium/Full modes produce expected token counts

### ✅ Regression Prevention

8. **Existing tests still pass**
   ```bash
   pytest tests/services/ -v
   pytest tests/tools/ -v
   # All pre-existing tests must remain green
   ```

9. **No breaking changes**
   - Backward compatibility maintained (if old clients exist)
   - Database schema unchanged
   - API contracts unchanged

---

## Implementation Details

### File Structure

```
tests/
├── integration/
│   └── test_json_mission_generation.py    # NEW - Integration tests
├── services/
│   ├── test_json_context_builder.py        # From 0347a (verify complete)
│   └── test_mission_planner.py             # From 0347b (verify updated)
└── tools/
    └── test_orchestration.py               # From 0347c (verify updated)
```

### Integration Test Template

```python
"""
Handover 0347f: Integration tests for JSON mission generation.

TDD Principles:
1. Write test FIRST (it should fail initially)
2. Implement minimal code to make test pass
3. Refactor if needed
4. Test should focus on BEHAVIOR, not implementation
"""

import pytest
import json
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project


@pytest.mark.asyncio
async def test_full_json_mission_generation(db_manager, sample_product, sample_project):
    """
    Test complete JSON mission generation workflow.

    TDD: This test should FAIL before 0347a-b are implemented.
    Expected behavior: Mission field is valid JSON with priority sections.
    """
    planner = MissionPlanner(db_manager)

    # Configure priorities (from Context Configurator UI)
    field_priorities = {
        "product_core": 1,      # CRITICAL
        "tech_stack": 1,        # CRITICAL
        "architecture": 2,      # IMPORTANT
        "testing": 2,           # IMPORTANT
        "agent_templates": 2,   # IMPORTANT
        "vision_documents": 3,  # REFERENCE
        "memory_360": 3,        # REFERENCE
        "git_history": 3        # REFERENCE
    }

    depth_config = {
        "vision_documents": "moderate",
        "agent_templates": "type_only",  # ~50 tokens/agent
        "memory_360": 5,
        "git_history": 25
    }

    # Generate JSON mission
    mission_json = await planner._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities=field_priorities,
        depth_config=depth_config
    )

    # BEHAVIOR TEST: Should be valid JSON
    parsed = json.loads(mission_json)
    assert parsed is not None, "JSON parsing failed"

    # BEHAVIOR TEST: Should have priority map
    assert "priorities" in parsed, "Missing priorities section"
    assert "CRITICAL" in parsed["priorities"]
    assert "IMPORTANT" in parsed["priorities"]
    assert "REFERENCE" in parsed["priorities"]

    # BEHAVIOR TEST: CRITICAL fields should be inlined
    assert "product_core" in parsed
    assert "tech_stack" in parsed
    assert parsed["product_core"] is not None
    assert parsed["tech_stack"] is not None

    # BEHAVIOR TEST: REFERENCE fields should have fetch tools
    assert "vision_documents" in parsed
    assert "fetch_tool" in parsed["vision_documents"]
    assert "fetch_vision_document" in parsed["vision_documents"]["fetch_tool"]

    # BEHAVIOR TEST: Token count should be <2,000
    estimated_tokens = len(mission_json) // 4
    assert estimated_tokens < 2000, f"Expected <2K tokens, got {estimated_tokens}"


@pytest.mark.asyncio
async def test_json_mission_with_vision_summary(db_manager, product_with_vision, sample_project):
    """
    Test vision documents are summarized, not inlined.

    TDD: Should FAIL if vision content is fully inlined (old behavior).
    Expected: Vision summary present, full content via fetch tool only.
    """
    planner = MissionPlanner(db_manager)

    field_priorities = {"vision_documents": 3}  # REFERENCE priority
    depth_config = {"vision_documents": "moderate"}  # 66% summary

    mission_json = await planner._build_context_with_priorities(
        product=product_with_vision,
        project=sample_project,
        field_priorities=field_priorities,
        depth_config=depth_config
    )

    parsed = json.loads(mission_json)

    # BEHAVIOR TEST: Should have vision section
    assert "vision_documents" in parsed

    # BEHAVIOR TEST: Should have summary (not full content)
    assert "summary" in parsed["vision_documents"]
    assert len(parsed["vision_documents"]["summary"]) > 0

    # BEHAVIOR TEST: Should have fetch tool reference
    assert "fetch_tool" in parsed["vision_documents"]
    assert "when_to_fetch" in parsed["vision_documents"]

    # BEHAVIOR TEST: Should be much smaller than full vision (21K tokens)
    estimated_tokens = len(mission_json) // 4
    assert estimated_tokens < 5000, f"Vision summary too large: {estimated_tokens} tokens"


@pytest.mark.asyncio
async def test_orchestrator_instructions_json_format(db_manager, sample_orchestrator):
    """
    Test get_orchestrator_instructions MCP tool returns JSON.

    TDD: E2E test through MCP tool layer.
    Expected: Response has mission_format=json and parseable mission field.
    """
    from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

    response = await get_orchestrator_instructions(
        orchestrator_id=str(sample_orchestrator.job_id),
        tenant_key=sample_orchestrator.tenant_key,
        db_manager=db_manager
    )

    # BEHAVIOR TEST: Should indicate JSON format
    assert response["mission_format"] == "json"

    # BEHAVIOR TEST: Mission should be valid JSON
    assert "mission" in response
    parsed = json.loads(response["mission"])
    assert parsed is not None

    # BEHAVIOR TEST: Should have priority structure
    assert "priorities" in parsed
    assert "CRITICAL" in parsed["priorities"]
    assert "IMPORTANT" in parsed["priorities"]
    assert "REFERENCE" in parsed["priorities"]


@pytest.mark.asyncio
async def test_json_is_valid_parseable(db_manager, sample_product, sample_project):
    """
    Test JSON output is always valid and parseable.

    TDD: Should catch any JSON syntax errors.
    Expected: stdlib json can parse without exceptions.
    """
    planner = MissionPlanner(db_manager)

    field_priorities = {
        "product_core": 1,
        "tech_stack": 1,
        "architecture": 2
    }

    mission_json = await planner._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities=field_priorities,
        depth_config={}
    )

    # BEHAVIOR TEST: Should parse without exceptions
    try:
        parsed = json.loads(mission_json)
        assert parsed is not None
    except json.JSONDecodeError as e:
        pytest.fail(f"JSON parsing failed: {e}")


@pytest.mark.asyncio
async def test_json_token_count_under_2000(db_manager, sample_product, sample_project):
    """
    Test JSON mission token count is <2,000.

    TDD: Verifies 93% token reduction goal (21K → <2K).
    Expected: All missions under token budget.
    """
    planner = MissionPlanner(db_manager)

    # Full configuration (all fields)
    field_priorities = {
        "product_core": 1,
        "tech_stack": 1,
        "architecture": 2,
        "testing": 2,
        "agent_templates": 2,
        "vision_documents": 3,
        "memory_360": 3,
        "git_history": 3
    }

    depth_config = {
        "vision_documents": "moderate",
        "agent_templates": "type_only",
        "memory_360": 5,
        "git_history": 25
    }

    mission_json = await planner._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities=field_priorities,
        depth_config=depth_config
    )

    # BEHAVIOR TEST: Token count estimation
    estimated_tokens = len(mission_json) // 4  # 4 chars ≈ 1 token

    assert estimated_tokens < 2000, (
        f"Token budget exceeded: {estimated_tokens} tokens "
        f"(target: <2,000)"
    )


@pytest.mark.asyncio
async def test_priority_map_structure(db_manager, sample_product, sample_project):
    """
    Test priority map structure is correct.

    TDD: Validates CRITICAL/IMPORTANT/REFERENCE sections.
    Expected: Fields categorized correctly by priority.
    """
    planner = MissionPlanner(db_manager)

    field_priorities = {
        "product_core": 1,      # CRITICAL
        "tech_stack": 1,        # CRITICAL
        "architecture": 2,      # IMPORTANT
        "testing": 2,           # IMPORTANT
        "vision_documents": 3,  # REFERENCE
        "memory_360": 3         # REFERENCE
    }

    mission_json = await planner._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities=field_priorities,
        depth_config={}
    )

    parsed = json.loads(mission_json)

    # BEHAVIOR TEST: Priority map exists
    assert "priorities" in parsed
    priority_map = parsed["priorities"]

    # BEHAVIOR TEST: CRITICAL section
    assert "CRITICAL" in priority_map
    assert "product_core" in priority_map["CRITICAL"]
    assert "tech_stack" in priority_map["CRITICAL"]

    # BEHAVIOR TEST: IMPORTANT section
    assert "IMPORTANT" in priority_map
    assert "architecture" in priority_map["IMPORTANT"]
    assert "testing" in priority_map["IMPORTANT"]

    # BEHAVIOR TEST: REFERENCE section
    assert "REFERENCE" in priority_map
    assert "vision_documents" in priority_map["REFERENCE"]
    assert "memory_360" in priority_map["REFERENCE"]


@pytest.mark.asyncio
async def test_agent_templates_depth_toggle(db_manager, sample_product, sample_project):
    """
    Test agent templates depth toggle (Type Only vs Full).

    TDD: From handover 0347d.
    Expected: Type Only ~50 tokens/agent, Full ~2000-3000 tokens/agent.
    """
    planner = MissionPlanner(db_manager)

    field_priorities = {"agent_templates": 2}  # IMPORTANT

    # Test Type Only mode
    depth_config_type_only = {"agent_templates": "type_only"}
    mission_type_only = await planner._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities=field_priorities,
        depth_config=depth_config_type_only
    )

    # Test Full mode
    depth_config_full = {"agent_templates": "full"}
    mission_full = await planner._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities=field_priorities,
        depth_config=depth_config_full
    )

    # BEHAVIOR TEST: Type Only should be much smaller
    tokens_type_only = len(mission_type_only) // 4
    tokens_full = len(mission_full) // 4

    assert tokens_type_only < tokens_full, (
        "Type Only mode should use fewer tokens than Full mode"
    )

    # Parse and verify structure
    parsed_full = json.loads(mission_full)
    assert "agent_templates" in parsed_full

    # Full mode should have agent prompts
    if "agents" in parsed_full["agent_templates"]:
        # Verify agent details are included
        agents = parsed_full["agent_templates"]["agents"]
        assert len(agents) > 0, "Full mode should include agent details"


@pytest.mark.asyncio
async def test_enhanced_response_fields_present(db_manager, sample_orchestrator):
    """
    Test enhanced response fields from 0347c are present.

    TDD: Verifies 6 new guidance fields added.
    Expected: All fields in response, ~175 tokens added.
    """
    from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

    response = await get_orchestrator_instructions(
        orchestrator_id=str(sample_orchestrator.job_id),
        tenant_key=sample_orchestrator.tenant_key,
        db_manager=db_manager
    )

    # BEHAVIOR TEST: New fields should be present
    expected_fields = [
        "post_staging_behavior",
        "required_final_action",
        "error_handling",
        "agent_spawning_limits",
        "context_management"
    ]

    for field in expected_fields:
        assert field in response, f"Missing enhanced field: {field}"

    # BEHAVIOR TEST: Mode-aware field (cli_mode=false only)
    # This requires checking if cli_mode is false in the test fixture
    # If cli_mode is false, multi_terminal_mode_rules should be present
```

---

## Manual E2E Testing Steps

**Purpose**: Verify the complete workflow works in production-like conditions.

### Setup

1. **Start development server**
   ```bash
   python startup.py --dev
   ```

2. **Open dashboard**
   ```
   http://localhost:7272
   ```

3. **Login** (use existing test user or create new)

### Test Scenario 1: YAML Mission Generation

1. **Create new project**
   - Navigate to Projects tab
   - Click "New Project"
   - Name: "YAML Test Project"
   - Description: "Testing YAML mission generation"

2. **Upload vision document**
   - Click "Upload Vision"
   - Select a multi-page document (>5,000 tokens)
   - Verify upload succeeds

3. **Configure context depth**
   - Go to My Settings → Context
   - Set vision_documents depth: "Moderate"
   - Set agent_templates depth: "Type Only"
   - Save configuration

4. **Launch orchestrator**
   - Return to project
   - Click "Launch Orchestrator"
   - Wait for orchestrator to spawn

5. **Fetch orchestrator instructions via MCP**
   - Use MCP client or test script
   - Call `get_orchestrator_instructions(orchestrator_id, tenant_key)`
   - Save response to file

6. **Verify JSON structure**
   ```bash
   # Parse JSON manually
   python -c "import json; print(json.load(open('response.json')))"
   ```

7. **Check token count**
   - Verify `estimated_tokens` in response
   - Should be <2,000

8. **Verify priority sections**
   - CRITICAL section exists
   - IMPORTANT section exists
   - REFERENCE section exists
   - Correct fields in each section

### Test Scenario 2: Vision Document Summarization

1. **Verify vision summary in JSON**
   - Check `vision_documents` section in mission JSON
   - Should have `summary` field (not full content)
   - Should have `fetch_tool` reference

2. **Test fetch_vision_document() tool**
   - Call `fetch_vision_document(page=1)`
   - Verify full content is returned
   - Confirm content matches uploaded document

### Test Scenario 3: Agent Templates Depth Toggle

1. **Test Type Only mode**
   - Set agent_templates depth: "Type Only"
   - Fetch orchestrator instructions
   - Verify agent_templates section is minimal (~50 tokens/agent)

2. **Test Full mode**
   - Set agent_templates depth: "Full"
   - Fetch orchestrator instructions
   - Verify agent_templates section includes full prompts (~2000+ tokens/agent)

### Test Scenario 4: Enhanced Response Fields

1. **Verify new fields in response**
   - Check for `post_staging_behavior`
   - Check for `required_final_action`
   - Check for `error_handling`
   - Check for `agent_spawning_limits`
   - Check for `context_management`

2. **Test mode-aware fields**
   - If cli_mode=false, verify `multi_terminal_mode_rules` present
   - If cli_mode=true, verify field absent

---

## Test Commands

### Run All Tests

```bash
# Complete test suite with coverage
pytest tests/ --cov=src/giljo_mcp --cov-report=html --cov-report=term

# Expected output:
# tests/integration/test_json_mission_generation.py ......... [100%]
# Coverage: >80%
```

### Run Integration Tests Only

```bash
pytest tests/integration/test_json_mission_generation.py -v

# Expected: 8+ tests, all passing
```

### Run Unit Tests for Dependencies

```bash
# Verify 0347a (JSON Context Builder)
pytest tests/services/test_json_context_builder.py -v

# Verify 0347b (MissionPlanner)
pytest tests/services/test_mission_planner.py -v

# Verify 0347c (Enhanced Response Fields)
pytest tests/tools/test_orchestration.py -v
```

### Coverage Report

```bash
# Generate HTML coverage report
pytest tests/ --cov=src/giljo_mcp --cov-report=html

# Open in browser (Windows)
start htmlcov/index.html

# Open in browser (Unix/Mac)
open htmlcov/index.html
```

### Target Modules for Coverage

- `src/giljo_mcp/json_context_builder.py` - Target: >80%
- `src/giljo_mcp/mission_planner.py` - Target: >80% (JSON paths)
- `src/giljo_mcp/tools/orchestration.py` - Target: >80% (get_orchestrator_instructions)

---

## Rollback Plan

If integration tests fail and cannot be fixed within 1 hour:

### Step 1: Identify Failing Component

```bash
# Run tests with verbose output
pytest tests/integration/test_json_mission_generation.py -v --tb=short

# Identify which handover's code is failing
```

### Step 2: Rollback Changes

```bash
# Rollback specific handover changes
git log --oneline --grep="0347[a-e]"
git revert <commit-hash>
```

### Step 3: Restore Previous State

```bash
# Restore markdown-based mission generation
# This may require reverting multiple commits from 0347a-e
git revert <commit-range>

# Run regression tests
pytest tests/services/ -v
pytest tests/tools/ -v
```

### Step 4: Document Failure

Create incident report:
- Which tests failed
- Error messages
- Suspected root cause
- Recommended fix approach

---

## Documentation Updates

### CLAUDE.md Updates

Add testing commands:

```markdown
## Testing JSON Mission Generation

**Integration Tests**:
```bash
pytest tests/integration/test_json_mission_generation.py -v
```

**Coverage Report**:
```bash
pytest tests/ --cov=src/giljo_mcp --cov-report=html
```

**Manual E2E Testing**:
See handovers/0347f_integration_e2e_testing.md for step-by-step guide.
```

### TESTING.md Updates

Add integration test examples:

```markdown
## Integration Testing Patterns

### JSON Mission Generation

Example integration test structure:

```python
@pytest.mark.asyncio
async def test_full_json_mission_generation(db_manager, sample_product, sample_project):
    """Test complete JSON mission generation workflow."""
    planner = MissionPlanner(db_manager)

    mission_json = await planner._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities={...},
        depth_config={...}
    )

    # Validate JSON structure
    parsed = json.loads(mission_json)
    assert "priorities" in parsed

    # Validate token count
    estimated_tokens = len(mission_json) // 4
    assert estimated_tokens < 2000
```

See: `tests/integration/test_json_mission_generation.py`
```

---

## Known Issues & Considerations

### Potential Issues

1. **JSON Special Characters**
   - Risk: Product names/descriptions with quotes or escape sequences
   - Mitigation: Use `json.dumps()` with proper escaping
   - Test: Include special characters in test fixtures

2. **Token Estimation Accuracy**
   - Risk: 4 chars/token is approximate, actual may vary
   - Mitigation: Accept 10% variance in tests
   - Test: Compare estimated vs actual tokens with OpenAI tokenizer

3. **Vision Document Chunking**
   - Risk: Summarization may truncate critical content
   - Mitigation: Provide fetch_tool for full content access
   - Test: Verify fetch_vision_document() returns complete document

4. **Database Fixtures**
   - Risk: Test fixtures may not match production data structure
   - Mitigation: Use realistic fixtures with vision docs, memory, git history
   - Test: Create comprehensive fixtures in conftest.py

### Performance Considerations

- **JSON Parsing**: stdlib json parsing is fast
  - Impact: Minimal overhead per mission fetch
  - Acceptable for high concurrent orchestrators

- **Token Counting**: Character-based estimation is fast
  - No need for OpenAI tokenizer API calls during tests
  - Validate with actual tokenizer in manual testing

---

## Acceptance Checklist

### Code Quality

- [ ] All integration tests written using TDD (test-first approach)
- [ ] Tests use descriptive names describing behavior
- [ ] Tests focus on behavior, not implementation details
- [ ] No hardcoded values (use constants/fixtures)
- [ ] Proper error handling in tests
- [ ] Tests are independent (no shared state)

### Functionality

- [ ] All 8+ integration tests pass
- [ ] JSON parsing works for all test cases
- [ ] Token count <2,000 for all missions
- [ ] Priority sections correctly structured
- [ ] Vision document summarization works
- [ ] Agent templates depth toggle works
- [ ] Enhanced response fields present

### Coverage

- [ ] >80% coverage for JSONContextBuilder
- [ ] >80% coverage for MissionPlanner (JSON paths)
- [ ] >80% coverage for orchestration MCP tools
- [ ] Coverage report generated (htmlcov/)

### E2E Validation

- [ ] Manual E2E test completed (all scenarios)
- [ ] JSON mission generated successfully via UI
- [ ] fetch_vision_document() works correctly
- [ ] Token estimates match actual usage
- [ ] No errors in server logs

### Regression

- [ ] All pre-existing tests still pass
- [ ] No breaking changes to API contracts
- [ ] Database schema unchanged
- [ ] Backward compatibility maintained

### Documentation

- [ ] CLAUDE.md updated with testing commands
- [ ] TESTING.md updated with integration test examples
- [ ] Manual E2E testing guide complete
- [ ] Rollback plan documented

---

## Commit Strategy

### Test Commits (Separate from Implementation)

```bash
# Commit 1: Integration test suite (FAILING state expected)
git add tests/integration/test_json_mission_generation.py
git commit -m "test: Add integration tests for JSON mission generation (Handover 0347f)

- Test complete JSON mission workflow
- Test vision document summarization
- Test priority mapping structure
- Test token count <2,000
- Test agent templates depth toggle
- Test enhanced response fields

Tests will PASS once 0347a-e are complete.

🤖 Generated with Claude Code

# Commit 2: Coverage reporting and documentation
git add pytest.ini htmlcov/ docs/
git commit -m "docs: Add coverage reporting and E2E testing guide (Handover 0347f)

- Configure pytest-cov for integration tests
- Add manual E2E testing steps
- Update CLAUDE.md with testing commands
- Update TESTING.md with integration examples

🤖 Generated with Claude Code
```

### No Implementation Commits

**CRITICAL**: This handover only adds tests for code implemented in 0347a-e. If tests fail due to missing implementation, go back and complete the dependent handovers first.

---

## Estimated Timeline

| Phase | Tasks | Duration | Dependencies |
|-------|-------|----------|--------------|
| **Setup** | Verify 0347a-e complete | 0.5h | ALL previous handovers |
| **Integration Tests** | Write 8+ tests (TDD) | 1.5h | Setup complete |
| **E2E Testing** | MCP tool testing | 1h | Integration tests complete |
| **Coverage & Validation** | Reports + manual testing | 0.5h | All tests complete |
| **Documentation** | Update guides | 0.5h | Validation complete |
| **TOTAL** | | **3-4h** | |

---

## Next Steps

After this handover is complete:

1. **Verify token reduction in production**
   - Deploy to staging environment
   - Monitor orchestrator token usage
   - Confirm 93% reduction achieved (21K → <2K)

2. **Gather orchestrator feedback**
   - Run 5-10 real orchestrator workflows
   - Collect feedback on YAML structure usability
   - Identify any missing context fields

3. **Performance benchmarking**
   - Measure YAML generation time vs markdown
   - Test with concurrent orchestrators (10-100)
   - Identify any bottlenecks

4. **Consider follow-up optimizations**
   - JSON alternative for faster parsing?
   - Compressed YAML for network transfer?
   - Caching for frequently-fetched context?

---

## References

- **Parent Handover**: `handovers/0347_mission_response_yaml_restructuring.md`
- **Dependencies**:
  - `handovers/0347a_yaml_context_builder.md`
  - `handovers/0347b_mission_planner_refactor.md`
  - `handovers/0347c_response_fields_enhancement.md`
  - `handovers/0347d_agent_templates_depth.md`
  - `handovers/0347e_vision_document_depth.md`
- **Testing Guide**: `docs/TESTING.md`
- **Handover Format**: `docs/HANDOVERS.md`
- **TDD Principles**: `.claude/agents/tdd-implementor.md`

---

**END OF HANDOVER 0347f**
